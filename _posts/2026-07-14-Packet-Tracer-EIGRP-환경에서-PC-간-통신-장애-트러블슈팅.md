---
title: "Packet Tracer EIGRP 환경에서 PC 간 통신 장애 트러블슈팅"
date: "2026-07-14T02:41:32.393Z"
categories:
  - "netwro"
  - "routing"
author: "현제 김_7254"
slug: "packet_tracer_eigrp_환경에서_pc_간_통신_장애_트러블슈팅"
---

!/assets/image_06f2a81f-6205-4896-8468-817ce051cb9d.png

# Packet Tracer EIGRP 환경에서 PC 간 통신 장애 트러블슈팅

## 들어가며

Cisco Packet Tracer에서 여러 라우터를 EIGRP로 연결한 뒤 PC 간 통신을 테스트했지만, 일부 PC 사이에서 Ping이 정상적으로 전달되지 않는 문제가 발생했다.

처음에는 PC의 IP 주소나 기본 게이트웨이 문제처럼 보였지만, 실제 원인은 다음 두 가지 EIGRP 설정 오류였다..

1. RTC 라우터의 EIGRP AS 번호가 다른 라우터와 달랐다.

1. RTA 라우터의 EIGRP 설정에서 RTC 연결 네트워크가 누락되어 있었다.

이번 글에서는 장애를 단순히 설정 몇 줄로 해결하는 데 그치지 않고, 다음 순서에 따라 문제를 좁혀 가는 과정을 정리한다.

```
PC 설정
→ 기본 게이트웨이
→ 라우터 인터페이스
→ 직결 라우터 통신
→ EIGRP 이웃 관계
→ 라우팅 테이블
→ 왕복 경로
→ 종단 간 통신
```

---

# 1. 실습 환경

## 1.1 네트워크 토폴로지

이번 실습 환경은 RTA를 중심으로 RTB, RTC, RTD, ISP 라우터가 연결된 구조다.

```
 PC1 192.168.135.1 ─┐
                     ├── RTB
 PC2 192.168.21.1  ──┘
                         │
                         │ 192.168.13.0/24
                         │
                        RTA
                       /   \
      192.168.12.0/24 /     \ 192.168.14.0/24
                     /       \
                   RTC       RTD
                  /   \     /   \
               PC3   PC5  PC6   PC7

RTA ── 192.168.15.0/24 ── ISP
```

RTA는 중앙 라우터 역할을 하며, 각 라우터가 보유한 LAN 네트워크를 EIGRP를 통해 학습해야 한다.

---

## 1.2 PC 주소 구성

각 PC의 기본 게이트웨이는 해당 PC가 연결된 라우터의 LAN 인터페이스 주소다.

예를 들어 PC1은 192.168.135.0/24 네트워크에 속하고, RTB의 192.168.135.72 인터페이스를 기본 게이트웨이로 사용한다.

---

## 1.3 라우터 간 연결망

---

# 2. 장애 증상

PC1에서 RTC 아래에 있는 PC3으로 Ping을 전송했다.

```
PC> ping 192.168.20.1
```

정상이라면 다음 경로로 패킷이 전달되어야 한다.

```
PC1
→ RTB
→ RTA
→ RTC
→ PC3
```

그러나 실제로는 응답을 받지 못했다.

```
Pinging 192.168.20.1 with 32 bytes of data:

Request timed out.
Request timed out.
Request timed out.
Request timed out.

Ping statistics for 192.168.20.1:
    Packets: Sent = 4, Received = 0, Lost = 4 (100% loss)
```

이 상태에서 바로 EIGRP 설정을 수정하기보다는, 먼저 어느 구간까지 정상적으로 통신되는지 확인해야 한다.

---

# 3. 네트워크 장애를 확인하는 기본 원칙

PC 간 Ping이 실패했다고 해서 반드시 라우팅 프로토콜이 원인은 아니다.

문제는 다음 계층 중 어디에서든 발생할 수 있다.

```
PC IP 주소 또는 서브넷 마스크
기본 게이트웨이
PC와 스위치 또는 라우터 사이의 링크
라우터 인터페이스 shutdown
라우터 간 IP 주소 불일치
Serial DCE clock rate 누락
EIGRP AS 번호 불일치
EIGRP network 명령 누락
라우팅 테이블 미학습
응답 경로 누락
```

따라서 장애 범위를 작은 구간부터 넓혀 가야 한다.

