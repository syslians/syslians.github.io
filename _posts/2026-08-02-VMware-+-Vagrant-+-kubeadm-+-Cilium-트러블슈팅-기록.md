---
title: "VMware + Vagrant + kubeadm + Cilium 트러블슈팅 기록"
date: "2026-08-02T06:54:01.767Z"
categories:
  - "vmware"
  - "vagrant"
  - "k8s"
  - "cillium"
author: "현제 김_7254"
slug: "vmware_vagrant_kubeadm_cilium_트러블슈팅_기록"
---

## Rocky Linux Worker Node 생성부터 Cillium VXLAN Overlay 복구까지

### 1. 개요 

이번 작업의 목표는 컨트롤 플레인으로 운영중이던 우분투 기반 kubernetes Control Plane에 Rocky Linux Worker Node를 새롭게 추가시키는 것이였다.

단순히 kubeadm join만 하면 끝날 줄 알았지만 실제로는 다음과 같은 문제가 연쇄적으로 발생했다.

- Worker SSH 접속시 Vagrant private key 인증 문제

- kubeadm join 과정에서 cgroup 관련 경고, 검증 문제

- join 이후 Node가 등록되었지만 NotReady

- 원인은 Cillium CNI가 Worker에 설치되지 않음

- 더 깊게 들어가니 kubelet의 resolvConf 경로가 Rocky 환경과 맞지 않아 pod Sandbox 생성 실패

- Cillium DaemonSet 재가동 → CNI 바이너리 설치 → VXLAN Overlay 복구

- 최종적으로 Worker가 Ready가 되고, Pending 상태였던 Pod들이 Worker에 정상 배치됨.

이번글은 그 과정을 문제 → 원인 분석 → 해결 → 최종 구조 순서로 정리한 기록이다.

## 2. 최종 목표 구조

### 현재 클러스터 구성

<img width="1672" height="941" alt="image" src="https://github.com/user-attachments/assets/a69e2823-1cb0-434c-892b-fd423ff2f8ec" />


그림 1. 현재 클러스터, VMnet8 Underlay, Cilium VXLAN 인캡슐레이션 및 인터페이스 연결 구조

이 구조에서 두 VM은 같은 VMware NAT 네트워크(VMnet8)에 올라와있기 때문에 별도의 포트포워드 없이 192.168.253.128:6443 으로 Control Plane에 접근할 수 있다.

### 3. kubernetes + Cillium Overlay 구조

```
                         Kubernetes Cluster
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  Service CIDR: 10.96.0.0/12                                                  │
│  Pod Overlay: Cilium VXLAN                                                   │
│                                                                              │
│  ┌──────────────────────────────┐        VXLAN Overlay        ┌────────────┐ │
│  │ Control Plane Node           │ <-------------------------> │ Worker-1   │ │
│  │ 192.168.253.128              │       Underlay: VMnet8      │ 192.168.253.130│
│  │                              │                              │            │ │
│  │ cilium_host                  │                              │ cilium_host│ │
│  │ cilium_vxlan                 │                              │ cilium_vxlan││
│  │ kube-proxy                   │                              │ kube-proxy │ │
│  │ coredns                      │                              │ nginx      │ │
│  │ cilium operator              │                              │ curl       │ │
│  │ Pod IP examples:             │                              │ Pod IP examples:│
│  │ 10.0.0.x                     │                              │ 10.0.1.x   │ │
│  └──────────────────────────────┘                              └────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

여기서 중요한 포인트는

- Underlay Network: VMware VMnet8의 192.168.253.0/24 

- Overlay Network: Cillium이 만드는 pod간 VXLAN 네트워크

- Pod는 실제로 10.0.x, 10.0.1.x와 같은 Overlay IP를 사용한다.

### 3.2 Pod → Cillium → VXLAN → Remote Pod 흐름

```
[Pod: curl 10.0.1.17]
        │
        │ eth0 (pod ns)
        ▼
[veth pair / lxc* interface]
        │
        ▼
[worker-1 root netns]
        │
        ├─ cilium_host
        ├─ cilium_net
        └─ cilium_vxlan
                │
                │ VXLAN Encapsulation
                ▼
       Underlay Network (192.168.253.130 -> 192.168.253.128)
                │
                ▼
[control-plane root netns]
        │
        ├─ cilium_vxlan
        ├─ cilium_host
        ▼
[Target Pod on remote node]
```

즉, Pod간 통신은 단순히 VM 네트워크를 직접 쓰는 것이 아니라, Cillium이 호스트 인터페이스 위에 Overlay(VXALN) 경로를 구성해서 처리한다.

## 4. Worker Node 생성: 왜 Vagrant인가

처음에는 학원 컴퓨터에 있는 기존 Kali linux를 Worker Node로 편입시키려 했지만, 구버젼이라 패키시 GPG Key/ 버젼 불일치 문제로 실습 환경이 지나치게 불안정해졌다. 그래서 최종적으로는 Rocky Linux를 Worker로 구성하고, 이를 위해 Vagrant를 써서 프로비져닝을 하기로 결정했다.

<img width="1011" height="540" alt="image" src="https://github.com/user-attachments/assets/200af8cd-9ce2-4e57-8a2e-9b9a16c6eb63" />


그림 2. 초기 Kali Worker 후보에서 인터페이스와 IP를 확인한 화면

- Vagrant + VMware

- Box: rockyliunx8

- Provisioning Shell로 kubelet/containerd/kubeadm 자동화

<img width="1083" height="847" alt="image" src="https://github.com/user-attachments/assets/b04aae58-40d2-4f17-a7ac-63e28a045092" />


그림 3. containerd, runc, nftables 등 패키지 다운로드가 404로 실패한 화면

Keyring도 오래되어 저장소 서명 검증이 실패했고, Keyring 패키지를 직접 내려받으려는 시도에서도 경로와 버젼 불일치가 이어졌다.

이 방식의 큰 장점은 VM 재생성이 쉽고, 환경을 코드로 (IaC)남길 수 있다. 향후 Ansible과도 자연스럽게 연결 가능하다.  재현 가능한 쿠버네티스 Worker 생성이라는 목적에도 가장 부합한 옵션 조합들이다.

### 5. Vagrant 프로비져닝과 Worker 준비

Vagrant Scripts.sh

```
#!/usr/bin/env bash

