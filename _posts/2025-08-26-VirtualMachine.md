---
layout: post
title: "Virtual Machine"
categories: [네트워크, 가상화, VMware, ESXi, HyperVisor]
author: cotes
published: true
---

## 가상 머신(VM), 가상화란?

**가상화는 곧 추상화의 한 형태이다.**

가상 머신(Virtual Machine, VM)은 물리 서버 위에서 독립적인 컴퓨팅 환경을 제공하는 소프트웨어 시스템 이라고 할 수 있겠습니다.
VM은 실제 하드웨어처럼 CPU, RAM, DISK, Network device를 에뮬레이션 하며, 자체 운영 체제(OS)와 애플리케이션을 구동합니다.
특히, 서버 가상화는 하나의 물리 하드웨어 위에 다양한, 혹은 여러개의 가상머신, 
즉, 운영체제의 인스턴스를 실행할 수 있게 해줍니다. 각각의 VM은 격리된 독립 머신처럼 동작합니다. 사용자의 입장에서 가상 서버는 물리 서버와
같은 방식으로 동작하는것으로 보입니다. 하드웨어를 운영체제에서 분리하는것은 엄청난 노력이 필요합니다. 가상화된 서버는 물리서버보다 더 확장가능하고
유연하며, 탄력적입니다. 뿐만 아니라 가상화는 클라우드 컴퓨팅을 지탱하고 있는 핵심 기술입니다. 좀 더 최근에는 OS 수준의 가상화 발전을 통해 컨테이너라
OS 추상화의 새 영역으로 나타났습니다. VMware의 경우, ESXi가 대표적인 Type-1 하이퍼바이저(bare-metal 설치형 가상화 플랫폼)로써 VM들을 구동하며, 이를 포함한 vSphere 제품군이 엔터프라이즈급 가상화 인프라를 구성합니다. 예를 들어 VMware ESXi는 독립 실행형 커널(VMKernel)을 갖춘 Type-1 하이퍼바이저로, 호스트 위에 설치되는 일반 OS 없이도
직접 하드웨어 자원을 제어하여 여러 VM을 구동합니다.


- **가상 머신은 하나의 호스트에서 여러 개를 생성 가능해 물리 서버 자원을 유연하게 활용할 수 있습니다.
- **각 VM은 하이퍼바이저를 통해 물리 자원을 할당받아 실행되며, 서로 격리된 환경으로 동작합니다.

### 하이퍼바이저: Type1 vs Type2
하이퍼바이저는 물리 서버의 하드웨어 자원을 가상화하여 VM에 제공하는 **가상화 매니저 입니다. 더 정확하게 이야기한다면, 가상머신이 구동되는 물리적 기저 하드웨어
간을 중재하는 소프트웨어 계층입니다. 하이퍼바이저는 게스트 OS간 시스템 자원 공유를 담당합니다. 이때 하이퍼바이저를 통해 가상 머신 간 또는 하드웨어로의 접근은 베타적으로
분리됩니다. 게스트 OS는 독립적입니다. 따라서, 같을 필요가 없습니다. 예를 들면 Cent OS와 Windows, FreeBSD등이 함께 동작할 수 있습니다.
하이퍼바이저는 크게 두가지 형태가 있습니다. 

