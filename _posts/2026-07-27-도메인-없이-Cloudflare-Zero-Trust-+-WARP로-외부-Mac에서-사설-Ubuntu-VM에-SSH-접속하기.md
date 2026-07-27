---
title: "도메인 없이 Cloudflare Zero Trust + WARP로 외부 Mac에서 사설 Ubuntu VM에 SSH 접속하기"
date: "2026-07-27T12:01:27.239Z"
categories:
  - "cloudflare"
  - "tunnel"
  - "zero-trust"
  - "warp"
author: "현제 김_7254"
slug: "도메인_없이_cloudflare_zero_trust_warp로_외부_mac에서_사설_ubuntu_vm에_ssh_접속하기"
---

!/assets/image_c48811ba-324d-42e9-bd43-1153c83a04fc.png

## 1. 시작하며

외부에서도 학원내에 구축한 VM 우분투 컨트롤 플레인에 접속해서 작업하기위해 SSH 연결을 해야하기에 Cloudflare Tunnel 구축을 진행하였다.

대상 ubuntu VM의 주소는 아래와 같다.

```
Hostname: control-plane
Privae-IP: 192.168.253.xxx/24
SSH Port:22
```

일반적으로 외부에서 사설망 장비에 접근하기 위해서는 아래와 같은 구성이 필요하다.

- 공유기 포트포워딩

- 공인 IP

- VPN 서버

- Bastion Host

- 도메인과 Reverse Proxy

하지만 이번 환경에서는 공유기에 대한 제어가 불가능했고, 이를 위해서 도메인을 구매하기에도 애매했다. 따라서 다음과 같은 접근 환경을 구축했다.

```
      Cloudflare WARP           Cloudflare Tunnel                 
외부 Macbook ------> Cloudflare Edge -------> ubuntu Control Plane VM
[-------------------------tunneling------------------------------------]
```

최종적으로는 macbook에서 다음 명령만으로 내부 VM의 파일시스템에 접속가능하게된다.

```
ssh kim-hyun-jae@<IP> 
```

이번 글에서는 다음과 같은 트러블슈팅 과정을 중심으로 정리한다.

- ubuntu ssh 서버 검증

- cloudflare 설치 중 dpkg 오류 해결

- Tunnel Connector 상태 확인

- WARP와 Docker Desktop의 DNS 충돌

- CIDR Route 등록

- WARP Split tunnel 정책 분석

- macOS Route Table을 이용한 실제 패킷 경로 확인

- 최종 SSH 연결 성공

## 2. 구성 환경

### Ubuntu Vm

```
OS: Ubuntu 26.04 LTS
Kernel: 7.0.0-28-generic
Interface: ens33
Ip 192.168.253.128/24
cloudflared: 2026.7.3
SSH: TCP 22
```

ip addr link

```
2: ens33: <BROADCAST, MULTICAST, UP, LOWER_UP>
		inet: 192.168.253.128/24
```

Ubuntu에서는 Kubernetes Control Plane과 Cillium도 구성되어 있었지만, 이번 접속 대상은 Pod 네트워크가 아닌 VM의 ens22 인터페이스였다.

외부 Mackbook

```
LocalIP: 192.168.20.40
DefaultGateway: 192.168.20.1 (공유기)
Cloudflare One Client: 2026.6.880
Zero Trust Organization: lucky-mountain-c38f
```

cloudflare Tunnel

```
Tunnel Name: megastudy_controlplane
Tunnel Type: cloudflared
Virtual Network: default
Private CIDR: 192.168.253.0/24
```

### 3. 가장 먼저 Ubuntuu 서버

ssh가 가능한 상태인지 부터 점검

```
sudo systemctl status ssh

● ssh.service - OpenBSD Secure Shell server
     Loaded: loaded
     Active: active (running)
```

22번 포트 확인

```
ss -lnt | grep 22

LISTEN 0 4096 0.0.0.0:22 0.0.0.0:*
LISTEN 0 4096 [::]:22    [::]:*

```

접속 확인

```
ssh kim-hyun-jae@192.168.253.128

Warning: Permanently added '192.168.253.xxx' (ED25519) to the list of known hosts.
kim-hyun-jae@192.168.253.128's password:

Welcome to Ubuntu 26.04 LTS
Last login: Mon Jul 27 09:34:15 2026 from 192.168.253.1
```

## 4. Ubuntu VM에 cloudflared 설치

먼저 Cloudflare 패키지 서명 키와 저장소를 등록

```
sudo mkdir -p --mode=0755 /usr/share/keyrings

curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg \
	| sudo tee /usr/share/keyrings/cloudflare-main.gpg > /dev/null
	
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] \
https://pkg.cloudflare.com/cloudflared any main" \
  | sudo tee /etc/apt/sources.list.d/cloudflared.list
```

이후 설치 실행

```
sudo apt update
sudo apt -y install -y cloudflared
```

첫 설치시 다음과 같은 오류가 발생하였다.

```
Error: dpkg was interrupted, you must manually run
'sudo dpkg --configure -a' to correct the problem.
```

이 문제는 cloudflared 자체의 문제가 아니라 이전 패키지 작업이 정상 종료되지 않아 dpkg 상태가 중간에 멈춰있었던 것 같다.

다음 순서로 복구

```
sudo dpkg --configure -a
sudo apt --fix-broken install -y
sudo apt update
sudo apt install -y cloudflared
```

설치 후 버젼 확인

```
cloudflared --version

cloudflared version 2026.7.3
```

dpkg 복구 이후 cloudflared 패키지 정상적으로 설치 완료.

## 5. Cloudflare Tunnel Connector 등록

Cloudflare Zero Trust Dashboard에서 Tunnel 생성

```
Tunnel Name: megastudy_controlplanevm
Tunnel Type: cloudflared
```

Dashboard에서 제공된 서비스 설치 명령을 ubuntu에서 실행

```
sudo cloudflared service install [REDACTED_TUNNEL_TOKEN]
```

Tunnel Token은 인증 정보이므로 블로그나 공개 저장소에 노출해서는 안된다.

설치 결과는 다음과 같다.

```
INF Using Systemd
INF Linux service for cloudflared installed successfully
```

서비스 상태 확인

```
systemctl status cloudflared

● cloudflared.service - Cloudflare Tunnel client
     Loaded: loaded
     Active: active (running)

Main PID: 7928
/usr/bin/cloudflared --no-autoupdate tunnel run \
  --token-file /etc/cloudflared/token
```

cloudflared 내부 사전 점검 결과도 정상

```
● cloudflared.service - Cloudflare Tunnel client
     Loaded: loaded
     Active: active (running)

Main PID: 7928
/usr/bin/cloudflared --no-autoupdate tunnel run \
  --token-file /etc/cloudflared/token
```

즉, Ubuntu VM에서 Cloudflare Edge로 나가는 Outbound Tunnel 연결은 정상적으로 생성되었다.

### Tunnel Connector 확인

!/assets/image_c48811ba-324d-42e9-bd43-1153c83a04fc.png

그림 1. Tunnel 상태는 Healthy이고 Ubuntu의 Control-plane Connector는 Connected 상태다.

Dashboard에서 다음 내용 확인 가능.

```
Tunnel name: megastudy_controlplanevm
Tunnel type: cloudflared
Status: Healthy
Connector hostname: control-plane
Platform: linux_amd64
Version: 2026.7.3
Connector status: Connected
```

Tunnel Healthy는 다음 구간이 정상이라는 것이다.

```
Ubuntu cloudflared ------> cloudflared Edge
```

아직 전체 경로가 정상이라는 것은 아니다.

```
MacBook
  ─► WARP
  ─► Cloudflare Edge
  ─► CIDR Route
  ─► Tunnel
  ─► Ubuntu SSH
```

Tunnel이 Healthy여도 클라이언트가 대상 IP를 WARP로 보내지 않으면 실제 통신은 실패한다.

## 6. Tunnel에 Private Network CIDR 등록

공개 도메인 기반의 Public Hostname 대신 사설 IP에 직접 접근하기 위해 Tunnel에 Private Network CIDR을 등록했다.

등록한 네트워크는 다음과 같다.

```
192.167.xxx.0/24
```

!/assets/image_c48811ba-324d-42e9-bd43-1153c83a04fc.png

그림2. 192.168.253.xxx/24 대역을 해당 Tunnel을 통해 접근하도록 등록

이 Route는 Cloudflare에 다음 정보를 제공한다.

```
192.168.253.xxx/24 목적지
        │
        ▼
megastudy_controlplanevm Tunnel
        │
        ▼
control-plane Connector
```

따라서 WARP에 연결된 클라이언트가 192.168.253.xxx 로 패킷을 보내면 Cloudflare Edge는 해당 트래픽을 이 Tunnel로 전달할 수 있다.

이 구성에서는 별도의 공개 도메인이 필요하지 않다. 사설 ip를 그대로 사용할 수 있다.

## 7. MacBook을 Zero Trust 조직에 등록

MackBook에 Cloudflare One Clinet를 설치하고 Zero Trust 조직에 등록한다.

조직이름은 다음과 같다.

```
lucky-mountain-c38f
```

등록 후 Dashboard에서 Device 상태를 확인

!/assets/image_c48811ba-324d-42e9-bd43-1153c83a04fc.png

그림 3. Cloudflare One Client는 Traffic and DNS 모드로 연결되었고 Virtual Network는 default로 표시된다.

```
Client: Cloudflare WARP
Status: Connected
Mode: Traffic and DNS
Platform: macOS
Virtual Network: default
```

표면적으로는 정상적인 상태였다.

- Client Connect

- Traffic and DNS 모드

- Virtual Network default

- Tunnel Healthy 

- Connector Connected

- CIDR Route 등록 완료

Device의 실제 Ip 정보도 확인

```
ISP IP: 183.98.32.212
Local Gateway: 192.168.20.1
Device IP: 192.168.20.40
WARP IPv4: 100.96.0.1
Status: Active
```

