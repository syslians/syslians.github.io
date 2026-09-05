---
title: "OCI E5 절약형 Kubernetes 구축: 필요할 때만 실행하고 cloud-init 실패 복구하기"
date: "2026-09-05T06:55:11.363Z"
categories:
  - "k8s"
  - "cloud"
  - "ubuntu"
  - "network"
author: "현제 김_7254"
slug: "oci_e5_절약형_kubernetes_구축_필요할_때만_실행하고_cloud-init_실패_복구하기"
---

OCI 도쿄 리전에 E5 VM 두 대로 학습용 Kubernetes 클러스터를 구성했다. 각 VM은 1 OCPU·4GB이고, 실습할 때만 시작한 뒤 사용을 마치면 정지하는 방식이다.

VM 생성은 성공했지만 cloud-init의 APT 잠금 충돌로 Kubernetes 초기화가 중단됐다. 복구 전 점검에서 OCI 메타데이터와 호스트 방화벽 설정 문제도 확인했다. 기존 VM에서 스크립트를 수정해 초기화를 다시 실행했고, Control Plane과 Worker의 Ready, CoreDNS와 Flannel의 정상 실행까지 확인했다.

이 글은 E5 구성 결정부터 최초 실행, 장애 진단, 복구, 일상적인 시작·정지까지의 작업 기록이다. 애플리케이션 이미지 빌드와 실제 앱 배포는 이번 검증 범위에 포함하지 않았다.

## 1. E5 절약형 구성으로 변경한 이유

기존 OCI Terraform은 VM.Standard.A1.Flex에 고정되어 있었다. Control Plane은 2 OCPU·8GB, Worker는 1 OCPU·4GB였고, Ubuntu 이미지와 애플리케이션의 노드 선택 조건도 ARM64를 기준으로 작성되어 있었다.

최종 선택은 E5 VM 두 대를 작은 사양으로 구성하고 필요할 때만 실행하는 방식이다. E5가 무료라는 의미는 아니다. VM 크기를 줄이고 실행 시간을 관리하는 것이 이번 구성의 비용 관리 방법이다.

infra/terraform/oci/data.tf의 최종 크기 설정은 다음과 같다.

```
instance_shape         = "VM.Standard.E5.Flex"
control_plane_ocpus    = 1
control_plane_memory_gb = 4
worker_ocpus           = 1
worker_memory_gb        = 4
```

VM Shape만 바꾸면 작업이 끝나지 않는다. Ubuntu 이미지 조회 조건도 E5 호환 이미지로 바꾸고, k8s/api-tester-oci.yaml의 kubernetes.io/arch를 amd64로 변경했다. 이후 앱 이미지를 만들 때도 --platform linux/amd64를 사용해야 한다.

## 2. 1 OCPU는 1 vCPU인가?

이번에 사용한 AMD E5에서는 1 OCPU = 2 vCPU다. 물리 코어 하나의 하드웨어 스레드 두 개를 VM에서 사용할 수 있다. 반면 Ampere A1은 1 OCPU가 1 vCPU에 해당한다. OCPU 숫자만 보고 서로 다른 아키텍처를 비교하면 혼동하기 쉽다. Oracle Compute Shapes

Control Plane에는 CPU가 두 개 이상 필요하므로 E5의 1 OCPU 구성으로 해당 조건을 충족한다. 다만 두 논리 CPU가 물리 코어 두 개와 같은 처리량을 보장한다는 뜻은 아니다. kubeadm 설치 요구 사항

VM의 크기는 Terraform 출력으로 확인할 수 있다.

```
terraform -chdir=infra/terraform/oci output cluster_shapes
```

> [출력 이미지 01 — E5 사양 확인] 위 명령의 두 노드 Shape, OCPU 1, 메모리 4GB, Boot Volume 50GB가 함께 보이는 화면을 첨부한다. OCI 상세 화면을 사용한다면 vCPU 2 항목도 포함한다.

## 3. 최종 아키텍처와 역할 분담