하나는 **Type-1 하이퍼바이저(Bare-metal)** 로 ESXi나 Hyper-V, KVM 같이 하이퍼바이저 자체가 호스트 하드웨어 위에 직접 설치되어 동작합니다.
KVM은 리눅스 커널을 하이퍼바이저로 변모시킵니다. 다른 하나는 **Type-2 하이퍼바이저(Hosted)** 로 VMWare Workstation이나 VirtualBox 처럼 일반 운영체제 위에 애플리케이션 형태로
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
있듯이 가상화된 CPU를 의미합니다. 즉, 물리적 CPU 자원을 가상화하여 여러 가상 머신이 동일한 물리 서버에서 동작할 수 있도록 해줍니다.vCPU는 물리적인 Core를 기반으로 하며, 가상화 기술을 통해 물리적인 CPU Core 하나를 여러 vCPU 로 나누서 사용할 수 있습니다. 
최신 프로세서는** Intel VT-x**나 **AMD-V**와 같은 x86 플랫폼에서 하드웨어 지원 기능을 갖추고 있어, 특권 명령(Priviliged Instruction)을 하이퍼바이저에 빠르게 전달합니다. 하이퍼바이저는 각 VM에 할당된 vCPU가 실제 물리 CPU 코어를 공유하며, **시분할(time-slice)**  방식으로 CPU 시간을 스케쥴링 합니다. 
기존의 시분할 방식은 프로세스 단위로 스케쥴링을 했다면, 하이퍼바이저는 가상머신들에게 할당한 vCPU를 스케쥴링하며 마치 여러대의 가상머신들을 동시에 실행하는것처럼 동작하게 할 수 있습니다.

이렇게 하여 하나의 물리 CPU가 여러개의 vCPU 처럼 동작하며, 이론적으로 VM은 실제 머신과 거의 동일한 환경인것처럼 프로그램이 실행됩니다. 예를 들어, 코어 4개를 가진 CPU 자원을 2개씩 나누어 8개의 vCPU로 구성할 수 있습니다. AWS, GCP와 같은 클라우드 서비스나 가상화 플랫폼에서도 하이퍼스레딩 기술을 도입하여 하나의 CPU 코어를 최대 2개의 vCPU로 나누어 할당하고 있습니다. 이론적으로 3개 이상의 vCPU로 나누는 건 가능하지만, vCPU 끼리 같은 물리적 CPU 자원을 공유하고 있기 때문에 각여러 가상머신이 동시에 높은 부하가 걸리게 되면 성능 저하가 발생할 수 있습니다. CPU 가상화는 가능한 한 물리 자원을 그대로 사용하려 하고, 오버헤드가 생기는 부분만 소프트웨어로 처리합니다.

## 전가상화 (Fukk Virtualization)
하드웨어를 완전히 가상화하는 방식으로, Hardware Virtual Machine 이라고도 합니다. 가상 머신들은 전부 물리자원에 연결되어 있다고 생각합니다. 그러다 보니, 가상머신들의 System call은 전부 하드웨어가 아닌 **하이퍼바이저**가 처리해서 보내줍니다.

<figure>
  <img src="https://github.com/lee20h/blog/assets/59367782/41ac69cd-7524-46b1-83dc-90f9ec87ec13" alt="샘플 이미지" width="400">
</figure>

[전가상화(Full Vertualization)]

### 구현 방법
- 하드웨어 자원 가상화
- 소프트웨어적으로 구현
두 가지 방법으로 구현할 수 있으며, 요즘에는 전가상화 == 하드웨어 자원 가상화로 쓰이고 있습니다.

먼저 Dual-mode operation(이중 동작 모드)에 대해서 알고 넘어가봅시다.

<figure>
  <img src="https://github.com/lee20h/blog/assets/59367782/23f8bccc-84b4-4c61-9ac6-e29262e80f0f" alt="샘플 이미지" width="400">
</figure>

[Virtual CPU 아키텍쳐]

사용자와 OS는 시스템 자원을 공유하는데 사용자가 제한없이 사용하게 되면 메모리 내의 주요 자원들을 망가뜨릴 수 있습니다. 이러한 부분을 보호하는 메커니즘입니다. 
- User Mode
- Kernel Mode

두가지 모드로 동작하게 되며, 애플리케이션은 User-mode에서 동작하다가 Sㅛstem Call을 OS에게 요청한 경우, Kernel-mode로 전환되어 요청된 서비스를 실행시킨 뒤 다시 User-mode로 전환되게 됩니다.

### Trap && Emulation
<figure>
  <img src="https://github.com/lee20h/blog/assets/59367782/be474a24-0fe3-49e6-a6f2-ecaf36bbb3b4" alt="샘플 이미지" width="400">
