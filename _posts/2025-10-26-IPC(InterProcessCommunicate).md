---
layout: post
title: "IPC(Inter Process Communicate)"
categories: [ComputerScience, OperatingSystem]
author: cotes
published: true
---

## Linux와 Windows의 프로세스간 통신(IPC) 메커니즘 

목차

- Shared Memory (with semaphore)
- Shared File
- Pipes (named and unnamed)
- Sockets
- Signals

IPC 개요

### IPC 개요 (Inter-Process Communicate 이란?)
프로세스 간 통신 (IPC, Inter Process Communication)은 개별 프로세서들이 데이터를 교환하고 동기화하기 위한 운영체제의 기술입니다. 현대 운영체제에서는 다중 프로세스가 협업 및 자원 공유를 위해 IPC는 필수 입니다. IPC에는 공유 메모리, 파이프, 메시지 큐, 소켓, 시그널 등 다양한 메커니즘이 있으며 각각 장단점과 알맞은 활용 사례들이 있습니다. 본 글에서는 Linux와 Windows 환경에서 IPC 메커니즘의 동작 방식, 관련 시스템 호출, 프로세스 간 데이터 흐름과 타이밍을 살펴보고, 가상머신 환경에서의 IPC, 로컬 루프백(loopback) 인터페이스와 IPC의 비교, 그리고 서로 다른 IPC를 활용한 현실적인 시나리오 3가지를 다룹니다.

### 공유 메모리 (Shared Memory)
공유 메모리를 이용한 프로세스 간 통신 개념도. 두 프로세스 A와 B가 동일한 메모리 영역을 공유하여 한 프로세스가 쓰면 다른 프로세스가 읽는다. 각 프로세스는 공유 메모리 세그먼트를 자신의 가상 주소 공간에 연결하여 직접 데이터를 주고 받는다. 이 방식은 중간 커널 버퍼를 거치는 복사 과정을 줄여 고속 통신이 가능하지만, 동시에 접근할 때 데이터 불일치가 발생하지 않도록 세마포어 등의 동기화 비법이 필요하다.

공유 메모리의 특징
1. 빠른 데이터 전송
2. 간단한 구현
3. 동기화 필요

[기본 구조]
```
   [Writer Process]    [Reader Process]
       │                 │
 shm_open()         shm_open()
 mmap()   ─────────► mmap()
       │                 │
  write("Hello")     read("Hello")
       ▼                 ▼
   +---------------------------------------+
   |  Shared memory segment (/dev/shm/...) |
   +---------------------------------------+

```

[그림1. 공유 메모리를 활용한 IPC]

![BitOperations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FbnOLMP%2FbtssfUfwnQX%2FAAAAAAAAAAAAAAAAAAAAAM7hhl4C5q04YESmTrkY_A5_DH8d2inF2oioHVnQVP6-%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1761922799%26allow_ip%3D%26allow_referer%3D%26signature%3D0dph7NeqcgVPJ9NasgSW1SYlszk%253D)

[그림1.2 공유 메모리 구조]

동작순서 (POSIX 버전 기준)
1. shm_open(): 공유 메모리 객체 생성(또는 접근)
2. ftruncated(): 크기 지정
3. nmap(): 해당 영역을 가상 메모리에 맵핑
4. 세마포어(sem_open, sem_wait, sem_post): 접근 동기화
5. munmap(), shm_unlink(): 해제

**기본원리**: 공유 메모리는 둘 이상의 프로세스가 동일한 메모리 블록을 함께 접근하는 방식의 IPC 입니다. **한 프로세스가 메모리 블록에 기록한 변경 사항을 다른 프로세스들이 곧바로 볼 수 있으므로, 데이터가 커널을 경유하여 복사될 필요없이 곧바로 공유됩니다. ** 이는 파이프, FIFO, 메시지 큐처럼 커널 버퍼를 경유하는 메시지 전달보다 효율적입니다. 예를 들어 파일을 한 프로세스에서 읽어 다른 프로세스로 전달하는 경우, 파이프나 메시지 큐를 쓰면 최대 4번의 데이터 복사(프로세스 -> 커널, 커널 -> 프로세스 *2회)가 발생하지만, 공유 메모리를 쓰면 2번의 복사(파일 -> 공유메모리, 공유메모리 -> 다른 프로세스 메모리)로 끝납니다. 따라서 대용량 데이터나 고빈도 통신에 유리합니다.


**Linux에서의 구현**: 유닉스 계열 시스템은 전통적으로 System V 공유 메모리와 POSIX 공유 메모리 두 가지 인터페이스를 제공합니다. System V API에서는 **ftok()**로 Key를 생성하고 **shmget()** 호출로 공유 메모리 세그먼트를 생성합니다. 성공시 공유 메모리에 대한 식별자를 얻으며, **shmat()**를 통해 프로세스의 가상 주소 공간에 해당 세그먼트를 attaching하여 사용합니다. 이후 해당 주소를 통해 일반 메모리 다루듯 데이터를 R/W를 할 수 있습니다. 

작업을 마치면 **shmdt()**로 세그먼트를 Detach하고, 마지막 프로세스가 detach 한 후에는 **shmctl(IPC_RMID)**로 커널에서 공유 메모리를 제거합니다. POSIX 공유 메모리(shm_open, mmap등)
는 이와 유사하나 이름 기반 식별을 사용하고 파일시스템의 **/dev/shm**
같은 영역을 활용합니다. 동기화는 공유 메모리의 필수 요소인데, 여러 프로세스가 동시에 같은 데이터를 수정하지 않도록 Semaphore, mutex 등의 잠금 기법이나 조건변수 등을 함께 사용해야 합니다. 이러한 추가 동기화 작업으로 인해 코드 복잡성이 높아질 수 있다는 단점이 있습니다.

