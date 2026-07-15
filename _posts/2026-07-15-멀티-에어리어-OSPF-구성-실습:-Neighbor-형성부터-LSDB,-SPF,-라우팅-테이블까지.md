---
title: "멀티 에어리어 OSPF 구성 실습: Neighbor 형성부터 LSDB, SPF, 라우팅 테이블까지"
date: "2026-07-15T13:49:30.424Z"
categories:
  - "network"
  - "ospf"
  - "routing"
author: "현제 김_7254"
slug: "멀티_에어리어_ospf_구성_실습_neighbor_형성부터_lsdb_spf_라우팅_테이블까지"
---

# 멀티 에어리어 OSPF 구성 실습: Neighbor 형성부터 LSDB, SPF, 라우팅 테이블까지

> Cisco Packet Tracer에서 Area 0을 중심으로 Area 100, 200, 300, 400을 연결하고, 각 지역 네트워크가 OSPF를 통해 경로를 학습하는 과정을 구성한다.

---

## 전체 네트워크 토폴로지

![image](/assets/image_f10331d1-6f04-429a-8c90-2bc71ee61077.png)

멀티 에어리어 OSPF 전체 토폴로지

---

## 1. 실습 목표

이번 실습은 단순히 router ospf 1 명령을 입력하고 Ping 성공 여부만 확인하는 것이 목적이 아니다!

다음과 같은 OSPF 내부 동작을 단계적으로 확인한다.

1. OSPF 프로세스가 라우터 내부에서 어떤 역할을 수행하는지

1. network 명령이 실제로 어떤 인터페이스를 선택하는지

1. Hello 패킷을 통해 Neighbor를 발견하는 과정

1. Neighbor 상태가 Down에서 Full까지 변화하는 과정

1. DBD, LSR, LSU, LSAck를 이용한 LSDB 동기화 과정

1. Area 내부 경로와 Area 간 경로의 차이

1. ABR이 Type 3 LSA를 만들어 다른 Area로 경로를 전달하는 과정

1. SPF 알고리즘으로 최단 경로를 계산하는 과정

1. 계산된 결과가 라우팅 테이블에 O, O IA로 설치되는 과정

1. 실제 데이터 패킷이 라우팅 테이블을 참조해 전달되는 과정

---

# 2. 전체 OSPF Area 구조

이 토폴로지는 하나의 OSPF 도메인을 여러 Area로 나눈 멀티 에어리어 OSPF 구조다.

```
Area 100 ── R2 ─┐
                 │
Area 200 ── R3 ─┤
                 ├── Area 0 Backbone
                 │
Area 300 ── R6 ─┤
                 │
Area 400 ── R7 ─┘
```

OSPF 멀티 에어리어 환경에서는 일반 Area가 원칙적으로 Area 0을 중심으로 연결되어야 한다.

예를 들어 Area 200의 PC가 Area 100의 PC와 통신한다면 논리적으로 다음과 같은 경로를 거친다.

```
Area 200
PC → R4 → R3
          │
          ▼
        Area 0
          │
          ▼
         R2
          │
          ▼
       Area 100
          │
        R1 → PC
```

실제 Area 0 내부에서 어느 라우터를 거치는지는 OSPF Cost 계산 결과에 따라 달라진다.

---

# 3. Area별 주소 대역

토폴로지에서는 지역별로 큰 주소 대역을 할당하고, 그 내부를 VLSM으로 나누어 LAN과 Serial 네트워크에 사용한다.

여기서 큰 주소 대역은 OSPF 설정을 간결하게 만들기 위해 사용한다.

예를 들어 Area 200에 다음 네트워크들이 있다고 가정한다.

```
81.0.0.0/20
81.0.16.0/20
81.0.32.0/20
81.0.48.0/30
```

이를 다음과 같이 한 줄로 OSPF에 포함할 수 있다.

```
network 81.0.0.0 0.255.255.255 area 200
```

하지만 이 명령이 위 네트워크들을 81.0.0.0/8 하나로 요약하는 것은 아니다.

OSPF는 실제 인터페이스에 설정된 Prefix를 그대로 광고한다.

```
81.0.0.0/20
81.0.16.0/20
81.0.32.0/20
81.0.48.0/30
```

---

# 4. OSPF의 network 명령이 의미하는 것

OSPF의 network 명령은 광고할 네트워크 주소를 직접 등록하는 명령처럼 보이지만, 실제 역할은 조금 다르다.

```
network 81.0.0.0 0.255.255.255 area 200
```

이 명령의 실제 의미는 다음과 같다.

> 이 라우터의 인터페이스 중 IP 주소가 81.0.0.0/8 범위에 포함되는 인터페이스를 찾아 OSPF를 활성화하고 Area 200에 소속시켜라.

Cisco IOS는 각 인터페이스의 IP 주소를 검사한다.

```
81.0.0.1      → 일치
81.0.16.1     → 일치
81.0.48.1     → 일치
198.133.100.1 → 불일치
```

따라서 network 명령은 다음 두 가지 작업을 수행한다.

1. 해당 인터페이스에서 OSPF Hello 패킷을 송수신하게 한다.

1. 해당 인터페이스의 Connected Network를 OSPF LSDB에 반영한다.

OSPF Area는 라우터 전체가 아니라 인터페이스 단위로 결정된다.

예를 들어 R3는 하나의 라우터이지만 인터페이스에 따라 서로 다른 Area에 소속된다.

```
R3
├── 81.x.x.x 인터페이스          → Area 200
└── 198.133.100.x 인터페이스     → Area 0
```

이 때문에 R3는 Area 200과 Area 0을 연결하는 ABR이 된다.

---

# 5. 와일드카드 마스크 이해하기

OSPF network 명령에서는 일반 서브넷 마스크가 아니라 와일드카드 마스크를 사용한다.

와일드카드 마스크는 서브넷 마스크를 반전한 값이다.

```
서브넷 마스크       255.255.0.0
와일드카드 마스크     0.0.255.255
```

와일드카드 마스크에서 각 비트의 의미는 다음과 같다.

```
0 → 반드시 일치해야 함
1 → 일치하지 않아도 됨
```

따라서 다음 명령은 첫 번째와 두 번째 Octet이 132.100으로 일치하는 모든 인터페이스를 선택한다.

```
network 132.100.0.0 0.0.255.255 area 100
```

---

# 6. 라우터별 역할

## Internal Router

모든 OSPF 인터페이스가 하나의 Area에만 소속된 라우터다.

R5는 여러 백본 라우터와 연결되어 있지만 모든 OSPF 인터페이스가 Area 0에 속한다.

