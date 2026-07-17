---
title: "Linux IPC를 배우면 Kafka와 스트리밍 시스템이 보이는 이유"
date: "2026-07-17T10:43:57.949Z"
categories:
  - "ipc"
  - "linux"
  - "os"
author: "현제 김_7254"
slug: "linux_ipc를_배우면_kafka와_스트리밍_시스템이_보이는_이유"
---

# 

## A Guide to Inter-Process Communication in Linux 실습 학습기

## 1. 들어가며

운영체제를 공부하다 보면 반드시 마주치는 개념이 있다.

바로 IPC, Inter-Process Communication이다.

IPC는 말 그대로 프로세스 간 통신이다. 그런데 처음 공부할 때는 이 개념이 꽤 추상적으로 느껴진다.

pipe, socket, shared memory, message queue, semaphore 같은 용어들이 각각 따로 떨어진 기능처럼 보이기 때문이다.

하지만 실제로 IPC를 이해하기 시작하면, 단순히 Linux API를 외우는 수준을 넘어 다음과 같은 시스템을 더 깊게 이해할 수 있다.

- Shell에서 | 파이프가 어떻게 동작하는가

- Client-Server 모델에서 socket 통신이 어떻게 연결되는가

- 하나의 머신 안에서 여러 프로세스가 데이터를 어떻게 주고받는가

- Kafka 같은 현대 메시징 시스템이 왜 파일, 페이지 캐시, append log, zero-copy 같은 구조를 중요하게 보는가

- 동시성 제어가 코드 레벨에서 왜 필요한가

- 왜 공유 메모리는 빠르지만 위험하고, 왜 semaphore나 lock이 함께 등장하는가

이번 글은 A Guide to Inter-Process Communication in Linux를 기반으로, Docker 안에 구성한 Linux 실습 환경에서 IPC를 직접 실행하면서 학습한 내용을 정리하는 글이다. 이 가이드는 shared files, shared memory with semaphores, pipes, message queues, sockets, signals를 C 코드 예제로 설명한다.

---

## 2. 이 가이드가 중요하다고 보는 이유

이 글에서 IPC를 중요하게 보는 이유는 단순히 "Linux에 이런 기능이 있다"를 알기 위해서가 아니다.

IPC는 현대 시스템 구조를 이해하는 가장 낮은 레벨의 출발점이다.

### 2.1 Client-Server Model을 socket 통신으로 이해할 수 있다

우리가 웹 서비스를 만들 때 흔히 말하는 구조가 있다.

```
Client  ───── request ─────>  Server
Client  <──── response ───── Server
```

HTTP, gRPC, Redis client, Kafka producer, Kubernetes API client 모두 결국은 이 구조를 가진다.

이때 가장 아래 계층에는 socket이 있다.

Linux에서 socket()은 통신을 위한 endpoint를 만들고, 성공하면 그 endpoint를 가리키는 file descriptor를 반환한다.

즉, socket을 공부하면 "클라이언트가 서버에 연결한다"는 말이 단순한 그림이 아니라 실제 시스템 콜 흐름으로 보이기 시작한다.

```
server:
socket()
bind()
listen()
accept()
read()
write()

client:
socket()
connect()
write()
read()
```

[코드 삽입 위치: socket server/client C 코드]

[그림1. socket server 실행 결과]

[그림2. socket client 요청 및 echo 응답 결과]

---

### 2.2 Linux/Unix의 pipe 철학을 이해할 수 있다

Unix 계열 시스템의 강력함은 작은 프로그램을 조합하는 데 있다.

예를 들어 다음 명령어를 보자.

```
ps aux | grep nginx | awk '{print $2}'
```

여기서 |는 단순한 기호가 아니다.

왼쪽 프로세스의 stdout이 오른쪽 프로세스의 stdin으로 연결된다.

즉, 프로세스 A가 출력한 byte stream이 프로세스 B의 입력으로 흘러간다.

