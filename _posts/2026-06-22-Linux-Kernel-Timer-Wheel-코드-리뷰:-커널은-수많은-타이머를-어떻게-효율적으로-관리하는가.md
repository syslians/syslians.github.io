---
title: "Linux Kernel Timer Wheel 코드 리뷰: 커널은 수많은 타이머를 어떻게 효율적으로 관리하는가"
date: "2026-06-22T14:57:54.022Z"
categories:
  - "linux"
  - "os"
author: "현제 김_7254"
slug: "linux_kernel_timer_wheel_코드_리뷰_커널은_수많은_타이머를_어떻게_효율적으로_관리하는가"
---

# Linux Kernel Timer Wheel 코드 리뷰: 커널은 수많은 타이머를 어떻게 효율적으로 관리하는가

## 초록

이 글은 Linux 커널의 internal timer 구현 코드를 분석한다. 분석 대상은 jiffies 기반의 kernel timer subsystem이며, 핵심 자료구조는 timer wheel이다. Timer wheel은 수많은 timeout timer를 낮은 비용으로 등록하고 만료시키기 위해 설계된 계층형 bucket 구조다. 이 구현은 "모든 타이머를 정확한 시각에 깨우는 것"보다 "대부분의 timeout timer를 충분히 효율적으로 관리하는 것"에 초점을 둔다.

커널의 많은 타이머는 네트워크, 디스크 I/O, 연결 추적, 드라이버 timeout처럼 정상적인 경우 만료되기 전에 취소된다. 따라서 모든 타이머를 고정밀로 관리하는 것보다, 만료 시간이 먼 타이머는 더 거친 granularity로 묶고, 가까운 타이머만 더 세밀하게 처리하는 방식이 효율적이다. 이 코드의 핵심은 바로 이 타협이다.

---

## 1. 왜 이 코드를 볼 가치가 있는가

Kubernetes, 컨테이너, 네트워크, eBPF, SRE를 공부하다 보면 결국 Linux 커널 내부 메커니즘을 만나게 된다. 컨테이너는 프로세스 격리 위에 있고, CNI는 네트워크 namespace와 routing 위에 있으며, kubelet과 container runtime은 Linux process, cgroup, namespace, timer, scheduler 위에서 동작한다.

이 코드가 흥미로운 이유는 Linux 커널이 시간을 처리하는 방식을 보여주기 때문이다. 사용자 공간에서는 sleep(1), timeout, setTimeout, cron, read timeout, TCP retransmission timeout 같은 기능을 당연하게 사용한다. 하지만 커널 내부에서는 수많은 타이머를 효율적으로 저장하고, 다음 만료 시점을 계산하고, CPU를 깨우고, callback을 실행하고, 동시 삭제와 재등록 race를 막아야 한다.

즉, 이 코드는 단순한 타이머 코드가 아니다. 운영체제가 다음과 같은 문제를 어떻게 푸는지 보여준다.

```
1. 수많은 timer를 어디에 저장할 것인가?
2. 새 timer가 들어왔을 때 어느 bucket에 넣을 것인가?
3. 시간이 지났을 때 어떤 timer가 만료되었는지 어떻게 찾을 것인가?
4. SMP 환경에서 CPU별 timer 상태를 어떻게 보호할 것인가?
5. idle CPU를 불필요하게 깨우지 않으려면 어떻게 해야 하는가?
6. timer callback이 실행 중일 때 삭제 요청이 오면 어떻게 동기화할 것인가?
```

---

## 2. 전체 구조 개요

이 코드는 크게 다음 흐름으로 이해할 수 있다.

```
timer_list
   |
   | add_timer() / mod_timer()
   v
__mod_timer()
   |
   | calc_wheel_index()
   v
timer wheel bucket 선택
   |
   | enqueue_timer()
   v
timer_base.vectors[idx]에 삽입
   |
   | tick / softirq
   v
collect_expired_timers()
   |
   | expire_timers()
   v
timer callback 실행
```

논문식으로 표현하면 다음과 같다.

