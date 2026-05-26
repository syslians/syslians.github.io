---
title: "Linux iptables"
date: "2026-05-26T06:55:56.868Z"
categories:
  - "os"
  - "linux"
  - "kernel"
  - "network"
author: "현제 김_7254"
slug: "linux_iptables"
---

## iptables

Iptables는 netfilter 프레임워크 기반의 패킷 처리 엔진을 관리하기 위한 커맨드라인 도구입입니다. iptable을 활용해 네트워크 트래픽을 규칙기반으로 필터링 및 NAT를 수행하는 리눅스 네트워크 스택입니다. NIC을 거쳐 유입되는 모든 네트워크 패킷은 Netfilter에 등록된 룰을 거쳐 제어됩니다. 예를 들어 iptables 테이블의 이름은 filter 입니다. 이 테이블에 있는 룰 체인들은 네트워크 트래픽을 패킷 필터링하는데 사용됩니다.

데비안과 우분투에서는 ufw라는 간단한 프론트엔드가 포함되어 있어 이를 이용해 일반적인 조작이나 환경설정이 가능합니다.

- 패킷이 NIC에 도착하면 네트워크 스택에서 유저 프로세스로 전달.

- 반대로 패킷이 유저 프로세스에서 생성되었으면 네트워크 스택으로 내려보내고 NIC으로 전달. 

- 패킷은 Routing roule에 따라 NIC으로 전달. 

이것은 커널레벨에서 이루어지는 일들입니다.


<iframe
  src="https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2F1Ql6J%2FbtrhjYd9GoS%2FAAAAAAAAAAAAAAAAAAAAAAbCdHSWZDUnO3aWNmQRDYHW76dTowdq-IKvnvQCfpdE%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1780239599%26allow_ip%3D%26allow_referer%3D%26signature%3DPlFvbt6rLXqWSdLqJ56VreAorfs%253D"
  width="100%"
  height="700"
  frameborder="0">
</iframe>


[그림 4: Netfilter의 플로우. 출처: https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2F1Ql6J%2FbtrhjYd9GoS%2FAAAAAAAAAAAAAAAAAAAAAAbCdHSWZDUnO3aWNmQRDYHW76dTowdq-IKvnvQCfpdE%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1780239599%26allow_ip%3D%26allow_referer%3D%26signature%3DPlFvbt6rLXqWSdLqJ56VreAorfs%253D]


<iframe
  src="https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FHFZZS%2FbtrhgkoDKj8%2FAAAAAAAAAAAAAAAAAAAAAKgj5M2GPoMxgFH5_CAZFfXkk0dDhRrkFbg66ESet56y%2Fimg.jpg%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1780239599%26allow_ip%3D%26allow_referer%3D%26signature%3D6UthPpt7m82ao5%252BpPVK55Tl6kMU%253D"
  width="100%"
  height="700"
  frameborder="0">
</iframe>