---

# 4. 1단계: 같은 라우터에 연결된 PC끼리 통신 확인

가장 먼저 EIGRP를 거치지 않는 통신을 확인한다.

테스트 대상은 다음과 같다.

```
PC1 ↔ PC2
PC3 ↔ PC5
PC6 ↔ PC7
```

예를 들어 PC1과 PC2는 모두 RTB에 연결되어 있다.

PC1에서 PC2로 Ping을 실행한다.

```
PC> ping 192.168.21.1
```

정상 결과 예시는 다음과 같다.

```
Pinging 192.168.21.1 with 32 bytes of data:

Reply from 192.168.21.1: bytes=32 time<1ms TTL=127
Reply from 192.168.21.1: bytes=32 time<1ms TTL=127
Reply from 192.168.21.1: bytes=32 time<1ms TTL=127
Reply from 192.168.21.1: bytes=32 time<1ms TTL=127

Ping statistics for 192.168.21.1:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)
```

이 통신은 RTB 내부에서만 처리된다.

```
PC1
→ RTB FastEthernet0/0
→ RTB 라우팅 테이블
→ RTB FastEthernet0/1
→ PC2
```

따라서 이 구간이 정상이라면 다음 항목은 일단 정상으로 판단할 수 있다.

- PC1과 PC2의 IP 설정

- 각 PC의 기본 게이트웨이

- PC와 RTB 사이 물리 연결

- RTB의 LAN 인터페이스

- RTB의 직접 연결 라우팅

반대로 같은 라우터에 연결된 PC끼리도 통신되지 않는다면 EIGRP보다 먼저 PC와 LAN 구간을 확인해야 한다.

---

# 5. 2단계: PC에서 기본 게이트웨이 확인

각 PC에서 자신의 기본 게이트웨이로 Ping을 실행한다.

## PC1

```
PC> ping 192.168.135.72
```

## PC2

```
PC> ping 192.168.21.95
```

## PC3

```
PC> ping 192.168.20.72
```

## PC5

```
PC> ping 192.168.120.24
```

## PC6

```
PC> ping 192.168.83.175
```

## PC7

```
PC> ping 192.168.59.73
```

PC의 주소 설정은 ipconfig로 확인한다.

```
PC> ipconfig
```

PC1의 정상 출력 예시는 다음과 같다.

```
FastEthernet0 Connection:

   Connection-specific DNS Suffix..:
   Link-local IPv6 Address.........: FE80::2D0:97FF:FE58:32B4
   IPv6 Address....................: ::
   IPv4 Address....................: 192.168.135.1
   Subnet Mask.....................: 255.255.255.0
   Default Gateway.................: 192.168.135.72
```

이 단계에서 확인해야 하는 것은 단순하다.

```
PC IP와 게이트웨이가 같은 네트워크인가?
서브넷 마스크가 올바른가?
기본 게이트웨이가 실제 라우터 인터페이스 주소인가?
```

PC1의 경우 다음 계산이 성립한다.

```
PC1:             192.168.135.1/24
Default Gateway: 192.168.135.72/24
Network:         192.168.135.0/24
```

두 주소 모두 같은 192.168.135.0/24 네트워크에 속하므로 정상이다.

---

# 6. 3단계: 라우터 인터페이스 상태 확인

각 라우터에서 다음 명령을 실행한다.

```
show ip interface brief
```

## RTA 확인 결과

```
RTA# show ip interface brief

Interface              IP-Address      OK? Method Status                Protocol
FastEthernet0/0        192.168.12.54   YES manual up                    up
Serial0/0              192.168.13.13   YES manual up                    up
Serial0/1              192.168.14.64   YES manual up                    up
Serial1/0              192.168.15.17   YES manual up                    up
Vlan1                  unassigned      YES unset  administratively down down
```

## RTB 확인 결과

```
RTB# show ip interface brief

Interface              IP-Address       OK? Method Status                Protocol
FastEthernet0/0        192.168.135.72   YES manual up                    up
FastEthernet0/1        192.168.21.95    YES manual up                    up
Serial0/0              192.168.13.163   YES manual up                    up
Vlan1                  unassigned       YES unset  administratively down down
```

## RTC 확인 결과

```
RTC# show ip interface brief

Interface              IP-Address       OK? Method Status                Protocol
FastEthernet0/0        192.168.12.22    YES manual up                    up
FastEthernet0/1        192.168.20.72    YES manual up                    up
FastEthernet1/0        192.168.120.24   YES manual up                    up
Vlan1                  unassigned       YES unset  administratively down down
```

