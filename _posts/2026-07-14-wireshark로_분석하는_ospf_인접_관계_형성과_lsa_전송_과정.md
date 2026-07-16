---
title: "Wireshark로 분석하는 OSPF 인접 관계 형성과 LSA 전송 과정"
date: "2026-07-14T08:02:00.000Z"
categories:
  - "ospf"
  - "wireshark"
author: "현제 김_7254"
slug: "wireshark로_분석하는_ospf_인접_관계_형성과_lsa_전송_과정"
---

![image](/assets/image_695b5199-6640-4bec-9a8d-c91043554d26.png)

## 1. 분석에 앞서 확인한 캡처 환경

패킷에 기록된 주소와 Router ID를 기준으로 보면, 다음 링크에서 R1과 R2가 Area 0 OSPF 인접 관계를 새로 형성하는 구간을 캡처한 파일이다.

```
R1
Router ID: 1.1.1.1
Interface IP: 13.13.12.1
        │
        │ 13.13.12.0/24
        │ Cisco HDLC Serial
        │
R2
Router ID: 2.2.2.2
Interface IP: 13.13.12.2
```

Router-LSA 내용을 통해 주변 네트워크를 다음처럼 추론할 수 있다.

```
172.16.1.0/24
      │
      │ Cost 1
      │
     R1
  1.1.1.1
      ├──────── 13.13.10.0/24, Cost 10
      │
      │ 13.13.12.1
      │ Cost 64
      │
  13.13.12.0/24
      │
      │ 13.13.12.2
      │ Cost 64
      │
     R2
  2.2.2.2
      ├──────── 13.13.20.0/24, Cost 10
      │
      │ 13.13.23.2
      │ Cost 64
      │
  13.13.23.0/24
      │
     R3
  3.3.3.3
```

R2는 R1과 인접 관계를 맺기 전부터 Router ID 3.3.3.3인 R3와 이미 연결되어 있었다.

PCAP에는 총 51개 프레임이 들어 있다.

캡처 링크 계층은 Ethernet이 아니라 다음과 같다.

```
BSD/OS Cisco HDLC
```

따라서 패킷 앞에는 Ethernet MAC Header 대신 Cisco HDLC Header가 존재한다.

```
Cisco HDLC Header
        ↓
IPv4 Header
        ↓
OSPF Header
        ↓
Hello / DBD / LSR / LSU / LSAck
```

OSPF 패킷의 공통 속성은 다음과 같다.

목적지 주소 224.0.0.5는 다음 의미를 가진다.

```
224.0.0.5
= AllSPFRouters
= 동일 링크에 있는 모든 OSPF 라우터
```

TTL이 1이므로 이 OSPF 제어 패킷은 다른 라우터를 넘어 전달되지 않는다.

### 전체 OSPF 협상 타임라인

아래 시간은 R2가 첫 번째 Hello를 보낸 프레임 15를 기준으로 계산한 상대 시간이다.

캡처상 R2의 첫 Hello부터 상호 LSDB 요청과 응답이 끝날 때까지는 약 0.156초가 걸렸다.

새 인접 관계를 반영한 Router-LSA의 Flooding과 LSAck까지 포함하면 약 3.172초가 걸렸다.

단, LSAck는 지연 전송될 수 있으므로 이것을 정확한 FULL 상태 전환 시간이라고 보기는 어렵다. 실제 Full 상태 도달은 프레임 28과 29에서 요청한 LSA를 모두 수신한 시점 전후로 해석할 수 있다.

# 1단계: Hello 패킷과 Neighbor 발견

## Frame 7, 12: R1만 Hello를 송신하는 구간

R1은 다음 정보를 담은 Hello를 반복적으로 전송한다.

![image](/assets/image_a0bc837e-77e8-4edf-88fd-1970b74d8d1e.png)

```
Source IP       : 13.13.12.1
Destination IP  : 224.0.0.5
Router ID       : 1.1.1.1
Area ID         : 0.0.0.0
Network Mask    : 255.255.255.0
Hello Interval  : 10
Dead Interval   : 40
DR              : 0.0.0.0
BDR             : 0.0.0.0
Neighbor List   : 없음
```

Neighbor 목록이 비어 있다는 것은 R1이 아직 이 링크에서 유효한 OSPF Neighbor를 발견하지 못했다는 의미다.

```
R1 Hello
Neighbor List: Empty
```

OSPF는 Hello 패킷에 자신이 인식한 Neighbor의 Router ID를 기록한다.

따라서 Neighbor 목록은 단순 장비 목록이 아니라 양방향 통신 여부를 확인하는 장치로 사용된다.

