---
layout: post
title: "Router to Switch 통신 문제(VMware, GNS) 분석 및 해결"
date: 2025-08-22 22:00:00 +0900
categories: [Router, Switch, Routing, L2, L3, GNS, VMware, Protocol,]
author: cotes
published: true
---<img width="1702" height="870" alt="gns기본네트워크토폴리지" src="https://github.com/user-attachments/assets/e287866b-ca4f-47a6-a9de-cefd1670d625" />


아래 네트워크 토폴로지에서 host -> Router 로 정상적으로 트래픽이 흐르지 않는 문제가 발생했습니다. ip 설정, 이전에 스위치와 라우터 포트간에 통신 방식(duplex, half duplex)
matching을 시켜주었지만, 통신이 되지 않았고, 스위치의 MAC 테이블에 MAC 러닝이 되지 않은걸 보니 Switch에서 연결이 끊긴거라 예측할 수 있었습니다. 하지만 지식 부족과 경험 부족으로
강사님께 도움을 받아 문제를 해결했습니다. 전체적인 통신 장애 원인 분석과 해결과정을 정리해보았습니다.


## 문제 발생 원인 (원인 분석)
- show int e0/1 switchport 결과 Switchport disabled -> 해당 포트가 L3 라우티드 포트(no switchport)로 동작
- 이 상태에선 스위치가 프레임을 L2로 브릿지하지 않고 L3 경계를 만들기 때문에, 같은 VLAN이라도 스위치 기준으로 네트워크가 끊김.
- 호스트의 게이트웨이가 라우터(E0/0=192.168.122.150/24)인데, 스위치가 L3 경계가 되면 호스트 <-> 라우터 사이 L2 프레임이 지나가지 못해 ARP/Ping 모두 실패.
추가로 스위치에 ip routing(글로벌)이나 SVI(IP 가진 interface vlan x)가 활성화 되어 있으면 스위치가 게이트웨이 역할을 가로채는 상황까지 발생할 수 있음.

## 해결 전략 (두 가지 중 하나만 선택)

### 전략 A - 순수 L2 스위치로 되돌리기 (가장 단순, 권장)
- 스위치-라우터 링크를 L2 Access 또는 Trunk로 구성
- 라우터는 물리 인터페이스(Access) 또는 서브인터페이스(trunk, route-on-a-stick)로 ip 운용.
- 호스트의 Deafault GW = 라우터(192.168.122.150)

### 전략 B - L3 스위치가 게이트웨이로 운영 (설계 변경이 필요)
- 스위치가 각 VLAN의 SVI에 IP를 갖고 게이트웨이가 됨
- 스위치-라우터 링크는 L3 라우티드 링크로 구성하고, 정적라우팅/동적라우팅으로 연동
-호스트의 Default G/W = 스위치 SVI IP


## 작업 명세서 (전략 A:L2 스위치로 되돌리기)

### 변경 개요
- 목적: 스위치와 라우터 사이를 L2로 전환해 Host <-> Router 통신 복수
- 영향: 라우터 연결 포트 일시 다운/업(수초 이내). 관리 IP(SVI)를 건드리면 원격접속 영향 가능
- 위험 완화: 콘솔로 작업. 현재 설정 백업 후 진행. 필요 시 즉시 롤백

### 1) 사전 점검 (스위치/라우터)

```shell
!Switch
show run | inc ip routing
show ip interface brief
show interface e0/1 switchport
show vlan brief
show mac address-table
show cdp neighbors

! Router
show ip interface brief
sho interfaces e0/0
```

### 2) 백업
```shell
! Switch
show run
copy running-config startup-config

! Router
show run
copy running-config startup-config
```

### 3) 구성 변경 - 스위치(라우터에 연결된 포트: e0/1 가정)

3-1. 포트를 L2로 복구
```shell
conf t
  default interface e0/1    
  interface e0/1
    switchport          // L2 포트로 전환 (no switchport 제거)
    switchport mode access  // 단일 VLAN이면 access
    switchport access vlan 1 // 필요 vlan으로 지정
    no shutdown
exit
```

>> Router-on-a-stick(여러 VLAN)이라면
```shell
int e0/1
  switchport 
  switchport trunk encapsulation dot1q  
  switchport mode trunk
  no shutdown
exit
```

>> 스위치 라우팅 끄기
스위치가 라우팅 중이면 L3 경계가 될 수 있음 -> 관리 목적 외에는 끄기
```shell
conf t
  no ip routing
end
```

>> 관리용 SVI 확인
관리용으로만 쓰려면, 호스트의 GW로 쓰이지 않게 주의
```shell
show run | sec interface Vlan 1
```

>> 라우터 확인/정합 
```shell
conf t
 interface e0/0
 ip add 192.168.122.150 255.255.255.0
 no shutdown
 
 /* duplex 정합(양쪽 모두 동일하게) */
 ! duplex auto | duplex full
 ! speed auto  | speed 100
 exit
end

show ip interface brief
show interfaces e0/0
```

### 5) 정합(duplex/speed) 확인

```shell
show interfaces e0/1
! 출력에서 full-duplex, 100mb/s(또는 auto/auto) 등 확인
! 에러 증가 시 양쪽 동일 값으로 강제
conf t
  interface e0/1
  duplex full
  speed 100
exit 
end
```

```shell
! Router
conf t
  interface e0/0
  duplex full
  speed 100
 exit
end
```

### 6) 검증 절차
```shell

! 트래픽유도 
Router > ping 192.168.122.22 
Host > ping 192.168.122.150

! 스위치에서 MAC 학습 확인 (L2가 정상이어야 테이블에 올라옴)
SW1# # show mac address-table | inc et0/1
SW1# show interfaces trunk

! CDP 이웃
SW1# show cdp neighbors
```

### 7) 성공 기준
- Host <-> Router 상호 ping 성공
- 스위치 MAC 테이블에 Host/Router MAC이 각 포트로 학습
- Duplex/Speed mismatch 및 인터페이스 에러(CRC 등) 없음

<img width="1662" height="854" alt="Host-to-Router정상통신" src="https://github.com/user-attachments/assets/d73d64b6-d6f7-4242-bd50-eb5952eb6cbe" />

### 정리
- 문제 원인: 스위치 포트(e0/1)가 라우티드 포트(no switchport)로 설정되어 L2 프레임 전송이 차단됨.
- 이로 인래 호스트와 라우터간 ARP/Ping 실패 및 MAC 테이블에 MAC 학습 안됨.

- 주요 작업
  1. 스위치 포트 L2 설정: switchport, switchport mode access, VLAN 지정.
  2. 스위치 라우팅 비활성화: no ip routing
  3. 라우터 인터페이스 IP 및 duplex/speed 정합 확인

- 검증
  호스트-라우터 ping 성공, 스위치 MAC 테이블에 MAC 학습 확인, duplex/speed mismatch 및
  에러(CRC 등) 없음.

- 결과: 호스트와 라우터간 L2 통신 복구, 정상적인 트래픽 흐름 확인.
