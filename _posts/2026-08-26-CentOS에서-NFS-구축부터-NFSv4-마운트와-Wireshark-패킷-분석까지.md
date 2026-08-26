---
title: "CentOS에서 NFS 구축부터 NFSv4 마운트와 Wireshark 패킷 분석까지"
date: "2026-08-26T12:41:18.326Z"
categories:
  - "linux"
  - "nfs"
  - "rpc"
author: "현제 김_7254"
slug: "centos에서_nfs_구축부터_nfsv4_마운트와_wireshark_패킷_분석까지"
---

# 

## 1. 들어가며

리눅스 서버를 운영하다 보면 여러 서버에서 동일한 파일을 공유해야 하는 상황이 자주 발생한다. 이때 대표적으로 사용하는 기술 중 하나가 NFS(Network File System)다.

이번 실습에서는 CentOS Stream 9 환경에서 NFS 서버를 구성하고, 다른 CentOS 클라이언트에서 NFS 공유 디렉터리를 마운트한다. 이후 /etc/fstab을 이용한 부팅 시 자동 마운트까지 구성하고, 마지막으로 Wireshark를 이용해 실제 NFS 통신이 rpc 기반으로 동작하는것을 확인하는것을 목표로 한다.

전체적인 실습 흐름은 다음과 같다.

```
NFS Server
    ↓
/etc/exports
    ↓
exportfs
    ↓
NFS Client
    ↓
showmount
    ↓
mount
    ↓
/etc/fstab
    ↓
NFSv4
    ↓
TCP/2049
    ↓
Wireshark 패킷 분석
```

---

# 2. 실습 환경

이번 실습은 VMware 기반 가상 머신 환경에서 진행하였다.

### NFS Server

```
Hostname : Server1
IP       : 192.168.2.203
OS       : CentOS Stream 9
Role     : NFS Server
```

### NFS Client

```
Hostname : Client1
IP       : 192.168.2.201
OS       : CentOS Stream 9
Role     : NFS Client
```

구성은 다음과 같다.

```
┌─────────────────────┐
│      Client1        │
│   192.168.2.201     │
│                     │
│    /mnt/nfs1        │
└──────────┬──────────┘
           │
           │ NFSv4 
           │ TCP/2049
           ▼
┌─────────────────────┐
│      Server1        │
│   192.168.2.203     │
│                     │
│   /test/share1      │
│   /test/share2      │
└─────────────────────┘
```

---

# 3. NFS란?

NFS(Network File System)는 네트워크를 통해 다른 시스템의 디렉터리를 마치 로컬 디렉터리처럼 사용할 수 있도록 해주는 파일 시스템 프로토콜이다.

예를 들어 서버에 다음 디렉터리가 있다고 하자.

```
Server1

/test/share1
```

이를 Client1에서:

```
/mnt/nfs1
```

에 마운트하면 Client1에서는:

```
ls /mnt/nfs1
```

처럼 접근할 수 있다.

하지만 실제 데이터는 Client1의 로컬 디스크가 아니라 Server1의:

```
/test/share1
```

에 존재한다.

구조적으로 보면 다음과 같다.

```
Client1

/mnt/nfs1
    │
    │ NFS request (rpc)
    ▼
Network
    │
    ▼
Server1

/test/share1
```

따라서 /mnt/nfs1은 단순한 디렉터리가 아니라 원격 파일 시스템이 연결되는 mount point가 된다.

---

# 4. NFS 서버에 패키지 설치

먼저 Server1에서 NFS 관련 패키지를 설치한다.

```
dnf install -y nfs-utils
```

설치된 파일을 확인.

```
rpm -ql nfs-utils
```

설치 과정에서 다음과 같은 매뉴얼 파일과 도구들을 확인할 수 있다.

```
/usr/share/man/man8/rpc.nfsd.8.gz
/usr/share/man/man8/rpc.statd.8.gz
/usr/share/man/man8/showmount.8.gz
/usr/share/man/man8/statd.8.gz
```

여기서 중요한 점은 nfs-utils.service 자체를 실제 NFS 서버 데몬으로 이해하면 안 된다는 것이다.

실제 NFS 서버 서비스를 확인할 때는 다음 명령을 사용한다.

```
systemctl status nfs-server
```

NFS 서버를 시작한다.

```
systemctl enable --now nfs-server
```

확인:

```
systemctl status nfs-server
```

> 

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

그림1. systemctl status nfs-server 실행 결과

---

# 5. nfs-utils.service와 nfs-server.service의 차이

실습 중 다음 명령을 실행했을 때:

```
systemctl status nfs-utils
```

다음과 같은 결과가 나타날 수 있다.

```
nfs-utils.service - NFS server and client services
Loaded: loaded (...)
Active: active (exited)
Process: ExecStart=/bin/true
```

처음 보면 NFS가 실행되고 있다고 생각하기 쉽다.

하지만 ExecStart=/bin/true라는 부분을 보면 이 서비스가 실제로 장시간 실행되는 데몬이 아니라는 것을 알 수 있다.

즉,

```
systemctl start nfs-utils
        ↓
/bin/true
        ↓
exit 0
```