**Windows에서의 구현**: Windows는 POSIX와 동일한 형태의 *shmget/shmat** 호출은 없지만, File mapping을 통해 유사한 공유 메모리를 제공합니다. **CreateFileMapping**함수를 특수한 파일(페이지 파일)에 대해 호출하면 이름 붙은 공유 메모리 객체를 생성할수 있습니다.

이러서 **MapViewOfFile**로 그 메모리 객체를 프로세스 주소 공간에 매핑하면, 동일한 이름의 메모리 객체를 연 다른 프로세스들과 메모리 내용을 공유하게 됩니다. 이 방식은 구현상 파일을 이용하지만 Disk I/O 없이 운영체제의 페이지 파일을 백킹 스토어로 활용하므로 매우 효율적이며,Windows 보안 속성을 적용하여 무단 접근을 방지할수도 있습니다.

Windows 공유 메모리는 시스템이 부팅된 동안엔 지속적이어서 (명시적으로 해제 전까지 메모리 객체 유지)프로세스가 종료되어도 남아 있을 수 있습니다. 단, 네트워크를 통한 공유 메모리는 지원되지 않으며 오직 동일한 로컬 시스템 내 프로세스 간에만 동작합니다. Windows에서도 동시 접근 조율을 위해 **CreateSemaphore**등 동기화 객체를 별도로 유지해야 합니다.

Writer (memwriter.c)
```c
int fd = shm_open("/shMemEx", O_CREAT | O_RWDR, 0666);
ftruncate(fd, ByteSize);
char *memptr = mmap(NULL, ByteSize, PORT_READ | PROT_WRITE, MAP_SHARED, fd, 0);

sem_t *sem = sem_open("/semEx", O_CREAT, 0666, 0); // 초기값 0
strcpy(memptr, "This is the way the world ends...");
sem_posts(sem); // 세마포어 증가 -> Reader 접근 허용
```

Reader Process
```c
int fd = shm_open("/shMemEx", O_RDWR, 0666);
char *memptr = mmap(NULL, ByteSize, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);

sem_t *sem = sem_open("/semEx", 0, 0666, 0);
sem_wait(sem); // Writer가 sem_post 할 때까지 대기
printf("%s\n", memptr);
sem_post(sem);
```

두 프로세스가 **/dev/shm/shMemEx **라는 공유 메모리 세그먼트를 통해 직접 통신하며, **sem_wait / sem_post **로 race condition을 방지합니다.


### Shared File 기반 IPC
> 디스크에 있는 같은 파일을 여러 프로세스가 번갈아 접근

공유 파일은 가장 기본적인 IPC 메커니즘 입니다. 이 메커니즘의 기본 시나리오는 하나의 프로세스(producer)가 파일을 생성하고 데이터를 쓰면, 다른 프로세스(consumer)가 동일한 디스크 파일에서 데이터를 읽는 방식입니다.

공유 파일이 포함된 IPC의 장점은 매우 유연하다는 것입니다. 공유되는 데이터는 방대한 양의 임의의 바이트일 수 있으며, 이는 파일 공유를 유연선성을 가진 IPC 메커니즘으로 만듭니다.

하지만 프로그래밍에는 항상 상충 관계가 존재하며, 공유 파일 접근의 단점은 읽기든, 쓰기든 파일 접근 속도가 상대적으로 느리다는 것입니다.

[기본구조]
```
   [Producer Process]         [Consumer Process]
        │                   │
        │ write()           │ read()
        ▼                   ▼
       +----------- 공유 파일 -------------+
       | data.dat (on disk filesystem)   |
       +---------------------------------+

```

[핵심 문제]
- Producer Process와 Writer Process가 동시에 접근하면 데이터가 섞이거나 깨짐. 
- File lock으로 상호 배제(Mutual Execlusion) 필요.

[동기화 도구: fcntl() / flock()]
- Exclusion lock(F_WRLCK) -> 쓰기 전용, 한 프로세스만 접근 가능
- Shared lock(F_RDLCK) -> 여러 Reader 동시 접근 가능, 하지만 writer 금지

Producer Process
```c
struct flock lock = {F_WRLCK, SEEK_SET, 0, 0, getpid()};
fnctl(fd, F_SETLK, &lock);    // 쓰기 락 획득
write(fd, DataString, len);   // 데이터 쓰기
lock.l_type = F_UNLCK;        
fcntl(fd, F_SETLK, &lock);    // 락 해제
```

Writer Process
```c
struct flock lock = {F_RDLCK, SEEK_SET, 0, 0, getpid()};
fcntl(fd, F_SETLK, &lock);    // 읽기 락 획득
read(fd, buf, sizeof(buf));   // 파일 읽기
lock.l_type = F_UNLCK;
fcntl(fd, F_SETLK, &lock);    // 락 해제
```

file Lock API 상세
표준 시스템 라이브러리의 잠금 API는 동기화를 위해 다음과 같이 요약할 수 있습니다. 

1. 베타적 잠금 (Exclusive lock): producer는 파일에 쓰기 전에 베타적 잠금을 획득해야 합니다.
 - 최대 하나의 프로세스만 베타적 잠금을 보유할 수 있습니다. 이는 다른 프로세스가 락이 해제될때까지 파일에 접근하는것을 막아 경쟁 조건을 배제합니다.

 - Producer 프로그램은 잠금을 베타적(읽기/쓰기) 잠금인 F_WRLCK로
 설정합니다.

2. 공유 잠금 (Shared Lock): Consumer는 파일에서 읽기 전에 최소한 공유 잠금을 획득해야 합니다.

