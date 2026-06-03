---
title: "iptables Ubuntu 26.01 LTS environment 실습"
date: "2026-06-02T14:30:35.778Z"
categories:
  - "kernel"
  - "network"
  - "os"
  - "ubuntu"
author: "현제 김_7254"
slug: "iptables_ubuntu_2601_lts_environment_실습"
---

이번주에 포스팅한 iptables의 내용에 대해서 실습해보자. 나는 Ubuntu 환경을 Mac OS에서 multipass라는 하이퍼바이져 위에 구성하여 실습하고 있다. 굉장히 간편하게 환경을 구성할 수 있기에 Mac OS를 쓰는 분들이라면 강력 추천드리고 싶다.

먼저 실습전에, 무엇을 할것인지에 대해서 간략하게 설명해보자면 우분투 OS위에서 가상환경을 쿠버네티스 없이 구축을 한 후 가상환경 → 호스트 → 인터넷 으로 패킷이 빠져나갈 수 있는 네트워크를 구축해줄것이다.

<image class="image_num_1" src="/assets/image_14786d15-6de7-4642-815a-30f93d1d29ab.png" alt="" width="100%" height=100% ></image>


이는 컨테이너 기반의 도커, 쿠버네티스 가상화에서 매우매우 중요한 부분인데, 이 컨테이너 가상화라는 기술이 리눅스 커널의 namespace 기술을 이용하여 구축된것이기 때문이다. 우리는 network namespace를 Host에서 생성한 다음, VHost↔ Vguest 로 네임스페이스 인터페이스를 연결해줄것이다. 가상 랜 케이블 하나의 양쪽을 각각의 가상 컴퓨터 포트에 연결해준것과 같다.

```
Namespace A
    |
  vHOST
===========
  VGUEST
    |
Namespace B
```

이후에 bridge(virtual Switch)를 생성한 다음 여기에 다시 vHOST를 연결해주면 L2 이더넷 도메인이 만들어진다.

```
        br0 (switch)
       /      |      \
   eth0     vHOST   tap0
              |
  ========================= (bridge. Virtual L2 Switch)
    |         |        |
 VGUEST    VGUEST1    VGUEST2  
```

vGUEST가 프레임을 송신하면

1. vGUEST TX

1. vHOST RX

1. vHOST가 br0 포트이므로

1. br0가 스위칭 수행

1. 다른 포트로 전달

이를 통해 virtal guest↔ virtual host, 또는 virtual guest ↔ another virtual guest, 즉컨테이너끼리 bridge를 통해 통신할 수 있게 된다.

### get Host PID

먼저 HOST PID를 echo $$로 출력한다.

```
ubuntu@plucky-pheasant:~$ echo $$
5661
```

### Network namespace Create

이 상태에서 unshare 명령어로 네트워크 네임스페이스를 생성하고 PID를 출력해보면 이전과 다른것을 알 수 있다. 네임스페이스가 분리된것이다. 즉, 환경이 분리되었다. 분리되었다는것은 개념적인 이해이고, 실제로는 /proc/sys/net 하위에 새로운 네트워크 네임스페이스 ID의 리소스 집합이 생성된다.

```
ubuntu@plucky-pheasant: unshare -r --net bash

root@plucky-pheasant:/home/ubuntu# echo $$
69980
```

현재 쉘 프로세스가 69980의 네임스페이스에 들어간다. 리눅스 커널은 프로세스마다 namespace 정보를 가리키는 구조체를 가지고 있다.

```
task_struct
 |__ nsproxy
	 |__ net_ns
```

대략적으로 unshare —net bash를 실행하면 새로운 net_ns 객체를 생성하고, 현재 프로세스의 nsproxy→net_ns를 새 객체로 변경. 이후 생성되는 자식 프로세스도 해당 net_ns 상속되는 형식이다.

이 같은 기능들로 인해 환경이 분리된다.

자 그러면 구체적으로 무엇이 분리되는가?

1. Network Namespace

기존 host: ip link > lo, eth0, docker0, br0

새 Namespace: ip link > lo

처음에는 Loopback만 존재. 즉, Host의 eth0를 볼 수 없다.

1. Routing Table

- Host

ip route >

default via <ip>

<ip/CIDR> dev eth0

- New Namespace

ip route >

empty

라우팅 테이블도 완전히 새로 생성된다.

1. ARP Cache

- Host

ip neigh >

<ip> lladdr <MAC>

- New Namespace

(empty)