형태로 종료된다.

실제 NFS 서버를 실행하는 서비스는:

```
systemctl status nfs-server
```

이다.

NFS 서버를 구성할 때는 nfs-utils.service의 상태보다 nfs-server.service의 상태를 확인하는 것이 중요하다.

---

# 6. NFS 공유 디렉터리 생성

Server1에서 공유할 디렉터리를 만든다.

```
mkdir -p /test/share1
mkdir -p /test/share2
```

확인:

```
ls -ld /test/share*
```

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

---

# 7. /etc/exports 설정

NFS 서버에서 가장 중요한 설정 파일 중 하나가 /etc/exports이다.

이번 실습에서는 Client1의 IP가:

```
192.168.2.201
```

이므로 다음과 같이 설정하였다.

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

각 필드를 보면:

```
/test/share1
```

공유할 서버 디렉터리이다.

```
192.168.2.201
```

NFS 접근을 허용할 클라이언트 IP이다.

```
rw
```

읽기와 쓰기를 모두 허용한다.

```
sync
```

또한 sync 옵션은 기본값이며 서버가 데이터를 동기적으로 처리하도록 한다.

---

# 8. export 설정 반영

/etc/exports를 수정한 뒤에는 다음 명령으로 설정을 반영한다.

```
systemctl restart /etc/exportfs
```

현재 export 상태를 확인한다.

```
exportfs -v
```

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

---

# 9. Client1에서 NFS export 확인

Client1에서 Server1의 export 목록을 조회한다.

```
showmount -e 192.168.2.203
```

실습 환경에서는 다음과 같은 결과를 확인할 수 있었다.

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

Server1이

```
/test/share1
/test/share2
```

를 export하고 있으며,

```
192.168.2.201
```

클라이언트가 접근 가능한 대상으로 설정되어 있음을 확인할 수 있기 때문이다.

---

# 10. Client1의 mount point 생성 및 수동 마운트

NFS를 마운트하려면 먼저 로컬 mount point가 필요하다.

Client1에서 다음 명령을 실행한다.

```
mount -t nfs 192.168.2.203:/test/share1 /mnt/nfs1
```

두 번째 공유도 마운트 실행.

```
mount -t nfs 192.168.2.203:/test/share2 /mnt/nfs2
```

정상적으로 마운트되었는지 확인한다.

```
df -hT
```

마운트 결과 확인

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

즉 Client1이 Server1의 export를 NFSv4 파일 시스템으로 마운트한 상태이다.

---

# 11. NFS mount의 의미

/mnt/nfs1을 단순히 디렉터리라고 생각하면 NFS를 이해하기 어렵다.

mount 전에는:

```
Client1

/
└── mnt
    └── nfs1
```

이라는 단순한 로컬 디렉터리다.

mount가 완료되면:

```
Client1

/
└── mnt
    └── nfs1
          │
          │ NFS
          ▼
       Server1
       /test/share1
```

이 된다.

따라서:

```
echo "Hello NFS" > /mnt/nfs1/client-test.txt
```

라고 실행하면 로컬 SSD에 직접 저장하는 것이 아니라 NFS를 통해 Server1의:

```
/test/share1/client-test.txt
```

에 파일이 생성된다.

---

# 12. 실제 파일 읽기/쓰기 테스트

Client1:

```
echo "Hello from Client1" > /mnt/nfs1/client-test.txt
```

Server1:

```
cat /test/share1/client-test.txt
```

결과

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

반대로 Server1에서:

```
echo "Hello from Server1" > /test/share1/server-test.txt
```

Client1에서:

```
cat /mnt/nfs1/server-test.txt
```

실행하여 확인할 수 있다.

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

이 과정을 통해:

```
Client write
    ↓
NFS request
    ↓
Server filesystem
```

의 실제 동작을 확인할 수 있다.

---

# 13. /etc/fstab을 이용한 자동 마운트

수동 mount는 재부팅하면 사라질 수 있기 때문에 /etc/fstab에 설정을 추가한다.

Client1의 /etc/fstab에 다음과 같이 작성한다.

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

각 항목은 다음 의미를 가진다.

```
[원격 NFS 경로]
        ↓
192.168.2.203:/test/share1

[로컬 mount point]
        ↓
/mnt/nfs1

[파일 시스템 타입]
        ↓
nfs

[옵션]
        ↓
defaults,_netdev,vers=4

[Dump]
        ↓
0

[fsck]
        ↓
0
```

특히:

```
_netdev
```

는 해당 파일 시스템이 네트워크 기반임을 systemd에 알려주는 옵션이다.

따라서 부팅 과정에서 네트워크가 준비되기 전에 NFS mount를 시도하는 문제를 줄이는 데 도움이 된다.

---

# 14. mount -a로 fstab 테스트

/etc/fstab 수정 후에는 재부팅하지 않고 바로 테스트할 수 있다.

```
mount -a
```

오류가 발생하지 않았다면 mount 상태를 확인한다.

```
df -hT
```

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

또는

```
findmnt /mnt/nfs1
findmnt /mnt/nfs2
```

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

# 15. NFS의 네트워크 구조

