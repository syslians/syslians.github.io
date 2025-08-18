---
layout: post
title: "라우팅 프로토콜"
date: 2025-08-05 22:00:00 +0900
categories: [네트워크, 라우팅, 정적 라우팅, OPSF, RIP, BGP]
author: cotes
published: true
---

### 라우팅
인터넷에서 통신이 가능하다는 것은, 내부적으로 수많은 라우터들이 패킷을 순차적으로 전달(Packet forwarding)하여 최종적으로 목적지 서버에
도달하는 일련의 과정을 의미합니다. 이를 라우팅(Routing)이라고 부릅니다.

라우팅 방식은 크게 Static Routing과 Dynamic Routing 두 가지로 나눌 수 있습니다.
- Static Routing은 네트워크 장비 관리자가 직접 라우터에 접속하여, 목적지 네트워크로 가능 경로를
  일일이 지정해주는 방식입니다.
- Dynamic Routing은 라우터들이 서로 정보를 교환하고 알고리즘을 기반으로 경로를 자동으로 계산하는 방식
  입니다.

규모가 작을때는 Static Routing도 가능하지만, 네트워크 규모가 커질수록 Dynamic Routing이 훨씬 효율적이고
관리하기 용이합니다.

| 구분         | Static Routing                                            | Dynamic Routing                                            |
| ---------- | --------------------------------------------------------- | ---------------------------------------------------------- |
| **구성 방식**  | 관리자가 수동으로 경로(next hop) 지정                                 | 라우터가 알고리즘(RIP, OSPF, EIGRP 등)으로 자동 계산                      |
| **설정 난이도** | 간단한 소규모 네트워크에 적합                                          | 초기 설정은 복잡하지만 대규모 네트워크에 적합                                  |
| **유연성**    | 경로 변경 시 수동 수정 필요                                          | 네트워크 변화 시 자동으로 최적 경로 재계산                                   |
| **트래픽 부하** | 라우팅 정보 교환이 없어 오버헤드가 없음                                    | 라우팅 정보 교환으로 오버헤드 발생 가능                                     |
| **장점**     | - 단순한 구조에 적합<br>- 보안성 높음(라우팅 정보 교환 없음)<br>- 리소스 소모가 거의 없음 | - 대규모 네트워크에 적합<br>- 장애 발생 시 자동 경로 우회<br>- 관리 효율적           |
| **단점**     | - 네트워크 확장성 낮음<br>- 장애 시 수동 조치 필요<br>- 관리 복잡성 증가           | - 초기 설정 복잡<br>- 라우팅 프로토콜 오버헤드 존재<br>- 리소스(CPU, 메모리) 사용량 증가 |


### Static Routing 
관리자가 직접 라우터에 명령어를 입력하여, 특정 목적지 네트워크로 가는 다음 홉(Next Hop)라우터 또는 출구 인터페이스를
지정하는 방식

![Bit Operations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Ft1.daumcdn.net%2Fcfile%2Ftistory%2F997468415D46908212)
[정적 라우팅 토폴로지]

```shell
Router(config) # ip route <목적지 네트워크> <서브넷 마스크> <다음 홉 IP>
```
ex(Cisco ios)

### 장점
- 단순하고 직관적이며 소규모 네트워크에 적합. 
- 라우터 간에 라우팅 정보 교환이 없으므로 네트워크 오버헤드가 최소화.
- 관리자가 지정한 경로로만 트래픽이 전달되므로 예측 가능성이 높음.

### 단점
- 네트워크 변경(링크 다운 등)시 자동으로 경로 갱신이 불가능.
- 수십 ~ 수백대의 라우터를 관리하기가 힘드므로 규모 확장에 한계가 명확.
- 관리자가 직접 모든 변경을 적용해야 하므로 운영 비용이 증가.

## 실제 사용 사례
- 소규모 네트워크 (예: 지점망, 단일 라우터 구성)
- 백업 경로(Backup Route)로 사용 -> Dynamic Routing 실패 시 대비
- 특정 트래픽에 대해 보안적 목적으로 경로를 고정할 때 사용

