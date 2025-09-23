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

---------------------------------------------------------------------------------------------------------------------------

### Terraform 모듈 구조

<img width="850" height="425" alt="image" src="https://github.com/user-attachments/assets/eb64d3d3-a4fa-42af-9ecd-da23153c07e4" />
[Terraform 모듈 구조]

Terraform에서는 한 디렉토리를 모듈이라고 한다. 



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

