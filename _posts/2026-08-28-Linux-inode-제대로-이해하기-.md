---
title: "Linux inode 제대로 이해하기
"
date: "2026-08-28T14:01:39.549Z"
categories:
  - "inode"
  - "file"
  - "block"
author: "현제 김_7254"
slug: "linux_inode_제대로_이해하기"
---

### 파일 이름, 데이터, 하드 링크와 심볼릭 링크는 어떻게 연결되는가

Linux에서 inode를 이해하면 ls -i, stat, df -i, hard link, symbolic link, 그리고 파일 삭제 후에도 공간이 반환되지 않는 현상까지 하나의 흐름으로 설명할 수 있다.

이 글에서는 다음 질문에 답할 수 있어야 한다.

1. inode의 메타 정보에는 무엇이 포함되는가?

1. rm file.txt를 하면 실제 데이터가 즉시 삭제되는가?

1. 하드 링크는 어떻게 서로 다른 이름으로 같은 파일을 가리키는가?

1. 심볼릭 링크와 하드 링크의 본질적인 차이는 무엇인가?

1. 삭제된 파일을 프로세스가 계속 사용할 수 있는 이유는 무엇인가?

1. 디스크 공간은 남았는데 No space left on device가 발생할 수 있는 이유는 무엇인가?

---

## 1. 우리가 말하는 파일은 여러 객체의 조합이다

사용자는 report.txt, app.py, engine.c, index.html처럼 파일 이름을 중심으로 파일을 인식한다. 하지만 파일시스템 내부에서는 파일 이름, inode, 실제 데이터 블록이 분리되어 관리된다.

```
report.txt
   ↓
Directory Entry
"report.txt" → inode 42137
   ↓
inode 42137
   ↓
Data / Extent Blocks
```

파일 이름은 디렉터리 엔트리 안에 존재하고, 그 이름이 inode 번호를 참조한다. inode는 다시 파일의 메타데이터와 실제 데이터가 위치한 block/extent 정보를 가진다.

---

## 2. ext4 파일시스템을 큰 구조에서 먼저 보자

ext4를 단순화하면 여러 Block Group으로 구성된다.

```
ext4 filesystem
    ├── Superblock
    ├── Group Descriptor
    ├── Block Bitmap
    ├── Inode Bitmap
    ├── Inode Table
    └── Data / Extent Blocks
```

Superblock은 파일시스템 전체 정보를 관리하고, Inode Bitmap은 inode 사용 여부를, Block Bitmap은 데이터 블록의 사용 여부를 추적한다.

!/assets/image_8c028b82-3d4f-4f42-8f45-271c9def070e.png

그림 1. ext4 파일시스템의 고수준 배치

!/assets/image_8c028b82-3d4f-4f42-8f45-271c9def070e.png

그림 2. inode 참조 관계 구조

inode의 대표적인 정보는 다음과 같다.

- inode number: inode 고유 식별 번호

- file type: 일반 파일, 디렉터리, 심볼릭 링크 등

- permission: 파일 권한

- UID / GID: 소유 사용자와 그룹

- file size: 논리적 파일 크기

- link count: 해당 inode를 참조하는 hard link 수

- atime: 마지막 데이터 접근 시간

- mtime: 파일 내용이 마지막으로 수정된 시간

- ctime: inode 상태(metadata)가 마지막으로 변경된 시간. 생성 시간이 아니다.

- extent / block mapping: 파일 논리 영역과 실제 데이터 블록의 매핑 정보

---

## 3. 파일 하나를 만들고 inode를 직접 확인해보자

```
printf 'hello inode\n' > original.txt
ls -li original.txt
stat original.txt
```

!/assets/image_8c028b82-3d4f-4f42-8f45-271c9def070e.png

CLI 출력 — ls -li original.txt, stat original.txt

ls -li의 첫 번째 숫자가 inode 번호다. 위 예시에서는 1048583이 inode 번호다. 이 번호는 파일 이름 자체의 번호가 아니라 해당 파일시스템 내부에서 inode를 식별하는 번호다.

---

## 4. 하드 링크는 같은 inode를 공유한다

하드 링크를 만들면 새로운 inode를 생성하는 것이 아니라 기존 inode를 참조하는 새로운 directory entry가 만들어진다.

