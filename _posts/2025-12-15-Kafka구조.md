---
layout: post
title: "Kafka구조"
categories: [Kafka, MessageBroker]
author: cotes
published: true
---

카프카는 대용량 스트리밍 데이터를 분산(Distribution) + 고가용성(HA) + 확장성(Scalable) 방식으로 처리하는 메시지 플랫폼입니다.
대량의 데이터를 처리하고 실시간으로 전송하는데 쓰입니다. 모든 데이터는 로그 형식으로 파일시스템에 기록됩니다.
카프카는 클러스터 -> 브로커 -> 토픽 -> 파티션 -> 세그먼트로 구성되어 있습니다. 

![BitOperations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FbXadeI%2FbtsCBLSUOgA%2FAAAAAAAAAAAAAAAAAAAAAMh8nKgcUpdAOlVEEba1fMY1WUQL7xcaB9fgEokP2tlc%2Fimg.webp%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1767193199%26allow_ip%3D%26allow_referer%3D%26signature%3DZ25Am4mCEpGOdBeI94osN8U%252B5W8%253D)

## 클러스터(Cluster)

- Kafka 클러스터는 여러 대의 서버(브로커)로 구성된 Kafka 시스템 입니다. 클러스터는 대량의 데이터를 처리하고, 여러 Consumer와 Producer에게 메시지 서비스를 제공합니다.
- 클러스터는 메시지의 저장, 처리 및 전달을 담당합니다. 클러스터는 고가용성과 확장성을 제공하며, 데이터를 여러 브로커에 분산시켜 저장합니다.

![BitOperations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FbXadeI%2FbtsCBLSUOgA%2FAAAAAAAAAAAAAAAAAAAAAMh8nKgcUpdAOlVEEba1fMY1WUQL7xcaB9fgEokP2tlc%2Fimg.webp%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1767193199%26allow_ip%3D%26allow_referer%3D%26signature%3DZ25Am4mCEpGOdBeI94osN8U%252B5W8%253D)

## 브로커(Broker)

- Kafka 브로커는 Kafka 시스템을 구성하는 개별 서버입니다. 이 브로커들은 Kafka 클러스터를 형성하여, 전체 시스템의 일부로 작동합니다. default는 3개입니다.
![BitOperations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FdLS1Za%2FbtsCMnQtgUY%2FAAAAAAAAAAAAAAAAAAAAAE7W2HyT7nGb1a9rwOPI4Ux3dwR4eexYjd4pJVWMpQNR%2Fimg.webp%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1767193199%26allow_ip%3D%26allow_referer%3D%26signature%3D5jwpLlNhvKPSzYmFtRgwFPpZs%252Fc%253D)

[데이터 저장 및 관리]
- 각 브로커는 Kafka 토픽의 하나 이상의 파티션을 저장하고 관리합니다. 이 파티션들에는 메시지 또는 레코드가 순차적으로 저장됩니다.

[클라이언트 요청 처리]
- 브로커는 Kafka Producer로부터 데이터를 받아 저장하고, Consumer의 요청에 따라 저장된 데이터를 제공합니다.

[고가용성 및 확장성]
- Kafka는 데이터의 안정성을 위해 파티션을 여러 브로커에 복제합니다. 이를 통해, 하나의 브로커에 장애가 발생하더라도 시스템은 계속 작동할 수 있습니다. 그리고 필요시 클러스터에
  새로운 브로커를 추가하여 시스템의 처리 능력과 저장 용량을 확장할 수 있습니다.


[리더와 팔로워]
- 각 파티션에는 리더와 팔로우 브로커가 있습니다. 리더 브로커는 모든 읽기 및 쓰기 작업을 처리하고, 팔로워 브로커는 리더의 데이터를 복제합니다. 이러한 구조는 데이터의 일관성을
  유지하고, 부하를 분산하는데 도움이 됩니다.
- 브로커가 죽어도 Follwer가 Leader로 승격되므로 fail over가 매우 빠르다.
  

[데이터 영속성]
Kafka는 단순 메시지 큐가 아니라 파일 시스템에 append-only 방식으로 데이터를 실제로 저장. Log Compaction / Segment 파일 구조로 인해
고성능 + 영속성을 동시에 충족함.