ARP 테이블도 별도

1. Netfilter, iptables

- Host iptables -L과  New Namespace의 방화벽 규칙은 독립적이다. 

1. Socket Table

- Host

ss -lnt >

<ip:port>

- New Namespace

ss -lnt

(empty)

Host에서 열려 있는 포트가 보이지 않는다.

두 환경은 같은 포트를 사용할 수 있다. 예를 들면 Host에서 실행중인 nginx 0.0.0.0:80 과 Namespace의

Python -m http.server 80은 둘다 공존할 수 있다. 왜냐하면 커널은 (netns, ip, port) 튜플 형식으로 소켓을 관리하기 때문이다. 즉, (container namespace, 0.0.0.0:80)과 (host namespace, 0.0.0.0:80)은 포트번호는 같지만 다른 소켓이다.

하지만 Network Namespace만 생성했다고 해서 외부와 통신이 되지 않는다. 루프백 인터페이스만 있고 NIC이 없기 때문에 host로 나갈 방법이 없다. 아래 그림과 같이 분리되어 있는 상황이다.

```
Host Namespace
 └─ vhost

New Namespace
 └─ vguest
```

이 때 사용하는 것이 veth interface이다.  ip link add vhost type veth peer name vguest와 같은 명령어로 veth pairt(가상 랜케이블)을 생성하고 이를 통해 두 Namespace를 연결한다. 그러면 아래처럼 연결될 것이다.

```
New Namespace
  (vhost)
		|
		| (veth pair)
		|
  (vguest)
Host Namespace
```

이와 같은 일들은 컨태이너 생성시 contaierd와 같은 docker engine이 암묵적으로 실행한다.

1. Network Namespace 생성

1. veth pair 생성

1. 한쪽을 컨테이너에 넣음

1. 다른쪽을 docker0 bridge에 연결

1. Ip 할당

1. NAT 설정

```
Container
   eth0
     │
   veth
     │
 docker0
     │
 Host eth0
     │
 Internet
```

Network Namespace를 분리하면 커널이 인터페이스, 라우팅 테이블, ARP 캐시, 소켓 테이블, iptables 상태 등을 포함한 "네트워크 스택 전체 인스턴스"를 새로 생성한다.

따라서 프로세스는 같은 커널을 사용하면서도 마치 별도의 머신처럼 독립된 네트워크 환경을 갖게 된다. 이것이 Docker, Kubernetes Pod, 컨테이너 네트워킹의 가장 기본적인 기술이다. 그러면 실제로 진행해보자.

### Configure Host side

```
# create veth interface
root@plucky-pheasant:/home/ubuntu# ip link add vGUEST type veth peer name vHOST

# move one of its peers to network namespace
root@plucky-pheasant:/home/ubuntu# ip link set vGUEST netns 69980

# create linux bridge
root@plucky-pheasant:/home/ubuntu# ip link ip link add br0 type bridge

# write vHOST to br0
Command "ip" is unknown, try "ip link help".
root@plucky-pheasant:/home/ubuntu# ip link add br0 type bridge
root@plucky-pheasant:/home/ubuntu# ip link set vHOST master br0

# set IP address and bring devices up
root@plucky-pheasant:/home/ubuntu# ip addr 172.16.0.1/16 dev br0
Command "172.16.0.1/16" is unknown, try "ip address help".
root@plucky-pheasant:/home/ubuntu# ip addr add 172.16.0.1/16 dev br0
root@plucky-pheasant:/home/ubuntu# ip link set br0 up
root@plucky-pheasant:/home/ubuntu# ip link set vHOST up
root@plucky-pheasant:/home/ubuntu# ip addr
1: lo: <LOOPBACK> mtu 65536 qdisc noop state DOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
2: vHOST@vGUEST: <NO-CARRIER,BROADCAST,MULTICAST,UP,M-DOWN> mtu 1500 qdisc noqueue master br0 state LOWERLAYERDOWN group default qlen 1000
    link/ether ae:8b:14:2c:15:53 brd ff:ff:ff:ff:ff:ff
3: vGUEST@vHOST: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN group default qlen 1000
    link/ether 52:93:07:2c:3c:5b brd ff:ff:ff:ff:ff:ff
4: br0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN group default qlen 1000
    link/ether ae:8b:14:2c:15:53 brd ff:ff:ff:ff:ff:ff
    inet 172.16.0.1/16 scope global br0
       valid_lft forever preferred_lft forever
       
       
       
ubuntu@purified-cusk:/$ sudo sysctl -w net.ipv4.ip_forward=1
net.ipv4.ip_forward = 1
```