여러 Reader가 동시에 공유 잠금을 보유할 수 있어 효율성을 높입니다.
그러나, 단 하나의 Reader라도 공유 잠금을 보유하고 있으면 어떤 writer도 파일에 접근할 수 없습니다. 읽기 전용 잠금(F_RDLCK)은 다른 프로세스가 파일에 쓰는 것을 방지하지만, 다른 프로세스가 파일에서 읽는 것은 허용합니다.

[잠금 구현 함수]
표준 I/O 라이브러리는 파일에 대한 베타적 잠금과 공유 잠금을 검사하고 조작하는데 사용할 수 있는 유틸리티 함수인 **fcntl**을 포함합니다. 이 함수는 프로세스 내에서 파일을 식별하는 음수가 아닌 정수 값인 파일 디스크립터를 통해 작동합니다. Linux는 fcntl의 얇은 Wrapper인 라이브러리 함수 **flock**도 제공합니다.

- fcntl 함수는 잠금 구조체(struct flock)을 사용하여 잠금 유형을 지정하고 작업을 수행합니다.

- 잠금 설정 작업(F_SETLK)은 블로킹되지 않고 즉시 반환되지만, F_SETLKW 플래그(w는 wait을 의미)를 사용하면 잠금을 획득할 수 있을때까지 호출이 블로킹 됩니다.

- 잠금은 fcntl을 호출하여 명시적으로 해제하거나(F_UNLCK로 설정) 파일이 닫히거나 프로세스가 종료될때 임시적으로 해제됩니다.

- Consumer 프로그램은 **fcntl**의 **F_GETLK** 작업을 사용하여 파일에 잠금이 있는지 확인할 수 있습니다.

공유 파일과 공유 메모리 접근 방식 모두 대용량 데이터 스트림 (massively large stream of data)를 처리하는 현대 애플리케이션에는 적합하지 않습니다. 이러한 상황에는 Channel 유형이 더 적합합니다.

### 파이프(pipes)
파이프는 한 프로세스의 출력(표준 출력 등)을 다른 프로세스의 입력 (표준 입력)으로 연결하는 단방향 바이트 스트림 IPC 입니다. 파이프는 익명 파이프 (anonymous pipe)와 이름있는 파이프(named pipe, UNIX의 FIFO)가 있으며, 프로세스 간 한쪽 방향으로 연속된 바이트 데이터를 전달하는데 사용됩니다. 기본적으로 파이프는 생성한 프로세스가 종료되면 함께 소멸되는 일시적 통로이며, 커널이 관리하는 메모리 버퍼를 통해 데이터를 주고받습니다.

[파이프 통신의 주요 특징]
1. 단방향 통신
2. 부모-자식 프로세스 간 통신
3. 파일 기반 통신
4. 단순한 데이터 전달

![BitOperations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FddPAsa%2FbtsshqEIfhG%2FAAAAAAAAAAAAAAAAAAAAACl77vMzkeGmslnO1qJ9Nw8CDQWdaQUA_afC-tCO5XLy%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1761922799%26allow_ip%3D%26allow_referer%3D%26signature%3DN1NT88NzE2EiIBSyxzef%252FMfzDKc%253D)
[그림2: pipe]

[익명 파이프(anonymous pipe)]
익명 파이프를 이용한 부모-자식 프로세스 통신: 부모 프로세스가 **pipe()** 시스템 콜로 파이프를 생성하면 커널이 파이프용 메모리 버퍼와 두 개의 파일 디스크립터(읽기 끝, 쓰기 끝)를 만들어줍니다. 

**fork()**로 자식 프로세스를 생성하면 이 파이프 디스크립터들이 복제되어 자식에도 존재하게 됩니다. 부모는 파이프의 쓰기 끝으로 데이터를 쓰고, 자식은 읽기 끝에서 데이터를 읽어들여 통신합니다. 파이프 버퍼는 커널 내부에 고정 크기로 존재하며, 쓰기시 버퍼가 가득차면 쓰는 측이 블록되고, 읽기 시 버퍼가 비어 있으면 읽는 측이 블록되어 Producer-Consumer 형태로 동작합니다.

[Linux 기반 파이프 예제]
```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

int main() {
    int pipefd[2];   // 파이프 파일 디스크립터 저장 배열
    pid_t cpid;      // 자식 프로세스 ID
    char buf;        // 읽기 버퍼
    char *message = "Hello, child process!\n";

    if (pipe(pipefd) == -1) { // 파이프 생성
        perror("pipe");
        exit(EXIT_FAILURE);
    }

    cpid = fork();            // 프로세스 복제
    if (cpid == -1) {
        perror("fork");
        exit(EXIT_FAILURE);
    }

    if (cpid == 0) {         // 자식 프로세스
        close(pipefd[1])     // 쓰기 끝 닫기

        // 파이프에서 데이터 읽기
        while (read(pipefd[0], &buf, 1) > 0
              write(STDOUT_FILENO, &buf, 1);

        write(STDOUT_FILEINFO, "\n", 1);
        close(pipefd[0]);    // 읽기 끝 닫기
        exit(EXIT_SUCCESS);  
    } else {                 // 부모 끝 프로세스
        close(pipefd[0]);  // 읽기 끝 닫기

        // 파이프로 데이터 쓰기
        write(pipefd[1], message, strlen(message));  
        close(pipefd[1])  // 쓰기 끝 닫기
        wait(NULL);       // 자식 프로세스가 종료될때까지 대기
        exit(EXIT_SUCESS);
    }
}
```
1. pipe() 함수를 호출하여 파이프를 생성하고, 파이프의 읽기 끝과 쓰기 끝을 나타내는 파일 디스크립터를 pipefd 배열에 저장
2. fork() 함수를 호출하여 현재 프로세스를 복제하여 부모 프로세스와 자식 프로세스를 생성합니다.
3. 자식 프로세스는 파이프의 쓰기 끝을 닫고, 파이프에서 데이터를 읽어 표준 출력으로 출력합니다.
4. 부모 프로세스는 파이프의 읽기 끝을 닫고, 파이프에 문자열을 쓴 후 쓰기 끝을 닫습니다.
5. 부모 프로세스는 자식 프로세스가 종료될때까지 대기합니다.

