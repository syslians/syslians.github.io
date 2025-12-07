---
layout: post
title: "대규모 트래픽 처리를 위한 뉴스 피드 시스템 설계 (News Feed Architecture)"
categories: [Sysyem Design, News Feed, Fan-out, Cassandra]
author: cotes
published: true
---

### 시스템 요구사항

- 차단 기능: 팔로우한 사람의 게시글에서 차단한 사람의 댓글이 보이지 않도록 구현
- 규모: DAU 1억명, 하루 평균 사용자당 피드 조회 5회, 글 작성 0.2회
- 성능 목표: 읽기 응답시간 200ms, 쓰기 응답시간 500ms
- QPS(초당 쿼리 수): 일반 시간대 읽기 QPS 5,800, 쓰기 QPS 230
- 피크 시간대: 읽기 QPS 3만, 쓰기 QPS 1,000

### 아키텍처 설계

- 핵심 기능: 피드 발행(포스트), 피드 조회(겟), 팔로우
- 기본 구조:
    - 로드 밸런서(LB) → 서비스 레이어 → 데이터베이스
    - 포스트 서비스: 게시글 작성 처리
    - 뉴스피드 서비스: 피드 조회 처리

### 데이터 스토리지 전략

- 대용량 데이터 처리: 하루 2천만 게시글, 월 6억 게시글
- 스케일 아웃 가능한 클러스터형 데이터베이스 활용
- CDC(Change Data Capture)를 통한 이벤트 스트리밍 처리
- 카프카 같은 이벤트 큐 사용
- 레이트 리밋 적용한 컨슈머 구현

### 캐싱 전략

- Redis Sorted Set 활용하여 피드 데이터 캐싱
- 캐시 키 구조: 팔로워 아이디를 키로, 포스트 아이디와 타임스탬프(점수)를 값으로 저장
- 캐시 제한:
    - 사용자당 최대 1,000개 포스트 저장
    - 30일 TTL 적용
- 캐시 미스 시 폴백 전략: 원본 DB에서 제한된 개수만 조회

### 인플루언서 처리 전략

- 문제: 인플루언서(1억 팔로워)의 게시글 처리 시 시스템 부하
- 해결 방안:
    - 인플루언서 게시글은 별도 캐싱 처리
    - 포스트 서비스에서 인플루언서 식별 및 마킹
    - 인플루언서 게시글은 개별 캐싱하여 조회 시 병합
    - 유저별 팔로우한 인플루언서 목록 캐싱

### 데이터 정합성과 확장성

- 사용자 접속 시점 또는 팔로우/언팔로우 시 인플루언서 캐시 동기화
- 게시물 삭제/탈퇴 처리: 조회 시 없는 게시글은 스킵
- 팔로우 수 실시간 관리: Redis 활용 후 배치 처리로 동기화

### Action Items

- [ ]  인플루언서 식별 기준 명확히 정의 (팔로워 수 등)
- [ ]  캐싱 전략 상세 구현 방안 확정
- [ ]  시스템 피크 부하 시나리오 추가 테스트


## 1. 개요 (Overview)

본 문서는 DAU 1억 명 규모의 글로벌 SNS 뉴스 피드 시스템을 위한 아키텍처 설계를 다룬다. 사용자가 팔로우하는 대상의 게시물을 시간 역순으로 보여주는 기능을 제공하며, **읽기 응답 속도 200ms, 쓰기 응답 속도 500ms**를 보장하는 것을 핵심 목표로 한다.

## 2. 요구사항 및 규모 추정 (Requirements & Estimation)

### 2.1 기능 요구사항

- **피드 생성:** 팔로우하는 사용자의 글을 시간 역순(Reverse Chronological)으로 노출.
- **포스팅:** 텍스트, 미디어 포함 게시물 작성.
- **팔로우:** 사용자 간 팔로우/언팔로우 관계 형성.