[통신 및 조정]
- 브로커들은 클러스터 내에서 서로 통신하여 데이터의 동기화와 상태 정보를 공유합니다. 이를 통해 클러스터 전체가 일관된 상태를 유지하고, 효율적으로 작동할 수 있습니다.
- Kafka 브로커는 Kafka 시스템의 중추적인 역할을 하며, 데이터의 저장, 처리 및 전송을 담당합니다. 브로커들은 상호작용과 조정을 통해 Kafka는 대용량의 데이터를
  효율적이고 안정적으로 관리할 수 있습니다.


### 토픽

- Kafka 토픽은 메시지들의 특정 카테고리 또는 피드를 나타냅니다. 토픽은 Producer가 데이터를 보내는 대상이며, Consumer가 데이터를 읽는 주체입니다.

![BitOperations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FcBllJP%2FbtsCAhR55Wl%2FAAAAAAAAAAAAAAAAAAAAAABAjjz_EiN_sa3tIun5-qm4sf31wuevMpI4JLm7xys2%2Fimg.webp%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1767193199%26allow_ip%3D%26allow_referer%3D%26signature%3D%252FeYRGa2dmiX%252FNk9p3P99sMDQPvc%253D)

토픽은 데이터를 카테고리화하여 관리할 수 있게 해줍니다. 예를 들어, 다양한 종류의 이벤트나 메시지들은 서로 다른 토픽으로 분류할 수 있습니다. 또한 하나의 토픽은 여러
소비자가 구독할 수 있으며, 이들은 토픽에서 발행된 메시지를 읽을 수 있습니다.

### 파티션

- 파티션은 Kafka 토픽을 구성하는 하위 단위입니다. 하나의 토픽은 여러개의 파티션으로 나누어질 수 있으며, 이는 Kafka의 확장성과 병렬 처리 능력을 향상시킵니다.

[파티션의 역할 및 중요성]

- 데이터 분산 및 병렬 처리: 각 파티션은 독립적으로 데이터를 저장하고, 여러 브로커에 걸쳐 분산될 수 있습니다. 이를 통해 kafka는 데이터를 효율적으로 관리하고,
  동시에 여러 소비자에게 서비스 할 수 있습니다.
  
- 순차적 데이터 관리: 각 파티션 내에서 메시지는 순차적으로 저장되며, 이 순서는 파티션 내에서 유지됩니다. 이는 데이터의 일관성과 정확한 순서 보장에 중요합니다.
  이 구조 덕분에 각 메시지는 파티션 내에서 고유한 offset 값을 가지게 되고, 이 오프셋을 통해 메시지의 위치를 정확하게 식별할 수 있습니다. Kafka의 파티션은
  기본적으로 로그 파일처럼 작동합니다. 이 로그 구조에서 각 메시지는 순차적으로 저장되며, 각 메시지에는 고유한 offset값이 할당됩니다. 이 offset은 메시지의
  위치를 나타내며, kafka 시스템 내에서 메시지를 정확히 식별하는데 사용됩니다.
  
- 수평확장: 파티션이 많아질수록 병렬 처리량이 증가

[Kafka 파티션의 주의점]

1. 키 선택의 중요성

- 프로듀서가 데이터를 파티션에 할당할때 사용하는 키의 선택은 중요합니다. 잘못된 키 선택은 데이터 분산의 불균형을 초래하고, 특정 브로커에 부하를 집중시킬 수 있습니다.
  해결방법은 키의 해시 분포가 균일하도록 키 선택 전략을 명확하게 정의하는것입니다.

- Kafka에서 키 선택의 중요성을 이해하기 위해서는 Kafka가 데이터를 어떻게 분산 저장하는지 이해해야 합니다. Kafka는 키를 기반으로 메시지를 파티션에 할당합니다.
  이 과정에서 키의 해시값을 사용하여 각 메시지가 어느 파티션에 저장될지 결정합니다. 적절한 키 선택은 데이터가 클러스터의 모든 파티션에 균등하게 분산되도록 합니다.
  아래는 키들이 균등하게 브로커에 분산된 그림입니다.


![BitOperations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FvKYNy%2FbtsCEI2FkUX%2FAAAAAAAAAAAAAAAAAAAAAF4kIjRpt8h184SjpGFMp_ZKCbdhhytboUWvBQYPr_H5%2Fimg.webp%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1767193199%26allow_ip%3D%26allow_referer%3D%26signature%3DEuheH8poyABfn1d88x5ms%252FWQtuE%253D)