set -euxo pipefail

KUBERNETES_MINOR="v1.36"
CONTROL_PLANE_IP="192.168.253.128"

export LANG=C

echo "========================================"
echo " Rocky Linux Kubernetes Worker Setup"
echo "========================================"

dnf install -y \
  dnf-plugins-core \
  curl \
  ca-certificates \
  gnupg2 \
  conntrack-tools \
  socat \
  ipset \
  iproute \
  ethtool \
  tar

hostnamectl set-hostname worker-1

if ! grep -q "control-plane" /etc/hosts; then
  echo "${CONTROL_PLANE_IP} control-plane" >> /etc/hosts
fi

swapoff -a || true
free -h 
cp -a /etc/fstab /etc/fstab.bak
sed -ri '/\sswap\s/s/^#?/#/' /etc/fstab

setenforce 0 || true
sed -ri 's/^SELINUX=enforcing$/SELINUX=permissive/' /etc/selinux/config

cat >/etc/modules-load.d/k8s.conf <<'EOF'
overlay
br_netfilter 
EOF

modprobe overlay
modprobe br_netfilter

cat >/etc/sysctl.d/99-kubernetes-cri.conf <<'EOF'
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sysctl --system

dnf config-manager --add-repo \
  https://download.docker.com/linux/centos/docker-ce.repo

dnf install -y containerd.io

mkdir -p /etc/containerd
containerd config default >/etc/containerd/config.toml

sed -i \
  's/SystemdCgroup = false/SystemdCgroup = true/' \
  /etc/containerd/config.toml

systemctl daemon-reload
systemctl enable --now containerd
systemctl restart containerd

cat >/etc/yum.repos.d/kubernetes.repo <<EOF
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/${KUBERNETES_MINOR}/rpm/
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/${KUBERNETES_MINOR}/rpm/repodata/repomd.xml.key
exclude=kubelet kubeadm kubectl cri-tools kubernetes-cni
EOF

dnf install -y \
  kubelet \
  kubeadm \
  --disableexcludes=kubernetes

systemctl enable kubelet

NODE_IP="$(
  ip -4 route get "${CONTROL_PLANE_IP}" |
  awk '{for (i=1; i<=NF; i++) if ($i=="src") print $(i+1)}' |
  head -n1
)"

if [[ -z "${NODE_IP}" ]]; then
  echo "ERROR: Node IP detection failed"
  exit 1
fi

cat >/etc/sysconfig/kubelet <<EOF
KUBELET_EXTRA_ARGS=--node-ip=${NODE_IP}
EOF

systemctl disable --now firewalld || true
systemctl daemon-reload
systemctl restart kubelet || true

cat >/root/worker-info.txt <<EOF
hostname=$(hostname)
os=$(cat /etc/redhat-release)
kernel=$(uname -r)
node_ip=${NODE_IP}
control_plane_ip=${CONTROL_PLANE_IP}
containerd=$(containerd --version)
kubeadm=$(kubeadm version -o short)
kubelet=$(kubelet --version)
selinux=$(getenforce)
EOF

cat /root/worker-info.txt
```

스크립트 작성후 권한을 할당하고 vagrant up —provider=vmware_desktop으로 프로바이더를 넘겨줘야한다.

아래 로그로 프로비져닝이 정상적으로 실행된걸 볼 수 있다.

```
PS D:\k8s-rocky-worker> vagrant up --provider=vmware_desktop
Bringing machine 'worker-1' up with 'vmware_desktop' provider...
==> worker-1: Cloning VMware VM: 'rockylinux/8'. This can take some time...
==> worker-1: Checking if box 'rockylinux/8' version '10.0.0' is up to date...
==> worker-1: Verifying vmnet devices are healthy...
==> worker-1: Preparing network adapters...
==> worker-1: Fixed port collision for 22 => 2222. Now on port 2200.
==> worker-1: Starting the VMware VM...
==> worker-1: Waiting for the VM to receive an address...
==> worker-1: Forwarding ports...
    worker-1: -- 22 => 2200
==> worker-1: Waiting for machine to boot. This may take a few minutes...
    worker-1: SSH address: 127.0.0.1:2200
    worker-1: SSH username: vagrant
    worker-1: SSH auth method: private key
    worker-1:
    worker-1: Vagrant insecure key detected. Vagrant will automatically replace
    worker-1: this with a newly generated keypair for better security.
    worker-1:
    worker-1: Inserting generated public key within guest...
    worker-1: Removing insecure key from the guest if it's present...
    worker-1: Key inserted! Disconnecting and reconnecting using new SSH key...