```
Figure 1. Kernel Timer Lifecycle

+-------------+
| timer_list  |
+-------------+
       |
       | add_timer / mod_timer
       v
+----------------+
| __mod_timer()  |
+----------------+
       |
       | calculate wheel index
       v
+---------------------+
| timer wheel bucket  |
+---------------------+
       |
       | enqueue
       v
+---------------------+
| per-CPU timer_base  |
+---------------------+
       |
       | timer interrupt / softirq
       v
+---------------------+
| expire callback     |
+---------------------+
```

여기서 timer_list는 개별 타이머 객체이고, timer_base는 CPU별 timer wheel 상태를 관리하는 자료구조다. timer_base 안에는 lock, 현재 실행 중인 timer, 현재 clock, 다음 만료 시각, pending bitmap, bucket 배열이 들어 있다.

---

## 3. 핵심 자료구조: timer_base

코드의 중심에는 struct timer_base가 있다.

```
struct timer_base {
    raw_spinlock_t      lock;
    struct timer_list   *running_timer;
    unsigned long       clk;
    unsigned long       next_expiry;
    unsigned int        cpu;
    bool                next_expiry_recalc;
    bool                is_idle;
    bool                timers_pending;
    DECLARE_BITMAP(pending_map, WHEEL_SIZE);
    struct hlist_head   vectors[WHEEL_SIZE];
};
```

이를 개념적으로 그리면 다음과 같다.

```
Figure 2. Per-CPU timer_base

+--------------------------------------------------+
| timer_base                                       |
|--------------------------------------------------|
| lock                 : timer_base 보호           |
| running_timer        : 현재 callback 실행 중 timer |
| clk                  : base clock                |
| next_expiry          : 다음 만료 시각             |
| cpu                  : 이 base가 속한 CPU         |
| pending_map          : bucket 사용 여부 bitmap    |
| vectors[]            : timer bucket 배열          |
+--------------------------------------------------+
```

중요한 점은 timer wheel이 전역 하나로만 존재하는 것이 아니라 per-CPU 기반으로 관리된다는 점이다.

```
CPU0 -> timer_base[0]
CPU1 -> timer_base[1]
CPU2 -> timer_base[2]
...
```

이렇게 하면 모든 timer 조작이 하나의 global lock에 몰리지 않는다. 각 CPU는 자기 timer base를 중심으로 timer를 enqueue/expire할 수 있고, 필요한 경우에만 migration이나 remote wakeup을 수행한다. 이것은 SMP 확장성을 위해 중요하다.

---

## 4. Timer Wheel이란 무엇인가

Timer wheel은 만료 시각을 기준으로 timer를 bucket에 넣는 자료구조다. 단순한 priority queue를 쓰면 가장 빠른 timer를 찾기 쉽지만, timer 추가와 삭제가 빈번한 kernel timeout workload에서는 비용이 커질 수 있다. Timer wheel은 시간을 bucket으로 나누어 timer를 넣는다.

이 코드의 timer wheel은 여러 level을 가진다.

```
Figure 3. Hierarchical Timer Wheel

Level 0: 짧은 timeout, 작은 granularity
Level 1: 조금 더 긴 timeout, 더 큰 granularity
Level 2: 더 긴 timeout, 더 큰 granularity
...
Level N: 매우 긴 timeout, 매우 큰 granularity
```

각 level은 64개의 bucket을 가진다.

```
LVL_BITS = 6
LVL_SIZE = 1 << 6 = 64
```

그리고 level이 올라갈수록 granularity는 8배씩 커진다.

```
LVL_CLK_SHIFT = 3
LVL_CLK_DIV   = 1 << 3 = 8
```

즉 level별 시간 해상도는 다음과 같은 구조다.

```
Level 0 granularity = 1
Level 1 granularity = 8
Level 2 granularity = 64
Level 3 granularity = 512
...
```

이를 도식화하면 다음과 같다.

```
Figure 4. Level별 Bucket 구조

+---------+---------+---------+---------+---------+
| Level 0 | Level 1 | Level 2 | Level 3 | Level N |
+---------+---------+---------+---------+---------+
| 64 buckets each                                   |
+--------------------------------------------------+

Level이 낮을수록:
- 가까운 미래 timer
- 세밀한 granularity

Level이 높을수록:
- 먼 미래 timer
- 거친 granularity
```