### 2.2 비기능 요구사항

- **Latency:** 피드 읽기 200ms 이하 (매우 중요), 쓰기 500ms 이하.
- **Consistency:** Eventual Consistency 허용 (피드 갱신에 약간의 지연 허용).
- **Availability:** 높은 가용성 요구 (SPOF 제거).

### 2.3 규모 추정 (100M DAU 기준)

- **Traffic:**
    - Read QPS: 약 5,800 ~ 30,000 (Peak)
    - Write QPS: 약 230 ~ 1,150 (Peak)
    - Read:Write 비율 = 약 100:1 (Read-Heavy System)
- **Storage:** 일일 약 6TB 데이터 생성 (Blob 별도).

---

## 3. 핵심 아키텍처: Push vs Pull

초기 설계 단계에서 읽기 지연(Read Latency) 200ms 달성을 위해 Push Model (Fan-out on Write)을 기본 전략으로 채택했다.

### 3.1 Pull Model (Fan-out on Read) 기각 사유

- 조회 시점(`SELECT * FROM posts WHERE user_id IN (friends...)`)에 발생하는 **Random I/O**가 과다함.
- 수천 명의 친구 데이터를 가져와 메모리에서 정렬(Merge Sort)하는 비용이 큼.
- DB 샤딩 환경에서 **Scatter-Gather**로 인한 성능 저하 발생.

### 3.2 Push Model (Fan-out on Write) 채택

- **Write Path:** 글 작성 시점에 팔로워들의 피드 캐시(Redis)에 게시물 ID를 미리 넣어둠.
- **Read Path:** 조회 시점에는 연산 없이 캐시(`O(1)`)만 읽어서 반환.

---

## 4. 상세 설계: 일반 유저 처리 (Push Model & CDC)

안정적인 Fan-out 처리를 위해 **CDC(Change Data Capture)** 기반의 비동기 아키텍처를 수립했다.

### 4.1 데이터 흐름 (Data Flow)

1. **Post Service:** 사용자가 글을 쓰면 RDB에 저장(`INSERT`)하고 즉시 응답 반환 (Write Latency 최소화).
2. **CDC (Debezium):** DB의 Transaction Log(Binlog)를 감지하여 Kafka로 이벤트 발행. (애플리케이션 결합도 제거 및 누락 방지).
3. **Fan-out Worker:** Kafka에서 이벤트를 소비하여 팔로워 목록을 조회하고, 각 팔로워의 Redis ZSET에 포스팅 ID를 추가(`ZADD`).
    - *Optimization:* Redis Pipeline을 사용하여 대량의 쓰기 작업을 배치 처리.

### 4.2 캐시 전략 (Caching Strategy)

- **구조:** Redis **Sorted Set (ZSET)** 사용.
    - Key: `feed:{user_id}`
    - Score: `timestamp`
    - Value: `post_id`
- **Retention Policy (Sliding Window):** 메모리 효율을 위해 최신 **800개**만 유지. 801번째부터는 DB에서 조회(Hybrid Pagination).
- **TTL:** 미접속 유저의 캐시 낭비를 막기 위해 **2주(14일)** 설정. 조회 시 갱신(Renew).

### 4.3 장애 대응 (Fallback Logic)

- **Cache Miss:** Redis 데이터 소실 시 DB에서 직접 조회하여 캐시를 재구축(Reconstruct).
- **Thundering Herd 방지:** 동시 요청 폭주를 막기 위해 **Local Lock** 적용 및 조회 범위 제한(최신 20개만 로딩).

### 4.4 페이지네이션 (Pagination)

- **Cursor-based Pagination:** 데이터 갱신 시 중복 노출을 막기 위해 `Offset(Rank)` 방식이 아닌 **`Timestamp(Score)` 기반 커서** 사용 (`ZREVRANGEBYSCORE`).

---

## 5. 확장성: 유명인(Celebrity) 처리와 Hybrid 아키텍처

