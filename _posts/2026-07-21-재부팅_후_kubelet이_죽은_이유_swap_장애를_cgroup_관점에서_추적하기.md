---
title: "재부팅 후 kubelet이 죽은 이유: Swap 장애를 cgroup 관점에서 추적하기"
date: "2026-07-21T14:02:00.000Z"
categories:
  - "cgroup"
  - "k8s"
  - "kubelet"
  - "ubuntu"
author: "현제 김_7254"
slug: "재부팅_후_kubelet이_죽은_이유_swap_장애를_cgroup_관점에서_추적하기"
---

## 들어가며

VMware의 Ubuntu VM을 kubeadm 기반 Kubernetes Control Plane으로 구성한 뒤 재부팅했다. 재부팅 직후 containerd는 정상적으로 올라왔지만 kubelet은 실행되지 않았고, 결국 kubectl도 API Server에 접근하지 못했다.

표면적으로 보인 오류는 다음과 같았다.

```
The connection to the server 192.168.253.128:6443 was refused
```

하지만 실제 원인은 API Server나 containerd가 아니라, 재부팅 과정에서 다시 활성화된 /swap.img와 kubelet의 Swap 정책이었다.

이번 글에서는 실제 명령어와 로그를 따라가며 장애를 복구하고, 그 내부에서 cgroup, systemd, containerd, kubelet이 어떤 관계로 동작하는지 정리한다.

---

## 1. 최초 증상

Control Plane 점검 스크립트의 결과는 다음과 같았다.

```
========================================
 Kubernetes Control Plane Health Check
========================================

[ OK ] containerd service is running
[FAIL] kubelet service is NOT running
[ OK ] containerd socket exists
[ OK ] kubelet config exists

Checking Static Pod manifests...
[ OK ] etcd manifest exists
[ OK ] kube-apiserver manifest exists
[ OK ] kube-controller-manager manifest exists
[ OK ] kube-scheduler manifest exists

Checking API Server...
[FAIL] Cannot connect to API Server
```

상태를 요약하면 다음과 같다.

containerd가 실행 중인데도 Control Plane은 올라오지 않았다.

```
sudo systemctl is-active containerd
```

```
active
```

API Server 포트를 확인해 보니 6443은 LISTEN 상태가 아니었다.

```
sudo ss-lntp |grep6443
```

```
# 출력 없음
```

kubectl은 올바른 Control Plane 주소로 접속하고 있었다.

```
kubectlget nodes
```

```
Get "https://192.168.253.128:6443/api?timeout=32s":
dial tcp 192.168.253.128:6443: connect: connection refused
```

따라서 kubeconfig 문제가 아니라 kube-apiserver 자체가 실행되지 않은 상황이었다.

---

## 2. containerd가 살아 있어도 Control Plane이 올라오지 않는 이유

kubeadm으로 설치한 Control Plane 구성 요소는 일반적인 systemd 서비스가 아니라 kubelet이 관리하는 Static Pod다.

```
/etc/kubernetes/manifests/
├── etcd.yaml
├── kube-apiserver.yaml
├── kube-controller-manager.yaml
└── kube-scheduler.yaml
```

정상적인 부팅 흐름은 다음과 같다.

```
systemd
  ↓
containerd 시작
  ↓
kubelet 시작
  ↓
/etc/kubernetes/manifests 감시
  ↓
Control Plane Static Pod 생성
  ↓
etcd 및 kube-apiserver 실행
  ↓
6443 포트 LISTEN
```

containerd는 컨테이너를 실행할 수 있는 런타임을 제공하지만, 어떤 Static Pod를 실행할지 결정하고 원하는 상태를 유지하는 주체는 kubelet이다.

따라서 현재 상태는 다음과 같았다.

```
containerd active
  ↓
kubelet failed
  ↓
Static Pod 복구 불가
  ↓
kube-apiserver 미실행
  ↓
6443 connection refused
```

---

## 3. Manifest와 컨테이너 객체 점검

먼저 kube-apiserver.yaml이 비어 있거나 손상되지 않았는지 확인했다.

```
sudowc-l /etc/kubernetes/manifests/kube-apiserver.yaml
```

