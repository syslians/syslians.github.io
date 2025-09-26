## Terraform

<img width="2048" height="1152" alt="image" src="https://github.com/user-attachments/assets/c9f46544-aea3-4a15-922f-2bddd6c02108" />

                                                [Terraform 구조 1]





<img width="2400" height="870" alt="image" src="https://github.com/user-attachments/assets/18b79d36-f693-4a48-80fb-8b13bd675620" />

`출처: https://github.com/user-attachments/assets/18b79d36-f693-4a48-80fb-8b13bd675620 [Terraform 구조 2]`

<img width="3276" height="1564" alt="image" src="https://github.com/user-attachments/assets/c98a5d0d-4f3b-4ac2-808d-b063504533cd" />
`출처: https://github.com/user-attachments/assets/c98a5d0d-4f3b-4ac2-808d-b063504533cd [Terraform 구조 3]`


이글은 Terraform 실행(특히 terraform apply)시 내부에서 실제로 무슨 일이 일어나는지 단계별, 구체적으로
정리한 내용입니다. 큰 그림으로 보자면 실행 흐름은 아래와 같습니다.


### Terraform 실행 흐름
```text
구성 로드 -> 상태(및 실제 리소스) 동기화 -> 의존성 그래프(DAG) 생성 -> Plan 생성 -> 승인 -> apply
```
순으로 진행되고, 그 과정에서 Provider 플러그인과 RPC로 대화하고 상태(backend)를 잠그고 갱신합니다.

<img width="524" height="736" alt="image" src="https://github.com/user-attachments/assets/384cf4fd-38f7-4387-89b2-a1bc0957d62d" />



### 0. 사전 조건 (꼭 확인할 것)
- 작업 디렉토리가 terraform init으로 초기화되어 있어야 함. (.terraform/ 에 provider 모듈 등 존재.)
- 원격 상태(backend)를 사용하면 locking(예: S3 + DynamoDB 또는 S3 native locking 등)설정이 있어야 동시성
  문제를 방지
- 필요한 변수 / Credential / Key 들이 준비되어 있어야 함.

### 1. terraform apply 를 실행했을 때의 전체 흐름
1. CLI Flag/인자 Parsing(-var, -parallelsim, -refresh=false 등)
2. 작업 디렉토리 초기화 검사(init 필요 여부)
3. 구성 파일(.tf)과 모듈 로드 -> 변수/locals 평가 -> HCL 해석
4. (필요시) 모듈/Provider 확인 및 다운로드(보통 init에서)
5. 상태(State) 로드(backend에서 최신 state 가져오기) 및 잠금(lock) 획득
6. (기본) Refresh: 현재 실제 리소스 상태를 Provider에 질의하여 상태를 갱신(옵션으로 끌 수 있음)
7. 의존성 그래프(Dependency Graph) 생성 - 리소스간의 의존성을 분석해 노드/엣지 구성
8. 계획(plan) 생서이 현재 상태 vs 선언된 구성의 차이를 계산해 실행계획(추가/변경/삭제)을 만듬
   - terraform plan -out=fplan으로 plan 바이너리 저장 가능.
9. (plan 파일을 전달하지 않았다면) 사용자에게 계획 요약을 보여주고 승인 대기(또는 -auto-approve)
10. Apply 단계 시작: (plan 파일을 사용하면) 해당 plan을 실행. 아니라면 위에서 생성한 plan을 즉시 실행.
11. 실행 중 Provider와 통신(RPC) - 각 리소스에 대해 PlanResourceChange -> ApplyResourceChange 등 호출.
12. 각 리소스가 성공적으로 처리되면 stae를 업데이트하고 원격 backend에 write(중간 persist)
13. 모든 작업 완료 후 outputs 계산, lock 해제. 결과 출력
14. 에러/중단 시: 일부 리소스가 생성되었지만 상태가 불안정할 수 있으므로 수동 복구/재실행 필요(apply 중단은 위험)

---------------------------------------------------------------------------------------------------------------------------

### 2. 상세 단계 - 구성 로드부터 그래프 생성까지