이 구조는 "가까운 시간은 정확하게, 먼 시간은 대략적으로" 처리하는 방식이다. timeout timer의 대부분은 만료되기 전에 취소되므로, 먼 미래 timeout을 지나치게 정밀하게 관리할 필요가 없다.

---

## 5. 이 구현의 철학: 정확성보다 확장성

코드 주석은 이 timer wheel이 기존 classic timer wheel과 달리 recascading을 제거했다고 설명한다. 기존 timer wheel에서는 시간이 흐르면서 상위 level에 있던 timer를 하위 level로 다시 옮기는 cascading 과정이 필요했다. 하지만 이 구현은 그 비용을 없애기 위해 timer를 더 거친 granularity에 묶어 처리한다.

이 설계는 다음 관점에서 이해할 수 있다.

```
정확한 timer expiry
    vs
대규모 timeout timer 처리 효율
```

Linux 커널의 많은 timer는 timeout 용도다. 예를 들어 네트워크 패킷 재전송, 디스크 I/O timeout, connection tracking timeout 등이 있다. 정상적인 경우 timeout은 발생하지 않는다. 이벤트가 정상 처리되면 timer는 만료 전에 삭제된다. 따라서 timeout이 실제 만료된다는 것은 이미 비정상 상황이거나 느린 경로에 들어갔다는 의미다.

그러므로 커널은 이렇게 판단한다.

> timeout timer가 수 ms 늦게 만료되는 것보다, 수많은 timer를 싸게 등록하고 삭제하는 것이 더 중요하다.

이 관점은 굉장히 실용적이다. 운영체제는 모든 추상화를 완벽하게 정확하게 만드는 것이 아니라, workload의 실제 성질에 맞춰 비용과 정확성을 trade-off한다.

---

## 6. Timer 등록 경로: add_timer → __mod_timer → enqueue_timer

타이머를 등록하는 대표 함수는 add_timer()다.

```
void add_timer(struct timer_list *timer)
{
    if (WARN_ON_ONCE(timer_pending(timer)))
        return;
    __mod_timer(timer, timer->expires, MOD_TIMER_NOTPENDING);
}
```

하지만 실제 핵심은 __mod_timer()다. mod_timer() 역시 내부적으로 __mod_timer()를 호출한다. 이 함수는 이미 pending 상태인 timer를 재설정하거나, inactive timer를 새로 enqueue한다.

등록 흐름은 다음과 같다.

```
Figure 5. Timer Registration Path

add_timer()
   |
   v
__mod_timer()
   |
   | 1. timer_base lock 획득
   | 2. 기존 pending timer인지 확인
   | 3. 같은 bucket이면 expiry만 갱신
   | 4. 필요하면 detach
   | 5. 새 bucket index 계산
   v
enqueue_timer()
   |
   | 6. bucket list에 삽입
   | 7. pending_map bit set
   | 8. next_expiry 갱신
   | 9. idle CPU wakeup 필요 여부 판단
```

여기서 중요한 최적화가 있다. 이미 pending인 timer를 다시 설정했는데, 새 만료 시각이 기존과 같은 bucket에 들어간다면 timer를 bucket에서 빼고 다시 넣지 않는다. 그냥 timer->expires만 갱신하고 반환한다. 이 최적화는 네트워크 코드에서 자주 발생하는 timer 재설정 비용을 줄인다.

이것은 커널 코드의 전형적인 특징이다. 알고리즘만 보면 단순히 "삭제 후 재삽입"하면 되지만, 실제 커널은 hot path에서 불필요한 list 조작과 lock 시간을 줄이기 위해 같은 bucket 여부를 검사한다.

---

## 7. Bucket 선택: calc_wheel_index()

타이머가 어느 bucket에 들어갈지는 calc_wheel_index()가 결정한다. 이 함수는 현재 base clock과 timer expiry의 차이, 즉 delta를 계산한 뒤, 그 크기에 따라 level을 선택한다.