이번 실습의 핵심 부분이다.

NFSv4에서는 기본적으로 NFS 서비스가 TCP/2049를 중심으로 동작한다.

구조는 다음과 같이 생각할 수 있다.

```
Client1
192.168.2.201
     │
     │ TCP
     │
     │ Destination Port 2049
     ▼
Server1
192.168.2.203
     │
     ▼
NFS Service
```

따라서 FTP 실습에서:

```
FTP
TCP/21
+
별도의 Data Connection
```

을 관찰했다면 NFSv4에서는:

```
NFS
TCP/2049
```

라는 구조를 비교해볼 수 있다.

다만 NFSv3에서는 rpcbind, mountd, statd, lockd 등 여러 RPC 서비스가 관여하기 때문에 포트 구조가 더 복잡해질 수 있다.

---

# 16. rpcbind와 NFS

NFS 관련 실습에서 자주 등장하는 서비스가 rpcbind다.

확인:

```
systemctl status rpcbind
```

RPC 서비스 목록:

```
rpcinfo -p localhost
```

NFS 환경에 따라 다음과 같은 서비스와 포트를 볼 수 있다.

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

NFSv4에서는 NFS 자체가 TCP/2049를 중심으로 통신하기 때문에 NFSv3보다 구조를 이해하기 쉽다.

---

# 17. Wireshark로 NFS 패킷 확인

이제 실제 네트워크 패킷을 확인한다.

Client1의 ens33 인터페이스를 기준으로 캡처할 경우:

```
tcpdump -i ens33 -nn -s 0 -w nfs.pcap
```

캡처를 시작한 상태에서 다른 터미널에서:

```
ls -l /mnt/nfs1
```

또는:

```
cat /mnt/nfs1/server-test.txt
```

을 실행한다.

실제 NFS 요청이 네트워크를 통해 발생하게 된다.

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

---

# 18. Wireshark 필터

Wireshark에서 먼저 다음 필터를 사용해본다.

```
ip.addr == 192.168.2.203 && tcp.port == 2049
```

이를 통해 Client1과 NFS Server 사이의 TCP/2049 트래픽을 확인할 수 있다.

또는:

```
tcp.port == 2049
```

만 사용해도 된다.

필터를 사용하여 NFS 프로토콜 패킷만 확인할 수 있다.

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

---

# 19. NFS 연결의 TCP 3-way handshake

Wireshark에서 NFS 연결을 처음 발생시키면 TCP handshake를 확인할 수 있다.

```
Client1                                           Server1
192.168.2.201                                     192.168.2.203:2049
    │                                                  │
    │                  최초 TCP 연결                  │
    │                                                  │
    │ ─────────────── SYN ───────────────────────────> │
    │ <──────────── SYN/ACK ───────────────────────── │
    │ ─────────────── ACK ───────────────────────────> │
    │                                                  │
    │              TCP ESTABLISHED                    │
    │══════════════════════════════════════════════════│
    │                                                  │
    │                    ls                            │
    │                     │                            │
    │                     ▼                            │
    │              NFS READDIR                         │
    │ ───────────── TCP Segment ─────────────────────>│
    │                                                  │
    │ <──────────── TCP Segment ──────────────────────│
    │              NFS READDIR Response                │
    │                     │                            │
    │                     ▼                            │
    │               파일 목록 출력                     │
    │                                                  │
    │                    cat                           │
    │                     │                            │
    │                     ▼                            │
    │                NFS READ                          │
    │ ───────────── TCP Segment ─────────────────────>│
    │                                                  │
    │ <──────────── TCP Segment ──────────────────────│
    │                 File Data                       │
    │                     │                            │
    │                     ▼                            │
    │                cat 화면 출력                     │
    │                                                  │
```

을 사용하여 NFS 통신이 진행된다.

여기서 중요한 점은 NFS 자체가 TCP 3-way handshake를 수행하는 것이 아니라, NFS가 TCP 위에서 동작하기 때문에 먼저 TCP 연결이 수립된다는 것이다.

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

---

---

# 20. NFS와 FTP 비교

이번 실습에서 앞서 진행한 FTP 실습과 비교하면 네트워크 파일 시스템의 특징이 훨씬 잘 보인다.

FTP에서는:

```
ftp
  ↓
get test.txt
  ↓
FTP command
  ↓
Data connection
```

이라는 구조라면,

NFS에서는:

```
cat /mnt/nfs1/test.txt
  ↓
Linux VFS
  ↓
NFS client
  ↓
NFS RPC
  ↓
Server
```

라는 차이가 있다.

---

# 21. NFS 실습에서 반드시 기억할 개념

### /etc/exports

NFS 서버가 어떤 디렉터리를 어떤 클라이언트에게 export할지 결정한다.

```
/test/share1 192.168.2.201(rw,sync)
```

### exportfs

현재 export 상태를 확인하고 반영한다.

```
exportfs -rav
exportfs -v
```

### showmount

NFS 서버의 export 목록을 확인한다.

```
showmount -e 192.168.2.203
```

### mount

원격 NFS 파일 시스템을 로컬 mount point에 연결한다.

```
mount -t nfs 192.168.2.203:/test/share1 /mnt/nfs1
```