- 불균등 키 분산: Kafka에서 특정 파티션에 키들이 집중되는 경우, 불균형한 분산이 발생합니다. 특정 파티션에 키들이 과도하게 집중되어, 다른 파티션은 충분히
  활용되지 않아 성능에 문제가 생깁니다.
- 아래 경우, Broker 1에 과부하가 걸리고 Broker2와 Broker3는 충분히 활용되지 않습니다. 결과적으로 클러스터의 전체적인 효율성이 떨어지며, 특정 브로커에
  부하가 집중되어 시스템의 안정성에 문제가 발생할 수 있습니다.

![BitOperations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FbfiL2z%2FbtsCIEk68WN%2FAAAAAAAAAAAAAAAAAAAAACJ7VqtTsnmABb2WDywrgYLQcE3s3kdbbc484ITME5-t%2Fimg.webp%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1767193199%26allow_ip%3D%26allow_referer%3D%26signature%3D0K9HreXlbEHE7z6ZKAi0uIQN5AY%253D)


[순서 보장의 의미]

- Kafka에서 순서 보장이란 메시지가 파티션에 저장된 순서대로 처리된다는 것을 의미합니다. 이는 프로듀서가 메시지를 보낸 순서가 중요함을 의미합니다. 만약 메시지가
  비순차적으로 보내진다면, 그 순서대로 Kafka가 처리하게 됩니다.
- 따라서, 프로듀서 측에서 메시지 발송 순서를 관리하는것이 중요합니다. 특히 시계열 데이터나 트랜잭션 순서가 중요한 경우, 올바른 순서로 메시지를 보내야 합니다.

### 파티션 로그 구조 이해하기
- offset 0부터 시작: Kafka에서는 파티션의 각 메시지에 0부터 시작하는 순차적인 오프셋 번호를 할당합니다.
- 메시지 추가 시 offset 증가: 새 메시지가 파티션에 추가될 때마다, 그 메시지에는 마지막 메시지의 오프셋에 1을 더한값이 할당됩니다.
  예를 들어 Message A 다음에 Message B가 저장되면, Message B에는 offset 1이 할당됩니다.

```
| Offset | Message     |
|--------|-------------|
| 0      | Message A   |
| 1      | Message B   |
| 2      | Message C   |
| 3      | Message D   |
| 4      | Message E   |
```



### 세그먼트

- Kafka의 세그먼트는 파티션의 데이터를 실제로 저장하는 물리적인 파일입니다. Kafka는 데이터를 파티션에 순차적으로 기록하지만, 이 데이터는 여러 세그먼트 파일로
  나누어 저장됩니다.

![BitOperations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2F4hFMa%2FbtsCJkmF9hU%2FAAAAAAAAAAAAAAAAAAAAABB6toohz4UhqmWDlWRAKG0FBAx3RPXnBk44R1IunzQC%2Fimg.webp%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1767193199%26allow_ip%3D%26allow_referer%3D%26signature%3DvyqzoJy39tSLUvI%252FZHhvynY1dDA%253D)

[세그먼트의 역할 및 특징]

- 데이터 저장 단위: 세그먼트는 Kafka 파티션 내의 데이터를 저장하는 기본 단위입니다. 각 세그먼트 파일은 일정 크기에 도달하거나 특정 시간이 경과하면 새로운 세그먼트
  파일로 전환됩니다.
- 효율적인 데이터 관리: 세그먼트 기반의 데이터 관리는 Kafka가 불필요한 데이터를 효율적으로 정리하고, 디스크 공간을 최적화하는데 도움을 줍니다.
- 로그 컴팩션 및 삭제: Kafka는 설정에 따라 오래된 세그먼트 파일을 삭제하거나 로그를 컴팩션(중복 제거)하는 방식으로 데이터를 관리합니다. 이는 저장 공간을 절약하고,
  시스템의 성능을 유지하는데 도움을 줍니다.

[세그먼트의 작동 방식]
- Producer가 파티션에 데이터를 기록할때, Kafka는 이 데이터를 현재 활성 세그먼트 파일에 추가합니다.
- 세그먼트 파일이 설정된 최대 크기에 도달하면, 새로운 세그먼트 파일이 생성되고, 이후의 데이터는 새 파일에 기록됩니다. 소비자는 이러한 세그먼트 파일들로부터 데이터를 읽어
  처리합니다.

[https://techblog.woowahan.com/17386/, https://curiousjinan.tistory.com/entry/kafka-explained?category=1401507, https://curiousjinan.tistory.com/entry/understand-kafka-partitions]
  