Linux man page에서 pipe()는 IPC에 사용할 수 있는 단방향 데이터 채널을 만들며, pipefd[0]은 read end, pipefd[1]은 write end를 가리킨다고 설명한다.

```
Process A
 stdout
   │
   ▼
 pipe buffer in kernel
   │
   ▼
 stdin
Process B
```

[코드 삽입 위치: unnamed pipe 예제 코드]

[그림3. pipe를 통해 parent-child 프로세스가 데이터를 주고받는 실행 결과]

이 구조를 이해하면 shell pipeline이 단순 문자열 조합이 아니라 커널이 관리하는 byte stream 연결이라는 것을 알 수 있다.

---

### 2.3 mmap/shared memory를 통해 modern messaging system의 감각을 잡을 수 있다

shared memory와 mmap은 IPC 중에서도 특히 중요하다.

왜냐하면 이것은 "데이터를 복사해서 전달하는 방식"이 아니라, 여러 프로세스가 같은 메모리 영역을 바라보게 하는 방식이기 때문이다.

Linux의 POSIX shared memory API는 프로세스들이 공유 메모리 영역을 통해 정보를 교환할 수 있게 한다. shm_open()은 POSIX shared memory object를 생성하거나 열고, 이 객체는 서로 관련 없는 프로세스들이 같은 공유 메모리 영역을 mmap()할 수 있게 하는 handle 역할을 한다.

```
Process A virtual memory
        │
        ▼
 shared memory object
        ▲
        │
Process B virtual memory
```

[코드 삽입 위치: shm_open + ftruncate + mmap + sem_open 예제 코드]

[그림4. /dev/shm에 생성된 shared memory object 확인 결과]

[그림5. shm writer 실행 결과]

[그림6. shm reader가 공유 메모리에서 byte를 읽은 결과]

여기서 중요한 점은 다음이다.

공유 메모리는 빠르다. 하지만 빠른 대신 위험하다.

두 프로세스가 같은 메모리를 동시에 수정하면 race condition이 발생할 수 있다. 원문 가이드도 shared memory에 writer가 포함되면 memory-based race condition 위험이 생기기 때문에 semaphore로 접근을 조정해야 한다고 설명한다.

즉, shared memory를 배울 때 핵심은 "빠르다"가 아니다.

핵심은 다음이다.

```
빠른 공유
+
명시적인 동기화
```

이 둘을 함께 이해해야 한다.

---

## 3. 프로세스는 기본적으로 서로의 메모리를 볼 수 없다

IPC를 이해하려면 먼저 프로세스 격리부터 이해해야 한다.

프로세스는 실행 중인 프로그램이다. 각 프로세스는 자신만의 address space를 가진다. 원문 가이드도 서로 다른 프로세스들은 기본적으로 메모리를 공유하지 않는다고 설명한다.

예를 들어 프로세스 A와 프로세스 B가 있다고 하자.

```
Process A
0x1000 ─────────────┐
0x2000              │  A의 가상 주소 공간
0x3000 ─────────────┘

Process B
0x1000 ─────────────┐
0x2000              │  B의 가상 주소 공간
0x3000 ─────────────┘
```

겉으로는 둘 다 0x1000이라는 주소를 가질 수 있다.

하지만 이 주소는 물리 메모리의 같은 위치를 의미하지 않는다.

각 프로세스의 가상 주소 공간은 MMU와 page table을 통해 서로 다른 물리 메모리로 매핑될 수 있다.

그래서 프로세스 A가 단순히 포인터 주소를 프로세스 B에게 넘긴다고 해서 B가 그 메모리를 읽을 수 있는 것은 아니다.

```
printf("%p\n", ptr);
```

이 주소값을 다른 프로세스에 전달해도, 그 프로세스 입장에서는 의미 없는 주소일 수 있다.

따라서 프로세스 간 데이터를 주고받으려면 커널이 제공하는 명시적인 통신 경로가 필요하다.

그것이 바로 IPC다.

---