### /etc/fstab

부팅 시 NFS를 자동 마운트하도록 설정한다.

### NFSv4

이번 실습에서는 NFSv4를 사용했고 기본적인 네트워크 통신은 TCP/2049를 중심으로 관찰할 수 있었다.

---

# 22. 최종 실습 흐름

이번 실습을 처음부터 다시 정리하면 다음과 같다.

```
[Server1]

dnf install nfs-utils
        ↓
mkdir /test/share1
        ↓
/etc/exports 설정
        ↓
exportfs -rav
        ↓
systemctl enable --now nfs-server
        ↓

[Client1]

showmount -e 192.168.2.203
        ↓
mkdir /mnt/nfs1
        ↓
mount -t nfs ...
        ↓
df -hT
        ↓
파일 read/write 테스트
        ↓
/etc/fstab 설정
        ↓
mount -a
        ↓
findmnt /mnt/nfs1
        ↓

[Wireshark]

TCP 3-way handshake
        ↓
TCP/2049
        ↓
NFSv4 request
        ↓
파일 접근
        ↓
NFS response
```

---

NFSv3에서는

```
rpcbind
TCP/UDP 111
        ↓
mountd
        ↓
nfsd
        ↓
statd
        ↓
lockd
```

등의 RPC 서비스가 추가로 등장할 수 있다.

따라서 통신구조는

```
NFSv4

Client
  │
  └──── TCP/2049 ────> Server


NFSv3

Client
  │
  ├──── RPC/111 ──────> Server
  │
  ├──── mountd ───────> Server
  │
  ├──── NFS ──────────> Server
  │
  └──── lock/stat ────> Server
```

처럼 훨씬 복잡한 통신 구조를 확인할 수 있다.

---

# 23. 마무리

이번 실습에서는 CentOS 환경에서 NFS 서버를 구성하고 특정 클라이언트만 공유 디렉터리에 접근하도록 설정하였다.

특히 다음 관계를 직접 확인했다.

```
/etc/exports
     ↓
exportfs
     ↓
showmount
     ↓
mount
     ↓
NFSv4
     ↓
TCP/2049
     ↓
/etc/fstab
```

또한 nfs-utils.service와 nfs-server.service의 차이를 확인하고, 실제 NFS 서버가 어떤 서비스에 의해 동작하는지도 확인했다.

가장 중요한 부분은 NFS를 단순히 "네트워크 드라이브처럼 사용하는 기능"으로 이해하지 않고,

```
Linux VFS
   ↓
NFS Client
   ↓
RPC/NFS
   ↓
TCP
   ↓
ens33
   ↓
Network
   ↓
NFS Server
   ↓
Server filesystem
```

이라는 실제 실행 및 네트워크 경로와 연결해서 이해하는 것이다.

특히 Wireshark를 이용하면 사용자가 단순히:

```
cat /mnt/nfs1/server-test.txt
```

라는 명령 하나를 실행했을 때에도 내부적으로 네트워크를 통해 NFS 요청과 응답이 발생한다는 사실을 직접 확인할 수 있다.

이를 FTP, NFS, HTTP 등의 프로토콜과 함께 비교하면 애플리케이션의 파일 접근이나 데이터 처리 과정이 TCP/IP 네트워크와 어떻게 연결되는지를 훨씬 깊게 이해할 수 있었다.

---

chroot는 특정 프로세스와 그 자식 프로세스가 바라보는 /를 다른 디렉터리로 변경하는 명령이며 테스트 환경·시스템 복구·부트로더 복구 등이 주요 사례가 될 수 있다.  GNU 문서 역시 정확히 chroot NEWROOT COMMAND 형태로 새로운 root에서 명령을 실행한다고 정의한다. 즉, 현재 있는 디렉토리를 기준으로 root 디렉토리를 재지정하는것이다.

## chroot 실습 가이드 — Server1 환경


```
Server1 실제 파일시스템

/                       <- 서버 입장에서 root 디렉토리 
├── bin
├── etc
├── usr
├── var
│   └── ftp
│
└── root
    └── jail             ← 우리가 만들 chroot 환경
        ├── bin
        │   ├── bash
        │   ├── ls
        │   └── cat
        ├── lib64
        ├── usr
        ├── etc
        ├── tmp
        └── proc

```

### 1. 현재 환경 확인

```
whoami
pwd
uname -r
cat /etc/os-release
chroot --version
```

현재 root인지 확인:

```
uid=0(root) gid=0(root) groups=0(root)
```

일반적으로 chroot()는 특권이 필요한 작업이며 GNU 문서도 많은 시스템에서 superuser 권한이 필요하다고 설명한다.

### 2. jail 디렉터리 생성

현재 root 계정에서는 $HOME이 /root이므로:

```
mkdir /root/jail
```

확인

```
ls -ld /root/jail
```

앞으로

```
/root/jail
```

을 새로운 /로 사용한다.

### 3. 디렉터리 구조 만들기

원문에서는 최소한 bin, lib64를 만듭니다.

우리는 뒤의 실습까지 고려해서 조금 더 만들어본다.