```
RTNETLINK answers: Operation not permitted
ubuntu@purified-cusk:/$ sudo ip link set vHOST master br0
ubuntu@purified-cusk:/$ sudo ip link set br0 up
ubuntu@purified-cusk:/$ sudo ip link set vHOST up
ubuntu@purified-cusk:/$ ip addr
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host noprefixroute
       valid_lft forever preferred_lft forever
2: ens3: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
    link/ether 52:54:00:c5:49:3f brd ff:ff:ff:ff:ff:ff
    altname enp0s3
    altname enx525400c5493f
    inet 192.168.252.4/24 metric 100 brd 192.168.252.255 scope global dynamic ens3
       valid_lft 3144sec preferred_lft 3144sec
    inet6 fd81:ea57:df3:69c2:5054:ff:fec5:493f/64 scope global dynamic mngtmpaddr noprefixroute
       valid_lft 2591924sec preferred_lft 604724sec
    inet6 fe80::5054:ff:fec5:493f/64 scope link proto kernel_ll
       valid_lft forever preferred_lft forever
3: vHOST@if4: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue master br0 state LOWERLAYERDOWN group default qlen 1000
    link/ether 12:a0:35:72:d6:3d brd ff:ff:ff:ff:ff:ff link-netnsid 0
5: br0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN group default qlen 1000
    link/ether f2:00:d8:4f:26:7c brd ff:ff:ff:ff:ff:ff
ubuntu@purified-cusk:/$ echo 1 > /proc/sys/net/ipv4/ip_forward
-bash: /proc/sys/net/ipv4/ip_forward: Permission denied
```

veth-pair를 생성하고 네트워크 네임스페이스 PID를 veth pair의 한쪽인 vGUEST에 할당한다. 마찬가지로 반대쪽 veth도 bridge에 연결한다.  bridge에 Ip를 할당한 후 양쪽 인터페이스를 활성화하면 negotiation이 이뤄진 후 L2 연결이 활성화 될것이다. 이후 /proc/sys/net/ipv4/ip_forward 파일에 1을 write 해주면 bridge가 가상 라우터로서 활성화 된다.

현재 나는 multipass type 1 하이퍼바이져 기반 Ubuntu 26.04 LTS 최신 버젼을 사용하고 있고, 구 버젼인 iptables 대신 nftables를 쓰고 있다. 먼저 netfilter 로거가 활성화되어 있는지 확인하기 위해서 lsmod 로 로그 모듈이 커널에 로딩되어 있는지 확인을 해야한다.

### lsmod로 로그 모듈이 현재 커널에 올라와있는지 확인

```
root@primary:/proc/sys/net/netfilter# lsmod | grep syslog
nf_log_syslog          20480  1


root@primary:/proc/sys/net/netfilter# cat /proc/sys/net/netfilter/nf_log/2
nf_log_ipv4
```

정상적으로 메모리에 커널 모듈이 올라와있는걸 확인할 수 있다.

### Namespace Side

마찬가지로 Namespace 쪽에서도 인터페이스를 활성화하고 Ip를 할당한다. 그리고 bridge ip를 바라볼수 있도록 route table을 수정해주면 두 Namespace는 아래처럼 통신이되는것을 확인할 수 있다. 참고로 가상머신을 한번 껐다 켜서 host name이 다른점 참고바란다.

!/assets/image_14786d15-6de7-4642-815a-30f93d1d29ab.png

이제 iptable rule들을 적용해본다.

### Namespace Side