따라서 R5는 ABR이 아니라 Area 0 Internal Router 또는 Backbone Router다.

## ABR

ABR은 Area Border Router의 약자다.

두 개 이상의 Area에 인터페이스를 가지고 있으며, 일반적으로 그중 하나가 Area 0인 라우터다.

ABR은 Area별로 LSDB를 별도로 유지한다.

예를 들어 R3는 다음과 같은 구조를 가진다.

```
R3
├── Area 200 LSDB
└── Area 0 LSDB
```

R3는 Area 200에서 학습한 경로를 Area 0으로 전달할 때 Type 3 Summary LSA를 생성한다.

반대로 Area 0에서 학습한 다른 지역의 경로도 Type 3 LSA를 이용해 Area 200으로 전달한다.

---

# 7. OSPF 구성 전 확인 사항

OSPF를 설정하기 전에 IP 주소와 인터페이스 상태가 먼저 정상이어야 한다.

```
show ip interface brief
```

정상적인 인터페이스는 다음처럼 표시된다.

```
Interface              IP-Address      Status     Protocol
Serial0/0              81.0.48.1      up         up
```

Status와 Protocol의 의미는 다르다.

```
Status up
→ 물리 계층이 정상

Protocol up
→ 데이터링크 계층이 정상
```

Serial 링크의 DCE 측에는 Clock Rate가 필요할 수 있다.

```
configure terminal
!
interface Serial0/0
 clock rate 64000
 no shutdown
!
end
```

OSPF를 설정하기 전에 직접 연결된 상대 라우터의 Serial IP로 Ping이 되어야 한다.

```
ping <상대 라우터 Serial IP>
```

직접 연결된 상대 라우터로 Ping이 되지 않는다면 다음 항목을 먼저 확인한다.

- 양쪽 인터페이스의 IP 주소

- 서브넷 마스크

- no shutdown

- DCE 측의 clock rate

- Serial 케이블 연결

- 양쪽 IP가 동일한 서브넷에 포함되는지

OSPF는 정상적인 IP 연결 위에서 동작하는 프로토콜이다. 기본적인 L1, L2, L3 연결이 되지 않는 상태에서 OSPF만 설정한다고 문제가 해결되지는 않는다.

---

# 8. 라우터별 OSPF 설정

모든 라우터에서 OSPF Process ID는 1로 통일한다.

```
router ospf 1
```

Process ID는 라우터 내부에서 OSPF 인스턴스를 구분하는 로컬 값이다.

OSPF 패킷에 포함되지 않기 때문에 이웃 라우터끼리 Process ID가 반드시 같을 필요는 없다.

예를 들어 다음 구성도 Neighbor 형성이 가능하다.

```
R1 → router ospf 1
R2 → router ospf 100
```

다만 관리 편의를 위해 이번 실습에서는 모두 1로 통일한다.

---

## 8.1 R1 설정 — Area 100 Internal Router

R1의 모든 인터페이스 주소가 132.100.0.0/16 범위에 포함되어 있다.

```
enable
configure terminal
!
router ospf 1
 router-id 1.1.1.1
 network 132.100.0.0 0.0.255.255 area 100
!
end
copy running-config startup-config
```

예를 들어 R1 인터페이스가 다음과 같이 설정되어 있어도 한 줄로 모두 OSPF에 포함된다.

```
FastEthernet0/0  132.100.5.254/23
FastEthernet0/1  132.100.6.30/27
Serial0/0        132.100.6.33/30
```

---

## 8.2 R2 설정 — Area 100과 Area 0의 ABR

R2는 Area 100과 Area 0에 동시에 연결된다.

```
enable
configure terminal
!
router ospf 1
 router-id 2.2.2.2
 network 132.100.0.0 0.0.255.255 area 100
 network 198.133.100.0 0.0.0.255 area 0
!
end
copy running-config startup-config
```

R2의 역할은 다음과 같다.

```
Area 100 경로
      ↓
     R2
      ↓
Area 0으로 Type 3 LSA 전달
```

반대로 Area 0에서 학습한 다른 Area의 경로도 Area 100으로 전달한다.

---

## 8.3 R3 설정 — Area 200과 Area 0의 ABR

```
enable
configure terminal
!
router ospf 1
 router-id 3.3.3.3
 network 81.0.0.0 0.255.255.255 area 200
 network 198.133.100.0 0.0.0.255 area 0
!
end
copy running-config startup-config
```

R3는 Area 200과 Area 0 사이의 경로 전달을 담당한다.

---

## 8.4 R4 설정 — Area 200 Internal Router

```
enable
configure terminal
!
router ospf 1
 router-id 4.4.4.4
 network 81.0.0.0 0.255.255.255 area 200
!
end
copy running-config startup-config
```

R4의 인터페이스가 다음처럼 서로 다른 Prefix를 사용해도 모두 81.0.0.0/8 범위에 포함된다.

```
81.0.0.0/20
81.0.16.0/20
81.0.48.0/30
```

---

## 8.5 R5 설정 — Area 0 Backbone Router

```
enable
configure terminal
!
router ospf 1
 router-id 5.5.5.5
 network 198.133.100.0 0.0.0.255 area 0
!
end
copy running-config startup-config
```

R5의 모든 OSPF 인터페이스는 Area 0에 속한다.

---

## 8.6 R6 설정 — Area 300과 Area 0의 ABR

```
enable
configure terminal
!
router ospf 1
 router-id 6.6.6.6
 network 160.100.0.0 0.0.255.255 area 300
 network 198.133.100.0 0.0.0.255 area 0
!
end
copy running-config startup-config
```

---

## 8.7 R7 설정 — Area 400과 Area 0의 ABR

```
enable
configure terminal
!
router ospf 1
 router-id 7.7.7.7
 network 142.100.0.0 0.0.255.255 area 400
 network 198.133.100.0 0.0.0.255 area 0
!
end
copy running-config startup-config
```

---

## 8.8 R8 설정 — Area 300 Internal Router

```
enable
configure terminal
!
router ospf 1
 router-id 8.8.8.8
 network 160.100.0.0 0.0.255.255 area 300
!
end
copy running-config startup-config
```

---

## 8.9 R9 설정 — Area 400 Internal Router

```
enable
configure terminal
!
router ospf 1
 router-id 9.9.9.9
 network 142.100.0.0 0.0.255.255 area 400
!
end
copy running-config startup-config
```

---

# 9. Router ID의 역할

Router ID는 OSPF 도메인에서 각 라우터를 구분하는 32비트 식별자다.

```
router-id 4.4.4.4
```

IPv4 주소 형식을 사용하지만 반드시 실제 인터페이스에 할당된 IP일 필요는 없다.