## RTD 확인 결과

```
RTD# show ip interface brief

Interface              IP-Address       OK? Method Status                Protocol
FastEthernet0/0        192.168.83.175   YES manual up                    up
FastEthernet0/1        192.168.59.73    YES manual up                    up
Serial0/1              192.168.14.78    YES manual up                    up
Vlan1                  unassigned       YES unset  administratively down down
```

정상 인터페이스는 반드시 다음 상태여야 한다.

```
Status:   up
Protocol: up
```

즉, up/up 상태여야 한다.

---

## 6.1 인터페이스 상태별 의미

### up/up

```
FastEthernet0/0   192.168.12.54   up   up
```

물리 계층과 데이터 링크 계층이 모두 정상이다.

### administratively down/down

```
FastEthernet0/0   192.168.12.54   administratively down   down
```

관리자가 인터페이스를 활성화하지 않은 상태다.

다음 명령으로 활성화한다.

```
enable
configure terminal
interface fastEthernet 0/0
 no shutdown
end
```

### up/down

```
Serial0/0   192.168.13.13   up   down
```

물리 연결은 감지되지만 데이터 링크 계층이 정상적으로 동작하지 않는 상태다.

Serial 구간이라면 다음 항목을 확인해야 한다.

- 양쪽 encapsulation 설정

- DCE 측 clock rate

- 반대편 인터페이스 상태

- 케이블 연결

- 서브인터페이스 또는 Frame Relay 설정

---

# 7. 4단계: 직결 라우터끼리 Ping 확인

EIGRP가 없어도 직접 연결된 라우터끼리는 통신되어야 한다.

RTA에서 각 이웃 라우터 인터페이스로 Ping을 실행했다.

```
RTA# ping 192.168.13.163

Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 192.168.13.163, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5)
```

```
RTA# ping 192.168.14.78

Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 192.168.14.78, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5)
```

```
RTA# ping 192.168.12.22

Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 192.168.12.22, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5)
```

```
RTA# ping 192.168.15.127

Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 192.168.15.127, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5)
```

직결 Ping이 성공했으므로 다음 항목은 정상이다.

```
RTA와 각 라우터 사이의 물리 연결
라우터 간 인터페이스 IP
서브넷 마스크
인터페이스 up/up 상태
Serial clock 설정
직접 연결 경로
```

이제 문제 범위를 EIGRP 설정으로 좁힐 수 있다.

---

# 8. 5단계: EIGRP 설정 확인

각 라우터에서 다음 명령을 실행한다.

```
show running-config
```

지원되는 IOS라면 다음처럼 EIGRP 부분만 확인할 수도 있다.

```
show running-config | section router eigrp
```

---

## 8.1 RTA EIGRP 설정

```
RTA# show running-config | section router eigrp

router eigrp 212
 network 192.168.13.0
 network 192.168.14.0
 no auto-summary
```

RTA에는 RTB 연결망과 RTD 연결망만 등록되어 있다.

```
192.168.13.0/24 → RTB 연결망
192.168.14.0/24 → RTD 연결망
```

하지만 RTC 연결망인 192.168.12.0/24가 없다.

RTA와 ISP 사이의 192.168.15.0/24도 누락되어 있다.

---

## 8.2 RTB EIGRP 설정

```
RTB# show running-config | section router eigrp

router eigrp 212
 network 192.168.13.0
 network 192.168.135.0
 network 192.168.21.0
 no auto-summary
```

RTB는 다음 네트워크를 EIGRP에 정상적으로 포함하고 있다.

```
192.168.13.0/24  → RTA 연결망
192.168.135.0/24 → PC1 LAN
192.168.21.0/24  → PC2 LAN
```

---

## 8.3 RTD EIGRP 설정

```
RTD# show running-config | section router eigrp

router eigrp 212
 network 192.168.14.0
 network 192.168.83.0
 network 192.168.59.0
 no auto-summary
```

RTD 역시 AS 번호와 네트워크 설정이 정상이다.

---

## 8.4 RTC EIGRP 설정

```
RTC# show running-config | section router eigrp

router eigrp 22
 network 192.168.12.0
 network 192.168.20.0
 network 192.168.120.0
 no auto-summary
```

RTC는 다른 라우터와 달리 EIGRP AS 번호가 22로 설정되어 있었다.