[그림1: iptable flow. 출처: https://jimmysong.io/en/blog/sidecar-injection-iptables-and-traffic-routing]

IP Packet이 유입된 이후에 아래처럼 L2, L3, L4 Header를 조작하거나, Header의 내용을 보면서 IP Packet을 다음 chain에서 처리하게 할지, 아니면 client (sender)로 되돌려 보낼지를 결정합니다.

위 그림에서 확인해 볼 수 있듯, 주황색 블록의 table은 Ip packet을 조작하고, filter와 같은 table에서는 Ip packet을 read만 할 수 있습니다.

!/assets/image_df00c8b3-1cfa-42ac-bf4f-06ac44cc366f.png

[그림1.  커널스택에서의 논리적인 패킷 처리 절차. 출처:  https://iximiuz.com/laymans-iptables-101/iptables-stages-white.png]

중간에 있는 라우팅 파트는 IP forwarding 으로 알려진 리눅스 커널의 기능입니다. 0이 아닌값을 /proc/sys/net/ipv4/ip_forward 파일로 보내면서 서로 다른 네트워크 인터페이스 간의 패킷이 전달되어 리눅스 머신을 가상라우터로 변환시킵니다.

네트워크 스택의 패킷 처리과정은 논리적인 과정이 더 추가가 됩니다. 예를 들어 PREROUTING 단계는 패킷 수집과 라우팅과정 사이 어딘가에 존재할것입니다. 다른 예시로 INPUT 단계에서는 유저 모드 프로세스 전에 존재할것입니다.

filter 체인은 기본 체인, FORWARD, INPUT, OUTPUT을 포함하고 있습니다. 커널에 의해 처리되는 각 패킷은 이 체인 중 하나를 통해 전달됩니다. 특정 조건에 부합하는 패킷의 수신, 송신, 포워딩을 제어 가능하며 방화벽 정책을 구성할 수 있는 다양한 옵션들이 존재합니다.

### iptables table

### iptables의 종류

- filter 

- 기본 테이블. 특정 룰에 따라 패킷을 허용(ACCEPT) 또는 차단(DROP)하는 패킷 필터링 역할을 담당 

- INPUT, OUTPUT, FORWARD와 같은 chain을 포함.

- 정책에 일치하는 패킷을 target에 전달하여 action을 수행

- target(ACTION)의 종류는 ACCEPT, REJECT, DROP, LOG, 사용자 정의 chain이 있음

- NAT

- NAT를 수행하는 테이블

- PREROUTING, POSTROUTING chain 포함

- 방화벽으로 향하는 패킷을 방화벽 내부 네트워크의 다른 주소로 포워딩하거나 방화벽 내부 네트워크에서 방화벽을 통해 외부 네트워크로 나갈때, IP, Port를 변환하는데 수행

- 정책에 일치하는 패킷의 주소를 변환하는 동작 수행

- target(ACTION)의 종류는 SNAT, DNAT, MASQUERADE, REDIRECT가 있음

- mangle

- 특정 유형의 패킷에 대해 정책에 일치하는 패킷의 IP Header의 필드 값을 다양한 방식으로 변경하는데 사용됨

- PREROUTING, OUTPUT 포함.

- 주로 데이터 전송 경로 변경, 우선순위 값 변경, QoS 적용. 패킷 마킹. MTU 조정 등의 패킷을 수정하여 네트워크 트래픽을 제어하는데 사용

- taraget의 종류에는 ACCEPT, DROP, MASK, TTL, TOS, TCPMSS, RETURN, LOG

- raw

- 패킷 필터링 외에도 네트워크 트래픽에 대한 특정 동작을 사전에 처리하는데 사용

- 이 테이블은 주로 패킷이 커널의 연결 추적 시스템(Connection Tracking)을 거치지 않도록 하여 연결 추적 우회 가능

- 기본적으로 Iptables은 filter 테이블 또는 nat 테이블에서 연결 추적이 이루어지지만, raw 테이블에서 이러한 연결 추적을 비활성화하여 패킷에 대한 연결 상태를 추적하는데 리소스가 소모되지 않도록 네트워크 성능 향상 가능

- raw 테이블에서 NOTTRACK 규칙을 사용하여 특정 트래픽에 대한 연결 추적을 비활성화 가능

- security

- SELinux와 같은 LSM과 연계하여 패킷에 보안 컨텍스트를 적용하는 역할을 담당

- SELinux가 활성화 된 RHEL 계열과 일부 SUSE Linux 계열에서 사용 가능

- SELinux가 기본 활성화된 배포판 (security 테이블 이용 가능)

- RHEL

- CentOS

- Rocky Lunux 

- Fedora

- SUSE Lunux

### iptables diagram

!/assets/image_df00c8b3-1cfa-42ac-bf4f-06ac44cc366f.png

[그림2. iptables의 다이어그램]

- 체인 조회 순서

1. 로컬 시스템으로 목적을 두는 패킷: PREROUTING → INPUT

1. 다른 시스템(호스트)로 목적을 두는 패킷: PREROUTING → FORWARD → POSTROUTING

1. 로컬 시스템에서 생성된 패킷: OUTPUT → POSTROUTING 

실제로 리눅스 네트워크 스택은 논리적 단계 분리를 제공합니다. 이제 기본 패킷 필터링, 수정 작업으로 돌아오겠습니다. a.out 프로세스로 도달하는 패킷들 중 일부를 drop 시키려면 어떻게 해야할까요?

예를 들어 한 소스 IP를 통해 대규모 요청이 들어온다고 하면 악성 사용자로 의심할 수 있습니다. 네트워크 스택에서 가장 좋은 후킹 방법은 INPUT 단계에서 들어오는 패킷에 대해 추가적인 로직을 적용해볼 수 있을것 같습니다. 아래 예제에서는 패킷의 소스 IP를 검사하여 수락할지 삭제할지 여부를 결정하는 기능을 만들어봅니다.

일반화하자면, 들어온 패킷에 대해 매 단계마다 실행할 콜백함수를 등록할 방법이 필요합니다. 다행히도 해당 기능을 제공하는 netfilter라는 프로젝트가 있으니, 이를 활용해봅니다. netfilter는 리눅스 커널에서 동작합니다. netfilter는 네트워크 스택의 다양한 단계에 hook이라고 불리는 확장 지점을 추가하여, 패킷이 해당 지점을 지날때마다 특정 로직이 실행될수 있도록 설계되었습니다. 확장 지점들은 위에서 설명한 PREROUTING, INPUT, FORWARD, OUTPUT, POSTROUTING 을 의미합니다.

사용자들은 특정 단계에 패킷이 도달했을때 실행될 규칙(Rule)을 등록할 수 있습니다.

패킷이 훅 지점에 도달하면, 등록된 콜백 함수들이 순차적으로 실행되며, 패킷을 통과시킬지, 버릴지, 수정할지를 결정합니다.

netfilter는 리눅스 커널 내부에서 실제로 패킷을 가로채고 처리하는 핵심 엔진입니다.  사용자가 사람이 읽기 쉬운 명령어로 규칙을 입력하면 이를 Netfilter가 이해할 수 있는 방식으로 커널에 전달해주는 도구들이 필요하며, Iptables는 이 도구들 중 하나일 뿐입니다. 실제로 nftables는 넷필터 시스템을 더 정교하게 개선한 것으로 iptables가 아닌 nft  명령어를 통해 환경을 설정합니다. 최신 사이트에서 고려해볼만 합니다.

흔히 네트워크 보안이라고 한다면 IP 주소만 차단하는 것으로 생각하기 쉽지만, netfilter의 능력은 그보다 더 낮은 계층까지 뻗어있습니다. nefilter는 L2 계층의 이더넷 프레임을 수정하거나 제어 가능합니다. 이를 활용하면 브릿징이나 하드웨어 레벨에 가까운 패킷 조작까지 가능하게 설계되었다는 것을 의미합니다.

iptables를 방화벽으로 사용하려면 반드시 먼저 IP 포워딩을 활성화시키고 여러가지 iptables 모듈들이 커널에 로딩되어 있음을 확인해야 합니다. 리눅스 방화벽은 보통 rc 시동 스크립트에 포함된 일련의 iptables 명령으로 구현됩니다. 각각의 iptables는 다음 중 한가지 형식을 취합니다.

```
iptables -F chain-name
iptables -P chain-name target
iptables -A chain-name -i interface -j target
```

-F 옵션은 체인에서 모든 이전 룰을 flush 합니다.

-P 옵션은 chain-name target은 체인의 기본 정책을 설정합니다. 기본 체인 타깃은

DROP 설정을 권유합니다.

-A 옵션은 현재 사양을 체인에 덧붙입니다. 테이블을 지정할때 -t 인수를 사용하지 않으면 명령들은 filter 테이블의 체인들에 의해 적용됩니다.

-i 매개변수는 룰을 명명된 인터페이스에 적용하며 -j 매개변수는 타깃을 지정합니다.

### iptables 기본 명령어

```
# iptables [-t 테이블 이름] <command> [Chain 이름] [parameters 옵션][-m 확장 모듈] [모듈 옵션] [target] [target 옵션]
```

규칙 확인 및 플러싱

- 현재 iptables Rule 확인

```
iptables -L -v -n
```

- L : 규칙 리스트 출력

- v: 상세 정보 출력

- n: IP와 PORT 번호 출력

모든 규칙 삭제

iptables -F

### iptables Rules, Targets, and Policies

Rule로 가보겠습니다. Input chain에서 모두 로그를 기록한 다음, 네트워크 스택에서 모든 패킷을 삭제하겠습니다.

```
# block packets with source IP 46.36.222.157
# -A is a shortcut for --append
# -j is a shortcut for --jump
$ iptables -A INPUT -s 46.36.222.157 -j DROP

# block outgoing SSH connections
$ iptables -A OUTPUT -p tcp --dport 22 -j DROP

# allow all incoming(HTTPS) connections
$ iptables -A INPUT -p tcp -m multiport --dports 80,443 \
-m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT 

$ iptables -A OUTPUT -p tcp -m multiport --dports 80,443 \
-m conntrack --ctstate ESTABLISHED -j ACCEPT
```

action을 수행하기 전에 모든 tcp connections 상태를 conntrack 모듈을 통해 상태를 저장하고 매 패킷마다 여러 속성들을 검사하여 꽤 복잡해보입니다. 이를 의사코드로 나타내면 아래와 비슷할 겁니다.

```
def handle_check(packet, chain):
	for rule in chain:
		modules = rule.modules
		for m in moudles:
			m.ensure_loaded()
			
		conditions = rule.conditions
		if all(c.apply(packet) for c in conditions):
			# terminating target, break the chain
			if rule.target in ('ACCEPT', 'DROP'):
				return rule.target
				
			# TODO: handle other targets
			
		# TODO: waht shall we do if there is no single
		# terminating target in the whole chain?
```

아이디어는 사실 꽤나 간단합니다. 순차적으로 모든 target이 종료될때까지 반복하고, chain의 끝에 도달할때까지 반복합니다.

```
# check the default policies
$ sudo iptables --list-rules # or -S
-P INPUT ACCEPT
-P FORWARD ACCEPT
-P OUTPUT ACCEPT

# change policy for chain FORWARD to target DROP
iptables --policy FORWAARD DROP 
```

### iptables Chains 

targets이 왜 action이 아닌 target으로 불리는지 알아보겠습니다. 아래 커맨드라인을 보면 rule은 iptables -A INPUT -s 46.36.222.157 -j DROP 이 -j 옵션으로 설정되어 있습니다. 이 말은 결과가 target으로 점프한다는 의미입니다.

```
 -j, --jump target
      This specifies the target of the rule; i.e., what to do
      if the packet matches it. The target can be a user-defined
      chain (other than the one this rule is in), one of the
      special builtin targets which decide the fate of the packet
      immediately, or an extension (see EXTENSIONS below).
```

```
$ iptables -P INPUT ACCEPT
# drop all forwards by default
$ iptables -P FORWARD DROP
$ iptables -P OUTPUT ACCEPT

# create a new chain
$ iptables -N DOCKER  # or --new-chain

# if outgoing interface is docker0, jump to DOCKER chain
$ iptables -A FORWARD -o docker0 -j DOCKER

# add some specific to Docker rules to the user-defined chain
$ iptables -A DOCKER ...
$ iptables -A DOCKER ...
$ iptables -A DOCKER ...

# jump back to the caller (i.e. FORWARD) chain
$ iptables -A DOCKER -j RETURN
```

```
 -P, --policy chain target
      Set the policy for the chain to the given target.
      See the section TARGETS for the legal targets.
      Only built-in (non-user-defined) chains can have policies,
      and neither built-in nor user-defined chains can be policy
      targets.
```

!/assets/image_df00c8b3-1cfa-42ac-bf4f-06ac44cc366f.png

[그림3. iptables의 룰 체인. 출처: https://iximiuz.com/laymans-iptables-101/user-defined-chains.png]

iptables라는 이름에서 알 수 있듯이 이 시스템은 여러개의 테이블으로 구성되어 있습니다. 각 테이블은 패킷 필터링(filter), 패킷 수정(mangle), 주소 변환(nat)등 목적에 따라 체인들을 논리적으로 그룹화합니다.

중요한 점은 INPUT이나 FORWARD 같은 동일한 이름의 체인이 여러 테이블에 동시에 존재할 수 있다는 점입니다. 예를 들어 filter 테이블에도 INPUT 체인이 있고, mangle 테이블에도 INPUT 체인이 있습니다. 이들은 이름은 같지만 독립적으로 동작합니다.

체인간의 우선순

- mangle.INPUT: 패킷에 대해 ACCEPT 판정을 내림

- filter.INPUT: 패킷에 대해 DROP 판정을 내림

이 경우 패킷의 운명은 어느 테이블의 체인이 먼저 실행되느냐에 달려 있습니다.

적용 순서

1. raw.PREROUTING

1. mangle.PREROUTING

1. nat.PREROUTING

1. mangle.INPUT 

1. filter.INPUT

따라서, mangle.INPUT에서 ACCEPT를 하더라도 패킷은 다음 순서인 filter.INPUT으로 넘어가게 됩니다. 여기서 DROP을 만나면 패킷은 최종적으로 버려지게 됩니다.

!/assets/image_df00c8b3-1cfa-42ac-bf4f-06ac44cc366f.png

[그림4: Linux namespace to 8.8.8.8. 출처: https://iximiuz.com/laymans-iptables-101/netns.png]

이 복잡한 우선순위를 확인하기 위해 모든 테이블의 체인에 LOG target을 추가해봅니다.

- 실험 환경: 호스트 시스템에 영향을 주지않기 위해 네트워크 네임스페이스를 사용하여 하나의 리눅스 머신안에서 두 대의 가상머신(클라이언트와 라우터 역할)을 시뮬레이션 합니다. 

- 로그 활성화: 커널 4.11 이상에서는 네임스페이스 내의 netfilter 로그를 확인하기 위해 /proc/sys/net/netfilter/nf_log_all_netns 값을 설정해야 합니다. 

- ping등을 실행하여 패킷을 발생시킨 후, 커널 메시지 dmesg또는 tail -f를 통해 로그 접두사가 찍히는 순서를 관찰

### 실험 환경 설정

네트워크 네임스페이스 생성

```
# run on host

$ unshare -r --net bash

# namespace (same terminal session)
$ echo $$
2979 # remember this PID
```

두 번째 터미널에서는 호스트에 관한 설정을 합니다.

```
# run on host

$ sudo -i

# create a veth interface
$ ip link add vGUEST type peer name vHOST

# move one of its peers to network namespace
$ ip link set vGUEST netns 2979 # PID form above

# create linux bridge
$ ip link add bro type bridge

# write vHOST to br0
$ ip link set vHOST master br0 

# set IP addrresses and bring devices up
$ ip addr add 172.16.0.1/16 dev br0
$ ip link set br0 up
$ ip link set vHOST up
$ ip addr

1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host
       valid_lft forever preferred_lft forever
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
    link/ether 52:54:00:26:10:60 brd ff:ff:ff:ff:ff:ff
    inet 10.0.2.15/24 brd 10.0.2.255 scope global noprefixroute dynamic eth0
       valid_lft 85752sec preferred_lft 85752sec
    inet6 fe80::5054:ff:fe26:1060/64 scope link
       valid_lft forever preferred_lft forever
3: vHOST@if4: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue master br0 state LOWERLAYERDOWN group default qlen 1000
    link/ether c2:96:cf:97:f4:12 brd ff:ff:ff:ff:ff:ff link-netnsid 0
5: br0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN group default qlen 1000
    link/ether c2:96:cf:97:f4:12 brd ff:ff:ff:ff:ff:ff
    inet 172.16.0.1/16 scope global br0
       valid_lft forever preferred_lft forever
       
# turn the host into a virtial router
iptables -t nat -A POSTROUTING -o eht0 -j MASSQUARE
$ echo 1 > /proc/sys/net/ipv4/ip_forward

# and dont forget to enable netfilter logs in namespace
$ echo 1 > /proc/sys/net/netfiltered/nf_log_all_nets
```

이제 네임스페이스 측에서 네트워크 인터페이스 설정을 마무리하겠습니다.

```
# run on the network namespace

# bridge devices
$ ip link set lo up
$ ip link set vGUEST up

# configure IP address
$ ip addr add 172.16.0.2/16 dev vGUEST
$ ip addr
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host
       valid_lft forever preferred_lft forever
4: vGUEST@if3: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default qlen 1000
    link/ether c2:31:a8:8b:d7:f8 brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet 172.16.0.2/16 scope global vGUEST
       valid_lft forever preferred_lft forever
    inet6 fe80::c031:a8ff:fe8b:d7f8/64 scope link
       valid_lft forever preferred_lft forever
       
       
 # set default route via br0
 $ ip route add default via 172.16.0.1 
 $ ip route
 default via 172.16.0.1
 172.16.0.0/16 dev vGUEST proto kernel scope link src 172.16.0.2
```

네임스페이스 안에서 iptables의 rule 변경사항들을 확인해보겠습니다.

```
# run in the network namespace:

$ iptables -S -t filter
-P INPUT ACCEPT
-P FORWARD ACCEPT
-P OUTPUT ACCEPT

$ iptables -S -t nat
-P PREROUTING ACCEPT
-P INPUT ACCEPT
-P OUTPUT ACCEPT
-P POSTROUTING ACCEPT

$ iptables -S -t mangle
-P PREROUTING ACCEPT
-P INPUT ACCEPT
-P FORWARD ACCEPT
-P OUTPUT ACCEPT
-P POSTROUTING ACCEPT

$ iptables -S -t raw
-P PREROUTING ACCEPT
-P OUTPUT ACCEPT

$ iptables -t filter -A INPUT -j LOG --log-prefix "NETNS_FILTER_INPUT "
$ iptables -t filter -A FORWARD -j LOG --log-prefix "NETNS_FILTER_FORWARD "
$ iptables -t filter -A OUTPUT -j LOG --log-prefix "NETNS_FILTER_OUTPUT "

$ iptables -t nat -A PREROUTING -j LOG --log-prefix "NETNS_NAT_PREROUTE "
$ iptables -t nat -A INPUT -j LOG --log-prefix "NETNS_NAT_INPUT "
$ iptables -t nat -A OUTPUT -j LOG --log-prefix "NETNS_NAT_OUTPUT "
$ iptables -t nat -A POSTROUTING -j LOG --log-prefix "NETNS_NAT_POSTROUTE "

$ iptables -t mangle -A PREROUTING -j LOG --log-prefix "NETNS_MANGLE_PREROUTE "
$ iptables -t mangle -A INPUT -j LOG --log-prefix "NETNS_MANGLE_INPUT "
$ iptables -t mangle -A FORWARD -j LOG --log-prefix "NETNS_MANGLE_FORWARD "
$ iptables -t mangle -A OUTPUT -j LOG --log-prefix "NETNS_MANGLE_OUTPUT "
$ iptables -t mangle -A POSTROUTING -j LOG --log-prefix "NETNS_MANGLE_POSTROUTE "

$ iptables -t raw -A PREROUTING -j LOG --log-prefix "NETNS_RAW_PREROUTE "
$ iptables -t raw -A OUTPUT -j LOG --log-prefix "NETNS_RAW_OUTPUT "
```

호스트에 설정된 iptables는 namespace 설정에 영향을 주지 않습니다.

```
# run on host:

$ iptables -S -t filter
-P INPUT ACCEPT
-P FORWARD ACCEPT
-P OUTPUT ACCEPT

$ iptables -S -t nat
-P PREROUTING ACCEPT
-P INPUT ACCEPT
-P OUTPUT ACCEPT
-P POSTROUTING ACCEPT
-A POSTROUTING -o eth0 -j MASQUERADE

$ iptables -S -t mangle
-P PREROUTING ACCEPT
-P INPUT ACCEPT
-P FORWARD ACCEPT
-P OUTPUT ACCEPT
-P POSTROUTING ACCEPT

$ iptables -S -t raw
-P PREROUTING ACCEPT
-P OUTPUT ACCEPT
```

iptables rule을 Host에서 업데이트 해보겠습니다.

```
# run on host:

$ iptables -t filter -A INPUT -j LOG --log-prefix "HOST_FILTER_INPUT "
$ iptables -t filter -A FORWARD -j LOG --log-prefix "HOST_FILTER_FORWARD "
$ iptables -t filter -A OUTPUT -j LOG --log-prefix "HOST_FILTER_OUTPUT "

$ iptables -t nat -A PREROUTING -j LOG --log-prefix "HOST_NAT_PREROUTE "
$ iptables -t nat -A INPUT -j LOG --log-prefix "HOST_NAT_INPUT "
$ iptables -t nat -A OUTPUT -j LOG --log-prefix "HOST_NAT_OUTPUT "
$ iptables -t nat -A POSTROUTING -j LOG --log-prefix "HOST_NAT_POSTROUTE "

$ iptables -t mangle -A PREROUTING -j LOG --log-prefix "HOST_MANGLE_PREROUTE "
$ iptables -t mangle -A INPUT -j LOG --log-prefix "HOST_MANGLE_INPUT "
$ iptables -t mangle -A FORWARD -j LOG --log-prefix "HOST_MANGLE_FORWARD "
$ iptables -t mangle -A OUTPUT -j LOG --log-prefix "HOST_MANGLE_OUTPUT "
$ iptables -t mangle -A POSTROUTING -j LOG --log-prefix "HOST_MANGLE_POSTROUTE "

$ iptables -t raw -A PREROUTING -j LOG --log-prefix "HOST_RAW_PREROUTE "
$ iptables -t raw -A OUTPUT -j LOG --log-prefix "HOST_RAW_OUTPUT "
```

마지막으로 8.8.8.8에 ping을 날리고 tailf 로 커널 메시지를 확인해보겠습니다.

```
# run in network namespace
$ ping 8.8.8.8
```

```
# run on host

$ tail -f /var/logs/messages
```

namepsace에서 8.8.8.8으로 핑을 날려보면 Nefilter에서 흥미로운 패턴을 발견할 수 있습니다.

```
Jun 21 13:25:19 localhost kernel: NETNS_RAW_OUTPUT IN= OUT=vGUEST SRC=172.16.0.2 DST=8.8.8.8 LEN=84 TOS=0x00 PREC=0x00 TTL=64 ID=2089 DF PROTO=ICMP TYPE=8 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: NETNS_MANGLE_OUTPUT IN= OUT=vGUEST SRC=172.16.0.2 DST=8.8.8.8 LEN=84 TOS=0x00 PREC=0x00 TTL=64 ID=2089 DF PROTO=ICMP TYPE=8 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: NETNS_FILTER_OUTPUT IN= OUT=vGUEST SRC=172.16.0.2 DST=8.8.8.8 LEN=84 TOS=0x00 PREC=0x00 TTL=64 ID=2089 DF PROTO=ICMP TYPE=8 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: NETNS_MANGLE_POSTROUTE IN= OUT=vGUEST SRC=172.16.0.2 DST=8.8.8.8 LEN=84 TOS=0x00 PREC=0x00 TTL=64 ID=2089 DF PROTO=ICMP TYPE=8 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: HOST_RAW_PREROUTE IN=br0 OUT= MAC=c2:96:cf:97:f4:12:c2:31:a8:8b:d7:f8:08:00 SRC=172.16.0.2 DST=8.8.8.8 LEN=84 TOS=0x00 PREC=0x00 TTL=64 ID=2089 DF PROTO=ICMP TYPE=8 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: HOST_MANGLE_PREROUTE IN=br0 OUT= MAC=c2:96:cf:97:f4:12:c2:31:a8:8b:d7:f8:08:00 SRC=172.16.0.2 DST=8.8.8.8 LEN=84 TOS=0x00 PREC=0x00 TTL=64 ID=2089 DF PROTO=ICMP TYPE=8 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: HOST_MANGLE_FORWARD IN=br0 OUT=eth0 MAC=c2:96:cf:97:f4:12:c2:31:a8:8b:d7:f8:08:00 SRC=172.16.0.2 DST=8.8.8.8 LEN=84 TOS=0x00 PREC=0x00 TTL=63 ID=2089 DF PROTO=ICMP TYPE=8 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: HOST_FILTER_FORWARD IN=br0 OUT=eth0 MAC=c2:96:cf:97:f4:12:c2:31:a8:8b:d7:f8:08:00 SRC=172.16.0.2 DST=8.8.8.8 LEN=84 TOS=0x00 PREC=0x00 TTL=63 ID=2089 DF PROTO=ICMP TYPE=8 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: HOST_MANGLE_POSTROUTE IN= OUT=eth0 SRC=172.16.0.2 DST=8.8.8.8 LEN=84 TOS=0x00 PREC=0x00 TTL=63 ID=2089 DF PROTO=ICMP TYPE=8 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: HOST_RAW_PREROUTE IN=eth0 OUT= MAC=52:54:00:26:10:60:52:54:00:12:35:02:08:00 SRC=8.8.8.8 DST=10.0.2.15 LEN=84 TOS=0x00 PREC=0x00 TTL=62 ID=17376 DF PROTO=ICMP TYPE=0 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: HOST_MANGLE_PREROUTE IN=eth0 OUT= MAC=52:54:00:26:10:60:52:54:00:12:35:02:08:00 SRC=8.8.8.8 DST=10.0.2.15 LEN=84 TOS=0x00 PREC=0x00 TTL=62 ID=17376 DF PROTO=ICMP TYPE=0 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: HOST_MANGLE_FORWARD IN=eth0 OUT=br0 MAC=52:54:00:26:10:60:52:54:00:12:35:02:08:00 SRC=8.8.8.8 DST=172.16.0.2 LEN=84 TOS=0x00 PREC=0x00 TTL=61 ID=17376 DF PROTO=ICMP TYPE=0 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: HOST_FILTER_FORWARD IN=eth0 OUT=br0 MAC=52:54:00:26:10:60:52:54:00:12:35:02:08:00 SRC=8.8.8.8 DST=172.16.0.2 LEN=84 TOS=0x00 PREC=0x00 TTL=61 ID=17376 DF PROTO=ICMP TYPE=0 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: HOST_MANGLE_POSTROUTE IN= OUT=br0 SRC=8.8.8.8 DST=172.16.0.2 LEN=84 TOS=0x00 PREC=0x00 TTL=61 ID=17376 DF PROTO=ICMP TYPE=0 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: NETNS_RAW_PREROUTE IN=vGUEST OUT= MAC=c2:31:a8:8b:d7:f8:c2:96:cf:97:f4:12:08:00 SRC=8.8.8.8 DST=172.16.0.2 LEN=84 TOS=0x00 PREC=0x00 TTL=61 ID=17376 DF PROTO=ICMP TYPE=0 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: NETNS_MANGLE_PREROUTE IN=vGUEST OUT= MAC=c2:31:a8:8b:d7:f8:c2:96:cf:97:f4:12:08:00 SRC=8.8.8.8 DST=172.16.0.2 LEN=84 TOS=0x00 PREC=0x00 TTL=61 ID=17376 DF PROTO=ICMP TYPE=0 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: NETNS_MANGLE_INPUT IN=vGUEST OUT= MAC=c2:31:a8:8b:d7:f8:c2:96:cf:97:f4:12:08:00 SRC=8.8.8.8 DST=172.16.0.2 LEN=84 TOS=0x00 PREC=0x00 TTL=61 ID=17376 DF PROTO=ICMP TYPE=0 CODE=0 ID=3197 SEQ=34
Jun 21 13:25:19 localhost kernel: NETNS_FILTER_INPUT IN=vGUEST OUT= MAC=c2:31:a8:8b:d7:f8:c2:96:cf:97:f4:12:08:00 SRC=8.8.8.8 DST=172.16.0.2 LEN=84 TOS=0x00 PREC=0x00 TTL=61 ID=17376 DF PROTO=ICMP TYPE=0 CODE=0 ID=3197 SEQ=34
```

로그는 꽤 장황하지만 로그 prefix에만 집중해보면 패턴은 아래와 같습니다.

```
NETNS_RAW_OUTPUT
NETNS_MANGLE_OUTPUT
NETNS_FILTER_OUTPUT
NETNS_MANGLE_POSTROUTE

HOST_RAW_PREROUTE
HOST_MANGLE_PREROUTE
HOST_MANGLE_FORWARD
HOST_FILTER_FORWARD
HOST_MANGLE_POSTROUTE
HOST_RAW_PREROUTE
HOST_MANGLE_PREROUTE
HOST_MANGLE_FORWARD
HOST_FILTER_FORWARD
HOST_MANGLE_POSTROUTE

NETNS_RAW_PREROUTE
NETNS_MANGLE_PREROUTE
NETNS_MANGLE_INPUT
NETNS_FILTER_INPUT
```

이로써 chain의 우선순위에 대한 기본적인 아이디어를 볼 수 있었습니다. namespace는 기본 클라이언트처럼 동작하고, host는 라우터처럼 동작합니다.

!/assets/image_df00c8b3-1cfa-42ac-bf4f-06ac44cc366f.png

[그림 5: 클라이언트의 처리 순서. 출처: https://iximiuz.com/laymans-iptables-101/tables-precedence.png]

!/assets/image_df00c8b3-1cfa-42ac-bf4f-06ac44cc366f.png

[그림 6: 라우터의 처리 순서: 출처: https://iximiuz.com/laymans-iptables-101/tables-precedence-route.png]

### 그 외 iptables 활용 예시

상태기반 필터링

위에서 이야기했듯이 iptables는 conntrack 모듈을 활용해 패킷의 상태를 추적할 수 있습니다.

- 기존에 확립된 연결 허용

```
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
```

- 특정 IP 차단

192.168.1.100에서 들어오는 모든 트래픽 차단

```
iptables -A INPUT -s 192.168.1.100 -j DROP
```

- 특정 대역폭 차단(Rate Limit)

SSH 브루트포스 공격 방지를 위해 초당 3개 이상의 SSH 접속 시도 차단

```
iptables -A INPUT -p tcp --dport=22 -m limit --limit 3/min --limit-burst 5 -j ACCEPT
```

- SNAT: 특정 출발지 IP 변경

```
iptables -t nat -A POSTROUTING -o eht0 -j MASSQUERADE
```

- DNAT: 외부 요청을 내부 서버로 포워딩

```
iptables -t nat -A PREROUTING -p tcp --dport=8000 -j DNAT --to-direction 192.168.1.200:80
```

iptables는 수십년간 사용되어 온 도구라 최신 트렌드와는 거리가 멀어 보일지 몰라도 이를 배우는것은 시간 낭비가 아닙니다. 현대 첨단 기술들은 이 오래된 기술 위에 세워졌기 때문입니다.

현대 컨테이너 생태계의 중심인 Docker와 k8s는 내부적으로 네트워킹 레이어를 설정하고 관리하기 위해 iptables를 매우 적극 활용하고 있습니다.

Docker는 컨테이너 간 격리, 포트 포워딩, NAT 등을 수행시 Iptables 규칙을 생성하여 처리합니다. k8s는 내부 서비스 통신을 제어하고 부하 분산을 구현할 때 기본적으로 iptables를 사요하여 패킷 경로를 지정합니다.

neffilter, iptalbes, IPVS와 같은 근본적인 기술들을 배우지 않고서는 현대적인 클라우드 클러스터 관리 도구를 대규모로 개발하거나 운영하는것이 불가능합니다.

예를 들어 쿠버네티스의 네트워크 문제(서비스 연결 오류, 통신 지연 등)를 해결하려면 결국 커널 레벨에서 패킷이 어떻게 흐르는지 어떤 Iptables 규칙이 적용되었는지 추적해야 합니다. 새로운 네트워크 플러그인(CNI)이나 고성능 클러스터 도구를 설계할때 리눅스 커널의 네트워크 스택 핸들링 방식을 모르면 한계에 부딪히게 됩니다.

예를 들면 쿠버네티스에서도 istio의 eonvoy proxy container와 app container의 상황에서 iptables가 어떻게 개입하는지도 생각해볼 수 있을것입니다.


<iframe
  src="https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FSVoee%2FbtrhjtMaPJM%2FAAAAAAAAAAAAAAAAAAAAAPoxfF7tegEBKs05bURSDhXyvHZMBoWin2g4_QK1PMWU%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1780239599%26allow_ip%3D%26allow_referer%3D%26signature%3DplrjwUwzEnb9yVvI0P15GTOkqsY%253D"
  width="100%"
  height="700"
  frameborder="0">
</iframe>


[그림: k8s istio에서의 iptable flow. 출처: https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FSVoee%2FbtrhjtMaPJM%2FAAAAAAAAAAAAAAAAAAAAAPoxfF7tegEBKs05bURSDhXyvHZMBoWin2g4_QK1PMWU%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1780239599%26allow_ip%3D%26allow_referer%3D%26signature%3DplrjwUwzEnb9yVvI0P15GTOkqsY%253D]


<iframe
  src="https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FcAerLU%2FbtrhfhegmL4%2FAAAAAAAAAAAAAAAAAAAAAOt9fBvRXE9K1V7en6zoHdqiE_gMMJdaSQf9j3m_hlpJ%2Fimg.jpg%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1780239599%26allow_ip%3D%26allow_referer%3D%26signature%3DZQywWMdPQvMuCdaN%252B74p%252FKBTJII%253D"
  width="100%"
  height="700"
  frameborder="0">
</iframe>


[그림: 네트워크 스택에서 프로세스까지 전달되는 과정. 출처: https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FcAerLU%2FbtrhfhegmL4%2FAAAAAAAAAAAAAAAAAAAAAOt9fBvRXE9K1V7en6zoHdqiE_gMMJdaSQf9j3m_hlpJ%2Fimg.jpg%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1780239599%26allow_ip%3D%26allow_referer%3D%26signature%3DZQywWMdPQvMuCdaN%252B74p%252FKBTJII%253D]

### Referrence

https://andrewpage.tistory.com/38

https://iximiuz.com/en/posts/laymans-iptables-101/ https://awx.notion.site/Linux-iptables-19685873b27880308e5af78fee51721

A Deep Dive into Iptables and Netfilter Architecture

Linux iptables Reference Guide with Examples

Iptables packet flow (and various others bits and bobs)

Linux Security Modules

https://en.wikipedia.org/wiki/Linux_Security_Modules

https://www.kernel.org/doc/html/latest/admin-guide/LSM/index.html

Introduction to Linux Security Modules (LSMs)

Linux NetFilter, IP Tables and Conntrack Diagrams

Iptables interactive scheme