```
관리 PC
  ├─ Terraform / OCI CLI : OCI 리소스와 VM 전원 관리
  ├─ SSH                 : 초기화 복구와 kubeconfig 수집
  └─ kubectl             : Kubernetes 상태 확인 및 앱 배포
          │
          │ 관리 PC의 공인 IP /32에서 SSH 22, API 6443 접근
          ▼
OCI Tokyo / ap-tokyo-1
  VCN: 10.42.0.0/16
  Public Subnet: 10.42.10.0/24
  ├─ api-tester-control-plane
  │    E5 / 1 OCPU / 4GB / Boot 50GB
  │    kube-apiserver, etcd, scheduler, controller-manager
  └─ api-tester-worker
       E5 / 1 OCPU / 4GB / Boot 50GB
       애플리케이션을 배치할 Worker

Pod CIDR: 10.244.0.0/16
CNI: Flannel / VXLAN UDP 8472
Container runtime: containerd
```

두 VM은 공인 IP로 패키지와 컨테이너 이미지를 내려받는다. 별도 NAT Gateway나 Load Balancer는 만들지 않았다. 앱을 배포한 뒤에는 kubectl port-forward로 접근하는 구성을 사용한다.

Control Plane의 taint는 유지한다. Worker에는 workload-pool=worker 라벨을 붙이고, 앱 매니페스트는 이 라벨과 amd64 아키텍처를 선택한다. Control Plane과 Worker가 각각 한 대인 학습 환경이므로 어느 한쪽의 장애나 정지가 곧 서비스 중단으로 이어질 수 있다.

복구 과정에서 확인한 환경은 Ubuntu 24.04.4 LTS, Kubernetes v1.37.0, containerd 2.2.1이었다. Flannel 배포 설정은 v0.28.8이다. 이 버전들은 당시 실습 기록이며, 다른 시점에 따라 할 때는 이미지와 패키지 버전이 달라질 수 있다.

## 4. render-kops-terraform.sh는 어떤 스크립트인가?

파일명에는 kOps가 남아 있지만 현재 OCI 구성은 Terraform과 kubeadm을 사용한다. 이 스크립트는 인자에 따라 준비 검사 또는 VM 전원 관리 스크립트를 호출하는 진입점이다.

기본 실행은 VM을 생성하거나 켜지 않는다. start 역시 새 VM을 만드는 명령이 아니다. 최초 생성은 별도로 Terraform plan과 apply를 실행해야 한다.

관련 파일의 역할도 구분해 두면 오류가 발생했을 때 찾아가기 쉽다.

## 5. 최초 실행 순서

### 도구와 인증 준비

관리 PC에는 OCI CLI, Terraform, kubectl, SSH가 필요하다. 복구 스크립트를 사용할 때는 Python 3도 필요하다. OCI API 인증은 ~/.oci/config, VM 접속은 SSH 키를 사용하며 두 키의 용도는 서로 다르다.

```
cd ~/Test/kubernetes-anotherclass-api-tester

oci --version
terraform version
kubectl version --client
python3 --version
```

아직 변수 파일이 없다면 예제를 복사한다. 이미 설정한 파일은 덮어쓰지 않는다.

```
if [ ! -f infra/terraform/oci/terraform.tfvars ]; then
  cp infra/terraform/oci/terraform.tfvars.example \
    infra/terraform/oci/terraform.tfvars
fi
```

terraform.tfvars에서 본인 Compartment OCID, 관리 PC 공인 IP의 /32, SSH 공개키 경로를 설정한다. 이번 실습은 ap-tokyo-1, 프로필 DEFAULT, SSH 공개키 ~/.ssh/oci-api-tester.pub를 사용했다. 관리 PC 공인 IP가 바뀌면 접근 허용 CIDR도 갱신해야 한다.

### 준비 검사와 VM 생성

```
./infra/scripts/render-kops-terraform.sh
terraform -chdir=infra/terraform/oci plan -out=oci.tfplan
```

계획에서 E5 두 대, 각 1 OCPU·4GB, Boot Volume 각 50GB인지 확인한다. SSH와 Kubernetes API의 외부 접근 범위는 관리 PC /32여야 한다. 기존 VM이 있는 환경이라면 교체나 삭제가 포함됐는지도 확인한다.