```
ln original.txt hardlink.txt
ls -li original.txt hardlink.txt
echo 'added by hardlink' >> hardlink.txt
cat original.txt
```

!/assets/image_8c028b82-3d4f-4f42-8f45-271c9def070e.png

CLI 출력 — 동일 inode 번호와 link count 2 확인

구조를 단순화하면 다음과 같다.

```
original.txt ─┐
              ├── inode 1048583 ──→ data blocks
hardlink.txt ─┘
```

두 파일 이름 모두 같은 inode를 참조하므로 어느 이름으로 내용을 수정해도 같은 데이터가 보인다. 그리고 inode의 link count는 1 → 2로 증가한다.

하드 링크는 일반적으로 서로 다른 파일시스템을 넘을 수 없다. 파일시스템마다 inode 번호 공간이 독립적이기 때문이다.

---

## 5. rm은 파일 내용을 즉시 지우는 명령이 아니라 이름을 unlink한다

original.txt와 hardlink.txt가 같은 inode를 가리키는 상태에서 original.txt만 삭제해보자.

```
rm original.txt
ls -li hardlink.txt original.txt
cat hardlink.txt
```

!/assets/image_8c028b82-3d4f-4f42-8f45-271c9def070e.png

CLI 출력 — rm original.txt 이후에도 hardlink.txt로 동일 데이터 접근

삭제 전:

```
original.txt ─┐
              ├── inode 1048583 ──→ data blocks
hardlink.txt ─┘
```

삭제 후:

```
hardlink.txt ───── inode 1048583 ──→ data blocks
```

즉 rm은 해당 directory entry와 inode의 연결을 끊는 unlink 동작으로 보는 것이 더 정확하다. 다른 hard link가 남아 있다면 inode와 데이터는 그대로 유지된다.

---

## 6. 심볼릭 링크는 inode를 공유하지 않고 경로 문자열을 저장한다

심볼릭 링크는 target 파일과 별도의 inode를 가진다.

```
printf 'symlink demo\n' > target.txt
ln -s target.txt symlink.txt
ls -li target.txt symlink.txt
rm target.txt
ls -l symlink.txt
cat symlink.txt
```

!/assets/image_8c028b82-3d4f-4f42-8f45-271c9def070e.png

CLI 출력 — symlink와 target의 서로 다른 inode 번호 확인

구조는 다음과 같다.

```
symlink.txt
   ↓
별도 inode
   ↓
"target.txt" 라는 경로 문자열
   ↓
target.txt의 inode
```

따라서 target이 삭제되면 symlink 자체는 남아 있지만 더 이상 실제 대상을 찾을 수 없는 dangling symbolic link가 된다.

---

## 7. 삭제된 파일을 프로세스가 계속 열고 있으면 디스크 공간이 반환되지 않는다

Linux에서 파일의 directory entry가 삭제되더라도 프로세스가 해당 inode에 대한 열린 file descriptor를 유지하고 있으면 데이터 블록은 즉시 해제되지 않는다.

```
printf 'log line\n' > app.log
tail -f app.log &
rm app.log
lsof +L1
```

!/assets/image_8c028b82-3d4f-4f42-8f45-271c9def070e.png

CLI 출력 — lsof +L1로 (deleted) 상태의 열린 파일 확인

이 상황에서 경로 이름은 사라졌지만 프로세스의 file descriptor는 해당 inode를 계속 참조한다.

```
Directory Entry → 삭제됨

Process FD ─────→ inode ─────→ data blocks
```

프로세스가 file descriptor를 닫거나 종료해야 최종적으로 inode와 데이터 블록이 해제될 수 있다.

운영 중 로그 파일은 단순히 rm으로 제거하기보다 서비스가 지원하는 log rotation 또는 reopen 절차를 사용하는 것이 안전하다. 대용량 로그를 지웠는데도 df -h가 줄지 않는다면 lsof +L1을 우선 확인할 수 있다.

---

## 8. df -h에 공간이 남아 있어도 inode가 고갈될 수 있다

파일 하나를 생성하려면 최소 하나의 inode가 필요하다. 아주 작은 파일을 대량으로 만들면 데이터 블록은 남아 있어도 inode가 먼저 소진될 수 있다.

!/assets/image_8c028b82-3d4f-4f42-8f45-271c9def070e.png