## Frame 15: R2의 첫 번째 Hello

R2가 다음 Hello를 전송한다.

![image](/assets/image_2c987a15-fd8f-48f5-9b26-581f615ea12e.png)

## Frame 15: R2의 첫 번째 Hello

R2가 다음 Hello를 전송한다.

```
Source IP       : 13.13.12.2
Router ID       : 2.2.2.2
Neighbor List   : 없음
```

R1이 이 Hello를 수신하면 R1의 Neighbor State Machine에서 R2는 우선 Init 상태가 된다.

```
R1이 R2의 Hello를 수신함
        ↓
R1은 R2의 존재를 알게 됨
        ↓
하지만 R2의 Hello에는 R1이 없음
        ↓
Neighbor State: Init
```

## Frame 16: R1이 R2를 Neighbor 목록에 추가

31ms 후 R1이 다음 Hello를 전송한다.

```
Router ID       : 1.1.1.1
Neighbor List   : 2.2.2.2
```

![image](/assets/image_e2b8aba2-aacd-463a-a80d-44da7ae7d550.png)

이 Hello를 받은 R2는 상대 Hello의 Neighbor 목록에서 자신의 Router ID인 2.2.2.2를 확인한다.

```
R2가 R1의 Hello 수신
        ↓
Neighbor 목록에서 2.2.2.2 발견
        ↓
양방향 통신 확인
        ↓
2-Way 상태 진입
```

## Frame 18: R2도 R1을 Neighbor 목록에 추가

R2 역시 다음 Hello를 보낸다.

```
Router ID       : 2.2.2.2
Neighbor List   : 1.1.1.1
```

![image](/assets/image_f1754e72-731d-4b5e-9382-ab50c2fd920d.png)

R1도 자신의 Router ID를 확인하게 된다.

```
R1 ↔ R2

R1이 R2를 인식함
R2가 R1을 인식함

Neighbor State: 2-Way
```

---

## Hello 값은 협상되는 값이 아니다

다음 값들은 두 라우터가 서로 협상해서 하나를 선택하는 값이 아니다.

```
Area ID
Hello Interval
Dead Interval
Authentication
Network Type
```

양쪽 설정이 미리 호환되어 있어야 한다.

예를 들어 R1의 Hello Interval이 10초이고 R2가 30초라면 서로의 Hello를 수신해도 정상적인 Neighbor가 되지 못한다.

이번 캡처에서는 양쪽 값이 모두 다음과 같이 일치한다.

```
Hello Interval : 10초
Dead Interval  : 40초
Area ID        : 0.0.0.0
Network Mask   : 255.255.255.0
Authentication : 없음
```

# 5. Point-to-Point 네트워크와 DR/BDR

Hello 패킷에서 다음 값이 확인된다.

```
DR  : 0.0.0.0
BDR : 0.0.0.0
```

캡처 링크는 Cisco HDLC Serial 링크다.

Serial Point-to-Point OSPF 네트워크에서는 두 라우터만 존재하므로 DR과 BDR을 선출할 필요가 없다.

```
Broadcast Ethernet
→ 여러 라우터 존재 가능
→ DR/BDR 선출

Point-to-Point Serial
→ 양 끝에 두 라우터만 존재
→ DR/BDR 선출 불필요
```

따라서 Neighbor 출력에서도 일반적으로 다음처럼 나타난다.

```
FULL/-
```

- 는 DR, BDR 역할이 없다는 의미다.

# 6. 2단계: ExStart와 Master/Slave 결정

2-Way 상태가 되면 R1과 R2는 LSDB의 요약 정보를 교환하기 위해 ExStart 단계로 진입한다.

이때 Database Description 패킷을 사용한다.

```
DBD
= Database Description
= LSDB 전체가 아니라 LSA Header 목록을 전달
```

---

## DBD의 I, M, MS 플래그

DBD 패킷에는 세 가지 핵심 플래그가 있다.

---

## Frame 17: R2의 초기 DBD

```
Source Router   : R2
Router ID       : 2.2.2.2
Interface MTU   : 1500
I               : 1
M               : 1
MS              : 1
DD Sequence     : 0x000023f0
LSA Header      : 없음
```

R2는 자신이 Master라고 제안한다.

---

## Frame 19: R1도 Master를 제안

```
Source Router   : R1
Router ID       : 1.1.1.1
Interface MTU   : 1500
I               : 1
M               : 1
MS              : 1
DD Sequence     : 0x00001516
```

R1 역시 자신이 Master라고 제안한다.

초기에는 양쪽 모두 MS=1로 시작할 수 있다.