==> worker-1: Machine booted and ready!
==> worker-1: Setting hostname...
==> worker-1: Configuring network adapters within the VM...
==> worker-1: Running provisioner: shell...
    worker-1: Running: C:/Users/User/AppData/Local/Temp/vagrant-shell20260728-17316-wtmlm4.sh
    worker-1: ========================================
    worker-1:  Rocky Linux Kubernetes Worker Setup
    worker-1: ========================================
    worker-1: + KUBERNETES_MINOR=v1.36
    worker-1: + CONTROL_PLANE_IP=192.168.253.128
    worker-1: + export LANG=C
    worker-1: + LANG=C
    worker-1: + echo ========================================
    worker-1: + echo ' Rocky Linux Kubernetes Worker Setup'
    worker-1: + echo ========================================
    worker-1: + dnf install -y dnf-plugins-core curl ca-certificates gnupg2 conntrack-tools socat ipset iproute ethtool tar
    worker-1: Rocky Linux 8 - AppStream                       6.7 kB/s | 4.7 kB     00:00
    worker-1: Rocky Linux 8 - AppStream                        17 MB/s |  31 MB     00:01
    worker-1: Rocky Linux 8 - BaseOS                          6.2 kB/s | 4.3 kB     00:00
    worker-1: Rocky Linux 8 - BaseOS                           40 MB/s |  68 MB     00:01
    worker-1: Rocky Linux 8 - Extras                          4.1 kB/s | 3.0 kB     00:00
    worker-1: Rocky Linux 8 - Extras                           17 kB/s |  15 kB     00:00
    worker-1: Last metadata expiration check: 0:00:01 ago on Tue Jul 28 03:53:01 2026.
    worker-1: Package dnf-plugins-core-4.0.21-25.el8.noarch is already installed.
    worker-1: Package curl-7.61.1-34.el8.x86_64 is already installed.
    worker-1: Package ca-certificates-2023.2.60_v7.0.306-80.0.el8_8.noarch is already installed.
    worker-1: Package gnupg2-2.2.20-3.el8_6.x86_64 is already installed.
    worker-1: Package ipset-7.1-1.el8.x86_64 is already installed.
    worker-1: Package iproute-6.2.0-6.el8_10.x86_64 is already installed.
    worker-1: Package ethtool-2:5.13-2.el8.x86_64 is already installed.
    worker-1: Package tar-2:1.30-9.el8.x86_64 is already installed.
    worker-1: Dependencies resolved.
    worker-1: ================================================================================
    worker-1:  Package                Arch   Version                          Repo       Size
    worker-1: ================================================================================
    worker-1: Installing:
    worker-1:  conntrack-tools        x86_64 1.4.4-11.el8                     baseos    203 k
    worker-1:  socat                  x86_64 1.7.4.1-2.el8_10                 appstream 322 k
    worker-1: Upgrading:
    worker-1:  ca-certificates        noarch 2025.2.80_v9.0.304-80.2.el8_10   baseos    1.0 M
    worker-1:  curl                   x86_64 7.61.1-34.el8_10.11              baseos    354 k
    worker-1:  gnupg2                 x86_64 2.2.20-4.el8_10                  baseos    2.4 M
    worker-1:  gnupg2-smime           x86_64 2.2.20-4.el8_10                  baseos    282 k
    worker-1:  libcurl                x86_64 7.61.1-34.el8_10.11              baseos    307 k
    worker-1:  tar                    x86_64 2:1.30-11.el8_10                 baseos    838 k
    worker-1: Installing dependencies:
    worker-1:  libnetfilter_cthelper  x86_64 1.0.0-15.el8                     baseos     23 k
    worker-1:  libnetfilter_cttimeout x86_64 1.0.0-11.el8                     baseos     23 k
    worker-1:  libnetfilter_queue     x86_64 1.0.4-3.el8                      baseos     30 k
    worker-1:
    worker-1: Transaction Summary
    worker-1: ================================================================================
    worker-1: Install  5 Packages
    worker-1: Upgrade  6 Packages
    worker-1:
    worker-1: Total download size: 5.7 M
    worker-1: Downloading Packages:
    worker-1: (1/11): libnetfilter_cthelper-1.0.0-15.el8.x86_ 242 kB/s |  23 kB     00:00
    worker-1: (2/11): conntrack-tools-1.4.4-11.el8.x86_64.rpm 1.8 MB/s | 203 kB     00:00
    worker-1: (3/11): libnetfilter_cttimeout-1.0.0-11.el8.x86 980 kB/s |  23 kB     00:00
    worker-1: (4/11): socat-1.7.4.1-2.el8_10.x86_64.rpm       2.5 MB/s | 322 kB     00:00
    worker-1: (5/11): libnetfilter_queue-1.0.4-3.el8.x86_64.r 1.4 MB/s |  30 kB     00:00
    worker-1: (6/11): curl-7.61.1-34.el8_10.11.x86_64.rpm      12 MB/s | 354 kB     00:00
    worker-1: (7/11): ca-certificates-2025.2.80_v9.0.304-80.2  20 MB/s | 1.0 MB     00:00
    worker-1: (8/11): gnupg2-smime-2.2.20-4.el8_10.x86_64.rpm  12 MB/s | 282 kB     00:00
    worker-1: (9/11): libcurl-7.61.1-34.el8_10.11.x86_64.rpm   14 MB/s | 307 kB     00:00
    worker-1: (10/11): tar-1.30-11.el8_10.x86_64.rpm           26 MB/s | 838 kB     00:00
    worker-1: (11/11): gnupg2-2.2.20-4.el8_10.x86_64.rpm       22 MB/s | 2.4 MB     00:00
    worker-1: --------------------------------------------------------------------------------
    worker-1: Total                                           4.0 MB/s | 5.7 MB     00:01
    worker-1: Running transaction check
    worker-1: Transaction check succeeded.
    worker-1: Running transaction test
    worker-1: Transaction test succeeded.
    worker-1: Running transaction
    worker-1:   Preparing        :                                                        1/1
    worker-1:   Upgrading        : gnupg2-smime-2.2.20-4.el8_10.x86_64                   1/17
    worker-1:   Upgrading        : gnupg2-2.2.20-4.el8_10.x86_64                         2/17
    worker-1:   Upgrading        : libcurl-7.61.1-34.el8_10.11.x86_64                    3/17
    worker-1:   Installing       : libnetfilter_queue-1.0.4-3.el8.x86_64                 4/17
    worker-1:   Running scriptlet: libnetfilter_queue-1.0.4-3.el8.x86_64                 4/17
    worker-1:   Installing       : libnetfilter_cttimeout-1.0.0-11.el8.x86_64            5/17
    worker-1:   Running scriptlet: libnetfilter_cttimeout-1.0.0-11.el8.x86_64            5/17
    worker-1:   Installing       : libnetfilter_cthelper-1.0.0-15.el8.x86_64             6/17
    worker-1:   Running scriptlet: libnetfilter_cthelper-1.0.0-15.el8.x86_64             6/17
    worker-1:   Installing       : conntrack-tools-1.4.4-11.el8.x86_64                   7/17
    worker-1:   Running scriptlet: conntrack-tools-1.4.4-11.el8.x86_64                   7/17
    worker-1:   Upgrading        : curl-7.61.1-34.el8_10.11.x86_64                       8/17
    worker-1:   Upgrading        : tar-2:1.30-11.el8_10.x86_64                           9/17
    worker-1:   Running scriptlet: tar-2:1.30-11.el8_10.x86_64                           9/17
    worker-1:   Running scriptlet: ca-certificates-2025.2.80_v9.0.304-80.2.el8_10.noa   10/17
    worker-1:   Upgrading        : ca-certificates-2025.2.80_v9.0.304-80.2.el8_10.noa   10/17
    worker-1:   Running scriptlet: ca-certificates-2025.2.80_v9.0.304-80.2.el8_10.noa   10/17
    worker-1:   Installing       : socat-1.7.4.1-2.el8_10.x86_64                        11/17
    worker-1:   Cleanup          : ca-certificates-2023.2.60_v7.0.306-80.0.el8_8.noar   12/17
    worker-1:   Cleanup          : curl-7.61.1-34.el8.x86_64                            13/17
    worker-1:   Cleanup          : gnupg2-2.2.20-3.el8_6.x86_64                         14/17
    worker-1:   Cleanup          : gnupg2-smime-2.2.20-3.el8_6.x86_64                   15/17
    worker-1:   Cleanup          : libcurl-7.61.1-34.el8.x86_64                         16/17
    worker-1:   Running scriptlet: tar-2:1.30-9.el8.x86_64                              17/17
    worker-1:   Cleanup          : tar-2:1.30-9.el8.x86_64                              17/17
    worker-1:   Running scriptlet: ca-certificates-2025.2.80_v9.0.304-80.2.el8_10.noa   17/17
    worker-1:   Running scriptlet: tar-2:1.30-9.el8.x86_64                              17/17
    worker-1:   Verifying        : socat-1.7.4.1-2.el8_10.x86_64                         1/17
    worker-1:   Verifying        : conntrack-tools-1.4.4-11.el8.x86_64                   2/17
    worker-1:   Verifying        : libnetfilter_cthelper-1.0.0-15.el8.x86_64             3/17
    worker-1:   Verifying        : libnetfilter_cttimeout-1.0.0-11.el8.x86_64            4/17
    worker-1:   Verifying        : libnetfilter_queue-1.0.4-3.el8.x86_64                 5/17
    worker-1:   Verifying        : ca-certificates-2025.2.80_v9.0.304-80.2.el8_10.noa    6/17
    worker-1:   Verifying        : ca-certificates-2023.2.60_v7.0.306-80.0.el8_8.noar    7/17
    worker-1:   Verifying        : curl-7.61.1-34.el8_10.11.x86_64                       8/17
    worker-1:   Verifying        : curl-7.61.1-34.el8.x86_64                             9/17
    worker-1:   Verifying        : gnupg2-2.2.20-4.el8_10.x86_64                        10/17
    worker-1:   Verifying        : gnupg2-2.2.20-3.el8_6.x86_64                         11/17
    worker-1:   Verifying        : gnupg2-smime-2.2.20-4.el8_10.x86_64                  12/17
    worker-1:   Verifying        : gnupg2-smime-2.2.20-3.el8_6.x86_64                   13/17
    worker-1:   Verifying        : libcurl-7.61.1-34.el8_10.11.x86_64                   14/17
    worker-1:   Verifying        : libcurl-7.61.1-34.el8.x86_64                         15/17
    worker-1:   Verifying        : tar-2:1.30-11.el8_10.x86_64                          16/17
    worker-1:   Verifying        : tar-2:1.30-9.el8.x86_64                              17/17
    worker-1:
    worker-1: Upgraded:
    worker-1:   ca-certificates-2025.2.80_v9.0.304-80.2.el8_10.noarch
    worker-1:   curl-7.61.1-34.el8_10.11.x86_64
    worker-1:   gnupg2-2.2.20-4.el8_10.x86_64
    worker-1:   gnupg2-smime-2.2.20-4.el8_10.x86_64
    worker-1:   libcurl-7.61.1-34.el8_10.11.x86_64
    worker-1:   tar-2:1.30-11.el8_10.x86_64
    worker-1: Installed:
    worker-1:   conntrack-tools-1.4.4-11.el8.x86_64
    worker-1:   libnetfilter_cthelper-1.0.0-15.el8.x86_64
    worker-1:   libnetfilter_cttimeout-1.0.0-11.el8.x86_64
    worker-1:   libnetfilter_queue-1.0.4-3.el8.x86_64
    worker-1:   socat-1.7.4.1-2.el8_10.x86_64
    worker-1:
    worker-1: Complete!
    worker-1: + hostnamectl set-hostname worker-1
    worker-1: + grep -q control-plane /etc/hosts
    worker-1: + echo '192.168.253.128 control-plane'
    worker-1: + swapoff -a
    worker-1: + cp -a /etc/fstab /etc/fstab.bak
    worker-1: + sed -ri '/\sswap\s/s/^#?/#/' /etc/fstab
    worker-1: + setenforce 0
    worker-1: + sed -ri 's/^SELINUX=enforcing$/SELINUX=permissive/' /etc/selinux/config
    worker-1: + cat
    worker-1: + modprobe overlay
    worker-1: + modprobe br_netfilter
    worker-1: + cat
    worker-1: + sysctl --system
    worker-1: * Applying /usr/lib/sysctl.d/10-default-yama-scope.conf ...
    worker-1: kernel.yama.ptrace_scope = 0
    worker-1: * Applying /usr/lib/sysctl.d/50-coredump.conf ...
    worker-1: kernel.core_pattern = |/usr/lib/systemd/systemd-coredump %P %u %g %s %t %c %h %e
    worker-1: kernel.core_pipe_limit = 16
    worker-1: * Applying /usr/lib/sysctl.d/50-default.conf ...
    worker-1: kernel.sysrq = 16
    worker-1: kernel.core_uses_pid = 1
    worker-1: kernel.kptr_restrict = 1
    worker-1: net.ipv4.conf.all.rp_filter = 1
    worker-1: net.ipv4.conf.all.accept_source_route = 0
    worker-1: net.ipv4.conf.all.promote_secondaries = 1
    worker-1: net.core.default_qdisc = fq_codel
    worker-1: fs.protected_hardlinks = 1
    worker-1: fs.protected_symlinks = 1
    worker-1: * Applying /usr/lib/sysctl.d/50-libkcapi-optmem_max.conf ...
    worker-1: net.core.optmem_max = 81920
    worker-1: * Applying /usr/lib/sysctl.d/50-pid-max.conf ...
    worker-1: kernel.pid_max = 4194304
    worker-1: * Applying /etc/sysctl.d/99-kubernetes-cri.conf ...
    worker-1: net.bridge.bridge-nf-call-iptables = 1
    worker-1: net.bridge.bridge-nf-call-ip6tables = 1
    worker-1: net.ipv4.ip_forward = 1
    worker-1: * Applying /etc/sysctl.d/99-sysctl.conf ...
    worker-1: * Applying /etc/sysctl.conf ...
    worker-1: + dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    worker-1: Adding repo from: https://download.docker.com/linux/centos/docker-ce.repo
    worker-1: + dnf install -y containerd.io
    worker-1: Docker CE Stable - x86_64                       794 kB/s |  66 kB     00:00
    worker-1: Last metadata expiration check: 0:00:01 ago on Tue Jul 28 03:53:09 2026.
    worker-1: Dependencies resolved.
    worker-1: ===============================================================================================
    worker-1:  Package             Arch    Version                                    Repository         Size
    worker-1: ===============================================================================================
    worker-1: Installing:
    worker-1:  containerd.io       x86_64  1.6.32-3.1.el8                             docker-ce-stable   35 M
    worker-1: Installing dependencies:
    worker-1:  container-selinux   noarch  2:2.229.0-3.module+el8.10.0+40223+e940a224 appstream          70 k
    worker-1: Enabling module streams:
    worker-1:  container-tools             rhel8
    worker-1:
    worker-1: Transaction Summary
    worker-1: ===============================================================================================
    worker-1: Install  2 Packages
    worker-1:
    worker-1: Total download size: 35 M
    worker-1: Installed size: 117 M
    worker-1: Downloading Packages:
    worker-1: (1/2): container-selinux-2.229.0-3.module+el8.1 676 kB/s |  70 kB     00:00
    worker-1: (2/2): containerd.io-1.6.32-3.1.el8.x86_64.rpm   55 MB/s |  35 MB     00:00
    worker-1: --------------------------------------------------------------------------------
    worker-1: Total                                            28 MB/s |  35 MB     00:01
    worker-1: Docker CE Stable - x86_64                        47 kB/s | 1.6 kB     00:00
    worker-1: Importing GPG key 0x621E9F35:
    worker-1:  Userid     : "Docker Release (CE rpm) <docker@docker.com>"
    worker-1:  Fingerprint: 060A 61C5 1B55 8A7F 742B 77AA C52F EB6B 621E 9F35
    worker-1:  From       : https://download.docker.com/linux/centos/gpg
    worker-1: Key imported successfully
    worker-1: Running transaction check
    worker-1: Transaction check succeeded.
    worker-1: Running transaction test
    worker-1: Transaction test succeeded.
    worker-1: Running transaction
    worker-1:   Preparing        :                                                        1/1
    worker-1:   Running scriptlet: container-selinux-2:2.229.0-3.module+el8.10.0+40223+   1/2
    worker-1:   Installing       : container-selinux-2:2.229.0-3.module+el8.10.0+40223+   1/2
    worker-1:   Running scriptlet: container-selinux-2:2.229.0-3.module+el8.10.0+40223+   1/2
    worker-1:   Installing       : containerd.io-1.6.32-3.1.el8.x86_64                    2/2
    worker-1:   Running scriptlet: containerd.io-1.6.32-3.1.el8.x86_64                    2/2
    worker-1:   Running scriptlet: container-selinux-2:2.229.0-3.module+el8.10.0+40223+   2/2
    worker-1:   Running scriptlet: containerd.io-1.6.32-3.1.el8.x86_64                    2/2
    worker-1:   Verifying        : container-selinux-2:2.229.0-3.module+el8.10.0+40223+   1/2
    worker-1:   Verifying        : containerd.io-1.6.32-3.1.el8.x86_64                    2/2
    worker-1:
    worker-1: Installed:
    worker-1:   container-selinux-2:2.229.0-3.module+el8.10.0+40223+e940a224.noarch
    worker-1:   containerd.io-1.6.32-3.1.el8.x86_64
    worker-1:
    worker-1: Complete!
    worker-1: + mkdir -p /etc/containerd
    worker-1: + containerd config default
    worker-1: + sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
    worker-1: + systemctl daemon-reload
    worker-1: + systemctl enable --now containerd
    worker-1: Created symlink /etc/systemd/system/multi-user.target.wants/containerd.service -> /usr/lib/systemd/system/containerd.service.
    worker-1: + systemctl restart containerd
    worker-1: + cat
    worker-1: + dnf install -y kubelet kubeadm --disableexcludes=kubernetes
    worker-1: Kubernetes                                      262  B/s | 481  B     00:01
    worker-1: Kubernetes                                      4.4 kB/s | 1.7 kB     00:00
    worker-1: Importing GPG key 0x9A296436:
    worker-1:  Userid     : "isv:kubernetes OBS Project <isv:kubernetes@build.opensuse.org>"
    worker-1:  Fingerprint: DE15 B144 86CD 377B 9E87 6E1A 2346 54DA 9A29 6436
    worker-1:  From       : https://pkgs.k8s.io/core:/stable:/v1.36/rpm/repodata/repomd.xml.key
    worker-1: Kubernetes                                       14 kB/s |  13 kB     00:00
    worker-1: Dependencies resolved.
    worker-1: ================================================================================
    worker-1:  Package             Arch        Version                  Repository       Size
    worker-1: ================================================================================
    worker-1: Installing:
    worker-1:  kubeadm             x86_64      1.36.3-150500.1.1        kubernetes       12 M
    worker-1:  kubelet             x86_64      1.36.3-150500.1.1        kubernetes       13 M
    worker-1: Installing dependencies:
    worker-1:  kubernetes-cni      x86_64      1.9.1-150500.1.1         kubernetes      8.8 M
    worker-1:
    worker-1: Transaction Summary
    worker-1: ================================================================================
    worker-1: Install  3 Packages
    worker-1:
    worker-1: Total download size: 34 M
    worker-1: Installed size: 196 M
    worker-1: Downloading Packages:
    worker-1: (1/3): kubeadm-1.36.3-150500.1.1.x86_64.rpm      18 MB/s |  12 MB     00:00
    worker-1: (2/3): kubernetes-cni-1.9.1-150500.1.1.x86_64.r  12 MB/s | 8.8 MB     00:00
    worker-1: (3/3): kubelet-1.36.3-150500.1.1.x86_64.rpm      14 MB/s |  13 MB     00:00
    worker-1: --------------------------------------------------------------------------------
    worker-1: Total                                            36 MB/s |  34 MB     00:00
    worker-1: Kubernetes                                      6.8 kB/s | 1.7 kB     00:00
    worker-1: Importing GPG key 0x9A296436:
    worker-1:  Userid     : "isv:kubernetes OBS Project <isv:kubernetes@build.opensuse.org>"
    worker-1:  Fingerprint: DE15 B144 86CD 377B 9E87 6E1A 2346 54DA 9A29 6436
    worker-1:  From       : https://pkgs.k8s.io/core:/stable:/v1.36/rpm/repodata/repomd.xml.key
    worker-1: Key imported successfully
    worker-1: Running transaction check
    worker-1: Transaction check succeeded.
    worker-1: Running transaction test
    worker-1: Transaction test succeeded.
    worker-1: Running transaction
    worker-1:   Preparing        :                                                        1/1
    worker-1:   Installing       : kubernetes-cni-1.9.1-150500.1.1.x86_64                 1/3
    worker-1:   Installing       : kubelet-1.36.3-150500.1.1.x86_64                       2/3
    worker-1:   Running scriptlet: kubelet-1.36.3-150500.1.1.x86_64                       2/3
    worker-1:   Installing       : kubeadm-1.36.3-150500.1.1.x86_64                       3/3
    worker-1:   Running scriptlet: kubeadm-1.36.3-150500.1.1.x86_64                       3/3
    worker-1:   Verifying        : kubeadm-1.36.3-150500.1.1.x86_64                       1/3
    worker-1:   Verifying        : kubelet-1.36.3-150500.1.1.x86_64                       2/3
    worker-1:   Verifying        : kubernetes-cni-1.9.1-150500.1.1.x86_64                 3/3
    worker-1:
    worker-1: Installed:
    worker-1:   kubeadm-1.36.3-150500.1.1.x86_64          kubelet-1.36.3-150500.1.1.x86_64
    worker-1:   kubernetes-cni-1.9.1-150500.1.1.x86_64
    worker-1:
    worker-1: Complete!
    worker-1: + systemctl enable kubelet
    worker-1: Created symlink /etc/systemd/system/multi-user.target.wants/kubelet.service -> /usr/lib/systemd/system/kubelet.service.
    worker-1: ++ awk '{for (i=1; i<=NF; i++) if ($i=="src") print $(i+1)}'
    worker-1: ++ ip -4 route get 192.168.253.128
    worker-1: ++ head -n1
    worker-1: + NODE_IP=192.168.253.130
    worker-1: + [[ -z 192.168.253.130 ]]
    worker-1: + cat
    worker-1: + systemctl disable --now firewalld
    worker-1: + systemctl daemon-reload
    worker-1: + systemctl restart kubelet
    worker-1: + cat
    worker-1: ++ hostname
    worker-1: ++ cat /etc/redhat-release
    worker-1: ++ uname -r
    worker-1: ++ containerd --version
    worker-1: ++ kubeadm version -o short
    worker-1: ++ kubelet --version
    worker-1: ++ getenforce
    worker-1: + cat /root/worker-info.txt
    worker-1: hostname=worker-1
    worker-1: os=Rocky Linux release 8.10 (Green Obsidian)
    worker-1: kernel=4.18.0-553.el8_10.x86_64
    worker-1: node_ip=192.168.253.130
    worker-1: control_plane_ip=192.168.253.128
    worker-1: containerd=containerd containerd.io 1.6.32 8b3b7ca2e5ce38e8f31a34f35b2b68ceb8470d89
    worker-1: kubeadm=v1.36.3
    worker-1: kubelet=Kubernetes v1.36.3
    worker-1: selinux=Permissive