```
124 /etc/kubernetes/manifests/kube-apiserver.yaml
```

```
sudo head-20 /etc/kubernetes/manifests/kube-apiserver.yaml
```

```
apiVersion: v1
kind: Pod
metadata:
  annotations:
    kubeadm.kubernetes.io/kube-apiserver.advertise-address.endpoint: 192.168.253.128:6443
  labels:
    component: kube-apiserver
    tier: control-plane
  name: kube-apiserver
  namespace: kube-system
spec:
  containers:
  - command:
    - kube-apiserver
    - --advertise-address=192.168.253.128
```

Manifest는 정상적으로 존재했다.

containerd에 등록된 객체도 확인했다.

```
sudo ctr-n k8s.io containers list
```

```
registry.k8s.io/kube-apiserver:v1.36.2
registry.k8s.io/kube-controller-manager:v1.36.2
registry.k8s.io/kube-scheduler:v1.36.2
registry.k8s.io/etcd:3.6.8-0
```

다만 containers list에 객체가 존재하는 것과 실제 프로세스가 실행 중인 것은 다르다.

```
sudo ctr-n k8s.io tasks list
```

- containers list: containerd에 등록된 컨테이너 메타데이터

- tasks list: 현재 실행 중인 컨테이너 프로세스

즉, 기존 컨테이너 객체가 남아 있어도 kubelet이 죽어 있다면 Control Plane 프로세스는 복구되지 않을 수 있다.

---

## 4. kubelet 로그에서 실제 원인 발견

가장 중요한 단서는 kubelet의 systemd 로그에 있었다.

```
sudo journalctl-u kubelet-n100--no-pager
```

```
"Kubelet version" kubeletVersion="v1.36.2"

"Using cgroup driver setting received from the CRI runtime"
cgroupDriver="systemd"

"Swap is on" /proc/swaps contents=<

Filename      Type  Size     Used     Priority
/swap.img     file  3954684  1451840 -1
>

"command failed"
err="failed to run Kubelet:
running with swap on is not supported,
please disable swap or set --fail-swap-on flag to false"
```

kubelet은 /swap.img가 활성화된 것을 감지한 뒤 status=1/FAILURE로 종료됐다. systemd는 kubelet을 다시 실행했지만 Swap이 계속 켜져 있었기 때문에 같은 오류가 반복됐다.

```
Scheduled restart job, restart counter is at 133
Scheduled restart job, restart counter is at 134
Scheduled restart job, restart counter is at 135
...
```

실제로 restart counter가 계속 증가하며 재시작 루프가 이어지고 있었다.

장애 흐름은 다음과 같이 확정됐다.

```
VM 재부팅
  ↓
/swap.img 자동 활성화
  ↓
kubelet의 Swap 검사 실패
  ↓
kubelet 종료
  ↓
Static Pod 복구 실패
  ↓
kube-apiserver 미기동
  ↓
6443 connection refused
```

Kubernetes kubelet은 기본적으로 노드에서 활성화된 Swap을 발견하면 시작을 거부한다. Swap을 유지하려면 failSwapOn: false와 별도의 Swap 동작 정책을 명시해야 한다.

---

## 5. cgroup은 무엇을 제어하는가

cgroup을 다음과 같은 구조로 설명할수 있다.

> 프로세스를 계층적인 그룹으로 묶고, 각 그룹의 CPU·메모리·I/O·프로세스 수 사용량을 제한하고 관찰하는 Linux 커널 기능

cgroup v2의 커널 인터페이스는 보통 다음 위치에 마운트된다.

```
mount-l |grep cgroup
```

```
cgroup2 on /sys/fs/cgroup type cgroup2
```

cgroup을 생성한다는 것은 본질적으로 cgroupfs 아래에 디렉터리를 만들고 특수 파일에 값을 쓰는 작업이다.

```
sudomkdir /sys/fs/cgroup/demo
```

생성된 디렉터리에는 다음과 같은 제어 파일이 만들어진다.

```
cpu.max
cpu.weight
memory.current
memory.max
memory.swap.current
memory.swap.max
io.max
pids.current
pids.max
cgroup.procs
```

