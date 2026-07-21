---
title: "VMware_NAT"
date: "2026-07-16T13:46:00.000Z"
categories:
  - "vmware"
  - "type-2-hypervisor"
author: "현제 김_7254"
slug: "notionvmwarenatsshblognoaclbinaryembed"
---



# VMware NAT 환경에서 외부 Mac → Ubuntu VM SSH 접속 트러블슈팅

> 기준 시각: 2026-07-16 오후 1시

주제: VMware NAT 환경에서 Ubuntu VM SSH 접속이 실패한 원인을 계층별로 좁히고, 최종적으로 공유기 포트포워딩 없이 ngrok으로 외부 접속까지 구성한 과정

---

## 0. 문제 상황

Windows Host 위에 VMware로 Ubuntu VM을 올려두고, 외부 MacBook에서 Ubuntu VM으로 SSH 접속하고 싶었다. 처음 생각한 구조는 다음과 같았다.

```
MacBook / 외부 장비
        ↓
Windows Host 192.168.10.50
        ↓
VMware NAT / VMnet8
        ↓
Ubuntu VM
```

처음에는 단순히 "SSH 서버가 안 떠 있나?" 정도의 문제라고 생각했다. 하지만 실제로는 Ubuntu SSH 서버, VMware NAT, Windows VMnet8 Host Adapter, Windows 방화벽, MacBook의 네트워크 대역, 그리고 공유기 포트포워딩 대안까지 확인해야 했다.

이번 글은 설정 명령어를 나열하는 글이 아니라, 어떤 가설을 세우고 어떤 테스트로 원인을 좁혔는지를 중심으로 정리한다.

---

## 1. 목표 구조

최종적으로 만들고 싶었던 구조는 두 가지였다.

### 1차 목표: 같은 LAN에서 Host 포트포워딩으로 접속

```
MacBook
  ↓
Windows Host 192.168.10.50:2222
  ↓
VMware NAT Port Forwarding
  ↓
Ubuntu VM 192.168.253.128:22
```

이 방식은 Windows Host가 외부에서 접근 가능한 네트워크에 있어야 하고, MacBook이 Windows Host의 192.168.10.50:2222까지 도달할 수 있어야 한다.

### 2차 목표: 공유기 설정 없이 외부에서 접속

```
MacBook
  ↓
ngrok TCP Endpoint
  ↓
Ubuntu VM localhost:22
```

이 방식은 공유기 포트포워딩이 필요 없다. Ubuntu VM이 먼저 ngrok 서버로 outbound 연결을 만들고, 외부 MacBook은 ngrok이 제공한 TCP 주소로 접속한다.

---

## 2. 1차 가설: Ubuntu SSH 서버 문제인가?

가장 먼저 확인한 것은 Ubuntu 내부의 SSH 서버 상태였다. SSH 접속이 안 될 때 곧바로 네트워크부터 의심하면 범위가 너무 넓어진다. 그래서 먼저 "로컬에서 자기 자신에게 SSH가 되는가?"를 확인했다.

Ubuntu VM에서 다음을 확인했다.

```
hostname -I
sudo systemctl status ssh
sudo ss -lntp | grep ':22'
ssh localhost
```

ssh localhost가 성공했다는 것은 다음을 의미한다.

```
Ubuntu에 openssh-server가 설치되어 있음
sshd가 정상 실행 중임
22번 포트가 LISTEN 상태임
Ubuntu 사용자 계정 인증도 가능함
```

![image](/assets/image_a6a02cf3-77b8-4650-86d0-f02632fef8c6.png)

그림 1. Ubuntu VM 내부에서 SSH localhost 접속이 성공한 화면

이 시점에서 SSH 서버 자체는 정상이라고 판단했다. 따라서 문제는 Ubuntu 내부가 아니라, 외부에서 Ubuntu VM까지 들어오는 네트워크 경로에 있었다.

---

## 3. 2차 가설: Windows Host가 Ubuntu VM 대역으로 라우팅할 수 있는가?

당시 Ubuntu VM은 VMware NAT 대역에서 다음 IP를 받고 있었다.

```
Ubuntu VM: 192.168.175.128/24
```

Windows Host에서 Ubuntu VM으로 ping과 TCP 22번 포트 테스트를 수행했다.

```
ping 192.168.175.128
Test-NetConnection 192.168.175.128 -Port 22
```

결과는 실패였다.

![image](/assets/image_05653c69-69b5-49ea-8bf1-4fe326facf76.png)

그림 2. Windows Host에서 Ubuntu VM IP로 ping 및 TCP 22번 접근이 실패한 화면

여기서 중요한 부분은 단순히 ping이 실패했다는 사실이 아니라, 실패 메시지의 출처였다.