> [출력 이미지 02 — 준비 검사와 Terraform 계획] 준비 검사 성공 메시지와 E5 두 대의 계획을 첨부한다. 계정 식별자와 불필요한 실제 공인 IP는 가린다.

계획을 확인한 뒤 적용한다. 이 단계부터 실행 중인 유료 VM이 만들어진다.

```
terraform -chdir=infra/terraform/oci apply oci.tfplan
./infra/scripts/render-kops-terraform.sh status
```

> [출력 이미지 03 — VM 생성 후 전원 상태] apply 완료와 두 VM의 RUNNING 상태를 첨부한다. 이 화면만으로 Kubernetes 준비 완료를 판단하지 않는다.

### kubeconfig 수집과 Worker 가입

정상적인 최초 생성이라면 cloud-init이 각 노드를 초기화한 뒤 다음 명령으로 Worker를 가입시킨다.

```
export SSH_PRIVATE_KEY_PATH="$HOME/.ssh/oci-api-tester"
./infra/scripts/configure-oci-kubectl.sh

export KUBECONFIG="$PWD/.kube/oci-config"
kubectl get nodes -o wide
```

스크립트는 Control Plane에서 유효기간 30분의 가입 명령을 발급해 Worker에서 실행한다. 이때 사용하는 토큰을 Terraform 상태에 저장하지 않는다. 가져온 관리자 kubeconfig는 .kube/oci-config에 권한 0600으로 저장한다.

실제 첫 실행에서는 이 단계에 도달하기 전에 두 VM의 초기화가 실패했다.

## 6. VM은 RUNNING인데 프로비저닝이 실패한 이유

OCI API에서 두 VM 모두 RUNNING이었다. Terraform 상태에도 요청한 E5 사양이 기록되어 있었다. 그러나 SSH로 확인한 cloud-init status --long은 두 노드 모두 error였고, 초기화 완료 마커도 없었다.

```
export SSH_PRIVATE_KEY_PATH="$HOME/.ssh/oci-api-tester"
CP_IP="$(terraform -chdir=infra/terraform/oci output -raw control_plane_public_ip)"
WORKER_IP="$(terraform -chdir=infra/terraform/oci output -raw worker_public_ip)"

ssh -i "$SSH_PRIVATE_KEY_PATH" "ubuntu@$CP_IP" \
  'cloud-init status --long; sudo journalctl -u cloud-final --no-pager -n 60'

ssh -i "$SSH_PRIVATE_KEY_PATH" "ubuntu@$WORKER_IP" \
  'cloud-init status --long; sudo journalctl -u cloud-final --no-pager -n 60'
```

실패 로그의 핵심은 다음과 같았다. PID는 노드마다 달랐다.

```
E: Could not get lock /var/lib/apt/lists/lock.
It is held by process ... (apt)
E: Unable to lock directory /var/lib/apt/lists/
```

> [출력 이미지 04 — 실제 APT 잠금 오류] cloud-init status: error와 /var/lib/apt/lists/lock 오류가 함께 보이는 최초 부팅 로그를 첨부한다.

다른 APT 프로세스가 패키지 목록 잠금을 가진 상태에서 초기화 스크립트의 apt-get update가 실행됐다. 스크립트에는 set -euo pipefail이 설정되어 있었고 재시도 처리가 없어, 명령 실패와 함께 나머지 초기화도 중단됐다. 어떤 서비스가 경쟁 APT 프로세스를 시작했는지까지는 확인하지 않았다.

이 사건에서는 다음 상태를 각각 확인해야 했다.

cloud-init의 마지막 안내 문구에 finished가 있어도 전체 작업 성공을 뜻하지 않을 수 있다. 실제 로그에서도 실패 이후 마지막 문구가 출력됐다. 완료 여부는 종료 상태와 성공 마커, Kubernetes 응답으로 판단하도록 정리했다.

## 7. APT 충돌을 재시도하도록 수정

두 cloud-init 템플릿에서 package_update를 false로 바꾸고, 패키지 작업을 초기화 스크립트의 apt_get 함수로 모았다. OS의 다른 패키지 작업과 경쟁할 가능성은 남으므로 함수 내부에서도 잠금 충돌을 처리한다.

처리 방식은 다음과 같다.