## 4. IPC를 크게 두 가지 관점으로 나누기

IPC는 여러 방식이 있지만, 학습할 때는 크게 두 가지 흐름으로 나누면 이해하기 쉽다.

```
1. 공유 저장소 기반 IPC
   - shared file
   - shared memory
   - mmap

2. 채널 기반 IPC
   - pipe
   - FIFO / named pipe
   - message queue
   - socket
   - signal
```

공유 저장소 기반 IPC는 두 프로세스가 같은 저장 공간을 바라보는 방식이다.

```
Producer ── write ──> shared storage <── read ── Consumer
```

채널 기반 IPC는 한쪽이 쓰고, 다른 한쪽이 읽는 흐름이다.

```
Producer ── write ──> kernel channel ── read ──> Consumer
```

이 차이를 잡고 들어가면 각 IPC API가 훨씬 명확하게 보인다.

---

## 5. Shared File: 가장 단순하지만 race condition이 보이는 IPC

가장 단순한 IPC는 파일이다.

프로세스 A가 파일에 쓰고, 프로세스 B가 같은 파일을 읽는다.

```
producer ── write ──> disk file <── read ── consumer
```

원문 가이드는 shared file을 가장 기본적인 IPC 방식으로 설명하면서, producer와 consumer가 동시에 파일에 접근하면 race condition이 발생할 수 있으므로 file lock이 필요하다고 설명한다.

예를 들어 producer가 아직 파일을 쓰는 중인데 consumer가 읽으면 어떻게 될까?

consumer는 완성되지 않은 데이터를 읽을 수 있다.

또는 두 writer가 동시에 파일에 쓰면 데이터가 섞일 수 있다.

따라서 shared file 기반 IPC에서는 다음 흐름이 필요하다.

```
producer:
lock
write
unlock

consumer:
lock
read
unlock
```

[코드 삽입 위치: shared file writer/reader 코드]

[그림7. file lock 없이 실행했을 때의 출력 결과]

[그림8. file lock 적용 후 producer/consumer 실행 결과]

이 실습의 핵심은 파일 입출력이 아니다.

핵심은 공유 자원에 접근할 때 동시성 제어가 필요하다는 점이다.

이 개념은 이후 shared memory, database lock, distributed lock까지 이어진다.

---

## 6. Shared Memory + Semaphore: 빠른 공유와 명시적 동기화

shared memory는 파일보다 더 직접적인 방식이다.

프로세스 A와 프로세스 B가 같은 메모리 영역을 매핑한다.

```
Process A ── mmap ──┐
                    ├── shared memory
Process B ── mmap ──┘
```

mmap()은 호출한 프로세스의 가상 주소 공간에 새로운 mapping을 만든다. MAP_SHARED로 매핑하면 같은 영역을 매핑한 다른 프로세스에게 업데이트가 보일 수 있다.

실습 흐름은 대략 다음과 같다.

```
writer:
shm_open()
ftruncate()
mmap()
sem_open()
write to shared memory
sem_post()

reader:
shm_open()
mmap()
sem_open()
sem_wait()
read from shared memory
```

[코드 삽입 위치: memwriter.c]

[코드 삽입 위치: memreader.c]

[그림9. memwriter 실행 결과]

[그림10. memreader가 shared memory에서 문자열을 읽은 결과]

여기서 sem_wait()와 sem_post()가 중요하다.

reader는 writer가 데이터를 쓰기 전까지 기다려야 한다.

```
reader:
sem_wait()
```

writer는 데이터를 다 쓴 뒤 reader에게 신호를 준다.

```
writer:
sem_post()
```

이 구조는 단순해 보이지만, 실제로는 매우 중요하다.

```
공유 메모리 = 데이터 평면
semaphore = 제어 평면
```

데이터 자체는 shared memory에 놓고, 접근 순서는 semaphore로 제어한다.

이 관점을 잡으면 운영체제의 IPC뿐만 아니라 database buffer pool, shared cache, multiprocessing queue 같은 구조도 더 잘 이해된다.