개념적으로는 다음과 같다.

```
delta = expires - base->clk

if delta is small:
    use Level 0
else if delta is medium:
    use Level 1, 2, 3 ...
else:
    use last Level
```

도식화하면 다음과 같다.

```
Figure 6. Delta 기반 Level 선택

expires - clk = delta

0ms ~ 짧은 범위
    -> Level 0

조금 먼 미래
    -> Level 1

더 먼 미래
    -> Level 2

매우 먼 미래
    -> Last Level
```

매우 큰 timeout은 wheel capacity를 넘어갈 수 있다. 이 경우 코드는 터무니없이 큰 timeout을 마지막 wheel level의 최대 timeout으로 강제한다. 즉, timer wheel이 표현할 수 있는 범위를 넘어서는 timeout은 maximum capacity에 맞춰 잘라낸다.

이 설계 역시 실용적이다. 무한히 먼 timeout을 위해 자료구조를 무한정 키울 수 없기 때문이다.

---

## 8. Timer enqueue: pending_map과 vectors

enqueue_timer()는 timer를 실제 bucket에 넣는다.

핵심 동작은 다음과 같다.

```
hlist_add_head(&timer->entry, base->vectors + idx);
__set_bit(idx, base->pending_map);
timer_set_idx(timer, idx);
```

이 코드는 세 가지 일을 한다.

```
1. timer를 bucket list에 삽입한다.
2. pending_map에서 해당 bucket bit를 켠다.
3. timer flags에 자신이 들어간 bucket index를 저장한다.
```

이를 그림으로 표현하면 다음과 같다.

```
Figure 7. Bucket과 Bitmap

pending_map
+---+---+---+---+---+---+
| 0 | 1 | 0 | 0 | 1 | ... |
+---+---+---+---+---+---+
      |           |
      v           v
 vectors[1]    vectors[4]
    |             |
 timer A       timer C
 timer B       timer D
```

pending_map은 bucket이 비어 있는지 빠르게 확인하기 위한 bitmap이다. 모든 bucket list를 순회하지 않고, bit operation으로 pending bucket을 찾을 수 있다. vectors[]는 실제 timer들이 연결된 hash list다.

또 하나 중요한 부분은 next_expiry다. 새 timer의 effective expiry가 현재 base->next_expiry보다 빠르면 next_expiry를 갱신하고, 필요한 경우 idle CPU를 깨운다.

---

## 9. NO_HZ와 idle CPU wakeup

현대 커널은 CPU가 idle 상태일 때 불필요한 timer tick을 줄이기 위해 NO_HZ 기능을 사용한다. 하지만 새 timer가 remote CPU에 enqueue되었고, 그 CPU가 idle 상태라면 문제가 생길 수 있다. CPU가 계속 자고 있으면 timer가 제때 처리되지 않을 수 있기 때문이다.

이때 trigger_dyntick_cpu()가 등장한다.

개념은 다음과 같다.

```
Figure 8. NO_HZ 환경의 Timer Wakeup

새 timer enqueue
   |
   v
이 timer가 idle CPU의 next_expiry를 앞당기는가?
   |
   v
필요하면 wake_up_nohz_cpu()
```

단, deferrable timer는 idle CPU를 깨우지 않는다. Deferrable timer는 이름 그대로 CPU가 idle이면 나중으로 미뤄도 되는 timer다. 따라서 전력 절약을 위해 idle CPU를 굳이 깨우지 않는다.

이 구조는 Linux 커널이 성능뿐 아니라 전력 효율도 같이 고려한다는 점을 보여준다.

---

## 10. Timer 만료 처리: collect_expired_timers와 expire_timers

타이머가 만료될 때는 collect_expired_timers()가 현재 clock 기준으로 만료된 bucket들을 모은다. 이후 expire_timers()가 각 timer의 callback을 실행한다.

흐름은 다음과 같다.

```
Figure 9. Timer Expiration Path

timer interrupt / softirq
   |
   v
collect_expired_timers()
   |
   | pending_map 확인
   | 만료 bucket list 이동
   v
expire_timers()
   |
   | timer detach
   | running_timer 설정
   | lock 해제
   | callback 실행
   | lock 재획득
   v
done
```