- dpkg 잠금은 DPkg::Lock::Timeout=30으로 대기한다.

- apt-get update의 목록 잠금 오류도 잡을 수 있도록 명령 출력을 확인한다.

- 잠금 오류일 때만 10초 간격으로 최대 30회 시도한다. 각 호출 자체의 대기 시간이 추가될 수 있다.

- 잠금과 무관한 패키지 오류는 즉시 실패로 반환한다.

- 다른 프로세스를 강제 종료하거나 잠금 파일을 삭제하지 않는다.

실행되는 함수의 형태는 다음과 같다.

```
apt_get() {
  local attempt status log
  log=$(mktemp)
  for attempt in $(seq 1 30); do
    if apt-get -o DPkg::Lock::Timeout=30 -o Acquire::Retries=3 \
      -o APT::Update::Error-Mode=any "$@" 2>&1 | tee "$log"; then
      rm -f "$log"
      return 0
    else
      status=${PIPESTATUS[0]}
    fi
    if ! grep -Eq 'Could not get lock|Unable to acquire.*lock|Unable to lock' "$log"; then
      rm -f "$log"
      return "$status"
    fi
    echo "APT lock is busy ($attempt/30); retrying in 10 seconds ..."
    sleep 10
  done
  rm -f "$log"
  return "$status"
}
```

실제 .tftpl 파일에는 Bash 변수 표현이 Terraform 보간으로 처리되지 않도록 status=$${PIPESTATUS[0]}로 저장한다. 렌더링된 셸 스크립트에서는 위 예제처럼 달러 기호가 하나다.

재실행에 필요한 부분도 보강했다. GPG 키 변환에는 --batch --yes를 사용하고, containerd 설정을 쓴 다음에는 서비스를 명시적으로 재시작한다. Control Plane과 Worker는 각자의 완료 마커가 있으면 초기화를 건너뛴다. 기존 /etc/kubernetes/admin.conf가 있으면 kubeadm init을 다시 실행하지 않는다. 다만 이것이 모든 부분 실패를 자동 복구한다는 의미는 아니며, 실패 지점이 다른 경우에는 로그 확인이 필요하다.

## 8. 복구 전 점검에서 발견한 추가 설정 문제

### OCI 메타데이터에는 기대한 publicIp가 없었다

원래 Control Plane 스크립트는 OCI 메타데이터에서 publicIp와 privateIp를 모두 읽어야 다음 단계로 진행했다. 실제 VM 응답의 필드에는 privateIp가 있었지만 publicIp는 없었다. 따라서 APT 오류만 해결해도 기존 코드는 이 조건을 통과할 수 없는 상태였다. OCI 인스턴스 메타데이터

VM 안에서는 아래 명령으로 필드 이름만 확인할 수 있다.

```
curl -fsS -H 'Authorization: Bearer Oracle' \
  http://169.254.169.254/opc/v2/vnics/ | jq '.[0] | keys'
```

> [출력 이미지 05 — OCI 메타데이터 필드] privateIp, vnicId 등의 필드는 있고 publicIp는 없는 출력 화면을 첨부한다.

수정 후에는 사설 IP만 조회해 --control-plane-endpoint와 --apiserver-advertise-address에 사용한다. 관리 PC가 사용할 공인 IP는 Terraform 출력에서 가져온다.

### 공인 IP로 접속하면서 사설 IP 인증서를 검증

API 서버 인증서에는 Control Plane 사설 IP가 포함된다. 관리 PC의 kubeconfig는 접속 주소를 공인 IP로 바꾸고, tls-server-name에는 사설 IP를 지정한다. 접속 목적지와 인증서 이름 검증 값을 분리한 것이다. CA 검증은 그대로 유지한다. kubectl config set-cluster

스크립트의 핵심 동작은 다음과 같다.

```
kubeconfig_cluster="$(kubectl config view --minify \
  -o jsonpath='{.contexts[0].context.cluster}')"
kubectl config set-cluster "$kubeconfig_cluster" \
  --tls-server-name="$control_plane_private_ip"
kubectl get --raw=/readyz --request-timeout=30s
```