다른 라우터는 모두 다음 프로세스를 사용한다.

```
router eigrp 212
```

반면 RTC만 다음 프로세스를 사용한다.

```
router eigrp 22
```

이 상태에서는 RTA와 RTC가 EIGRP Hello 패킷을 주고받더라도 이웃 관계를 형성할 수 없다.

---

# 9. EIGRP AS 번호의 의미

EIGRP에서 다음 명령의 숫자는 EIGRP 프로세스 또는 Autonomous System 번호를 의미한다.

```
router eigrp 212
```

EIGRP 이웃 관계를 맺으려는 라우터는 동일한 AS 번호를 사용해야 한다.

예를 들어 다음 두 라우터는 이웃 관계를 형성할 수 있다.

```
RTA: router eigrp 212
RTB: router eigrp 212
```

하지만 다음 구성은 이웃 관계를 형성할 수 없다.

```
RTA: router eigrp 212
RTC: router eigrp 22
```

IP 주소가 같은 네트워크에 있고 직결 Ping이 성공하더라도, EIGRP AS 번호가 다르면 동적 라우팅 정보를 교환하지 않는다.

이것이 중요한 이유는 다음과 같다.

```
직결 Ping 성공
≠
EIGRP 이웃 관계 정상
```

직결 Ping은 IP 계층의 직접 연결성을 확인하지만, EIGRP 인접 관계는 별도의 프로토콜 조건을 만족해야 한다.

---

# 10. 6단계: EIGRP 이웃 관계 확인

다음 명령으로 EIGRP 이웃을 확인한다.

```
show ip eigrp neighbors
```

## 장애 상태의 RTA

```
RTA# show ip eigrp neighbors

IP-EIGRP neighbors for process 212
H   Address          Interface       Hold Uptime   SRTT   RTO  Q  Seq
                                      (sec)         (ms)       Cnt Num
0   192.168.13.163   Se0/0             12 00:18:42   20   200  0  8
1   192.168.14.78    Se0/1             13 00:18:39   18   200  0  11
```

RTA는 RTB와 RTD만 이웃으로 인식한다.

```
192.168.13.163 → RTB
192.168.14.78  → RTD
```

RTC 주소인 192.168.12.22는 목록에 없다.

이 결과만으로 다음 중 하나를 의심할 수 있다.

```
RTA에서 192.168.12.0 네트워크가 EIGRP에 포함되지 않음
RTC에서 EIGRP가 실행되지 않음
RTA와 RTC의 AS 번호가 다름
passive-interface 설정
K-value 불일치
인증 설정 불일치
```

이번 환경에서는 실제로 두 가지 문제가 동시에 존재했다.

```
RTA의 network 192.168.12.0 누락
RTC의 AS 번호 22 설정
```

---

# 11. 7단계: 라우팅 테이블 확인

라우터가 목적지 네트워크를 알고 있는지 확인한다.

```
show ip route
```

EIGRP 경로만 보려면 다음 명령을 사용할 수 있다.

```
show ip route eigrp
```

## 장애 상태의 RTA 라우팅 테이블

```
RTA# show ip route eigrp

     192.168.0.0/24 is subnetted, 6 subnets
D       192.168.135.0 [90/2172416] via 192.168.13.163, 00:12:43, Serial0/0
D       192.168.21.0  [90/2172416] via 192.168.13.163, 00:12:43, Serial0/0
D       192.168.83.0  [90/2172416] via 192.168.14.78, 00:12:39, Serial0/1
D       192.168.59.0  [90/2172416] via 192.168.14.78, 00:12:39, Serial0/1
```

RTA는 RTB와 RTD 아래 네트워크를 학습하고 있다.

하지만 RTC 아래의 다음 네트워크는 없다.

```
192.168.20.0/24
192.168.120.0/24
```

따라서 PC1에서 PC3으로 전달된 패킷이 RTA에 도착하더라도 RTA는 192.168.20.0/24 네트워크로 가는 경로를 찾지 못한다.

---

# 12. 장애 원인 정리

이번 장애의 직접적인 원인은 두 가지였다.

## 원인 1. RTC의 EIGRP AS 번호 불일치

```
다른 라우터: EIGRP 212
RTC:         EIGRP 22
```

이 때문에 RTC는 RTA와 EIGRP 이웃 관계를 형성할 수 없었다.

---

## 원인 2. RTA의 RTC 연결 네트워크 누락