Router ID는 다음 용도로 사용된다.

- Neighbor 식별

- LSA 생성자 식별

- LSDB 내부의 라우터 구분

- SPF 그래프의 노드 식별

- Ethernet 환경의 DR/BDR 선출

- OSPF 관리 및 트러블슈팅

Router ID를 직접 설정하지 않으면 일반적으로 다음 순서로 선택된다.

```
1. 가장 높은 Loopback 인터페이스 IP
2. Loopback이 없으면 활성 인터페이스 중 가장 높은 IP
```

OSPF가 이미 실행된 후 Router ID를 변경했다면 프로세스를 다시 시작해야 반영될 수 있다.

```
clear ip ospf process
```

이 명령을 실행하면 기존 Neighbor 관계가 일시적으로 끊긴 후 다시 형성된다.

---

# 10. OSPF 설정 직후 내부에서 일어나는 일

다음 명령을 입력했다고 가정한다.

```
router ospf 1
 network 81.0.0.0 0.255.255.255 area 200
```

이 명령을 입력했다고 즉시 다른 라우터의 경로가 라우팅 테이블에 나타나는 것은 아니다.

내부에서는 다음 과정이 순서대로 진행된다.

1. network 명령 입력 

1. 일치하는 로컬 인터페이스 검색

1. 인터페이스에서 OSPF 활성화

1. Hello 패킷 송신

1. Neighbor 발견

1. Adjeancy 형성

1. LSDB 정보 교환

1. LSDB 동기화

1. SPF 알고리즘 실행

1. 최적 경로 계산

1. 라우팅 테이블에 경로 설치

OSPF는 이 전체 과정을 수행하는 라우터 내부의 제어 프로세스다.

---

# 11. Hello 패킷을 이용한 Neighbor 탐색

OSPF가 활성화된 인터페이스에서는 주기적으로 Hello 패킷을 전송한다.

OSPF는 TCP나 UDP를 사용하지 않는다.

IPv4 헤더의 Protocol Number 89를 직접 사용한다.

일반적인 OSPF 멀티캐스트 주소는 다음과 같다.

```
224.0.0.5 → AllSPFRouters
224.0.0.6 → AllDRouters
```

Hello 패킷에는 다음 정보가 포함된다.

- Router ID

- Area ID

- Hello Interval

- Dead Interval

- Network Mask

- OSPF Network Type

- 인증 정보

- DR과 BDR 정보

- 현재 알고 있는 Neighbor 목록

두 라우터가 Neighbor가 되기 위해서는 대표적으로 다음 조건이 일치해야 한다.

```
동일한 IP 서브넷
동일한 Area ID
동일한 Hello Interval
동일한 Dead Interval
호환되는 Network Type
동일한 인증 조건
서로 다른 Router ID
```

예를 들어 R4의 Serial0/0이 Area 200인데, R3의 반대편 Serial 인터페이스가 Area 0이라면 인접 관계가 정상적으로 형성되지 않는다.

---

# 12. OSPF Neighbor 상태 변화

OSPF Neighbor는 처음부터 FULL 상태가 되지 않는다.

```
Down
  ↓
Init
  ↓
2-Way
  ↓
ExStart
  ↓
Exchange
  ↓
Loading
  ↓
Full
```

## Down

아직 상대 라우터의 Hello 패킷을 수신하지 못한 상태다.

## Init

상대 라우터의 Hello 패킷은 수신했지만, 그 Hello 안의 Neighbor 목록에 자신의 Router ID가 없는 상태다.

```
R4가 R3의 Hello 수신
하지만 R3의 Hello 안에 R4의 Router ID가 없음
```

## 2-Way

양쪽 라우터가 서로의 Hello 패킷에서 자신의 Router ID를 확인한 상태다.

```
R3가 R4를 인식
R4도 R3를 인식
```

양방향 통신이 확인된 상태다.

## ExStart

LSDB를 교환하기 전에 Master와 Slave를 결정하고 DBD Sequence Number를 협상한다.

## Exchange

Database Description 패킷을 이용해 서로가 가진 LSA의 요약 목록을 교환한다.

DBD 패킷에는 전체 LSA 내용이 아니라 LSA Header 중심의 요약 정보가 들어간다.

## Loading

상대 라우터가 가지고 있지만 자신에게 없는 LSA를 발견하면 LSR 패킷으로 해당 LSA를 요청한다.

## Full

필요한 LSA 교환이 끝나 양쪽 LSDB가 동기화된 상태다.

```
show ip ospf neighbor
```

Serial Point-to-Point 링크에서는 다음처럼 보일 수 있다.

```
Neighbor ID     Pri   State      Dead Time   Address      Interface
3.3.3.3           0   FULL/-     00:00:35    81.0.48.2   Serial0/0
```

FULL/-의 의미는 다음과 같다.

```
FULL
→ LSDB 동기화 완료

-
→ Point-to-Point 링크이므로 DR/BDR 역할이 없음
```

---

# 13. OSPF 패킷 종류

OSPF는 LSDB를 동기화하기 위해 다섯 가지 주요 패킷을 사용한다.

동작 흐름은 다음과 같다.

```
R3                           R4
│                             │
│──── Hello ─────────────────>│
│<─── Hello ──────────────────│
│                             │
│──── DBD ───────────────────>│
│<─── DBD ────────────────────│
│                             │
│<─── LSR ────────────────────│
│──── LSU ───────────────────>│
│<─── LSAck ──────────────────│
│                             │
│         LSDB 동기화           │
```

LSU와 LSA는 같은 개념이 아니다.

```
LSU
→ 여러 LSA를 운반할 수 있는 OSPF 패킷

LSA
→ 링크 상태 정보를 담은 실제 데이터 구조
```

---

# 14. LSDB란 무엇인가

LSDB는 Link-State Database의 약자다.

OSPF 라우터가 자신이 속한 Area의 토폴로지 정보를 저장하는 데이터베이스다.

LSDB에는 단순 목적지와 Next Hop만 저장되는 것이 아니다.

다음과 같은 정보가 저장된다.

- 어떤 라우터가 존재하는지

- 라우터들이 어떤 링크로 연결되어 있는지

- 각 링크의 OSPF Cost

- 어떤 Prefix가 어느 라우터에 연결되어 있는지

- 어떤 라우터가 ABR인지

- 외부 경로를 광고하는 라우터가 있는지

OSPF는 라우팅 테이블을 이웃 라우터에게 그대로 복사하지 않는다.

```
RIP
→ 목적지 네트워크와 거리 중심으로 경로 전달

OSPF
→ 링크 상태 정보를 전달하고 각 라우터가 직접 계산
```