최종 Master는 Router ID가 더 높은 라우터가 된다.

```
R1 Router ID : 1.1.1.1
R2 Router ID : 2.2.2.2

2.2.2.2 > 1.1.1.1
        ↓
R2가 Master
R1이 Slave
```

## Frame 20: R1이 Slave로 전환

R1은 R2가 제시한 DBD Sequence Number를 받아들인다.

```
I               : 0
M               : 1
MS              : 0
DD Sequence     : 0x000023f0
```

MS=0이므로 R1은 Slave다.

R1은 자신이 처음 제안했던 0x1516을 더 이상 사용하지 않고, Master인 R2의 0x23f0을 그대로 사용한다.

이 패킷부터 실제 LSA Header 목록이 포함된다.

## DBD Sequence Number 동작

이후 Sequence Number는 다음처럼 진행된다.

```
R2 Master  : 0x23f0
R1 Slave   : 0x23f0

R2 Master  : 0x23f1
R1 Slave   : 0x23f1

R2 Master  : 0x23f2
R1 Slave   : 0x23f2
```

Master가 번호를 증가시키고 Slave가 해당 번호를 확인하는 구조다.

이 Sequence Number는 Router-LSA의 Sequence Number와는 다른 값이다.

```
DBD Sequence Number
→ DBD 교환 순서를 제어

LSA Sequence Number
→ 동일한 LSA 중 어느 것이 최신인지 판단
```

# 7. MTU가 일치해야 하는 이유

R1과 R2의 DBD 패킷에는 모두 다음 값이 있다.

```
Interface MTU: 1500
```

MTU가 서로 다르면 DBD 교환 과정에서 문제가 발생해 Neighbor가 다음 상태에 머물 수 있다.

```
EXSTART
또는
EXCHANGE
```

이번 캡처에서는 양쪽 MTU가 1500으로 일치하므로 정상적으로 Exchange 단계로 진행한다.

# 8. 3단계: Exchange와 DBD Header 비교

DBD 패킷은 완전한 LSA를 전달하지 않는다.

각 LSA의 최신 여부를 비교하기 위한 20바이트 LSA Header를 전달한다.

LSA Header에는 다음 정보가 포함된다.

```
LS Age
Options
LSA Type
Link State ID
Advertising Router
LS Sequence Number
LS Checksum
LS Length
```

## Frame 21: R2가 전송한 LSDB 요약

R2의 DBD에도 세 개의 Router-LSA Header가 들어 있다.

두 데이터베이스를 비교하면 차이를 확인할 수 있다.

## R1 Router-LSA 비교

```
R1이 가진 R1 LSA
Sequence: 0x80000008

R2가 가진 R1 LSA
Sequence: 0x80000006
```

R1의 LSA가 더 최신이다.

```
0x80000008 > 0x80000006
```

따라서 R2는 R1의 최신 Router-LSA가 필요하다.

---

## R2 Router-LSA 비교

```
R1이 가진 R2 LSA
Sequence: 0x80000005

R2가 가진 R2 LSA
Sequence: 0x80000006
```

R2의 LSA가 더 최신이다.

따라서 R1은 R2의 최신 Router-LSA가 필요하다.

## R3 Router-LSA 비교

R3의 Router-LSA는 양쪽 모두 동일하다.

```
Sequence : 0x80000004
Length   : 72
Checksum : 0x7682
```

양쪽이 동일한 LSA를 이미 가지고 있으므로 R3의 LSA를 다시 요청하지 않는다.

이 과정이 OSPF가 전체 데이터베이스를 매번 복사하지 않고 필요한 정보만 요청할 수 있는 이유다.

# 9. LSA의 최신 여부를 판단하는 기준

OSPF는 주로 다음 값을 이용해 LSA의 최신 여부를 판단한다.

```
1. LS Sequence Number
2. LS Checksum
3. LS Age
```

일반적으로 Sequence Number가 더 큰 LSA가 최신이다.

```
0x80000008
>
0x80000006
```

Sequence Number가 같은 경우 Checksum과 Age를 추가로 비교한다.

LSA Sequence Number는 일반적으로 다음 값부터 시작한다.

```
0x80000001
```

토폴로지가 변경되어 해당 라우터가 LSA를 다시 생성하면 Sequence Number가 증가한다.

# 10. 4단계: Loading과 LSR

DBD 비교를 통해 자신에게 없는 최신 LSA를 확인한 라우터는 Link State Request를 전송한다.

---

## Frame 25: R2가 R1 Router-LSA 요청

![image](/assets/image_c8f127b5-610a-4eb3-abfa-3732e71f3232.png)