**리눅스 익명 파이프**: **pipe()** 시스템 호출을 사용하여 생성하며, 이 때 반환되는 두 개의 파일디스크립터(pipefd[0] = Read end, pipefd[1] = Write end)를 통해 파이프를 다룹니다. 일반적으로 파이프는 부모와 자식 프로세스 사이의 통신에 사용됩니다. 한 프로세스(예: 부모)가 **fork()**를 호출하면 자식은 보모의 열린 파일 디스크립터를 복사받는데, 이때 파이프의 양 끝점 디스크립터도 복제되므로 부모와 자식이 동일한 파이프에 접근할 수 있게 됩니다.

이후 부모 프로세스는 쓰기 끝으로 데이터를 출력하고, 자식 프로세스는 읽기 끝으로 입력을 받아 처리합니다. 파이프는 단방향이라 한쪽에서 쓰기만, 반대쪽에서 읽기만 가능하며, 양방향 통신이 필요하면 파이프 두 개(각 방향 하나씩) 혹은 소켓쌍 등을 사용해야 합니다.

**Windows 익명 파이프**: Windows에서도 **CreatePipe()** 함수를 통해 유사하게 부모-자식 간 파이프를 만들 수 있습니다. 동작 개념은 Linux와 비슷하나 Windows 파이프 핸들러는 파일이 아닌 커널 오브젝트로 취급됩니다. Windows 익명 파이프는 부모-자식 관계로 연결된 프로세스 사이에서만 사용 가능하며, 네트워크나 무관한 프로세스 간에는 사용할 수 없습니다. 표준 입출력 리디렉션에 주로 쓰이며, 부모가 자식의 입력/출력을 자신의 파이프로 물려받아 통신하는 형태로 활용됩니다. 양방향으로 통신하려면 Linux와 마찬가지로 두 개의 파이프를 만들어 교차 연결해야 합니다.

**데이터 흐름**: 파이프는 커널 내의 환형 버퍼(Circular buffer)를 매개로 전달합니다. 쓰는 프로세스는 파이프와 쓰기 디스크립터를 통해 버퍼에 데이터를 쓰고, 읽는 프로세스는 읽기 디스크립터로 버퍼에서 데이터를 읽어갑니다. 커널은 파이프 버퍼를 다 채울 경우 쓰는 쪽을 잠시 정지(block)시켜 자동 흐름 제어를 해줍니다. 

이러한 동작으로 Producer-Consumer 문제를 자연스럽게 해결하며, 동기화는 커널이 책임집니다. (명시적 잠금 불필요). 한편, 한쪽 끝의 모든 디스크립터가 닫히면 다른 쪽에서는 EOF나 **SIGPIPE** 시그널을 통해 파이프 종료를 감지하게 됩니다. 따라서 파이프 사용 후에는 필요 없는 끝을 반드시 **close()** 하여야 하며, 그래야 상대 프로세스가 종료를 정확히 인지하고 블로킹을 해제하는 등 자원 누수가 없습니다.

### 이름있는 파이프 (FIFO 및 Named Pipe)
**유닉스 FIFO**: 이름 있는 파이프(FIFO)는 파일 시스템에 특별한 파일 형태로 존재하는 파이프 입니다. **mkfifo()** 또는 **mknod()**로 명시적으로 생성하며, 경로를 가지므로 관련 없는 프로세스들끼리도 이름을 알고 있으면 해당 FIFO를 통해 통신할 수 있습니다.

사용 방법은 한 프로세스가 FIFO 파일을 쓰기 모드로 열고, 다른 프로세스가 읽기 모드로 열면 커널이 둘 사이에 파이프와 동일하게 데이터 흐름을 연결합니다. FIFO 파일은 일반 파일처럼 경로를 가지므로 시스템 재부팅 전까지 지속될 수 있고, 다시 사용하면 **unlink()**로 지워서 없앨 수 있습니다. 

예를 들어 **mkfifo /tmp/my_pipe**로 FIFO를 만든 뒤 한 셸에서 **gzip -9 -c < tmp/my_pipe > out.gz &**로 백그라운드 압축 프로그램을 실행하고, 다른 셸에서 **cat largefile > /tmp/my_pipe**로 데이터를 보내 압축하는 식의 파이프라인을 구축할 수 있습니다. 이렇듯 FIFO를 사용하면 중간 임시 파일을 생성하지 않고 프로세스간 데이터를 주고받을 수 있어 편리합니다.

**Windows Named Pipe**: Windows에서도 Named Pipe라는 이름으로 유사 개념을 제공합니다. 하지만 구현과 동작 면에서 몇가지 차이점이 있습니다. Windows의 이름있는 파이프는 파일 시스템의 일반 경로를 나타내지 않으며, 시스템이 별도로 관리하는 **\\.\pipe\** 네임스페이스 아래에 생성됩니다.

예를 들어 이름 "foo"인 파이프의 전체 경로는 **\\.pipe\foo**처럼 표현됩니다. 한 프로세스가 **CreateNamedPipe()**로 서버용 파이프를 만들고 클라이언트 프로세스는 **ReadFile(), WriteFile()**로 데이터를 주고받을 수 있습니다. Windows 이름있는 파이프는 기본적으로 통신이 끝나면 파이프 객체가 소멸하는 휘발성 특징을 가지며, 마지막 핸들이 닫히면 커널이 파이프를 제거합니다.