```
192.168.10.1의 응답: 대상 호스트에 연결할 수 없습니다.
```

Windows가 192.168.175.128로 가는 패킷을 VMware VMnet8 쪽으로 보내야 하는데, 실제로는 기본 게이트웨이인 192.168.10.1 쪽으로 보내고 있었다.

이 결과로 다음 가설을 세웠다.

> Windows 라우팅 테이블에 192.168.175.0/24로 가는 VMnet8 경로가 없거나, VMware NAT 설정과 Windows VMnet8 어댑터 대역이 서로 맞지 않는다.

---

## 4. 3차 가설: VMware NAT 설정과 Windows VMnet8 어댑터가 불일치하는가?

VMware Virtual Network Editor에서 VMnet8 설정을 확인했다.

```
VMnet8
Type   : NAT
Subnet : 192.168.175.0/24
```

![image](/assets/image_4e3e50d5-2a3e-4b26-bbfb-13aa319fdeff.png)

그림 3. VMware Virtual Network Editor에서 VMnet8이 192.168.175.0/24로 보이는 화면

NAT Settings에서도 Gateway IP는 다음과 같이 보였다.

```
Gateway IP: 192.168.175.2
```

![image](/assets/image_96cc7282-af32-46ad-a77d-2fad767cd423.png)

그림 4. VMware NAT Settings에서 Gateway IP 192.168.175.2를 확인한 화면

VMware 설정 화면만 보면 정상처럼 보였다. 하지만 Windows의 ipconfig와 네트워크 어댑터 정보를 확인하자 VMnet8 Host Adapter가 전혀 다른 대역에 있었다.

```
VMware Network Adapter VMnet8
IPv4 Address: 192.168.2.1/24
```

실제 상태를 정리하면 다음과 같았다.

```
VMware NAT Subnet      : 192.168.175.0/24
VMware NAT Gateway     : 192.168.175.2
Ubuntu VM              : 192.168.175.128
Windows VMnet8 Adapter : 192.168.2.1       ← 불일치
```

이것이 첫 번째 핵심 원인이었다.

---

## 5. Gateway는 살아있지만 Host Adapter는 해당 대역에 없었다

Ubuntu VM에서 직접 gateway와 host adapter를 각각 테스트했다.

```
ping 192.168.175.2
ping 192.168.175.1
```

결과는 다음과 같았다.

```
192.168.175.2 → 성공
192.168.175.1 → 실패
```

![image](/assets/image_e0e0315b-425a-4e89-87a6-171ca160b4f1.png)

그림 5. Ubuntu에서 NAT Gateway는 응답하지만 Host Adapter는 응답하지 않는 화면

여기서 192.168.175.1과 192.168.175.2의 역할을 구분하는 것이 중요했다.

```
192.168.175.1 = Windows Host Virtual Adapter가 보통 가져야 할 주소
192.168.175.2 = VMware NAT Gateway
192.168.175.128 = Ubuntu VM
```

Ubuntu가 192.168.175.2에 ping할 수 있다는 것은 VMware NAT Gateway 자체는 살아있다는 의미다. 하지만 192.168.175.1에 ping할 수 없다는 것은 Windows Host Adapter가 해당 NAT 대역에 정상적으로 붙어 있지 않다는 뜻이다.

즉, 이 문제는 Ubuntu SSH 서버 문제가 아니었고, Windows 방화벽 문제도 아니었다. 핵심은 VMware NAT 대역과 Windows VMnet8 Host Adapter 대역의 불일치였다.

---

## 6. 해결: VMnet8 재구성

VMware Virtual Network Editor에서 VMnet8을 재구성했다. 재구성 후 NAT 대역은 다음처럼 정리되었다.

```
VMnet8 Subnet : 192.168.253.0/24
Gateway IP   : 192.168.253.2
Host Adapter : 192.168.253.1
Ubuntu VM    : 192.168.253.128
```

![image](/assets/image_d63d3c84-6f32-48c5-96ba-2a7264154bfb.png)

그림 6. VMnet8 재구성 후 192.168.253.0/24 대역으로 정리된 화면

이후 Windows Host에서 Ubuntu VM의 22번 포트로 다시 테스트했다.

```
Test-NetConnection 192.168.253.128 -Port 22
```

결과는 성공이었다.

```
InterfaceAlias   : VMware Network Adapter VMnet8
SourceAddress    : 192.168.253.1
TcpTestSucceeded : True
```

![image](/assets/image_77968f9c-cb21-4ac9-ac0a-3c05a585929b.png)

그림 7. Windows에서 Ubuntu VM의 22번 포트 접근이 성공한 화면

이 시점에서 Windows Host → Ubuntu VM SSH는 정상화되었다.