```
Source Router      : R2
LSA Type           : 1, Router-LSA
Link State ID      : 1.1.1.1
Advertising Router : 1.1.1.1
```

의미는 다음과 같다.

```
R2:
“Advertising Router가 1.1.1.1인
최신 Router-LSA를 보내 달라.”
```

## Frame 26: R1이 R2 Router-LSA 요청

```
Source Router      : R1
LSA Type           : 1, Router-LSA
Link State ID      : 2.2.2.2
Advertising Router : 2.2.2.2
```

```
R1:
“Advertising Router가 2.2.2.2인
최신 Router-LSA를 보내 달라.”
```

LSR에는 전체 LSA 정보가 들어 있지 않다.

필요한 LSA를 식별하기 위한 다음 세 값만 들어 있다.

```
LSA Type
Link State ID
Advertising Router
```

![image](/assets/image_5f5106d1-e785-40a5-b898-ca19d378a1e6.png)

# 11. 5단계: LSU를 이용한 요청 응답

LSR을 받은 라우터는 Link State Update 패킷으로 실제 LSA를 전달한다.

```
LSU
= Link State Update
= 하나 이상의 완전한 LSA를 운반
```

---

## Frame 28: R1이 자신의 Router-LSA 전송

![image](/assets/image_70f290ac-00dd-4f6b-8052-a9927bd4304d.png)

```
Source           : R1
LSA Type         : 1, Router-LSA
Link State ID    : 1.1.1.1
Advertising RID  : 1.1.1.1
Sequence         : 0x80000008
LS Age           : 14
LSA Length       : 60
Number of Links  : 3
```

이 패킷은 Frame 25에서 R2가 요청한 LSA에 대한 응답이다.

## Frame 29: R2가 자신의 Router-LSA 전송

![image](/assets/image_e895f428-9511-4782-8066-52e34706ad7b.png)

```
Source           : R2
LSA Type         : 1, Router-LSA
Link State ID    : 2.2.2.2
Advertising RID  : 2.2.2.2
Sequence         : 0x80000006
LS Age           : 120
LSA Length       : 60
Number of Links  : 3
```

이 패킷은 Frame 26에서 R1이 요청한 LSA에 대한 응답이다.

프레임 28과 29를 통해 양쪽이 요청한 데이터베이스 항목을 모두 수신한다.

```
DBD 비교
   ↓
필요한 LSA 확인
   ↓
LSR 요청
   ↓
LSU 응답
   ↓
LSDB 동기화
```

이 시점 전후로 Neighbor는 Loading 상태를 끝내고 Full 상태에 도달한 것으로 해석할 수 있다.

# 12. LSA Type과 Router-LSA 내부 Link Type의 차이

이번 캡처를 분석할 때 가장 혼동하기 쉬운 부분이다.

Frame 28의 LSA 자체는 다음 종류다.

```
LSA Type 1
= Router-LSA
```

그런데 Router-LSA 내부에는 다시 Link Type이라는 필드가 존재한다.

```
Router-LSA 내부 Link Type 1
= Point-to-Point Router Link

Router-LSA 내부 Link Type 3
= Stub Network
```

두 Type 번호는 서로 다른 계층의 값이다.

```
LSA Type 1
└── Router-LSA라는 LSA 종류

Router-LSA 내부 Link Type 1
└── 다른 라우터로 연결된 Point-to-Point Link

Router-LSA 내부 Link Type 3
└── Stub Network
```

# 13. Frame 28: R1 Router-LSA 상세 분석

R1이 전달한 기존 Router-LSA에는 총 세 개의 Link Descriptor가 있다.

## Link 1: 172.16.1.0/24

```
Link ID    : 172.16.1.0
Link Data  : 255.255.255.0
Link Type  : 3, Stub Network
Metric     : 1
```

이 네트워크는 R1에 직접 연결된 Stub Network다.

Cost 1은 Cisco 기본 Reference Bandwidth를 사용할 경우 100Mbps 인터페이스에서 흔히 나타나는 값이다.

```
100Mbps / 100Mbps = Cost 1
```

## Link 2: 13.13.10.0/24

```
Link ID    : 13.13.10.0
Link Data  : 255.255.255.0
Link Type  : 3, Stub Network
Metric     : 10
```

Cost 10은 논리 Bandwidth가 10Mbps인 인터페이스에서 나타날 수 있다.

```
100Mbps / 10Mbps = Cost 10
```

---

## Link 3: 13.13.12.0/24

```
Link ID    : 13.13.12.0
Link Data  : 255.255.255.0
Link Type  : 3, Stub Network
Metric     : 64
```