동일한 Area의 라우터들은 원칙적으로 동일한 LSDB를 가지지만, 각자 자신을 루트로 SPF 계산을 수행하기 때문에 최종 라우팅 테이블은 서로 다를 수 있다.

---

# 15. 주요 LSA Type

이번 토폴로지에서 핵심적으로 확인할 LSA는 Type 1과 Type 3이다.

## Type 1 Router LSA

각 라우터가 자신이 속한 Area마다 생성한다.

Router LSA에는 다음 정보가 포함된다.

- 자신에게 연결된 OSPF 링크

- 인접 OSPF 라우터

- 링크 Cost

- 연결된 Stub Network

- ABR 여부

예를 들어 R4는 Area 200에서 자신의 연결 정보를 Type 1 LSA로 광고한다.

```
R4
├── 81.0.0.0/20
├── 81.0.16.0/20
└── R3 방향 Serial 링크
```

Type 1 LSA는 해당 Area 내부에서만 Flooding된다.

Area 200의 Type 1 LSA가 Area 100까지 그대로 전달되지는 않는다.

## Type 2 Network LSA

Broadcast 또는 Multi-Access 네트워크에서 DR이 생성한다.

하나의 Ethernet 네트워크에 여러 OSPF 라우터가 연결된 경우 해당 세그먼트에 어떤 라우터들이 연결되어 있는지를 표현한다.

이번 토폴로지의 라우터 간 핵심 연결은 대부분 Serial Point-to-Point이므로 Type 1과 Type 3의 흐름이 더 중요하다.

## Type 3 Summary LSA

ABR이 한 Area의 Prefix를 다른 Area로 전달할 때 생성한다.

예를 들어 Area 200의 81.0.32.0/20 경로를 R3가 Area 0으로 전달하면 Type 3 LSA가 사용된다.

```
Area 200의 81.0.32.0/20
          ↓
         R3
          ↓
Area 0에 Type 3 LSA 생성
```

Summary LSA라는 이름 때문에 여러 Prefix를 자동으로 하나로 요약한다고 오해하기 쉽다.

하지만 별도의 수동 요약을 설정하지 않았다면 각 Prefix가 Type 3 LSA 형태로 전달될 수 있다.

---

# 16. ABR을 통한 Area 간 경로 전달

Area 200의 81.0.32.0/20 경로가 Area 100까지 전달되는 과정을 살펴보자.

## 1단계: Area 200 내부 광고

Area 200 내부 라우터가 81.0.32.0/20에 대한 링크 상태 정보를 광고한다.

```
Area 200 Router LSA
        ↓
R3가 Area 200 LSDB에 저장
```

## 2단계: R3가 Area 0으로 전달

R3는 Area 200과 Area 0을 연결하는 ABR이다.

R3는 Area 200에서 확인한 Prefix 정보를 바탕으로 Area 0에 Type 3 LSA를 생성한다.

```
R3
Area 200 LSDB 확인
        ↓
Area 0용 Type 3 LSA 생성
```

## 3단계: Area 0 라우터가 학습

R5와 다른 Area 0 라우터들이 R3가 생성한 Type 3 LSA를 자신의 Area 0 LSDB에 저장한다.

## 4단계: R2가 Area 100으로 전달

R2는 Area 100과 Area 0을 연결하는 ABR이다.

R2는 Area 0에서 학습한 81.0.32.0/20 경로를 Area 100에 Type 3 LSA로 전달한다.

```
Area 200
   ↓
R3 ABR
   ↓
Area 0
   ↓
R2 ABR
   ↓
Area 100
```

Area 100의 R1은 이 경로를 O IA 경로로 설치한다.

```
O IA 81.0.32.0/20 ...
```

---

# 17. Area별로 LSDB를 분리하는 이유

모든 라우터가 전체 OSPF 도메인의 세부 링크 정보를 전부 유지한다면 네트워크가 커질수록 다음 문제가 발생한다.

- LSDB 크기 증가

- LSA Flooding 증가

- SPF 계산량 증가

- CPU와 메모리 사용량 증가

- 하나의 링크 장애가 전체 네트워크에 큰 영향을 줌

Area를 나누면 Type 1과 Type 2 LSA의 Flooding 범위를 해당 Area 내부로 제한할 수 있다.

예를 들어 Area 200의 내부 링크가 Down되면 Area 200에서는 Type 1 LSA가 변경되고 SPF 재계산이 발생한다.

다른 Area에는 Area 200의 세부 링크 구조가 그대로 전달되지 않는다.

ABR이 계산한 Prefix 도달 가능성 변화가 Type 3 LSA 형태로 전달된다.

멀티 에어리어 OSPF의 장점은 다음과 같다.

- Area 내부 토폴로지 변화 격리

- LSDB 크기 감소

- SPF 계산 범위 감소

- 장애 영향 범위 축소

- ABR에서 경로 요약 가능

- 대규모 네트워크의 관리성 향상

---

# 18. SPF 계산 과정

LSDB 동기화가 완료되면 각 라우터는 자신을 루트로 Dijkstra SPF 알고리즘을 실행한다.

```
LSDB
  ↓
Dijkstra SPF 계산
  ↓
Shortest Path Tree 생성
  ↓
목적지 Prefix별 최적 경로 선택
  ↓
OSPF 경로 후보 생성
  ↓
RIB에 설치
```

모든 라우터가 같은 Area에서 동일한 LSDB를 가지고 있어도 SPF 결과는 라우터마다 다르다.

각 라우터가 자기 자신을 트리의 루트로 사용하기 때문이다.

```
R4가 계산한 최단 경로
≠
R5가 계산한 최단 경로
```

OSPF는 실제 데이터 패킷이 들어올 때마다 SPF 계산을 수행하지 않는다.

네트워크 상태가 변경되었을 때 LSDB를 갱신하고 SPF를 다시 계산한 뒤, 결과를 라우팅 테이블에 반영한다.

이후 데이터 패킷은 이미 계산된 라우팅 정보에 따라 전달된다.

---

# 19. OSPF Cost 계산

OSPF는 단순히 거치는 라우터 수가 적은 경로를 선택하지 않는다.

각 인터페이스의 Cost를 더해 누적 Cost가 가장 낮은 경로를 선택한다.

Cisco의 기본적인 Cost 계산 방식은 다음과 같다.

```
OSPF Cost = Reference Bandwidth / Interface Bandwidth
```

기본 Reference Bandwidth는 일반적으로 100Mbps다.

## FastEthernet Cost

```
100Mbps / 100Mbps = 1
```

## T1 Serial Cost

Serial 인터페이스의 기본 Bandwidth가 약 1.544Mbps라면 다음과 같다.