대표적인 의미는 다음과 같다.

실행 중인 프로세스의 PID를 cgroup.procs에 기록하면 그 프로세스가 해당 cgroup으로 이동한다.

```
echo <PID> |sudotee /sys/fs/cgroup/demo/cgroup.procs
```

예시로 CPU 50%, 메모리 100MB 제한을 다음과 같이 적용한다.

```
echo"50000 100000" |sudotee /sys/fs/cgroup/demo/cpu.maxecho"100M" |sudotee /sys/fs/cgroup/demo/memory.max
```

첫 번째 값은 한 주기 동안 사용할 수 있는 CPU 시간이고, 두 번째 값은 주기의 길이다. 50000 / 100000이므로 CPU 한 코어 기준 약 50%로 제한된다. cgroup v2에서는 디렉터리와 제어 파일을 통해 프로세스의 CPU와 메모리를 직접 제한하며, 상위 cgroup의 정책은 하위 그룹에 계층적으로 적용된다.

---

## 6. systemd와 cgroup의 관계

실제로 운영 중인 Ubuntu에서는 /sys/fs/cgroup을 직접 수정하기보다 systemd가 cgroup 계층을 관리하게 하는 것이 일반적이다.

iximiuz의 예제처럼 systemd-run으로 제한된 프로세스를 바로 실행할 수 있다.

```
sudo systemd-run \--unit=resource-demo \--property=CPUQuota=50% \--property=MemoryMax=100M \--collect \sleep300
```

이 명령은 다음 작업을 대신 수행한다.

```
systemd transient unit 생성
  ↓
전용 cgroup 생성
  ↓
CPUQuota를 cpu.max에 반영
  ↓
MemoryMax를 memory.max에 반영
  ↓
프로세스를 해당 cgroup에서 실행
```

현재 cgroup 계층은 다음 명령으로 볼 수 있다.

```
systemd-cgls--all
```

cgroup 단위 자원 사용량은 다음과 같이 확인한다.

```
systemd-cgtop
```

systemd 기반 배포판에서는 systemd가 서비스마다 slice와 scope를 만들기 때문에, containerd와 Kubernetes도 systemd를 cgroup 관리자로 사용하는 구성이 권장된다. iximiuz의 글 역시 systemd가 사실상 cgroupfs 관리자가 되므로 다른 구성 요소가 systemd cgroup driver를 사용하게 된다고 설명한다.

---

## 7. containerd와 kubelet의 cgroup driver

Kubernetes 노드에서는 kubelet과 container runtime이 동일한 cgroup driver를 사용해야 한다.

![image](/assets/image_943b46eb-141d-4ca8-9350-9a69f84c0b86.png)

그림 1. grep Cgroup으로 검색하면 다른 설정의 Cgroup = false가 잡힐 수 있다. 실제로 확인해야 하는 항목은 runc options 아래의 SystemdCgroup이다.

containerd 1.x에서는 다음 설정을 확인한다.

```
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
  SystemdCgroup = true
```

```
sudogrep-n"SystemdCgroup" \
  /etc/containerd/config.toml
```

설정을 수정했다면 containerd를 재시작한다.

```
sudo systemctlrestart containerdsudo systemctl is-active containerd
```

kubelet도 systemd driver를 사용해야 한다.

```
grep'^cgroupDriver:' \
  /var/lib/kubelet/config.yaml
```

```
cgroupDriver: systemd
```

cgroup v2 환경에서는 kubelet과 container runtime 모두 systemd cgroup driver를 사용하는 구성이 요구되며, kubeadm 기반 환경에서도 systemd driver가 권장된다.

---

## 8. Kubernetes의 리소스 제한은 cgroup으로 변환된다

Pod에 다음과 같은 리소스 제한을 지정했다고 가정해 보자.

```
resources:
  requests:
    cpu: 250m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

전체 흐름은 다음과 같다.

```
Pod resources 설정
  ↓
kubelet
  ↓
CRI 요청
  ↓
containerd
  ↓
runc
  ↓
Linux cgroup 파일 설정
```

개념적으로 다음과 같이 연결된다.

```
CPU limit
→ cpu.max