이 시점의 LSA에서는 13.13.12.0/24가 Stub Network로만 표현되어 있다.

아직 Router-LSA 내부에 R2로 향하는 Point-to-Point Router Link가 반영되지 않았

# 14. Frame 29: R2 Router-LSA 상세 분석

R2가 전달한 기존 Router-LSA에도 세 개의 Link Descriptor가 있다.

## Link 1: 13.13.20.0/24

```
Link ID    : 13.13.20.0
Link Data  : 255.255.255.0
Link Type  : 3, Stub Network
Metric     : 10
```

R2에 직접 연결된 LAN으로 해석할 수 있다.

![image](/assets/image_de32a4fe-197e-410b-9d3e-13e736af9e53.png)

## Link 2: R3 Point-to-Point Link

```
Link ID    : 3.3.3.3
Link Data  : 13.13.23.2
Link Type  : 1, Point-to-Point
Metric     : 64
```

각 필드의 의미는 다음과 같다.

```
Link ID
→ 상대 라우터의 Router ID
→ 3.3.3.3

Link Data
→ 자신의 로컬 인터페이스 주소
→ 13.13.23.2
```

즉, R2는 이미 Router ID 3.3.3.3인 R3와 Full 인접 관계를 가지고 있었다.

## Link 3: 13.13.23.0/24

```
Link ID    : 13.13.23.0
Link Data  : 255.255.255.0
Link Type  : 3, Stub Network
Metric     : 64
```

OSPF Router-LSA는 Point-to-Point 인터페이스를 표현할 때 다음 두 정보를 함께 포함할 수 있다.

```
상대 Router ID를 가리키는 Point-to-Point Link
+
해당 인터페이스의 IP Prefix를 나타내는 Stub Link
```

# 15. 6단계: Full 인접 관계 형성 후 새로운 Router-LSA 생성

프레임 28과 29는 LSR에 대한 응답이다.

그런데 곧바로 프레임 30과 31에서 새로운 Router-LSA가 발생한다.

이 두 패킷은 단순 요청 응답이 아니다.

R1과 R2의 인접 관계가 Full로 바뀌면서 각 라우터가 자신의 토폴로지 상태가 변경되었다고 판단하고 새로운 Router-LSA를 생성한 것이다.

```
Neighbor 상태가 Full로 변경
        ↓
새로운 Point-to-Point Link가 생김
        ↓
로컬 링크 상태 변경
        ↓
새 Router-LSA 생성
        ↓
Sequence Number 증가
        ↓
Area 전체로 Flooding
```

# 16. Frame 30: R2가 새 Router-LSA 생성

Frame 29의 R2 Router-LSA는 다음 상태였다.

![image](/assets/image_31a09e7c-2eba-48fd-9c81-ffb911f9bea5.png)

```
Sequence Number : 0x80000006
LS Age          : 120
Length          : 60
Number of Links : 3
```

Frame 30에서는 다음과 같이 변경된다.

```
Sequence Number : 0x80000007
LS Age          : 1
Length          : 84
Number of Links : 5
```

변화를 정리하면 다음과 같다.

Sequence Number가 증가했고 Age가 1로 초기화되었다.

이는 기존 LSA의 단순 재전송이 아니라 새로운 LSA가 생성되었다는 직접적인 증거다.

## R2가 새로 추가한 Link 1

```
Link ID    : 1.1.1.1
Link Data  : 13.13.12.2
Link Type  : 1, Point-to-Point
Metric     : 64
```

```
Link ID
→ 새 Neighbor인 R1의 Router ID

Link Data
→ R2 자신의 로컬 인터페이스 IP
```

## R2가 새로 추가한 Link 2

```
Link ID    : 13.13.12.0
Link Data  : 255.255.255.0
Link Type  : 3, Stub Network
Metric     : 64
```

R2는 새로 활성화된 Serial 인터페이스의 IP Prefix도 Router-LSA에 반영했다.

Router-LSA의 Link Descriptor는 하나당 기본 12바이트다.

R2는 두 개의 Link Descriptor를 추가했다.

```
2 × 12바이트 = 24바이트
```

실제 LSA 길이도 다음처럼 24바이트 증가했다.

```
60바이트 → 84바이트
```

# 17. Frame 31: R1도 새 Router-LSA 생성

R1의 기존 LSA는 다음과 같다.

```
Sequence Number : 0x80000008
LS Age          : 14
Length          : 60
Number of Links : 3
```

새로운 LSA에서는 다음처럼 변경된다.

```
Sequence Number : 0x80000009
LS Age          : 1
Length          : 72
Number of Links : 4
```

R1은 다음 Point-to-Point Link를 추가했다.