```
100Mbps / 1.544Mbps ≈ 64
```

Serial 링크 하나와 FastEthernet 링크 하나를 통과하는 경로는 다음과 같은 Cost를 가질 수 있다.

```
Serial Cost         64
FastEthernet Cost    1
-----------------------
총 Cost             65
```

라우팅 테이블에는 다음처럼 표시된다.

```
[110/65]
```

단, OSPF가 실제 링크 속도를 측정하는 것은 아니다.

인터페이스에 설정된 논리적인 Bandwidth 값을 기준으로 계산한다.

```
show interfaces Serial0/0
```

OSPF 인터페이스 Cost는 다음 명령으로도 확인할 수 있다.

```
show ip ospf interface Serial0/0
```

필요하다면 Cost를 직접 지정할 수도 있다.

```
configure terminal
!
interface Serial0/0
 ip ospf cost 10
!
end
```

---

# 20. R4 라우팅 테이블 분석

R4에서 확인한 라우팅 테이블은 다음과 같다.

```
Gateway of last resort is not set

     81.0.0.0/8 is variably subnetted, 4 subnets, 2 masks
C       81.0.0.0/20 is directly connected, FastEthernet0/1
C       81.0.16.0/20 is directly connected, FastEthernet0/0
O       81.0.32.0/20 [110/65] via 81.0.48.2, 00:01:56, Serial0/0
C       81.0.48.0/30 is directly connected, Serial0/0

     198.133.100.0/30 is subnetted, 1 subnets
O IA    198.133.100.4 [110/128] via 81.0.48.2, 00:01:56, Serial0/0
```

---

## Gateway of last resort is not set

```
Gateway of last resort is not set
```

R4에 기본 경로가 없다는 의미다.

기본 경로는 다음처럼 목적지에 대한 더 구체적인 경로가 없을 때 사용하는 경로다.

```
0.0.0.0/0
```

현재는 OSPF가 개별 목적지 Prefix를 학습하고 있으므로 내부망 통신에는 반드시 기본 경로가 필요한 것은 아니다.

---

## Variably subnetted

```
81.0.0.0/8 is variably subnetted, 4 subnets, 2 masks
```

81.0.0.0/8 범위 아래에 총 네 개의 서브넷 경로가 있고, 두 종류의 서브넷 마스크를 사용한다는 뜻이다.

```
/20 사용
81.0.0.0/20
81.0.16.0/20
81.0.32.0/20

/30 사용
81.0.48.0/30
```

즉, VLSM이 적용되어 있다.

---

## Connected Route

```
C 81.0.0.0/20 is directly connected, FastEthernet0/1
```

C는 Connected Route를 의미한다.

R4의 FastEthernet0/1이 81.0.0.0/20 네트워크에 직접 연결되어 있다.

이 경로는 OSPF가 만든 것이 아니다.

인터페이스가 IP 주소를 가지고 up/up 상태가 되면 IOS가 자동으로 라우팅 테이블에 설치한다.

```
C 81.0.16.0/20 is directly connected, FastEthernet0/0
```

이 경로 역시 R4에 직접 연결된 LAN이다.

```
C 81.0.48.0/30 is directly connected, Serial0/0
```

이 네트워크는 R4와 R3를 연결하는 Serial 구간이다.

주소는 다음과 같이 구성될 수 있다.

```
81.0.48.0 → 네트워크 주소
81.0.48.1 → R4 Serial 주소
81.0.48.2 → R3 Serial 주소
81.0.48.3 → 브로드캐스트 주소
```

---

## Intra-Area OSPF Route

```
O 81.0.32.0/20 [110/65]
  via 81.0.48.2, 00:01:56, Serial0/0
```

각 항목을 분해하면 다음과 같다.

```
O
→ 같은 OSPF Area에서 학습한 Intra-Area 경로
```

```
81.0.32.0/20
→ 목적지 네트워크
```

```
[110/65]
→ [Administrative Distance / OSPF Cost]
```

```
via 81.0.48.2
→ 다음으로 패킷을 전달할 Next Hop
```

```
00:01:56
→ 해당 경로가 라우팅 테이블에 설치된 후 경과 시간
```

```
Serial0/0
→ 패킷이 나갈 출구 인터페이스
```

R4가 81.0.32.0/20 목적지로 패킷을 전달하는 과정은 다음과 같다.

```
목적지 IP 확인
      ↓
81.0.32.0/20 경로 검색
      ↓
Next Hop 81.0.48.2 선택
      ↓
Serial0/0으로 전송
      ↓
R3가 다음 포워딩 수행
```

O로 표시되는 이유는 목적지 81.0.32.0/20이 R4와 동일한 Area 200에 있기 때문이다.

---

## Administrative Distance와 Metric

```
[110/65]
```

첫 번째 값 110은 Administrative Distance다.

서로 다른 출처에서 동일한 목적지 Prefix를 학습했을 때 어떤 경로 출처를 더 신뢰할지 결정하는 값이다.

값이 작을수록 우선한다.

두 번째 값 65는 OSPF Cost다.

```
프로토콜 간 경로 출처 비교
→ Administrative Distance 사용

동일한 OSPF 경로끼리 비교
→ OSPF Cost 사용
```

---

## Inter-Area OSPF Route

```
O IA 198.133.100.4 [110/128]
     via 81.0.48.2, 00:01:56, Serial0/0
```

출력 상단에 다음 내용이 있다.

```
198.133.100.0/30 is subnetted, 1 subnets
```

따라서 실제 Prefix는 다음과 같다.

```
198.133.100.4/30
```

O IA는 OSPF Inter-Area Route를 의미한다.

```
O  → OSPF
IA → Inter Area
```

R4는 Area 200에 있고, 198.133.100.4/30은 Area 0에 있다.

따라서 R4는 이 경로를 ABR인 R3를 통해 학습한다.

```
R4
 │
 │ Area 200
 ▼
R3 ABR
 │
 │ Area 0
 ▼
198.133.100.4/30
```

같은 Area의 경로가 아니므로 O가 아니라 O IA로 표시된다.

---

# 21. O와 O IA의 차이

OSPF 라우팅 테이블 코드의 의미는 다음과 같다.

이번 토폴로지에서는 외부 라우팅 프로토콜 재분배가 없으므로 주로 다음 코드가 나타난다.

```
C
O
O IA
```

OSPF 내부 경로 선택에서는 일반적으로 다음 순서가 우선된다.

```
Intra-Area
    ↓
Inter-Area
    ↓
External Type 1
    ↓
External Type 2
```

동일한 경로 유형끼리는 누적 Cost가 더 낮은 경로를 선택한다.