</figure>

[Trap & Emulation]

하이퍼바이저는 Root mode, 논리화된 도메인들은 Non-root mode로 동작됩니다. 여기서 도메인들은 **privileged** command를 실행하면 **Trap**이 발생하고, Trap Handler가 vm exit 명령을 통해 하이퍼바이저가 실행할 수 있게 합니다.
실행이 완료되면 vm enter 명령을 통해 다시 도메인이 실행되도록 하여 하드웨어에 대한 명령을 내릴 수 있는 방식입니다. 따라서 하이퍼바이저와 커널의 처리 방식에서 오버헤드가 발생하여 성능 저하가 일어납니다.

### Binary Translation
<figure>
  <img src="https://github.com/lee20h/blog/assets/59367782/7308d85c-6ebc-41b2-8584-bc3c1bbc035c" alt="샘플 이미지" width="400">
</figure>

[Binary Translation]

논리화된 도메인에서 Guest OS는 다양한 OS를 사용할 수 있습니다. 이로 인해, 가상화된 하드웨어에 요청 인터페이스도 OS마다 다르게 되는데, 하나의 형식으로 변환해주는 작업을 Binary Translation 이라고 합니다.

### Software Assisted - Full Virtualization (BT - Binary Translation)
<figure>
  <img src="https://github.com/lee20h/blog/assets/59367782/5e5850b7-acb8-49d1-8823-117ef178e48f" alt="샘플 이미지" width="400">
</figure>

[Binary Translation]

소프트웨어 지원 전가상화를 한 경우를 살펴봅시다. Binary Translation을 이용하여 명령어를 trap과 가상화하여 실행하게 됩니다. 위의 그림과 동일하게 하드웨어를 emulate하여 명령을 내릴 수 있게 됩니다. 따라서 오버헤드에 의한 성능 문제가 발생합니다.

- VMware 워크스테이션 (32bit guest OS)
- Virtual PC
- Virtual Bow (32bit guest OS)
- VMware 서버

Hardware-Assisted - Full Virtualization (VT)
<figure>
  <img src="https://github.com/lee20h/blog/assets/59367782/b7838ee0-79bd-47da-877d-4e0ba8e38db4" alt="샘플 이미지" width="400">
</figure>

[Hardware Virtualization]

하드웨어 자원 가상화는 Binary Translation을 제거하고 가상화하여 직접 하드웨어와 통신할 수 있게 합니다. 그를 이용해, 유저 애플리케이션과 Guset OS에서 trap과 emulate를 이용하여 **privilged command**를 실행할 수 있게 됩니다.

## 반가상화 (Para Virtulization)
전가상화의 경우 가상화 단계에서 오버헤드가 발생하여 성능 저하가 발생합니다. 이 부분을 해결하기 위해 반가상화가 등장하게 되었습니다. 여기서의 핵심 키워드는 **Hyper Call** 입니다.

<figure>
  <img src="https://github.com/lee20h/blog/assets/59367782/4ef08ecc-f451-4328-a746-80d074d1e789" alt="샘플 이미지" width="400">
</figure>

[Para Visualization]

Guest OS에서 하이퍼바이저에게 직접 요청을 날리는 부분을 **Hyper Call** 이라는 인터페이스라고 하며, OS에서 애플리케이션이 커널에게 System Call을 호출하여 하드웨어를 사용하는 방법과 동일합니다. 요청하는 대상이 Guest OS, 요청받는 대상이 하이퍼바이저라는 점이 다릅니다. **또한, Guest OS가 하이퍼바이저에게 요청을 하려면 본인이 Guest OS임을 인지해야하므로**, 커널을 수정해서 Guest OS를 따로 제작해야 합니다.