### Dynamic Routing
동적 라우팅은 내부 라우팅(Inner Gateway Protocol)과 외부 라우팅(External Gateway Protocol)로 나뉩니다.
![Bit Operations](https://velog.velcdn.com/images/yh_lee/post/160b93ca-c810-4b09-94d1-7ae96003f761/image.png)
- 내부 라우팅(IGP): 같은 AS 내부의 라우팅 정보를 교환하는 프로토콜
- 외부 라우팅(EGP): 다른 AS 간의 라우팅 정보를 교환(다른 AS와 연결)하는 프로토콜

**AS(Autonomius System)란?**
- AS Number(망 식별번호): 각각의 자율시스템을 식별하기 위한 인터넷 상의 고유번호
- 하나의 그룹/기관/회사 같이 동일한 라우팅 정책으로 하나의 관리자에 의해 운영되는 네트워크

### RIP(Routing Information Protocol)
- 최소 Hop Count를 파악하여 라우팅하는 프로토콜
- 거리와 방향으로 길을 찾아가는 Distance Vector 다이나믹 프로토콜
- 최단거리 즉, Hop Count가 적은 경로를 택하여 라우팅하는 프로토콜로 Routing Table에 인접 라우터 정보를 저장하여 경로를 결정.
- 최대 Hop Count는 15로 거리가 짧기 때문에 IGP로 많이 이용하는 프로토콜.
- 라우터의 메모리를 적게 사용하며, 30초 마다 라우팅 정보를 업데이트.
- Hop Count가 낮을수록 좋은 경로, 소규모 네트워크에서 간편하게 구성 가능.
- 직접 연결되어 있는 라우터는 hop으로 계산하지 않고 30초 주기로 default routing을 업데이트하여 인접 라우터로 정보를 전송.
- 4 ~ 6개까지 로드밸런싱이 가능.
- 주로 UDP 세그먼트에 캡슐화 되어 있음.
- RIP는 단순 hop을 count하여 경로를 결정하기 때문에 경로의 네트워크 속도는 판단하지 않는다. 비효율적인 경로로 패킷을 전달할 가능성이 있다.
- Distance Vector 알고리즘으로 네트워크 변화에 대처하는 시간(컨버전스 타임)이 느리다는 단점이 있다.

**Bellman Ford 알고리즘(Distance Vector)**
- 비용(metric): 홉 수(Hop Count) - 목적지까지 거치는 라우터 수
  
- 방정식  
$$D_x(y) = \min\limits_{v \in N(x)} [c(x,v) + D_v(y)]$$

- $D_x(y)$: 노드 x에서 목적지 y까지의 최소 비용
- $c(x, y)$: x에서 인접 노드 v까지의 링크 비용(홉 수 1)
- $N(x)$: x의 인접 노드 집합
- RIP는 이 계산을 주기적으로(기본 30초) 수행



### BGP(Border Gateway Protocol)
- BGP는 외부 라우팅 프로토콜(EGP) AS(관리 도메인)와 AS 간에 사용되는 라우팅 프로토콜.
- 정해진 정책에 따라 최적 라우팅 경로를 수립.
- 경로벡터(Distance Vector) 방식의 라우팅 프로토콜로 다른 IGP보다 컨버전스는 느리지만 대용량의 라우팅 정보를 교환할 수 있다.
- TCP 포트 179번을 통해 인접 라우터들과 이웃(Neighbor) 관계를 성립, 이웃 노드 간에는 유니캐스트 라우팅 업데이트를 실시.
  (유니캐스트 라우팅 프로토콜: 최적의 경로를 찾아내는 프로토콜. 하나의 Sender와 하나의 Receiver 간의 통신을 의미하며 One-to-One 통신이라고 합니다.)

### OSPF(Open Shortest Path First)
OSPF(Open Shortest Path First)는 링크 상태(link-state) 방식의 IGP 이며, 표준 라우팅 프로토콜 입니다. 
각 라우터는 인접 링크 상태정보를 LSA(Link State Advertisement)로 교환하여 전체 네트워크 토폴리지를 학습합니다. 모든 라우터가 동일한 링크 상태 
데이터베이스(LSDB)를 보유하며, 변화가 생기면 해당 LSA만 멀티캐스트로 전파하여 부분 갱신을 합니다. 
최적 경로를 계산할때 SPF(Shortest path First) 또는 다익스트라(dijkstra) 알고리즘을 이용하여
각 목적지까지의 최적 경로를 계산합니다. Mecric costs는 대역폭(Bandwidth)을 사용합니다. AD값은 110

![Bit Operations](https://velog.velcdn.com/images/yh_lee/post/029358c6-7794-4c21-a1f0-3ffda2587405/image.png)

라우터들은 Area(영역) 개념으로 네트워크를 계층화하며, 백본 영역(Area 0)을 중심으로 각 Area가 연결됩니다.

**Dijkstra 알고리즘(Link state 방식)**
- 비용(metric): 인터페이스 대역폭을 기반으로 한 비용
  
  $Cost = \frac{Reference Bandwidth}{Interface Bandwidth}$

예: Reference BW =  100 Mbps, Interface BW = 10 Mbps -> Cost = 10
- 방정식 (Dijkstra의 핵심 단계)
  
  $SPF(s)=\min\limits_{p \in P(s,t)}\sum\limits_{(u, v) \in p}c(u, v)$

  - p: 가능한 경로 집합
  - c(u, v): 링크(u, v)의 비용
  - OSPF는 네트워크 전체 토폴리지를 알고 있기 때문에 한 번에 전체 최단 경로 트리를 계산
    

### OSPF의 장점

1. OSPF는 area 단위로 구성되어 대규모 네트워크를 안정되게 운영할 수 있음
   특정 area에서 발생하는 상세한 라우팅 정보가 다른 area로 전송되지 않아 큰 규모에서 안정되게 운영할 수 있습니다.

2. Stub 이라는 강력한 축약 기능
   기존 라우팅 프로토콜과는 달리 IP 주소가 연속되지 않아도 Routing table의 크기를 획기적으로
   줄일 수 있습니다.

3. Convergence time이 전반적으로 빠른편임.

### OSPF의 네트워크 분류
- 동작 방식 및 설정이 다름
- 아래 설명에는 없지만 Point-to-access 라는게 하나 더 있음.
![Bit Operations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FrCclL%2FbtqA1Ata3vH%2FAAAAAAAAAAAAAAAAAAAAAPSHMMwHoc_HofxyuYgkZIirY5zInE9KVuJtF7v3gGG7%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1756652399%26allow_ip%3D%26allow_referer%3D%26signature%3D47J63rp5a79OEqBPUahJAxYlZng%253D)

### Broadcast Multi Access
- 하나의 Broadcast 패킷을 전송할 경우 동일 네트워크 상의 모든 장비에게 전달되는 네트워크를
  Broadcast 네트워크, 하나의 인터페이스를 통해 다수의 장비와 연결된 네트워크를 Multi Access
  네트워크라고 합니다.

![Bit Operations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FtAQhs%2FbtqA4yOuahe%2FAAAAAAAAAAAAAAAAAAAAAOtXol-Zt1qZR6iaKWJ2kU53glh9leX3hZqRlypcxjuk%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1756652399%26allow_ip%3D%26allow_referer%3D%26signature%3Dolx2tGwCUBn03MfhjwG3q%252B%252FJJNM%253D)

### Non Broadcast Multi Access (NBMA)
- Broadcast가 지원되지 않는 Multi Access 네트워크를 의미. (ex: ATM, X.25, Frame Relay)
- 대부분 내부에 Virtual Circuit (가상 회로) 방식을 사용
- NBMA 에서는 Broadcast를 사용하여 전송할 경우 가상회로 하나당 하나씩 Broadcast packet을 전송해야함.

![Bit Operations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FbhNO2G%2FbtqA6o5p3zF%2FAAAAAAAAAAAAAAAAAAAAAMHm5YVG3OALRTO4pkxs_oPjHrSIvv-peQEfcc4LeW_O%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1756652399%26allow_ip%3D%26allow_referer%3D%26signature%3Dk04O62rcpJVJRZ4X7J0mfLq9q1s%253D)

### Point-to-Point
하나의 인터페이스와 연결된 장비가 하나뿐인 네트워크 (ex: HDLC, PPP, F/R의 sub interface 중 point-to-point)
![Bit Operations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FnfyQz%2FbtqA3eQhKoF%2FAAAAAAAAAAAAAAAAAAAAAB1w2Ji5KzNYUkbdjZDTopsSIl7g8aAGxKxJwdcvsE5Y%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1756652399%26allow_ip%3D%26allow_referer%3D%26signature%3DCpIztzv7zkUBF0Vn4u1Wfz2QfOY%253D)

### OSPF의 패킷
1. OSPF를 설정한 Router 끼리 hello packet을 교환해서 Neighbor 혹은 adjacent Neighbor를 맺음.
   - adjacent Neighbor: 라우팅 정보(LSA)를 교환하는 이웃
   - LSA(Link State Advertisement): OSPF 에서의 라우팅 정보

2. adjacent neighbor인 라우터간 라우팅 정보(LSA)를 서로 교환하고 전송받은 LSA를 Link-state-Database에 저장

3. LSA를 모두 교환하고 SPF(Shortest Path First) 또는 diikstra 알고리즘을 이용하여 각 목적지까지의 최적 경로 계산 후
   Routing table에 올림

4. 그 후에도 주기적으로 hello packet을 교환하면서 정상 동작중인지 확인

5. 네트워크의 상태가 변하면 다시 위의 과정을 반복하여 Routing table 생성

패킷의 종류로는 Hello, DBD, LSR, LSU, LSAck 패킷이 있습니다.

### Hello Packet
- OSPF가 설정된 인접한 라우터간 Neighbor 관계를 형성하고 Neighbor 관계를 유지하는데 사용
- OSPF가 설정된 인터페이스로 서로 hello packet을 교환하여 Neighbor 관계를 맺음
- Neighbor를 맺은 후에도 일정 주기(hello 주기)로 hello 패킷을 전송하고 정해진 주기 안에(dead 주기)
  상대방에게 hello 패킷을 수신받지 못하면 해당 Neighbor에 문제가 생긴걸로 간주하고 Neighbor 관계를 끊음
- Router-id, area id, 인증 암호, 서브넷 마스크, hello 주기, dead 주기, stub area flag, Router Priority
  DR, BDR, Neighbor list의 정보를 가지고 있음

### DBD (Database Description) packet
- OSPF의 네트워크 정보를 LSA(Link-state adcertisement)라고 부르는데, OSPF는 자신이 만든 LSA와 Neighbor에게
  받은 LSA를 Link-state DataBase에 저장함.
- DBD는 OSPF 라우터의 Link state 데이터베이스에 있는 LSA들의 요약된 정보를 알려주는 패킷. 즉, Neighbor간 LSA
  를 교환하기 전에 자신의 link state 데이터베이스에 있는 요약된 LSA 목록을 상대방에게 알려주기 위해 사용.

### LSR (Link State Request)Packet
- Neighbor에게 전송받은 DBD에 자신의 link state 데이터베이스에 정보가 없는 네트워크가 있다면 그 네트워크에 대한 상세정보
  (LSA)를 요청할 때 사용되는 패킷

### (Link State Update)LSU Packet
- Neighbor에게 LSA를 요청받는 LSR을 받거나 자신이 알고 있는 네트워크의 상태가 변했을 경우(Link Down시) 해당 라우팅 정보를 전송할 때
  사용하는 패킷 (즉, LSA를 실어나를 때 사용)

### LSAck Packet
- OSPF 패킷을 정상적으로 수신했음을 알려줄 때 사용. (DBD, LSR, LSU 패킷을 수신하면 LSAck 패킷을 사용하여 수신받았음을
  상대방에게 전달. 신뢰성을 보장하기 위해)
  
| 패킷 종류     | 목적             | 주요 역할        |
| --------- | -------------- | ------------ |
| **Hello** | Neighbor 발견/유지 | 라우터 인접 관계 형성 |
| **DBD**   | LSDB 요약 교환     | "목차" 교환      |
| **LSR**   | 필요한 LSA 요청     | 부족한 정보 요청    |
| **LSU**   | LSA 전달         | 링크 상태 정보 플러딩 |
| **LSAck** | LSA 수신 확인      | 신뢰성 보장       |

### 핵심 내용 정리
라우팅은 패킷의 최적 경로를 결정하는 과정으로, 정적 라우팅은 단순하지만 유연성이 부족하고, 동적 라우팅은 OSPF, RIP, EIGRP 같은 
프로토콜이 자동으로 최단 경로를 계산합니다. 특히 OSPF는 링크(회선) 상태 방식을 사용해 네트워크 전체 토폴리지를 공유하고, DR/BDR
선출과 SPF 알고리즘을 통해 효율적이고 안정적인 라우팅을 제공합니다.


### OSPF의 Neighbor 테이블과 데이터베이스 테이블

1. **OSPF Neighbor Table**
   OSPF가 설정된 Router 간에 인접관계를 성립한 Neighbor 정보 저장, 주기적으로 hello packet을 교환하여 Neighbor
   관계 유지 여부 확인. (show ip ospf neighbor)
   ![Bit Operations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FnUgad%2FbtqA4AyQ7Cl%2FAAAAAAAAAAAAAAAAAAAAAJ3G50MblHc1RDIgH_wZ9Z6VA8s_DFMV6g1-akXAvzX_%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1756652399%26allow_ip%3D%26allow_referer%3D%26signature%3DRn8v%252BTnSbGvwKxRqVCJI2vnimUo%253D)

3. **OSPF Neighbor Table State**
   - show ip ospf database
   Down 상태에서 시작해서 Neighbor와 Routing 정보 교환을 끝내고 Full 상태로 완료.

1-1. **Down 상태**: OSPF가 설정되고 hello packet을 전송했지만 상대 라우터가 아직 내가 보낸 hello packet을 받지 못한 상태.

1-2. **init 상태**: 근접 라우터에게 hello packet을 받았지만 상대 라우터가 아직 내가 보낸 hello packet을 받지 못한 상태.(상대방이
       전송한 hello packet 안의 Neighbor 리스트에 내 router-id가 없는 경우)
       
1-3. **Two-way 상태**: Neighbor와 양방향 통신이 이루어진 상태. Multi Access 네트워크일 경우 이 단계에서 DR/BDR 선출
       (서로 전송한 hello packet안의 Neighbor list에 서로의 router-id가 없는 경우)
       
1-4. **Extrast 상태**: adjacent neighbor가 되는 첫 번째 단계. master와 slave 라우터를 선출. (router-id가 높은 라우터가 master)
  
1-5. **Exchange 상태**: 각 라우터가 자신의 Link-state database에 저장된 LSA의 Header 만을 DBD packet에 담아 상대방에게 전송 (DBD packet
     을 수신한 라우터는 자신의 데이터베이스 내용과 비교한 후 자신에게 없거나 자신의 것보다 더 최신 정보일 경우 상대방에게 상세정보(LSA)를 요청하기
     위해 Link state request list에 기록하고, DBD packet의 정보에 자신이 모르는 정보가 없다면 바로 Full 상태가 됨)
     
1-6. **Loading 상태**: DBD Packet 교환이 끝난 후 자신에게 없는 정보를 LSR packet으로 요청 함. LSR을 요청받은 라우터는 정보를 LSU packet
    으로 요청함. LSR을 요청받은 라우터는 정보를 LSU Packet에 담아서 전송해준다.
    
1-7. **Full 상태**: adjacent neighbor간 라우팅 정보 교환이 모두 끝난 상태.

3. OSPF Database Table
   라우팅 업데이트 정보를 관리하는 테이블
![Bit Operations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2Fl3d6s%2FbtqA3eCL9DX%2FAAAAAAAAAAAAAAAAAAAAAEgNU0vsvqpgIXcerBFgs6A9_HPiT6KUCi30yB5ohPUS%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1756652399%26allow_ip%3D%26allow_referer%3D%26signature%3D4hJXpjDa7Lht866RG%252FDye4usjhY%253D)

### OSPF의 동작 과정 (DR/BDR 선출)
1. DR/BDR 선출 기준
   - 우선순위(OSPF Priority)가 가장 높은 라우터가 DR(Designed Router)로 선출됨
   - 그 다음으로 높은 라우터가 BDR(Backup Designated Router)로 선출됨
   - 우선순위가 동일할 경우 Router-ID가 높은 라우터가 DR/BDR이 됨
     
2. 선출 이후의 규칙
   - DR/BDR이 한 번 선출되면, 더 높은 우선순위를 가진 라우터가 나중에 추가되더라도 기존 DR/BDR은 변경되지 않음
   - DR이 다운되면 BDR이 자동으로 DR로 승격되며, 새로운 BDR을 다시 선출함
   - DR, BDR이 아닌 나머지 라우터는 DROther라고 호칭
     
3. DR/BDR 선출 이유
   - Ethernet, NBMA(Non-Broadcast Multi Access) 같은 멀티 엑세스 네트워크 환경에서는 라우터가 1:1로 LSA를 교환하면 중복된
     LSA 및 ACK 패킷이 과도하게 발생
   - 이를 방지하기 위해 중앙 중계자 역할을 하는 DR을 선출하고, DR 장애 대비용으로 BDR을 함께 선출
   - DR/BDR은 Broadcast 및 Non-Broadcast 네트워크에서만 사용됨
   - Point-to-Point 네트워크에서는 필요하지 않아 DR/BDR 선출이 이루어지지 않음

![Bit Operations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FcSPcuz%2FbtqA2N6HBpX%2FAAAAAAAAAAAAAAAAAAAAACPJp6ZS63AYCMKtzfy4Vt0XN9d5InchXdTudjYDdmHn%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1756652399%26allow_ip%3D%26allow_referer%3D%26signature%3Df91xrc5vZAPaSEM3HoMykx82OCQ%253D)

-> 중계 역할을 하는 DR(Designated Router)를 선출하고, DR에 문제가 발생할 경우를 대비하여 Backup용으로 BDR(Backup DR)을 선출
-> DR, BDR은 Broadcast 및 Non Broadcast 네트워크에서만 사용 (Point-to-Point 네트워크에서는 사용하지 않음)

![Bit Operations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FEbl2i%2FbtqA2Vjd5Ww%2FAAAAAAAAAAAAAAAAAAAAAC7TwW7m_0KQGX4jxhz4Y_mawcUzUJuW8629T0JfxqPl%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1756652399%26allow_ip%3D%26allow_referer%3D%26signature%3Dw9fZKCLz1UZRFu3MKKJrgXwe8qE%253D)

1. adjacent neighbor
 - OSPF에서 라우팅 정보(LSA)를 서로 교환하는 neighbor를 adjacent neighbor 라고 함
(1) DR과 다른 라우터
(2) BDR과 다른 라우터
(3) Point-to-Point 네트워크로 연결된 두 라우터
(4) Point-to-Multipoint로 연결된 두 라우터
(5) Virtual-link로 연결된 두 라우터

 
2. OSPF 메트릭
 - OSPF 메트릭은 cost라고 부름
 - 10^8/banddwidth(bps) = cost
 - 코스트 계산 시 소수점 이하는 전부 버리고, 1미만은 1로 계산
 - 인터페이스에서 명령어로 코스트를 변경할 수 있음 (ip ospf cost ?)
   
 
3. OSPF area
 - OSPF는 복수개의 Area로 나눠서 설정
 - 규모가 작은 경우 하나의 Area만 사용해도 상관 없음
 - Area가 하나일 경우 아무 번호나 사용해도 상관 없지만, Area가 두 개 이상일 경우 하나는 반드시 0으로 설정 해야 함
 - Area 0은 Backbone Area (다른 Area는 Area 0과 물리적으로 연결 되어야 함)
  -> Backbone Router : Backbone Area (Area 0)에 소속된 라우터
  -> Internal(내부) Router : 하나의 Area에만 소속된 라우터
  -> ABR (Area Border Router) : 두 개 이상의 Area에 소속된 Area 경계 라우터
  -> ASBR (AS boundary Router) : OSPF 네트워크와 다른 라우팅 프로토콜이 설정된 네트워크를 연결하는 AS 경계 라우터

![Bit Operations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FbwNTSO%2FbtqA2b7Rhaw%2FAAAAAAAAAAAAAAAAAAAAAOAdfvDo_YKKhPYPky90aW1ThTQZ-Vt1NzhnpLSdENcU%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1756652399%26allow_ip%3D%26allow_referer%3D%26signature%3D2RuIrmvAAW05gPjfPzzO1jM6bvE%253D)
| OSPF 상태 (Neighbor State) | 주요 동작                     | 사용 패킷                        |
| ------------------------ | ------------------------- | ---------------------------- |
| **Down**                 | 초기, Hello 송신              | Hello                        |
| **Init**                 | Hello 수신 (상대는 나 모름)       | Hello                        |
| **2-Way**                | 서로 Neighbor 확인, DR/BDR 선출 | Hello                        |
| **ExStart**              | Master/Slave 협상           | DBD 시작                       |
| **Exchange**             | DBD 교환 (LSA 요약본 공유)       | DBD                          |
| **Loading**              | LSA 요청/갱신/확인              | LSR, LSU, LSAck              |
| **Full**                 | LSDB 동기화 완료, SPF 계산       | Hello (주기), LSU/LSAck (변경 시) |

- Hello -> Neighbor 발견 및 유지
- DBD -> "내가 가진 라우팅 요약 정보" 교환
- LSR/LSU/LSAck -> "부족한 LSA 요청,전송,확인"
- Full State -> 최종적으로 라우팅 정보 일치 


### OSPF 설정 방법

1) 기본 설정
- router ospf [process-id]
   - 하나의 라우터에 여러개의 OSPF를 설정할 때 구분하기 위한 값이기 때문에 다른 라우터들끼리 달라도 상관이 없음
- router-id x.x.x.x 
   최적의 경로를 누가 알려줬는지 파악하기 위해 필요, 일반적으로 가장 작은 IP를 설정하기 때문에 loop back 같은곳에 IP를 넣고 설정
- network [네트워크대역] [와일드마스크] area [area number]
 
2) 축약 설정
 - ABR 또는 ASBR에서만 축약 가능
 - router ospf [process-id]
 - area [축약하고싶은 area number] range [N/W IP] [wildcard mask]
 
 3) 재분배
 - ASBR 에서 재분배 설정을 해야 함
 - 모두 통신이 되기 위해선 다른 프로토콜을 사용하는 인터페이스와 OSPF를 사용하는 인터페이스 모두 재분배를 해주어야 양방향 통신 가능

 OSPF가 EIGRP를 알 수 있도록 OSPF에 재분배 설정 방법
  -> router ospf [process-id]
  -> redistribute [반대편 프로토콜] [AS number] subnets

 EIGRP가 OSPF를 알 수 있또록 EIGRP에 재분배 설정 방법
  -> router eigrp [AS number]
  -> redistribute [반대편 프로토콜] [process number] metric [Bandwidth값] [delay값] [reliability값] [load값] [MTU값]

 직접 연결된 대역대를 OSPF에게 재분배
  -> router ospf [process-id]
  -> redistribute connected subnets