그러나 실제 SSH 접속은 아직 성공하지 못했다.

## 8. 첫 번째 장애: WARP와 Docker Desktop의 DNS 충돌

WARP를 처음 연결하는 과정에서 다음 오류가 발생했다.

```
CF_DNS_PROXY_FAILURE
```

warp-cli status에서는 다음과 같이 표시

```
Unable
Reason: Another process is bound to port 53
Suspected Processes: [mDNSResponder]
```

macOS의 53번 포트를 확인헀을때 mDNSResponder가 사용중이였고 warp를 키면 인터넷이 되지 않았다. 당시 시스템에서는 아래 두 네트워크 계층이 동시에 동작중이였다.

```
Docker Desktop
 ├─ 가상 네트워크
 ├─ DNS Proxy
 └─ VPNKit

Cloudflare One Client
 ├─ 로컬 DNS 처리
 ├─ WARP Tunnel
 └─ 트래픽 가로채기
```

Docker Desktop을 완전히 종료하자 WARP 상태가 Connected로 바뀌었다.

이 문제를 통해 WARP연결 장애가 발생헀을때는 다음 항목들을 확인해야 함을 알 수 있었다.

```
warp-cli status

sudo lsof -nP -iUDP:53
sudo lsof -nP -iTCP:53
```

특히 다음 프로그램들은 WARP와 충돌할 가능성이 있다.

- Docker Desktop

- 다른 VPN 클라이언트

- 로컬 DNS 프록시

- 광고 차단 DNS 프로그램

- 보안 에이전트

- macOS Network Extension 기반 프로그램

## 9. 두번째 장애: 모든 상태가 정상인데 SSH Timeout

WARP 연결 이후 Mac에서 SSH를 시도했다.

```
ssh -vvv kim-hyun-jae@192.168.253.xxx
```

결과는 다음과 같았다.

```
Connecting to 192.168.253.128 port 22.
connect to address 192.168.253.128 port 22: Operation timed out
```

SSH 서버의 배너나 인증 화면까지 가지 못했다.

Conneection refused라면 일반적으로 대상 서버까지 패킷은 도달했지만, 해당 포트에서 Listen 중인 프로세스가 없거나 즉시 거절된 상태다.

```
Client --SYN---> Server
Client <--- RST ---- Server
```

반면  Operation Time out은 SYN을 보냈지만 응답을 받지 못했다는 의미이다.

우분투에서는 이미 다음 상태를 확인.

```
sshd active
0.0.0.0:22 LISTEN
내부 SSH 접속 성공
```

## 10. cert.pem 오류는 직접적인 원인이 아니다.

Ubuntu에서 Tunnel Route의 CLI로 확인하기 위해 다음 명령을 실행한다.

```
sudo cloudflared tunnel route ip show
```

```
ERR Cannot determine default origin certificate path.
No file cert.pem in:
  ~/.cloudflared
  ~/.cloudflare-warp
  ~/cloudflare-warp
  /etc/cloudflared
  /usr/local/etc/cloudflared

error while creating backend client:
Error locating origin cert
```

이 결과는 Tunnel Route설정이 잘못된것이 아니다. 현재 cloudflared서비스는 다음 방식으로 실행되고 있었다.

```
cloudflared tunnel run --token-file /etc/cloudflared/token
```

즉, cloudflared에서 발급한 Tunnel Token을 사용하는 원격 관리 방식이였다.

이 경우 두 동작을 구분해야 한다.

```
Data Plane
- Cloudflared가 Cloudflare Edge에 연결
- 실제 Private Network에 트래픽 전달

Managed plane
- Cloudflared CLI로 Tunnel 목록 및 Route 조회
- Cloudflared tunnel route ip show : cert.pem 오류
```

cert.pem 오류는 Root cause가 아니다.

## 11. 결정적인 단서: 실제 macOS Route확인

Cloudflared Dashboard에는 WARP가 Connected라고 표시되어 있었다.

하지만 VPN 또는 Overlay Network 묹데에서 중요한 것은 UI 상태가 아니라 다음 질문이다.

> 특정 목적지 IP로 가는 패킷이 실제로 어느 인터페이스로 나가는가?

Mac에서 다음 명령 실행

```
route -n get 192.168.253.xxx 
```

문제가 발생하던 상태의 결과는 다음과 같았다.