```

kubelet 패키지를 먼저 활성화하면, 아직 kubeadm이 /var/kib/kubelet/config,yaml을 만들지 않은 상태이므로 서비스가 재시작을 반복할 수 있다.

```
kubelet.service: Started kubelet: The Kubernetes Node Agent.
failed to load kubelet config file:
open /var/lib/kubelet/config.yaml: no such file or directory
kubelet.service: Main process exited, status=1/FAILURE
kubelet.service: Scheduled restart job...
```

그림 4. kubelet이 설정 파일을 아직 생성하지 않음.

## 6. API Server 연결 확인과 kubeadm join

Worker에서 Control Plane API Server의 실제 도달성을 먼저 분리해 확인한다.

```
$ curl -k --connect-timeout 3 https://192.168.253.128:6443/livez
curl: (28) Connection timed out after 3001 milliseconds

$ curl -k --connect-timeout 3 https://192.168.253.128:6443/livez
ok
$ curl -k --connect-timeout 3 https://192.168.253.128:6443/livez
ok
```

연결이 안정된 뒤 토큰과 CA hash를 사용해 join을 실행했다.

```
sudo kubeadm join 192.168.253.128:6443 \
  --token <redacted> \
  --discovery-token-ca-cert-hash sha256:<redacted> \
  --v=5