Memory limit
→ memory.max

Swap 정책
→ memory.swap.max

PID 제한
→ pids.max
```

Kubernetes가 자체적인 CPU 또는 메모리 스케줄러를 새로 구현하는 것이 아니다. Kubernetes는 원하는 정책을 계산하고, container runtime을 통해 Linux 커널의 cgroup 설정으로 변환한다.

Swap을 허용하도록 구성한 노드에서도 kubelet은 CRI를 통해 컨테이너별 memory.swap.max와 같은 cgroup v2 설정을 적용한다. 기본 NoSwap 동작에서는 kubelet이 실행되더라도 Pod 워크로드에는 Swap이 할당되지 않는다.

---

## 9. 이번 장애는 cgroup 오류였을까

정확히 말하면 이번 장애는 cgroup 자체의 고장이 아니었다.

```
containerd cgroup driver: systemd
kubelet cgroup driver: systemd
```

두 구성 요소의 cgroup driver는 정상적으로 일치하고 있었다.

문제는 kubelet이 cgroup을 구성하기도 전에 Swap 정책 검사에서 종료됐다는 점이다.

```
kubelet 시작
  ↓
노드 Swap 상태 확인
  ↓
/swap.img 발견
  ↓
failSwapOn=true 정책 위반
  ↓
kubelet 종료
```

kubelet이 죽었기 때문에 Pod별로 다음과 같은 cgroup 설정을 유지할 주체도 사라졌다.

```
kubepods.slice
├── kubepods-burstable.slice
├── kubepods-besteffort.slice
└── 각 Pod 및 컨테이너 scope
```

따라서 이번 문제의 핵심은 다음과 같다.

> cgroup으로 자원을 관리하는 kubelet이 Swap 정책 위반으로 시작하지 못하면서 Control Plane 전체가 복구되지 않았다.

---

## 10. 즉시 복구

먼저 활성화된 Swap을 확인했다.

```
swapon--show
```

```
NAME      TYPE SIZE USED PRIO
/swap.img file 3.8G 1.4G   -1
```

현재 부팅 세션에서 Swap을 비활성화했다.

```
sudo swapoff-a
```

다시 확인한다.

```
swapon--show
free-h
```

정상 상태:

```
swapon --show
# 출력 없음

Swap: 0B 0B 0B
```

그다음 kubelet을 재시작했다.

```
sudo systemctlrestart kubeletsudo systemctl is-active kubelet
```

```
active
```

kubelet이 Static Pod를 복구할 시간을 잠시 기다린 후 API Server를 확인한다.

```
sleep10sudo ss-lntp |grep6443
kubectlget--raw='/readyz'
kubectlget nodes
```

정상 결과:

```
6443    → LISTEN
readyz  → ok
Node    → Ready
```

---

## 11. 재부팅 후에도 Swap이 켜지지 않도록 설정

swapoff -a는 현재 부팅에만 적용된다. 재부팅 후에도 유지하려면 /etc/fstab 또는 systemd swap unit을 수정해야 한다.

먼저 파일을 백업한다.

```
sudocp /etc/fstab \
  /etc/fstab.backup.$(date +%Y%m%d-%H%M%S)
```

Swap 항목을 확인한다.

```
grep-nE'\sswap\s|swap.img|swapfile' \
  /etc/fstab
```

기존 설정:

```
/swap.img none swap sw 0 0
```

Swap 행만 주석 처리한다.

```
sudosed-i \'/[[:space:]]swap[[:space:]]/ s/^[^#]/#&/' \
  /etc/fstab
```

변경 결과:

```
#/swap.img none swap sw 0 0
```

서비스 자동 시작도 확인한다.

```
sudo systemctl enable containerd kubelet