1. 구성 파일(.tf) 읽기 & 문법 파싱
   - 모든 .tf 파일을 읽어 HCL AST로 파싱. 변수, locals, 함수 호출, interpolation 등을 평가.

2. 모듈 해석
   - module 블록이 있으면 모듈 소스(레지스트리, Git, Local) 가져오기. (보통 init에서 다운로드)

3. 변수/값 설정
   cli 인자. -var-file. 환경변수 등에서 변수 값을 결정.

4. 의존성(implicit/explicit) 파악
   - 리소스 속성 내에서 다른 리소스의 속성을 참조하면 그걸 기반으로 의존성 연결을 만듦. depnds on은 명시적
     의존성

5. 의존성 그래프 생성
   - Terraform이 내부적으로 노드(리소스, provider-config 등)를 만들고 Edge로 연결함. 그래프는 나중에 병렬
     실행과 순서 결정을 위해 사용됩니다.

---------------------------------------------------------------------------------------------------------------------------

### 3. 상태(state) 처리 & Refresh 단계(중요)
- Terraform은 먼저 현재 저장된 state(로컬 파일 혹은 원격 backend)를 불러옵니다.
- 기본 동작: plan/apply 수행 전에 Terraform(대부분의 경우) Provider들을 호출해 실제 리소스의 최신 속성을
  읽어 state를 메모리(또는 -refresh-only는 파일)로 갱신(refresh) 합니다. (이 동작은 기본 값이며 -refresh=false로
  끌 수 있음)
- 이유: 외부에서 사람이 콘솔로 변경한 값(드리프트)을 반영해서 올바른 plan을 만들기 위해서.
- Remote backend를 쓰는 경우 이 시점에 state-lock을 획득해 다른 동시 변경을 방지함(ex: S3 + DynamoDB 또는 S3 native locking)

---------------------------------------------------------------------------------------------------------------------------

### 4. Plan(계획) 생성 (무엇이 어떻게 바뀌는지 계산)
- 현재(갱신된) state와 선언된 구성(코드)을 비교하여 각 리소스를 destroy + create 로 분리해서 그래프 상에서 서로 다른 노드로
  취급(destroy 순서와 생성 순서가 다를 수 있음.)
- terraform plan -out=xxx 로 실행하면 바이너리 plan 파일에 위의 계획을 저장할 수 있음. 이 파일은 그대로 terrfaorm apply xxx로
  재사용 가능

---------------------------------------------------------------------------------------------------------------------------

### 5. Apply 실행(승인 후 실제 적용) - Provider 상호작용(핵심)
- apply는 plan에 따라 실제 Provider API를 호출해 리소스를 변경합니다. 내부적으로는 Terraform Core <-> Provider
  플러그인(프로토콜: gRPC/protobuf) 방식으로 통신합니다. 주요 RPC 흐름(간소화)
  1. GetProviderSchema / ConfigureProvider (프로바이더 초기화)
  2. UpgradeResourceState (기존 state와의 호환성 검사)
  3. ReadResource (존재 리소스 읽기 - refresh 시)
  4. PlanResourceChange (변경 계획을 provider 에게 확인/보정)
  5. ApplyResourceChange (실제 API 호출로 리소스 생성/수정/삭제)
     
- 이 RPC 단계는 provier마다 구현 세부가 다르지만, 핵심은 Terraform Core가 provicer와 계약된 RPC로
  CRUD(및 읽기/계획/적용)을 수행한다는 점입니다.

추가 포인트:
- 병렬성(parallelism): 그래프 상에서 의존관계가 해결된 노드들은 병렬로 실행(기본 동시성 10개, -parallelism으로 조절 가능)

- Provisioners: 리소스 생성 직후(또는 삭제 직전) 실행되는 local-exec/remote-exec 같은 프로비저너는 적용 흐름에
  끼어듭니다.(단, 권장사항은 '최후의 수단'으로만 사용) 생성/삭제 시의 실행 시점 규칙이 문서화되어 있습니다.

---------------------------------------------------------------------------------------------------------------------------