```

Worker가 Control Plane 인증을 완료하고 클러스터에 등록됨.

```
[kubelet-check] The kubelet is healthy
[kubelet-start] Waiting for the kubelet to perform the TLS Bootstrap

This node has joined the cluster:
* Certificate signing request was sent to apiserver and a response was received.
* The Kubelet was informed of the new secure connection details.
```

kubeadm join 성공은 Node 객체 등록 성공을 의미한다. CNI가 준비되지 않으면 node는 NotReady 이고 일반 Pod를 정상 실행할 수 없다.

### 7. Node NotReady와 Cillium CNI 미설치

Node는 등록되었지만 기존 curl과 nginx Pod는 pending 상태였고, Worker용 Cillium Pod는 Init:0/6에서 진행되지 않았다.

```
cilium-envoy-6fcz4   0/1   ContainerCreating   ...   worker-1
cilium-kmlvw         0/1   Init:0/6            ...   worker-1
kube-proxy-rz5x8     0/1   ContainerCreating   ...   worker-1

curl                 0/1   Pending
nginx                0/1   Pending
```

Worker의 CNI 디렉토리를 직접 확인하자 일반 CNI 플러그인은 존재했지만, Cillium이 설치해야 하는 핵심 파일이 없었다.

```
$ sudo ls -al /etc/cni/net.d
total 0