CLI 출력 — 블록 공간은 남아 있지만 inode가 100% 사용된 상황

위 상황에서는 df -h 기준으로 약 8.9GB가 남아 있지만 df -i의 IUse%가 100%다. 이 경우 새 파일을 만들 때도 No space left on device가 발생할 수 있다.

따라서 메일 큐, cache, session, 임시 파일, 빌드 산출물처럼 작은 파일이 대량 생성되는 환경에서는 다음 두 명령을 함께 보는 것이 좋다.

```
df -h
df -i
```

---

## 9. inode 개수를 확인하는 기본 명령

현재 파일시스템의 inode 통계를 확인한다.

```
df -i /
```

특정 파일의 inode 번호를 확인한다.

```
ls -li /etc/passwd
stat /etc/passwd
```

stat은 inode 번호뿐 아니라 권한, UID/GID, size, link count, atime/mtime/ctime, filesystem block size 등의 정보를 한 번에 확인할 수 있어서 inode 분석에 가장 유용한 명령 중 하나다.

---

## 10. atime, mtime, ctime을 실제로 비교해보자

파일의 내용 변경과 metadata 변경은 서로 다른 timestamp에 영향을 준다.

```
printf 'time demo\n' > time-test.txt
stat time-test.txt
cat time-test.txt
echo 'more' >> time-test.txt
chmod 600 time-test.txt
stat time-test.txt
```

!/assets/image_8c028b82-3d4f-4f42-8f45-271c9def070e.png

CLI 출력 — 데이터 변경과 chmod 전후의 atime/mtime/ctime 비교

정리하면:

- atime: 파일 데이터를 읽은 시간과 관련된다.

- mtime: 파일의 내용(data)이 변경된 시간이다.

- ctime: inode metadata가 변경된 시간이다. 권한, 소유자, link count뿐 아니라 파일 내용 변경으로 inode 상태가 바뀌어도 갱신될 수 있다.

단, atime은 mount option에 따라 동작이 달라질 수 있다. Linux에서는 성능을 위해 relatime, noatime 정책을 사용할 수 있으므로 read마다 항상 즉시 갱신된다고 단정하면 안 된다.

---

## 11. inode 번호로 파일 경로를 찾을 수 있다

inode 번호를 알고 있다면 해당 inode를 참조하는 경로를 검색할 수 있다.

```
find / -xdev -inum 1048583 2>/dev/null
```

같은 파일시스템 안에서 hard link가 여러 개 존재한다면 동일 inode 번호를 가진 여러 경로가 검색될 수 있다.

---

## 12. VFS에서 실제 block I/O까지의 흐름

사용자가 파일을 읽거나 쓸 때 inode는 Linux 저장 계층의 중간 핵심 객체로 동작한다.

```
Application
    ↓
VFS (Virtual File System)
    ↓
Directory Entry
    ↓
inode / filesystem metadata
    ↓
extent / block mapping
    ↓
Block Device
    ↓
LVM / RAID / Disk
```

예를 들어 애플리케이션이 /etc/passwd를 읽으면 VFS가 경로를 탐색하고 directory entry를 통해 inode를 찾는다. 파일시스템은 inode의 extent/block mapping을 이용해 실제 데이터 블록 위치를 확인한 후 block layer로 I/O를 전달한다.

---

## 핵심 요약

- 파일 이름은 inode가 아니다. 파일 이름은 directory entry 안에서 inode를 참조한다.

- inode는 파일의 메타데이터와 실제 데이터 위치 정보를 관리한다.

- hard link는 동일 inode를 공유하며 link count를 증가시킨다.

- symbolic link는 별도의 inode를 사용하고 target 경로 문자열을 지정한다.

- rm은 기본적으로 파일 이름과 inode 연결을 unlink한다.

- link count가 0이어도 프로세스가 inode를 열고 있으면 데이터는 유지될 수 있다.

- 삭제했는데 디스크 공간이 줄지 않으면 lsof +L1을 확인한다.

- df -h뿐 아니라 df -i도 함께 확인해야 inode 고갈 장애를 찾을 수 있다.

- ctime은 create time이 아니라 inode 상태 변경 시간이다.

- 파일 접근 흐름은 path → dentry → inode → extent/block → block device로 이해하면 된다.