또한 전이중(duplex)통신을 기본 지원하므로 양쪽 어느 방향으로도 R/W 가능하게 생성할 수 있습니다. 특별한 점은 Windows 이름 파이프는 네트워크 경유 통신도 지원하여, **\\HostName\pipe\PipeName**형식으로 다른 호스트의 파이프에 접속할 수도 있습니다. 권한 및 인증은 Windows 보안 토큰으로 관리되어 허용된 클라이언트만 접속하도록 설정할 수 있습니다.

**비교 및 활용**: 유닉스 FIFO와 Windows named Pipe 모두 프로세스 사이에 영속적인 이름을 통해 데이터를 스트림으로 교환한다는 공통점이 있습니다. Linux/Unix에서는 FIFO 파일이 실제 파일 시스템 노드로 존재하기에 ls로 확인하거나 chmod로 permission 변경도 가능하지만, Windows에서는 **\\.\pipe** 경로로만 접근되고 일반 파일처럼 다룰수는 없습니다.

### 메시지 큐(Message Queues)
**메시지 큐를 통한 통신 개념**: 송신 프로세스는 커널 내부의 메시지 큐에 메시지를 보관하고, 수신 프로세스는 큐로부터 메시지를 차례로 꺼내 간다. 메시지 큐는 커널 공간에 유지되는 연결 리스트 형태의 버퍼로 구현되며 각 메시지는 식별을 위한 type과 본문 데이터로 구성됩니다. 프로세스들은 **msgsnd** 시스템 호출로 큐에 메시지를 추가하고, **msgrcv** 호출로 수신하여 데이터를 얻습니다.

커널은 각 메시지에 메시지 타입(사용자 정의 분류용 숫자)과 길이를 함께 저장하고 FIFO(선입선출) 순서로 메시지를 큐에 쌓습니다. 수신 프로세스는 **msgcrv()**를 호출시 원하는 메시지 타입을 지정해 해당 타입의 첫 번째 메시지를 받을수도 있고, 특정 타입을 지정하지 않으면 기본적으로 가장 먼저 들어온 메시지를 받습니다. 

POSIX 메시지 큐(mq_open, nq_send, mq_receive등)는 비슷한 기능을 제공하며, 구현상 Linux에서는 가상 파일시스템인 **/dev/mqueue**에 각각의 큐가 파일처럼 나타납니다. 두 방식 모두 커널 공간에 큐 버퍼를 두고 프로세스들 간에 비동기 메시지 전달을 가능하게 합니다.

![BitOperations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2Fbs3nRQ%2FbtssvvY5DJq%2FAAAAAAAAAAAAAAAAAAAAAAzV8wNbAJKa0Pu151ohq9RDsMbsx1lG5BvubUPhYJfu%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1761922799%26allow_ip%3D%26allow_referer%3D%26signature%3DM0NAuSYO5zBenF1PO81Ls35qL%252FQ%253D)
[그림3. 메시지 큐 구조]

메시지의 큐의 주요 특징
1. **비동기 통신**
- 메시지 큐는 송신자(Sender)와 수신자(Receiver)가 동시에 동작할 필요가 없습니다.
- 송신자는 메시지를 큐에 넣기만 하고 바로 다음 작업을 수행할 수 있으며,수신자는 나중에 큐에서 메시지를 꺼내 처리합니다.
- 이 방식은 프로세스 간 결합도를 낮추고, 네트워크 지연이나 장애에도 서비스의 지속성(Resilience)을 보장합니다.(예: 웹 서버가 요청을 큐에 넣고, 백엔드가 워커가 나중에 처리 (예: 이메일 전송, 결제 승인 등))

2.**메시지 단위 통신(Message-based Communication)**
- 메시지 큐는 데이터를 메시지 단위로 교환합니다.
- 각 메시지는 일반적으로 다음과 같은 구조를 가집니다.
```
┌───────────────────────────────┐
│ Header (ID, Timestamp, Priority) │
│ Body   (Payload data)            │
└───────────────────────────────┘
```
- 즉, 단순한 바이트 스트림(파이프, 소켓)과 달리 자체적인 구분 단위와 메타데이터를 포함합니다.
- 이로 인해 송신자와 수신자는 서로의 내부 구조를 몰라도 안전하게 통신할 수 있습니다.

3. **버퍼링(buffering)** 기능
- 메시지 큐는 생산자와 소비자 속도의 불균형을 완화하기 위한 중간 버퍼 역할을 합니다.
- 따라서 시스템 전체 처리율(Throguput)을 높이고, 트래픽이 몰릴 때 임시 저장소(backpressure 완화)로 작동합니다 (예: Kafka의 Topic, RabbitMQ의 Queue가 메시지를 버퍼링함으로써 피크 트래픽을 흡수)

4. 우선순위(Priority)처리
- 많은 메시지 큐 시스템은 메시지마다 우선순위(Priority)를 부여할 수 있습니다.
- 높은 우선순위를 가진 메시지가 먼저 처리되며, 이를 통해 긴급 작업을 빠르게 수행할 수 있습니다.
- 운영체제 수준 IPC(msgsnd, msgrcv)나 RabbitMQ 등에서도 priority 속성을 설정할 수 있습니다. (예: 긴급 결제 승인 메시지를 일반 로그처리보다 먼저 소비)

![BitOperations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2Fc78NcM%2FbtssuxbRK1k%2FAAAAAAAAAAAAAAAAAAAAAJ8tXuIAMPc-lMwqZCLarucALLVreobYruvt7d8cY85M%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1761922799%26allow_ip%3D%26allow_referer%3D%26signature%3DYLGL9G10kxv0X3l4lvLbeW83v%252Fk%253D)
[그림3.1 메시지 큐의비동기 처리]

