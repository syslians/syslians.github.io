---
title: "VMware Workstation Pro에서 Ubuntu 설치하기: 설치 옵션 분석부터 DHCP 장애 해결까지"
date: "2026-07-14T02:48:05.356Z"
categories:
  - "os"
  - "linux"
  - "ubuntu"
author: "현제 김_7254"
slug: "vmware_workstation_pro에서_ubuntu_설치하기_설치_옵션_분석부터_dhcp_장애_해결까지"
---

# VMware Workstation Pro에서 Ubuntu 설치하기: 설치 옵션 분석부터 DHCP 장애 해결까지

## 들어가며

VMware Workstation Pro에 Ubuntu를 설치하는 과정에서 다음과 같은 문제를 연속으로 경험했다.

1. Ubuntu 설치 과정에서 Erase disk and install Ubuntu와 Manual installation의 차이가 명확하지 않았다.

1. 수동 파티션 설정 화면에서 EFI 파티션 옵션이 보이지 않았다.

1. 설치 후 Use Wired Connection이 정상적으로 활성화되지 않았다.

1. ens33 인터페이스는 존재했지만 IPv4 주소를 받지 못했다.

1. VMware의 가상 네트워크를 초기화한 뒤 네트워크가 복구되었다.

1. 이후 Windows C 드라이브가 가득 차면서 VMware 가상머신이 종료되는 문제도 발생했다.

이 글에서는 단순히 해결 명령만 나열하지 않고, Ubuntu 설치 옵션과 VMware 가상 하드웨어 구조를 함께 살펴보면서 각 문제의 원인을 단계적으로 좁혀간 과정을 정리하는 글이다.

## 1. 실습 환경

### 호스트 환경

- Host OS: Windows

- Hypervisor: VMware Workstation Pro

- 가상머신 저장 위치: 초기에는 Windows C 드라이브

- 네트워크 방식: VMware NAT

- 가상 네트워크: VMnet8

### Ubuntu 가상머신 환경

- Guest OS: Ubuntu Desktop

- 메모리: 4GB

- 프로세서: 2 vCPU

- 가상 디스크: 30GB SCSI

- 가상 NIC: Intel 82545EM Gigabit Ethernet Controller

- Linux 인터페이스 이름: ens33

그림 1. 가상머신의 네트워크 어댑터는 NAT로 설정되어 있었고 Connected 및 Connect at power on도 활성화되어 있었다.

!/assets/image_1940f7f6-92ec-4e7e-ba84-84fe0ce94df6.png

## 2. Ubuntu 설치 옵션 이해하기

### 2.1 VMware의 가상 디스크와 Windows 실제 디스크

VMware에서 Ubuntu 가상머신에 30GB 디스크를 추가하면 Ubuntu는 이를 실제 디스크처럼 인식한다. 하지만 그 실체는 Windows 파일시스템에 저장된 .vmdk 파일이다.

```
Windows C 드라이브
└── Virtual Machines
    └── Ubuntu
        ├── Ubuntu.vmx
        ├── Ubuntu.vmdk
        ├── Ubuntu.nvram
        └── vmware.log
```

```
Ubuntu 파일 쓰기
        ↓
Ubuntu 파일시스템
        ↓
가상 디스크 /dev/sda
        ↓
VMware 가상 디스크 계층
        ↓
Windows의 Ubuntu.vmdk
        ↓
Windows C 또는 D 드라이브
```

### 2.2 Erase disk and install Ubuntu

Erase disk and install Ubuntu는 현재 가상머신에 연결된 가상 디스크 내부의 파티션을 초기화하고 Ubuntu에 필요한 파티션을 자동으로 만든다.

> 여기서 지워지는 대상은 Windows의 C 드라이브 전체가 아니라, 해당 VM에 연결된 VMDK 가상 디스크 내부다.

설치 프로그램은 대략 다음 작업을 수행한다.

1. 가상 디스크 내부의 기존 파티션 테이블 확인

1. 기존 파티션 삭제

1. 새 파티션 테이블 생성

1. 루트 파일시스템 생성

1. 부트로더 설치

1. Ubuntu 시스템 파일 복사

### 2.3 Manual installation

Manual installation은 파티션을 직접 설계하는 방식이다. 다음과 같은 요구가 있을 때 적합하다.

- /와 /home 분리

- LVM 직접 구성

- 디스크 암호화

- 여러 개의 가상 디스크 사용

- 기존 데이터 파티션 유지

```
/dev/sda
├── /boot/efi   512MB    FAT32
├── /           25GB     ext4
└── /home       나머지    ext4
```

## 3. EFI 파티션이 보이지 않았던 이유