RTA의 기존 설정은 다음과 같았다.

```
router eigrp 212
 network 192.168.13.0
 network 192.168.14.0
 no auto-summary
```

RTC와 연결된 네트워크는 192.168.12.0/24다.

하지만 RTA의 EIGRP 설정에 다음 명령이 없었다.

```
network 192.168.12.0
```

따라서 RTA는 RTC 방향 FastEthernet 인터페이스에서 EIGRP를 활성화하지 않았다.

---

# 13. 설정 수정

## 13.1 RTA 수정

RTA에 RTC 연결망을 추가한다.

ISP까지 EIGRP에 포함하기 위해 192.168.15.0도 함께 추가했다.

```
enable
configure terminal
!
router eigrp 212
 network 192.168.12.0
 network 192.168.15.0
 no auto-summary
!
end
copy running-config startup-config
```

수정 후 설정은 다음과 같다.

```
RTA# show running-config | section router eigrp

router eigrp 212
 network 192.168.12.0
 network 192.168.13.0
 network 192.168.14.0
 network 192.168.15.0
 no auto-summary
```

---

## 13.2 RTC 수정

RTC의 잘못된 EIGRP 22 프로세스를 삭제하고, EIGRP 212로 다시 구성한다.

```
enable
configure terminal
!
no router eigrp 22
!
router eigrp 212
 network 192.168.12.0
 network 192.168.20.0
 network 192.168.120.0
 no auto-summary
!
end
copy running-config startup-config
```

수정 후 결과를 확인한다.

```
RTC# show running-config | section router eigrp

router eigrp 212
 network 192.168.12.0
 network 192.168.20.0
 network 192.168.120.0
 no auto-summary
```

기존 EIGRP 22 프로세스를 제거한 이유는 잘못된 라우팅 프로세스를 남겨 두지 않기 위해서다.

단순히 다음 설정만 추가하면 기존 프로세스가 그대로 남을 수 있다.

```
router eigrp 212
```

따라서 다음 명령으로 기존 프로세스를 명확하게 삭제하는 것이 좋다.

```
no router eigrp 22
```

---

# 14. 수정 후 EIGRP 이웃 관계 확인

RTA에서 다시 이웃 관계를 확인한다.

```
RTA# show ip eigrp neighbors

IP-EIGRP neighbors for process 212
H   Address          Interface       Hold Uptime   SRTT   RTO  Q  Seq
                                      (sec)         (ms)       Cnt Num
0   192.168.13.163   Se0/0             12 00:24:15   20   200  0  15
1   192.168.14.78    Se0/1             13 00:24:11   18   200  0  19
2   192.168.12.22    Fa0/0             14 00:00:32    8   200  0  6
3   192.168.15.127   Se1/0             12 00:00:28   17   200  0  5
```

이제 RTC 주소인 192.168.12.22가 EIGRP 이웃 목록에 나타난다.

RTC에서도 RTA가 확인된다.

```
RTC# show ip eigrp neighbors

IP-EIGRP neighbors for process 212
H   Address          Interface       Hold Uptime   SRTT   RTO  Q  Seq
                                      (sec)         (ms)       Cnt Num
0   192.168.12.54    Fa0/0             13 00:00:41    9   200  0  21
```

---

# 15. 수정 후 라우팅 테이블 확인

## RTA

```
RTA# show ip route eigrp

     192.168.0.0/24 is subnetted, 8 subnets
D       192.168.135.0 [90/2172416] via 192.168.13.163, 00:25:17, Serial0/0
D       192.168.21.0  [90/2172416] via 192.168.13.163, 00:25:17, Serial0/0
D       192.168.83.0  [90/2172416] via 192.168.14.78, 00:25:13, Serial0/1
D       192.168.59.0  [90/2172416] via 192.168.14.78, 00:25:13, Serial0/1
D       192.168.20.0  [90/30720] via 192.168.12.22, 00:01:22, FastEthernet0/0
D       192.168.120.0 [90/30720] via 192.168.12.22, 00:01:22, FastEthernet0/0
```

이제 RTA가 RTC 아래의 두 LAN을 학습한다.

```
192.168.20.0/24
192.168.120.0/24
```

---

## RTC