```
Link ID    : 2.2.2.2
Link Data  : 13.13.12.1
Link Type  : 1, Point-to-Point
Metric     : 64
```

Link Descriptor 한 개가 추가되면서 LSA 길이가 정확히 12바이트 증가했다.

```
60바이트 → 72바이트
```

# 18. Router-LSA 변경 전후 비교

## R1

```
변경 전

R1
├── 172.16.1.0/24     Stub, Cost 1
├── 13.13.10.0/24     Stub, Cost 10
└── 13.13.12.0/24     Stub, Cost 64
```

```
변경 후

R1
├── 172.16.1.0/24     Stub, Cost 1
├── 13.13.10.0/24     Stub, Cost 10
├── R2 2.2.2.2        P2P, Cost 64
└── 13.13.12.0/24     Stub, Cost 64
```

## R2

```
변경 전

R2
├── 13.13.20.0/24     Stub, Cost 10
├── R3 3.3.3.3        P2P, Cost 64
└── 13.13.23.0/24     Stub, Cost 64
```

```
변경 후

R2
├── 13.13.20.0/24     Stub, Cost 10
├── R3 3.3.3.3        P2P, Cost 64
├── 13.13.23.0/24     Stub, Cost 64
├── R1 1.1.1.1        P2P, Cost 64
└── 13.13.12.0/24     Stub, Cost 64
```

이제 Area 0 LSDB에는 R1과 R2가 실제 Router Link로 연결된 형태가 반영된다.

```
1.1.1.1 ── Cost 64 ── 2.2.2.2
```

# 19. OSPF Cost 분석

캡처된 Metric은 다음 세 종류다.

```
Cost 1
Cost 10
Cost 64
```

Cisco의 기본 Reference Bandwidth가 100Mbps라고 가정하면 다음처럼 해석할 수 있다.

```
Cost = Reference Bandwidth / Interface Bandwidth
```

따라서 Cost 64의 링크는 Cisco Serial 인터페이스의 기본 Bandwidth 값인 약 1.544Mbps를 사용하는 것으로 해석할 수 있다.

중요한 점은 OSPF가 실제 전송 속도를 실시간으로 측정하는 것이 아니라는 것이다.

```
실제 물리 속도 측정
→ 하지 않음

인터페이스 bandwidth 값 사용
→ OSPF Cost 계산
```

---

# 20. 7단계: LSAck

LSU를 받은 라우터는 해당 LSA를 정상적으로 수신했다는 사실을 알려야 한다.

이때 Link State Acknowledgment를 사용한다.

## Frame 34: R1의 LSAck

R1은 R2가 보낸 두 Router-LSA를 한 번에 확인한다.

```
R2 Router-LSA
Sequence: 0x80000006

R2 신규 Router-LSA
Sequence: 0x80000007
```

![image](/assets/image_0594ce8f-c031-40a1-87c0-559eaab35f78.png)

## Frame 35: R2의 LSAck

![image](/assets/image_7f34cd72-736f-4c55-9046-999e1f15e30f.png)

R2도 R1이 보낸 두 Router-LSA를 한 번에 확인한다.

```
R1 Router-LSA
Sequence: 0x80000008

R1 신규 Router-LSA
Sequence: 0x80000009
```

OSPF는 LSA 하나마다 반드시 즉시 독립적인 LSAck를 보내야 하는 것은 아니다.

여러 LSA Header를 하나의 LSAck 패킷에 모아서 전송할 수 있다.

```
LSA 수신
   ↓
잠시 ACK 대기
   ↓
여러 ACK를 하나의 패킷으로 결합
   ↓
제어 패킷 수 감소
```

이번 캡처에서도 각 LSAck가 두 개의 LSA Header를 담고 있다.

# 21. LSR, LSU, LSAck의 관계

세 패킷의 관계를 정리하면 다음과 같다.

```
LSR
“이 LSA가 필요하다.”

        ↓

LSU
“요청한 LSA를 전달한다.”

        ↓

LSAck
“해당 LSA를 정상적으로 받았다.”
```

DBD까지 포함하면 전체 과정은 다음과 같다.

```
DBD
LSA Header를 비교
        ↓
부족하거나 오래된 LSA 발견
        ↓
LSR
필요한 LSA 요청
        ↓
LSU
완전한 LSA 전송
        ↓
LSAck
수신 확인
```

---

# 22. LSU와 LSA를 혼동하면 안 되는 이유

LSU는 패킷이고 LSA는 그 안에 담기는 데이터 구조다.

```
Link State Update Packet
├── Number of LSAs
├── LSA 1
├── LSA 2
└── LSA 3
```