수동 설치 화면에서 EFI 파티션 옵션이 보이지 않았던 이유는 가상머신이 UEFI가 아니라 Legacy BIOS 모드로 부팅되었기 때문이다.

### 3.1 UEFI 모드

```
파일시스템: FAT32
크기: 약 512MB
마운트 지점: /boot/efi
플래그: ESP 또는 boot
```

```
UEFI Firmware
      ↓
EFI System Partition
      ↓
GRUB EFI 실행 파일
      ↓
Linux Kernel
      ↓
Ubuntu 부팅
```

### 3.2 Legacy BIOS 모드

Legacy BIOS 모드에서는 EFI System Partition을 사용하지 않는다.

```
Legacy BIOS
      ↓
MBR 또는 BIOS 부트 영역
      ↓
GRUB
      ↓
Linux Kernel
```

### 3.3 부팅 모드 확인

```
if [ -d /sys/firmware/efi ]; then
    echo "UEFI mode"
else
    echo "Legacy BIOS mode"
fi
```

## 4. 주요 파티션과 설치 옵션

### 4.1 루트 파티션 /

루트 파티션은 Ubuntu 파일시스템의 기준점이다. 별도 파티션을 만들지 않으면 /var, /home, /opt 등도 모두 루트 디스크를 사용한다.

Docker나 Kubernetes 실습 시 다음 경로가 빠르게 커질 수 있다.

```
/var/log
/var/lib/docker
/var/lib/containerd
/var/lib/kubelet
/home
```

### 4.2 /home

사용자 파일을 저장한다. 별도 파티션으로 분리하면 OS 재설치 시 사용자 데이터를 유지하기 쉽다.

### 4.3 /boot

Linux 커널, initramfs, GRUB 관련 파일이 저장된다. 일반적인 Desktop 설치에서는 별도 파티션이 필수는 아니다.

### 4.4 /boot/efi

UEFI 부팅에서 EFI System Partition을 마운트하는 위치다. Legacy BIOS 환경에서는 사용하지 않는다.

### 4.5 Swap

RAM이 부족할 때 메모리 페이지를 디스크로 이동시키는 공간이다. 현대 Ubuntu에서는 별도 파티션 대신 /swapfile을 사용하는 경우도 많다.

### 4.6 LVM

```
가상 디스크
    ↓
Physical Volume
    ↓
Volume Group
    ↓
Logical Volume
    ↓
ext4 파일시스템
```

LVM은 볼륨 확장과 공간 관리가 유연하지만 일반 파티션보다 구조가 복잡하다.

## 5. Use Active Directory 옵션

Use Active Directory는 Ubuntu를 Microsoft Active Directory 도메인에 가입시키는 기업용 기능이다.

```
Ubuntu
   ↓
Active Directory Domain
   ↓
도메인 사용자 인증
   ↓
Kerberos / LDAP / 정책 적용
```

개인 실습 환경에서는 일반적으로 선택하지 않는다. 정상적인 도메인 가입을 위해서는 DNS, 시간 동기화, Domain Controller 접근성, 도메인 가입 권한이 필요하다.

## 6. 설치 후 발생한 네트워크 문제

Ubuntu 설치 후 Use Wired Connection이 정상적으로 동작하지 않았다. 우선 인터페이스 상태를 확인했다.

```
ip link
```

그림 2. ens33 인터페이스가 생성되어 있고 UP, LOWER_UP 상태였다.

!/assets/image_1940f7f6-92ec-4e7e-ba84-84fe0ce94df6.png

핵심 출력은 다음과 같다.

```
ens33: <BROADCAST,MULTICAST,UP,LOWER_UP>
```

- UP: 운영체제가 인터페이스를 활성화함

- LOWER_UP: 하위 링크 계층이 연결됨

- BROADCAST: 브로드캐스트 처리 가능

- MULTICAST: 멀티캐스트 지원

따라서 NIC가 존재하지 않거나 가상 케이블이 끊긴 문제는 우선 배제할 수 있었다.

## 7. PCI 장치와 가상 NIC 확인

```
lspci
```

그림 3. VMware가 에뮬레이션한 Intel 82545EM Gigabit Ethernet Controller가 보인다.

!/assets/image_1940f7f6-92ec-4e7e-ba84-84fe0ce94df6.png

```
Ethernet controller:
Intel Corporation 82545EM Gigabit Ethernet Controller
```

실제 Intel NIC가 장착된 것이 아니라 VMware가 Intel e1000 계열처럼 동작하는 가상 PCI 장치를 제공한 것이다.