설정 확인 시에는 인증서나 개인키가 포함된 kubeconfig 전체 대신 필요한 두 항목만 출력한다.

```
kubectl config view --minify \
  -o jsonpath='{.clusters[0].cluster.server}{"\n"}{.clusters[0].cluster.tls-server-name}{"\n"}'
kubectl get --raw=/readyz
```

> [출력 이미지 06 — API 접속 설정과 readyz] 공인 IP의 접속 주소, 사설 IP의 tls-server-name, /readyz의 ok 응답을 첨부한다. kubeconfig 원문은 캡처하지 않는다.

### OCI 네트워크 규칙 외에 VM 내부 방화벽도 확인

두 Ubuntu VM의 iptables -S INPUT에는 SSH 허용 규칙 뒤에 나머지 트래픽을 거부하는 규칙이 있었다. 이 상태에서는 OCI NSG에서 포트를 허용해도 호스트 방화벽이 API와 노드 간 통신을 막을 수 있다.

```
sudo iptables -S INPUT
```

> [출력 이미지 07 — 수정 전 호스트 방화벽] SSH 22 허용과 마지막 REJECT --reject-with icmp-host-prohibited가 보이는 진단 당시 출력을 첨부한다. 복구 후에는 허용 규칙이 추가되어 있으므로 전후 상태를 구분한다.

기존 방화벽을 유지하면서 다음 규칙을 추가했다.

추가 규칙은 기존 거부 규칙보다 먼저 평가되도록 넣고, 중복 여부를 확인한 뒤 삽입한다. iptables-persistent를 사용하며 iptables-save로 /etc/iptables/rules.v4에 저장했다. 외부 노출 범위는 OCI NSG 규칙과 함께 제한된다.

## 9. 기존 VM에서 초기화 복구

이번에는 생성된 VM을 그대로 사용했다. recover-oci-bootstrap.sh가 현재 Terraform 변수로 동일한 cloud-init 템플릿을 렌더링하고, Terraform 상태의 두 VM IP로 SSH 접속해 수정된 셸 스크립트를 적용한다.

```
./infra/scripts/render-kops-terraform.sh status

export SSH_PRIVATE_KEY_PATH="$HOME/.ssh/oci-api-tester"
./infra/scripts/recover-oci-bootstrap.sh
./infra/scripts/configure-oci-kubectl.sh
```

복구 스크립트는 Control Plane, Worker 순서로 실행한다. 원래 초기화 스크립트는 .pre-recovery 이름으로 보관하고, 작업이 성공한 노드에는 완료 마커를 남긴다. 이 작업은 Terraform apply나 VM 재생성을 실행하지 않는다.

> [출력 이미지 08 — 초기화 복구 성공] Control Plane 초기화 성공과 Bootstrap completed가 보이는 복구 로그를 첨부한다. 로그에 가입 토큰이 포함되어 있다면 가린다.

완료 마커는 다음 두 파일이다.

```
Control Plane: /var/lib/kubernetes-bootstrap-complete
Worker:        /var/lib/kubernetes-worker-prepared
```

configure-oci-kubectl.sh도 이 마커를 기준으로 준비 여부를 판단하도록 바꿨다. 수동 복구 후에는 최초 부팅의 cloud-init 실패 기록이 남을 수 있어, 그 기록만 검사하면 이미 복구된 VM을 계속 실패로 판단하기 때문이다.

Worker 가입 전에는 /readyz로 API 응답을 확인하고, Worker 노드가 실제로 없는 경우에 가입 명령을 실행한다. API 인증이나 통신 오류를 단순히 "Worker가 없다"로 취급하지 않도록 했다. 가입 후에는 workload-pool=worker 라벨을 설정하고 두 노드 모두 Ready가 될 때까지 기다린다.

> [출력 이미지 09 — Worker 가입과 두 노드 Ready] Worker 가입 완료, 라벨 설정, Control Plane과 Worker의 Ready 상태가 보이는 설정 스크립트 출력을 첨부한다.

## 10. 최종 검증 결과

복구 후 관리 PC에서 다음 명령을 실행했다.

