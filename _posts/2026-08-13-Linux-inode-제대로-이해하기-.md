---
title: "Linux inode 제대로 이해하기
"
date: "2026-08-13T02:56:13.594Z"
categories:
  - "inode"
  - "file"
  - "block"
author: "현제 김_7254"
slug: "linux_inode_제대로_이해하기"
---

### 파일 이름, 데이터, 하드 링크와 심볼릭 링크는 어떻게 연결되는가

Linux에서 inode를 자주 접하게 된다.

```
ls -i
stat file.txt
df -i
```

리눅스와 유닉스에서는 시스템, 설정, 애플리케이션, 네트워크 입출력 모두 파일로 관리된다. 그리고 이 파일들은 inode 와 block으로 구성되며 inode번호로 같은 파일을 여러 파일이 참조하게 만들수도 있다.

먼저 이 글에서는 아래의 질문에 대해서 답할 수 있어야 한다.

1. inode의 메타 정보에는 어떤것들이 포함되어 있는가?

1. rm file.txt를 하면 실제 데이터가 즉시 삭제될까?

1. 하드 링크는 어떻게 서로 다른  이름으로 같은 파일을 가리킬까?

1. 심볼릭 링크와 하드링크의 본질적인 차이는 무엇인가?

1. 파일을 삭제했는데 프로세스가 계속 파일을 사용할 수 있는 이유는 무엇일까?

1. 디스크 공간은 남았는데 No space left on device가 뜨는 이유는 무엇인가?

## 1. 우리가 말하는 파일은 여러 객체의 조합이다.

사용자는 다음과 같은것을 파일이라고 생각한다.

report.txt, app.py, engine.c, index.html 등등

하지만 파일 시스템 내부에서는 파일 이름과 파일 메타데이터, 실제 내용이 분리된다.

```
report.txt 
     ↓
Directory Entry
"report.txt" -> inode 42137
     ↓
 inode 42137
     ↓
Data Block
```

파일 이름은 디렉토리 안에 존재하는 이름이고, 그 이름이 특정 inode number와 연결된다. inode는 다시 파일의 메타데이와 실제 데이터 위치를 관리한다. 이 구분이 inode를 이해하는 출발점이다.

## 2. ext4 파일 시스템을 큰 구조에서 먼저 보자.

Linux에서 흔히 사용하는 ext4를 단순화하면 여러 개의 Block Group으로 구성된다고 볼 수 있다.

```
ext4 filesystem
        │
        ├── Superblock
        │
        ├── Group Descriptor
        │
        ├── Block Bitmap
        │
        ├── Inode Bitmap
        │
        ├── Inode Table
        │
        └── Data / Extent Blocks
```

Superblock은 파일 시스템 전체에 대한 중요한 메타데이터를 가진다. Inode Bitmap은 inode사용 여부를 추적하d고, Block Bitmap은 데이터 블록의 사용 여부를 추적한다.

!/assets/image_5cf249b0-0331-4054-aebc-627db773b0e8.png

그림1. ext4 파일시스템의 고수준 배치

!/assets/image_5cf249b0-0331-4054-aebc-627db773b0e8.png

그림2. inode 참조관계 구조

여기서 중요한 것은 inode와 실제 데이터 블록의 별도의 영역이 관리된다는 점이다.

inode의 대표적인 정보들은 다음과 같다.

- inode number : inode 고유 식별 번호

- FIle Type : 파일의 유형

- Permission : 파일의 권한 

- UID : 파일 소유자 아이디를 나타낸다

- GID : 파일 소유자의 그룹 아이디를 나타낸다. 

- FIle Size : 파일 크기(bytes)를 나타낸다.

- Link Count : 이 아이노드에 대한 참조 수를 나타낸다.

- atime : 마지막으로 이 파일에 접근한 시간

- mtime : ?

- ctime : 마지막으로 이 파일을 수정한 시간

- Extent / Block Mapping 