---

## 7. mmap을 Kafka와 연결해서 이해하기

여기서 조심해야 할 점이 있다.

Kafka가 단순히 "POSIX shared memory로 프로세스끼리 통신한다"는 뜻은 아니다.

Kafka를 이해할 때 중요한 연결점은 다음이다.

```
mmap/shared memory 실습
→ page cache
→ file-backed memory
→ append-only log
→ sequential I/O
→ zero-copy
→ Kafka
```

Kafka는 메시지를 메모리 객체로만 관리하려 하지 않고, 파일 시스템과 OS page cache를 적극적으로 활용하는 구조를 택한다. Kafka 설계 문서는 모든 데이터를 persistent log에 즉시 쓰며, 이 과정이 사실상 kernel page cache로 전달되는 것이라고 설명한다.

Confluent 문서도 Kafka가 메시지 저장과 캐싱을 위해 파일 시스템에 의존한다고 설명하며, linear read/write가 운영체제의 read-ahead와 write-behind 최적화를 잘 활용한다고 설명한다.

즉, Kafka를 이해할 때 핵심은 다음이다.

```
메시지를 객체로 계속 들고 있는 것이 아니라
append-only log에 쓰고
운영체제 page cache와 sequential I/O를 활용한다.
```

Kafka 설계 문서는 batching을 통해 더 큰 network packet, 더 큰 sequential disk operation, contiguous memory block을 만들 수 있고, 이것이 bursty random writes를 linear writes로 바꾸는 데 도움을 준다고 설명한다.

또한 Kafka는 page cache에서 socket으로 데이터를 전달할 때 Linux의 sendfile 기반 zero-copy 경로를 활용할 수 있음을 설명한다. 일반적인 경로에서는 kernel space와 user space 사이 복사가 여러 번 발생하지만, sendfile을 사용하면 page cache에서 network로 더 직접적으로 전달할 수 있다.

따라서 이번 IPC 실습에서 shared memory와 mmap을 배울 때는 단순히 "두 프로세스가 메모리를 공유한다"에서 끝내면 안 된다.

다음 질문까지 이어져야 한다.

- 왜 copy를 줄이는 것이 중요한가?

- 왜 user space와 kernel space 사이의 복사가 비용이 되는가?

- 왜 streaming system은 작은 메시지를 하나씩 처리하지 않고 batch로 묶는가?

- 왜 Kafka는 memory-only queue가 아니라 append-only log를 중심에 두는가?

- 왜 page cache가 성능에 큰 영향을 주는가?

[그림11. mmap/shared memory와 Kafka page cache 구조 연결도]

---

## 8. Pipe: 가장 Unix다운 IPC

pipe는 채널이다.

파일처럼 어딘가에 저장해두고 읽는 것이 아니라, 한 프로세스가 쓴 byte stream을 다른 프로세스가 읽는다.

```
writer process
   │
   ▼
kernel pipe buffer
   │
   ▼
reader process
```

Linux의 pipe와 FIFO는 단방향 IPC 채널이며, write end에 쓴 데이터는 read end에서 읽을 수 있다.

pipe의 핵심은 FIFO다.

```
먼저 쓴 byte가 먼저 읽힌다.
```

이 구조는 shell pipeline을 이해하는 데 중요하다.

```
cat access.log | grep ERROR | wc -l
```

이 명령어는 사실상 여러 프로세스가 pipe로 연결된 구조다.

```
cat ── pipe ──> grep ── pipe ──> wc
```

[코드 삽입 위치: pipe() parent-child 예제 코드]

[그림12. parent process가 pipe에 쓰고 child process가 읽은 결과]

여기서 눈여겨볼 부분은 file descriptor다.

```
pipefd[0] = read end
pipefd[1] = write end
```

프로세스는 pipe 자체를 직접 만지는 것이 아니라 file descriptor를 통해 읽고 쓴다.