### 6. State(상태) 업데이트 & 잠금 해제
- 각 리소스 작업이 성공적으로 끝나면 Terraform은 state를 갱신하여 로컬 또는 원격 backend에 기록합니다.
  (원격 backend인 경우 write + 버전 처리/locking 동작이 발생)
- apply가 끝나면 lock을 해제하고, outputs을 계산해 사용자에게 출력합니다.
- 주의: 중간에 강제 종료(Ctrl + C 등)하거나 네트워크 문제 발생 시 state와 실제 리소스가 불일치 상태가 될 수 있으니
  복구가 필요할 수 있음. (실제 사례/문제 사례는 커뮤니티 이슈들이 있음)

---------------------------------------------------------------------------------------------------------------------------

### 7. terraform apply vs terraform apply <saved-plan>의 차이 (중요)
- 일반 terraform apply: 내부적으로 plan을 실행(기본적으로 refresh 포함) -> 변경 계획 보여주고 승인 -> apply
- terraform plan -out=tfplan -> terraform apply: tfpan: 이미 계산된 plan(바이너리)을 그대로 신뢰하고 적용. 이 경우 Terraform은 새로
  plan 생성 시점 이후에 발생한 외부 변경(state 변경)이 있으면 plan이 state(더 이상 적용 불가)할 수 있음. 주의 필요

---------------------------------------------------------------------------------------------------------------------------

### 8. 에러/충돌/동시성 관련 주의 사항
- 동시 실행 금지: 같은 state에 대해 동시 apply는 상태 손상 위험 -> backend lock 필요(ex: S3 + DynamoDB 또는 S3 native)
- plan-apply 간격: plan을 만들고 상당 시간이 지난 뒤 apply 하면 state가 변경되어 plan이 stale해질 수 있음. 가능한 한 plan-out ->
  바로 apply tfplan 흐름 권장(또는 CI에서 atomic하게 처리)
- 프로비저너 실패: provisoiner 실패는 apply 실패로 이어지고, destroy-time provisioner는 실패 시 재시도/수동 처리 필요.

---------------------------------------------------------------------------------------------------------------------------

### 9. 한눈에 보는 실행 흐름 (단계별 요약)
1. terraform init (사전) - provisoner/module 준비
2. terraform apply 호출 -> CLI 인자 파싱
3. 구성 읽기 -> 변수 해석 -> modules 불러오기
4. backend에서 state 로드 -> state lock 획득(원격 backend일 경우)
5. (기본) refresh: provider에 질의하여 현재 리소스 상태 반영
6. 의존성 그래프 생성(노드 엣지) -> plan 생성(차이 계산)
7. plan을 출력/저장(-out) -> 승인
8. apply: Provider RPC로 PlanResourceChange -> ApplyResourceChange 수행
9. 각 리소스 성공 시 state 갱신/원격에 쓰기 -> 모든 작업 완료 -> outputs 계산 -> lock 해제
10. 종료

다시 실행흐름을 정리 해보겠습니다.

1️⃣ Terraform 전체 실행 흐름
```
[ Parse HCL ] 
      ↓       
[ Build Dependency Graph ] 
      ↓                   
[ Plan Phase ]
      ↓        
[ Apply Phase ] 
      ↓       
[ Provision Resources (gRPC → Provider Plugins) ] 
      ↓          
[ Update State ] 
```



```
2️⃣ Apply 단계
시간 →   0s       1s       2s       3s       4s       5s       6s
----------------------------------------------------------------------
parent.resource_a  |==== 실행 중 ====|
parent.resource_b  |== 실행 완료 ==|
child.resource_c                       |== 실행 ==|
child.resource_d                                |== 실행 ==|

- parent.resource_a -> child.resource_c -> child.resource_d 순차 실행
- parent.resource_b 는 독립적이므로 동시에 실행 가능
- Terraform 내부에서는 각 리소스를 goroutine으로 실행하고, **의존성 그래프(DAG)**로 동기화
```



🏗 Terraform 실행 구조

1. Terraform Core
  - 하나의 싱글 프로세스로 동작
  - plan, apply, graph 같은 로직을 담당
  - 의존성 그래프를 만들고, 각 리소스를 언제 병렬 실행할지 스케쥴링