[예제: POSIX 메시지 큐 사용하기]
송신측
```c
#include <stdio.h>
#include <stlib.h>
#include <string.h>
#include <mqueue.h>
#include <sys/stat.h>

int main() {
    mqd_t mq;
    struct mq_attr attr;
    char *msg = "Hello, POSIX Message Queue";

    // 메시지 큐 속성 설정
    attr.mq_flags = 0;
    attr.mq_maxmsg = 10;
    attr.mq_msgsize = 128;
    attr.mq_curmsgs = 0;

    // 메시지 큐 생성
    mq = mq_open("/test_mq", O_CREAT | O_WRONLY, 0644, &attr);
    if (mq == -1) {
        perror("Message queue creation failed");
        exit(1);
    }

    // 메시지 전송
    if (mq_send(mq, msg, strlen(msg) + 1, 0) == -1) {
        perror("Message send failed");
        exit(1);
    }

    printf("Message sent\n");

    // 메시지 큐 닫기
    mq_close(mq);

    return 0;
}
```

수신측
```c
#include <stdio.h>
#include <stdlib.h>
#include <mqueue.h>
#include <sys/stat.h>

int main() {
    mqd_t mq;
    struct mq_attr attr;
    char buffer[128];

    // 메시지 큐 오픈
    mq = mq_open("/test_mq", O_RDONLY);
    if (mq == -1) {
        perror("Message queue open failed");
        exit(1);
    }

    // 메시지 수신
    if (mq_receive(mq, buffer, 128, NULL) == -1) {
        perror("Message receive failed");
        exit(1);
    }

    printf("Received message: %s\n", buffer);

    // 메시지 큐 닫기
    mq_close(mq);

    // 메시지 큐 삭제
    mq_unlink("/test_mq");

    return 0;
}
```

위 예제에서는 먼저 메시지를 큐에 전송하는 프로그램을 실행하고, 이후 메시지를 수신하는 프로그램을 실행하여 메시지를 받습니다. mq_open 함수를 사용하여 메시지 큐를 생성하거나 열고, mq_send와 mq_receive 함수로 메시지를 송수신합니다. 마지막으로 mq_close로 큐를 닫고, mq_receive로 생성된 메시지 큐를 삭제합니다.

### 소켓(Socket)
소켓은 컴퓨터 네트워크를 통해 프로세스들 간에 양방향 통신(전이중)을 할 수 있게 해주는 표준 IPC 인터페이스 입니다. 소켓의 한쪽 끝은 서버, 다른 한쪽 끝은 클라이언트(client)로 구성되어, 네트워크 상의 주소 (IP)와 포트(port)번호로 서로를 식별하며 통신합니다. 

소켓의 특징
- **네트워크 통신 기반**: 소켓은 네트워크 (주로 TCP/IP)를 통해 프로세스 간 데이터 송수신을 가능하게 하는 통신 인터페이스이다.
- **클라이언트-서버 구조**: 한쪽은 서버 소켓(listen/accept), 다른 한쪽은 클라이언트 소켓(connect/send)을 통해 양방향 통신을 수행한다.
- **프로토콜 지정 가능**: TCP(신뢰성, 연결지향) 또는 UDP(비연결, 빠름) 등 전송 프로토콜을 명시적으로 지정하여 통신 특성을 선택할 수 있다.
- **동기(Synchronous)** 통신: 송신 후 응답을 기다리는 블로킹 방식으로, 처리 순서가 명확하고 구현이 단순하다.
- **비동기(Asynchronous)**: 송신, 수신이 동시에 가능하며, 응답을 기다리지 않아 실시간 처리나 병렬 작업에 유리하다. 

![BitOperations  ](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FdXgwCa%2Fbtssv0dzeYH%2FAAAAAAAAAAAAAAAAAAAAAOba0rWeWM2zhSOgT1xETu-CdOlaDUcIAWzSAr_M_8hR%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1761922799%26allow_ip%3D%26allow_referer%3D%26signature%3DQH2KAEphkWI4VBucVZYlDKjb7YI%253D)
[그림5. 소켓 구조]

예를 들어 서버 프로세스가 특정 포트 번호에 소켓을 열고(bind/listen)대기하고 있으면, 클라이언트 프로세스가 그 IP 포트로 연결(connect)을 요청하여 통신 채널이 형성됩니다. 연결이 맺어진 이후에는 서버와 클라이언트 양쪽에서 데이터를 송수신(senc/receive)할 수 있으며, 이 때의 데이터 흐름은 네트워크 프로토콜(TCP/UDP 등)에 따라 패킷 형태 또는 스트림 형태로 주고받게 됩니다.

소켓 IPC는 동일한 호스트 내의 통신 뿐만 아니라 인터넷 등을 통한 원격 통신까지 포괄하는 것이 특징입니다.실제로 소켓에는 로컬 소켓과 네트워크 소켓 두가지 형태가 있습니다. 로컬 소켓의 한 예로 **유닉스 도메인 소켓(UDS)**이 있는데, 이는 IP 주소 대신 파일시스템 경로로 통신 Endpoint를 만들어 같은 OS 내의 프로세스끼리 통신할 때 사용됩니다. 

반면, 일반적으로 우리가 말하는 소켓(IPv4, IPv6소켓)은 IP 주소를 사용하며 원격 시스템 간의 통신도 지원하는 형태입니다. 즉, 소켓을 이용하면 한 머신 내의 프로세스 간에도 통신이 가능하고(예: 로컬 호스트), 전혀 다른 곳에 있는 시스템의 프로세스와도 통신할 수 있습니다. 이러한 범용성 덕분에 소켓은 IPC 방식 중 가장 유연하고 범위가 넓은 수단으로 꼽힙니다.