---

# 22. 다른 지역 경로가 아직 보이지 않는 이유

R4의 현재 라우팅 테이블에는 다음 경로만 보인다.

```
O    81.0.32.0/20
O IA 198.133.100.4/30
```

아직 다음 지역의 LAN 경로는 보이지 않는다.

```
Area 100 → 132.100.x.x
Area 300 → 160.100.x.x
Area 400 → 142.100.x.x
```

이는 R4와 R3 사이의 Area 200 OSPF는 동작하지만, 다음 중 하나가 아직 완료되지 않았을 가능성이 있다.

- Area 0의 모든 라우터에 OSPF 설정이 완료되지 않음

- Area 0 Neighbor가 아직 FULL이 아님

- 다른 ABR의 일반 Area 설정이 누락됨

- 일부 Serial 인터페이스가 다른 Area로 잘못 지정됨

- 네트워크가 아직 수렴 중임

- 상대 라우터 인터페이스가 up/up이 아님

전체 구성이 완료되면 R4에서 다른 Area의 실제 Prefix들이 O IA로 나타나야 한다.

예상 형태는 다음과 같다.

```
O IA 132.100.4.0/23 ...
O IA 132.100.6.0/27 ...
O IA 132.100.6.32/30 ...

O IA 160.100.x.x/xx ...
O IA 142.100.x.x/xx ...
```

수동 요약을 설정하지 않았다면 반드시 /16이나 /8 하나로 보이는 것은 아니다.

OSPF는 실제 Prefix Length를 전달하는 Classless 라우팅 프로토콜이다.

---

# 23. ping 132.100.0.0이 실패한 이유

다음 Ping 테스트는 실패했다.

```
Sending 5, 100-byte ICMP Echos to 132.100.0.0
.....
Success rate is 0 percent
```

132.100.0.0은 Area 100에 할당한 큰 주소 범위를 나타내는 Network ID다.

일반적인 Ping 테스트는 실제 인터페이스나 호스트에 할당된 IP 주소를 대상으로 해야 한다.

예를 들어 R1의 FastEthernet0/0 주소가 132.100.5.254라면 다음과 같이 테스트한다.

```
ping 132.100.5.254
```

또는 Area 100 PC에 실제로 설정한 IP 주소를 사용한다.

```
ping <Area 100 PC 주소>
```

통신 테스트에 적절한 대상은 다음과 같다.

- 상대 라우터 인터페이스 IP

- 목적지 PC IP

- 목적지 서버 IP

- 실제로 설정된 Loopback IP

큰 주소 대역을 나타내는 Network ID 자체는 일반적인 호스트 통신 대상으로 적절하지 않다.

---

# 24. Passive Interface 적용

대역 단위로 network 명령을 설정하면 해당 범위의 LAN과 Serial 인터페이스가 모두 OSPF에 포함된다.

예를 들어 R4에서는 다음 인터페이스들이 모두 OSPF에 참여할 수 있다.

```
FastEthernet0/0
FastEthernet0/1
Serial0/0
```

하지만 FastEthernet에 PC와 스위치만 연결되어 있다면 해당 LAN으로 OSPF Hello를 보낼 필요가 없다.

이때 passive-interface를 사용할 수 있다.

```
router ospf 1
 passive-interface FastEthernet0/0
 passive-interface FastEthernet0/1
```

Passive Interface의 동작은 다음과 같다.

```
Hello 패킷 송신 중지
Neighbor 형성 중지
연결된 네트워크의 OSPF 광고는 유지
```

즉, Passive Interface로 설정해도 LAN Prefix가 OSPF에서 제거되는 것은 아니다.

## R1 권장 설정

```
configure terminal
!
router ospf 1
 passive-interface FastEthernet0/0
 passive-interface FastEthernet0/1
!
end
```

## R4 권장 설정

```
configure terminal
!
router ospf 1
 passive-interface FastEthernet0/0
 passive-interface FastEthernet0/1
!
end
```

## R8과 R9 권장 설정

PC와 스위치만 연결된 FastEthernet 인터페이스를 Passive Interface로 설정한다.

```
router ospf 1
 passive-interface FastEthernet0/0
 passive-interface FastEthernet0/1
```

라우터끼리 연결된 Serial 인터페이스는 Passive Interface로 설정하면 안 된다.

Serial 인터페이스가 Passive가 되면 Hello 패킷이 중단되어 Neighbor 관계를 형성할 수 없다.

---

# 25. OSPF 설정 검증 순서

OSPF 문제를 확인할 때는 라우팅 테이블부터 무작정 확인하기보다 계층적으로 접근하는 것이 좋다.

```
인터페이스 상태
      ↓
직접 연결 통신
      ↓
OSPF 인터페이스 활성화
      ↓
Neighbor 상태
      ↓
LSDB
      ↓
라우팅 테이블
      ↓
End-to-End 통신
```

---

## 25.1 인터페이스 상태 확인

```
show ip interface brief
```

모든 라우터 간 연결 인터페이스가 다음 상태여야 한다.

```
Status   up
Protocol up
```

---

## 25.2 직접 연결된 상대 라우터 확인

```
ping <상대 Serial 인터페이스 IP>
```

이 Ping이 실패하면 OSPF를 확인하기 전에 IP 주소, 서브넷 마스크, Clock Rate, 인터페이스 상태를 점검한다.

---

## 25.3 OSPF 프로세스 확인

```
show ip protocols
```

예상 출력은 다음과 같다.

```
Routing Protocol is "ospf 1"

Routing for Networks:
  81.0.0.0 0.255.255.255 area 200
```

이 명령으로 다음 내용을 확인할 수 있다.

- 어떤 OSPF Process ID가 동작하는지

- 어떤 Network 문이 설정되어 있는지

- Passive Interface가 무엇인지

- Router ID가 무엇인지

---

## 25.4 인터페이스별 Area 확인

```
show ip ospf interface
```

Packet Tracer IOS에서 지원한다면 다음 명령을 사용할 수 있다.

```
show ip ospf interface brief
```

R4에서는 다음과 같은 구성이 보여야 한다.

```
Serial0/0 → Area 200
```

R3에서는 인터페이스에 따라 Area가 구분되어야 한다.

```
81.x.x.x 인터페이스          → Area 200
198.133.100.x 인터페이스     → Area 0
```

---

## 25.5 Neighbor 확인

```
show ip ospf neighbor
```

정상적인 인접 관계의 핵심은 FULL이다.

```
FULL/-
FULL/DR
FULL/BDR
FULL/DROTHER
```

Serial Point-to-Point 환경에서는 일반적으로 FULL/-가 나타난다.

---