이번 캡처의 LSU에는 각각 하나의 Router-LSA가 들어 있다.

예를 들어 Frame 30의 길이 관계는 다음과 같다.

```
OSPF Header       24바이트
LSA Count          4바이트
Router-LSA        84바이트
---------------------------
OSPF Packet      112바이트
```

실제 Frame 30의 OSPF Packet Length도 112바이트다.

Cisco HDLC와 IPv4 Header를 포함하면 다음과 같다.

```
Cisco HDLC Header   4바이트
IPv4 Header        20바이트
OSPF Packet       112바이트
----------------------------
전체 Frame        136바이트
```

PCAP에서도 Frame 30의 길이는 정확히 136바이트다.

---

# 23. DBD는 전체 LSA를 전송하지 않는다

DBD 패킷에 포함된 것은 LSA Header다.

```
DBD
└── 20바이트 LSA Header들
```

완전한 LSA Body는 LSU에서 전달된다.

```
DBD
→ 내가 어떤 버전의 LSA를 가지고 있는지 알려 줌

LSR
→ 필요한 LSA를 선택해서 요청

LSU
→ 실제 LSA 내용 전달
```

OSPF가 이 구조를 사용하는 이유는 데이터베이스 전체를 무조건 복제하는 비용을 줄이기 위해서다.

---

# 24. 이번 캡처에서 확인되지 않은 LSA

이번 PCAP에서 완전한 형태로 전달된 LSA는 모두 다음 종류다.

```
LSA Type 1
Router-LSA
```

다음 LSA는 이번 캡처에 포함되어 있지 않다.

```
Type 2 Network-LSA
Type 3 Summary-LSA
Type 4 ASBR Summary-LSA
Type 5 AS-External-LSA
```

Type 2가 없는 이유는 해당 구간이 Point-to-Point Serial 링크여서 DR이 존재하지 않기 때문이다.

Type 3이 없는 이유는 캡처된 R1과 R2의 OSPF 패킷이 모두 Area 0이며, 이 구간에서 다른 Area의 Prefix 전달 과정이 포착되지 않았기 때문이다.

또한 R1과 R2의 Router-LSA Flags는 모두 0으로 확인된다.

```
B-bit: 0
E-bit: 0
V-bit: 0
```

따라서 이 캡처에서 R1과 R2는 자신을 ABR이나 ASBR로 표현하지 않는다.

---

# 25. 인접 관계 상태와 패킷 매핑

패킷 하나에 Neighbor State: Full이라는 필드가 직접 실리는 것은 아니다.

패킷의 순서와 DBD, LSR, LSU 교환 결과를 바탕으로 상태 변화를 해석해야 한다.

---

# 26. 인접 관계 형성과 LSA Flooding은 별개 과정이다

이번 캡처에서는 두 종류의 LSU가 연속해서 나타난다.

## 첫 번째 LSU: LSDB 동기화 목적

```
Frame 28
R1 Sequence 0x80000008

Frame 29
R2 Sequence 0x80000006
```

이 패킷들은 상대가 LSR로 요청한 기존 LSA를 전달한다.

## 두 번째 LSU: 토폴로지 변경 Flooding

```
Frame 30
R2 Sequence 0x80000007

Frame 31
R1 Sequence 0x80000009
```

이 패킷들은 새 인접 관계가 생겼기 때문에 새로 생성된 LSA다.

이를 구분하지 않으면 다음과 같이 오해할 수 있다.

```
“같은 Router-LSA를 왜 두 번 보내지?”
```

실제로는 목적이 다르다.

```
첫 번째 전송
→ 기존 LSDB 동기화

두 번째 전송
→ Full 인접 관계로 발생한 새로운 링크 상태 광고
```

---

# 27. 안정화 이후 Hello 패킷

프레임 36 이후에는 R1과 R2가 주기적으로 Hello를 교환한다.

각 Hello의 Neighbor 목록에는 상대 Router ID가 계속 포함된다.

```
R1 Hello
Neighbor: 2.2.2.2

R2 Hello
Neighbor: 1.1.1.1
```

이제 Hello는 Neighbor를 새로 발견하는 목적보다 기존 Neighbor의 생존 여부를 확인하는 Heartbeat 역할을 한다.

```
Hello 수신
→ Dead Timer 초기화

40초 동안 Hello 미수신
→ Neighbor Down 판단
→ Router-LSA 갱신
→ SPF 재계산
```

---

# 28. 캡처에서 확인한 전체 OSPF 동작 흐름