그렇다보니, 반가상화에서는 모든 명령어를 가상화할 필요 없으며, 필요한 명령어만 가상화 할 수 있습니다. 이러한 부분 덕분에 전가상화에 비해 성능이 좋다고 할 수 있습니다. 여기서 필요한 명령어를 구분하기 위해서 커널의 수정이 필요하며, Guset OS가 하이퍼바이저에게 명령어를 가상화해달라고 하는 요청을 Hyper Call 이라고 합니다. Xen 하이퍼바이저가 이에 해당합니다.

           Hyper Call               System Call
[Guest OS] ----------> [HyperVisor] -----------> [Host OS]

<figure>
  <img src="https://user-images.githubusercontent.com/67403886/157030545-4f05f1b9-efb0-4730-9a95-87091180537f.png" alt="샘플 이미지" width="400">
</figure>
    
[Virtual CPU 아키텍쳐</figcaption>]

                                                                                                                              

<figure>
  <img src="https://hoststud.com/attachments/1614317912921-png.1341" alt="샘플 이미지" width="400">
</figure>

[Virtual CPU 아키텍쳐]

### Live Migration
가상머신은 서로 다른 물리 하드웨어에서 동작하는 하이퍼바이저 간에 실시간으로 이동할 수 있습니다. 이 떄, 서비스 장애나 접속의 끊김없이 마이그레이션이 이루어지는데,
이러한 기능을 라이브 마이그레이션이라고 합니다. 이러한 마법의 비밀은 원천지와 목적지 호스트 사이에 메모리를 다루는데 있습니다. 하이퍼바이저는 원천지에서 목적지로 
변경점을 복사하고 메모리가 두 부분에서 같아지는 시점에 마이그레이션이 완료됩니다. 이러한 기능 덕분에 라이브 마이그레이션은 Disaster Ricovery, 서버 유지 보수,
일반적인 시스템 유동성 등에 도움이 많이 됩니다.

<img width="533" height="341" alt="image" src="https://github.com/user-attachments/assets/b027fea2-226f-4145-bea5-8d56e0e57497" />

[KVM 내에서의 Live Migration]


### 가상 머신 이미지
가상 서버는 이미지에서 생성됩니다. 이미지는 하이퍼바이저가 load와 실행(execute)이 가능한 환경설정된 운영체제 템플릿 입니다. 이미지 파일 형식은 하이퍼바이저마다 
다릅니다. 대부분의 하이퍼바이저 프로젝트는 이미지의 모음을 관리하고 있어 우리가 다운로드하고 고유 커스텀 이미지를 우한 기반으로 사용할 수 있습니다. 또한, 이미지를 
만들거나 중요한 데이터를 백업하고자 더 많은 가상머신의 생성을 위한 기반 이미지로 사용할 때 가상머신의 스냅샷을 뜰 수 있습니다.
하이퍼바이저에 의해 표시되는 가상 머신 하드웨어는 표준화되어 있으므로 실제 하드웨어가 다르더라도 이미지는 시스템 간 이동성이 있습니다. 이미지는 특정 하이퍼바이저에
의존적이지만 하이퍼바이저 간 이미지를 Porting 시키는 변환도구가 있습니다.

### 컨테이너화
OS 수준 가상화(또는 컨테이너화)는 하이퍼바이저를 사용하지 않고 격리시키는 조금 다른 접근법입니다. 이는 시스템의 나머지 구성 요소와 프로세스를 격리시키는 커널 기능에 
의존합니다. 각 프로세스 컨테이너 또는 jail은 개인 루트 파일 시스템과 프로세스 네임스페이스를 갖습니다. 컨테이너 프로세스는 호스트 OS의 다른 서비스와 커널을 공유합니다.
그러나 그 컨테이너 밖의 파일이나 자원에 접근할 수 없습니다. 이것이 하드웨어 가상화를 필요로 하지 않기 때문에, 오버헤드는 굉장히 낮습니다. 대부분의 구현은 거의 네이티브와
같은 수준의 성능을 보여줍니다. 컨테이너는 **리눅스 커널이 제공하는 프로세스 격리 기술(namespace + cgroup) 을 조합해 만든 가벼운 가상 환경** 입니다.