2. Provider Plugins
   - Core가 직접 리소스를 만들지 않음
   - 외부 바이너리(별도 프로세스)로 실행됨
   - Core <-> Provider 간은 gRPC (IPC 방식)로 통신
     ex: terraform-provider-aws, terraform-provider-azurerm, terraform-provider-kubernetes ...
즉, Core는 AWS에서 EC2 생성 명령을 Provider에게 gRPC로 보내고, Provider 프로세스가 실제 AWS API를 호출해서
EC2를 생성하는 구조입니다.

⚡ 정리
-✅ Terraform Core -> 싱글 프로세스
-✅ Provider -> 별도 프로세스 (여러 개 동시 실행 가능)
-✅ Core는 goroutine으로 병렬 스케쥴링을 하고, Provider 호출은 gRPC IPC를 통해 다른 프로세스로 분리

```
┌───────────────────────────────┐
│         Terraform Core         │  (싱글 프로세스)
│  - HCL Parsing                 │
│  - Dependency Graph (DAG)      │
│  - Plan/Apply Engine           │
│  - goroutine 스케줄링          │
└───────────────┬───────────────┘
                │  gRPC (IPC)
                │
 ┌──────────────▼────────────────┐
 │       Provider Plugin          │  (별도 프로세스)
 │  - terraform-provider-aws      │
 │  - terraform-provider-azurerm  │
 │  - terraform-provider-k8s      │
 │  ...                           │
 │  (각 Provider는 실제 API 호출)   │
 └────────────────────────────────┘
```

```
⏱ Terraform 실행 타임라인 (예시)
시간 →   0s       1s       2s       3s       4s       5s
-------------------------------------------------------------

Terraform Core (goroutines)
   ├─ goroutine A: [ parent.resource_a 실행 요청 ]─────┐
   ├─ goroutine B: [ parent.resource_b 실행 요청 ]──┐ │
   │                                                 │ │
   ▼                                                 ▼ ▼

Provider 프로세스 (gRPC IPC)
   ├─ provider-aws:  EC2 생성 API 호출  ───────────────┐
   ├─ provider-aws:  S3 Bucket 생성 API 호출 ────────┐│
   │                                                 ││
   ▼                                                 ▼▼

Cloud API (AWS 등)
   ├─ EC2 생성 처리 중 … 완료 (3s)  ────────────────▶ Core 응답
   ├─ S3 생성 처리 중 … 완료 (2s)  ────────────────▶ Core 응답
```

- Core는 싱글 프로새스
- Provider는 외부 바이너리로 띄워지고, Core와 gRPC로 통신
- Core가 스케쥴링한 실행 단위는 goroutine에서 동작하고,
  Provider 호출시에는 별도 프로세스에서 처리

⚡ 네트워크 작업은 비동기 
1. Core가 goroutine에서 리소스 실행 결정
2. gRPC를 통해 Provider 프로세스에 요청 전송
3. Provider는 API 요청(ex: AWS EC2 생성)을 비동기 네트워크 호출로 처리
   - Go의 네트워크 라이브러리는 기본적으로 Non-blocking I/O
   - 따라서 동시에 여러 Provider 요청을 날려도 Core 레벨에서 병렬 실행처럼 동작
4. 응답이 오면 Core가 받아서 State 갱신

Terraform은 싱글 프로세스인가?
- Core만 보면 싱글 프로세스이지만, 전체 실행 환경은 멀티 프로세스 구조(Core + 여러 Provider)

✅ 결론
- Core -> 싱글 프로세스 + goroutine 기반 병렬 스케쥴링
- Provider -> 별도 프로세스 (멀티), Core와 gRPC IPC
- Provider 네트워크 호출은 비동기적으로 처리되므로, 수십개 리소스도 동시 실행 가능

```

```



-------------------------------------------------------------

Terraform Core (State Update)
   - EC2 완료 이벤트 수신 → child.resource_c 실행
   - S3 완료 이벤트 수신 → 병렬 실행 계속