```
R1이 주기적으로 Hello 전송
        ↓
R2가 OSPF Hello 전송 시작
        ↓
서로의 Router ID를 Neighbor List에서 확인
        ↓
2-Way 상태
        ↓
DBD Initial 패킷 교환
        ↓
Router ID가 높은 R2가 Master
        ↓
DBD Sequence Number로 LSDB Header 목록 교환
        ↓
R2는 R1의 최신 LSA가 필요함을 확인
R1은 R2의 최신 LSA가 필요함을 확인
        ↓
서로 LSR 전송
        ↓
LSU로 요청받은 Router-LSA 전달
        ↓
LSDB 동기화
        ↓
Full 인접 관계 형성
        ↓
각 라우터가 새 Point-to-Point Link를 반영
        ↓
Router-LSA Sequence Number 증가
        ↓
새 Router-LSA Flooding
        ↓
LSAck
        ↓
주기적인 Hello로 Neighbor 유지
```

---

# 29. Wireshark에서 재현할 필터

전체 OSPF 패킷만 확인한다.

```
ospf
```

IP Protocol Number 89로 확인한다.

```
ip.proto == 89
```

R1이 보낸 OSPF 패킷만 확인한다.

```
ospf && ip.src == 13.13.12.1
```

R2가 보낸 OSPF 패킷만 확인한다.

```
ospf && ip.src == 13.13.12.2
```

협상 핵심 구간만 확인한다.

```
ospf && frame.number >= 15 && frame.number <= 35
```

Hello 패킷을 확인한다.

```
ospf.msg == 1
```

DBD 패킷을 확인한다.

```
ospf.msg == 2
```

LSR 패킷을 확인한다.

```
ospf.msg == 3
```

LSU 패킷을 확인한다.

```
ospf.msg == 4
```

LSAck 패킷을 확인한다.

```
ospf.msg == 5
```

Wireshark 버전에서 특정 필드명이 다르게 보인다면 패킷 상세 창의 해당 필드를 우클릭한 뒤 Apply as Filter를 사용하면 된다.

# 31. 최종 분석 결과

이번 PCAP은 OSPF가 단순히 Hello 패킷 몇 개를 교환한 뒤 바로 경로를 설치하는 프로토콜이 아니라는 사실을 보여 준다.

OSPF는 다음 세 단계를 분리해서 수행한다.

## Neighbor 발견

```
Hello
→ 상대 존재 확인
→ 양방향 통신 확인
```

## 데이터베이스 동기화

```
DBD
→ 보유 LSA 목록 비교

LSR
→ 필요한 LSA 요청

LSU
→ 실제 LSA 전달
```

## 토폴로지 변화 Flooding

```
Full Neighbor 형성
→ 새로운 링크 상태 발생
→ Router-LSA 재생성
→ Sequence Number 증가
→ LSU Flooding
→ LSAck
```

이번 캡처에서 가장 중요한 장면은 Frame 30과 31이다.

R1과 R2는 단순히 상대의 기존 LSA를 받아 데이터베이스를 맞추는 데서 끝나지 않았다.

새로운 Full 인접 관계 자체가 토폴로지의 변경이므로 자신들의 Router-LSA를 다시 생성했다.

```
R2
0x80000006 → 0x80000007
3 Links → 5 Links

R1
0x80000008 → 0x80000009
3 Links → 4 Links
```

이 과정에서 LS Age는 1로 초기화되고, 새로운 Point-to-Point Neighbor Link가 Router-LSA에 추가되었다.

즉, OSPF 인접 관계 형성은 다음 결과를 만든다.

```
Neighbor Table 변화
        ↓
Router-LSA 변화
        ↓
LSDB 변화
        ↓
SPF 계산
        ↓
라우팅 테이블 변화
```

OSPF의 핵심은 라우팅 테이블을 서로 복사하는 것이 아니다.

각 라우터가 LSA를 이용해 동일 Area의 토폴로지 지도를 만들고, 그 지도에서 자신을 루트로 SPF 계산을 수행하는 것이다.

https://velog.io/@hsshin0602/컴퓨터-네트워크-MPLSMultiprotocol-Label-Switching

https://www.qsfptek.com/ko/qt-news/osfp-vs-bgp-choosing-the-right-routing-protocol?srsltid=AfmBOoq9NZzHSccLtY4HYAk82Ri5ENGOIcZ2WhNzWZc-i4Bc7p9c3Iul

https://velog.io/@adoo24/AIOps-Agent-실전-구축기-RCA-시간을-93-단축한-방법

https://www.netmanias.com/ko/post/blog/5462/lte-mpls-network-protocol-vpn/the-design-of-lte-over-mpls-l3vpn-network-part-1-concept