```
Ubuntu
   ↓
Linux e1000 드라이버
   ↓
가상 Intel 82545EM PCI 장치
   ↓
VMware 가상 스위치
   ↓
VMnet8 NAT
   ↓
Windows 네트워크
```

## 8. IPv4 주소가 없다는 사실 확인

```
ip addr
```

그림 4. ens33에는 IPv6 링크 로컬 주소만 있고 IPv4 주소가 없었다.

!/assets/image_1940f7f6-92ec-4e7e-ba84-84fe0ce94df6.png

ens33에는 다음과 같은 IPv6 링크 로컬 주소만 존재했다.

```
inet6 fe80::20c:29ff:fe52:36a4/64
```

하지만 일반적인 VMware NAT 환경에서 기대하는 IPv4 주소는 없었다.

```
inet 192.168.x.x/24
```

즉, 인터페이스와 링크는 살아 있었지만 DHCP를 통한 IPv4 설정이 실패한 상태였다.

## 9. NetworkManager 상태 확인

```
systemctl status NetworkManager
```

그림 5. NetworkManager는 실행 중이었지만 DHCP lease를 받지 못했다.

!/assets/image_1940f7f6-92ec-4e7e-ba84-84fe0ce94df6.png

서비스 상태는 active (running)이었고, 로그에는 다음 메시지가 나타났다.

```
dhcp4 (ens33): activation: beginning transaction
dhcp4 (ens33): state changed no lease
```

no lease는 DHCP 서버에서 IPv4 임대 정보를 받지 못했다는 의미다.

```
Ubuntu                 DHCP Server
  │                         │
  │──── DHCPDISCOVER ──────>│
  │<──── DHCPOFFER ─────────│
  │──── DHCPREQUEST ───────>│
  │<──── DHCPACK ───────────│
  │                         │
  └─ IPv4 주소 설정
```

## 10. VMware NAT 설정과 구조

VM 설정 화면에서는 Connected, Connect at power on, NAT가 모두 정상으로 보였다.

```
Ubuntu ens33
      ↓
가상 NIC
      ↓
VMware 가상 스위치 VMnet8
      ↓
VMware NAT Service
      ↓
Windows Host 네트워크
      ↓
공유기 또는 인터넷
```

VMware NAT 환경에서는 VMware DHCP Service가 VMnet8의 게스트에게 사설 IPv4 주소를 할당한다.

## 11. NAT, Bridged, Host-only, Custom 비교

### Bridged

```
Ubuntu
   ↓
VMnet0 Bridge
   ↓
Host의 Wi-Fi 또는 Ethernet NIC
   ↓
실제 공유기
```

실제 공유기나 사내 DHCP 서버에서 주소를 받는다.

### NAT

```
Ubuntu 사설 IP
   ↓
VMware NAT
   ↓
Windows Host IP
   ↓
외부 네트워크
```

개인 실습에서 가장 편리하다.

### Host-only

```
Windows Host ↔ Ubuntu VM
```

외부 인터넷 없이 Host와 VM 사이의 사설망을 만든다.

### Custom

가상머신에서 물리 NIC를 직접 고르는 것이 아니라 특정 VMnet을 선택한다. Custom: VMnet8을 선택해도 VMnet8 자체가 깨졌다면 문제가 해결되지 않는다.

## 12. 원인을 좁힌 과정

```
PCI 가상 NIC 인식       정상
Linux 드라이버          정상
ens33 인터페이스 생성   정상
인터페이스 UP           정상
LOWER_UP                정상
NetworkManager          정상
DHCP 시작               정상
IPv4 Lease              실패
```

따라서 문제 범위를 다음 구간으로 좁혔다.

```
ens33
  ↓
VMware 가상 스위치
  ↓
VMnet8
  ↓
VMware DHCP/NAT
```

## 13. Windows 서비스와 Virtual Network Editor 확인

Windows의 services.msc에서 다음 서비스를 확인했다.

```
VMware DHCP Service
VMware NAT Service
```

서비스는 실행 중이었지만, 서비스가 실행 중이라는 사실만으로 VMnet 설정 전체가 정상이라고 단정할 수는 없다.

## 14. 최종 해결: Restore Defaults

VMware Workstation Pro에서 다음 작업을 수행했다.

```
Edit
→ Virtual Network Editor
→ Restore Defaults
```

이 작업은 VMnet0, VMnet1, VMnet8, DHCP 범위, NAT 설정, Host 가상 어댑터 연결 관계를 기본 상태로 재구성한다.

복구 후 Ubuntu의 네트워크 연결이 정상화되었다.