```
RTC# show ip route eigrp

     192.168.0.0/24 is subnetted, 8 subnets
D       192.168.135.0 [90/2195456] via 192.168.12.54, 00:01:25, FastEthernet0/0
D       192.168.21.0  [90/2195456] via 192.168.12.54, 00:01:25, FastEthernet0/0
D       192.168.83.0  [90/2195456] via 192.168.12.54, 00:01:25, FastEthernet0/0
D       192.168.59.0  [90/2195456] via 192.168.12.54, 00:01:25, FastEthernet0/0
```

RTC도 RTB와 RTD 아래 네트워크를 학습했다.

이 경로는 PC3이 PC1로 Echo Reply를 돌려보내기 위해 반드시 필요하다.

---

# 16. 최종 PC 간 Ping 테스트

PC1에서 PC3으로 다시 Ping을 실행한다.

```
PC> ping 192.168.20.1
```

정상 결과:

```
Pinging 192.168.20.1 with 32 bytes of data:

Reply from 192.168.20.1: bytes=32 time<1ms TTL=125
Reply from 192.168.20.1: bytes=32 time<1ms TTL=125
Reply from 192.168.20.1: bytes=32 time<1ms TTL=125
Reply from 192.168.20.1: bytes=32 time<1ms TTL=125

Ping statistics for 192.168.20.1:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)
```

PC1에서 PC5로도 테스트한다.

```
PC> ping 192.168.120.1
```

```
Pinging 192.168.120.1 with 32 bytes of data:

Reply from 192.168.120.1: bytes=32 time<1ms TTL=125
Reply from 192.168.120.1: bytes=32 time<1ms TTL=125
Reply from 192.168.120.1: bytes=32 time<1ms TTL=125
Reply from 192.168.120.1: bytes=32 time<1ms TTL=125
```

반대 방향도 확인한다.

```
PC3> ping 192.168.135.1
```

```
Pinging 192.168.135.1 with 32 bytes of data:

Reply from 192.168.135.1: bytes=32 time<1ms TTL=125
Reply from 192.168.135.1: bytes=32 time<1ms TTL=125
Reply from 192.168.135.1: bytes=32 time<1ms TTL=125
Reply from 192.168.135.1: bytes=32 time<1ms TTL=125
```

---

# 17. Traceroute로 실제 경로 확인

Ping은 통신 성공 여부를 보여주지만, 어떤 라우터를 거쳤는지는 자세히 보여주지 않는다.

Packet Tracer PC에서는 tracert를 사용할 수 있다.

```
PC> tracert 192.168.20.1
```

정상적인 경로 예시는 다음과 같다.

```
Tracing route to 192.168.20.1 over a maximum of 30 hops:

  1   <1 ms   <1 ms   <1 ms   192.168.135.72
  2   <1 ms   <1 ms   <1 ms   192.168.13.13
  3   <1 ms   <1 ms   <1 ms   192.168.12.22
  4   <1 ms   <1 ms   <1 ms   192.168.20.1

Trace complete.
```

각 홉의 의미는 다음과 같다.

```
1번 홉: RTB의 PC1 기본 게이트웨이
2번 홉: 중앙 라우터 RTA
3번 홉: 목적지 LAN을 보유한 RTC
4번 홉: 목적지 PC3
```

---

# 18. PC1에서 PC3까지 패킷 전달 과정

## 18.1 PC1의 목적지 네트워크 판단

PC1의 주소는 다음과 같다.

```
192.168.135.1/24
```

목적지 PC3의 주소는 다음과 같다.

```
192.168.20.1/24
```

PC1은 서브넷 마스크를 적용하여 두 주소가 서로 다른 네트워크라는 것을 판단한다.

```
PC1 네트워크: 192.168.135.0/24
PC3 네트워크: 192.168.20.0/24
```

따라서 PC1은 목적지 PC3의 MAC 주소를 직접 찾지 않는다.

대신 기본 게이트웨이인 RTB의 MAC 주소를 ARP로 조회한다.

---

## 18.2 RTB의 라우팅 결정

RTB는 패킷의 목적지 IP 192.168.20.1을 확인한다.

RTB 라우팅 테이블에는 다음과 같은 EIGRP 경로가 있다.

```
D 192.168.20.0/24 via 192.168.13.13
```

따라서 패킷을 RTA 방향 Serial 인터페이스로 전달한다.

---

## 18.3 RTA의 라우팅 결정

RTA는 목적지 192.168.20.1에 대해 Longest Prefix Match를 수행한다.

수정 후 RTA에는 다음 경로가 존재한다.

