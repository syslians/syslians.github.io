---
layout: post
title: "VirtualSwitch(VMware)"
date: 2025-07-27 22:00:00 +0900
categories: [VMware, 서버가상화, vCenter, vSphere, Bare metal, Virtualization, Switch, VirtualSwitch, Network, SDN, Private Cloud, SDDC]
author: cotes
published: true
---

### Virtual Switch
가상 스위치(Virtual Switch)란 가상 네트워크(Virtual Network)에서 VM을 위해서 제공되는 스위치를 의미합니다. 이 스위치는 Host OS
에서 소프트웨적으로 제공하기 때문에 가상 스위치라고 부릅니다. VMware ESXi는 VM과 물리 네트워크 간 트래픽을 연결하기 위해 Virtual Switch
라는 핵심 네트워킹 컴포넌트를 제공합니다. Virtual Switch는 ESXi 호스트 내에서 동작하는 소프트웨어 기반 L2 스위치입니다.
역할은 물리 스위치와 비슷하지만, 네트워크 포트는 물리적 인터페이스 대신 가상 NIC(vNIC) 또는 업링크(NIC Team)에 연결됩니다.

<img width="1197" height="671" alt="Vis" src="https://github.com/user-attachments/assets/3ddab70c-2bc5-46e8-affb-2342b23ac753" />
[그림 1: VM의 Virtual NIC와 Virtual Switch 간의 연결]


<img width="583" height="489" alt="VirtualSwitchConcept" src="https://github.com/user-attachments/assets/c84b3c7d-eb72-4070-9723-2428e1d8d27c" />
[그림 1-2: Virtual Switch의 Port 와 Uplink Port 연결]

### Virtual Switch의 종류
VMware에서 제공하는 Virtual Switch에는 두 가지 종류가 있습니다.
| 구분 |표준 스위치(vSS)   | 분산 스위치(vDS)   |  
|---|---|---|
| 관리 범위  | 개별 ESXi 호스트 단위   | vCenter 단위(클러스터 전체)   |  
| 정책 적용 | 호스트별 수동 구성 | 중앙 집중형 정책 관리   |  
| 사용 편의성 | 소규모 환경 적합 | 대규모/엔터프라이즈 환경 적합 |
| 고급 기능 | 제한적 | NetFlow, Port Mirroring, NIOC 등 지원 |




<img width="481" height="631" alt="VirtualSwitch_to_Physical_Network" src="https://github.com/user-attachments/assets/35207c05-2b7c-4485-9b63-44809ed693f6" />

[그림 2: VM -> Virtual Switch -> Physical Switch -> Network ]

vSphere Standard Switch(vSS)와 vSphere Distributed Switch(vDS)는 vSphere 환경에서 가상 머신, 다양한 네트워크 및 워크로드 간에 네트워크
연결을 제공하는 두 가지 유형의 가상 스위치입니다. 두 스위치는 동시에 사용할 수 있지만, 동일한 네트워크 또는 포트 그룹에서는 사용할 수 없습니다. 
이는 일부 네트워크에는 중앙 집중식 관리를, 다른 네트워크에는 분산식 관리를 적용할 수 있음을 의미합니다.

두 스위치는 모두 이더넷 Layer 2 스위치와 유사하게 **업링크** 와 **포트 그룹** 이라는 공통 기능을 가지고 있습니다. 또한, 두 스위치 모두
레이어 2 트래픽 처리, 가상 LAN, 세분화, 801.1Q 태깅, NIC 티밍 및 아웃바운드 트래픽 쉐이핑을 지원합니다.

### vSphere Standard Switch (vSS)
- 기본 설정 및 가용성: ESXi 하이퍼바이저를 처음 설치할 때에 기본 네트워크 설정으로 제공되며, ESXi 설치시 무료로 제공됩니다. 각 ESXi 호스트에 여러개의
- vSS를 생성할 수 있습니다.

- 기능: vSS는 호스트 및 VM에 네트우크 연결을 제공하고, vmKernel 트래픽을 처리하며 물리적 하드웨어 스위치를 에뮬레이션 합니다. 주요 기능으로는 Teaming 및 failover
- 가 있습니다. 하드웨어 문제가 발생하여 물리적 NIC가 실패하면, ESXi는 vSS를 사용하여 호스트의 다른 대기 NIC로 자동으로 Failover 합니다. 또한, outbound traffic sharing
- , NIC Teaming 및 다양한 보안 정책과 같은 고급 기능도 지원합니다. 각 표준 그룹은 현재 호스트에 고유한 네트워크 레이블 식별을 사용해야 하며, 다른 호스트에 포트 그룹을 생성할
- 경우 동일한 레이블을 사용해야 합니다.

### vSphere Ditributed Switch (vDS)
- 설치 요구사항: vDS를 설치하려면 vSphere Enterprise Plus 라이센스가 필요합니다.

- 구성 및 관리: vDS는 vCenter Server를 통해 생성하고 구성해야 합니다. vDS는 데이터센터 수준에서 한 번만 생성하면 되며, 변경 사항도 한 번의 재구성을 통해 적용됩니다.
- 이는 vSS보다 훨씬 간단하고 효율적입니다. VMware는 vDS에서 control plane을 data plane과 분리했습니다. data plane은 packet switching, Filtering, Vlan tagging과 같은
- 작업을 수행하고, control plane은 vCenter Server에서 데이터만 제어합니다. vDS는 vSS에 없는 다음과 같은 추가 기능을 제공합니다.

- Network I/O Control: 가상 네트워크에서 네트워크 리소스 풀을 사용하여 리소스 풀에 대한 제한 및 공유를 생성할 수 있습니다. 이는 트래픽 유형에 따라 네트워크 트래픽을
  특정 리소스 풀로 전달합니다.

- SR_IOV support: 낮은 지연 시간과 높은 I/O 워크로드를 네트워크에서 실행할 수 있도록 합니다.

= Load-based Teming: 네트워크 워크로드를 관리하고 로드 기반 티밍을 통해 물리적 업링크를 선택합니다. 이는 NIC 팀 내에서 트래픽을 분산하는 로드밸런싱 정책을 결정합니다.

vSS와 vDS는 vSphere 및 ESXi 네트워킹의 핵심입니다. vSS는 단일 ESxi 호스트에서 사용할 수 있으며, 소규모 환경에 적합한 반면, vDS는 더 큰 데이터센터에 가장
적합하며 중앙 집중식 관리와 고급 네트워킹 기능을 제공합니다. 


<img width="1376" height="547" alt="image" src="https://github.com/user-attachments/assets/4febc4be-2fa5-4694-b580-69e2e0c9ebc1" />