팔로워가 수백만 명인 VIP(Hotkey)의 글을 Push 방식으로 처리하면 시스템 지연(Lag)이 발생하므로 **Hybrid Model**을 도입했다.

### 5.1 처리 기준 및 전략

- **VIP 기준:** 팔로워 50만 명 이상 (User Metadata 혹은 Graph DB `is_vip` 플래그로 식별).
- **일반 유저 (Push):** 기존대로 팔로워 피드에 직접 배달.
- **VIP (Pull):** 배달하지 않음. VIP 전용 캐시(`vip_posts:{vip_id}`)에만 저장.

### 5.2 읽기 로직의 변화 (Merge Read)

사용자가 피드를 조회할 때(`GET /feed`) 다음 과정을 거친다.

1. **Native Feed:** 내 Redis 피드(`feed:{my_id}`) 조회.
2. **VIP Feed:** 내가 팔로우하는 VIP 목록(`following_vips:{my_id}`)을 확인 후, 각 VIP의 전용 캐시 조회.
3. **Merge:** 애플리케이션 메모리에서 두 리스트를 합쳐 시간순 정렬 후 반환.

---

## 6. 데이터 저장소 전략: Why Cassandra?

500억 건(1억 유저 × 500 팔로우) 이상의 관계(Relationship) 데이터를 저장하기 위해 Wide-Column Store (Cassandra/DynamoDB)를 선정했다.

### 6.1 선정 이유 (vs RDB)

- **Sequential I/O:** RDB는 팔로워 조회 시 인덱스를 타고 여기저기 뒤져야 하는 **Random I/O**가 발생. 반면 Cassandra는 Partition Key(`user_id`) 기준으로 데이터가 물리적으로 인접해 있어(Wide Row), **단 한 번의 Seek**로 500명을 읽어올 수 있음.
- **Linear Scalability:** 데이터 양 증가 시 노드 추가만으로 선형적인 성능 확장이 가능.

### 6.2 데이터 모델링 (Denormalization)

- **Table:** `Followers` (Fan-out용), `Followings` (View용)
- **Optimization:** `Followings` 테이블에 **`is_vip` (Boolean)** 컬럼을 추가하여, 팔로우 목록 조회 시 별도 쿼리 없이 VIP 여부를 즉시 식별.

---

## 7. 엣지 케이스: VIP 탈퇴 처리

1억 명의 팔로워를 가진 VIP 탈퇴 시 시스템 부하를 막기 위해 **"Fast Hide, Slow Clean"** 전략을 사용한다.

1. **Fast Hide (동기 처리):**
    - User DB status `DELETED` 변경.
    - Redis `vip_posts:{id}` 즉시 삭제 또는 Tombstone 마킹.
    - *Effect:* 사용자 입장에선 즉시 피드에서 사라짐.
2. **Read-time Defense:**
    - 피드 조회 시 VIP 캐시가 없거나 Tombstone이면 결과에서 제외.
    - 조회한 유저의 `following_vips` 목록에서 해당 VIP 제거 (Self-Repair).
3. **Slow Clean (비동기 처리):**
    - 별도의 Cleanup Worker가 Cassandra 팔로워 목록을 천천히 스캔하며 데이터를 물리적으로 삭제. (Rate Limiting 적용).

---

## 8. 결론 (Conclusion)

본 설계는 "읽기 성능의 극대화"를 위해 쓰기 시점의 복잡도(Push Model)를 감수하고, "규모의 비대칭성(Celebrity)"을 해결하기 위해 Hybrid 방식을 도입했다. 또한, 대규모 데이터의 I/O 효율성을 위해 **NoSQL(Cassandra)의 Sequential Access** 특성을 활용했다.

이를 통해 1억 DAU 환경에서도 안정적으로 200ms 이내의 읽기 응답 속도를 보장하는 시스템을 구축할 수 있다.
