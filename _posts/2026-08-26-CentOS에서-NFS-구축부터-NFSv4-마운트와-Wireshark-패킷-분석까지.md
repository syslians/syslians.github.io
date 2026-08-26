---
title: "CentOS에서 NFS 구축부터 NFSv4 마운트와 Wireshark 패킷 분석까지"
date: "2026-08-24T02:35:00.000Z"
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

![image](/assets/image_c9aa887c-4cbf-4012-b362-f3b470f5938b.png)

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

![image](/assets/image_455a1452-6b1c-454a-8f80-77bb9cba71dd.png)

---

# 7. /etc/exports 설정

NFS 서버에서 가장 중요한 설정 파일 중 하나가 /etc/exports이다.

이번 실습에서는 Client1의 IP가:

```
192.168.2.201
```

이므로 다음과 같이 설정하였다.

![image](/assets/image_f20d416e-8ba7-44de-8681-80beffe1d5f1.png)

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

![image](/assets/image_3d24247c-6c2e-4ab3-b2de-cccb1c2f758f.png)

---

# 9. Client1에서 NFS export 확인

Client1에서 Server1의 export 목록을 조회한다.

```
showmount -e 192.168.2.203
```

실습 환경에서는 다음과 같은 결과를 확인할 수 있었다.

![image](/assets/image_53a07cd3-313d-4bfa-a135-a59445fb928e.png)

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

![image](/assets/image_092c4cfa-e4e2-415a-a940-ca4e814a619b.png)

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

![image](/assets/image_a2c26255-a6a6-4b47-9c00-0a663de9fcda.png)

반대로 Server1에서:

```
echo "Hello from Server1" > /test/share1/server-test.txt
```

Client1에서:

```
cat /mnt/nfs1/server-test.txt
```

실행하여 확인할 수 있다.

![image](/assets/image_a7e2d1b4-1687-4d69-89cd-fc85e658c5c8.png)

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

![image](/assets/image_c790524c-dc67-4b37-bd97-258d91cf69ff.png)

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

![image](/assets/image_e8e8e9ea-27db-4320-a33b-7a240d723d7e.png)

또는

```
findmnt /mnt/nfs1
findmnt /mnt/nfs2
```

![image](/assets/image_d0d9d8a0-7f2b-41b7-b619-a2b1ccf3e388.png)

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

![image](/assets/image_4f598c02-8034-45d0-ab2f-aa715caecf5e.png)

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

![image](/assets/image_61377889-f5b2-4abf-8618-02da70bc2382.png)

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

![image](/assets/image_eab79e3b-0267-4a81-87f4-74131cc8fb35.png)

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

![image](/assets/image_2cfd6c9b-2c66-4bcd-97d6-f6c5d18adf56.png)

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