### 내용 정리 및 가상 면접 질문

### OPSF Neighbor 상태에서 Init과 2-way 단계의 차이를 설명해보세요.
- Follow-up: 왜 2way 단계에서 DR/BDR 선출이 이루어지나요?

### 두 라우터가 OSPF Hello 패킷을 주고받고 있는데 2-way 상태에서 더 이상 진행되지 않습니다. 원인이 될 수 있는 문제는 무엇일까요?
- 힌트: 네트워크 타입(Point-to-Point / Broadcast), DR/BDR 문제, 인증 불일치, Hello/Dead Timer 불일치 등

### OSPF에서 Database Descripton(DBD) 패킷과 Link State Update(LSU) 패킷은 각각 언제 사용되나요?
- Follow-up: DBD 교환 과정에서 Master/Slave 역할은 어떻게 결정되나요?

### OSPF 라우터가 FULL 상태에 도달하면 어떤 과정을 통해 최적 경로를 계산하나요?
- 모든 라우터가 LSDB를 통해 동기화 -> SPF 알고리즘 실행 -> Routing table 업데이트

### 현재 네트워크에서 OSPF 인접 관계가 ExStart 단계에서 멈춰있습니다. 이 경우 어떻게 트러블 슈팅을 하는게 좋을까요?
- MTU 불일치, Router-ID 충돌, 패킷 손실 여부 확인, 디버그 명령어 활용 등

출처: https://nirsa.tistory.com/32, https://velog.io/@yh_lee/%EB%9D%BC%EC%9A%B0%ED%8C%85-%ED%94%84%EB%A1%9C%ED%86%A0%EC%BD%9C-RIP-BGP-OSFP