```
route to: 192.168.253.128
destination: default
mask: default
gateway: 192.168.20.1
interface: en0
```

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % ssh -vvv kim-hyun-jae@192.168.253.128
OpenSSH_9.9p2, LibreSSL 3.3.6
debug1: Reading configuration data /etc/ssh/ssh_config
debug1: /etc/ssh/ssh_config line 21: include /etc/ssh/ssh_config.d/* matched no files
debug1: /etc/ssh/ssh_config line 54: Applying options for *
debug2: resolve_canonicalize: hostname 192.168.253.128 is address
debug3: expanded UserKnownHostsFile '~/.ssh/known_hosts' -> '/Users/gimhyeonje/.ssh/known_hosts'
debug3: expanded UserKnownHostsFile '~/.ssh/known_hosts2' -> '/Users/gimhyeonje/.ssh/known_hosts2'
debug1: Authenticator provider $SSH_SK_PROVIDER did not resolve; disabling
debug3: channel_clear_timeouts: clearing
debug3: ssh_connect_direct: entering
debug1: Connecting to 192.168.253.128 [192.168.253.128] port 22.
debug3: set_sock_tos: set socket 3 IP_TOS 0x48
debug1: Connection established.
debug1: identity file /Users/gimhyeonje/.ssh/id_rsa type -1
debug1: identity file /Users/gimhyeonje/.ssh/id_rsa-cert type -1
debug1: identity file /Users/gimhyeonje/.ssh/id_ecdsa type -1
debug1: identity file /Users/gimhyeonje/.ssh/id_ecdsa-cert type -1
debug1: identity file /Users/gimhyeonje/.ssh/id_ecdsa_sk type -1
debug1: identity file /Users/gimhyeonje/.ssh/id_ecdsa_sk-cert type -1
debug1: identity file /Users/gimhyeonje/.ssh/id_ed25519 type -1
debug1: identity file /Users/gimhyeonje/.ssh/id_ed25519-cert type -1
debug1: identity file /Users/gimhyeonje/.ssh/id_ed25519_sk type -1
debug1: identity file /Users/gimhyeonje/.ssh/id_ed25519_sk-cert type -1
debug1: identity file /Users/gimhyeonje/.ssh/id_xmss type -1
debug1: identity file /Users/gimhyeonje/.ssh/id_xmss-cert type -1
debug1: identity file /Users/gimhyeonje/.ssh/id_dsa type -1
debug1: identity file /Users/gimhyeonje/.ssh/id_dsa-cert type -1
debug1: Local version string SSH-2.0-OpenSSH_9.9
debug1: Remote protocol version 2.0, remote software version OpenSSH_10.2p1 Ubuntu-2ubuntu3.5
debug1: compat_banner: match: OpenSSH_10.2p1 Ubuntu-2ubuntu3.5 pat OpenSSH* compat 0x04000000
debug2: fd 3 setting O_NONBLOCK
debug1: Authenticating to 192.168.253.128:22 as 'kim-hyun-jae'
debug1: load_hostkeys: fopen /Users/gimhyeonje/.ssh/known_hosts2: No such file or directory
debug1: load_hostkeys: fopen /etc/ssh/ssh_known_hosts: No such file or directory
debug1: load_hostkeys: fopen /etc/ssh/ssh_known_hosts2: No such file or directory
debug3: order_hostkeyalgs: no algorithms matched; accept original
debug3: send packet: type 20
debug1: SSH2_MSG_KEXINIT sent
debug3: receive packet: type 20
debug1: SSH2_MSG_KEXINIT received
debug2: local client KEXINIT proposal
debug2: KEX algorithms: sntrup761x25519-sha512,sntrup761x25519-sha512@openssh.com,mlkem768x25519-sha256,curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group-exchange-sha256,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512,diffie-hellman-group14-sha256,ext-info-c,kex-strict-c-v00@openssh.com
debug2: host key algorithms: ssh-ed25519-cert-v01@openssh.com,ecdsa-sha2-nistp256-cert-v01@openssh.com,ecdsa-sha2-nistp384-cert-v01@openssh.com,ecdsa-sha2-nistp521-cert-v01@openssh.com,sk-ssh-ed25519-cert-v01@openssh.com,sk-ecdsa-sha2-nistp256-cert-v01@openssh.com,rsa-sha2-512-cert-v01@openssh.com,rsa-sha2-256-cert-v01@openssh.com,ssh-ed25519,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,sk-ssh-ed25519@openssh.com,sk-ecdsa-sha2-nistp256@openssh.com,rsa-sha2-512,rsa-sha2-256
debug2: ciphers ctos: chacha20-poly1305@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com
debug2: ciphers stoc: chacha20-poly1305@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com
debug2: MACs ctos: umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha1-etm@openssh.com,umac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512,hmac-sha1
debug2: MACs stoc: umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha1-etm@openssh.com,umac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512,hmac-sha1
debug2: compression ctos: none,zlib@openssh.com
debug2: compression stoc: none,zlib@openssh.com
debug2: languages ctos:
debug2: languages stoc:
debug2: first_kex_follows 0
debug2: reserved 0
debug2: peer server KEXINIT proposal
debug2: KEX algorithms: mlkem768x25519-sha256,sntrup761x25519-sha512,sntrup761x25519-sha512@openssh.com,curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,ext-info-s,kex-strict-s-v00@openssh.com
debug2: host key algorithms: rsa-sha2-512,rsa-sha2-256,ecdsa-sha2-nistp256,ssh-ed25519
debug2: ciphers ctos: chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr
debug2: ciphers stoc: chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr
debug2: MACs ctos: umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha1-etm@openssh.com,umac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512,hmac-sha1
debug2: MACs stoc: umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha1-etm@openssh.com,umac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512,hmac-sha1
debug2: compression ctos: none,zlib@openssh.com
debug2: compression stoc: none,zlib@openssh.com
debug2: languages ctos:
debug2: languages stoc:
debug2: first_kex_follows 0
debug2: reserved 0
debug3: kex_choose_conf: will use strict KEX ordering
debug1: kex: algorithm: sntrup761x25519-sha512
debug1: kex: host key algorithm: ssh-ed25519
debug1: kex: server->client cipher: chacha20-poly1305@openssh.com MAC: <implicit> compression: none
debug1: kex: client->server cipher: chacha20-poly1305@openssh.com MAC: <implicit> compression: none
debug3: send packet: type 30
debug1: expecting SSH2_MSG_KEX_ECDH_REPLY
debug3: receive packet: type 31
debug1: SSH2_MSG_KEX_ECDH_REPLY received
debug1: Server host key: ssh-ed25519 SHA256:YAnsag76cvdglb91AUbmRhd+KkG1Qpkjj+uIrswojc8
debug1: load_hostkeys: fopen /Users/gimhyeonje/.ssh/known_hosts2: No such file or directory
debug1: load_hostkeys: fopen /etc/ssh/ssh_known_hosts: No such file or directory
debug1: load_hostkeys: fopen /etc/ssh/ssh_known_hosts2: No such file or directory
debug3: hostkeys_find_by_key_hostfile: trying user hostfile "/Users/gimhyeonje/.ssh/known_hosts"
debug3: hostkeys_foreach: reading file "/Users/gimhyeonje/.ssh/known_hosts"
debug1: hostkeys_find_by_key_cb: found matching key in ~/.ssh/known_hosts:10
debug3: hostkeys_find_by_key_hostfile: trying user hostfile "/Users/gimhyeonje/.ssh/known_hosts2"
debug1: hostkeys_find_by_key_hostfile: hostkeys file /Users/gimhyeonje/.ssh/known_hosts2 does not exist
debug3: hostkeys_find_by_key_hostfile: trying system hostfile "/etc/ssh/ssh_known_hosts"
debug1: hostkeys_find_by_key_hostfile: hostkeys file /etc/ssh/ssh_known_hosts does not exist
debug3: hostkeys_find_by_key_hostfile: trying system hostfile "/etc/ssh/ssh_known_hosts2"
debug1: hostkeys_find_by_key_hostfile: hostkeys file /etc/ssh/ssh_known_hosts2 does not exist
The authenticity of host '192.168.253.128 (192.168.253.128)' can't be established.
ED25519 key fingerprint is SHA256:YAnsag76cvdglb91AUbmRhd+KkG1Qpkjj+uIrswojc8.

```

192.168.253.xxx로 가는 패킷이 WARP 인터페이스가 아니라 MacBook의 물리 인터페이스 en0로 나가고 있었다.

```
MacBook
192.168.20.40
    │
    │ en0
    ▼
로컬 공유기
192.168.20.1
    │
    └─ 192.168.253.128로 가는 경로 없음
```

이는 곧 Cloudflare Tunnel은 전혀 사용되지 않고 있다는 의미다.

```
WARP Client: Connected
Tunnel: Healthy
Connector: Connected
CIDR Route: 등록 완료

하지만 실제 macOS Route:
192.168.253.128 → en0 → 192.168.20.1
```

## 12. Root Cause: WARP Split Tunnel에서 사설망이 제외됨

WARP 클라이언트에 실제 적용된 정책을 확인해보자.

```
warp-cli settings
```

문제의 출력에는 다음 내용들이 있었다.

```
(network policy) Exclude mode, with hosts/ips:
  10.0.0.0/8
  100.64.0.0/10
  169.254.0.0/16
  172.16.0.0/12
  192.0.0.0/24
  192.168.0.0/16
  224.0.0.0/24
  240.0.0.0/4
  255.255.255.255/32
```

핵심은 다음 규칙이였다. VM의 대역대는 192.168.253.xxx /24이다. 이는 192.168.0.0/16 대역대에 포함된다. cloudflare의 split tunnel에서는 warp의 exlude정책에 포함된 대역대들은 tunneling시키지 않는다.

```
192.168.0.0/16
```

따라서 WARP의 판단은 다음과 같았다.

목적지: 192.168.253.xxx —→ 192.168.0.0/16 exclude 규칙과 match.—> WARP Tunnel에서 제외 —→ macOS 기본 Route 사용 —→ en0 —> 192.168.20.1

1. Macbook의 Split Tunnel 판단

- 제외 대상 (exclude) → 로컬 네트워크(en0)로 전달

- WARP 대상 → Cloudflare Edge로 전달

1. Cloudflare Edge의 CIDR Route 판단

- 192.168.253.xxx → megastudy_controlplanevm

1. cloudflare Connector

- 내부 네트워크로 패킷 전달

그러니까 맥북에서 잘못된 인터페이스로 나가는것이 문제였다. cloudflare 정책 설정에서 exlude항목에서 내 private subnet대역대를 제거하고 client에서 반영하여 올바른 인터페이스로 나가도록 구성하자.

## 13. Split Tunnel 정책 변경

Cloudflare Zero Trus Dashboard에서 Macbook에 적용되는 Device Profile을 수정.

```
Settings
└─ Cloudflare One Client
   └─ Onboarding Device Profile
      └─ Split Tunnels
```

!/assets/image_c48811ba-324d-42e9-bd43-1153c83a04fc.png

## 14. 정책 변경 후 실제 Route 확인

정책이 반영된 후 다시 동일 명령 실행

```
route -n get 192.168.253.xxx 
```

결과가 다음과 같이 바뀌었다

```
route to: 192.168.253.128
destination: 192.168.128.0
mask: 255.255.128.0
interface: utun6
flags: <UP,DONE,PRCLONING>
mtu: 1280
```

가장 중요한 부분은 인터페이스 부분이다. 기본 인터페이스로 나가지 않고, warp 인터페이스인 utun6로 나가서 clouflare edge서버로 간 후, 라우팅 정책에 의해 사설 서버로 tunneling을 수행한다.

## 최소 범위의 CIDR만 광고

전체 사설망을 광고하기보다 필요한 범위만 등록하는것이 좋다. 네트워크 세그먼트를 광고하는것이 아닌 특정 vm주소만 정책에 지정하자.

이번 Device Profile은 사용자 이메일 조건으로 적용되었다. 하지만 운영환경에서는 허용사용자, 등록된 Device, OS version 등등을 복합조건으로 내걸수 있다.

## Cloudflare 구조에서 추가되는 세가지 

### overlay network

Overlay Network는 기존 인터넷망 위에 논리적인 별도 네트워크를 만드는것.

실제 물리 경로는 아래와 같다.

```
Mac -> Wi-Fi -> 공유기 -> ISP -> 인터넷 -> Cloudflare Edge
```

그러나 사용자와 애플리케이션 관점에서는 다음과 같은 논리적인 경로가 만들어진다.

```
        논리적 overlay        tunnel                   
Mac WARP ------> Cloudflare Edge -----> Cloudflared -----> 사설 ubuntu VM
```

Mac과 Ubuntu VM이 같은 물리 LAN에 있는것은 아니다. 그런데 Cloudflare가 중간에 논리적 경로를 만들기때문에 Mac에서는 원결 VM의 사설 Ip로 직접 접속하는것처럼 보인다.

Cloudflare의 pricate network route는 특정 IP는 CIDR을 특정 Tunnel connector에 매칭한다. 사용자가 해당 목적지에 접속하면 cloduflare가 해당 트래픽을 대응되는 터널로 매핑

```
                                tunnel-id
(출발지) ------- 85de9b4b-8271-4a88-b517-789ea757e0dd ---- 192.168.253.xxx
```

```
Cloudflare account private route table

Destination         Connector
────────────────────────────────────────
192.168.x.0/24      Tunnel A
10.10.0.0/16        Tunnel B
```

### Underlay와 Overlay 구분

```

Overlay
────────────────────────────────────────
WARP Client → Cloudflare Edge → Tunnel → VM


Underlay
────────────────────────────────────────
Wi-Fi → 공유기 → ISP → 인터넷 → Cloudflare

```

### Zero Trust Policy 구성

네트워크 안에 들어왔다고 단순히 허용하지 않는다. 복합적인 조건들을 동시에 평가한다. Cloudflare gateway Netwrok Policy는 protocol, RDB, port, 사용자 신원, 장치 등을 복합적으로 평가후 허용및 차단 가능

```
사용자 이메일 = user@example.com
AND
Device = 조직에 등록됨
AND
WARP = 연결됨
AND
목적지 = dst ip
AND
prot = 22
```

### 실제 SSH 연결에서 라우팅은 어떻게 결정되는가

1. 사용자가 목적지 ip와 함께 ssh 실행

1. ssh 프로세스는 os kernel에 다음 연결 요청(목적지 ip, port)

1. 커널이 목적지에 대한 라우팅 조회

- 운영체제는 라우팅 테이블에서 목적지와 일치하는 경로를 찾는다. 원칙적으로 Longest Prefix match 실행

- ex: 

- 192.168.B.X/32 → utn6

- 192.168.B.0/24 → utn6

- 192.168.0.0/16 → en0

- 0.0.0.0 → en0, gateway, 192.168.A.1

/32 > /24 > /16> /0

따라서 /32 또는 /24 WARP 경로가 있으면 utun6가 선택

```
route -n get 192.168.B.X
```

### Exclude 모드

기본적으로 WARP로 보낸다. 목록에 있는 목적지만 WARP에서 제외한다.

Exclude: 192.168.A.0/24

결과

192.168.A.10 → en0

192.168.B.X → utn6

8.8.8.8 → 정책에 따라 utn6

### Include 모드

기본적으로 WARP로 보내지 않는다. 목록에 명시된 목적지만 WARP로 보낸다.

Include:

192.168.B.0/24

결과

192.168.B.X → utn6

192.168.A.10 → en0

8.8.8.8 0 → en0

패킷을 가상 인터페이스에 넘기면 WARP 프로그램이 이를 받아 캡슐화.

# cpu-mem-hog MODE

작성 위치: /Users/gimhyeonje/cpu-mem-hog/cpu-mem-hog-mode-observation-guide.md
프로젝트 위치: /Users/gimhyeonje/cpu-mem-hog
주요 소스: main.go
Kubernetes manifest: cpu-mem-hog-fixed.yaml 또는 cpu-mem-hog.yaml

## 1. 프로젝트 개요

cpu-mem-hog 프로젝트를 환경변수 MODE 기준으로 나누어 관찰하기 위한 실험 문서다.

1. MODE=retain, MODE=discard, MODE=window가 Go heap, RSS, cgroup memory, GC 로그에 어떤 차이를 만드는지 관찰한다.

1. Go 소스 코드, Kubernetes 설정, 실행 로그, /metrics 결과를 한 화면에서 연결해서 설명할 수 있게 만든다.

이 프로젝트는 go소스 코드로 메모리 부하를 의도적으로 생성하고, 가시화하여 cgroup, 쿠버네티스의 resource limit과 GC, OOMKilled, swap 동작등을 종합적으로 이해하는것이 목표이다.

### 1.1 전체 System Architeture

!/assets/image_c48811ba-324d-42e9-bd43-1153c83a04fc.png

그림1. cpu-mem-hog System Architecure

- main.go의 실행 흐름

```
main()
  ├─ 환경변수 읽기
  ├─ cpuWorker goroutine 실행
  ├─ allocator goroutine 실행
  ├─ statsLoop goroutine 실행
  └─ HTTP server 실행
       ├─ /          HTML dashboard
       ├─ /metrics   JSON metrics
       ├─ /force-gc  runtime.GC() 강제 실행
       └─ /healthz   Kubernetes probe
```

```
Go make([]byte)
  -> slice backing array 할당
  -> byte slice 전체 touch
  -> physical page fault/RSS 증가
  -> MODE별 reference 유지/삭제
  -> Go GC 동작
  -> HeapAlloc / HeapSys / HeapReleased 변화
  -> Linux RSS / cgroup memory.current 변화
  -> Kubernetes memory limit/OOMKilled 가능성
```

```
gc 33233 @8921.312s 6%: 0.81+93+0.37 ms clock, 9.8+0/74/0.077+4.5 ms cpu, 413->413->412 MB, 412 MB goal, 0 MB stacks, 0 MB globals, 12 P
scav 128 KiB work (bg), 200 KiB work (eager), 94712 KiB now, 99% util
2026/07/26 13:05:46 allocation mode=window chunk_id=8716 chunk_mib=10 retained_chunks=40 total_allocated_mib=87160 allocations=8716 freed_chunks=8676
gc 33234 @8921.417s 6%: 66+5.9+1.8 ms clock, 797+0/2.5/0+21 ms cpu, 412->412->412 MB, 412 MB goal, 0 MB stacks, 0 MB globals, 12 P
scav 0 KiB work (bg), 288 KiB work (eager), 94936 KiB now, 99% util
gc 33235 @8922.284s 6%: 2.4+8.8+0.54 ms clock, 29+0.21/5.4/0+6.5 ms cpu, 412->423->411 MB, 412 MB goal, 0 MB stacks, 0 MB globals, 12 P
scav 1152 KiB work (bg), 0 KiB work (eager), 84824 KiB now, 97% util
gc 33236 @8922.298s 6%: 0.91+9.8+76 ms clock, 11+0.10/6.3/0+914 ms cpu, 411->413->413 MB, 411 MB goal, 0 MB stacks, 0 MB globals, 12 P
scav 128 KiB work (bg), 11144 KiB work (eager), 94576 KiB now, 99% util
2026/07/26 13:05:47 metrics {"time_unix_ms":1785071147299,"uptime_seconds":8922.188531122,"mode":"window","chunks_retained":40,"retained_mib":400,"total_allocated_mib":87160,"allocations":8716,"freed_chunks":8676,"approx_freed_mib":86760,"num_cpu":12,"gomaxprocs":12,"num_goroutine":21,"num_cgo_call":0,"heap_alloc_mib":422,"heap_sys_mib":506,"heap_idle_mib":82,"heap_inuse_mib":423,"heap_released_mib":82,"heap_objects":4252,"stack_inuse_mib":1,"mspan_inuse_mib":0,"mcache_inuse_mib":0,"buck_hash_sys_mib":0,"gc_sys_mib":2,"other_sys_mib":2,"next_gc_mib":411,"last_gc_pause_ms":3.004625,"pause_total_ms":499723.898425,"num_gc":33235,"gc_cpu_fraction":0.06333909661730386,"rss_mib":414,"vmsize_mib":1652,"vmdata_mib":546,"threads":19,"cgroup_memory_mib":429,"cgroup_memory_max_mib":512,"cgroup_memory_max_text":"536870912","cgroup_cpu_usage_usec":8183379857,"cgroup_cpu_nr_throttled":56070,"cgroup_cpu_throttled_usec":1314950598,"cgroup_cpu_max":"100000 100000","min_fault":22765644,"maj_fault":38,"delta_min_fault":3877,"delta_maj_fault":0,"anon_mib":414,"file_mib":7,"swap_mib":0,"pgpgin":4455685,"pgpgout":2091788,"pswpin":0,"pswpout":1,"delta_pgpgin":0,"delta_pgpgout":76,"delta_pswpin":0,"delta_pswpout":0,"fragmentation_mib":0}
scav 128 KiB work (bg), 136 KiB work (eager), 94624 KiB now, 99% util
gc 33237 @8922.387s 6%: 1.6+6.2+8.0 ms clock, 20+0.62/2.8/0+96 ms cpu, 413->413->412 MB, 413 MB goal, 0 MB stacks, 0 MB globals, 12 P
```

그림 2: Pod 기동 직후 kubectl logs deploy/cpu-mem-hog --tail=80

---

## 2. 부팅 시 환경변수 읽기 코드

소스 위치: main.go:153-185

```
func main() {
	cfg := config{
		Mode:            envString("MODE", "window"),
		ChunkMiB:        envInt("CHUNK_MIB", 10),
		AllocIntervalMS: envInt("ALLOC_INTERVAL_MS", 1000),
		StatsIntervalMS: envInt("STATS_INTERVAL_MS", 1000),
		WindowChunks:    envInt("WINDOW_CHUNKS", 40),
		CPUWorkers:      envInt("CPU_WORKERS", runtime.NumCPU()),
		HTTPAddr:        envString("HTTP_ADDR", ":8080"),
	}

	log.Printf("starting cpu-mem-hog deep dive: mode=%s chunk=%dMiB window=%d alloc_interval=%dms stats_interval=%dms cpu_workers=%d num_cpu=%d gomaxprocs=%d godebug=%q gogc=%q gomemlimit=%q",
		cfg.Mode, cfg.ChunkMiB, cfg.WindowChunks, cfg.AllocIntervalMS, cfg.StatsIntervalMS, cfg.CPUWorkers, runtime.NumCPU(), runtime.GOMAXPROCS(0), os.Getenv("GODEBUG"), os.Getenv("GOGC"), os.Getenv("GOMEMLIMIT"))
}
```

---

## 3. Kubernetes 기본 설정

현재 manifest의 핵심 환경변수와 resource limit은 다음과 같다.

```
env:
  - name: MODE
    value: "window"
  - name: CHUNK_MIB
    value: "10"
  - name: ALLOC_INTERVAL_MS
    value: "1000"
  - name: STATS_INTERVAL_MS
    value: "1000"
  - name: WINDOW_CHUNKS
    value: "40"
  - name: CPU_WORKERS
    value: "auto"
  - name: GODEBUG
    value: "gctrace=1,scavtrace=1"
  - name: GOGC
    value: "100"
  - name: GOMEMLIMIT
    value: "400MiB"

resources:
  requests:
    cpu: "250m"
    memory: "128Mi"
  limits:
    cpu: "1"
    memory: "512Mi"
```

주의할 점:

- GOMEMLIMIT=400MiB는 Kubernetes limits.memory=512Mi보다 낮게 잡혀 있다.

- Kubernetes OOM 판단은 Go HeapAlloc이 아니라 cgroup memory.current 기준이다.

- Go heap 외에도 goroutine stack, runtime metadata, binary mapping, page table/accounting overhead가 cgroup memory에 포함된다.

- CPU_WORKERS=auto는 코드상 숫자 파싱에 실패하므로 runtime.NumCPU() 기본값으로 fallback된다.

---

## 4. 빌드와 배포

현재 cluster가 cka-cluster이고 imagePullPolicy: Never를 쓰는 경우, 이미지는 host Docker가 아니라 minikube profile의 각 node/containerd image store에 있어야 한다.

빌드/로드:

```
cd /Users/gimhyeonje/cpu-mem-hog
minikube -p cka-cluster image build -t cpu-mem-hog:enhanced .
```

배포:

```
kubectl apply -f cpu-mem-hog-fixed.yaml
kubectl rollout status deployment/cpu-mem-hog --timeout=120s
kubectl get deploy cpu-mem-hog
kubectl get pod -l app=cpu-mem-hog -o wide
```

대시보드:

```
kubectl port-forward svc/cpu-mem-hog 18080:8080
open <http://127.0.0.1:18080>
```

검증:

```
curl -fsS <http://127.0.0.1:18080/healthz>
curl -fsS <http://127.0.0.1:18080/metrics>
curl -fsS -X POST <http://127.0.0.1:18080/force-gc>
```

---

## 5. 핵심 allocator 코드

MODE별 차이는 allocator() 함수의 switch 문에서 결정된다.

```
func allocator(ctx context.Context, wg *sync.WaitGroup, st *appState) {
	ticker := time.NewTicker(time.Duration(st.cfg.AllocIntervalMS) * time.Millisecond)
	defer ticker.Stop()
	for ctx.Err() == nil {
		select {
		case <-ticker.C:
			chunk := make([]byte, st.cfg.ChunkMiB*mib)
			for i := range chunk {
				chunk[i] = byte(i)
			}

			slot := chunkSlot{
				ID:              st.nextChunkID.Add(1),
				Ptr:             fmt.Sprintf("%p", unsafe.SliceData(chunk)),
				Callsite:        "main.go:allocator:make([]byte)",
				SizeMiB:         st.cfg.ChunkMiB,
				AllocatedUnixMS: time.Now().UnixMilli(),
				Live:            true,
				data:            chunk,
			}

			st.chunksMu.Lock()
			switch st.cfg.Mode {
			case "retain":
				st.chunks = append(st.chunks, slot)
			case "discard":
				st.freedChunks.Add(1)
				recordFreed(st, slot, "main.go:allocator:discard")
			case "window":
				st.chunks = append(st.chunks, slot)
				for len(st.chunks) > st.cfg.WindowChunks {
					evicted := st.chunks[0]
					st.chunks[0].data = nil
					st.chunks[0].Live = false
					copy(st.chunks, st.chunks[1:])
					st.chunks[len(st.chunks)-1] = chunkSlot{}
					st.chunks = st.chunks[:len(st.chunks)-1]
					st.freedChunks.Add(1)
					recordFreed(st, evicted, "main.go:allocator:window-evict")
				}
			default:
				st.chunks = append(st.chunks, slot)
			}
			retained := len(st.chunks)
			st.chunksMu.Unlock()

			log.Printf("allocation mode=%s chunk_id=%d chunk_mib=%d retained_chunks=%d total_allocated_mib=%d allocations=%d freed_chunks=%d",
				st.cfg.Mode, slot.ID, st.cfg.ChunkMiB, retained, st.totalAllocatedMiB.Load(), st.allocations.Load(), st.freedChunks.Load())
		}
	}
}
```

중요한 코드 흐름:

```
chunk := make([]byte, CHUNK_MIB MiB)
  -> Go heap에 큰 byte slice 생성

for i := range chunk { chunk[i] = byte(i) }
  -> 모든 page를 실제 touch
  -> minor fault 증가
  -> RSS/cgroup memory 증가

switch MODE
  -> retain: reference 유지
  -> discard: reference 버림
  -> window: 최근 N개 reference만 유지
```

- 그림 3: allocator 코드 캡처 삽입 위치

- 로그 5: allocation 로그 삽입 위치

---

## 6. 공통 관찰 지표

/metrics는 dashboard와 문서의 핵심 데이터 소스다.

소스 위치: main.go:431-439

```
mux.HandleFunc("/metrics", func(w http.ResponseWriter, r *http.Request) {
	st.samplesMu.Lock()
	samples := append([]sample(nil), st.samples...)
	st.samplesMu.Unlock()
	if len(samples) == 0 {
		samples = []sample{collectSample(st)}
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]any{
		"config": st.cfg,
		"samples": samples,
		"chunks": snapshotChunks(st),
		"freed_events": snapshotFreed(st),
		"vmas": readProcMaps(),
		"scenarios": scenarioCatalog(),
	})
})
```

관찰해야 하는 주요 field:

```
mode                  현재 MODE
chunks_retained       현재 live reference가 남은 chunk 개수
retained_mib          chunks_retained * CHUNK_MIB 근사값
total_allocated_mib   누적 allocation 총량
freed_chunks          discard/window eviction으로 reference 제거된 chunk 수
heap_alloc_mib        Go runtime이 보는 live heap
heap_sys_mib          Go runtime이 OS에서 확보한 heap 영역
heap_idle_mib         heap 중 idle 영역
heap_released_mib     OS에 반환된 heap page
next_gc_mib           다음 GC 목표
num_gc                GC 횟수
rss_mib               Linux process RSS
cgroup_memory_mib     cgroup memory.current
cgroup_memory_max_mib cgroup memory.max
cgroup_cpu_nr_throttled CPU throttling 횟수
```

메트릭 요약 명령:

```
curl -fsS <http://127.0.0.1:18080/metrics> \
  | python3 -c 'import json,sys; j=json.load(sys.stdin); s=j["samples"][-1]; print(json.dumps({k:s.get(k) for k in ["mode","chunks_retained","retained_mib","total_allocated_mib","freed_chunks","heap_alloc_mib","heap_sys_mib","heap_released_mib","next_gc_mib","num_gc","rss_mib","cgroup_memory_mib","cgroup_memory_max_mib","cgroup_cpu_nr_throttled"]}, indent=2))'
```

- 로그 6: 각 MODE별 /metrics 요약 출력 삽입 위치

---

## 7. MODE=retain

### 7.1 목적

retain 모드는 모든 chunk reference를 계속 보관한다.

이 모드는 다음을 관찰하기 좋다.

- live object가 있으면 GC가 메모리를 회수하지 못한다.

- HeapAlloc, RSS, cgroup_memory_mib가 계속 증가한다.

- Kubernetes memory limit에 가까워지면 OOMKilled가 발생할 수 있다.

### 7.2 실행 설정

안전하게 관찰하려면 처음에는 chunk를 작게 잡는다.

```
kubectl set env deployment/cpu-mem-hog \
  MODE=retain \
  CHUNK_MIB=5 \
  ALLOC_INTERVAL_MS=1000 \
  WINDOW_CHUNKS=40 \
  GOMEMLIMIT=400MiB

kubectl rollout status deployment/cpu-mem-hog --timeout=120s
kubectl logs -f deploy/cpu-mem-hog
```

OOMKilled까지 유도하려면 다음처럼 할 수 있다.

```
kubectl set env deployment/cpu-mem-hog MODE=retain CHUNK_MIB=10 GOMEMLIMIT-
```

주의: 이 설정은 512Mi memory limit 근처에서 Pod가 죽을 수 있다.

### 7.3 관련 Go 코드

```
case "retain":
	st.chunks = append(st.chunks, slot)
```

st.chunks가 slot.data를 계속 들고 있으므로 byte slice backing array가 reachable 상태로 남는다.

```
appState
  -> chunks
     -> chunk #1 data []byte  live
     -> chunk #2 data []byte  live
     -> chunk #3 data []byte  live
     -> ... 계속 증가
```

### 7.4 예상 allocation 로그

```
allocation mode=retain chunk_id=1 chunk_mib=10 retained_chunks=1 total_allocated_mib=10 allocations=1 freed_chunks=0
allocation mode=retain chunk_id=2 chunk_mib=10 retained_chunks=2 total_allocated_mib=20 allocations=2 freed_chunks=0
allocation mode=retain chunk_id=3 chunk_mib=10 retained_chunks=3 total_allocated_mib=30 allocations=3 freed_chunks=0
```

관찰 포인트:

- retained_chunks가 계속 증가한다.

- freed_chunks는 계속 0에 가깝다.

- HeapAlloc, RSS, cgroup_memory_mib가 같이 증가한다.

### 7.5 예상 /metrics 결과 모양

```
{
  "mode": "retain",
  "chunks_retained": 30,
  "retained_mib": 300,
  "total_allocated_mib": 300,
  "freed_chunks": 0,
  "heap_alloc_mib": 300,
  "rss_mib": 300,
  "cgroup_memory_mib": 300,
  "cgroup_memory_max_mib": 512
}
```

이 수치는 예시다. 실제 값은 runtime metadata와 GC 시점 때문에 달라진다.

### 7.6 결과 해석

retain에서 핵심은 reference가 살아 있으면 GC가 객체를 회수할 수 없다는 점이다.

```
GC 실행됨
  -> st.chunks에서 chunk reference 발견
  -> backing array live object로 판단
  -> HeapAlloc 감소하지 않음
  -> RSS/cgroup memory도 계속 증가
```

- 그림 4: retain dashboard에서 memory line 계속 증가하는 화면 삽입 위치

- 로그 7: retain allocation 로그 삽입 위치

- 로그 8: retain /metrics 요약 삽입 위치

- 로그 9: OOMKilled 유도 시 kubectl describe pod Last State 삽입 위치

---

## 8. MODE=discard

### 8.1 목적

discard 모드는 chunk를 만들고 touch한 뒤 reference를 보관하지 않는다.

이 모드는 다음을 관찰하기 좋다.

- allocation pressure는 계속 생긴다.

- Go GC가 unreachable object를 회수할 수 있다.

- HeapAlloc은 내려갈 수 있지만 RSS/cgroup memory는 즉시 내려가지 않을 수 있다.

- GC와 scavenger가 서로 다른 역할이라는 점을 확인할 수 있다.

### 8.2 실행 설정

```
kubectl set env deployment/cpu-mem-hog \
  MODE=discard \
  CHUNK_MIB=10 \
  ALLOC_INTERVAL_MS=1000 \
  GOMEMLIMIT=400MiB

kubectl rollout status deployment/cpu-mem-hog --timeout=120s
kubectl logs -f deploy/cpu-mem-hog
```

강제 GC:

```
curl -fsS -X POST <http://127.0.0.1:18080/force-gc>
```

### 8.3 관련 Go 코드

```
case "discard":
	// Deliberately drop the reference. GC can reclaim it later.
	st.freedChunks.Add(1)
	recordFreed(st, slot, "main.go:allocator:discard")
```

여기서는 st.chunks = append(...)를 하지 않는다. 따라서 allocator() tick이 끝나면 chunk reference가 사라지고 GC 대상이 된다.

```
allocator tick
  -> chunk 생성
  -> 전체 byte touch
  -> slot metadata 기록
  -> st.chunks에 저장하지 않음
  -> tick 종료 후 chunk reference 없음
  -> GC가 회수 가능
```

### 8.4 예상 allocation 로그

```
allocation mode=discard chunk_id=1 chunk_mib=10 retained_chunks=0 total_allocated_mib=10 allocations=1 freed_chunks=1
allocation mode=discard chunk_id=2 chunk_mib=10 retained_chunks=0 total_allocated_mib=20 allocations=2 freed_chunks=2
allocation mode=discard chunk_id=3 chunk_mib=10 retained_chunks=0 total_allocated_mib=30 allocations=3 freed_chunks=3
```

관찰 포인트:

- retained_chunks는 0에 가깝다.

- freed_chunks는 allocation마다 증가한다.

- total_allocated_mib는 계속 증가한다.

- heap_alloc_mib는 GC 후 낮아질 수 있다.

- rss_mib와 cgroup_memory_mib는 HeapAlloc보다 늦게 내려갈 수 있다.

### 8.5 예상 /metrics 결과 모양

```
{
  "mode": "discard",
  "chunks_retained": 0,
  "retained_mib": 0,
  "total_allocated_mib": 300,
  "freed_chunks": 30,
  "heap_alloc_mib": 10,
  "heap_released_mib": 120,
  "rss_mib": 80,
  "cgroup_memory_mib": 90,
  "num_gc": 8
}
```

이 수치는 예시다. 핵심은 total_allocated_mib는 커져도 chunks_retained와 retained_mib는 낮게 유지된다는 점이다.

### 8.6 결과 해석

discard에서 중요한 차이는 다음이다.

```
Go GC 회수
  -> unreachable chunk를 free 상태로 전환
  -> HeapAlloc 감소 가능

Go scavenger
  -> idle heap page를 OS에 반환
  -> HeapReleased 증가
  -> RSS/cgroup memory 감소 가능
```

즉 GC가 끝났다고 RSS가 즉시 줄어드는 것은 아니다.

- 그림 5: discard dashboard에서 HeapAlloc과 RSS가 다르게 움직이는 화면 삽입 위치

- 로그 10: discard allocation 로그 삽입 위치

- 로그 11: discard force-gc 전후 /metrics 비교 삽입 위치

---

## 9. MODE=window

### 9.1 목적

window 모드는 최근 WINDOW_CHUNKS개 chunk만 유지한다.

현재 기본 실험 설정은 다음과 같다.

```
MODE=window
CHUNK_MIB=10
WINDOW_CHUNKS=40
GOMEMLIMIT=400MiB
Kubernetes memory limit=512Mi
```

즉 live payload가 대략 400MiB 근처에서 안정화되도록 만든다.

이 모드는 다음을 관찰하기 좋다.

- reference 제거가 live heap을 제한한다.

- retained_chunks가 WINDOW_CHUNKS에서 안정화된다.

- freed_chunks는 window eviction 이후 계속 증가한다.

- HeapAlloc/RSS/cgroup memory가 400MiB 근처에서 흔들린다.

- GC는 자주 돌지만 OOMKilled를 피할 수 있다.

### 9.2 실행 설정

```
kubectl set env deployment/cpu-mem-hog \
  MODE=window \
  CHUNK_MIB=10 \
  WINDOW_CHUNKS=40 \
  ALLOC_INTERVAL_MS=1000 \
  GOMEMLIMIT=400MiB

kubectl rollout status deployment/cpu-mem-hog --timeout=120s
kubectl logs -f deploy/cpu-mem-hog
```

### 9.3 관련 Go 코드

```
case "window":
	st.chunks = append(st.chunks, slot)
	for len(st.chunks) > st.cfg.WindowChunks {
		evicted := st.chunks[0]
		st.chunks[0].data = nil
		st.chunks[0].Live = false
		copy(st.chunks, st.chunks[1:])
		st.chunks[len(st.chunks)-1] = chunkSlot{}
		st.chunks = st.chunks[:len(st.chunks)-1]
		st.freedChunks.Add(1)
		recordFreed(st, evicted, "main.go:allocator:window-evict")
	}
```

동작 흐름:

```
새 chunk append
  -> len(chunks) <= WINDOW_CHUNKS 이면 그대로 유지
  -> len(chunks) > WINDOW_CHUNKS 이면 가장 오래된 chunk 제거
      -> data=nil
      -> slice에서 제거
      -> freed event 기록
```

### 9.4 예상 allocation 로그

초기에는 retained_chunks가 증가한다.

```
allocation mode=window chunk_id=1 chunk_mib=10 retained_chunks=1 total_allocated_mib=10 allocations=1 freed_chunks=0
allocation mode=window chunk_id=2 chunk_mib=10 retained_chunks=2 total_allocated_mib=20 allocations=2 freed_chunks=0
```

WINDOW_CHUNKS=40에 도달한 뒤에는 retained_chunks가 40에서 유지되고 freed_chunks가 증가한다.

```
allocation mode=window chunk_id=40 chunk_mib=10 retained_chunks=40 total_allocated_mib=400 allocations=40 freed_chunks=0
allocation mode=window chunk_id=41 chunk_mib=10 retained_chunks=40 total_allocated_mib=410 allocations=41 freed_chunks=1
allocation mode=window chunk_id=42 chunk_mib=10 retained_chunks=40 total_allocated_mib=420 allocations=42 freed_chunks=2
```

### 9.5 실제 관찰된 /metrics 샘플

기존 실험에서 관찰된 sample:

```
{
  "mode": "window",
  "chunks_retained": 40,
  "total_allocated_mib": 450,
  "allocations": 45,
  "num_cpu": 12,
  "gomaxprocs": 12,
  "num_goroutine": 18,
  "heap_alloc_mib": 410,
  "heap_sys_mib": 427,
  "heap_idle_mib": 16,
  "heap_released_mib": 16,
  "next_gc_mib": 400,
  "last_gc_pause_ms": 75.743327,
  "pause_total_ms": 1755.824263,
  "num_gc": 29,
  "gc_cpu_fraction": 0.03018828865143869,
  "rss_mib": 408,
  "vmsize_mib": 1587,
  "vmdata_mib": 465,
  "threads": 17,
  "cgroup_memory_mib": 407,
  "cgroup_memory_max_mib": 512,
  "cgroup_cpu_nr_throttled": 301,
  "cgroup_cpu_throttled_usec": 12527040,
  "cgroup_cpu_max": "100000 100000"
}
```

해석:

- chunks_retained=40, CHUNK_MIB=10이므로 live payload는 약 400MiB다.

- heap_alloc_mib=410으로 Go live heap이 400MiB 근처에 있다.

- rss_mib=408, cgroup_memory_mib=407도 거의 비슷하게 따라온다.

- cgroup_memory_max_mib=512라서 Kubernetes memory limit 아래에 있다.

- next_gc_mib=400, num_gc=29로 GOMEMLIMIT 근처에서 GC가 자주 돈다.

- cgroup_cpu_max="100000 100000"은 1 CPU quota다.

- num_cpu=12, gomaxprocs=12라서 Go runtime은 12 CPU로 동작하려고 하지만 cgroup quota는 1 CPU라 throttling이 발생한다.

### 9.6 실제 GC trace 예시

기존 실험에서 관찰된 GC/scavenger 로그:

```
gc 84 @82.958s 3%: 1.9+7.7+0.42 ms clock, 23+4.0/7.2/0+5.0 ms cpu, 410->410->400 MB, 410 MB goal, 0 MB stacks, 0 MB globals, 12 P
scav 64 KiB work (bg), 10240 KiB work (eager), 16360 KiB now, 97% util
```

핵심 구간:

```
410->410->400 MB, 410 MB goal
```

의미:

- GC 시작 전 heap: 약 410MiB

- GC 중/후 heap: 약 410MiB

- live heap: 약 400MiB

- 다음 GC 목표: 약 410MiB

window 모드에서는 오래된 chunk reference를 제거하므로 live heap이 WINDOW_CHUNKS * CHUNK_MIB 근처에서 제한된다.

- 그림 6: window dashboard에서 retained chunks가 40에 고정된 화면 삽입 위치

- 로그 12: window allocation 로그 삽입 위치

- 로그 13: window /metrics 요약 삽입 위치

- 로그 14: window GC/scavtrace 로그 삽입 위치

---

## 10. MODE별 비교표

---

## 11. 실험 실행 템플릿

각 모드를 같은 방식으로 비교하려면 다음 순서로 반복한다.

### 11.1 공통 준비

```
cd /Users/gimhyeonje/cpu-mem-hog
minikube -p cka-cluster image build -t cpu-mem-hog:enhanced .
kubectl apply -f cpu-mem-hog-fixed.yaml
kubectl rollout status deployment/cpu-mem-hog --timeout=120s
kubectl port-forward svc/cpu-mem-hog 18080:8080
```

### 11.2 모드 변경

```
kubectl set env deployment/cpu-mem-hog MODE=<retain|discard|window>
kubectl rollout status deployment/cpu-mem-hog --timeout=120s
```

### 11.3 로그 수집

```
kubectl logs deploy/cpu-mem-hog --tail=120 > logs-<mode>.txt
```

### 11.4 메트릭 수집

```
curl -fsS <http://127.0.0.1:18080/metrics> > metrics-<mode>.json
```

### 11.5 요약 출력

```
python3 - <<'PY'
import json
mode = "window"
with open(f"metrics-{mode}.json") as f:
    j = json.load(f)
s = j["samples"][-1]
keys = [
    "mode", "chunks_retained", "retained_mib", "total_allocated_mib",
    "freed_chunks", "heap_alloc_mib", "heap_sys_mib", "heap_released_mib",
    "next_gc_mib", "num_gc", "rss_mib", "cgroup_memory_mib",
    "cgroup_memory_max_mib", "cgroup_cpu_nr_throttled"
]
print(json.dumps({k: s.get(k) for k in keys}, indent=2))
PY
```

- 로그 15: retain 요약 출력 삽입 위치

- 로그 16: discard 요약 출력 삽입 위치

- 로그 17: window 요약 출력 삽입 위치

---

## 12. 발표/보고서용 결론 문장

### retain 결론

MODE=retain에서는 모든 chunk reference가 st.chunks에 남아 있으므로 Go GC가 객체를 회수할 수 없다. 따라서 retained_chunks, HeapAlloc, RSS, cgroup_memory_mib가 계속 증가하고 Kubernetes memory limit에 가까워지면 OOMKilled가 발생할 수 있다.

### discard 결론

MODE=discard에서는 chunk를 할당하고 touch하지만 reference를 보관하지 않는다. 그래서 total_allocated_mib는 계속 증가해도 live heap은 GC 이후 낮아질 수 있다. 다만 GC가 객체를 회수하는 것과 Go runtime이 OS에 page를 반환해서 RSS가 줄어드는 것은 별개라서 HeapAlloc과 RSS/cgroup memory가 다르게 움직일 수 있다.

### window 결론

MODE=window에서는 최근 WINDOW_CHUNKS개 chunk만 유지하므로 live heap이 CHUNK_MIB * WINDOW_CHUNKS 근처에서 제한된다. 현재 기본 설정에서는 10MiB chunk 40개를 유지하므로 live payload가 약 400MiB가 되고, GOMEMLIMIT=400MiB, Kubernetes memory limit 512Mi 조합으로 OOMKilled를 피하면서 GC/RSS/cgroup 변화를 안정적으로 관찰할 수 있다.

---

## 13. 빠른 장애 확인

Pod가 뜨지 않으면 먼저 image 문제를 확인한다.

```
kubectl describe pod -l app=cpu-mem-hog
```

다음 에러가 보이면 image가 node에 없는 것이다.

```
ErrImageNeverPull
Container image "cpu-mem-hog:enhanced" is not present with pull policy of Never
```

해결:

```
cd /Users/gimhyeonje/cpu-mem-hog
minikube -p cka-cluster image build -t cpu-mem-hog:enhanced .
kubectl delete pod -l app=cpu-mem-hog
kubectl rollout status deployment/cpu-mem-hog --timeout=120s
```

---

## 14. 문서에 최종 첨부할 자료 체크리스트

- 그림 1: 전체 아키텍처

- 그림 2: dashboard 첫 화면

- 그림 3: allocator 코드 캡처

- 그림 4: retain memory 증가 그래프

- 그림 5: discard HeapAlloc/RSS 차이 그래프

- 그림 6: window retained chunks 안정화 그래프

- 로그 1: Pod 기동 로그

- 로그 2: MODE별 startup 로그

- 로그 3: image build 로그

- 로그 4: rollout/pod 상태

- 로그 5: 공통 allocation 로그

- 로그 7~9: retain 로그와 OOMKilled 결과

- 로그 10~11: discard 로그와 force-gc 전후 결과

- 로그 12~14: window allocation/metrics/GC trace

- 로그 15~17: MODE별 /metrics 요약 비교

쿠버네티스의 OOMKilled 상황을 직접 관찰하기 위해 Go로 리소스 폭증 프로세스를 만들고 모니터링까지 연결지어서 관찰해보았다.

흐름은 다음과 같다.

1. Go 소스 작성 

1. Docker image build

1. Minikube에 이미지 넣기

1. kubernetes deplotment 배포

1. 메모리 limit 초과

1. OOMkilled / CrashLoopBackOff 관찰

GO 소스는 크게 다음 두가지 작업을 한다. 이 소스코드에 대한 내용은 따로 링크를 참조하여 글을 작성했다. 이 글에서는 OOMkilled를 확인하는것이 목적이기에 생략하겠다.

1. CPU를 계속 사용하는 goroutine 실행

1. 1초마다 10Mib씩 메모리 할당

- 내 가설

그리고 쿠버네티스 쪽에서는 memory limit을 256Mi로 걸어둔다. 그러면 대략 26초 뒤에 컨테이너가 limit을 넘고 OOMKilled 되는 모습을 볼 수 있다.

###  GO 소스 작성 후 작업 디렉토리에 Dockerfile 빌드

hungry_process.go

```
package main

import (
	"context"
	"fmt"
	"os/signal"
	"runtime"
	"sync"
	"syscall"
	"time"
)

func main() {
	ctx, cancel := signal.NotifyContext(
		context.Background(),
		syscall.SIGINT,
		syscall.SIGTERM,
	)
	defer cancel()

	var wg sync.WaitGroup

	numCPU := runtime.NumCPU()
	runtime.GOMAXPROCS(numCPU)

	// CPU 부하 생성
	for i := 0; i < numCPU; i++ {
		wg.Add(1)

		go func(workerID int) {
			defer wg.Done()

			fmt.Printf("Started CPU hog worker=%d\n", workerID)

			for ctx.Err() == nil {
				// 의도적인 busy loop
			}

			fmt.Printf("Stopped CPU hog worker=%d\n", workerID)
		}(i)
	}

	const memChunkMiB = 10
	var chunks [][]byte

	// 메모리 부하 생성
	wg.Add(1)
	go func() {
		defer wg.Done()

		for ctx.Err() == nil {
			chunk := make([]byte, memChunkMiB*1024*1024)

			// 실제 물리 메모리 페이지가 할당되도록 데이터를 기록
			for i := 0; i < len(chunk); i++ {
				chunk[i] = byte(i % 256)
			}

			// 참조를 유지해서 GC가 회수하지 못하게 함
			chunks = append(chunks, chunk)

			fmt.Printf(
				"Allocated %d MiB, total=%d MiB, chunks=%d\n",
				memChunkMiB,
				len(chunks)*memChunkMiB,
				len(chunks),
			)

			select {
			case <-ctx.Done():
				return
			case <-time.After(time.Second):
			}
		}
	}()

	<-ctx.Done()

	fmt.Println("Received termination signal. Initiating shutdown...")

	wg.Wait()

	fmt.Println("Shutdown complete.")
}
```

```
bash
mkdir -p ~/cpu-mem-hog
cd ~/cpu-mem-hog

```

### dockerfile

```
    FROM golang:1.22-bookworm AS builder

    WORKDIR /src
    COPY go.mod .
    COPY main.go .

    RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /cpu-mem-hog .

    FROM debian:bookworm-slim

    COPY --from=builder /cpu-mem-hog /usr/local/bin/cpu-mem-hog

    ENTRYPOINT ["/usr/local/bin/cpu-mem-hog"]
```

docker build -t cpu-mem-hog:local .

```
[+] Building 33.5s (15/15) FINISHED                                     docker:desktop-linux
 => [internal] load build definition from Dockerfile                                    0.1s
 => => transferring dockerfile: 320B                                                    0.0s
 => [internal] load metadata for docker.io/library/golang:1.22-bookworm                 1.8s
 => [internal] load metadata for docker.io/library/debian:bookworm-slim                 1.8s
 => [auth] library/debian:pull token for registry-1.docker.io                           0.0s
 => [auth] library/golang:pull token for registry-1.docker.io                           0.0s
 => [internal] load .dockerignore                                                       0.0s
 => => transferring context: 2B                                                         0.0s
 => CACHED [stage-1 1/2] FROM docker.io/library/debian:bookworm-slim@sha256:7b140f374b  0.0s
 => [builder 1/5] FROM docker.io/library/golang:1.22-bookworm@sha256:3d699e4d15d0f8f13  0.0s
 => [internal] load build context                                                       0.0s
 => => transferring context: 1.08kB                                                     0.0s
 => CACHED [builder 2/5] WORKDIR /src                                                   0.0s
 => CACHED [builder 3/5] COPY go.mod .                                                  0.0s
 => [builder 4/5] COPY main.go .                                                        0.1s
 => [builder 5/5] RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /cpu-mem-hog   19.4s
 => [stage-1 2/2] COPY --from=builder /cpu-mem-hog /usr/local/bin/cpu-mem-hog           0.1s
 => exporting to image                                                                  0.1s
 => => exporting layers                                                                 0.1s
 => => writing image sha256:79c265dabc62ab96d54ec885212c6e6efbd1c908fcd0d12e014634c4fa  0.0s
 => => naming to docker.io/library/cpu-mem-hog:local                                    0.0s

```

### Deployment.yaml 작성

쿠버네티스 Pod를 만들 yaml을 작성한다.

cpu-mem-hog.yaml

```
bash
cat > cpu-mem-hog.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cpu-mem-hog
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cpu-mem-hog
  template:
    metadata:
      labels:
        app: cpu-mem-hog
    spec:
      terminationGracePeriodSeconds: 10
      containers:
        - name: cpu-mem-hog
          image: cpu-mem-hog:local
          imagePullPolicy: Never
          resources:
            requests:
              cpu: "250m"
              memory: "128Mi"
            limits:
              cpu: "1"
              memory: "256Mi"
EOF
```

이미지를 외부 registry에 올리지 않고 Minikube안에 직접 빌드하기 위해 쿠버네티스가 Docker Hub에서 이미지를 찾지 않도록 imagePullPolicy:Never 옵션을 설정한다.

다음은 핵심인 resource 설정이다.

```

resources:
  requests:
    cpu: "250m"
    memory: "128Mi"
  limits:
    cpu: "1"
    memory: "256Mi"

```

request.cpu: 250m —→ 스케쥴링 시 최소 0.25 core 필요하다고 선언

limits.cpu: 1 ——> 컨테이너가 최대 1 core까지만 사용할 수 있다고 선언

request.memory: 128Mi ——> 스케쥴링 시 최소 128Mi 필요하다고 선언.

limits.memory: 256Mi ——→ 컨테이너가 256Mi를 넘으면 OOMkilled 가능.

### Deployment 배포

k apply -f cpu-mem-hog.yaml

rollout 상태 확인

k rollout status deploy/cpu-mem-hog —timeout=60s

pod 상태 확인

k get pods -l app=cpu-mem-hog -o wide

```
NAME                           READY   STATUS    RESTARTS   AGE   IP             NODE
cpu-mem-hog-66859c8595-frwzn   1/1     Running   0          4s    10.244.0.102   minikube
```

### 로그로 메모리 증가 및 OOMkilled 확인

k logs -f deploy/cpu-mem-hog

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k logs -f deploy/cpu-mem-hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Allocated 10 MB of memory, total chunks=1
Allocated 10 MB of memory, total chunks=2
Allocated 10 MB of memory, total chunks=3
Allocated 10 MB of memory, total chunks=4
Allocated 10 MB of memory, total chunks=5
Allocated 10 MB of memory, total chunks=6
Allocated 10 MB of memory, total chunks=7
Allocated 10 MB of memory, total chunks=8
Allocated 10 MB of memory, total chunks=9
Allocated 10 MB of memory, total chunks=10
Allocated 10 MB of memory, total chunks=11
Allocated 10 MB of memory, total chunks=12
Allocated 10 MB of memory, total chunks=13
Allocated 10 MB of memory, total chunks=14
Allocated 10 MB of memory, total chunks=15
Allocated 10 MB of memory, total chunks=16
Allocated 10 MB of memory, total chunks=17
Allocated 10 MB of memory, total chunks=18
Allocated 10 MB of memory, total chunks=19
Allocated 10 MB of memory, total chunks=20
Allocated 10 MB of memory, total chunks=21
Allocated 10 MB of memory, total chunks=22
Allocated 10 MB of memory, total chunks=23
Allocated 10 MB of memory, total chunks=24
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ %
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ %
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ %

(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k get pods
NAME                           READY   STATUS      RESTARTS         AGE
cpu-mem-hog-66859c8595-frwzn   0/1     OOMKilled   12 (5m44s ago)   42m
nginx-56c45fd5ff-7l49n         1/1     Running     9 (13d ago)      54d
```

chunks=24는 24 chunks * 10MiB = 240MiB를 직접 할당했다는 뜻이다. 그런데 컨테이너의 실제 메모리 사용량은

이보다 조금 더 크다. Go runtime, heap metadata, goroutine stack, base image overhead등이 같이 들어가기 때문이다.

10번을 넘게 시도해보았는데 모두 24번째에서 모두 OOMKilled가 발생했다. 명확히 의도한대로 동작했다.

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % kubectl describe pod -l app=cpu-mem-hog
Name:             cpu-mem-hog-66859c8595-frwzn
Namespace:        default
Priority:         0
Service Account:  default
Node:             minikube/192.168.49.2
Start Time:       Wed, 22 Jul 2026 16:32:34 +0900
Labels:           app=cpu-mem-hog
                  pod-template-hash=66859c8595
Annotations:      <none>
Status:           Running
IP:               10.244.0.102
IPs:
  IP:           10.244.0.102
Controlled By:  ReplicaSet/cpu-mem-hog-66859c8595
Containers:
  cpu-mem-hog:
    Container ID:   docker://32825f1bf218f7795e85d3541aa6aa384171c1ccfb5fba6c882dc1cfd388550d
    Image:          cpu-mem-hog:local
    Image ID:       docker://sha256:bc6a4023ab4ea8c58928f9b4a8ef4fd8701ecb68e2929c0e1270b343cc699cf4
    Port:           <none>
    Host Port:      <none>
    State:          Waiting
      Reason:       CrashLoopBackOff
    Last State:     Terminated
      Reason:       OOMKilled
      Exit Code:    137
      Started:      Wed, 22 Jul 2026 18:44:24 +0900
      Finished:     Wed, 22 Jul 2026 18:44:55 +0900
    Ready:          False
    Restart Count:  28
    Limits:
      cpu:     1
      memory:  256Mi
    Requests:
      cpu:        250m
      memory:     128Mi
    Environment:  <none>
    Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-pj7ck (ro)
Conditions:
  Type                        Status
  PodReadyToStartContainers   True
  Initialized                 True
  Ready                       False
  ContainersReady             False
  PodScheduled                True
Volumes:
  kube-api-access-pj7ck:
    Type:                    Projected (a volume that contains injected data from multiple sources)
    TokenExpirationSeconds:  3607
    ConfigMapName:           kube-root-ca.crt
    Optional:                false
    DownwardAPI:             true
QoS Class:                   Burstable
Node-Selectors:              <none>
Tolerations:                 node.kubernetes.io/not-ready:NoExecute op=Exists for 300s
                             node.kubernetes.io/unreachable:NoExecute op=Exists for 300s
Events:
  Type     Reason   Age                     From     Message
  ----     ------   ----                    ----     -------
  Normal   Created  13m (x27 over 134m)     kubelet  Container created
  Warning  BackOff  2m54s (x109 over 133m)  kubelet  Back-off restarting failed container cpu-mem-hog in pod cpu-mem-hog-66859c8595-frwzn_default(547207f2-b6f5-434c-adb9-987491fb471f)
```

1. memory 계속 증가

1. OOMKilled

1. Deployment가 pod 재시작

1. 다시 OOMKilled

1. CrashLoopBackOff

Exit Code 137도 외워두면 좋을 것 같다. 여기서 9는 SIGKILL을 의미한다. 프로세스가 정상 종료된것이 아닌 kill 되었다는 뜻이다.

컨테이너가 죽은 이전 로그를 보고 싶다면 -p 옵션을 사용한다.

k logs -p deploy/cpu-mem-hog

그러면 memory limit을 늘려서 한번더 확인해보자. 예상대로라면 대략 50 mib가 할당되면 OOMKilled가 발생해야 한다.

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro cpu-mem-hog % k logs -f deploy/cpu-mem-hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Started a CPU hog
Allocated 10 MB of memory, total chunks=1
Allocated 10 MB of memory, total chunks=2
Allocated 10 MB of memory, total chunks=3
Allocated 10 MB of memory, total chunks=4
Allocated 10 MB of memory, total chunks=5
Allocated 10 MB of memory, total chunks=6
Allocated 10 MB of memory, total chunks=7
Allocated 10 MB of memory, total chunks=8
Allocated 10 MB of memory, total chunks=9
Allocated 10 MB of memory, total chunks=10
Allocated 10 MB of memory, total chunks=11
Allocated 10 MB of memory, total chunks=12
Allocated 10 MB of memory, total chunks=13
Allocated 10 MB of memory, total chunks=14
Allocated 10 MB of memory, total chunks=15
Allocated 10 MB of memory, total chunks=16
Allocated 10 MB of memory, total chunks=17
Allocated 10 MB of memory, total chunks=18
Allocated 10 MB of memory, total chunks=19
Allocated 10 MB of memory, total chunks=20
Allocated 10 MB of memory, total chunks=21
Allocated 10 MB of memory, total chunks=22
Allocated 10 MB of memory, total chunks=23
Allocated 10 MB of memory, total chunks=24
Allocated 10 MB of memory, total chunks=25
Allocated 10 MB of memory, total chunks=26
Allocated 10 MB of memory, total chunks=27
Allocated 10 MB of memory, total chunks=28
Allocated 10 MB of memory, total chunks=29
Allocated 10 MB of memory, total chunks=30
Allocated 10 MB of memory, total chunks=31
Allocated 10 MB of memory, total chunks=32
Allocated 10 MB of memory, total chunks=33
Allocated 10 MB of memory, total chunks=34
Allocated 10 MB of memory, total chunks=35
Allocated 10 MB of memory, total chunks=36
Allocated 10 MB of memory, total chunks=37
Allocated 10 MB of memory, total chunks=38
Allocated 10 MB of memory, total chunks=39
Allocated 10 MB of memory, total chunks=40
Allocated 10 MB of memory, total chunks=41
Allocated 10 MB of memory, total chunks=42
Allocated 10 MB of memory, total chunks=43
Allocated 10 MB of memory, total chunks=44
Allocated 10 MB of memory, total chunks=45
Allocated 10 MB of memory, total chunks=46
Allocated 10 MB of memory, total chunks=47
Allocated 10 MB of memory, total chunks=48
Allocated 10 MB of memory, total chunks=49
Allocated 10 MB of memory, total chunks=50
```

정확히 50번 반복후에 OOMKilled가 발생하고 deployment가 5번째 재시작을 했다는것을 확인할 수 있다.

```
Containers:
  cpu-mem-hog:
    Container ID:   docker://a3efaa3799e9c713eb490fbe0e58e5dc1d54bf49d87747695a6735543098f09a
    Image:          cpu-mem-hog:local
    Image ID:       docker://sha256:bc6a4023ab4ea8c58928f9b4a8ef4fd8701ecb68e2929c0e1270b343cc699cf4
    Port:           <none>
    Host Port:      <none>
    State:          Running
      Started:      Wed, 22 Jul 2026 19:03:18 +0900
    Last State:     Terminated
      Reason:       OOMKilled
      Exit Code:    137
      Started:      Wed, 22 Jul 2026 19:00:52 +0900
      Finished:     Wed, 22 Jul 2026 19:01:57 +0900
    Ready:          True
    Restart Count:  5
    Limits:
      cpu:     1
      memory:  512Mi
    Requests:
      cpu:        250m
      memory:     128Mi
```

### 최종 정리 

1. Go 프로그램이 CPU hog goroutine을 CPU 개수만큼 생성했다.

1. 동시에 1초마다 10MiB씩 메모리를 할당했다.

1. 쿠버네티스 Deployment에 memory limit 256Mi를 선언 및 배포

1. 프로그램은 약 24~25 chunks 근처까지 메모리를 할당함

1. 컨테이너는 memory limit을 넘고 OOMKilled.

1. Deployment Controller가 이를 감지하고 계속 재시작. 

1. 반복 실패 후 Pod의 상태는 CrashLoopBackOff.