여기서 중요한 부분은 callback 실행 전에 timer base lock을 해제한다는 점이다. Timer callback은 임의의 커널 코드를 실행할 수 있기 때문에 lock을 잡은 상태로 callback을 실행하면 lock contention과 deadlock 위험이 커진다.

하지만 lock을 풀면 또 다른 문제가 생긴다. 다른 CPU나 다른 코드가 현재 실행 중인 timer를 삭제하거나 변경하려 할 수 있다. 이를 위해 base->running_timer가 사용된다. 현재 어떤 timer callback이 실행 중인지 표시해두고, timer_delete_sync() 같은 동기 삭제 함수가 이를 확인한다.

---

## 11. Timer 삭제와 동기화: timer_delete_sync()

Timer 삭제는 단순히 list에서 제거하면 끝나는 문제가 아니다. timer callback이 이미 다른 CPU에서 실행 중일 수 있다. 그래서 Linux 커널은 여러 삭제 함수를 제공한다.

```
timer_delete()
    - pending timer를 제거하지만 callback 실행 완료까지 기다리지는 않음

timer_delete_sync()
    - timer를 제거하고 callback이 실행 중이면 끝날 때까지 기다림

timer_shutdown()
    - timer를 비활성화하고 재등록을 막음

timer_shutdown_sync()
    - callback 종료까지 기다리고 이후 재등록도 막음
```

특히 timer_delete_sync()의 주석은 매우 중요하다. 이 함수는 callback이 다른 CPU에서 실행 중일 수 있는 상황까지 고려한다. 또한 잘못된 lock ordering에서 deadlock이 발생할 수 있음을 경고한다.

도식화하면 다음과 같다.

```
Figure 10. timer_delete_sync Race

CPU1
  timer callback 실행 중
  base->running_timer = mytimer

CPU0
  timer_delete_sync(mytimer)
  |
  | callback 끝날 때까지 대기
  v
  안전하게 삭제 완료
```

문제는 caller가 callback이 필요로 하는 lock을 잡고 있으면 deadlock이 발생할 수 있다는 점이다. 그래서 커널 timer API는 단순히 "삭제 함수"가 아니라 "동시성 계약"을 포함한다.

이 부분이 커널 코드의 난이도다. 사용자 공간에서는 timer를 cancel하면 끝이라고 생각하기 쉽지만, 커널에서는 interrupt context, softirq context, PREEMPT_RT, SMP, lockdep까지 모두 고려해야 한다.

---

## 12. PREEMPT_RT에서의 추가 고려

코드에는 CONFIG_PREEMPT_RT 조건부 로직도 포함되어 있다. PREEMPT_RT 커널은 실시간성을 높이기 위해 softirq와 lock 처리 방식이 일반 커널과 다르다. 따라서 timer callback이 실행 중일 때 삭제하려는 쪽이 priority inversion이나 livelock을 일으키지 않도록 별도의 expiry_lock, timer_waiters 같은 장치를 둔다.

개념적으로는 다음과 같다.

```
Figure 11. PREEMPT_RT Timer Synchronization

timer callback 실행
   |
   | expiry_lock 보호
   v
delete_sync 시도
   |
   | callback 실행 중이면 wait
   v
priority inversion / livelock 완화
```

이 부분은 Linux 커널이 일반 서버 workload뿐 아니라 실시간성 요구가 있는 환경까지 고려한다는 점을 보여준다.

---

## 13. 코드의 설계상 장점

첫 번째 장점은 확장성이다. per-CPU timer_base 구조와 bucket 기반 timer wheel은 많은 timer를 낮은 비용으로 처리할 수 있게 한다. 모든 timer를 하나의 global priority queue에 넣는 방식보다 lock contention을 줄일 수 있다.

두 번째 장점은 실제 workload에 맞춘 최적화다. 대부분의 kernel timer는 timeout 용도이며 만료 전에 취소된다. 따라서 먼 미래 timer를 정밀하게 관리하기보다, granularity를 높여 batching하는 것이 합리적이다.