## 25.6 LSDB 확인

```
show ip ospf database
```

Router LSA만 확인하려면 다음 명령을 사용한다.

```
show ip ospf database router
```

다른 Area에서 전달된 Summary LSA를 확인하려면 다음 명령을 사용한다.

```
show ip ospf database summary
```

ABR인 R3에서는 Area 200과 Area 0에 대한 데이터베이스 항목이 모두 존재해야 한다.

---

## 25.7 OSPF 경로 확인

```
show ip route ospf
```

전체 라우팅 테이블은 다음 명령으로 확인한다.

```
show ip route
```

특정 목적지에 사용할 경로를 확인할 수도 있다.

```
show ip route 132.100.5.254
```

이 명령을 사용하면 해당 목적지에 어떤 Prefix가 Longest Prefix Match되는지 확인할 수 있다.

---

## 25.8 경로 추적

라우터에서는 다음 명령을 사용한다.

```
traceroute <목적지 IP>
```

Packet Tracer PC에서는 다음 명령을 사용한다.

```
tracert <목적지 IP>
```

Ping은 통신 성공 여부를 확인하는 데 적합하고, Traceroute는 패킷이 어느 라우터까지 도달했는지 확인하는 데 적합하다.

---

# 26. Area 200 PC에서 Area 100 PC까지의 패킷 전달

Area 200의 PC4가 Area 100의 PC1으로 패킷을 전송한다고 가정한다.

## 1단계: PC4의 목적지 네트워크 판단

PC4는 자신의 IP와 서브넷 마스크를 이용해 목적지가 같은 네트워크에 있는지 판단한다.

```
출발지 네트워크와 목적지 네트워크가 다름
                ↓
기본 게이트웨이로 전달
```

PC4는 목적지 PC의 MAC 주소를 찾는 것이 아니라 기본 게이트웨이인 R4의 MAC 주소를 ARP로 확인한다.

IP 패킷의 목적지 주소는 PC1 주소로 유지되지만 Ethernet Frame의 목적지 MAC 주소는 R4의 MAC 주소가 된다.

## 2단계: R4의 라우팅 테이블 조회

R4는 IP 패킷의 목적지 주소를 기준으로 Longest Prefix Match를 수행한다.

정상적으로 전체 OSPF가 구성되었다면 다음과 같은 경로가 존재한다.

```
O IA 132.100.x.x/xx
     via 81.0.48.2
```

R4는 패킷을 Serial0/0을 통해 R3로 전달한다.

## 3단계: R3의 포워딩

R3는 Area 200과 Area 0의 ABR이다.

R3는 자신의 라우팅 테이블에서 Area 100 목적지로 가는 가장 낮은 Cost의 경로를 검색한다.

패킷은 Area 0 방향으로 전달된다.

## 4단계: Area 0 내부 전달

Area 0 라우터들은 각자의 라우팅 테이블을 참조해 패킷을 R2 방향으로 전달한다.

실제 경로는 OSPF Cost에 따라 결정된다.

```
R3 → R5 → R2
```

또는 Cost와 토폴로지에 따라 다른 Area 0 경로가 선택될 수 있다.

## 5단계: R2에서 Area 100으로 전달

R2는 Area 0과 Area 100의 ABR이다.

R2는 목적지 Prefix가 Area 100에 있으므로 Area 100 방향 인터페이스로 패킷을 전달한다.

## 6단계: 목적지 LAN 도달

목적지 PC가 R1 뒤에 있다면 패킷은 R1으로 전달된다.

R1은 Connected Route를 이용해 최종 LAN으로 패킷을 전달한다.

## 7단계: 응답 패킷

ICMP Echo Reply 역시 독립적인 라우팅 과정을 거친다.

```
PC1
 ↓
R1
 ↓
R2
 ↓
Area 0
 ↓
R3
 ↓
R4
 ↓
PC4
```

요청 패킷이 목적지에 도착했다고 해서 응답 경로가 자동으로 보장되는 것은 아니다.

반대편 라우터들도 출발지 PC 네트워크에 대한 라우팅 정보를 가지고 있어야 한다.

---

# 27. 제어 평면과 데이터 평면

OSPF를 이해할 때 제어 평면과 데이터 평면을 구분해야 한다.

## 제어 평면

다음 동작은 경로를 만들기 위한 제어 평면에 해당한다.

```
Hello 패킷 교환
Neighbor 관리
DBD, LSR, LSU, LSAck 교환
LSDB 유지
SPF 계산
라우팅 테이블 갱신
```

## 데이터 평면

다음 동작은 실제 사용자 트래픽을 전달하는 데이터 평면에 해당한다.

```
ICMP 패킷 전달
TCP 패킷 전달
UDP 패킷 전달
목적지 IP 기반 라우팅 조회
출구 인터페이스로 패킷 전달
```

OSPF는 사용자의 ICMP나 TCP 패킷을 직접 운반하는 프로토콜이 아니다.

OSPF는 해당 패킷을 어디로 보낼지 결정하는 경로 정보를 만든다.

```
OSPF 제어 평면
→ 경로 계산

라우팅 테이블과 포워딩 테이블
→ 실제 패킷 전달
```

---

# 28. 대역 단위 OSPF 선언과 경로 요약의 차이

이번 실습에서는 다음과 같이 큰 주소 범위로 인터페이스를 선택했다.

```
network 132.100.0.0 0.0.255.255 area 100
```

이 명령은 경로 요약 명령이 아니다.

```
network 명령
→ 어떤 인터페이스에서 OSPF를 실행할지 결정
```

실제 Area 요약은 ABR에서 area range 명령으로 설정한다.

예를 들어 R2가 Area 100의 세부 Prefix를 132.100.0.0/16으로 요약해 Area 0으로 전달하려면 다음과 같이 설정할 수 있다.

```
configure terminal
!
router ospf 1
 area 100 range 132.100.0.0 255.255.0.0
!
end
```

두 명령의 차이는 다음과 같다.

```
network 132.100.0.0 0.0.255.255 area 100
→ 로컬 인터페이스를 Area 100에 참여시킴

area 100 range 132.100.0.0 255.255.0.0
→ ABR이 Area 100 경로를 다른 Area에 요약해서 전달
```

이번 실습에서는 각 VLSM Prefix가 실제로 어떻게 전달되는지 확인하기 위해 수동 요약은 적용하지 않는다.

---

# 29. 대역 단위 선언 시 주의점

대역 단위 선언은 설정이 간결하다는 장점이 있지만, 예상하지 않은 인터페이스까지 OSPF에 포함될 수 있다.

예를 들어 R1에 향후 다음 인터페이스를 추가했다고 가정한다.

