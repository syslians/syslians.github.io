---
layout: post
title: "하이퍼바이저 vs Virtual Machine"
categories: [네트워크, 가상화, VMware]
author: cotes
published: true
---

## 가상 머신(VM), 가상화란?

**가상화는 곧 추상화의 한 형태이다.**

가상 머신(Virtual Machine, VM)은 물리 서버 위에서 독립적인 컴퓨팅 환경을 제공하는 소프트웨어 시스템 이라고 할 수 있겠습니다.
VM은 실제 하드웨어처럼 CPU, RAM, DISK, Network device를 완전히 에뮬레이션 하며, 자체 운영 체제(OS)와 애플리케이션을 구동합니다.
즉, 한대의 물리 서버에서 여러 개의 VM을 실행하면, 각각의 VM은 격리된 독립 머신처럼 동작합니다. VMware의 경우, ESXi가 대표적인
Type-1 하이퍼바이저(bare-metal 설치형 가상화 플랫폼)로써 VM들을 구동하며, 이를 포함한 vSphere 제품군이 엔터프라이즈급 가상화 인프라를
구성합니다. 예를 들어 VMware ESXi는 독립 실행형 커널(VMKernel)을 갖춘 Type-1 하이퍼바이저로, 호스트 위에 설치되는 일반 OS 없이도
직접 하드웨어 자원을 제어하여 여러 VM을 구동합니다.

- **가상 머신은 하나의 호스트에서 여러 개를 생성 가능해 물리 서버 자원을 유연하게 활용할 수 있습니다.
- **각 VM은 하이퍼바이저를 통해 물리 자원을 할당받아 실행되며, 서로 격리된 환경으로 동작합니다.

### 하이퍼바이저: Type1 vs Type2
하이퍼바이저는 물리 서버의 하드웨어 자원을 가상화하여 VM에 제공하는 **가상화 매니저 입니다. 하이퍼바이저는 크게 두가지 형태가 있습니다. 
하나는 **Type-1 하이퍼바이저(Bare-metal)** 로 ESXi나 Hyper-V 같이 하이퍼바이저 자체가 호스트 하드웨어 위에 직접 설치되어 동작합니다.
다른 하나는 **Type-2 하이퍼바이저(Hosted)** 로 VMWare Workstation이나 VirtualBox 처럼 일반 운영체제 위에 애플리케이션 형태로
설치되는 방식입니다. 주요 차이점은 아래와 같습니다.

- **구동 구조**: Type-1 **베어메탈** 위에 직접 설치되어 하드웨어 자원을 바로 제어합니다. 반면, Type-2는 호스트 OS 위에서 애플리케이션으로
  동작하므로, 모든 VM 명령은 먼저 호스트 OS를 거칩니다.

- **성능과 자원 효율**: Type-1 하이퍼바이저는 OS 레이어를 거치지 않고 CPU와 직접 관리하므로 VM 성능이 높고 지연이 적습니다. Type-2
  는 호스트 OS가 자원을 중간에 관리하므로 약간의 성능 손실이 있습니다.

- **격리 및 보안**: Type-1 구조는 별도의 호스트 OS가 없으므로 VM간에 공유레이어가 없어 격리가 강력합니다. 실질적으로 한 VM에서
  발생한 보안 사고가 다른 VM으로 확산되기 어렵습니다.

- **관리 편의성**: Type-2는 일반 PC에서 손쉽게 설치하여 개인이나 개발 환경에서 사용하기 좋습니다. 반면, Type-1은 서버급 관리 지식이
  필요하며, 기업용 데이터센터등에 적합합니다.

### 가상화의 주요 개념

### CPU 가상화(vCPU)
하이퍼바이저는 물리 CPU를 VM에 가상 CPU(vCPU)로 제공하여 동시에 여러 VM이 실행되도록 합니다. CPU 앞에 virtual 이라는 단어에서 볼 수 
있듯이 가상화된 CPU를 의미합니다. 즉, 물리적 CPU 자원을 가상화하여 여러 가상 머신이 동일한 물리 서버에서 동작할 수 있도록 해줍니다.
최신 프로세서는** Intel VT-x**나 **AMD-V**와 같은 하드웨어 지원 기능을 갖추고 있어, 특권 명령을 하이퍼바이저에 빠르게 전달합니다. 
하이퍼바이저는 각 VM에 할당된 vCPU가 실제 물리 CPU 코어를 공유하며, **시분할(time-slice)**  방식으로 CPU 시간을 스케쥴링 합니다. 

이렇게 하여 하나의 물리 CPU가 여러개의 vCPU 처럼 동작하며, 이론적으로 VM은 실제 머신과 거의 동일한 환경인것처럼 프로그램이 실행됩니다. 
예를 들어, 코어 4개를 가진 CPU 자원을 2개씩 나누어 8개의 vCPU로 구성할 수 있습니다. AWS, GCP와 같은 클라우드 서비스나 가상화 플랫폼에서도
하이퍼스레딩 기술을 도입하여 하나의 CPU 코어를 최대 2개의 vCPU로 나누어 할당하고 있습니다. 이론적으로 3개 이상의 vCPU로 나누는 건 가능하지만,
vCPU 끼리 같은 물리적 CPU 자원을 공유하고 있기 때문에 각여러 가상머신이 동시에 높은 부하가 걸리게 되면 성능 저하가 발생할 수 있습니다.
CPU 가상화는 가능한 한 물리 자원을 그대로 사용하려 하고, 오버헤드가 생기는 부분만 소프트웨어로 처리합니다.