즉, 별도의 커널이나 하이퍼바이저를 사용하는 게 아니라, 하나의 커널 위에서 여러 개의 격리된 유저 공간(user space) 을 만들어서 마치 독립된 시스템처럼 동작하게 하는것입니다.

🔹 1️⃣ Namespace — 논리적 분리
  Namespace는 프로세스가 볼 수 있는 자원 범위를 제한하는 커널 기능입니다.
  프로세스 입장에서 보이는 세상을 따로 만들어줍니다.
  
| Namespace 종류 | 격리 대상               | 예시                    |
| ------------ | ------------------- | --------------------- |
| **PID**      | 프로세스 ID 공간          | 각 컨테이너가 PID 1부터 시작    |
| **NET**      | 네트워크 인터페이스, 라우팅 테이블 | 각 컨테이너마다 독립된 eth0     |
| **IPC**      | 프로세스 간 통신 자원        | 세마포어, 메시지 큐 등 분리      |
| **UTS**      | 호스트명, 도메인명          | 컨테이너별 hostname 다름     |
| **MNT**      | 파일시스템 마운트 포인트       | 컨테이너별 rootfs 독립       |
| **USER**     | 사용자/그룹 ID           | 컨테이너 내 root ≠ 실제 root |

🔹 2️⃣ cgroup(Control Groups) — 물리적 제한
  cgroup은 프로세스가 사용할 수 있는 리소스(물리 자원)를 제한하는 기술입니다.
  
| 리소스       | 제한 예시                  |
| --------- | ---------------------- |
| CPU       | CPU time 비율 제한         |
| Memory    | 메모리 사용량 제한 (OOM 발생 가능) |
| Block I/O | 디스크 I/O 속도 제한          |
| Network   | 네트워크 대역폭 제한 (v2부터 지원)  |

🔹 3️⃣ 두 기술의 결합 → 컨테이너

```
+--------------------------------------------+
|        Linux Kernel (공유됨)               |
|--------------------------------------------|
| Namespace: 논리적 격리 (PID, NET, FS 등)   |
| cgroup: 자원 제한 (CPU, Memory 등)         |
|--------------------------------------------|
| Container A (PID 1: nginx)                 |
| Container B (PID 1: redis)                 |
+--------------------------------------------+

```
가상머신과 컨테이너를 헷갈리기 쉽습니다.두 가지 모두 유연성, 독립된 실행 환경을 정의하며 루트 파일 시스템과 프로세스 수행을 통해
완전 운영체제와 같이 보이고 동작하기 때문입니다. 물론 그 둘의 구현은 완전히 다릅니다. 가상 머신은 OS 커널, init 프로세스, 하드웨어와
통신을 위한 드라이버, 유닉스 운영체제의 모든 trap을 가집니다. 반면, 컨테이너는 운영체제의 겉모습일 뿐입니다. 

가상머신과 컨테이너를 결합해 사용하는 것은 매우 일반적인 유즈케이스 입니다. 가상 머신은 물리 서버를 관리 가능한 조각으로 나누는 가장 좋은 방법입니다.
그리고 나서 VM 위에 컨테이너로 애플리케이션을 구동할 수 있습니다. 이는 최적의 시스템 밀도를 달성하게 도와줍니다. 

### 리눅스 가상화
Xen과 KVM은 리눅스에서 오픈소스 가상화 프로젝트르르 선도하고 있습니다. Xen은 현재 리눅스 재단의 프로젝트이고, 가장 큰 공개 클라우드에서 활용됩니다.
여기에서는 아마존 웹 서비스와 IBM의 소프트레이어가 포함됩니다. KVM은 커널 기반 가상 머신으로 리눅스 커널 메인라인에 통합됐습니다. Xen과 KVM은 모두
대규모 사이트에 여러 제품 설치를 통해 그 안정성을 입증했습니다.                                                              