```
17274999 drwxr-xr-x.   6 root root    77 2024-01-23 23:19 NetworkManager
17666743 drwxr-xr-x.   3 root root    18 2026-08-10 11:04 alsa
 1127255 drwxr-xr-x.   2 root root     6 2024-04-26 23:44 binfmt.d
  773454 lrwxrwxrwx.   1 root root    10 2026-07-10 06:02 cpp -> ../bin/cpp
50332584 drwxr-xr-x.   9 root root   109 2026-08-10 11:03 cups
16777355 drwxr-xr-x.   4 root root    76 2026-08-10 10:59 debug
17151887 drwxr-xr-x.   4 root root  4096 2026-08-10 11:02 dracut
52442495 drwxr-xr-x.   2 root root    33 2026-08-10 11:02 environment.d
50742568 drwxr-xr-x.   8 root root    97 2026-08-10 10:59 firewalld
50366260 drwxr-xr-x. 101 root root 16384 2026-08-10 11:04 firmware
17190084 drwxr-xr-x.   3 root root    19 2026-08-10 11:00 fontconfig
33900919 dr-xr-xr-x.   2 root root     6 2021-08-10 05:40 games
53627490 drwxr-xr-x.   3 root root    33 2026-08-11 21:17 gcc
34723552 drwxr-xr-x.   3 root root    21 2026-08-10 11:01 grub
  751203 drwxr-xr-x.   6 root root    76 2026-08-10 10:59 kbd
52679373 drwxr-xr-x.   2 root root    79 2026-08-10 11:03 kdump
52406822 drwxr-xr-x.   3 root root    43 2026-08-10 11:02 kernel
50768832 drwxr-xr-x.   5 root root   106 2026-07-30 03:33 locale
     190 drwxr-xr-x.   2 root root    89 2026-08-10 11:02 modprobe.d
  754248 drwxr-xr-x.   3 root root    35 2026-08-10 11:02 modules
17119475 drwxr-xr-x.   2 root root    81 2026-08-10 11:03 modules-load.d
  754236 -rw-r--r--.   1 root root     0 2024-02-07 17:40 motd
  754237 drwxr-xr-x.   2 root root     6 2024-02-07 17:40 motd.d
33688858 drwxr-xr-x.   5 root root    69 2026-08-10 10:57 mozilla
  754231 -rw-r--r--.   1 root root   389 2024-03-21 02:58 os-release
34495929 drwxr-xr-x.   2 root root    55 2026-08-10 11:03 ostree
 1127264 drwxr-xr-x.   2 root root    26 2026-08-10 11:02 pam.d
 1118701 drwxr-xr-x.   2 root root    50 2026-08-10 11:02 polkit-1
52256572 drwxr-xr-x.   3 root root    27 2026-08-10 11:00 python3.9
 2006147 drwxr-xr-x.   2 root root    60 2026-08-10 11:03 realmd
17053390 drwxr-xr-x.   6 root root  4096 2026-08-10 11:03 rpm
  754232 drwxr-xr-x.   2 root root   181 2026-08-10 11:02 sysctl.d
17062418 drwxr-xr-x.   2 root root     6 2021-08-10 05:40 sysimage
17062406 drwxr-xr-x.  15 root root  4096 2026-08-10 11:04 systemd
17232988 drwxr-xr-x.   2 root root  4096 2026-08-10 11:15 sysusers.d
16787498 drwxr-xr-x.   2 root root  4096 2026-08-10 11:15 tmpfiles.d
 2007735 drwxr-xr-x.  17 root root  4096 2026-08-10 11:04 tuned
33865523 drwxr-xr-x.   4 root root  4096 2026-08-10 11:04 udev

```

!/assets/image_5cf249b0-0331-4054-aebc-627db773b0e8.png

```
-rw-r--r--.  1  root  root  system_u:object_r:passwd_file_t:s0  2304  2026-08-12 15:23  /etc/passwd
│            │   │     │    │                                    │        │             │
│            │   │     │    │                                    │        │             └─ 파일명
│            │   │     │    │                                    │        └─ 수정 시간
│            │   │     │    │                                    └─ 파일 크기
│            │   │     │    └─ SELinux Security Context
│            │   │     └─ 소유 Group
│            │   └─ 소유 User
│            └─ Hard Link 수
└─ 파일 종류 + Unix Permission
```

- 필드 정보 해석

1. 첫번째 -는 파일 종류(디렉토리라면 d, 심볼릭 링크라면 1, 그 뒤 9비트 

```
rw-r--r--. 
│  │  │  │ ---> RHEL,CentOS의ls . 표시는 SELinux security context 확장 보안정보 
│  │  └── other = r-- 4
│  └───── group = r-- 4
└──────── owner = rw- 6
```

1. 1 — Hard Link Count

```
-rw-r--r--. 1 
```

여기서 1은 이 inode를 가리키는 hard link 수

개념적으로

```
filename ---> directory entry ---> inode
```

현재 /etc/passwd의 inode를 가리키는 directory entry가 1개라는 뜻이다.

ls -li /etc/passwd

1. 첫번째 root - Owner

```
1 root root 
  └──┘
  Owner
```

파일의 소유 사용자. indoe 내부에는 실제로 문자열 root가

저장되는게 아니라 UID가 저장된다.