```
root@purified-cusk:/# iptables -S -t nat
-P PREROUTING ACCEPT
-P INPUT ACCEPT
-P OUTPUT ACCEPT
-P POSTROUTING ACCEPT
-A POSTROUTING -o eht0 -j MASQUERADE
-A POSTROUTING -o eht0 -j MASQUERADE
root@purified-cusk:/# iptables -t nat -A POSTROUTING -o ens3 -j MASQUERADE
root@purified-cusk:/# iptables -S -t nat
-P PREROUTING ACCEPT
-P INPUT ACCEPT
-P OUTPUT ACCEPT
-P POSTROUTING ACCEPT
-A POSTROUTING -o eht0 -j MASQUERADE
-A POSTROUTING -o eht0 -j MASQUERADE
-A POSTROUTING -o ens3 -j MASQUERADE
root@purified-cusk:/# iptables -S -t mangle
-P PREROUTING ACCEPT
-P INPUT ACCEPT
-P FORWARD ACCEPT
-P OUTPUT ACCEPT
-P POSTROUTING ACCEPT
root@purified-cusk:/# iptables -s -t raw
Bad argument `raw'
Try `iptables -h' or 'iptables --help' for more information.
root@purified-cusk:/# iptables -S -t raw
-P PREROUTING ACCEPT
-P OUTPUT ACCEPT
root@purified-cusk:/# iptables -t filter -A INPUT -j LOG --log-prefix "NETNS_FILTER_INPUT"
root@purified-cusk:/# iptables -t filter -A FORWARD -j LOG --log-prefix "NETNS_FILTER_FORWARD"
root@purified-cusk:/# iptables -t filter -A OUTPUT -j LOG --log-prefix "NETNS_FILTER_OUTPUT"
root@purified-cusk:/# iptables -S -t filter
-P INPUT ACCEPT
-P FORWARD ACCEPT
-P OUTPUT ACCEPT
-A INPUT -j LOG --log-prefix NETNS_FILTER_INPUT
-A FORWARD -j LOG --log-prefix NETNS_FILTER_FORWARD
-A OUTPUT -j LOG --log-prefix NETNS_FILTER_OUTPUT
```

!/assets/image_14786d15-6de7-4642-815a-30f93d1d29ab.png

위 사진을 보면 컨테이너 → google.com 으로의 Icmp는 빠져나가지 못하는 모습이다. 하나씩 파해쳐보자.

현재 내 환경은 아래와 같다.

```
Container (172.16.0.2) 
    |
   (vGUEST)
    |
   (vHOST)
    | 
   br0 (172.16.0.1)
    | 
   Host 
    |
   ens3 (192.168.0.1) 
```

먼저 Container의 인터페이스인 vGUEST(172.168.0.2)에서부터 시작해보자.

Iptables의 규칙들을 통과해야 할 것이다.

1. 인터페이스 상태 (ip addr)

인터페이스 상태를 먼저 체크해보자. 모두 UP 상태이고 루프백 주소, 링크 로컬 주소 모두 정상적으로 보인다.

```
root@purified-cusk:/# ip addr
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host proto kernel_lo
       valid_lft forever preferred_lft forever
4: vGUEST@if3: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default qlen 1000
    link/ether 4e:7c:e9:56:48:6b brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet 172.16.0.2/16 scope global vGUEST
       valid_lft forever preferred_lft forever
    inet6 fe80::4c7c:e9ff:fe56:486b/64 scope link proto kernel_ll
       valid_lft forever preferred_lft forever
```

1. 라우팅 확인 (ip route)

default gateway로 vGUEST 정상적으로 설정되어 있고 서브넷 라우팅 설정도 문제 없어 보인다. 현재 네트워크 네임스페이스와 서브넷 대역대가 정상적으로 연결되어 있다.

```
root@purified-cusk:/# ip route
default via 172.16.0.1 dev vGUEST
172.16.0.0/16 dev vGUEST proto kernel scope link src 172.16.0.2
```

1. Host까지 통신 확인 (ping to host)

문제 없이 icmp 패킷이 외부로 빠져나가고 정상적으로 sequnce가 증가하면 응답도 빠른시간 내에 온다. 역시 문제 없다. 그러면 Network Namepsace ↔ vGUEST ↔ vHOST ↔ br0 구간은 정상이다.

```
172.16.0.0/16 dev vGUEST proto kernel scope link src 172.16.0.2
root@purified-cusk:/# ping 172.16.0.1
PING 172.16.0.1 (172.16.0.1) 56(84) bytes of data.
64 bytes from 172.16.0.1: icmp_seq=1 ttl=64 time=0.143 ms
64 bytes from 172.16.0.1: icmp_seq=2 ttl=64 time=0.184 ms
64 bytes from 172.16.0.1: icmp_seq=3 ttl=64 time=0.187 ms
^C
--- 172.16.0.1 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2067ms
rtt min/avg/max/mdev = 0.143/0.171/0.187/0.020 ms
```

1. ARP 확인 (ip neigh)

역시나 정상적으로 ARP를 수행해서 bridge의 MAC 주소를 받아오고 있다.

```
root@purified-cusk:/# ip neigh
172.16.0.1 dev vGUEST lladdr f2:00:d8:4f:26:7c STALE
```