### 메모리 가상화(vMemory)
각 VM은 자신만의 **게스트 물리 메모리(guest physical memory)** 공간을 갖고 있다고 생각하지만, 실제로는 **호스트의 물리 메모리(Host RAM)**
에 맵핑됩니다. 하이퍼바이저는 VM 마다 **그림자 페이지 테이블**이나 EPT(Extended Page Tables)같은 기술로 게스트의 메모리 주소를 
호스트 메모리 주소에 대응시킵니다. 예를 들어 VMware ESXi는 게스트의 물리 메모리를 호스트 물리 메모리에 백업하여 관리합니다. 또한, ESXi는
메모리 **오버커밋(Overcommit)**을 지원하여, 전체 VM의 할당 메모리 합이 실제 물리 메모리보다 커질 수 있습니다. 이 경우, 중복된 메모리 페이지를
하나로 합쳐 사용하는 **TPS(Transpert Page Sharing)**나, 사용 중인 메모리를 호스트에 회수하는 **풍선 드라이버(Ballooing)**, 불필요한 메모리를 디스크로 옮기는 **Swap Out** 기법 등으로 자원을 효율화 합니다. 예를 들어 TPS는 중복된 메모리 페이지를 하나로 통합하여 물리 메모리를 절약합니다.


<figure>
  <img src="https://github.com/user-attachments/assets/19a5c8d4-5020-45a6-ba43-7750ed55cc64](https://github.com/user-attachments/assets/19a5c8d4-5020-45a6-ba43-7750ed55cc64" alt="이미지" width="400">
</figure>

[Virtual Memory]

<figure>
  <img src="https://github.com/user-attachments/assets/1ffdea09-3d9e-4866-9c3a-aa7ea12112f5" alt="이미지" width="400">
</figure>

[Virtual Memory Swap in/out]
                                            

<figure>
  <img src="https://www.vmwarearena.com/wp-content/uploads/2014/05/Memory-Ballooning-300x253.jpg" alt="샘플 이미지" width="400">
  <figcaption style="text-align:center;"></figcaption>
</figure>

[Virtual Memory Balloning]

                                                        
### GPU 가상화(VGPU, Virtual Graphic Card)


<figure>
  <img src="https://krutavshah.github.io/GPU_Virtualization-Wiki/assets/img/vgpu-overview.49e0b6b1.png" alt="샘플 이미지" width="400">
  <figcaption style="text-align:center;"></figcaption>
</figure>

[Virtual GPU]


### Storage 가상화(VSAN,Virtual Storage)


<figure>
  <img src="https://ik.imagekit.io/upgrad1/abroad-images/imageCompo/images/1_21VI6V7.png?pr-true" alt="샘플 이미지" width="400">
</figure>

[Virtual Storage]


                                                 

### 장치 가상화(Device Emulation)
가상 머신은 네트워크 카드, 디스크 컨트롤러 같은 가상 하드웨어 장치를 통해 I/O를 수행합니다. 하이퍼바이저는 이러한 가상 장치를 에뮬레이션
하거나, 성능 최적화를 위해 패러베추얼(paravirtualized) 드라이버(e.g VMXNET3 가상 NIC, PVSCSI 가상 SCSI 등)를 제공합니다.
결과적으로 VM 내부의 운영체제는 마치 실제 장치 드라이버를 다루는 것처럼 가상 장치를 사용할 수 있습니다. 이 모든 장치 가상화 레이어를 
통해 VM은 외부 세계(호스트 네트워크, 스토리지)와 투명하게 통신합니다.

### 스냅샷(Snapshot)
가상 머신 스냅샷은 VM의 **특정 시점 상태(PIT, point-in-time)**를 저장하는 기능입니다. **스냅샷은 VM의 모든 데이터와 상태(메모리, 디스크,
전원상태 등)를 캡처하여 백업이나 테스트용 롤백에 사용합니다.** 스냅샷이 생성되면 하이퍼바이저는 원본 가상 디스크 파일(A)의 쓰기 작업을
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

