---
layout: post
title: "Router to Switch 통신 문제(VMware, GNS) 분석 및 해결"
date: 2025-08-22 22:00:00 +0900
categories: [Router, Switch, Routing, L2, L3, GNS, VMware, Protocol,]
author: cotes
published: true
---


<img width="800" height="500" alt="image" src="https://github.com/user-attachments/assets/8cba3a21-f3e0-4366-ae5e-252939c6b0b4" />

`https://github.com/user-attachments/assets/8cba3a21-f3e0-4366-ae5e-252939c6b0b4`

## CSMA / CD

### CSMA (Carrier Sense Muliple Access)
전송하기 전에 채널이 비어있는지(캐리어 감지) 확인.

### CD(Collison Detection)
전송 중 충돌이 발생하면 이를 감지하고, 랜덤한 시간 후 재전송(backoff)


이더넷이 프레임을 전송하는 방식은 duplex mode가 Half인가 Full 인가에 따라 다릅니다. Half-duplex는 데이터의 
송신과 수신을 동시에 할 수 없는 통신방식을 의미합니다. 즉, 데이터를 수신하고 있을 때에는 송신이 불가능하고, 수신할 때에는
송신이 불가능 합니다. 그러나, Full-duplex 모드에서는 프레임의 송신과 수신을 동시에 할 수 있습니다.
Half duplex로 동작하는 링크에서 이더넷이 프레임을 전송하는 절차는 다음과 같습니다.

1) 프레임을 전송하기 전에 현재 전송되고 있는 프레임이 있는지 확인합니다. 이 과정을 캐리어 센스(carrier sense)라고 합니다.
   전송중인 프레임이 없으면 자신의 프레임을 케이블상으로 전송합니다. 만약, 전송중인 프레임이 있으면 기다립니다.

2) 이처럼 전송할 프레임을 가진 모든 이더넷 장비는 언제라도 캐리어 센싱을 한 다음 자신의 프레임을 전송할 수 있는데, 이를
   Multiple Access라고 합니다.

3) 이더넷은 복수개의 장비가 동시에 프레임을 전송할 수 있고, 이 경우 충돌이 일어날 수 있으므로, 프레임 전송후에는 항상 충돌발생
   여부를 확인합니다. 이것을 Collision Detection 이라고 합니다. 만약, 충돌이 발생하면 임의의 시간동안 기다렸다가 다시 전송합니다.

Half duplex 네트워크에서 데이터 전송량이 많을 때 프레임 충돌이 많이 발생합니다. 이더넷 장비들은 충돌 발생시 최대 15회까지
재전송을 시도하고, 그래도 실패하면 해당 프레임의 전송을 포기합니다. 이상에서 설명한 이더넷 동작방식을 줄여서 CSMA/CD라고 합니다.

### Full Duplex Mode 에서의 이더넷 동작
풀 듀플렉스 모드로 동작하는 링크는 프레임의 송신과 수신이 서로 다른 채널을 통하여 이루어지므로 충돌이 발생해도 
충돌이 발생할 염려가 없습니다. 송신할 프레임이 있는 장비는 항상 송신할 수 있으며, 송신후에 충돌감지도 하지 않습니다.
따라서, Full Duplex 모드에서의 이더넷 동작방식은 CSMA/CD가 아닙니다. 이더넷의 최소 길이의 프레임을 전송하는데 걸리는
시간을 Slot time 이라고 합니다.

CSMA/CD 방식에서는 slot time 이내에 프레임의 충돌을 감지할 수 있어야 하기 때문에 케이블의 길이가 제약됩니다. 그러나, 
Full duplex 모드에서는 충돌감지를 하지 않으므로 slot time에 제약을 받지 않습니다. 결과적으로 케이블의 길이를 확장할 수 있어
장거리 전송이 가능합니다.

Full duplex 모드에서는 송신과 수신이 별개의 채널로 이루어지기 때문에, 송수신 트래픽의 양이 동일하다면 half-duplex 보다 속도가
2배나 더 빠릅니다. 현재 10Mbps로 동작하는 10Base-T를 비롯하여 모든 상위 전송속도의 이더넷에서 Full duplex 모드를 지원합니다. 
허브와 연결된 장비들은 Full duplex가 지원되지 않습니다.

### 이더넷 헤더
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/19a63c8e-538c-4b90-a7e8-43035f279f97" />

`https://github.com/user-attachments/assets/19a63c8e-538c-4b90-a7e8-43035f279f97`

구성 요소
- Preamble: 프레임 시작을 알리는 동기화 비트 패턴으로, 수신 측에서 프레임의 시작을 인식할 수 있게 합니다.

- Destination MAC: 수신할 장치의 물리적 주소인 MAC 주소를 나타냅니다. 목적지 주소를 통해 프레임이 올바른 수신자에게 전달되도록
  합니다.

- Source MAC address: 데이터를 전송할 장치의 물리적 주소인 MAC 주소를 나타냅니다. 수신 측에서는 이를 통해 데이터의 출처를 확인할
  있습니다.

- Ether Type: 프레임 내의 페이로드 데이터 형식을 식별하는 필드로, 상위 계층 프로토콜(IPv4, IPv6)의 종류를 알려줍니다.

- Payload: 전송할 실제 데이터를 담고 있는 부분으로, 일반적으로 최대 1500 byte의 크기를 가집니다.

- Frame Check Sequence: 프레임의 무결성을 확인하기 위한 오류 검출 코드로, 수신측에서 프레임의 오류를 검출하는데 사용됩니다.

### CSMA/CA (무선 LAN에서 충돌 방지)
- CSMA/CD의 문제점: 무선은 half-duplex 방식이라 송신과 수신을 동시에 못함 -> 충돌감지(CD)를 할 수 없음.
- 대안: CSMA/CA (Collision Avoidance, 충돌 회피)
  - 무선 LAN에서 사용
  - 송신 전 채널 감지 -> 채널이 비어있으면 바로 송신, 아니면 랜덤 backoff 대기.
  - 추가로 RTS/CTS (Requests to Send / Clear to Send) 메커니즘을 사용해 단말 문제 완화.

<img width="717" height="355" alt="image" src="https://github.com/user-attachments/assets/17db52dc-7faf-457a-b097-3ad85b96c8a8" />

`https://github.com/user-attachments/assets/17db52dc-7faf-457a-b097-3ad85b96c8a8`

🔹 허브(Hub) 환경

허브는 단순히 신호를 모든 포트에 브로드캐스트합니다.

따라서 하나의 공유 매체(Shared Medium) 위에 여러 장비가 붙는 구조 → 충돌 가능성 높음.

이때 CSMA/CD가 필요.

🔹 스위치(Switch) 환경

스위치는 포트 단위로 충돌 도메인을 분리합니다.

일반적으로 각 링크는 1:1 전용(full-duplex 가능) 연결.

→ 충돌 자체가 발생하지 않음.

따라서 CSMA/CD는 동작하지 않고, 사실상 불필요합니다.

🔹 정리

허브 + 반이중 → CSMA/CD 필요

스위치 + 전이중 → CSMA/CD 불필요 (실제로 비활성화됨)