```
mkdir -p /root/jail/{bin,lib,lib64,etc,usr/bin,tmp,proc}
```

확인

```
find /root/jail -maxdepth 2 -type d
```

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

그림 1. /root/jail 하위 디렉토리

### 4. bash만 복사한다

원문처럼 먼저 bash를 복사합니다.

```
cp /bin/bash /root/jail/bin/
```

확인:

```
ls -lh /root/jail/bin/bash
```

이제 구조는:

```
/root/jail
└── bin
    └── bash
```

```
chroot /root/jail /bin/bash
```

그런데 여전히 다음처럼 실패할 가능성이 높습니다.

```
chroot: failed to run command '/bin/bash':
No such file or directory
```

여기서 아주 중요한 Linux 개념이 하나 나옵니다.

파일은 실제로 있는데 "No such file or directory"가 발생합니다.

https://wikidocs.net/299207

https://kkamji.net/posts/linux-cheat-sheet/

https://kkamji.net/posts/pod-graceful-shutdown/

### awk

awk '{print $2,  $3}'my.txt print 2nd & 3rd fields seperate by space

awk '{print $2, "," , $3}' print 2nd & 3rd field seperate by comma

awk '$2>100' my.txt print line where 2nd field is >100

awk '/error/' my.txt print line containing the word 'error'

awk '{sum}'

awk '{print $1, $NF}' print the number of filed in each line

awk '{}'

awk '{print substr($2,1,3)}' my.txt extract the substring from 2nd field

awk '$1 ~ /ERR/' my.log   print lines where 1st field matches pattern

awk. '$1 ~/^[0-9][a-z]+$' my.log print lines where 1st field is a numeri value

### FIles & directory

ls  : list directory contents

ls -l : list in long format

ls -lah: List all (hidden) in long format

less <file>

find <path> -name <name>

Process Management

ps -ef : Full format Listing

pgrep <name> : Find Process Id

nice -n 10 <cmd>

renice 10 -p <PID>

journalctl -u <svc>

### Networking

ip a : show all ip list

ip r : show routing table

ss -tulnp : List open ports & services

scp <src> <user@host>:<dest> : secure copy

ip addr add <ip><subnet> dev eth0

ip addr del <ip><subnet>

ip addr flush dev eth0

ip route show default

ip route

ip route get 1.1.1.1 : show a route matched with 1.1.1.1

ip route show 1.1.1.0/24 : show a route entry for 1.1.1.0/24 default via eth0

ip route add default via 192.168.0.1 dev eth0 : add the default gateway

ip route add/del 1.1.1.1/24 via 192.168.0.1 : add/remove a route entry via next hop

ip route replace 1.1.1.0/24 via 192.168.1.1 dev eth0 replace a route entry for 1.1.1.0/24

ip route add 1.1.1.0/24 via 192.168.1.1 dev eth0 metric 100

arp

ip neigh : display arp table

ip neigh show dev eth0: display arp entries for eth0 only

ip neigh del 192.168.0.2 dev eth0 : remove arp entry

ip neigh add 192.168.0.2 lladdr <mac-addr> dev eth0 nud permanent : add static arp entry

ip neigh change 192.168.0.2 lladdr <mac-addr> dev eth0 : updates an existing arp entry

ip neigh flush to <ip><subnet>

ip tunnel show

ip tunnel gre1 mode gre remote <remoteip> local <localip> ttl 255 create GRE Tunnel

### ip link: manage network interface

ip link show :  display all network interface

ip link show eth0: show detail on eth0

ip link set eth0 up, down

ip link set eth0 mtu 9000

ip link set eth0 promisc on

ip -s link show eth0 : show traffic stats

ip link set etho addr <change mac-address>

### System Log

dmesg  : Kernel Buffer ring

journalctl : View System Log

journalctl -xe : view log detail

tail -f /var/log/syslog : Follow syslog

tail -f /var/log/auth.log : Follow auth log

cat /etc/os-release : Show os information

lsblk : list block of device

### Archive & COMPRESSION

tar -cvf <f.tar> <dir> : create archive

tar -xvf <f.tar> : Extract tar archive

tar -czvf <f.tar.gz> : Extract tar.gz archive

zip -r <f.zip> : Create zip archive

unzip <f.zip> : Extract zip archive

gzip <file> : Compress file

gunzip <file> : decmpress file

### Text formatting

less <file>

head <file>

tail -f <file>

grep -r <pattern> <dir> : search recursive

awk '{print $1}' <file>

sed 's/old/new/g' <file>

sort <file>

uniq <file>

cut -d',' -f1 <file>

### docker 

doker ps -a

docker build -t <img>

docker logs <cid>

find . -name <file>

find . / -type d -name <dir> 
find. . -type d -name "dir name"

find . -type f -name "*.jpg|png|jpeg"

find . -type f -size +100M

find . -type f -size+100M-size-500M

find . -type f -mtime-1

find . -type g -perm 077

find . -type -f -ctime -2

find . -newermt "2024-01-01"!-newermt "2024-03-15"

