---
layout: post
title: "가상메모리"
categories: [ComputerScience, OperatingSystem]
author: cotes
published: true
---


목차

서론

가상 메모리의 정의 및 필요성

가상 메모리의 동작 원리 (주소 변환, 페이징, 스왑)

가상 메모리의 주요 구성요소 (페이지, 프레임, 페이지 테이블, MMU 등)

가상 메모리의 장점과 단점

스래싱 및 페이지 폴트

운영체제별 스왑 방식 차이 (리눅스 vs 윈도우)

요약 및 결론

# 가상 메모리
실제 메모리 크기와 상관없이 메모리를 이용할 수 있도록 가상의 메모리 주소를 사용하는 방법입니다. 예를 들어, 100mb 메모리 크기에서 200mb 크기의 프로세스를 수행할 수 있도록 하는것입니다.

![BitOperations](https://parkmuhyeun.github.io/assets//img/blog/etc/operating%20system/vm_1.PNG)

그림1 : 가상 메모리의 구조

### 1. 서론

가상 메모리(Virtual Memory)는 현대 운영체제(OS)의 핵심 개념으로, 물리적 메모리(RAM)의 한계를 극복하고 효율적인 메모리 관리를 가능하게 합니다. 가상 메모리를 통해 프로세스는 실제 RAM 크기보다 훨씬 큰 연속된 메모리 공간이 있는 것처럼 동작할 수 있으며(오버커밋), 여러 프로그램을 동시에 실행하여도 서로 간섭 없이 독립적인 메모리 공간을 갖도록 보장합니다. 본 글에서는 가상 메모리의 정의와 필요성, 동작 원리(주소 변환, 페이징, 스왑 과정), 주요 구성 요소, 장점과 단점, 페이지 폴트 및 스래싱 현상의 설명, 그리고 운영체제별(리눅스 vs 윈도우) 스왑 방식의 차이를 기술합니다. 이를 통해 가상 메모리 시스템의 개념과 구현상의 특징을 종합적으로 이해할 수 있을 것입니다.

### 2. 가상 메모리의 정의 및 필요성

가상 메모리는 운영체제가 물리 메모리보다 큰 연속적 메모리를 제공하는 추상화 기법입니다. 즉, 실제 RAM 용량이 한정되어 있어도 **디스크 공간을 활용하여 프로그램에 큰 메모리가 있는 듯한 “환상”**을 줍니다. 운영체제는 **프로세스를 페이지(page)**라는 작은 단위(4kb)로 분할하고, 실행에 당장 필요하지 않은 페이지들은 디스크의 스왑 영역으로 내보냈다가 필요해지면 다시 가져오는 방식으로 작동합니다
이러한 기법이 필요한 이유는 다음과 같습니다.

**물리 메모리 부족 극복**: 프로그램이 실제 RAM보다 커도 전체를 한꺼번에 메모리에 올리지 않고 필요한 부분만 적재하여 실행할 수 있습니다. 따라서 물리 메모리 크기를 넘는 대규모 프로그램도 실행 가능합니다.

**효율적인 메모리 활용**: 한정된 RAM을 여러 프로세스가 나눠 쓰되, 잠시 사용하지 않는 메모리 공간은 디스크로 내보내어 RAM을 비우고, 필요할 때 다시 불러오는 방식으로 메모리를 효율적으로 관리합니다. 이로써 동시에 더 많은 프로그램을 실행할 수 있습니다.

**프로세스 격리 및 안정성**: **각 프로세스마다 독립된 가상 주소 공간을 제공**하여, 한 프로세스의 메모리 접근이 다른 프로세스를 침범하지 못하도록 합니다. 이러한 **메모리 격리(memory isolation)**는 시스템 안정성과 보안을 향상시킵니다.


**프로그래밍 편의성**: 프로그래머는 마치 큰 연속 메모리가 있는 것처럼 프로그램을 작성하면 되며, 메모리 부족 시의 세부 처리(예: 오버레이 관리 등)는 운영체제가 맡습니다. 이는 복잡한 프로그램을 더 쉽게 개발할 수 있게 해줍니다.

정리하자면, 가상 메모리는 디스크를 보조기억장치로 활용하여 실제 메모리 한계를 넘는 주소 공간을 제공하고, 필요한 내용만 메모리에 유지하는 스마트한 관리로 시스템 자원의 활용도를 높이는 기술입니다.

### 3. 가상 메모리의 동작 원리 (주소 변환, 페이징, 스왑)

가상 메모리는 하드웨어와 소프트웨어가 협력하여 작동합니다. CPU가 **가상 주소(virtual address)**를 생성하면, 이를 실제 **물리 주소(physical address)**로 변환하여 RAM에 접근해야 합니다. 이 과정에서 페이징(paging) 기법과 스왑(swap) 동작이 핵심적으로 이루어집니다.

### 3.1 주소 변환과 페이징

프로세스의 가상 주소 공간은 **같은 크기의 페이지(page)**들로 나뉘어 있으며, 물리 메모리는 대응되는 **프레임(frame)**들로 구획되어 있습니다. **페이지 테이블(page table)**은 가상 페이지 번호를 물리 프레임 번호로 매핑한 표로서, 각 프로세스마다 운영체제가 해당 테이블을 관리합니다. CPU가 어떤 가상 주소를 접근할 때, 가상 주소의 페이지 번호를 페이지 테이블에서 찾아 해당 페이지가 상주하는 물리 프레임 번호를 얻고, 페이지 오프셋(offset)을 더하여 실제 물리 주소를 산출합니다. 이러한 주소 변환 작업은 보통 
**메모리 관리 장치(MMU)**라는 하드웨어에 의해 수행되며, MMU는 CPU 내에 내장되어 고속으로 주소 변환을 처리합니다.

하지만 페이지 테이블이 메모리에 존재하므로 매번 메모리 접근 시 2번의 메모리 접근(페이지 테이블 조회 후 실제 데이터 접근)이 필요하여 성능 저하가 발생합니다. 이를 완화하기 위해 **TLB(Translation Lookaside Buffer)**라는 주소 변환 캐시를 사용합니다.

![BitOperations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FcANX34%2Fbtr9RwPiE8M%2FAAAAAAAAAAAAAAAAAAAAAGcqQP-LmOpiCGKVdvd5aRAE80I-cJ_ZOfNPs1SSaH3J%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1761922799%26allow_ip%3D%26allow_referer%3D%26signature%3DIbgzjzK6YhzAnGDqsX9DkuGAX3s%253D)

그림 2: 가상 주소를 물리 주소로 변환하는 과정

![BitOperations](https://upload.wikimedia.org/wikipedia/commons/thumb/d/dc/MMU_principle_updated.png/960px-MMU_principle_updated.png)
그림 3: MMU 동작 구성도

CPU가 가상 주소를 생성하면 MMU가 TLB를 먼저 조회하여 해당 **가상 페이지 번호에 대한 물리 프레임 번호가 캐시에 존재하는지 확인(①)**합니다. TLB에 해당 항목이 있다면(TLB 히트) 곧바로 프레임 번호를 얻어 오프셋과 결합함으로써 물리 주소를 결정하고, RAM에서 데이터에 접근합니다. 만약 TLB에 없다면(TLB 미스) MMU는 메모리에 있는 페이지 테이블을 참고하여(②) 해당 페이지의 프레임 번호를 찾아냅니다. 페이지 테이블 조회로 얻은 프레임 정보는 TLB에 새로 저장하여 이후 접근을 빠르게 하고, 최종적으로 물리 주소를 구성하여 메모리에 접근하게 됩니다. 이처럼 TLB를 활용하면 자주 참조되는 페이지의 주소 변환을 캐시하여 메모리 접근 성능을 향상시킬 수 있습니다.

한편, 가상 메모리 시스템에서 CPU가 요구한 가상 주소가 현재 물리 메모리에 없을 경우 (예: 해당 페이지가 아직 적재되지 않았거나 한때 적재되었지만 스왑 아웃된 경우), **페이지 폴트(page fault)**가 발생합니다. 페이지 폴트가 일어나면 하드웨어가 CPU의 제어를 운영체제 커널에 넘겨 해당 페이지를 디스크에서 읽어와 메모리에 적재하는 일련의 과정을 트리거합니다. 페이지 폴트 처리 과정은 후술하는 6장에서 상세히 다루겠습니다.

### 3.2 스왑과 페이지 교체 알고리즘

**스왑(swap)**이란 사용되지 않는 페이지를 디스크상의 스왑 영역으로 내보내고(스왑 아웃, swap-out), 필요한 페이지를 디스크에서 메모리로 불러오는(스왑 인, swap-in) 과정을 뜻합니다. 가상 메모리 시스템은 일반적으로 **지연 로딩(demand paging)** 방식을 사용하여, **프로그램 실행 시 처음부터 모든 페이지를 다 메모리에 올리지 않고 실제 접근되는 시점에 디스크에서 가져오는 전략을 취합니다.** 이에 따라 메모리가 부족해지면 오래 사용하지 않은 페이지를 내보내 공간을 확보하고, 새로운 페이지를 가져오는 **페이지 교체(page replacement)**가 이루어집니다.

페이지 교체 시 운영체제는 특정 알고리즘(예: FIFO, LRU, 최적 알고리즘 등)을 사용하여 어떤 페이지를 내보낼지 결정합니다. **일반적으로 가장 오랫동안 사용되지 않은 페이지를 교체하는 등 페이지 폴트 발생률을 최소화하는 전략이 사용됩니다.** 스왑 아웃되는 페이지가 나중에 다시 필요해지면 디스크에서 읽어와 재적재하며, 이 때 다른 페이지가 다시 선택적으로 내보내질 수 있습니다. **이러한 방식으로 운영체제는 물리 메모리 크기 이상의 프로그램도 실행할 수 있게 하며, 디스크를 마치 추가 메모리처럼 활용합니다.** 페이지 교체 알고리즘의 경우 자세한 부분은 따로 다루겠습니다.

현대 운영체제(예: 리눅스, 윈도우)는 일반적으로 프로세스 전체를 통째로 스왑하지 않고 페이지 단위로 스왑합니다. 과거의 전통적인 유닉스 시스템에서는 메모리가 부족할 때 프로세스 전체를 디스크로 내보내는 스와핑을 사용하기도 했으나, 전체 프로세스를 옮기는 데 걸리는 시간이 너무 크기 때문에 현재는 부분적인 페이징 기법(일부 페이지만 교체)을 사용합니다. 이는 물리 메모리를 초과하여도 성능 저하를 최소화하면서 메모리를 과할당(over-subscribe)할 수 있는 유연한 방법입니다.

### 4. 가상 메모리의 주요 구성요소 (페이지, 프레임, 페이지 테이블, MMU 등)

가상 메모리 시스템을 구성하는 주요 요소는 다음과 같습니다:

**페이지(Page)**: 가상 메모리에서의 고정 크기 데이터 블록을 말합니다. 일반적으로 수 KB 크기(예: 4KB)로 정의되며, 프로그램의 주소 공간은 여러 개의 페이지로 분할됩니다. 페이지는 가상 주소 공간상의 조각으로서, 각 페이지에는 연속된 가상 주소 범위가 들어 있습니다.

**프레임(Frame)**: 물리 메모리(RAM)를 페이지와 동일한 크기로 나눈 고정 크기 블록입니다. **프레임은 실제 메모리상의 슬롯으로, 각 프레임에 하나의 페이지를 적재할 수 있습니다.** 즉, 페이지가 퍼즐 조각이라면 프레임은 그 조각이 들어가는 보드의 칸에 비유할 수 있으며, 가상 메모리 시스템에서 페이지와 프레임은 1:1 크기로 대응됩니다.

**페이지 테이블(Page Table)**: **가상 페이지 번호를 물리 프레임 번호에 매핑하는 테이블 입니다.** 운영체제는 프로세스마다 별도의 페이지 테이블을 유지하며, 각 **페이지 테이블 엔트리(PTE)**에는 해당 가상 페이지가 현재 어느 프레임에 있는지 또는 없다면 디스크의 어디에 있는지 등의 정보와 함께 유효 비트, 변경 비트(더티 비트) 등 상태 정보가 포함됩니다. 페이지 테이블은 CPU가 가상 주소를 변환할 때 참고하는 기본 자료구조로서, 일반적으로 메모리에 저장되지만 CPU 레지스터에 페이지 테이블의 시작 주소(베이스 레지스터) 등을 보관하여 빠르게 접근할 수 있도록 합니다.

**메모리 관리 장치(MMU, Memory Management Unit)**: CPU 내지 메모리 서브시스템에 포함된 하드웨어 모듈로, 가상 주소를 물리 주소로 변환하는 역할을 합니다. MMU는 현재 실행 중인 프로세스의 페이지 테이블을 참고하여 가상 페이지 번호를 물리 프레임으로 매핑하고, 결과 물리 주소로 메모리에 접근합니다. 또한 **메모리 보호를 위해 잘못된 메모리 접근을 감지하면 CPU에 트랩(예: 페이지 폴트)을 발생시킵니다** 현대 MMU에는 TLB와 같은 고속 캐시가 내장되어 있어 주소 변환을 가속화합니다.

**TLB(변환 색인 버퍼, Translation Lookaside Buffer)**: 페이지 테이블 항목을 캐싱하는 소형 고속 메모리입니다. TLB에는 최근에 사용된 가상 페이지→물리 프레임 매핑이 저장되어 있어, CPU가 가상 주소를 변환할 때 먼저 TLB를 조회하여 일치하는 항목이 있으면 페이지 테이블에 접근하지 않고 바로 물리 주소를 얻습니다. TLB에 없는 경우에만 메모리의 페이지 테이블을 접근하므로, **TLB의 높은 적중률(hit ratio)**은 가상 메모리 시스템 성능에 매우 중요합니다. TLB는 일반적으로 수십에서 수백 개의 항목을 가지며, 캐시와 유사한 구조로 동작합니다.

**스왑 공간(Swap Space)**: 물리 메모리에 올라오지 않은 페이지들을 저장해 두는 디스크상의 영역입니다. 물리 메모리가 모자랄 때 사용하지 않는 페이지들을 이 곳에 임시 보관하며, 해당 페이지가 다시 필요해지면 스왑 공간에서 읽어옵니다. 스왑 공간은 운영체제의 가상 메모리 확장을 위한 공간으로, 유닉스 계열 OS에서는 주로 별도의 스왑 파티션으로 할당되고 윈도우 등에서는 **페이지 파일(pagefile)**이라는 디스크 파일 형태로 존재합니다. 예를 들어 리눅스는 일반적으로 /swap 파티션이나 스왑 파일을 사용하고, 윈도우는 pagefile.sys라는 파일을 통해 스왑 영역을 구현합니다.

### 5. 가상 메모리의 장점과 단점

가상 메모리 도입으로 얻는 이점과 한계는 다음과 같습니다.

① 장점(Benefits):

**대용량 프로그램 지원 및 다중 작업 향상**: 가상 메모리는 물리 메모리보다 큰 프로그램도 실행할 수 있게 하며, 동시에 여러 프로그램을 메모리 부족 없이 실행할 수 있도록 합니다. 즉, 실제 RAM 이상으로 메모리를 활용할 수 있으므로 멀티프로그래밍이 향상되고, 큰 애플리케이션도 구동 가능합니다. 필요 시 프로그램의 일부만 메모리에 올려 실행할 수 있어 메모리 공간 제약을 완화합니다.

**메모리 활용 효율 및 단편화 감소**: 가상 메모리는 실제 사용되는 데이터만 메모리에 유지하고 나머지는 디스크로 보내므로 메모리 낭비를 줄이고 활용률을 극대화합니다. 또한 고정 크기 페이지를 사용함으로써 외부 단편화를 피하고, 연속된 물리 메모리 할당이 필요 없으므로 메모리 관리가 수월해집니다.

**프로세스 간 격리와 보안 강화**: 각 프로세스는 자기만의 가상 주소 공간을 가지므로 다른 프로세스의 메모리를 침범할 수 없습니다. 이로 인해 프로세스 간 간섭이 줄어들고 오류 및 악의적 접근으로부터 보호됩니다. 한 프로세스의 비정상 동작이 다른 프로세스 메모리를 덮어쓰지 못하므로 시스템 안정성이 높아집니다.

**프로그램 개발 단순화**: 개발자는 실제 메모리 크기에 신경 쓰지 않고 큰 주소 공간을 가정하여 프로그래밍할 수 있습니다. 메모리 부족 시 어떤 부분을 디스크로 내보낼지 등의 고민은 운영체제가 처리하므로, 개발 생산성이 향상되고 복잡한 메모리 관리 작업이 불필요해집니다.

② 단점(Limitations):

**성능 저하 가능성**: 가상 메모리 사용으로 인해 주소 변환 오버헤드가 발생하고, 특히 **디스크 접근(페이지 스왑)**이 잦아지면 시스템 성능이 크게 저하될 수 있습니다. 디스크 I/O는 메모리 접근보다 수백배 이상 느리기 때문에, 페이지 폴트가 빈번하면 응답 속도가 떨어지고 애플리케이션 수행이 지연됩니다. (예: 심한 경우 CPU가 유휴 대기하게 되는 스래싱 현상 발생 가능 - 6장에서 설명).

**복잡성 증가**: 가상 메모리 구현으로 운영체제와 하드웨어의 구조가 복잡해집니다. 운영체제는 페이지 테이블, 스왑 공간 관리, 페이지 교체 알고리즘 등 추가 작업을 수행해야 하며, MMU/TLB 등의 하드웨어 지원이 요구됩니다. 이는 시스템 구현 비용을 높이고, 메모리 관리에 추가적인 메모리 공간(페이지 테이블 등)도 소모합니다.

**데이터 일관성 및 오류 위험**: 메모리를 디스크와 오가며 사용하므로, 전원 장애나 시스템 오류 시 스왑 중이던 데이터의 손실 위험이 있습니다. 또한 개발 시 가상 메모리 동작을 잘 이해하지 못하면 예상치 못한 성능 문제를 초래할 수 있습니다. 예를 들어, 실시간 성능이 중요한 시스템에서는 예측 불가능한 페이지 폴트 지연이 문제가 될 수 있습니다.


1. **CPU가 페이지 접근 시도**
   프로세스가 특정 가상 주소의 데이터를 요청합니다.

2. **페이지 테이블 조회**
   MMU가 해당 주소의 유효 비트(valid bit)을 확인합니다.
 
 
3. **유효하지 않음(0) -> 페이지 폴트 발생** 
   CPU는 페이지 폴트 예외를 발생시키고 커널(운영체제)에 제어를 넘깁니다.

4. **커널에서 처리**
   디스크(스왑 영역)에서 해당 페이지를 찾아 메모리에 적재합니다.

5. **페이지 테이블을 갱신**
   해당 가상 주소 <-> 물리 주소 매핑 업데이트

6. **프로세스 재시작**
   폴트가 발생했던 명령어를 다시 실행 -> 이번엔 정상 접근 가능

이 전체 과정(페이지 폴트 서비스)에 수반되는 시간은 디스크 I/O 때문에 메모리 접근에 비해 매우 크며, 가능한 한 페이지 폴트를 줄이는 것이 시스템 성능에 중요합니다.

### 6. 스래싱 및 페이지 폴트

가상 메모리 환경에서 **페이지 폴트(page fault)**와 **스래싱(thrashing)**은 메모리 관리와 성능 측면에서 중요한 개념입니다.

먼저, 페이지 폴트란 프로세스가 필요한 페이지가 현재 물리 메모리에 존재하지 않을 때 발생하는 이벤트입니다. 예를 들어 어떤 명령이 주소 X를 읽으려고 했는데 해당 가상 페이지가 RAM에 없으면 CPU 하드웨어가 트랩(trap)을 발생시켜 운영체제에 페이지 폴트 예외를 알립니다. 페이지 폴트가 발생하는 즉시 CPU는 실행을 중단하고 OS 커널이 개입하여 아래와 같은 과정을 수행합니다.


**스래싱(thrashing)**은 페이지 폴트가 지나치게 빈번하게 발생하여 CPU가 유용한 계산을 하기보다 대부분의 시간을 페이지 교체 작업에 소비하는 상태를 말합니다. 쉽게 말해, 프로세스들이 계속해서 필요한 페이지들이 메모리에 없어서 **페이지 폴트 -> 페이지 적재/교체 -> 곧 다른 페이지 폴트... 가 연쇄적으로 일어나 디스크 스왑 입출력이 과도하게 발생하고, 그 결과 전체 시스템 성능이 급격히 악화되는 현상입니다.**

![BitOperations](https://velog.velcdn.com/images/jjuny7712/post/a306671f-ecf7-46dd-95e2-3a4513807adc/image.png)

그림4 Degree of Multiprogramming과 CPU Usage간의 모델링

위 모델링은 초반에는 프로세스 수(다중 프로그래밍)가 늘어날수록 CPU는 더 바빠져서 활용률이 증가합니다. 하지만, 일정 임계점을 넘어서게 되면 페이지 폴트가 급증하게되고 CPU 활용률이 급감하게 됩니다. 이 급락 지점을 쓰레싱(trashing)이라고 부릅니다.

### 6.1 CPU와 I/O의 동시성 모델로 해석
큰 틀에서 운영체제의 기본 자원은 다음 두 가지로 볼 수 있습니다.
- CPU (연산 자원)
- I/O 장치 (디스크 등)
정상적인 상태에서는 다음과 같은 병렬성이 있습니다.


|프로세스 A가 CPU를 사용 중 | 프로세스 B는 디스크 I/O 중 |
|----------|---------|
|CPU와 디스크 모두 바쁘게 일함 | 높은 시스템 활용률 유지 |

이 경우 CPU Utilization은 높습니다.

하지만, 쓰레싱 발생시 이 흐름은 붕괴됩니다.

1. 프로세스가 페이지를 참조
2. 해당 페이지가 메모리에 없음 -> Page Fault 발생(Trap)
3. CPU는 즉시 대기 상태(Blocked)로 전환(CPU는 더 이상 이   프로세스를 실행하지 않음) 
4. 디스크 I/O 요청 발생 (Swap-in/out)
5. 디스크는 매우 느림 (수ms 단위)
   -> CPU는 다른 프로세스를 실행하려 하지만, 다른 프로세스도 똑같이 페이지 폴트 발생
6. 결국 대부분의 프로세스가 I/O 상태가 되어 CPU는 놀게됨 (Idle)
> 핵심: CPU가 쉬는 이유는 일할 코드나 데이터가 메모리에 없기 때문입니다. 디스크는 병목(bottleneck)이 되어, CPU는 거의 모든 시간 동안 I/O 대기 상태에 빠집니다.

모델링 관점으로 본다면, 큐잉 시스템으로 분석할 수 있습니다.
운영체제 성능을 M/M/1 Queue로 단순 모델링하면

- λ: 요청 도착률

- μ: 처리율

- ρ = λ/μ : 자원 이용률

CPU 입장에서, 페이지 폴트율이 급증하면 프로세스가 CPU Queue -> I/O Queue로 이동하는 비율이 증가합니다.
즉,

- CPU에 머무는 평균 시간 ↓

- I/O 대기 시간 ↑

- 전체 Throughput ↓

- 따라서 CPU Utilization ↓

이를 수식으로 표현하면 대략적으로 다음과 같습니다.
```latex
UCPU ​= 1−P(CPU Idle)
```
쓰레싱이 심할수록 P(CPU Idle)이 증가하기 때문에 -> Ucpu는 급격히 감소합니다.

### 6.3 악순환 구조 (피드백 루프)
쓰레싱은 자기 강화적(positive feedback) 현상입니다.
```
CPU Utilization ↓
-> OS가 "CPU가 놀고 있네? -> 프로세스 더 투입"
-> 메모리 부족 심화
-> 페이지 폴트 증가
-> 디스크 I/O 폭증
-> CPU 더 놀게 됨
-> 악순환
```

결과적으로 CPU가 바쁘게 일하는게 아니라, 디스크가 쉬지 않고 일하지만 시스템 전체는 느려지는 현상입니다. 이를 방지하기 위한 두 가지 알고리즘이 있습니다.

(1) working Set Model
개념
- 각 프로세스는 일정 시간 Δ(델타) 동안 자주 참조하는 페이지의 집합을 가집니다. 이 집합을 WSSi (Working Set Size process i) 라고 부릅니다. 
- 이 집합에 메모리에 완전히 올라와 있어야만 페이지 폴트율이 낮게 유지됩니다.

공식
$$
WSS_i(t) = \{\; \text{pages referenced by process } i \text{ in } [t-\Delta,\, t] \;\}
$$
- D: 전체 시스템이 요구하는 프레임 수
- M: 실제 물리적 프레임 수

만약 D > m -> 시스템 메모리가 부족 -> Trashing 발생 가능성 높음

[동작 방식]
    1. OS는 각 프로세스의 최근 참조 이력을 추적합니다.
    2. 일정 주기마다 WSS를 계산합니다.
    3. 전체 요구 D가 실제 프레임 수보다 크면, 일부 프로세스를 Suspend 시켜 메모리 부담을 줄입니다.

[관측 지표]
- 페이지 부재율(Page Fault Rate)이 급증하기 직전 구간인 Δ 결정에 중요한 기준
- Δ가 너무 크면 불필요하게 많은 페이지를 포함 -> 비효율적
- Δ가 너무 작으면 지역성이 무시되어 자주 교체 발생

[코드]
```C
/* thrashsim.c
   Educational VM thrashing simulator (Working Set / PFF / Load Control)
   - Per-process locality-based reference generator
   - Per-process page table with LRU replacement
   - Working Set window Δ (ring buffer) to estimate WSS_i(t)
   - PFF control: adjusts frames based on page-fault rate thresholds
   - Load Control: suspends/resumes processes based on pressure
   (c) for learning purposes. No external deps.
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdbool.h>
#include <math.h>

#define MAX_PROCS  64
#define MAX_PAGES  4096   // virtual pages universe per process (educational)
#define MAX_FRAMES 8192   // total physical frames bound

typedef enum { MODE_WS, MODE_PFF, MODE_LOAD } Mode;

typedef struct {
    int pid;
    bool active;         // for load control
    int frames_alloc;    // current frames allocated
    int resident_count;  // current resident pages
    int *resident;       // -1 empty, or page id
    unsigned *last_use;  // LRU timestamp per slot
    unsigned faults;     // total page faults
    unsigned refs;       // total references
    // locality parameters
    int center;          // working set center page id
    int span;            // locality span (size of hot set)
    // working set window (Δ)
    int delta;
    int *window;         // ring buffer of last Δ refs (page ids)
    int wpos;
    int *inwin_count;    // count occurrences of page in window
    int wss;             // |WSS_i|
    // recent PFs for PFF
    unsigned pf_in_interval;
    unsigned instr_in_interval;
} Proc;

typedef struct {
    Mode mode;
    int nprocs;
    int total_frames; // system m
    int ticks;        // total time steps
    int delta;        // default Δ
    double pfr_low, pfr_high; // PFF thresholds
    // load control
    double sys_pfr_high; // system-level trigger
} Config;

typedef struct {
    Config cfg;
    Proc procs[MAX_PROCS];
    unsigned now;
    int free_frames;
} Sys;

static unsigned urand() { return (unsigned)rand(); }

static int clampi(int v, int lo, int hi) {
    if (v < lo) return lo; if (v > hi) return hi; return v;
}

// Pick a page according to locality (uniform in [center-span/2, center+span/2])
static int next_reference(Proc *p) {
    int half = p->span / 2;
    int base = clampi(p->center - half, 0, MAX_PAGES - 1);
    int offset = (int)(urand() % (unsigned)(p->span+1));
    int page = base + offset;
    if (page >= MAX_PAGES) page = MAX_PAGES - 1;
    // slowly drift center to simulate phase changes
    if ((urand() % 1000) == 0) {
        int drift = ((int)urand() % 41) - 20;
        p->center = clampi(p->center + drift, 0, MAX_PAGES-1);
    }
    return page;
}

static void init_proc(Proc *p, int pid, int frames_alloc, int delta, int hot_span) {
    memset(p, 0, sizeof(*p));
    p->pid = pid;
    p->active = true;
    p->frames_alloc = frames_alloc;
    p->resident = (int*)malloc(sizeof(int)*frames_alloc);
    p->last_use = (unsigned*)malloc(sizeof(unsigned)*frames_alloc);
    for (int i=0;i<frames_alloc;i++){ p->resident[i] = -1; p->last_use[i]=0; }
    p->resident_count = 0;
    p->center = (urand() % MAX_PAGES);
    p->span   = clampi(hot_span, 8, MAX_PAGES);
    p->delta = delta;
    p->window = (int*)malloc(sizeof(int)*delta);
    p->inwin_count = (int*)calloc(MAX_PAGES, sizeof(int));
    for (int i=0;i<delta;i++) p->window[i] = -1;
    p->wpos = 0;
    p->wss = 0;
}

// Reallocate frames array when frames_alloc changes
static void resize_frames(Proc *p, int new_frames) {
    if (new_frames < 1) new_frames = 1;
    int *new_res = (int*)malloc(sizeof(int)*new_frames);
    unsigned *new_last = (unsigned*)malloc(sizeof(unsigned)*new_frames);
    // keep as many recent pages as possible (copy best LRU)
    // simple strategy: copy first min
    int copy = (p->resident_count < new_frames) ? p->resident_count : new_frames;
    for (int i=0;i<new_frames;i++){ new_res[i]=-1; new_last[i]=0; }
    // pick copy most recent by last_use
    for (int c=0;c<copy;c++){
        int best=-1; unsigned bestts=0;
        for (int i=0;i<p->frames_alloc;i++){
            if (p->resident[i] != -1 && p->last_use[i]>=bestts){
                bestts = p->last_use[i]; best = i;
            }
        }
        if (best>=0){
            new_res[c] = p->resident[best];
            new_last[c] = p->last_use[best];
            p->resident[best] = -1; // mark taken
        }
    }
    free(p->resident); free(p->last_use);
    p->resident = new_res; p->last_use = new_last;
    p->frames_alloc = new_frames;
    // recount
    int rc=0; for (int i=0;i<new_frames;i++) if (p->resident[i]!=-1) rc++;
    p->resident_count = rc;
}

// Update working set ring and |WSS|
static void ws_push(Proc *p, int page){
    int out = p->window[p->wpos];
    if (out >= 0) {
        p->inwin_count[out]--;
        if (p->inwin_count[out]==0) p->wss--;
    }
    p->window[p->wpos] = page;
    p->wpos = (p->wpos+1)%p->delta;
    if (p->inwin_count[page]==0) p->wss++;
    p->inwin_count[page]++;
}

// find hit slot or -1
static int find_resident_slot(Proc *p, int page) {
    for (int i=0;i<p->frames_alloc;i++){
        if (p->resident[i] == page) return i;
    }
    return -1;
}

// choose victim slot (LRU)
static int choose_victim(Proc *p) {
    int victim=-1; unsigned best=~0u;
    for (int i=0;i<p->frames_alloc;i++){
        if (p->resident[i]==-1) return i; // free
    }
    for (int i=0;i<p->frames_alloc;i++){
        if (p->last_use[i] < best) { best = p->last_use[i]; victim = i; }
    }
    return victim;
}

static void ref_page(Sys *sys, Proc *p, int page){
    if (!p->active) return;
    p->refs++;
    p->instr_in_interval++;
    ws_push(p, page);
    int slot = find_resident_slot(p, page);
    if (slot >= 0) {
        p->last_use[slot] = sys->now;
        return;
    }
    // fault
    p->faults++; p->pf_in_interval++;
    int vic = choose_victim(p);
    if (p->resident[vic]==-1) { p->resident_count++; }
    p->resident[vic] = page;
    p->last_use[vic] = sys->now;
}

// sum of WSS
static int sum_WSS(Sys *sys){
    int D=0;
    for (int i=0;i<sys->cfg.nprocs;i++){
        Proc *p = &sys->procs[i];
        if (!p->active) continue;
        D += p->wss;
    }
    return D;
}

// sum of frames allocated to active procs
static int sum_frames(Sys *sys){
    int s=0;
    for (int i=0;i<sys->cfg.nprocs;i++){
        Proc *p = &sys->procs[i];
        if (!p->active) continue;
        s += p->frames_alloc;
    }
    return s;
}

static void ws_control(Sys *sys){
    // Working Set based load control:
    // If D > m, suspend processes (largest WSS first) until sum ≤ m.
    int D = sum_WSS(sys);
    if (D <= sys->cfg.total_frames) return;
    // build list
    int idx[MAX_PROCS], n=0;
    for (int i=0;i<sys->cfg.nprocs;i++) if (sys->procs[i].active) idx[n++]=i;
    // sort by wss desc
    for (int a=0;a<n;a++) for (int b=a+1;b<n;b++){
        if (sys->procs[idx[a]].wss < sys->procs[idx[b]].wss){
            int t=idx[a]; idx[a]=idx[b]; idx[b]=t;
        }
    }
    for (int k=0;k<n && D > sys->cfg.total_frames; k++){
        Proc *p = &sys->procs[idx[k]];
        p->active = false;
        D -= p->wss;
    }
}

static void pff_control(Sys *sys){
    // For each active process: if PFR > high → give frame; if < low → take one.
    // Keep global frames bound.
    int total = sys->cfg.total_frames;
    int used = sum_frames(sys);
    for (int i=0;i<sys->cfg.nprocs;i++){
        Proc *p = &sys->procs[i];
        if (!p->active) continue;
        double pfr = (p->instr_in_interval==0)?0.0:
                     (double)p->pf_in_interval / (double)p->instr_in_interval;
        if (pfr > sys->cfg.pfr_high && used < total){
            resize_frames(p, p->frames_alloc + 1);
            used++;
        } else if (pfr < sys->cfg.pfr_low && p->frames_alloc > 1){
            resize_frames(p, p->frames_alloc - 1);
            used--;
        }
        p->pf_in_interval = 0;
        p->instr_in_interval = 0;
    }
}

static void load_control(Sys *sys){
    // If system PFR too high (pressure), suspend lowest-efficiency procs
    // Efficiency proxy: frames_alloc / wss  (smaller is worse)
    // Or use recent PFR as penalty.
    double pf_sum=0.0, instr_sum=0.0;
    for (int i=0;i<sys->cfg.nprocs;i++){
        Proc *p=&sys->procs[i];
        pf_sum += p->pf_in_interval;
        instr_sum += p->instr_in_interval;
    }
    double sys_pfr = (instr_sum==0)?0.0: pf_sum / instr_sum;
    if (sys_pfr < sys->cfg.sys_pfr_high) {
        // maybe try to resume one suspended process if room (D ≤ m)
        int D = sum_WSS(sys);
        if (D <= sys->cfg.total_frames) {
            for (int i=0;i<sys->cfg.nprocs;i++){
                Proc *p=&sys->procs[i];
                if (!p->active){
                    p->active = true;
                    break;
                }
            }
        }
    } else {
        // suspend one worst-off process
        int worst = -1; double worstScore = -1.0;
        for (int i=0;i<sys->cfg.nprocs;i++){
            Proc *p=&sys->procs[i];
            if (!p->active) continue;
            double eff = (p->wss==0)?1.0 : (double)p->frames_alloc / (double)p->wss;
            double pfr = (p->instr_in_interval==0)?0.0:
                         (double)p->pf_in_interval / (double)p->instr_in_interval;
            double score = pfr + (1.0 - eff); // higher worse
            if (score > worstScore){ worstScore = score; worst = i; }
        }
        if (worst>=0) sys->procs[worst].active = false;
    }
    // reset window counters for next control epoch
    for (int i=0;i<sys->cfg.nprocs;i++){
        sys->procs[i].pf_in_interval=0;
        sys->procs[i].instr_in_interval=0;
    }
}

static void parse_args(int argc, char **argv, Config *cfg){
    // defaults
    cfg->mode = MODE_WS;
    cfg->nprocs = 6;
    cfg->total_frames = 200;
    cfg->ticks = 50000;
    cfg->delta = 64;
    cfg->pfr_low = 0.05;
    cfg->pfr_high = 0.20;
    cfg->sys_pfr_high = 0.25;

    for (int i=1;i<argc;i++){
        if (!strncmp(argv[i], "--mode=", 7)){
            const char *m = argv[i]+7;
            if (!strcmp(m,"ws")) cfg->mode=MODE_WS;
            else if (!strcmp(m,"pff")) cfg->mode=MODE_PFF;
            else if (!strcmp(m,"load")) cfg->mode=MODE_LOAD;
        } else if (!strncmp(argv[i],"--procs=",8)){
            cfg->nprocs = atoi(argv[i]+8);
        } else if (!strncmp(argv[i],"--frames=",9)){
            cfg->total_frames = atoi(argv[i]+9);
        } else if (!strncmp(argv[i],"--ticks=",8)){
            cfg->ticks = atoi(argv[i]+8);
        } else if (!strncmp(argv[i],"--delta=",8)){
            cfg->delta = atoi(argv[i]+8);
        } else if (!strncmp(argv[i],"--pfr-low=",10)){
            cfg->pfr_low = atof(argv[i]+10);
        } else if (!strncmp(argv[i],"--pfr-high=",11)){
            cfg->pfr_high = atof(argv[i]+11);
        } else if (!strncmp(argv[i],"--sys-pfr-high=",16)){
            cfg->sys_pfr_high = atof(argv[i]+16);
        }
    }
    if (cfg->nprocs > MAX_PROCS) cfg->nprocs = MAX_PROCS;
    if (cfg->total_frames > MAX_FRAMES) cfg->total_frames = MAX_FRAMES;
}

int main(int argc, char **argv){
    srand((unsigned)time(NULL));
    Sys sys; memset(&sys,0,sizeof(sys));
    parse_args(argc, argv, &sys.cfg);

    // initial equal share of frames
    int base_frames = sys.cfg.total_frames / sys.cfg.nprocs;
    if (base_frames < 2) base_frames = 2;

    // init procs with varying locality spans
    for (int i=0;i<sys.cfg.nprocs;i++){
        int span = 32 + (i*7)%200; // different hot-set sizes
        init_proc(&sys.procs[i], i, base_frames, sys.cfg.delta, span);
    }

    // main loop
    unsigned control_every = 1000; // control epoch (instructions)
    for (sys.now=1; sys.now<= (unsigned)sys.cfg.ticks; sys.now++){
        // reference from each active proc
        for (int i=0;i<sys.cfg.nprocs;i++){
            Proc *p=&sys.procs[i];
            if (!p->active) continue;
            int page = next_reference(p);
            ref_page(&sys, p, page);
        }

        // control at epoch
        if (sys.now % control_every == 0){
            if (sys.cfg.mode == MODE_WS){
                ws_control(&sys); // suspend if D > m
            } else if (sys.cfg.mode == MODE_PFF){
                pff_control(&sys); // per-proc frames ++/--
            } else if (sys.cfg.mode == MODE_LOAD){
                load_control(&sys); // suspend/resume by system PFR
            }
        }
    }

    // final stats
    unsigned long total_refs=0, total_faults=0;
    int active=0, suspended=0;
    int D = sum_WSS(&sys);
    int used = sum_frames(&sys);

    printf("== Simulation complete ==\n");
    printf("Mode: %s, procs=%d, frames(m)=%d, ticks=%d, Δ=%d\n",
        (sys.cfg.mode==MODE_WS?"WS":(sys.cfg.mode==MODE_PFF?"PFF":"LOAD")),
        sys.cfg.nprocs, sys.cfg.total_frames, sys.cfg.ticks, sys.cfg.delta);

    for (int i=0;i<sys.cfg.nprocs;i++){
        Proc *p=&sys.procs[i];
        double pfr = (p->refs==0)?0.0: (double)p->faults / (double)p->refs;
        printf("[P%02d] %s frames=%3d refs=%7u faults=%7u PFR=%.4f WSS=%4d span=%3d\n",
               p->pid, p->active?"ACTIVE ":"SUSPEND",
               p->frames_alloc, p->refs, p->faults, pfr, p->wss, p->span);
        total_refs += p->refs;
        total_faults += p->faults;
        if (p->active) active++; else suspended++;
    }
    double sys_pfr = (total_refs==0)?0.0: (double)total_faults / (double)total_refs;
    printf("Summary: ACTIVE=%d, SUSPENDED=%d, ΣWSS=D=%d, Σframes=%d (m=%d), System PFR=%.4f\n",
           active, suspended, D, used, sys.cfg.total_frames, sys_pfr);

    // cleanup
    for (int i=0;i<sys.cfg.nprocs;i++){
        Proc *p=&sys.procs[i];
        free(p->resident); free(p->last_use); free(p->window); free(p->inwin_count);
    }
    return 0;
}
```

- Working Set(WS)모델
  - ws_push()가 $$\delta-윈도우$$로 WSS_i를 추정
  - ws_control()이 $$ D = \sum WSS_i$$가 m을 초과하면 WSS가 큰 프로세스부터 중단
- PFF(Page-Fault Frequency)
  - 각 프로세스별 pf_in_interval / instr_in_interval로 PFR_i 추정
  - pff_control()이 PFR_high 초과 시 프레임 추가, PFR_low 미만이면 프레임 회수
  - 프레임 증감 시 resize_frames()가 LRU 킵하여 재배열
- Load Control (system-level)
  - load_control()이 시스템 PFR(모든 프로세스 합계)를 보고
    높으면 효율 낮은 프로세스를 일시 중단
  - 낮으면 조건부로 재개

[시뮬레이션 팁]
- 프레임이 빠듯하고 $$ Δ/Span$$을 키우면 쓰레싱 경향이 커짐
- --pfr-low, --pfr-high, --sys-pfr-high를 바꿔 민감도를 테스트
- WS 모드에서 --delete를 키우면 WSS가 커져 D>m가 쉽게 발생 -> 중단 정책이 자주 트리거됨.

(2)Page-Fault Frequency (PFF) Algorithm
[개념]
- 페이지 폴트율(Page Fault Rate, PFR)을 직접 모니터링하여 프로세스별로 프레임 수를 동적으로 조정하는 방법

[동작방식]
    1. 각 프로세스에 대해 최근 페이지 폴트 간 시간 간격을 측정합니다.
    2. 폴트율이 너무 높으면 -> 프레임을 더 할당
    3. 폴트율이 너무 낮으면 -> 일부 프레임을 회수(다른 프로세스에 재분배)
    4. 시스템 전체적으로 페이지 폴트율이 안정될 때까지 조정 반복.

[기준값 설정]
- 두 개의 임계값을 둠
  - $$PFR_low$$ : 너무 낮은 경우 -> 프레임 회수 가능
  - $$PFR_high$$ : 너무 높은 경우 -> 프레임 추가 필요

[모델식]
$$
\mathrm{PFR}_i =
\frac{\text{Page Faults in interval } \Delta}{
\text{Instructions executed in } \Delta}    

-> PFR_i > PFR_high => Allocate More Frames
-> PFR_i < PFR_low => Deallocate Some Frames
$$  

[관측 지표]
- 각 프로세스의 페이지 폴트 횟수를 시간 단위로 측정하면 주기적 진동 패턴이 관측됨
- 안정 구간에서는 PFR이 거의 일정하게 유지됩니다.

(3) Load Control (System-Level Control)
[개념]
- 시스템 전체의 다중 프로그래밍 정도 (Degree of Multiprogramming)를 조절합니다.
- CPU 활용률, 페이지 폴트율, I/O 대기율을 실시간 관측하며 프로세스 수를 동적으로 관리.

[동작 방식]
    1. CPU Utilization이 떨어지고, 페이지 폴트율이 급증하면 -> 쓰레싱 구간 진입 감지.
    2. 일부 프로세스를 Swap Out하여 물리 프레임 확보.
    3. 남은 프로세스가 안정되면 -> 순차적으로 Swap in

| 지표 | 의미 | 관측 방식 |
|-------|-------|------| 
| CPU Utilization | CPU가 실제로 바쁘게 일하는 비율 | 프로세서 스케쥴러 로그|
| Page Fault Rate | 단위 시간 당 페이지 폴트 수 | MMU 카운터|
| I/O Queue Length | 디스크 대기열 길이 | 커널 I/O 스케쥴러 통계 |
| Active Process Count | 동시에 실행중인 프로세스 수 | OS 프로세스 테이블|

[실제 데이터 관측 예시]
| 지표 | 정상 구간 | 쓰레싱 구간 | 단위 |
|------|--------|----------|------|
| vmstat si/so | 거의 0 | 수백 ~ 수천 증가 | kb/s |
| sar -B(paging/pageout) | 100 ~ 200 | 10,000이상 | 페이지/s|
| top CPU idle | 10~30% | 90% 이상 | % |
| iostat %util(디스크) | <40% | >90% | %|
| 페이지 폴트율(PFR) | 0.01 | 0.5 ~ 1.0 이상 | fault/instr |
> 즉, 디스크는 바쁘고 CPU는 한가한 비정상적 상태가 바로 쓰레싱의 전형적인 시그널 입니다.

시스템 총 요구 프레임
$$
D(t) = \sum_i WSS_i(t)
$$

메모리 초과 조건(쓰레싱 가능성)
$$
D(t) \;>\; m
$$

### Page-Fault Frequency (PFF)
$$

$$

제어 규칙(임계값):
$$
\math{PFR}_i > \mathrm{PFR}_{\text{high}} \;\Rightarrow\; \text{프레임 추가} \quad, \quad
\mathrm{PFR}_i < \mathrm{PFR}_{\text{low}} \; \Rightarrow\; \text{프레임 회수}
$$

### CPU 활용률의 단순 모델

CPU 유휴 확률로 표현
$$
U_{\text{CPU}} \;=\; 1 \;-\; P(\text{CPU Idle})
$$

총 수요 대비 물리 프레임 비율 \(r = D/m\) 일 때, (경험적 패널티 예)

$$
U_{\text{actual}}(k) \;=\; U_{\text{base}}(k)\, \times\, \begin{case}
1, & r \le 1 \\
e^{-\alpha\, (r - 1)}, & r > 1
\end{case}
$$

여기서 \U_{\text{base}}(k)는 다중 프로그래밍 정도 \(K)에서 쓰레싱이 없다고 가정한 기본 곡선

정리하면, 페이지 폴트는 가상 메모리 시스템의 정상적인 동작 일부이지만 과도한 페이지 폴트 발생은 스래싱으로 이어져 성능 문제를 일으킵니다. 
쓰레싱이 발생하면 CPU Utilization이 급격히 떨어지는 이유는 프로세스들이 지속적으로 페이지 폴트를 일으켜 I/O 대기 상태로 전환되며, CPU가 실제 명령어 실행보다 I/O 대기 상태 전환에 더 많은 시간을 쓰기 때문입니다. 즉, CPU는 더 이상 계산하지 않고 대부분의 시간을 놀게 되어 활용률이 급감합니다.적절한 메모리 관리 전략(설명된 작업 세트 기반의 부하 제어 등)을 통해 스래싱을 방지하는 것이 중요합니다.


7. 운영체제별 스왑 방식 차이 (리눅스 vs 윈도우)

운영체제마다 가상 메모리 구현과 스왑 관리에 약간의 차이가 있습니다. 여기서는 대표적으로 리눅스와 윈도우의 스왑(페이지 파일) 방식을 비교합니다.

스왑 공간의 형태: 리눅스(Linux) 시스템에서는 전통적으로 별도의 디스크 파티션을 스왑 영역으로 확보하는 방식을 사용해왔습니다. 즉, 설치 시 일정 용량의 파티션을 아예 스왑 전용으로 할당하여 사용하거나, 필요 시 일반 파일시스템 위에 스왑 파일을 만들어 사용할 수도 있습니다. 반면 윈도우(Windows) 시스템에서는 **스왑 공간을 하나의 디스크 파일(pagefile.sys)**로 관리하는 것이 일반적입니다. 윈도우의 페이지파일은 시스템 드라이브(C:)에 숨김 파일로 존재하며, 운영체제가 동적으로 그 크기를 관리합니다. 요약하면 **유닉스 계열 OS는 “swap” 파티션(또는 파일)을, 윈도우는 “페이지 파일”**을 통해 가상 메모리 스왑을 구현하며, 개념적으로 두 방식 모두 디스크상의 가상 메모리 영역이라는 점에서는 유사합니다.

크기 및 관리 방식: 윈도우는 기본 설정으로 페이지 파일의 최소/최대 크기를 자동으로 관리합니다. 일반적으로 최소 크기를 RAM 용량의 1.5배, 최대 4배 정도로 권장하며, 시스템 여건에 따라 운영체제가 페이지파일 크기를 조절합니다. 사용자는 수동으로 이 값을 변경하거나 고정할 수도 있습니다. 반면 리눅스의 스왑 파티션은 고정 크기이므로 설치 시 설정한 용량 내에서만 사용됩니다 (스왑 파티션은 미리 연속된 공간을 확보하므로 조각화 없이 빠르게 접근 가능). 최근 리눅스에서도 스왑 파일 사용이 흔해졌는데, 스왑 파일은 크기 조절이 비교적 용이하나 파일시스템 위에 있어 조각화의 영향을 받을 수 있다는 차이가 있습니다. 리눅스 관리자는 필요 시 fallocate 등의 명령으로 스왑 파일을 생성/확장하여 사용할 수 있습니다.

스왑 사용 정책: 리눅스 커널에는 **swappiness**라는 파라미터가 있어 메모리가 충분해도 스왑을 어느 정도 활용할지를 결정합니다. 기본값(60)은 비교적 적극적으로 스왑을 사용하여 캐시 공간을 확보하려는 성향이고, 값이 낮으면 가능한 RAM을 다 쓰고 나서야 스왑을 사용합니다. 윈도우에는 직접적으로 대응되는 튜닝 파라미터는 없지만, 메모리 압력이 높아질 때만 페이지파일을 활용하는 경향이 있습니다. 또한 현대 윈도우(예: Windows 10 이후)는 메모리 압축 기능을 도입하여, 스왑으로 보내기 전에 메모리 내의 데이터를 압축함으로써 물리 메모리 사용을 최적화하고 디스크 스왑을 줄이려는 노력을 합니다.

추가적인 차이점: 윈도우 8/10 이상에서는 기본 페이지파일 외에 swapfile.sys라는 추가 파일을 사용합니다. 이 작은 스왑 파일(~~200MB 수준)는 UWP/메트로 앱 등의 특정 메모리 관리에 활용되며, 일반 프로세스의 메모리 관리에 사용되는 pagefile.sys와 역할을 구분합니다. 리눅스에는 이와 대응되는 이중 구조는 없으며, 모든 스왑 공간이 통합된 리소스로 활용됩니다. 대신 리눅스는 여러 개의 스왑 파티션/파일을 가질 수 있고 우선순위를 지정하여 사용하는 기능을 제공합니다.

요약하면, 리눅스와 윈도우 모두 가상 메모리를 위해 디스크를 활용하지만 구현 세부가 다릅니다. 리눅스는 전통적으로 전용 스왑 파티션을 쓰고 swappiness 등으로 동작을 조절하며, 윈도우는 유동적인 페이지파일을 사용하고 자동 크기 관리를 합니다. 이러한 차이에도 불구하고 궁극적으로 양쪽 모두 부족한 물리 메모리를 보완하기 위해 디스크를 사용하는 원리는 동일합니다.

8. 몇가지 가상 시나리오
### 가상 시나리오

>> 사용자가 메모장(NotePad) 프로그램을 실행하는 상황.


    1. **프로그램 실행 요청**
    - 사용자가 메모장을 실행하면 OS는 notepad.exe 파일을 디스크(SSD/HDD)에서 읽습니다.
    - 이 실행 파일은 수 MB 크기일 수 있지만, OS는 처음부터 전부 메모리에 올리지 않습니다.
    - 대신, 실행에 필요한 최소한의 페이지(예: 코드 첫 부분)만 로드하고, 나머지는 "필요할 때 가져오도록" 표시합니다.
    - 이 방식을 **Demanding Page**라고 합니다.

    2. **첫 실행 중 페이지 폴트 발생**
    - 프로그램이 시작되면, CPU는 main() 함수의 첫 명령어를 실행하려고 합니다.
    - 그런데 해당 코드가 아직 디스크에만 있고 RAM에는 없는 상태입니다.
    - MMU가 페이지 테이블을 확인했는데, 유효 비트가 꺼져 있습니다.(즉,0)
    - CPU가 페이지 폴트 예외(Page Fault Exception 즉, trap)를 발생시킵니다. 

    trap -> 제어권이 CPU에서 커널로 넘어감 -> 디스크 Exe 실행 파일을 읽어옴 -> 빈 메모리 프레임(4Kb)을 확보 -> 디스크에서 메모리로 페이지 복사 -> 페이지 테이블 갱신(가상주소 <-> 물리주소 연결) -> 폴트가 발생했던 명령어 재실행

    이 일련의 과정을 통해 CPU는 다시 main() 함수를 정상적으로 실행할 수 있습니다.

    3. **프로그램이 점점 커지며 추가 폴트 발생**
    - 사용자가 메모장에 텍스트를 입력하거나, 파일을 열면 프로그램은 추가 데이터 영역(heap, stack)에 접근하게 됩니다.
    - 이때도 아직 메모리에 없는 페이지에 접근하면 새로운 페이지 폴트가 발생하고, OS가 그때그때(On-demand) 필요한 페이지를 불러옵니다.

    4. **페이지 교체(page Replacement)**
    - 만약 RAM이 가득 찼다면?
    OS는 오래쓰지않은 페이지(LRU 알고리즘 등)를 디스크의 스왑 영역으로 내보내고, 새 페이지를 메모리에 올립니다.
    - 이때도 폴트가 발생하면, 이건 정상적인 교체 과정입니다. 

>> Trap이란 CPU가 프로그램을 실행하는 도중, **의도적으로 커널**로 제어를 넘기는 인터럽트 입니다. 
|-------|---------|--------|
|System Call Trap| 사용자 프로그램이 커널 서비스를 요청할 때|read(), write()|
|Exception Trap | 실행 중 오류나 특수 상황 발생 | 0으로 나누기, 페이지 폴트 등|
| Debug Trap | 디버깅 시점 제어용 | Breakpoint, Single-step 실행|

9. 요약 및 결론

가상 메모리는 운영체제가 제공하는 메모리 관리의 핵심 기술로서, 한정된 물리 메모리로도 다중 프로세스 환경을 구현하고 대용량 프로그램을 실행할 수 있게 합니다. 페이지와 프레임 단위의 주소 변환, 페이지 테이블과 TLB를 통한 효율적인 매핑, 디스크 스왑 공간 활용을 통한 메모리 확장 등의 원리를 바탕으로, 가상 메모리는 프로세스마다 독립적이고 거대한 가상 주소 공간을 제공하여 시스템 성능과 안정성을 높입니다.

물론 가상 메모리 사용에는 약간의 성능 오버헤드와 구현 복잡성이 따르며, 특히 페이지 폴트 발생이 잦을 경우 스래싱으로 인한 성능 저하를 유발할 수 있습니다. 따라서 운영체제는 효율적인 페이지 교체 알고리즘과 메모리 부담 제어 정책을 통해 이러한 문제를 완화합니다. 현대의 리눅스, 윈도우 등 주요 OS는 가상 메모리를 기반으로 동작하면서도 각기 고유한 방식으로 스왑을 관리하여 최적의 성능을 도모합니다.

결론적으로, 가상 메모리는 제한된 메모리 자원을 최대한 활용하여 컴퓨터 시스템의 가능성을 확장하는 필수적인 기술입니다. 이 보고서에서 다룬 개념들과 동작 원리, 그리고 다양한 측면의 고려사항을 통해 가상 메모리 시스템에 대한 이해를 높이고자 합니다. 운영체제의 가상 메모리 관리에 대한 깊은 이해는 시스템 성능 튜닝, 소프트웨어 개발 최적화, 그리고 컴퓨터 공학 연구 등 여러 분야에서 중요한 밑거름이 됩니다

참고자료: geeksforgeeks, stackoverflow, techtarget, superuse