$ sudo test -f /etc/cni/net.d/05-cilium.conflist \
  && echo "Cilium config exists" \
  || echo "Cilium config missing"
Cilium config missing

$ sudo test -x /opt/cni/bin/cilium-cni \
  && echo "Cilium binary exists" \
  || echo "Cilium binary missing"
Cilium binary missing
```

Cillium DaemonSet에는 install -cni-binaries init container가 있고, Worker의 /opt/cni/bin을 HostPath로 마운트하고 있었다. 따라서 설치 경로보다 Pod Sandbox 자체가 생성되지 않는 상황을 의심했다.

### 8. 결정적 원인: Rocky에 존재하지 않는 resolvConf 경로

k describe pod cillium-kmlvw -n kube-system의 Events에서 직접 확인

```
Warning  FailedCreatePodSandBox
Failed to create pod sandbox:
open /run/systemd/resolve/resolv.conf:
no such file or directory
```

Control Plane의 kubelet 설정이 Ubuntu 환경을 기준으로 /run/systemd/resolve/resolv.conf 를 사용하고 있었고, 이 값이 Rocky Worker의 kubelet 설정에도 적용되었다. 그러나 Rocky Linux에는 해당 파일이 기본적으로 존재하지 않았다.

```
잘못된 resolvConf
-> kubelet이 Pod DNS 파일을 열지 못함
-> Cillium Pod init container 시작 실패
-> install-cni-binaries 미실행
-> /opt/cni/bin/cillium-cni 미생성
-> /etc/cni/net.d/05-cillium.confolist 미생성
-> NetworkPluginNotReady
-> Worker NotReady / 일반 Pod Pending
```

```
sudo vi /var/lib/kubelet/config.yaml