이번 시간에는 가상 디스크 여러개를 소프트웨어 RAID로 구성하여 고가용성을 확보하는 실습을 진행해보겠습니다. RAID 구성에는 하드웨어 방식과 소프트웨어 방식이 존재하지만, 실습 구조 한계상 mdadm을 이용한 소프트웨어 RAID를 구축해보겠습니다. RAID는 스토리리에서 고가용성을 확보하기 위한 기술입니다. 하나의 디스크가 고장이 나더라도 전체 디스크에 장애가 나지않도록 운영하거나, 병렬 읽기로 인한 성능향상까지 도모할 수 있습니다. RAID에는 여러 종류가 있지만 이 글에서는 RAID5, RAID10, RAID 01을 집중적으로 다뤄보겠습니다.

## 1. 실습 목표

이번 실습을 끝내면 다음 흐름을 직접 확인할 수 있습니다.

1. 시스템 디스크와 RAID용 추가 디스크를 구분한다.

1. 추가 디스크에 Linux RAID 파티션을 만든다.

1. mkraid.sh로 /dev/md0 RAID 5를 생성한다.

1. /dev/md0에 XFS 파일시스템을 만들고 /raid5에 마운트한다.

1. /etc/fstab과 /etc/mdadm.conf를 점검해 재부팅 후 자동 복구를 검증한다.

1. 디스크 하나의 장애를 모의하고 데이터 무결성을 확인한다.

1. 교체 디스크를 추가해 RAID 5를 리빌드한다.

1. 마운트와 자동 마운트 설정을 해제한 뒤 RAID를 안전하게 삭제한다.

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

## 2. 실습 환경과 디스크 계획

현재 실습 환경의 기준은 다음과 같습니다.

실습에서는 VMware에 동일한 크기의 가상 디스크 4개를 추가합니다.

### RAID 5 용량 계산

동일한 크기 S의 디스크 N개로 RAID 5를 만들 때 이론상 사용 가능 용량은 다음과 같습니다.

```
RAID 5 사용 가능 용량 = (N - 1) × S
```

예를 들어 1GiB 디스크 3개라면 이론상 RAID 용량은 약 2GiB입니다.

```
(3 - 1) × 1GiB = 2GiB
```

실제 df 용량은 RAID 메타데이터, 파티션 정렬, XFS 메타데이터 때문에 이 값보다 조금 작게 표시됩니다.

## 3. RAID 아래와 위의 계층 구분하기

이번 실습의 저장 계층은 다음 순서로 구성됩니다.

```
/dev/sdb1 ─┐
/dev/sdc1 ─┼─ mdadm RAID 5 ── /dev/md0 ── XFS ── /raid5 ── 파일과 디렉터리
/dev/sdd1 ─┘
```

각 계층의 역할은 서로 다릅니다.

## 4. 실습 전 점검

### 4.1 운영체제와 블록 장치 확인

```
hostnamectl
cat /etc/os-release
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,UUID
df -hT
pvs
vgs
lvs
```

lsblk뿐 아니라 pvs, vgs, lvs도 확인하는 이유는 새 디스크처럼 보이는 장치가 기존 LVM PV로 사용 중일 수 있기 때문입니다.

> 실습 시작 전 시스템 정보

- 포함 명령: cat /etc/os-release

- 확인 포인트: 호스트명이 Client1인지, CentOS Stream 9 계열인지 표시

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

> RAID 생성 전 디스크 구조

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

- 포함 명령: lsblk, df -hT

- 확인 포인트: /dev/sda가 시스템 디스크이며 /dev/sdb~/dev/sde가 비어 있는 추가 디스크인지 표시

- 캡처 주의: 실제 디스크 이름과 크기가 모두 보이도록 터미널 폭 조정

### 4.2 대상 디스크가 사용 중인지 확인

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

```
for disk in /dev/sdb /dev/sdc /dev/sdd /dev/sde
do
    lsblk "$disk"
    findmnt -S "$disk" || true
done
```

다음 중 하나라도 해당하면 바로 진행하지 않습니다.

- 마운트 지점이 표시된다.

- FSTYPE에 기존 파일시스템이 표시된다.

- LVM의 PV, VG, LV로 사용 중이다.

- 기존 RAID의 구성원으로 조립되어 있다.

- 보존해야 할 데이터가 있다.

## 5. mdadm 설치와 서비스 상태 확인

mdadm은 Linux 커널의 MD(Multiple Devices) 기능을 구성하고 관리하는 사용자 공간 도구입니다. 실제 RAID I/O는 커널의 MD 계층이 처리하고, mdadm은 배열의 생성·조립·상태 변경·메타데이터 관리를 담당합니다.

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

## 6. 추가 디스크 파티션 준비

다음 명령은 /dev/sdb~/dev/sde의 기존 파티션 테이블을 새 GPT로 교체합니다. 보존할 데이터가 없는 실습용 디스크에서만 실행합니다.

```
for disk in /dev/sdb /dev/sdc /dev/sdd /dev/sde
do
    parted -s "$disk" mklabel gpt
    parted -s "$disk" mkpart primary 1MiB 100%
    parted -s "$disk" set 1 raid on
done

udevadm settle
```

결과를 확인합니다.