### 핵심 포인트
- Core는 goroutine을 통해 동시에 여러 Provider에 실행 요청을 보냄
- Provider는 별도 프로세스에서 Cloud API 호출 수행
- 네트워크 호출은 비동기(Non-blocking I/O)라, EC2 실행은 오래 걸리고 S3는 빨리 끝나더라도
  Core가 각각 완료 이벤트를 받아 다음 DAG 노드를 실행
- 최종적으로 모든 결과는 State에 반영

👉이렇게 보시면, Terraform이 단순히 싱글 프로세스가 아니라 Core(싱글) + Provider(멀티) + Cloud API(비동기) 구조라는것이 핵심


----------------------------------------------------------------------------------------------------------------------------

### Terraform 의존성 그래프
Terraform은 리소스 간의 의존성을 분석해 DAG(Directed Acycling Graph)를 만듭니다. 이 그래프는 리소스 생성/변경/삭제 
순서를 결정하는데 사용되는 중요한 자료구조입니다. 아래는 실제로 terraform의 graph 명령어 사용시 생성되는 그래프입니다. 

![Terraform 의존성 그래프](https://web-unified-docs-hashicorp.vercel.app/api/assets/terraform/latest/img/docs/graph-example.png)

- 사각형(aws_route53_record, aws_elb.www, aws_instance.test 등) AWS 리소스를 나타냅니다.
  사각형 안에 있는 이름은 일반적으로 리소스_타입.리소스 이름 형식으로 구성됩니다.

- 타원(aws_instance.test): 일반적으로 다른 리소스를 구성하는데 사용되는 그룹이나 모듈을 나타낼 수 있습니다. 이는 로드밸런서가 트래픽을 전달할 EC2
  인스턴스들이 먼저 생성되어야 함을 나타냅니다.

- aws_instance.test: 이 그룹 또는 모듈은 aws_instance.test.0, aws_instance.test.1, aws_instance.test.2 라는 세 개의 개별 인스턴스에
  의존하고 있습니다. 이는 이 인스턴스들이 먼저 생성되어야 그룹으로 묶일 수 있다는 것을 의미합니다.

- aws_instance.test.0, aws_instance.test.1, aws_instance.test.2: 이 세개의 EC2 인스턴스는 모두 provider.aws에 직접 의존하고 있습니다. 
  즉, AWS 프로바이더가 구성되면 이 인스턴스들을 생성할 수 있습니다.

- Provider.aws: 모든 리소스의 최하단에 위치하며, 모든 리소스가 최종적으로 AWS 프로바이더에 의존하고 있음을 나타냅니다. 모든 리소스가 AWS 환경 내에서
  생성되기 때문에 가장 기본적인 의존성이라고 볼 수 있습니다.

이 그래프는 Terraform 공식 사이트에 나와있는 웹 서비스의 아키텍쳐 스키마와 유사하며, DNS 레코드(www)가 로드 밸런서(ELB)로 트래픽을 보내고, 로드밸런서는 다시
여러개의 EC2 인스턴스(test.0, test.1, test.2)로 트래픽을 분산하는 일반적인 웹 서비스 구성입니다.

의존성 그래프는 IAc 도구에서 리소스 배포의 순서와 방식을 결정하는데 매우 중요한 역할을 합니다. 이는 리소스를 통해 생성, 업데이트, 삭제할때 안전하고 효율적인 시스템을
보장하는 핵심적인 역할을 합니다.

의존성 그래프는 어떤 리소스가 먼저 생성되어야 하는지를 보여줍니다. 화살표가 시작되는 리소스(부모)가 먼저 생성되어야 화살표가 끝나는 리소스(자식)를 성공적으로 배포할 수 있습니다.

### Terraform Module
Terraform Module은 코드 베이스를 논리적으로 분리하여 각각의 인프라 리소스를 독립적으로 관리할 수 있게 해주는 문법입니다.
한 인프라를 여러 프로젝트로 나누어 관리할 수 있게 되어 중복되는 코드를 줄여 재사용성과 유지보수성을 크게 향상시킬 수 있는 특징을
가지고 있습니다.

![Terraform Module 구조](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2F0bkpq%2FbtsIsMyyN2I%2FAAAAAAAAAAAAAAAAAAAAAJ_ewh2EDdWr_KAJFql0X7VJ1nhJ0kBQf1BI_a49UglM%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1759244399%26allow_ip%3D%26allow_referer%3D%26signature%3DpdVlignRN%252Bw6gY40pYgTgcq0R8w%253D)

모듈은 Root Module과 Child Module로 나눌 수 있습니다. Root Module은 최상위 디렉토리에 위치하며, Child Module은 Root Module에서 호출되는 하위 모듈입니다.

### Terraform Module이 필요한 이유
모듈은 테라폼 구성의 집합으로 테라폼으로 관리하는 대상의 규모가 커지고 복잡해져 생긴 문제를 보완하고 관리하는 작업을 효율적으로 하기 위한 방안으로 활용됩니다. 즉, 하나 이상의 tf 파일이 있는 단일
디렉토리 구조로 구성된 간단한 구조도 모듈로 볼 수 있습니다. 
이러한 디렉토리에서 직접 terraform 명령어로 실행하면 루트 모듈로 간주됩니다.

예를 들어, 초기 설정을위해 VPC, 서브넷, 라우팅 테이블, 인터넷 게이트웨이 등을 설정하는 코드를 작성한다고 가정해봅시다.
이러한 설정은 대부분의 AWS 인프라에서 공통적으로 사용되기 때문에, 이를 매번 새로 작성하는 것은 비효율적입니다.
이럴 때, 이러한 공통 설정을 하나의 모듈로 만들어두면, 다른 프로젝트에서도 쉽게 재사용할 수 있습니다. 

**관리성** 
- 모듈을 서로 연관 있는 구성의 묶음
- 원하는 구성요소를 단위별로 쉽게 찾고 업데이트를 할 수 있습니다
- 모듈은 다른 구성에서 쉽게 하나의 덩어리로 추가하거나 삭제할 수 있습니다
- 모듈이 업데이트되면 이 모듈을 사용하는 모든 구성에서 일관된 변경작업을 진행할 수 있습니다.

**캡슐화**
- 테라폼 구성 내에서 각 모듈은 논리적으로 묶여져 독립적으로 프로비저닝 및 관리되며, 그 결과는 은닉성을 갖춰 필요한 항목만 외부에 노출합니다

**재사용성**
-구성을 처음부터 작성하는 것에는 시간과 노력이 필요하고 작성 중간에 디버깅과 오류를 수정하는 반복작업이 발생합니다
- 테라폼 구성을 모듈화하면 이후에 비슷한 프로비저닝에 이미 검증된 구성을 바로 사용할 수 있습니다.

### 자식 모듈과 루트 모듈의 디렉토리 구조
![Terraform Module 구조](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FbXhXBG%2FbtsIsyURCWC%2FAAAAAAAAAAAAAAAAAAAAAH-mT5yE8vHS5MVWarn4rGzxXIEwNbiEC7jSHPGYkmej%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1759244399%26allow_ip%3D%26allow_referer%3D%26signature%3DmgLMS9XPPL5AjVSHqOknEk613Hg%253D)

모듈화의 목적은 테라폼 코드를 작성하는 작업자마다 다릅니다. 점점 많아지고 복잡해지는 구성 파일을 관리하기 위해 연관성 있는 리소스 집합을 논리적으로 묶어 관리하기 위해서 모듈화를 사용할 수 있습니다.
또한, 여러 프로젝트에서 공통적으로 사용되는 구성을 재사용하기 위해서도 모듈화를 사용할 수 있습니다.

### 모듈의 기본 구조
모듈의 기본 구조는 테라폼 구성으로 입력 변수를 구성하고 결과를 출력하기 위한 구조로 구성합니다.
![Terraform Module 구조](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FbvwaSk%2FbtsItCvhWCS%2FAAAAAAAAAAAAAAAAAAAAAJPF9ZpCXaBWeir0-C2icxci6eJCcAjciYcwH1dA8igm%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1759244399%26allow_ip%3D%26allow_referer%3D%26signature%3D%252B%252BOs%252FoyL1fymE45MCmT5UkKbRVs%253D)

### 루트 모듈과 자식 모듈
![Terraform Module 구조](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2Fbxo4fK%2FbtsIrKamGD8%2FAAAAAAAAAAAAAAAAAAAAAKZYzmk6VKRHCRmQ7Je60Xxo_SxrA9NyDL1Zcd9xVhTB%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1759244399%26allow_ip%3D%26allow_referer%3D%26signature%3DLTaHgwwjLRKUyrBZqK0BWZqtmUs%253D)

기존에 작성한 모듈은 다른 모듈에서 참조하여 사용할 수 있으며, 사용 방식은 리소스와 비슷합니다. 모듈에서 필요한 값은 variable로 선언하여 결정하고, 모듈에서 생성된 값 중 외부 모듈에서 참조하고 싶은 값은 output으로 선언하여 노출합니다.

variable → 모듈/루트에서 외부로부터 값을 주입받는 인터페이스

output → 모듈/루트에서 외부에 값을 반환하는 인터페이스

즉, 모듈 간 데이터 전달 인터페이스 역할을 함.

### Terraform Modul 시작하기
```HCL
module "vpc" {
  source = "./modules/vpc"  # 모듈 소스 경로

    aws_region = "us-west-2"

    vpc_cidr = var.vpc_cidr
    vpc_name = var.vpc_name

    public_subnet_cidrs = var.public_subnet_cidrs
    private_subnet_cidrs = var.private_subnet_cidrs
    availability_zones = var.availability_zones
}
```

이 예시에서, source 속성은 모듈의 위치를 지정합니다. 이는 로컬 경로일 수도 있고, Git 저장소, Terraform Registry 등 다양한 소스를 사용할 수 있습니다. 이 모듈은 VPC와 관련된 모든 리소스를 포함하고 있으며, 필요한 변수들을 인자로 전달받아 동작합니다.

1️⃣ Provider 정의하기
Terraform Module을 구성할 때, 가장 먼저 해야 할 일은 Provider를 정의하는 것입니다. Provider는 Terraform이 특정 클라우드 서비스와 상호작용할 수 있도록 해주는 플러그인입니다.

```HCL


provider "aws" {
    # Provider는 terraform 블록보다 위에 위치하며 Terraform이 사용할 클라우드 서비스를 명시
    region = var.aws_region
}

terraform {
    # terraform 버전을 명시
    required_version = ">= 1.3"

    # 필수로 사용할 provider를 명시
    required_providers {
        aws = {
            source  = "hashicorp/aws"
            version = "~> 5.0"
        }
    }
}
```

2️⃣ 변수 정의하기
Terraform Module은 변수(variable)를 사용하여 모듈의 동작을 유연하게 조정할 수 있습니다. 변수는 모듈 외부에서 값을 전달받아 모듈 내부에서 사용할 수 있게 해줍니다. 이렇게 구현된다면 해당 모듈이
외부에서 원하는 동작을 명확하게 수행할 수 있게 되어 모듈의 재사용성과 유연성이 높아지게 됩니다.

```HCL
variable "aws_region" {
    description = "AWS Region to deploy to"
    type        = string
    default     = "us-west-2"
}

variable "vpc_cidr" {
    description = "CIDR block for the VPC"
    type        = string
    default     = "10.0.0.0/16"
}

variable "vpc_name" {
    description = "Name tag for the VPC"
    type        = string
    default     = "my-vpc"
}

variable "public_subnet_cidrs" {
    description = "List of CIDR blocks for public subnets"
    type        = list(string)
    default     = ["10.0.1.0/24"]
    }

variable "private_subnet_cidrs" {
    description = "List of CIDR blocks for private subnets"
    type        = list(string)
    default     = [ "10.0.2.0/24"]
}

variable "availability_zones" {
    description = "List of availability zones for subnets"
    type        = list(string)
    default     = ["us-west-2a", "us-west-2b"]
    }
```

3️⃣ Resource 정의하기
모듈의 핵심은 실제 인프라 리소스를 정의하는 부분입니다. 이 부분에서는 VPC, 서브넷, 라우팅 테이블 등 필요한 AWS 리소스를 선언합니다.

```HCL
###########################################
### VPC
###########################################
resource "aws_vpc" "main" {
    cidr_block = var.vpc_cidr
    tags = {
        Name = var.vpc_name
    }
}

###########################################
### Subnets
###########################################

locals {
    public_subnet_count  = length(var.public_subnet_cidrs)
    private_subnet_count = length(var.private_subnet_cidrs)
    availability_length = length(var.availability_zones)
}

resource "aws_subnet" "public" {
    count                   = local.public_subnet_count

    vpc_id                  = aws_vpc.main.id
    cidr_block              = var.public_subnet_cidrs[countindex.index]

    availability_zone       = var.availability_zones[count.index % local.availability_length]
    map_public_ip_on_launch = true # Public Ip를 자동 할당

    tags = {
        Name = "${var.vpc_name}-public-${count.index + 1}"
        NetworkType = "public"
    }
}

resource "aws_subnet" "private" {
    count                   = local.private_subnet_count

    vpc_id                  = aws_vpc.main.id
    cidr_block              = var.private_subnet_cidrs[count.index]

    availability_zone       = var.availability_zones[count.index % local.availability_length]
    map_public_ip_on_launch = false # Public Ip를 자동 할당 안함

    tags = {
        Name = "${var.vpc_name}-private-${count.index + 1}"
        NetworkType = "private"
    }
}

###########################################
### Route Table
###########################################

resource "aws_route_table" "public" {
    vpc_id = aws_vpc.main.id

    tags = {
        Name = "${var.vpc_name}-public-rt"
        NetworkType = "public"
    }
}

resource "aws_route" "public" {
    reoute_table_id         = aws_route_table.public.id
    destination_cidr_block = "0.0.0.0/0"
    gateway_id              = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public" {
    count          = local.public_subnet_count
    subnet_id      = aws_subnet.public[count.index].id
    route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
    vpc_id = aws_vpc.main.id

    tags = {
        Name = "${var.vpc_name}-private-rt"
        NetworkType = "private"
    }
}

resource "aws_route_table_association" "private" {
    count          = local.private_subnet_count

    subnet_id      = aws_subnet.private[count.index].id
    route_table_id = aws_route_table.private.id
}
```

모듈 내에서 생성하는 네트워크 관련 리소스들입니다. VPC, 퍼블릭/프라이빗 서브넷, 라우팅 테이블 등을 정의하고 있습니다. Subnet과 Route table에는 NetworkType 태그를 추가하였습니다. 이렇게 태그를 추가하면 해당 태그를 바탕으로 리소스가 어떤 역할을 담당하는지 알 수 있을 뿐더러 Subnet에 대한 정보를 명확하게 알지 못하더라도 Terraform Data에서 태그를 바탕으로 필터링할 수 있어 더욱 편안하게 리소스를 관리할 수 있게 됩니다.

4️⃣ Resource 정보 내보내기
모든 리소스를 정의하였습니다. 해당 모듈에서 생성된 다양한 정보를 외부로 전달해줄 수 있어야 합니다. 우리가 일반적으로 사용하였던 output 변수를 사용하여 모듈에서 생성된 리소스의 속성들을 외부로 내보낼 수 있습니다. 


## 실무에서 쓸만한 팁? 
- 항상 terraform init로 환경 준비
- 팀 환경에선 원격 상태 + 락(S3/DynamoDB 또는 S3 native) 반드시 사용
- PR/CI 단계에서 terraform plan(검토)을 돌리고, Merge 후 CI가 terraform apply(또는 자동 승인 포함)를 수행하는 워크플로우가 안전
- terraform plan -out -> terraform apply tfplan 패턴은 "예측 가능성"을 높여주지만, plan과 apply 사이 state 변경(다른 작업자)이
  없는지 주의


참조(핵심 문서)
Terraform Dependency Graph (how graph is built & walked). 
HashiCorp Developer

terraform plan (옵션: -refresh=false, -out= 등) 문서. 
HashiCorp Developer

Terraform Plugin Protocol (provider RPC sequence used during plan/apply). 
HashiCorp Developer

Backend / State Locking (S3 backend 등). 
HashiCorp Developer

Provisioners (create/destroy timing & behavior). 
HashiCorp Developer