```
ssh <ubuntu-user>@192.168.253.128
```

---

## 7. VMware NAT Port Forwarding 구성

다음 목표는 Windows Host의 LAN IP와 특정 포트를 통해 Ubuntu VM으로 들어가는 것이었다.

```
Windows Host 192.168.10.50:2222
        ↓
VMware NAT Port Forwarding
        ↓
Ubuntu VM 192.168.253.128:22
```

VMware NAT Settings에서 다음 포트포워딩을 추가했다.

```
Host Port            : 2222
Type                 : TCP
Virtual Machine IP   : 192.168.253.128
Virtual Machine Port : 22
Description          : Ubuntu SSH
```

Windows 방화벽에서도 2222/TCP를 허용했다.

```
New-NetFirewallRule `
  -DisplayName "Ubuntu SSH 2222" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 2222 `
  -Action Allow
```

Windows 자기 자신에서 다음 테스트가 성공했다.

```
Test-NetConnection 192.168.10.50 -Port 2222
```

```
ComputerName     : 192.168.10.50
RemoteAddress    : 192.168.10.50
RemotePort       : 2222
InterfaceAlias   : 이더넷
SourceAddress    : 192.168.10.50
TcpTestSucceeded : True
```

이 결과는 다음을 의미한다.

```
Windows Host의 2222 포트는 열려 있음
VMware NAT Port Forwarding은 동작함
Windows → Ubuntu VM 경로는 정상임
```

하지만 여기서 중요한 주의점이 있었다. Windows 자기 자신에서 성공했다는 것은 Windows 내부와 VMware NAT까지 정상이라는 의미이지, 다른 장비가 Windows Host까지 도달할 수 있다는 뜻은 아니다.

---

## 8. MacBook에서 접근 실패: 원인은 다른 서브넷

MacBook에서 Windows Host로 ping을 수행했다.

```
ping 192.168.10.50
```

결과는 실패였다. MacBook의 IP를 확인해보니 다음과 같았다.

```
MacBook : 192.168.20.22
Windows : 192.168.10.50
```

즉 두 장비는 서로 다른 네트워크에 있었다.

```
MacBook  → 192.168.20.0/24
Windows  → 192.168.10.0/24
```

이 상태에서 MacBook이 192.168.10.50:2222로 접속하려면 두 대역 사이에 라우팅이 가능해야 한다. 하지만 게스트 Wi-Fi, AP Isolation, VLAN 분리, 이중 공유기 구성 같은 환경에서는 같은 공간에 있어도 서로 통신하지 못한다.

이 단계에서 두 번째 핵심 원인이 정리되었다.

> VMware NAT 포트포워딩은 정상이다. 하지만 MacBook이 Windows Host까지 도달하지 못하므로 192.168.10.50:2222 방식은 사용할 수 없다.

---

## 9. 공유기 포트포워딩 없이 외부에서 접근하기: ngrok

공유기 포트포워딩을 설정할 수 없다면, 외부에서 내부로 직접 들어오는 구조는 어렵다. 이럴 때는 내부 장비가 먼저 외부 중계 서버로 연결을 만들고, 외부 사용자는 그 중계 주소로 접속하는 방식이 필요하다.

그래서 Ubuntu VM에 ngrok을 설치하고 TCP 터널을 열었다.

Ubuntu VM에서:

```
ngrok tcp 22
```

ngrok은 다음과 같은 TCP endpoint를 제공한다.

```
Forwarding tcp://0.tcp.ngrok.io:<port> -> localhost:22
```

MacBook에서는 다음 형태로 접속한다.

```
ssh -p <ngrok-port> <ubuntu-user>@0.tcp.ngrok.io
```

여기서 <ubuntu-user>는 ngrok 계정이 아니라 Ubuntu VM의 사용자 계정이다. 비밀번호 역시 ngrok 비밀번호가 아니라 Ubuntu 사용자 계정의 로그인 비밀번호다.

Ubuntu에서 현재 사용자 이름은 다음으로 확인한다.

```
whoami
```

예를 들어 Ubuntu에서 whoami 결과가 hyunjae라면 MacBook에서는 다음처럼 접속한다.

```
ssh -p <ngrok-port> hyunjae@0.tcp.ngrok.io
```

비밀번호를 잊었다면 기존 비밀번호를 확인할 수는 없고, Ubuntu VM에서 새 비밀번호로 변경해야 한다.

```
passwd
```

또는 특정 사용자에 대해:

```
sudo passwd <ubuntu-user>
```

---

## 10. 최종 구조 정리

최종적으로 가능한 접근 방식은 두 가지로 정리된다.

### 같은 LAN에서 접근 가능한 경우