![BitOperations](https://user-images.githubusercontent.com/67403886/157030545-4f05f1b9-efb0-4730-9a95-87091180537f.png)

                                                        <그림1: vcpu 아키텍쳐>
                                                                                       

![BitOperations](https://hoststud.com/attachments/1614317912921-png.1341)

                                                        <그림2: vcpu 아키텍쳐>

### 메모리 가상화(vMemory)
각 VM은 자신만의 **게스트 물리 메모리(guest physical memory)** 공간을 갖고 있다고 생각하지만, 실제로는 **호스트의 물리 메모리(Host RAM)**
에 맵핑됩니다. 하이퍼바이저는 VM 마다 **그림자 페이지 테이블**이나 EPT(Extended Page Tables)같은 기술로 게스트의 메모리 주소를 
호스트 메모리 주소에 대응시킵니다. 예를 들어 VMware ESXi는 게스트의 물리 메모리를 호스트 물리 메모리에 백업하여 관리합니다. 또한, ESXi는
메모리 **오버커밋(Overcommit)**을 지원하여, 전체 VM의 할당 메모리 합이 실제 물리 메모리보다 커질 수 있습니다. 이 경우, 중복된 메모리 페이지를
하나로 합쳐 사용하는 **TPS(Transpert Page Sharing)**나, 사용 중인 메모리를 호스트에 회수하는 **풍선 드라이버(Ballooing)**, 불필요한
메모리를 디스크로 옮기는 **Swap Out** 기법 등으로 자원을 효율화 합니다. 예를 들어 TPS는 중복된 메모리 페이지를 하나로 통합하여 물리 메모리를
절약합니다.
![BitOperations](<img width="1020" height="738" alt="image" src="https://github.com/user-attachments/assets/1ffdea09-3d9e-4866-9c3a-aa7ea12112f5" />

                                                        <그림3: Virtual Memory Swap in/out>

![BitOperations](https://www.vmwarearena.com/wp-content/uploads/2014/05/Memory-Ballooning-300x253.jpg)

                                                        <그림4: Virtual Memory Balooning>
### GPU 가상화(VGPU, Virtual Graphic Card)
![BitOperations](https://krutavshah.github.io/GPU_Virtualization-Wiki/assets/img/vgpu-overview.49e0b6b1.png)

### Storage 가상화(VSAN,Virtual Storage)

![BitOperations](https://ik.imagekit.io/upgrad1/abroad-images/imageCompo/images/1_21VI6V7.png?pr-true)

                                                        <그림6: Virtual Storage> 

### 장치 가상화(Device Emulation)
가상 머신은 네트워크 카드, 디스크 컨트롤러 같은 가상 하드웨어 장치를 통해 I/O를 수행합니다. 하이퍼바이저는 이러한 가상 장치를 에뮬레이션
하거나, 성능 최적화를 위해 패러베추얼(paravirtualized) 드라이버(e.g VMXNET3 가상 NIC, PVSCSI 가상 SCSI 등)를 제공합니다.
결과적으로 VM 내부의 운영체제는 마치 실제 장치 드라이버를 다루는 것처럼 가상 장치를 사용할 수 있습니다. 이 모든 장치 가상화 레이어를 
통해 VM은 외부 세계(호스트 네트워크, 스토리지)와 투명하게 통신합니다.

### 스냅샷(Snapshot)
가상 머신 스냅샷은 VM의 **특정 시점 상태(PIT, point-in-time)**를 저장하는 기능입니다. 스냅샷은 VM의 모든 데이터와 상태(메모리, 디스크,
전원상태 등)를 캡처하여 백업이나 테스트용 롤백에 사용합니다. 스냅샷이 생성되면 하이퍼바이저는 원본 가상 디스크 파일(A)의 쓰기 작업을
중단하고, 새 데이터는 별도의 델타 파일(B)에 기록합니다. 이렇게 하면 원본 디스크(A)는 스냅샷 시점의 상태로 고정되고, 변경사항은 B 파일에
저장됩니다. 이후 스냅샷으로 복원하면 B파일을 삭제하고 VM을 A상태로 되돌립니다. 메모리 상태를 포함하도록 선택하면, 해당 시점의 RAM 내용도
저장되어 VM이 정확히 같은 상태로 복원됩니다. 스냅샷은 시스템 업데이트 전후 백업, 문제 발생 시 빠른 복구 등에 활용됩니다.


마지막으로 크롬 브라우저(V8), JVM과 같은 엔진들도 가상머신 입니다. 따라서 가상화라는 개념을 받아들일때에는 시스템 가상화(VMware, Virtual Box, AWS 플랫폼)뿐만 
아니라 개념적으로 받아들일때에는 하드웨어를 소프트웨어화 시키고, 운영체제나 하드웨어에 종속되어 호환되지 않거나, 확장성과 유연성을 확보하기 위한 목적이다. 라고 생각하시면 
될 것 같습니다. V8과 JVM의 런타임 기능은 매우 유사합니다. JIT(Just-In-Time) 방식으로 코드를 컴파일하고 실행하며, Garbage Collection을 통해 Collection Heap을 관리합니다.
소프트웨어 분야에서 가상화는 정말 폭넓게 쓰이고 중요한 개념이기에 이러한 포괄적인 관점, 접근이 필요하다 생각합니다.





참고자료: VMware와 관련 기술 문헌을 참조하여 작성되었습니다.
redhat.com, en.wikipedia.org, aws.amazon.com, aws.amazon.com ,geek-university.com, stormagic.com
geek-university.com, nakivo.com, scribd.com, community.broadcom.com, atlassian.com, blogs.vmware.com
datamotive.io, stephenwagner.com, atlassian.com