```
export KUBECONFIG="$PWD/.kube/oci-config"

kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl -n kube-system rollout status deployment/coredns --timeout=120s
kubectl -n kube-flannel rollout status daemonset/kube-flannel-ds --timeout=120s
```

확인한 두 노드는 api-tester-control-plane, api-tester-worker이고 모두 Ready였다. 아키텍처는 amd64, Kubernetes 버전은 v1.37.0, 런타임은 containerd://2.2.1이었다.

시스템 Pod 10개는 모두 1/1 Running이었고 관찰 시점의 재시작 횟수는 0이었다. 구성은 Flannel 2개, CoreDNS 2개, kube-proxy 2개, etcd·API 서버·controller-manager·scheduler 각 1개다. CoreDNS Deployment와 Flannel DaemonSet의 rollout도 성공했다.

> [출력 이미지 10 — 최종 노드 상태] kubectl get nodes -o wide에서 두 노드의 Ready, 버전, OS, containerd 정보를 확인할 수 있는 화면을 첨부한다.

> [출력 이미지 11 — 시스템 Pod와 rollout] kubectl get pods -A -o wide의 10개 시스템 Pod와 CoreDNS·Flannel rollout 성공 출력을 첨부한다.

kubectl get nodes의 EXTERNAL-IP가 <none>으로 보이더라도 OCI 공인 IP가 없다는 뜻은 아니다. 이번 구성에서는 관리 PC가 Terraform 출력의 공인 IP를 통해 API에 접속하는 것까지 확인했다.

코드 수준 검증도 수행했다. Terraform validate, fmt -check, 렌더링한 YAML과 Bash 구문 검사를 통과했다. 전원 관리 스크립트는 시작·정지 순서, 이미 목표 상태인 경우, 실패 처리 등을 포함한 11개 테스트를 통과했다. APT 함수는 두 템플릿 각각에 대해 즉시 성공, 잠금 후 성공, 재시도 소진, 일반 오류 즉시 실패의 총 8개 하위 시나리오를 검증했다.

재확인 명령은 다음과 같다.

```
terraform -chdir=infra/terraform/oci fmt -check
terraform -chdir=infra/terraform/oci validate
python3 -B -m unittest discover -s infra/scripts/tests -v
```

이 결과는 클러스터 초기화와 기본 시스템 구성의 정상 상태를 확인한 기록이다. Spring 앱 배포, 앱 API 응답, 노드 정지·재시작 후의 실제 서비스 복구나 별도 Pod 간 통신 테스트까지 완료했다는 뜻은 아니다.

## 11. 실습할 때만 시작하고 끝나면 정지

초기 구성과 Worker 가입이 끝난 뒤에는 매번 Terraform apply를 실행할 필요가 없다.

```
# 실습 시작
./infra/scripts/render-kops-terraform.sh start

export KUBECONFIG="$PWD/.kube/oci-config"
kubectl wait --for=condition=Ready nodes --all --timeout=10m
kubectl get nodes

# 실습 종료
./infra/scripts/render-kops-terraform.sh stop
./infra/scripts/render-kops-terraform.sh status
```

start는 Control Plane → Worker 순서로 시작하고 OCI의 RUNNING 상태를 기다린다. Kubernetes 준비는 이어지는 kubectl 명령으로 확인한다. stop은 Worker → Control Plane 순서로 OCI SOFTSTOP을 호출하고 STOPPED 상태를 기다린다. 이미 목표 상태인 VM에는 같은 요청을 다시 보내지 않는다.

정지 중 한 VM에서 오류가 나더라도 다른 VM의 정지는 시도한다. 일부 정지가 실패하면 실패 코드와 안내 메시지를 반환하므로 status로 확인하고 다시 시도한다. 전환 중인 상태에서는 반대 전원 요청을 바로 보내지 않고, 현재 전환이 끝난 뒤 재실행하도록 안내한다.

> [출력 이미지 12 — 실습 종료 후 정지 확인] 다음 실습을 마친 뒤 status에서 두 VM 모두 STOPPED인 화면을 첨부한다. 이번 복구 완료 시점에는 사용을 위해 두 VM을 실행 상태로 유지했으며, 이 이미지는 아직 촬영하지 않은 후속 확인 자리다.