즉, Linux에서는 파일, pipe, socket이 모두 file descriptor 추상화 아래에서 다뤄진다.

이 점을 이해하면 "Linux에서는 everything is a file"이라는 말이 조금 더 현실적으로 다가온다.

---

## 9. Named Pipe / FIFO: 이름이 있는 pipe

unnamed pipe는 보통 부모-자식 프로세스 사이에서 사용하기 쉽다.

하지만 서로 관계없는 프로세스가 pipe로 통신하려면 어떻게 해야 할까?

이때 named pipe, 즉 FIFO를 사용할 수 있다.

FIFO special file은 named pipe와 유사하며, 파일 시스템 경로를 통해 접근할 수 있다. 다만 프로세스들이 FIFO로 데이터를 교환할 때 실제 데이터는 파일 시스템에 기록되는 것이 아니라 커널 내부를 통해 전달된다.

```
mkfifo tester
```

```
Terminal 1:
cat tester

Terminal 2:
echo "hello" > tester
```

[명령어 삽입 위치: mkfifo tester 실습 명령어]

[그림13. Terminal 1에서 FIFO를 읽고 대기하는 화면]

[그림14. Terminal 2에서 FIFO에 데이터를 쓰는 화면]

[그림15. Terminal 1에서 FIFO 데이터를 수신한 결과]

여기서 중요한 점은 tester라는 이름이 실제 데이터 저장 파일이 아니라는 것이다.

tester는 커널 내부 pipe channel에 접근하기 위한 이름이다.

데이터는 디스크 파일에 쌓이는 것이 아니라 커널을 통해 전달된다.

이 실습을 통해 다음 차이를 구분할 수 있다.

```
regular file:
데이터가 파일에 저장됨

FIFO:
파일 경로는 이름 역할만 함
데이터는 커널 내부 pipe buffer를 통해 흐름
```

---

## 10. Message Queue: byte stream이 아니라 message 단위로 통신하기

pipe는 byte stream이다.

즉, 쓰는 쪽은 byte를 흘려보내고 읽는 쪽은 그 byte를 순서대로 읽는다.

반면 message queue는 message 단위로 데이터를 다룬다.

원문 가이드는 message queue가 message들의 sequence이며, 각 message는 byte 배열 형태의 payload와 양의 정수 type을 가진다고 설명한다.

```
Message Queue
 ┌──────────────┐
 │ type=1 msg1  │
 │ type=2 msg2  │
 │ type=3 msg3  │
 └──────────────┘
```

pipe와 message queue의 차이는 다음과 같다.

```
pipe:
byte stream 중심

message queue:
message boundary 중심
```

이 차이는 현대 메시징 시스템을 이해할 때 중요하다.

Kafka, RabbitMQ, NATS 같은 시스템을 공부하면 결국 "메시지 단위", "순서", "consumer", "ack", "offset" 같은 개념이 등장한다.

Linux message queue는 현대 분산 메시징 시스템과 같지는 않지만, "프로세스가 직접 서로 호출하지 않고 중간 큐를 통해 데이터를 주고받는다"는 구조를 이해하는 출발점이 된다.

[코드 삽입 위치: message queue sender 코드]

[코드 삽입 위치: message queue receiver 코드]

[그림16. sender가 type별 message를 전송한 결과]

[그림17. receiver가 message type에 따라 수신한 결과]

이 실습에서 볼 포인트는 다음이다.

- pipe는 byte stream이다.

- message queue는 message boundary가 있다.

- message type을 기준으로 선택적으로 받을 수 있다.

- producer와 consumer가 직접 강하게 결합되지 않는다.

---

## 11. Socket: Client-Server 모델의 실제 구현

socket은 IPC 중에서도 가장 중요하다.

왜냐하면 socket은 같은 머신 안의 프로세스뿐 아니라, 다른 머신에 있는 프로세스와도 통신할 수 있기 때문이다.