```
D 192.168.20.0/24 via 192.168.12.22
```

RTA는 RTC의 주소 192.168.12.22를 다음 홉으로 선택하고 FastEthernet0/0으로 패킷을 전달한다.

---

## 18.4 RTC의 직접 연결 경로

RTC는 192.168.20.0/24 네트워크를 직접 연결된 네트워크로 알고 있다.

```
C 192.168.20.0/24 is directly connected, FastEthernet0/1
```

따라서 PC3이 연결된 FastEthernet0/1 인터페이스로 패킷을 전달한다.

필요한 경우 RTC는 PC3의 MAC 주소를 찾기 위해 ARP Request를 전송한다.

---

## 18.5 응답 경로

PC3은 Echo Reply를 생성한다.

PC3 입장에서도 PC1은 다른 네트워크에 있으므로 기본 게이트웨이 192.168.20.72로 응답을 전송한다.

응답 경로는 다음과 같다.

```
PC3
→ RTC
→ RTA
→ RTB
→ PC1
```

Ping이 성공하려면 요청 경로뿐 아니라 응답 경로도 모두 존재해야 한다.

---

# 19. 수정 전에는 패킷이 어디에서 폐기되었는가

수정 전에는 RTA가 RTC 아래 네트워크를 학습하지 못했다.

```
PC1
→ RTB
→ RTA
→ 목적지 경로 없음
→ 패킷 폐기
```

RTA에는 다음 경로가 존재하지 않았다.

```
192.168.20.0/24
192.168.120.0/24
```

따라서 패킷이 RTA까지 도착하더라도 더 이상 전달할 인터페이스를 결정하지 못했다.

이 장애의 중요한 점은 RTA와 RTC 사이의 직결 Ping은 성공했다는 것이다.

```
RTA# ping 192.168.12.22
!!!!!
```

하지만 직결 Ping이 성공한다고 해서 RTA가 RTC 뒤쪽 LAN까지 알고 있는 것은 아니다.

```
직결 인터페이스 통신 가능
≠
원격 LAN 경로 학습 완료
```

---

# 20. Packet Tracer Simulation Mode로 확인하기

CLI 결과 외에도 Packet Tracer의 Simulation Mode를 이용하면 패킷이 어느 장비에서 폐기되는지 시각적으로 확인할 수 있다.

오른쪽 아래에서 다음 모드로 전환한다.

```
Realtime → Simulation
```

이후 이벤트 필터에서 다음 프로토콜만 남긴다.

```
ARP
ICMP
EIGRP
```

PC1에서 PC3으로 Simple PDU를 전송한다.

관찰할 항목은 다음과 같다.

```
PC1이 기본 게이트웨이 MAC 주소를 ARP로 조회하는가?
RTB가 ICMP 패킷을 RTA로 전달하는가?
RTA가 목적지 경로를 찾는가?
RTA와 RTC 사이에 EIGRP Hello가 교환되는가?
EIGRP Update를 통해 LAN 경로가 전달되는가?
PC3의 Echo Reply가 PC1까지 돌아오는가?
```

수정 전에는 RTA와 RTC 사이에 정상적인 EIGRP 이웃 관계가 형성되지 않는다.

수정 후에는 다음 흐름을 확인할 수 있다.

```
EIGRP Hello
→ 이웃 관계 형성
→ EIGRP Update 교환
→ 라우팅 테이블 갱신
→ ICMP Echo Request 전달
→ ICMP Echo Reply 반환
```

---

# 21. 트러블슈팅에 사용한 핵심 명령어

## PC

```
ipconfig
ping <기본 게이트웨이>
ping <목적지 PC>
tracert <목적지 PC>
```

## 라우터 인터페이스

```
show ip interface brief
show interfaces
show interfaces serial 0/0
show controllers serial 0/0
```

## EIGRP

```
show running-config
show running-config | section router eigrp
show ip protocols
show ip eigrp neighbors
show ip eigrp topology
show ip route
show ip route eigrp
```

## 연결성 확인

```
ping <직결 라우터 IP>
ping <원격 LAN PC IP>
traceroute <목적지 IP>
```

---

# 22. EIGRP 장애 체크리스트

PC 간 통신이 실패할 경우 다음 순서로 확인한다.