**TCP 소켓과 UDP 소켓**: 소켓은 전송 계층 프로토콜에 따라 성질이 달라집니다. TCP 소켓은 연결 지향적이고 신뢰성 있는 바이트 스트림을 제공하여, 통신 중 데이터 순서 보장과 오류 제어를 해줍니다. 반면 UDP 소켓은 연결 설정 없이 데이터를 보내는 데이터그램(Packet) 중심의 통신으로, 빠르지만 신뢰성은 전적으로 응용계층에서 보완해야 합니다. 채팅 같은 응용에서는 보통 TCP 소켓을 사용하여 메시지 순서와 전달을 보장하지만, 실시간 게임 상태나 스트리밍처럼 약간의 데이터 손실을 감수하고서라도 속도를 중시하는 경우 UDP를 사용할 수도 있습니다.

**소켓의 장단점**: 소켓을 사용하면 네트워크 투명성을 얻을 수 있습니다. 즉, 동일한 소켓 API로 동일 장비 내 프로세스와도 통신할 수 있고, 전 세계 어디에 있든 네트워크로 연결된 프로세스와도 통신할 수 있습니다. 따라서 분산 시스템이나 클라이언트-서버 모델의 핵심 통신 수단으로 활용되며, 웹 서버, 데이터베이스 등 대부분의 서버 프로그램이 소켓을 사용합니다. 또한 양방향 통신이 기본으로 지원되며, 하나의 서버 소켓에 여러 클라이언트가 연결해오는 다대일 통신도 구현 가능합니다. 표준화된 인터페이스와 프로토콜을 사용하므로 이기종 시스템 간에도 통신이 가능하고, 인터넷 기반응용을 만들기 수월합니다.

하지만 소켓 프로그래밍은 구현 난이도가 다소 높습니다. 연결 설정, 패킷 혹은 스트림 처리, byte-order 변환, 에러 처리 등 개발자가 신경 써야 할 부분이 많습니다. 또한 같은 머신 내 통신이라도 파이프나 공유 메모리에 비해 오버헤드가 큽니다. 데이터가 애플리케이션에서 커널로, 커널에서 네트워크 계층을 거쳐 다시 커널, 애플리케이션으로 복사되고, 프로토콜 스택을 처리하는 비용이 있습니다.

특히 네트워크를 경유하는 경우 latency나 패킷 손실 등의 문제가 생길 수 있어, 이를 고려한 오류 제어와 시간 제한 등을 설계해야 합니다. 요약하면 소켓은 범용적이고 강력하지만 성능 면에서는 로컬 IPC보다 느릴 수 있고, 구현이 복잡하며 보안(네트워크를 통한 공격 가능성)도 고려해야 합니다.

리눅스 C에서 소켓을 이용한 간단예제

TCP 서버
```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>

#define PORT 8080

int main() {
    int server_fd, new_socket;
    struct sockaddr_in address;
    int opt = 1;
    int addrlen = sizeof(address);
    char buffer[1024] = {0};
    char *hello = "Hello from server";

    // 소켓 생성
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("socket failed");
        exit(EXIT_FAILURE);
    }

    // 소켓에 옵션 설정
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, &opt, sizeof(opt))) {
        perror("setsockopt");
        exit(EXIT_FAILURE);
    }

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    // 소켓을 포트에 바인드
    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address))<0) {
        perror("bind failed");
        exit(EXIT_FAILURE);
    }

    // 연결 대기
    if (listen(server_fd, 3) < 0) {
        perror("listen");
        exit(EXIT_FAILURE);
    }

    // 연결 수락
    if ((new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen))<0) {
        perror("accept");
        exit(EXIT_FAILURE);
    }

    // 데이터 수신 및 응답 전송
    read(new_socket, buffer, 1024);
    printf("Message from client: %s\n", buffer);
    send(new_socket, hello, strlen(hello), 0);
    printf("Hello message sent\n");

    // 소켓 닫기
    close(new_socket);
    close(server_fd);

    return 0;
}

```

TCP 클라이언트
```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define PORT 8080

int main() {
    int sock = 0;
    struct sockaddr_in serv_addr;
    char *hello = "Hello from client";
    char buffer[1024] = {0};

    // 소켓 생성
    if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
        printf("\n Socket creation error \n");
        return -1;
    }

    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(PORT);

    // 서버 주소 변환
    if(inet_pton(AF_INET, "127.0.0.1", &serv_addr.sin_addr)<=0) {
        printf("\nInvalid address/ Address not supported \n");
        return -1;
    }

    // 서버에 연결
    if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
        printf("\nConnection Failed \n");
        return -1;
    }

    // 데이터 전송 및 응답 수신
    send(sock, hello, strlen(hello), 0);
    printf("Hello message sent\n");
    read(sock, buffer, 1024);
    printf("Message from server: %s\n", buffer);

    // 소켓 닫기
    close(sock);

    return 0;
}
```
이 예제에서 서버는 지정된 포트에서 클라이언트 연결을 기다립니다. 클라이언트가 연결을 시도하면, 서버는 클라이언트의 메시지를 받고 응답을 보냅니다. 클라이언트는 서버에 메시지를 전송하고, 서버로부터의 응답을 기다립니다. 이 과정을 통해 양방향 통신이 이루어집니다. 소켓 프로그래밍은 네트워크 프로그래밍의 기초이며, 분산 시스템, 네트워크 서비스, 클라이언트-서버 애플리케이션 등 다양한 분야에서 활용됩니다.