원문 가이드는 Unix domain socket은 같은 host의 프로세스 간 channel 기반 통신을 가능하게 하고, network socket은 서로 다른 host의 프로세스 간 통신까지 확장한다고 설명한다.

socket을 사용한 client-server 흐름은 다음과 같다.

```
server:
socket()
bind()
listen()
accept()
read()
write()
close()

client:
socket()
connect()
write()
read()
close()
```

server는 먼저 대기한다.

```
listen()
accept()
```

client는 server에게 연결을 시도한다.

```
connect()
```

연결이 성립되면 양쪽은 file descriptor를 통해 데이터를 읽고 쓴다.

```
client fd ───────── TCP connection ───────── server fd
```

[코드 삽입 위치: iterative server 코드]

[코드 삽입 위치: client 코드]

[그림18. server가 localhost에서 listen하는 결과]

[그림19. client가 server에 요청을 보내는 결과]

[그림20. server가 client 요청을 echo하는 결과]

여기서 원문 가이드의 중요한 지점은 iterative server다.

iterative server는 한 번에 하나의 client를 처리한다. 개발 실습에는 적합하지만, 특정 client 처리가 오래 걸리면 뒤의 client들이 기다려야 한다. 원문 가이드는 production-grade server는 보통 multi-processing, multi-threading 또는 이 둘의 조합으로 concurrent하게 처리한다고 설명한다.

이 지점이 바로 Nginx, Redis, PostgreSQL, Kubernetes API Server 같은 서버 구조로 연결된다.

단순 server는 다음과 같다.

```
client1 ──> server 처리
client2 ──> 대기
client3 ──> 대기
```

동시성 server는 다음과 같다.

```
client1 ──> worker1
client2 ──> worker2
client3 ──> worker3
```

[그림21. iterative server와 concurrent server 비교 그림]

---

## 12. Signal: 데이터 전달보다는 이벤트 알림

signal은 다른 IPC와 성격이 조금 다르다.

pipe, queue, socket, shared memory는 데이터를 주고받는 데 초점이 있다.

signal은 주로 이벤트를 알리는 데 사용한다.

예를 들어 다음과 같은 상황이다.

```
parent process ── SIGTERM ──> child process
```

child process는 signal handler를 통해 종료 전에 정리 작업을 할 수 있다.

원문 가이드는 signal handling 예제에서 POSIX 권장 방식인 sigaction()을 사용한다고 설명한다.

[코드 삽입 위치: fork + sigaction + SIGTERM 예제 코드]

[그림22. parent가 child에게 SIGTERM을 보내는 결과]

[그림23. child가 signal을 받고 graceful termination하는 결과]

signal을 학습할 때는 다음을 구분해야 한다.

```
pipe/socket/message queue:
데이터 통신

signal:
이벤트 알림
```

예를 들어 운영 환경에서 kill -TERM <pid>를 보내는 것은 프로세스에게 "정상 종료 준비를 하라"고 알리는 이벤트에 가깝다.

Kubernetes에서도 Pod 종료 시 컨테이너 프로세스에 SIGTERM을 보내고, grace period 이후에도 종료되지 않으면 SIGKILL로 강제 종료한다.

따라서 signal은 단순한 종료 명령이 아니라 Linux 프로세스 생명주기와 graceful shutdown을 이해하는 핵심이다.

---

## 13. 동시성 제어를 코드 레벨에서 이해하기

IPC 실습의 진짜 목적은 단순히 통신이 되는 것을 확인하는 것이 아니다.

진짜 목적은 동시성 제어가 왜 필요한지 코드 레벨에서 체감하는 것이다.

특히 shared file과 shared memory에서 이 문제가 잘 드러난다.

두 프로세스가 같은 자원에 접근한다고 해보자.

```
Process A: write
Process B: read
```

타이밍이 맞지 않으면 B는 A가 다 쓰기 전에 읽을 수 있다.

또는 두 프로세스가 동시에 쓸 수 있다.

```
Process A: write "hello"
Process B: write "world"
```

결과는 예측하기 어렵다.