# 변경 전
resolvConf: /run/systemd/resolve/resolv.conf

# 변경 후
resolvConf: /etc/resolv.conf

sudo systemctl restart kubelet
```

/etc/sysconfig/kubelet에는 실제 Worker의 Node IP 명시

```
KUBELET_EXTRA_ARGS=--node-ip=192.168.253.130
```

### 8. Cillium DaemonSet 재생성과 VXLAN 복구

kubelet 설정을 수정한 후 기존 Worker용 Cillium Pod를 삭제했다. Cillium은 DaemoSet이므로 Controller가 동일 노드에 새 Pod를 자동 생성한다

```
kubectl -n kube-system delete pod cillium-kmlvw
kubectl -n kube-system get pods -l k8s-app=cillium -o wide -w
```

1. CNI 설치 

cillium-cni가 Worker의  /opt/cni/bin에 복사되고 05-cillium.conflist가 생성된다

```
[vagrant@worker-1 net.d]$ ip -br addr
lo               UNKNOWN        127.0.0.1/8 ::1/128
eth0             UP             192.168.253.130/24 fe80::20c:29ff:fef5:5d1a/64
cilium_net@cilium_host UP             fe80::a492:8aff:fecd:c8f/64
cilium_host@cilium_net UP             10.0.1.172/32 fe80::84ce:85ff:fe7f:cac0/64
cilium_vxlan     UNKNOWN        fe80::ac53:7fff:fe4e:c68/64
lxc_health@if6   UP             fe80::cc:7dff:fe95:8c7e/64
lxca6d73cdfba6a@if8 UP             fe80::14f9:49ff:feea:5b7a/64
lxcf3cbec6138e4@if10 UP             fe80::d87a:eaff:fe93:43bb/64
lxcf87e3c5340b1@if12 UP             fe80::8073:58ff:fe80:47da/64
lxc34a27d04c153@if14 UP             fe80::a002:7dff:fea6:1efc/64
lxcb4a4e7236e8b@if16 UP             fe80::346a:f8ff:fed7:91a3/64
lxcb2ca45a1e2b1@if20 UP             fe80::5cae:ecff:fefe:5629/64
lxc02344b65a0ac@if22 UP             fe80::54db:d0ff:fe40:6ab4/64
lxc7d5ac68f7f8a@if24 UP             fe80::a800:2aff:fe96:c521/64
lxc84c76dfe23d8@if26 UP             fe80::185e:2ff:fece:2c55/64