1. HOST가 가상 라우터로써의 역할을 하는가?

flag가 0이면 비활성. 1이면 활성이다. 역시나 문제 없다.

```
sysctl net.ipv4.ip_forward

ubuntu@purified-cusk:/var/log$ sysctl net.ipv4.ip_forward
net.ipv4.ip_forward = 1
```

1. HOST 라우팅 확인

host 부분은 살짝 복잡하다. 왜냐면 host는 브릿지와도 연결되고 현재 환경 기준 맥북과도 연결되어 있기 때문이다. 하지만 설정 자체는 문제 없어 보인다.

```
ubuntu@purified-cusk:/var/log$ ip route
default via 192.168.252.1 dev ens3 proto dhcp src 192.168.252.4 metric 100
172.16.0.0/16 dev br0 proto kernel scope link src 172.16.0.1
192.168.252.0/24 dev ens3 proto kernel scope link src 192.168.252.4 metric 100
192.168.252.1 dev ens3 proto dhcp scope link src 192.168.252.4 metric 100
```

1. FORWARD Chain

위 모든것들에도 문제가 없다면 이제 이번 학습의 최종 목적인 iptables Rule을 확인한다.

- Host side

정상으로 보인다.

```
ubuntu@purified-cusk:/var/log$ sudo iptables -L FORWARD -n -v
Chain FORWARD (policy ACCEPT 0 packets, 0 bytes)
 pkts bytes target     prot opt in     out     source               destination
```

1. NAT Check

65개의 패킷이 NAT되어서 나갔다.

```
ubuntu@purified-cusk:/var/log$ sudo iptables -t nat -L POSTROUTING -n -v
Chain POSTROUTING (policy ACCEPT 65 packets, 11786 bytes)
 pkts bytes target     prot opt in     out     source               destination
   60 10040 MASQUERADE  all  --  *      ens3    0.0.0.0/0            0.0.0.0/0
    2   142 LOG        all  --  *      *       0.0.0.0/0            0.0.0.0/0            LOG flags 0 level 4 prefix "HOST_NAT_POSTROUTE "
```

1. Packet이 Host까지 도달하는가?

```
sudo tcpdump -i vHOST -nn icmp
```

!/assets/image_14786d15-6de7-4642-815a-30f93d1d29ab.png

정상적으로 패킷이 나갔지만 들어오지 못하는것을  볼 수 있다. ens3에서 잘 캡쳐가 되면 사실상 문제는 NAT 실패인것이다.

```
# Container
ip route

# Host
sysctl net.ipv4.ip_forward

iptables -L FORWARD -n -v

iptables -t nat -L POSTROUTING -n -v

tcpdump -i ens3 -nn icmp
```

### ping은 되는데 왜 http get은 안될까?

NAT 수정 후 icmp 패킷은 정상적으로 왕복한다. 그런데 tcp 프로토콜로 리소스를 가져오는 rest api는 동작하지 않는다. 이는 네임서버가 nameserver 127.0.0.53 로 설정되어 있기 때문이다. 네트워크 네임스페이스를 직접 만든 경우 nameserver 127.0.0.53은 호스트의 systemd-resolved가 아니라 컨테이너 자신의 루프백이기 때문이다. 그런데 컨테이너 안에는 DNS 서버를 구축하지 않았다.

curl http://www.google.com → could not reolve host

```
root@purified-cusk:/# cat /etc/resolv.conf
# This is /run/systemd/resolve/stub-resolv.conf managed by man:systemd-resolved(8).
# Do not edit.
#
# This file might be symlinked as /etc/resolv.conf. If you're looking at
# /etc/resolv.conf and seeing this text, you have followed the symlink.
#
# This is a dynamic resolv.conf file for connecting local clients to the
# internal DNS stub resolver of systemd-resolved. This file lists all
# configured search domains.
#
# Run "resolvectl status" to see details about the uplink DNS servers
# currently in use.
#
# Third party programs should typically not access this file directly, but only
# through the symlink at /etc/resolv.conf. To manage man:resolv.conf(5) in a
# different way, replace this symlink by a static file or a different symlink.
#
# See man:systemd-resolved.service(8) for details about the supported modes of
# operation for /etc/resolv.conf.

nameserver 127.0.0.53
options edns0 trust-ad
search .
```

### DNS 직접 테스트 

nslookup google.com 8.8.8.8 또는 dig google.com @8.8.8.8 이 성공하면 DNS 경로는 이상없음