> 정확히 어떤 설정 파일 하나가 손상되었는지는 추가 로그 분석 없이는 확정할 수 없지만, Guest OS가 아니라 VMware VMnet8의 DHCP/NAT 계층에 문제가 있었던 것으로 범위를 좁힐 수 있었다.

## 15. 복구 후 검증

### IPv4 주소

```
ip -4 addr show dev ens33
```

### 기본 경로

```
ip route
```

### NetworkManager

```
nmcli device status
```

### DNS

```
resolvectl status ens33
```

### 외부 통신

```
ping -c 4 8.8.8.8
getent hosts google.com
```

## 16. “인터넷은 되는데 IPv4가 없다”는 현상

복구 전에 촬영한 ip addr 화면에는 IPv4가 없었다. 복구 후에는 반드시 다시 확인해야 한다.

```
ip -4 addr show ens33
ip route
nmcli device show ens33
```

정말 IPv4 없이 인터넷이 된다면 IPv6 경로를 확인할 수 있다.

```
ip -6 route
ping -6 -c 4 google.com
```

## 17. 추가 문제: Windows C 드라이브 용량 부족

이후 Windows C 드라이브가 가득 차면서 VMware 가상머신이 종료되는 문제가 발생했다.

```
Ubuntu에서 파일 쓰기
        ↓
가상 디스크에 블록 쓰기
        ↓
Windows의 VMDK 파일 증가
        ↓
C 드라이브 여유 공간 없음
        ↓
가상 디스크 쓰기 실패
        ↓
VM 일시중지 또는 종료
```

Thin Provisioning 방식에서는 VMDK가 사용량에 따라 증가하므로 Host 디스크의 실제 여유 공간이 반드시 필요하다.

## 18. 가상머신을 D 드라이브로 이동

1. Ubuntu 완전 종료

1. VMware Workstation Pro 종료

1. VM 폴더 전체를 D 드라이브로 복사

1. D 드라이브의 .vmx 파일 열기

1. 질문이 나오면 I moved it 선택

1. 부팅, 네트워크, 파일 정상 여부 검증

1. 정상 확인 후 C 드라이브 원본 삭제

```
기존:
C:\Users\사용자\Documents\Virtual Machines\Ubuntu

이동:
D:\VMs\Ubuntu
```

.vmdk만 이동하면 안 된다. 스냅샷과 설정 파일을 포함한 폴더 전체를 이동해야 한다.

## 19. Ubuntu 로그인 사용자 이름을 잊어버린 경우

설치 시 입력한 Your name, Computer name, Username은 서로 다를 수 있다. 실제 로그인 계정은 Username이다.

Recovery Mode의 root shell에서 다음 명령으로 확인할 수 있다.

```
ls /home
getent passwd | grep '/home'
```

## 20. 트러블슈팅에서 배운 점

- UP, LOWER_UP은 IP와 인터넷 연결 성공을 의미하지 않는다.

- fe80::/64 IPv6 링크 로컬 주소는 IPv4 DHCP 성공을 의미하지 않는다.

- no lease는 DHCP 경로를 의심하게 하는 강력한 단서다.

- 가상머신 장애는 Guest OS, Hypervisor, Host OS를 분리해서 봐야 한다.

- Guest 디스크 여유 공간과 Host의 실제 디스크 여유 공간은 별도로 확인해야 한다.

## 21. 최종 체크리스트

```
lspci | grep -i ethernet
ip link
ip addr
ip route
systemctl status NetworkManager --no-pager
nmcli device status
journalctl -u NetworkManager -b --no-pager
sudo tcpdump -ni ens33 'udp port 67 or udp port 68'
```

VMware 측에서는 다음을 확인한다.

- Connected

- Connect at power on

- NAT 또는 의도한 네트워크 모드

- VMware DHCP Service

- VMware NAT Service

- Virtual Network Editor의 VMnet8 설정

- 필요 시 Restore Defaults

## 마무리

```
Ubuntu NIC 인식             정상
Linux 드라이버              정상
ens33 링크                  정상
NetworkManager              정상
DHCP 시작                   정상
IPv4 Lease                  실패
VMware 네트워크 초기화 후   정상화
```

이번 문제는 Ubuntu 자체의 네트워크 드라이버 문제가 아니라 VMware Workstation Pro의 VMnet8 NAT/DHCP 구성 문제였다. Virtual Network Editor에서 기본값 복원을 수행한 뒤 네트워크가 복구되었다.

또한 가상머신 종료 문제는 Ubuntu의 가상 디스크 크기뿐 아니라 VMDK가 저장된 Windows C 드라이브의 실제 공간 부족과 관련되어 있었다. 가상머신 환경에서는 Guest와 Host의 네트워크 및 디스크 계층을 함께 확인해야 한다.