systemctl is-enabled containerd
systemctl is-enabled kubelet
```

```
enabled
enabled
```

---

## 12. cgroup 상태를 직접 관찰하는 방법

현재 시스템이 cgroup v2인지 확인한다.

```
stat-fc %T /sys/fs/cgroup
```

```
cgroup2fs
```

kubelet 프로세스가 어느 cgroup에 속하는지 확인한다.

```
KUBELET_PID=$(pidof kubelet)cat /proc/${KUBELET_PID}/cgroup
```

cgroup v2라면 보통 다음 형식으로 나타난다.

```
0::/system.slice/kubelet.service
```

kubelet cgroup의 실제 메모리 사용량을 확인할 수 있다.

```
CGROUP_PATH=$(
  awk -F:'$1 == "0" {print $3}' \
  /proc/$(pidof kubelet)/cgroup
)cat"/sys/fs/cgroup${CGROUP_PATH}/memory.current"cat"/sys/fs/cgroup${CGROUP_PATH}/memory.max"cat"/sys/fs/cgroup${CGROUP_PATH}/cpu.stat"
```

전체 계층은 다음 명령으로 확인한다.

```
systemd-cgls--all
systemd-cgtop
```

이 명령을 사용하면 단순히 top으로 프로세스 하나만 보는 것이 아니라, system.slice, kubepods.slice처럼 서비스와 Pod 그룹 단위로 CPU와 메모리 사용량을 관찰할 수 있다.

---

## 13. 최종 점검 스크립트

```
#!/usr/bin/env bashecho"=== cgroup version ==="
stat-fc %T /sys/fs/cgroupechoecho"=== active swap ==="
swapon--showechoecho"=== service state ==="
printf"containerd: "
systemctl is-active containerd

printf"kubelet: "
systemctl is-active kubeletechoecho"=== cgroup drivers ==="grep'^cgroupDriver:' \
  /var/lib/kubelet/config.yaml2>/dev/null ||truegrep-n'SystemdCgroup' \
  /etc/containerd/config.toml2>/dev/null ||trueechoecho"=== static pod manifests ==="sudols-lh /etc/kubernetes/manifests/echoecho"=== API server ==="sudo ss-lntp |grep6443 ||trueechoecho"=== Kubernetes health ==="
kubectlget--raw='/readyz'2>/dev/null ||true
kubectlget nodes2>/dev/null ||trueechoecho"=== recent kubelet errors ==="sudo journalctl \-u kubelet \-p warning \-n20 \--no-pager
```

---

## 마무리

이번 장애는 다음 흐름으로 정리할 수 있다.

```
재부팅
  ↓
Swap 자동 활성화
  ↓
kubelet 시작 거부
  ↓
cgroup 및 Static Pod 관리 중단
  ↓
etcd와 kube-apiserver 복구 실패
  ↓
6443 connection refused
```

트러블슈팅 과정에서 가장 중요한 교훈은 세 가지였다.

첫째, containerd가 active라고 해서 Kubernetes가 정상인 것은 아니다. Static Pod를 복구하는 주체는 kubelet이다.

둘째, kubectl connection refused는 최종 증상일 뿐이다. 포트, kubelet 상태, journal 로그 순서로 내려가야 실제 원인을 찾을 수 있다.

셋째, Kubernetes의 리소스 제한을 제대로 이해하려면 cgroup을 알아야 한다. Pod의 CPU·메모리·Swap 정책은 최종적으로 Linux 커널의 cpu.max, memory.max, memory.swap.max 같은 cgroup 인터페이스로 구현된다.

---

## 참고 자료

- Ivan Velichko, Controlling Process Resources with Linux Control Groups, iximiuz Labs. cgroupfs 직접 조작부터 systemd-run, systemd slice를 이용한 영구적인 자원 제어까지 단계적으로 설명한 글이다. 이번 글의 cgroup 구조와 실습 명령은 이 자료를 적극적으로 참고했다.

- Kubernetes 공식 문서, About cgroup v2. cgroup v2 요구사항과 kubelet·container runtime의 systemd cgroup driver 구성을 설명한다.

- Kubernetes 공식 문서, Configuring a cgroup driver. kubeadm 환경에서 kubelet과 container runtime의 cgroup driver를 일치시키는 방법을 설명한다.

- Kubernetes 공식 문서, Swap memory management. failSwapOn, NoSwap, LimitedSwap과 cgroup v2의 memory.swap.max 관계를 설명한다.

- Linux Kernel Documentation, Control Group v2. cgroup v2 계층 구조와 각 controller 인터페이스의 기준 문서다.