```
Loopback0 132.100.200.1/32
```

기존 설정이 다음과 같다면 Loopback0도 자동으로 Area 100에 포함된다.

```
network 132.100.0.0 0.0.255.255 area 100
```

따라서 대역 단위 선언을 사용할 때는 다음을 함께 확인해야 한다.

```
show ip ospf interface
```

운영 환경에서는 인터페이스 단위 설정을 사용하기도 한다.

```
interface Serial0/0
 ip ospf 1 area 100
```

하지만 이번 실습에서는 주소 설계가 Area별로 명확하게 분리되어 있으므로 대역 단위 선언이 적합하다.

---

# 30. 자주 발생하는 문제와 원인

## Neighbor가 나타나지 않는 경우

```
show ip ospf neighbor
```

결과가 비어 있다면 다음을 확인한다.

- 양쪽 인터페이스가 up/up인가

- 상대 Serial IP로 Ping이 되는가

- 양쪽 Area ID가 같은가

- network 명령이 인터페이스 IP와 일치하는가

- Serial 인터페이스가 Passive로 설정되지 않았는가

- Router ID가 중복되지 않았는가

- Hello와 Dead Timer가 동일한가

---

## Neighbor가 INIT에서 멈추는 경우

상대 Hello는 수신하지만 자신의 Router ID가 상대 Hello에 포함되지 않는 상태다.

다음과 같은 단방향 통신 문제를 확인한다.

- ACL

- 한쪽 인터페이스의 OSPF 누락

- 멀티캐스트 전달 문제

- 잘못된 네트워크 타입

---

## Neighbor가 EXSTART 또는 EXCHANGE에서 멈추는 경우

대표적으로 MTU 불일치를 확인한다.

```
show interfaces Serial0/0
```

양쪽 인터페이스의 MTU가 다른지 확인한다.

Router ID 중복이나 DBD Sequence 협상 문제도 원인이 될 수 있다.

---

## Neighbor는 FULL인데 경로가 없는 경우

Neighbor FULL은 해당 이웃과 LSDB 동기화가 완료되었다는 의미다.

전체 OSPF 도메인의 모든 경로가 정상이라는 의미는 아니다.

다음 순서로 확인한다.

```
show ip ospf database
show ip ospf database summary
show ip route ospf
```

특히 ABR에서 다음을 확인한다.

- 일반 Area와 Area 0이 모두 존재하는가

- Area 0 Neighbor가 정상인가

- Type 3 LSA가 생성되고 있는가

- 다른 ABR의 경로가 Area 0에 존재하는가

---

## 특정 Area의 경로만 보이지 않는 경우

해당 Area의 ABR을 우선 확인한다.

예를 들어 Area 300 경로가 다른 지역에 보이지 않는다면 R6에서 다음을 실행한다.

```
show ip ospf interface
show ip ospf neighbor
show ip ospf database
show ip ospf database summary
show ip route ospf
```

R6에는 다음 두 Area가 모두 보여야 한다.

```
Area 300
Area 0
```

---

## 라우터끼리는 통신되지만 PC끼리 Ping이 안 되는 경우

이 경우 OSPF가 아니라 End Host 설정 문제일 가능성이 있다.

다음을 확인한다.

- PC IP 주소

- PC 서브넷 마스크

- PC Default Gateway

- 목적지 PC 설정

- 라우터 LAN 인터페이스 주소

- 스위치 포트 연결 상태

- 동일 LAN 내 주소 중복 여부

---

# 31. 최종 검증 체크리스트

```
[ ] 모든 라우터 인터페이스가 up/up 상태다.

[ ] 직접 연결된 상대 라우터의 Serial IP로 Ping이 된다.

[ ] 모든 라우터의 Router ID가 중복되지 않는다.

[ ] 일반 Area 인터페이스가 올바른 Area에 포함되어 있다.

[ ] Area 0 인터페이스가 모두 Area 0으로 설정되어 있다.

[ ] 라우터 간 Serial 인터페이스가 Passive로 설정되지 않았다.

[ ] 지역 Area의 OSPF Neighbor가 FULL 상태다.

[ ] Area 0의 OSPF Neighbor가 FULL 상태다.

[ ] ABR에서 두 Area의 LSDB가 확인된다.

[ ] 같은 Area의 원격 경로가 O로 나타난다.

[ ] 다른 Area의 경로가 O IA로 나타난다.

[ ] PC의 Default Gateway가 올바르다.

[ ] 네트워크 주소가 아닌 실제 Host IP로 Ping을 테스트했다.

[ ] Traceroute 결과가 예상 Area 경계를 따라 이동한다.

[ ] 왕복 경로가 모두 존재한다.
```

---

# 32. 핵심 정리

이번 토폴로지에서 OSPF가 동작하는 전체 흐름은 다음과 같다.

```
1. network 명령으로 OSPF를 실행할 인터페이스를 선택한다.

2. 선택된 인터페이스에 Area를 할당한다.

3. 인터페이스에서 Hello 패킷을 송신한다.

4. 상대 라우터와 Neighbor 관계를 형성한다.

5. Neighbor 상태가 Down, Init, 2-Way, ExStart,
   Exchange, Loading, Full 순서로 변화한다.

6. DBD, LSR, LSU, LSAck를 통해 LSDB를 동기화한다.

7. 각 라우터가 자신을 루트로 SPF 계산을 수행한다.

8. 동일한 Area의 경로는 O로 설치된다.

9. ABR이 다른 Area의 Prefix를 Type 3 LSA로 전달한다.

10. 다른 Area에서 학습한 경로는 O IA로 설치된다.

11. 실제 데이터 패킷은 LSDB를 직접 조회하지 않고
    최종 라우팅 테이블과 포워딩 정보를 이용해 전달된다.
```

가장 중요한 개념은 network 명령, Neighbor, LSDB, SPF, 라우팅 테이블을 서로 분리해서 이해하는 것이다.

```
network 명령
→ OSPF 인터페이스 선택

Hello
→ Neighbor 발견 및 유지

DBD, LSR, LSU, LSAck
→ LSDB 동기화

LSA
→ 네트워크 링크 상태 표현

SPF
→ 최단 경로 계산

라우팅 테이블
→ 계산 결과 저장

데이터 평면
→ 계산된 경로에 따라 실제 패킷 전달
```

OSPF는 단순히 다른 라우터가 알려준 라우팅 테이블을 복사하는 프로토콜이 아니다.

각 라우터가 링크 상태 정보를 수집해 네트워크 지도를 만들고, 그 지도를 기반으로 자신에게 가장 유리한 최단 경로를 직접 계산하는 Link-State Routing Protocol이다.