Terraform 인스턴스에는 아래 설정을 추가했다. 정지한 기존 VM의 전원 상태를 일반 apply가 다시 바꾸지 않도록 한 것이다. VM 교체나 새 생성이 계획된 경우에는 새 VM이 실행 상태로 만들어질 수 있으므로 계획을 확인해야 한다.

```
lifecycle {
  ignore_changes = [state]
}
```

정지하면 VM과 Boot Volume을 보존하므로 다음에 같은 클러스터를 다시 사용할 수 있다. 터미널을 닫거나 SSH 연결을 끊는 것만으로 VM이 정지하지는 않는다. 시작 시점의 OCI 가용 용량에 따라 재시작이 실패할 가능성도 있다.

Standard Flex는 정지 상태에서 Compute 과금이 중단되지만, Boot Volume과 Registry 등 보존한 리소스의 비용은 별도로 남을 수 있다. OS 내부의 shutdown만 사용하지 않고 OCI API로 정지한 뒤 상태를 확인한다. Oracle Compute 과금 FAQ, OCI 인스턴스 정지

자동 시작 스케줄은 등록하지 않았다. retry-oci-capacity.sh도 명시적으로 실행해야 작동하는 별도 도구이며, 일상적인 시작·정지 절차에서는 사용하지 않는다. 현재 start, stop 경로는 Terraform 출력에 저장된 두 VM ID, 리전, 프로필만 대상으로 한다.

## 12. 다시 문제가 생겼을 때 확인할 순서

VM에 접속할 수 없으면 먼저 status와 관리 PC의 /32 접근 허용 범위를 확인한다. VM은 실행 중인데 Kubernetes에 연결되지 않으면 cloud-init·bootstrap 로그와 API 접근 경로를 본다. API는 정상인데 Worker가 준비되지 않으면 Worker 가입 상태, kubelet, CNI 순서로 좁혀 간다.

```
# 관리 PC: 현재 전원 상태
./infra/scripts/render-kops-terraform.sh status

# 관리 PC: Kubernetes API, 노드, 시스템 Pod
export KUBECONFIG="$PWD/.kube/oci-config"
kubectl get --raw=/readyz --request-timeout=30s
kubectl get nodes -o wide
kubectl get pods -A -o wide
```

VM 내부에서 볼 로그는 다음과 같다.

```
# 공통
cloud-init status --long
sudo journalctl -u cloud-final --no-pager -n 100
sudo journalctl -u kubelet --no-pager -n 100
sudo iptables -S INPUT

# Control Plane
sudo tail -n 100 /var/log/bootstrap-kubernetes.log

# Worker
sudo tail -n 100 /var/log/prepare-kubernetes-worker.log
```

복구가 끝난 환경에서 과거 cloud-init 오류만 보고 VM을 다시 만들 필요는 없다. 완료 마커와 실제 API·노드 상태를 함께 확인한다. 반대로 RUNNING만으로 프로비저닝 성공을 판단해서도 안 된다.

Terraform 상태 파일은 이 스크립트들이 VM을 찾는 기준이다. .kube/oci-config, SSH 개인키, OCI API Key, 가입 토큰과 함께 Git에 올리지 않고 관리한다. 템플릿 수정 이후 기존 VM에 apply할 때는 교체 계획 여부를 먼저 확인한다.

## 관련 코드와 문서

이번 글은 이 프로젝트의 로컬 작업 트리와 2026년 9월 5일 실행 로그를 기준으로 작성했다. 아래 GitHub 주소는 프로젝트 원격 저장소이며, 이번 수정분의 커밋·푸시는 수행하지 않았다.

- 프로젝트: kubernetes-anotherclass-api-tester

- 로컬 상세 가이드: docs/OCI_ARM_KUBEADM_DEPLOYMENT_GUIDE.md — 파일명은 이전 ARM 구성이지만 본문은 E5 구성과 복구 절차로 갱신했다.

- VMware + Vagrant + kubeadm + Cilium 트러블슈팅 기록 — 다른 실습 환경의 Worker 가입·CNI 진단 기록.

- Oracle Compute Shapes

- kubeadm 설치 요구 사항

- OCI 메타데이터

- kubectl config set-cluster