그래서 lock, semaphore, mutex 같은 동기화 도구가 필요하다.

```
critical section 진입 전:
lock

공유 자원 접근:
read/write

critical section 종료 후:
unlock
```

shared memory 실습에서는 semaphore가 이 역할을 한다.

```
writer:
write shared memory
sem_post()

reader:
sem_wait()
read shared memory
```

이 구조는 단순한 C 코드 실습이지만, 실제 시스템의 핵심과 연결된다.

- database row lock

- Redis distributed lock

- Kafka consumer offset commit

- Kubernetes leader election

- OS scheduler의 critical section

- multi-threaded server의 shared state 보호

결국 동시성 제어는 "여러 실행 흐름이 하나의 공유 자원에 접근할 때 순서를 어떻게 보장할 것인가"의 문제다.

---

## 14. 실습 순서 추천

Docker 환경은 이미 구성되어 있으므로, 실습은 다음 순서로 진행하는 것을 추천한다.

### Step 1. 프로세스 격리 확인

목표는 프로세스가 기본적으로 서로의 메모리를 공유하지 않는다는 것을 이해하는 것이다.

[코드 삽입 위치: fork 후 parent/child 주소값 출력 코드]

[그림24. parent/child에서 같은 변수 주소 또는 값 변화를 비교한 결과]

확인할 질문:

- parent와 child는 같은 변수를 보는가?

- fork 이후 값 변경이 서로에게 영향을 주는가?

- copy-on-write 관점에서 어떻게 해석할 수 있는가?

---

### Step 2. unnamed pipe 실습

목표는 부모-자식 프로세스가 커널 pipe buffer를 통해 byte stream을 주고받는 구조를 이해하는 것이다.

[코드 삽입 위치: pipe() 예제 코드]

[그림25. parent가 write하고 child가 read한 결과]

확인할 질문:

- pipefd[0]과 pipefd[1]의 역할은 무엇인가?

- 왜 사용하지 않는 read end/write end를 close해야 하는가?

- pipe는 양방향인가 단방향인가?

---

### Step 3. named pipe / FIFO 실습

목표는 서로 관계없는 두 프로세스가 파일 시스템 이름을 통해 pipe에 접근하는 구조를 이해하는 것이다.

[명령어 삽입 위치: mkfifo 실습 명령어]

[그림26. FIFO 파일 생성 결과]

[그림27. 한 터미널에서 cat으로 읽기 대기하는 화면]

[그림28. 다른 터미널에서 FIFO에 문자열을 쓰는 화면]

확인할 질문:

- FIFO 파일 자체에 데이터가 저장되는가?

- writer가 없을 때 reader는 어떻게 동작하는가?

- reader가 없을 때 writer는 어떻게 동작하는가?

---

### Step 4. shared memory + semaphore 실습

목표는 두 프로세스가 같은 메모리 영역을 매핑하고, semaphore로 순서를 제어하는 구조를 이해하는 것이다.

[코드 삽입 위치: shm writer 코드]

[코드 삽입 위치: shm reader 코드]

[그림29. /dev/shm 확인 결과]

[그림30. writer 실행 결과]

[그림31. reader 실행 결과]

확인할 질문:

- shm_open()은 무엇을 생성하는가?

- ftruncate()는 왜 필요한가?

- mmap()은 무엇을 프로세스 주소 공간에 연결하는가?

- MAP_SHARED와 MAP_PRIVATE는 어떻게 다른가?

- semaphore를 제거하면 어떤 문제가 생길 수 있는가?

---

### Step 5. message queue 실습

목표는 byte stream이 아니라 message 단위로 데이터를 주고받는 모델을 이해하는 것이다.

[코드 삽입 위치: message sender 코드]

[코드 삽입 위치: message receiver 코드]

[그림32. sender 실행 결과]

[그림33. receiver 실행 결과]

확인할 질문:

- pipe와 message queue는 무엇이 다른가?

- message type은 왜 유용한가?