세 번째 장점은 전력 효율 고려다. round_jiffies() 계열 함수와 NO_HZ 관련 처리는 timer를 적절히 뭉쳐 CPU wakeup 횟수를 줄이려는 목적을 가진다. 이는 서버뿐 아니라 모바일, 임베디드, 노트북 환경에서도 중요하다.

네 번째 장점은 동시성 안정성이다. running_timer, TIMER_MIGRATING, base lock, sync delete 계열 함수는 SMP 환경에서 timer callback과 삭제/재등록이 충돌하는 문제를 다룬다.

---

## 14. 코드의 복잡성과 한계

이 구현은 효율적이지만 단순하지 않다. 특히 다음 지점들이 어렵다.

```
1. level별 granularity와 bucket index 계산
2. pending timer 재등록 최적화
3. timer migration
4. NO_HZ idle CPU wakeup
5. callback 실행 중 삭제 동기화
6. PREEMPT_RT 조건부 동작
```

또한 이 timer wheel은 고정밀 timer를 위한 구조가 아니다. 커널에는 hrtimer라는 별도 고해상도 timer subsystem이 존재한다. 이 코드의 timer wheel은 주로 timeout성 timer에 최적화되어 있다. 따라서 "정확한 시각에 반드시 실행되어야 하는 timer"와 "대략 이 시점 이후 실행되면 되는 timeout timer"를 구분해서 봐야 한다.

이 점에서 이 코드는 성능과 정확성의 trade-off를 보여주는 좋은 사례다.

---

## 16. 최종 리뷰

이 코드는 Linux 커널이 시간이라는 자원을 얼마나 실용적으로 다루는지 보여준다. 커널은 모든 timer를 완벽하게 정확히 실행하려 하지 않는다. 대신 timer의 성격을 분석한다. 대부분의 timer는 timeout이고, 대부분 만료 전에 취소된다. 따라서 커널은 먼 미래 timer를 coarse-grained bucket에 넣고, 가까운 timer만 더 세밀하게 다룬다.

또한 이 코드는 운영체제 설계의 핵심 원칙을 보여준다.

```
정확성
확장성
전력 효율
동시성 안정성
실시간성
```

이 다섯 가지는 서로 충돌한다. Linux timer wheel은 이 충돌을 실용적으로 조정한 결과다. 가까운 timer는 비교적 정확하게 처리하고, 먼 timer는 granularity를 높여 batching한다. CPU별 timer base를 두어 lock contention을 줄이고, NO_HZ 환경에서는 idle CPU를 불필요하게 깨우지 않는다. 동시에 timer callback과 삭제가 충돌하지 않도록 복잡한 동기화 규칙을 둔다.

내가 이 코드를 보며 가장 크게 느낀 점은, 시스템 프로그래밍은 "기능 구현"보다 "경계 조건 관리"에 가깝다는 것이다. timer를 추가하고 만료시키는 기본 아이디어는 어렵지 않다. 하지만 진짜 어려운 부분은 SMP, softirq, idle CPU, timer migration, callback 실행 중 삭제, PREEMPT_RT, lock ordering 같은 경계 조건이다.

Kubernetes와 클라우드 네이티브를 공부하는 입장에서도 이 코드는 좋은 학습 대상이다. Kubernetes는 높은 수준의 오케스트레이션 시스템이지만, 결국 Linux 커널 위에서 동작한다. Pod가 죽고, kubelet이 heartbeat를 보내고, timeout이 발생하고, probe가 실패하고, connection이 재시도되는 모든 동작 아래에는 이런 커널 메커니즘이 있다.

따라서 이 코드는 단순한 Linux 내부 구현이 아니라, 클라우드 네이티브 시스템의 가장 아래 계층을 이해하기 위한 좋은 출발점이다.

---

## 17. 한 문장 정리

Linux kernel timer wheel은 수많은 timeout timer를 효율적으로 처리하기 위해 정확성을 일부 양보하고, level별 granularity와 per-CPU timer base를 사용해 확장성, 전력 효율, 동시성 안정성을 동시에 달성하려는 커널 내부 시간 관리 구조다.