```

2. 가상 인터페이스 생성 

Pod namespace의 eth0, veth/lxc, cillium_host, cillium_vxlan이 연결된다.

3. VXLAN 캡슐화

Pod IP 패킷을 Inner Packet으로 유지하고 노드 IP 192.168.253.130 → 192.168.253.128을 Outer packet으로 사용한다

4. VMnet8 Underlay 전송

VXLAN 패킷은 실제 VM NIC인 Worker eth0와 Control Plane ens33사이를 통과한다.


<img width="625" height="313" alt="image" src="https://github.com/user-attachments/assets/84699257-cb3a-4446-a181-a09e9f3be781" />
그림 5. 다른 노드에 존재하는 Pod간의 VXLAN 통신 [출처:https://miro.medium.com/v2/resize:fit:640/format:webp/1*zT08DafNDpuzAx9pKwtTew.png]

| Ethernet | IP | UDP | VXLAN | Ethernet(in) | IP(in) | Payload |

Worker 인터페이스 관찰. CNI namespace와 연결된 veth가 생성됨

```
link/ether 16:f9:49:ea:5b:7a ...
link-netns cni-6647df41-569d-edbf-715a-89133c9372a6
```

linke-netns cni-… 는 인터페이스 반대편이 Pod Sandbox의 네트워크 네임스페이스에 연결되어 있다는 뜻이다.

### 9. Core DNS 문제

Worker와 애플리케이션 Pod 복구

최종 확인 - Pod IP 할당 및 Worker 스케쥴링 성공

```
NAME                    READY   STATUS    IP          NODE
curl                    1/1     Running   10.0.1.17   worker-1
nginx-7f8fbb96d-8hlsm   1/1     Running   10.0.1.67   worker-1

kube-system/cilium-gmcg9   1/1   Running
```

```
open /run/systemd/resolve/resolv.conf: no such file or directory
```

## 왜 이게 문제였나?

Ubuntu는 종종 다음 경로를 DNS 설정 파일로 사용한다.

```
/run/systemd/resolve/resolv.conf
```

하지만 Rocky Linux는 기본적으로 이 경로를 사용하지 않는다.

즉, kubelet이 존재하지 않는 resolv.conf를 참조하도록 설정되어 있었던 것이다.

그 결과:

1. kubelet이 Pod Sandbox 생성 실패

2. Cilium init 단계 실패

3. cilium-cni 설치 실패

4. Node NotReady

라는 연쇄 오류가 발생했다.

### 10. 비슷한 장애에 재사용할 수 있는 점검 순서

```
## 1. 노드 상태
k get nodes -o wide
k describe node worker-1

## 2. CNI Pod 상태
k -n kube-system pods -o wide
k -n kube-system describe pod <worker-cillium-pod>

## 3. Worker CNI 설치 결과
sudo ls -al /etc/cni/net.d
sudo ls -al /opt/cni/bin
sudo test -x /opt/cni/bin/cillium-cni && echo ok

## 4. Kubelet OS 종속 설정
grep -E 'resolvConf|cgroupDriver' /var/lib/kubelet/config.yaml
cat /etc/sysconfig.kubelet

## 5. 서비스 재시작
sudo systemctl restart containerd
sudo systemctl restart kubelet

## 6. DaemonSet Pod 재생성
k -n kube-system delete pod <worker-cillium-pod>


## 7. 인터페이스와 네임스페이스 확인
ip link | grep -E 'cillium|lxc'
ip netns list

## 8. DNS 후속 확인
kubectl -n kube-system get endpoints kube-dns -o wide
kubectl -n kube-system logs -l k8s-app=kube-dns
kubectl exec -it curl -- nslookup kubernetes.default.svc.cluster.local
```

정말 중요한 점은 Cillium binary missing이 원인이 아니라 결과였다는 것이다. 실제 원인은 kubelet이 Rocky linux에 잘못된 경로를 참조해 Pod Sandbox를 만들지 못한것이였다.

반복적으로 컨트롤 플레인 노드에는 테인트 가 적용되어 컨트롤 플레인 팟만 이를 허용하므로 일반 팟은 컨트롤 플레인 노드에서 실행되지 않습니다