- FIFO 순서를 깨고 type 기반으로 받을 수 있다는 것은 어떤 의미인가?

---

### Step 6. socket client-server 실습

목표는 Client-Server 모델이 실제 socket API로 어떻게 구현되는지 이해하는 것이다.

[코드 삽입 위치: socket server 코드]

[코드 삽입 위치: socket client 코드]

[그림34. server listen 결과]

[그림35. client connect 결과]

[그림36. request-response 출력 결과]

확인할 질문:

- server는 왜 bind()와 listen()을 하는가?

- client는 왜 connect()를 하는가?

- accept()가 반환하는 file descriptor는 무엇을 의미하는가?

- 하나의 server socket과 connection socket은 어떻게 다른가?

---

### Step 7. signal 실습

목표는 signal이 데이터 통신이 아니라 이벤트 알림이라는 점을 이해하는 것이다.

[코드 삽입 위치: signal handler 코드]

[그림37. parent가 child에게 signal을 보내는 결과]

[그림38. child가 graceful shutdown하는 결과]

확인할 질문:

- SIGTERM과 SIGKILL은 무엇이 다른가?

- signal handler 안에서 어떤 작업을 조심해야 하는가?

- Kubernetes Pod 종료 흐름과 어떻게 연결되는가?

---

## 15. IPC별 핵심 비교

---

## 16. 이번 학습의 핵심 정리

이번 IPC 학습에서 가장 중요한 문장은 다음이다.

> 프로세스는 기본적으로 서로 격리되어 있고, IPC는 그 격리된 프로세스들이 안전하게 정보를 주고받기 위한 운영체제의 통신 장치다.

Pipe는 Unix 철학을 이해하게 해준다.

Socket은 Client-Server 모델을 코드 레벨에서 이해하게 해준다.

Shared memory와 mmap은 데이터 복사 비용, page cache, zero-copy, Kafka 같은 현대 스트리밍 시스템의 성능 설계를 이해하게 해준다.

Semaphore는 공유 자원 접근에서 왜 동시성 제어가 필요한지를 보여준다.

Message queue는 producer와 consumer를 직접 연결하지 않고 중간 큐를 통해 느슨하게 결합하는 사고방식을 보여준다.

Signal은 프로세스 생명주기와 graceful shutdown을 이해하는 출발점이 된다.

결국 IPC는 단순한 Linux API 모음이 아니다.

IPC는 다음 질문에 답하기 위한 학습이다.

```
격리된 실행 단위들이
어떻게 데이터를 공유하고
어떻게 순서를 맞추고
어떻게 실패 없이 협력하는가?
```

이 질문은 운영체제에서 시작하지만, 현대 백엔드와 클라우드 시스템 전체로 이어진다.

Docker, Kubernetes, Kafka, Redis, Nginx, PostgreSQL을 더 깊게 이해하려면 IPC를 한 번은 직접 코드로 만져봐야 한다.

이번 실습의 목표는 바로 그것이다.

---

## 17. 다음 글에서 이어갈 수 있는 주제

이번 글에서는 IPC 메커니즘을 하나씩 실습하며 큰 그림을 잡았다.

다음 글에서는 다음 주제로 확장할 수 있다.

1. strace로 IPC system call 흐름 추적하기

1. pipe와 socket의 kernel buffer 차이 보기

1. ipcs, /dev/shm, /proc/<pid>/fd로 IPC 리소스 관찰하기

1. shared memory에서 semaphore 제거 후 race condition 재현하기

1. socket server를 iterative 방식에서 multi-process 방식으로 확장하기

1. mmap/page cache 관점에서 Kafka가 빠른 이유 정리하기

1. Docker container 안에서 IPC namespace가 어떻게 격리되는지 확인하기

[그림39. /proc//fd에서 pipe/socket fd 확인 결과]

[그림40. strace로 socket system call 흐름을 추적한 결과]

[그림41. Docker container 내부 IPC namespace 확인 결과]