```
MacBook
  ↓
Windows Host 192.168.10.50:2222
  ↓
VMware NAT Port Forwarding
  ↓
Ubuntu VM 192.168.253.128:22
```

이 방식은 MacBook이 Windows Host까지 ping 또는 TCP 연결이 가능해야 한다.

확인 명령은 다음과 같다.

```
ping 192.168.10.50
nc -vz 192.168.10.50 2222
ssh -p 2222 <ubuntu-user>@192.168.10.50
```

### 공유기 설정 없이 외부에서 접근하는 경우

```
MacBook
  ↓
ngrok TCP Endpoint
  ↓
Ubuntu VM localhost:22
```

이 방식은 공유기 포트포워딩이 필요 없다. Ubuntu VM이 outbound로 ngrok에 연결하기 때문에 NAT 뒤에 있어도 외부에서 SSH 접근이 가능하다.

접속 형식은 다음과 같다.

```
ssh -p <ngrok-port> <ubuntu-user>@<ngrok-host>
```

---

## 11. 이번 트러블슈팅에서 얻은 교훈

이번 문제는 겉으로는 단순한 SSH 장애처럼 보였다. 하지만 실제 원인은 하나가 아니었다.

```
1. Ubuntu SSH 서버는 정상이었다.
2. Windows Host가 Ubuntu VM 대역으로 라우팅하지 못했다.
3. 원인은 VMware NAT 설정과 Windows VMnet8 Host Adapter 대역 불일치였다.
4. VMnet8 재구성 후 Windows → Ubuntu SSH는 정상화되었다.
5. VMware NAT Port Forwarding도 정상 동작했다.
6. 그러나 MacBook은 Windows와 다른 서브넷에 있어 Windows Host까지 도달하지 못했다.
7. 공유기 설정 없이 외부에서 접근하기 위해 ngrok TCP 터널을 사용했다.
```

이 과정에서 가장 중요했던 것은 "SSH가 안 된다"라는 증상에만 묶이지 않는 것이었다.

```
Application  : ssh localhost 성공 여부
Transport    : 22/TCP LISTEN, Test-NetConnection
Network      : IP 대역, Gateway, route
Virtualization: VMnet8, NAT Gateway, Host Adapter
Host OS      : Windows 방화벽, 포트포워딩
External Path: MacBook과 Windows의 서브넷, 외부 접근 대안
```

결국 핵심 질문은 하나였다.

> 지금 이 패킷은 실제로 어느 인터페이스를 통해 어디로 가고 있는가?

Windows가 192.168.175.128로 가는 패킷을 VMnet8이 아니라 기본 게이트웨이 192.168.10.1로 보내고 있었다는 사실이 원인 추적의 결정적인 단서였다. 이후 VMnet8 대역을 정리하고, Host → VM 경로를 복구한 뒤, 외부 접근은 ngrok으로 분리해 해결했다.

---

## 12. 최종 체크리스트

### Ubuntu VM

```
hostname -I
ip route
sudo systemctl status ssh
sudo ss -lntp | grep ':22'
ssh localhost
whoami
```

### Windows Host

```
ipconfig
route print
Get-NetIPAddress -InterfaceAlias "VMware Network Adapter VMnet8"
Test-NetConnection 192.168.253.128 -Port 22
Test-NetConnection 192.168.10.50 -Port 2222
```

### MacBook

```
ifconfig | grep "inet "
ping 192.168.10.50
nc -vz 192.168.10.50 2222
ssh -p 2222 <ubuntu-user>@192.168.10.50
```

### ngrok 사용 시

```
ngrok tcp 22
ssh -p <ngrok-port> <ubuntu-user>@<ngrok-host>
```

---

## 마무리

이번 트러블슈팅은 SSH 설정 하나의 문제가 아니었다. Ubuntu 내부에서는 SSH가 정상 동작했지만, Windows Host가 VMnet8 NAT 대역을 제대로 바라보지 못했고, 이후에는 MacBook과 Windows가 서로 다른 네트워크에 있어 Host 포트포워딩 방식도 사용할 수 없었다.

최종적으로는 문제를 두 단계로 나누어 해결했다.

```
1단계: VMware NAT / VMnet8 불일치 해결 → Windows Host에서 Ubuntu VM SSH 가능
2단계: 공유기 포트포워딩 한계 우회 → ngrok TCP 터널로 외부 MacBook에서 SSH 가능
```

네트워크 트러블슈팅에서 중요한 것은 특정 명령어 하나가 아니라, 패킷의 실제 이동 경로를 계층별로 확인하는 습관이다. 이번 문제도 그 순서대로 확인했기 때문에 원인을 놓치지 않고 좁혀갈 수 있었다.