```
[ ] PC IP 주소가 올바른가?
[ ] PC 서브넷 마스크가 올바른가?
[ ] PC 기본 게이트웨이가 올바른가?
[ ] PC에서 기본 게이트웨이 Ping이 성공하는가?
[ ] 라우터 인터페이스가 up/up 상태인가?
[ ] 직결 라우터끼리 Ping이 성공하는가?
[ ] EIGRP AS 번호가 동일한가?
[ ] network 명령에 연결망이 포함되어 있는가?
[ ] passive-interface가 적용되어 있지 않은가?
[ ] show ip eigrp neighbors에 이웃이 나타나는가?
[ ] show ip route eigrp에 원격 LAN 경로가 있는가?
[ ] 요청 경로뿐 아니라 응답 경로도 존재하는가?
```

---

# 23. 이번 장애에서 배운 점

## 첫째, Ping 실패를 곧바로 라우팅 프로토콜 문제로 판단하면 안 된다

PC 설정, 기본 게이트웨이, 인터페이스 상태, 직접 연결 구간을 먼저 확인해야 한다.

---

## 둘째, 직결 Ping 성공과 EIGRP 정상 동작은 별개의 문제다

RTA와 RTC 사이의 IP 통신은 가능했지만 EIGRP AS 번호가 달라 라우팅 정보를 교환하지 못했다.

```
IP 연결성 정상
EIGRP 인접 관계 비정상
```

두 상태는 동시에 존재할 수 있다.

---

## 셋째, EIGRP의 network 명령은 단순한 경로 광고 명령이 아니다

EIGRP의 network 명령은 해당 주소와 일치하는 인터페이스에서 EIGRP를 활성화한다.

RTA에 다음 명령이 없으면:

```
network 192.168.12.0
```

RTA는 RTC 방향 인터페이스에서 EIGRP Hello를 전송하지 않는다.

---

## 넷째, Ping은 왕복 통신이다

출발지에서 목적지까지의 경로만 있어서는 안 된다.

```
Echo Request 경로
Echo Reply 경로
```

두 경로가 모두 존재해야 Ping이 성공한다.

---

## 다섯째, 중앙 라우터의 라우팅 테이블을 먼저 확인하면 장애를 빠르게 좁힐 수 있다

이번 토폴로지에서는 모든 라우터 간 통신이 RTA를 통과한다.

따라서 RTA에서 다음 명령을 확인하는 것이 효과적이었다.

```
show ip eigrp neighbors
show ip route eigrp
show ip protocols
```

RTA가 어떤 라우터와 이웃 관계를 맺고 있는지, 어떤 LAN을 학습했는지 확인하면 문제 구간을 빠르게 찾을 수 있다.

---

# 24. 최종 수정 명령 모음

## RTA

```
enable
configure terminal
!
router eigrp 212
 network 192.168.12.0
 network 192.168.15.0
 no auto-summary
!
end
copy running-config startup-config
```

## RTC

```
enable
configure terminal
!
no router eigrp 22
!
router eigrp 212
 network 192.168.12.0
 network 192.168.20.0
 network 192.168.120.0
 no auto-summary
!
end
copy running-config startup-config
```

## 수정 결과 확인

```
show ip interface brief
show ip protocols
show ip eigrp neighbors
show ip route eigrp
```

---

# 마무리

이번 장애는 PC 설정이나 물리 인터페이스 문제가 아니라, EIGRP 인접 관계가 형성되지 않아 원격 네트워크 경로를 학습하지 못한 문제였다.

핵심 원인은 다음 두 가지였다.

```
RTC의 EIGRP AS 번호 불일치
RTA의 RTC 연결 네트워크 누락
```

설정을 수정한 뒤 RTA와 RTC가 EIGRP 이웃 관계를 형성했고, RTC 아래의 192.168.20.0/24와 192.168.120.0/24 경로가 다른 라우터에 전파되었다.

결과적으로 서로 다른 라우터에 연결된 PC 사이에서도 정상적으로 Ping이 전달되었다.

네트워크 장애를 해결할 때 가장 중요한 것은 설정을 무작정 바꾸는 것이 아니라, 다음과 같이 장애 범위를 단계적으로 좁히는 것이다.

```
호스트
→ 게이트웨이
→ 인터페이스
→ 직결 구간
→ 라우팅 프로토콜
→ 라우팅 테이블
→ 왕복 경로
```

이 순서를 습관화하면 EIGRP뿐 아니라 OSPF, RIP, 정적 라우팅, VLAN 간 라우팅 환경에서도 훨씬 빠르게 문제를 찾을 수 있다.