```
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS
parted -s /dev/sdb print
parted -s /dev/sdc print
parted -s /dev/sdd print
parted -s /dev/sde print
```

파티션 된 모습.

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

## 7. mkraid.sh의 역할과 실행 전 검사

이번 실습에 사용하는 mkraid.sh는 다음 두 기능을 제공합니다.

```
1) RAID 생성
   입력 수집 → mdadm --create → 배열 정보 저장

2) RAID 삭제
   구성원 검색 → mdadm --stop → 구성원 superblock 초기화
   → mdadm.conf의 ARRAY 항목 삭제
```

다만 다음 작업은 스크립트의 범위에 포함되지 않습니다.

- 디스크 파티션 생성

- 파일시스템 생성

- 마운트와 /etc/fstab 등록

- 디스크 장애·제거·교체·리빌드

- 삭제 전 마운트 해제와 /etc/fstab 정리

- 제거되어 현재 배열에 보이지 않는 디스크의 오래된 superblock 정리

따라서 스크립트만 실행하는 것이 아니라 이 글의 전후 절차를 함께 따라야 합니다.

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

### Partition → Filesystem → Mount → etc/fstab 까지

Linux 에서 새 디스크를 추가했다고 해서 바로

cd /dev/sdb

/dev/sdb는 Linux Kernel이 노출한 Block Device다.

실제로 파일을 저장하려면 그 위에 저장공간을 구성하고 Filesystem을 만든 뒤 Linux Directory  Tree에 연결해야 한다.

```
 Physical / Virtual Disk
           │
           ▼
    Partition Table
           │
           ▼
       Partition
           │
           ▼
       Mount Point
           │
           ▼
       Linux Directory Tree    
```

LVM을 사용하면 중간에 새로운 Storage Abstraction Layer가 들어간다.

```
Physical / Virtual Disk
        |
        PV
        |
        VG
        |
        LV
        | 
    File System 
        |
      Mount 
        |
     Linux Directory Tree
```

명령으로 표현하면 다음과 같다

```
/dev/sdb
    │ fdisk
    ▼
/dev/sdb1
    │ mkfs.ext4
    ▼   
ext4 filesystem
    │
    ▼
/data     
```

### 1. 실습 환경먼저 확인

새 디스크를 만들기 전에 현재 디스크 구조부터 확인한다.

실습전에 vmware 에서 가상디스크 sdb를 40mb 씩 총 4개를 할당한다.

```
sda   20G    ← CentOS 시스템 디스크
│
├─sda1  1G  /boot
└─sda2 19G
   ├─cs-root 17G /
   └─cs-swap  2G

sdb  204M    ← 실습 디스크
sdc  204M    ← 실습 디스크
sdd  204M
sde  204M
sdf  204M
sdg  204M
```

현재 /dev/sdb 에는 이미

```
sdb
├─sdb1 40M
├─sdb2 40M
├─sdb3 40M
└─sdb4 40M
```

가 존재한다. 여기서 우리가 만들 최종 구조는 다음과 같다.

```
/dev/sdb 204M
│
├── sdb1  40M   Primary
├── sdb2  40M   Primary
├── sdb3  40M   Primary
│
└── sdb4        Extended
     │
     ├── sdb5    5M Logical
     ├── sdb6    5M Logical
     ├── sdb7    5M Logical
     ├── sdb8    5M Logical
     ├── sdb9    5M Logical
     ├── sdb10   5M Logical
     ├── sdb11   5M Logical
     ├── sdb12   5M Logical
     ├── sdb13   5M Logical
     ├── sdb14   5M Logical
     └── sdb15   5M Logical

                 = Logical 11개


/dev/sdc 204M
│
└── sdc1        Extended
     │
     ├── sdc5    5M Logical
     ├── sdc6    5M Logical
     ├── sdc7    5M Logical
     └── sdc8    5M Logical

                 = Logical 4개


총 Logical Partition
11 + 4 = 15개
```

여기서 /dev/sdb4와 /dev/sdc1은 데이터를 저장하기 위한 일반 파티션이라기보다 Logical Partition을 담당하기 위한 Extended partition 컨테이너.

---

## 1. VMware에서 실습 디스크 준비

실습 시작 전 VMware에서 추가 virtua disk들을 연결한 상태.

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

그림1. VMware → VM Settings → Hard Disk 설정화면

lsblk

```
root@Client1 /root# lsblk
NAME        MAJ:MIN RM  SIZE RO TYPE MOUNTPOINTS
sda           8:0    0   20G  0 disk
├─sda1        8:1    0    1G  0 part /boot
└─sda2        8:2    0   19G  0 part
  ├─cs-root 253:0    0   17G  0 lvm  /
  └─cs-swap 253:1    0    2G  0 lvm  [SWAP]
sdb           8:16   0  204M  0 disk
├─sdb1        8:17   0   40M  0 part
├─sdb2        8:18   0   40M  0 part
├─sdb3        8:19   0   40M  0 part
└─sdb4        8:20   0   40M  0 part
sdc           8:32   0  204M  0 disk
sdd           8:48   0  204M  0 disk
sde           8:64   0  204M  0 disk
sdf           8:80   0  204M  0 disk
sdg           8:96   0  204M  0 disk
sr0          11:0    1  9.6G  0 rom
root@Client1 /root#


```