### 루프백 인터페이스
루프백 인터페이스는 자기 자신에게 네트워크 통신을 하는 가상 네트워크 장치를 뜻합니다. 흔히 로컬호스트(localhost) 주소라고 불리는 127.0.0.1(IPv4)이나 ::1(IPv6)이 바로 루프백 주소입니다. 이 주소로 보내는 모든 트래픽은 컴퓨터를 떠나지 않고 곧바로 자신에게 반환되며, 실제 네트워크 카드나 물리적 케이블을 거치지 않고 OS 내부에서 처리됩니다
. 즉, 루프백은 외부망과 분리된 자기 자신과의 통신으로, 네트워크 스택을 통해 진행되지만 패킷이 외부로 나가지 않기 때문에 보안상 안전하고 지연이 최소화됩니다. 실제로 127.0.0.1로의 통신은 물리적 하드웨어를 완전히 우회하기 때문에 가능한 가장 빠른 네트워크 통신 방법으로 불리기도 합니다
. 또한 패킷 손실도 없으므로 신뢰성이 100% 확보되어, 성능 저하를 유발하는 재전송 과정 등이 필요 없습니다.

**루프백의 용도**: 개발 단계에서 로컬 서버를 실행하고 테스트할 때 주로 사용됩니다. 예를 들어 웹 개발 시 localhost로 웹 서버에 접속하면 인터넷에 연결되지 않은 상태에서도 웹사이트 테스트가 가능합니다. 데이터베이스 서버나 캐시 서버(redis 등)를 로컬 PC에서 구동하고 애플리케이션이 127.0.0.1로 연결하게 하면, 네트워크 환경에 영향을 받지 않고도 마치 실제 서버와 통신하듯 개발할 수 있습니다. 또한 동일한 컴퓨터 내의 서로 다른 프로세스 간 통신을 네트워크 프로그래밍 방식으로 처리하고 싶을 때 루프백을 이용합니다. 

운영체제 입장에서는 루프백도 하나의 네트워크 인터페이스이므로, 일반 소켓 프로그래밍을 할 때 대상 주소를 127.0.0.1로 지정하기만 하면 원격이 아닌 로컬 프로세스와 통신이 이루어집니다. 이렇듯 루프백을 사용하면, 네트워크 서버와 클라이언트를 한 시스템에서 구동하면서 통신을 검증하거나, IPC 수단으로 네트워크 소켓을 활용할 수 있습니다.

### 정리
IPC(Inter-Process Communication)는 운영체제에서 서로 다른 프로세스 간에 데이터를 주고받기 위한 기술로, 대표적으로 파이프, 메시지 큐, 공유 메모리, 소켓, 루프백 인터페이스 방식이 있습니다. 파이프와 메시지 큐는 운영체제가 중재하는 메시지 패싱 방식이고, 공유 메모리는 프로세스들이 메모리 공간을 직접 공유하여 빠른 통신이 가능하지만 동기화가 필요합니다. 소켓은 로컬 및 네트워크 간 양방향 통신이 가능하며, 루프백 인터페이스를 통해 한 시스템 내에서 네트워크 테스트도 가능합니다. 각 방식은 속도, 구현 난이도, 데이터 크기, 네트워크 여부 등 다양한 기준에 따라 적절하게 선택됩니다. 예를 들어 채팅 프로그램에서는 간단한 1:1 통신에는 파이프, 다자간 또는 원격 통신에는 소켓이 주로 사용됩니다.

### 각 IPC 방식 5가지에 대해 실제 유즈케이스

[pipe]
1. 리눅스 쉘 명령어 파이프라인 (ls)
2. 부모-자식 프로세스 간 통신: 부모가 자식에게 명령을 전달 시, pipe()로 연결된 FD를 사용
3. 백그라운드 로그 전달기: 프로그램의 로그를 별도 로그 처리기로 실시간 전달

[Message Queue]
1. 센서 데이터 수집 시스템: 각 센서 프로세스가 중앙 수집기에게 측정값을 메시지 큐로 전송
2. 주문 처리 대기열: 전자상거래 백엔드에서 사용자 주문을 큐에 넣고, 처리기는 순차적으로 처리
3. 프로세스 간 작업 분배기: 마스터 프로세스가 작업 요청을 메시지 큐에 넣고 워커들이 꺼내 처리

[Shared Memory]
1. 비디오 프레임 처리: 카메라 입력 프로세스가 프레임을 공유 메모리에 쓰고, 처리 프로세스가 실시간 분석
2. 금융 데이터 피드: 고속 주식 가격 수신기와 차트 시각화 앱이 메모리 버퍼를 공유
3. 머신러닝 추론 결과 공유: 추론 서버가 예측 결과를 공유 메모리에 기록하고 UI 프로세스가 즉시 반영

[Socket]
1. 채팅 애플리케이션: 클라이언트들이 서버의 TCP 소켓 연결을 맺고 메시지 송수신
2. REST API 통신: 백엔드 서비스 간 HTTP 통신으로 JSON 데이터를 교환
3. 게임 서버와 클라이언트:실시간 멀티플레이어 게임에서 소켓을 통한 위치/행동 동기화 처리

[루프백 인터페이스]
1. 로컬 개발 환경 테스트: 웹 서버(localhost:8000)와 브라우저가 동일 컴퓨터에서 통신
2. 애플리케이션-DB 통신: 로컬에서 실행중인 PostgreSQL에 127.0.0.1:5432로 연결
3. 보안된 내부 RPC 테스트: 외부 노출 없이 gRPC 서버/클라이언트 테스트 진행

출처: https://ground90.tistory.com/99, https://wikidocs.net/231840, mohitdtumce.medium
,pinggy, geeksforgeeks, en.wikipedia, learn.microsoft