## 2. 디스크와 파티션의 차이부터 확인

현재

```
sdb    TYPE=disk
sdb1   TYPE=part
sdb2   TYPE=part
...
```

이다.

즉,

```
/dev/sdb
= 하나의 Block Device / Disk

/dev/sdb1
= sdb 안의 partition

/dev/sdb2
= sdb 안의 partition
```

따라서 현재 구조는

```
VMware Virtual Disk
        │
        ▼
Linux SCSI block device
        │
        ▼
     /dev/sdb
        │
   Partition Table
        │
 ┌──────┼──────┬──────┐
 ▼      ▼      ▼      ▼
sdb1   sdb2   sdb3   sdb4
40M    40M    40M    40M
```

## 3. / dev/sdb 의 정확한 Partition Table 확인

lsblk 는 구조 확인에는 좋지만 Primary, Extended  여부를 정확히 보려면 fdisk가 좋다

```
fdisk -l /dev/sdb

root@Client1 /root# fdisk -l /dev/sdb
Disk /dev/sdb: 204 MiB, 213909504 bytes, 417792 sectors
Disk model: VMware Virtual S
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
Disklabel type: dos
Disk identifier: 0xc5f48473

Device     Boot  Start    End Sectors Size Id Type
/dev/sdb1         2048  83967   81920  40M 83 Linux
/dev/sdb2        83968 165887   81920  40M 83 Linux
/dev/sdb3       165888 247807   81920  40M 83 Linux
/dev/sdb4       247808 329727   81920  40M 83 Linux
root@Client1 /root#

```

Id가 83 Linux 라면 일반 Linux primary/logical partition이고  5 extended라면 extended partition 이다.

## 4. MBR vs GPT 방식 

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

그림 2. MBR vs GPT partitioninig

MBR 방식은 기본적으로 Disk를 사용하기 위해 여러 프라이머리 파티션으로 나눈다. Primary 파티션은 총 4개까지 만들 수 있으며 확장 파티션은 다시 논리 파티션으로 12개로 나눌수 있다.

DOS/MBR partition table에는 기본 partition entry가 4개 있다.

그래서

```
Partition Entry #1
Partition Entry #2
Partition Entry #3
Partition Entry #4
```

까지만 직접 기록 가능. 이를 그대로 사용하면

```
sdb1 Primary
sdb2 Primary
sdb3 Primary
sdb4 Primary
```

그래서 네 번째 entry를 일반 partition으로 쓰지 않고 sdb4 = Extended로 만들 수 있다.

구조는 다음과 같다.

```
MBR
│
├── Entry 1 → sdb1 Primary
├── Entry 2 → sdb2 Primary
├── Entry 3 → sdb3 Primary
│
└── Entry 4 → sdb4 Extended
                │
                ├── sdb5 Logical
                ├── sdb6 Logical
                ├── sdb7 Logical
                └── ...
```

## 5. 첫 번째 파티션이 sector 2048에서 시작하는 이유

앞서 살펴본것처럼 fdisk 정렬에서는 첫 파티션이

Start = 2048

에 만들어지는 경우가 많다.

512-byte 기준

```
2048 x 512 bytes = 1Mib 
```

util-linux의 partiton alignment는 일반적으로 1Mib 단위의 grain을 사용해 partition을 정렬하는 기능을 사용.

즉, 2048바이트가 아니라 2048 sector라는점에 주의해야 할것.

## 6. 현재 공간 계산

현재 sdb

204M

이고 기존 Primary partition이 40M x 4 이다.

하지만 우리는

sdb1 40M

sdb2 40M

sdb3 40M

까지만 유지하고 sdb4를 다시 만들 것

앞쪽에서는 disk 전체가 약 204M이므로 대략

204M - 120M = 84M 정도가 남습니다.

실제로 1Mib alignment등을 고려하면 약 83 Mib 수존의 extended 영역을 기대할 수 있다.

우리가 /dev/sdb 에 만들 logical partition은 11 x 5mib = 55 mib 이므로 공간은 충분하다.

## 7. fdisk 실행

fdisk /dev/sdb

먼저 현재 상태를 확인

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png

그림 4. fdisk로 확인한 파티션 상태

## 8. sdb4를 Extended Partition으로 다시 생성

```
Command (m for help): n
```

DOS/MBR fdisk에서 다음과 비슷하게 나타난다.

```
Partition Type
	p  primary
	e  extended
```

선택 e

Partition number 4

First Selector: Default

그냥 Enter

```
sdb
│
├─sdb1 40M Primary
├─sdb2 40M Primary
├─sdb3 40M Primary
│
└─sdb4 Extended
     │
     └── 아직 비어 있음
```

## 9. 첫 Logical Partition 생성

```
Command (m for help): n
```

이미 primary slot 1 ~ 3과 extended slot4가 모두 사용되었으므로 현재 util-linux fdisk에서는 logical partition 생성 경로로 들어간다.

!/assets/image_7207950f-3f8e-4a31-837d-eb95bb7b1de9.png