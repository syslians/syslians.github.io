---
title: "disaster-recovery-workloads-on-aws 요약"
date: "2026-06-20T08:57:00.530Z"
categories:
  - "aws"
  - "disaster-recovery"
  - "sla"
  - "datastructure"
  - "hpa"
  - "cloud"
author: "현제 김_7254"
slug: "disaster-recovery-workloads-on-aws_요약"
---

# AWS 백서 리뷰: Disaster Recovery of Workloads on AWS — Recovery in the Cloud

- 원문 PDF: https://docs.aws.amazon.com/pdfs/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-workloads-on-aws.pdf

- 원문 HTML: https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-workloads-on-aws.html

- 중심 장: https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html

- 작성 목적: AWS 공식 Disaster Recovery 백서의 전체 맥락을 요약하고, 실무 아키텍처/운영 관점에서 리뷰한다.

- 문서 성격: AWS Well-Architected Framework, Reliability Pillar의 DR 관점을 확장한 백서

---

## 1. 한 줄 요약

이 백서는 "DR은 백업 기술이 아니라 비즈니스 연속성 목표를 만족하기 위한 반복 검증 가능한 운영 체계"라는 메시지를 중심으로, RTO/RPO·비용·복잡도·데이터 보호 수준에 따라 Backup and Restore, Pilot Light, Warm Standby, Multi-site Active/Active 전략을 선택하라고 설명한다.

---

## 2. 전체 맥락 요약

AWS 백서의 핵심 흐름은 다음과 같다.

1. 먼저 DR을 고가용성(HA)과 구분한다.

2. AWS와 고객 사이의 resiliency shared responsibility model을 설명한다.

3. “재해”를 자연재해, 기술 장애, 인간 행위로 나누고, 그 지리적 범위를 local, regional, country-wide, continental, global 수준으로 판단하게 한다.

4. DR 계획은 독립 문서가 아니라 Business Continuity Plan(BCP)의 일부여야 한다고 강조한다.

5. Business Impact Analysis와 Risk Assessment를 통해 RTO와 RPO를 정한다.

6. AWS Cloud에서 DR이 기존 온프레미스 DR과 어떻게 다른지 설명한다.

7. 네 가지 DR 전략을 비용과 복잡도, RTO/RPO 수준에 따라 비교한다.

8. 마지막으로 detection과 testing 없이는 DR 전략이 실제로 작동한다고 볼 수 없다고 정리한다.

이 문서의 가장 중요한 관점은 "기술적으로 가능한 가장 강한 DR"이 아니라 "비즈니스 영향, 장애 확률, 비용, 규제 요구사항을 고려해 정당화 가능한 DR"을 선택해야 한다는 점이다.

---

## 3. 핵심 개념 정리

![BitOperations](https://d2908q01vomqb2.cloudfront.net/2a459380709e2fe4ac2dae5733c73225ff6cfee1/2023/01/24/P77670400_IM02.png)

### 3.1 Disaster Recovery와 Availability는 다르다

백서는 DR과 availability를 모두 resiliency 전략의 일부로 보지만, 측정 대상과 설계 초점은 다르다고 설명한다.

- Availability

- 일반적인 장애, 컴포넌트 실패, 네트워크 이슈, 소프트웨어 버그, 부하 급증에 대한 지속적인 가용성

- MTBF, MTTR, successful requests / valid requests 같은 평균값 기반 지표

- Disaster Recovery

- 비즈니스에 심각한 부정적 영향을 주는 일회성/대규모 이벤트에 대한 복구

- RTO와 RPO 중심

- 전체 workload를 다른 위치 또는 다른 Region으로 복구하거나 전환하는 문제

백서에서 특히 중요한 문장은 "High availability is not disaster recovery"이다. Multi-AZ 설계가 HA와 DR 양쪽에 도움이 될 수는 있지만, 데이터 삭제·오염·계정 침해·Region 단위 장애처럼 workload 전체를 복구해야 하는 상황에서는 별도의 DR 전략이 필요하다.

<img width="934" height="636" alt="스크린샷 2026-06-21 오후 7 27 24" src="https://github.com/user-attachments/assets/b0f23315-cb52-4943-9c26-2c2efde22c6d" />
재해 복구는 가용성과 비교할 수 있으며, 이는 또 다른 중요한 구성 요소입니다. 재해 복구는 일회성 이벤트와 가용성에 대한 목표를 측정하는 반면 목표는 일정 기간 동안의 평균값을 측정합니다. 

가용성은 아래와 같은 식으로 구해냅니다.이 접근 방식은 종종 "nines"이라고 불린다. 99.9% 가용성은 3개의 availabilty-zone을 전제로 하며, s3, dynamodb 와 같은서비스는 aws에서 디폴트로 3개의 az로 복제한다.소규모 워크로드의 경우 성공한 요청과 실패한 요청을 세는 것이 더 쉬울 수 있다. 이 경우 다음 계산을 사용할 수 있다. 
<img width="934" height="171" alt="스크린샷 2026-06-21 오후 8 01 20" src="https://github.com/user-attachments/assets/12e8b09a-ef09-4805-93be-e4bcdb01e1ab" />



## 4. AWS Shared Responsibility Model 관점
<img width="934" height="418" alt="스크린샷 2026-06-21 오후 8 06 24" src="https://github.com/user-attachments/assets/b001e895-dae2-4993-8a02-5b1372b8bd1b" />

AWS는 "Resiliency of the Cloud"를 책임지고, 고객은 "Resiliency in the Cloud"를 책임진다.

AWS 책임:

- AWS Global Infrastructure

- Region과 Availability Zone의 물리적 격리

- AWS Cloud 서비스의 하드웨어, 소프트웨어, 네트워크, 시설

- AZ 간 고대역폭/저지연/암호화된 네트워크

고객 책임:

- workload를 여러 AZ 또는 Region에 어떻게 배치할지

- EC2 기반 workload의 Auto Scaling, self-healing, application-level resiliency

- S3, DynamoDB 같은 managed service에서도 backup, versioning, replication 전략

- IaC, 배포 자동화, 데이터 보호, 계정/Region 분리 전략

리뷰 관점에서 이 부분은 매우 중요하다. AWS managed service를 쓴다고 DR 책임이 사라지는 것이 아니라, DR 설계의 추상화 수준이 올라갈 뿐이다. 예를 들어 S3는 기본적으로 multi-az로 구성되기때문에 매우 내구성이 높지만, 잘못된 삭제나 악의적 변경으로부터 보호하려면 versioning, replication, object lock, point-in-time 성격의 백업 전략을 별도로 고려해야 한다.

---

## 5. “재해”의 범위 정의

백서는 DR 계획을 만들 때 재해를 다음 세 범주로 평가하라고 한다.

1. 자연재해

- 지진, 홍수, 허리케인, 토네이도 등

1. 기술 실패

- 전력 장애, 네트워크 연결 실패, 인프라/서비스 장애 등

1. 인간 행위

- 오설정, 무단 접근, 악의적 수정/삭제, 내부자 위협 등

또한 지리적 범위도 고려해야 한다.

- Local

- Regional

- Country-wide

- Continental

- Global

실무적으로 이 구분은 DR 투자 수준을 결정한다. 예를 들어 한 AZ에 영향을 주는 로컬 장애는 Multi-AZ로 완화할 수 있지만, 생산 데이터가 공격으로 오염된 상황은 단순 replication만으로 해결되지 않는다. 이 경우 다른 Region 또는 다른 계정에 보호된 point-in-time backup이 필요하다.

---

## 6. Business Continuity Plan과 DR

<img width="934" height="437" alt="스크린샷 2026-06-21 오후 8 21 08" src="https://github.com/user-attachments/assets/114dd6fe-665d-4a33-ba69-3f5ffd76f361" />


백서는 DR 계획을 BCP의 하위 요소로 본다. 이 관점은 매우 타당하다. 애플리케이션만 복구되어도 물류, 결제, 고객지원, 규제 보고, 운영 인력이 동시에 복구되지 않으면 비즈니스는 계속되지 않는다.

따라서 DR 계획은 다음 질문과 연결되어야 한다.

- 이 workload가 중단되면 고객과 내부 조직에 어떤 영향이 있는가?

- 영향은 시간대나 기간에 따라 달라지는가?

- 손실 가능한 데이터 양은 얼마인가?

- 복구 시간, 허용 데이터 손실은 어느 정도까지 허용 가능한가? (RTO, RPO)

- 해당 장애 시나리오의 발생 가능성은 어느 정도인가?

- 복구 전략 비용은 장애 비용보다 정당화되는가?

- 규제나 계약상 요구사항이 있는가?

이 문서는 DR을 엔지니어링 관점에만 가두지 않고, 비즈니스 영향 분석과 비용 판단에 연결한다는 점에서 실무성이 높다.

---

### 3.2 RTO와 RPO
<img width="934" height="437" alt="스크린샷 2026-06-21 오후 8 31 31" src="https://github.com/user-attachments/assets/64fe0eb9-3b9d-4476-918d-26247705251c" />
RTO(Recovery Time Objective) 는 장애 발생 후 서비스가 복구되어야 하는 최대 허용 시간이다.
이 목표는 허용 가능한 시간대를 결정한다.
이 백서에서는 백업 및 복원, 파일럿 라이트, 웜 스탠바이등 크게 네 가지 DR 전략에 대해 논의한다.
위 다이어그램에 따르면, 비즈니스는 최대 허용 RTO와 한도를 결정한다.서비스 복구 전략에 지출할 수 있는 금액, 비즈니스의 목표를 고려할 때, DR
파일럿 라이트 또는 웜 스탠바이 전략은 RTO와 비용 기준을 모두 충족한다.

RPO(Recovery Point Objective)는 장애 발생시 잃어도 되는 데이터의 최대 범위를 의미한다. 

위 다이어그램에서 비즈니스는 최대 허용 RPO와 데이터 복구 전략에 지출할 수 있는 금액의 한계를 고려했을때 네 가지 DR 전략 중 파일럿 라이트,
또는 웜 스탠바이 DR 전략은 RPO와 비용에 대한 두 가지 기준을 모두 충족한다.

### 3.3 비용과 리스크의 균형

/assets/image_3d086b76-5dc8-4711-8c0a-a88a446bdb4a.png

백서의 현실적인 조언은 다음 문장으로 요약된다.

> 복구 전략의 비용이 장애나 손실 비용보다 크다면, 규제 같은 2차 요구사항이 없는 한 해당 복구 옵션은 적용하지 않는 것이 합리적이다.

즉, 모든 workload에 Multi-Region Active/Active를 적용하는 것은 성숙한 DR이 아니라 과잉 설계일 수 있다.

---

## 7. AWS Cloud에서 DR이 다른 이유

백서는 온프레미스 DR과 AWS Cloud DR의 차이를 다음과 같이 설명한다.

- 물리적 백업 센터를 고정비로 유지할 필요가 줄어든다.

- 필요한 시점에 필요한 규모로 리소스를 프로비저닝할 수 있다.

- IaC와 자동화로 복구 절차를 반복 가능하게 만들 수 있다.

- Multi-AZ, Multi-Region 설계를 조합할 수 있다.

- DR 테스트를 더 자주, 더 낮은 비용으로 수행할 수 있다.

하지만 이 장점은 자동으로 주어지는 것이 아니다. IaC, 배포 자동화, Region별 quota 확인, 계정 분리, 데이터 복제/백업 검증, health check, failover runbook이 갖춰져야 한다.

---

## 8. Disaster recovery options in the cloud
<img width="934" height="400" alt="스크린샷 2026-06-21 오후 8 43 00" src="https://github.com/user-attachments/assets/b516b6db-d412-43f0-8069-d3968bd25704" />

백서의 중심 장은 네 가지 DR 전략이다.

### 8.1 Backup and Restore

<img width="934" height="449" alt="스크린샷 2026-06-21 오후 8 43 27" src="https://github.com/user-attachments/assets/e64dc72d-3ddc-4ead-98e5-711e27eefd0c" />


가장 낮은 비용과 복잡도를 가진 전략이다. 데이터 손실이나 데이터 오염에 대한 대응, 단일 AZ workload의 복구, Region 간 백업 복제에 적합하다.

그러나 IaC와 자동화 파이프라인이 잘 되어 있으면 Backup and Restore도 꽤 강력해질 수 있다.



핵심 요구사항:

- 데이터뿐 아니라 infrastructure, configuration, application code도 복구 가능해야 한다.

- AWS CloudFormation 또는 AWS CDK 같은 IaC가 필요하다.

- AMI, EC2 metadata, CodePipeline 구성, 네트워크/보안 구성도 복구 대상에 포함되어야 한다.

- 백업 주기는 RPO를 결정한다.

- 복구 절차는 수동 문서가 아니라 자동화 가능한 형태여야 한다.

사용 가능한 AWS 서비스 예:

- EBS snapshots

- DynamoDB backup / PITR

- RDS snapshots

- Aurora snapshots

- EFS backup with AWS Backup

- Redshift, Neptune, DocumentDB, FSx backups

- S3 Cross-Region Replication, S3 Versioning

- AWS Backup cross-Region/cross-account copy

리뷰:

Backup and Restore는 "가장 단순한 DR"이지만 "가장 쉬운 DR"은 아니다. 실제 복구 시간은 백업 파일 존재 여부보다 restore 자동화, IaC 품질, quota 준비, dependency 복구 순서에 의해 좌우된다. 특히 백서가 지적하듯 AWS Backup restore는 자동 스케줄 복구가 기본 기능으로 제공되는 것이 아니므로, Lambda/SNS/SDK 기반 자동 복구 패턴을 별도로 설계해야 한다.

### 8.2 Pilot Light

<img width="934" height="480" alt="스크린샷 2026-06-21 오후 8 44 29" src="https://github.com/user-attachments/assets/83a8ce56-45b0-4dfb-8a1f-62706d439e8d" />


Pilot Light는 DR Region에 핵심 데이터와 핵심 인프라를 최소 규모로 유지하고, 재해 시 나머지 애플리케이션 서버나 전체 용량을 켜는 전략이다.

특징:

- 데이터베이스와 object storage replication은 항상 유지한다.

- 애플리케이션 서버 등 일부 리소스는 평상시 꺼두거나 미배포 상태로 둔다.

- 재해 시 full-scale production 환경으로 확장한다.

- Backup and Restore보다 RTO가 낮다.

- Warm Standby보다 비용이 낮다.

주요 서비스:

- S3 Replication

- RDS read replicas

- Aurora Global Database

- DynamoDB global tables

- DocumentDB global clusters

- ElastiCache Global Datastore

- CloudFormation/CDK

- Image Builder, AMI copy

- Route 53, ARC, Global Accelerator

- AWS Elastic Disaster Recovery

리뷰:

Pilot Light의 장점은 비용과 복구 속도의 균형이다. 다만 "꺼져 있는 리소스"는 실제 장애 시 켜져야 하므로, deployment pipeline과 scale-out 절차가 자주 검증되지 않으면 RTO가 쉽게 무너진다. 또한 continuous replication은 데이터 삭제나 corruption까지 자동으로 해결하지 못하므로 versioning과 point-in-time backup이 반드시 병행되어야 한다.

### 8.3 Warm Standby

<img width="934" height="480" alt="스크린샷 2026-06-21 오후 8 45 19" src="https://github.com/user-attachments/assets/f8198ad3-e20e-4d0e-a39c-fbc3ae5eee43" />


Warm Standby는 DR Region에 축소된 형태지만 완전히 동작 가능한 production copy를 유지하는 전략이다.

특징:

- DR Region이 항상 켜져 있다.

- 평상시 reduced capacity로 운영된다.

- 장애 시 scale up만 수행하면 된다.

- Pilot Light보다 RTO가 낮다.

- Multi-site Active/Active보다 비용과 복잡도는 낮다.

백서는 Pilot Light와 Warm Standby의 차이를 명확히 설명한다.

- Pilot Light: 요청을 처리하기 전에 서버를 켜거나, 추가 인프라를 배포하거나, scale up해야 한다.

- Warm Standby: 이미 요청을 처리할 수 있지만, production traffic 전체를 감당하려면 scale up이 필요하다.

리뷰:

Warm Standby는 많은 엔터프라이즈 workload에 현실적인 절충안이다. 특히 RTO가 짧지만 Active/Active의 데이터 일관성 복잡도를 감당하기 어려운 조직에 적합하다. 다만 scale up 과정이 Auto Scaling 같은 control plane 동작에 의존할 경우, 장애 시 control plane 가용성에 대한 의존이 생긴다. 백서가 말하는 "full capacity를 미리 provision하는 hot standby"는 이 trade-off를 줄이지만 비용이 증가한다.

### 8.4 Multi-site Active/Active

<img width="934" height="480" alt="스크린샷 2026-06-21 오후 8 45 38" src="https://github.com/user-attachments/assets/f6478c56-e6bb-4cea-adfe-bae5903a3346" />


가장 높은 비용과 복잡도를 가지지만, 올바르게 구현하면 대부분의 Region 장애에서 near-zero RTO를 목표로 할 수 있는 전략이다.

특징:

- 여러 Region이 동시에 production traffic을 처리한다.

- 일반적인 의미의 failover보다 traffic steering과 regional isolation이 핵심이다.

- 데이터 corruption, 삭제, obfuscation 같은 인간/보안 재해에는 여전히 backup과 point-in-time recovery가 필요하다.

- 데이터 일관성 모델 설계가 어렵다.

쓰기 전략:

- Write global: 모든 write를 한 Region으로 라우팅하고 장애 시 다른 Region을 승격

- Write local: 사용자와 가까운 Region에서 write 수행, 예: DynamoDB global tables

- Write partitioned: partition key 기준으로 write Region을 분리해 conflict를 줄임

리뷰:

Active/Active는 DR 전략인 동시에 분산 시스템 설계 문제다. 네트워크 라우팅, 데이터 일관성, conflict resolution, idempotency, regional dependency 제거, observability, security blast radius, 비용 관리가 모두 중요하다. 백서가 "대부분 고객은 두 번째 Region에 full environment를 둘 것이라면 Active/Active 사용을 고려한다"고 말하지만, 실제로는 조직의 운영 성숙도와 데이터 모델이 따라오지 않으면 Active/Active는 오히려 장애 표면을 넓힐 수 있다.

---

## 9. Data plane vs Control plane 관점

이 백서에서 특히 실무적으로 중요한 부분은 failover에 control plane 의존성을 줄이라는 조언이다.

- Data plane: 실시간 서비스 제공 경로

- Control plane: 환경 구성, 설정 변경, 리소스 생성/수정 경로

백서는 최대 resiliency를 위해 failover operation은 가능한 data plane operation만 사용하라고 말한다. 예를 들어 Route 53 ARC routing control을 사용하면 고가용 data plane API를 통해 failover switch를 조작할 수 있다. 반면 DNS weight 변경이나 Auto Scaling desired capacity 변경은 control plane 성격이 강하므로 장애 상황에서 의존하면 전체 복구 전략의 신뢰도가 낮아질 수 있다.

리뷰:

이 관점은 DR 설계 리뷰에서 체크리스트로 반드시 들어가야 한다. "재해가 발생하면 콘솔에서 설정을 바꾸면 된다"는 계획은 DR 계획으로 부족하다. 장애 시 사용해야 하는 API, IAM 권한, runbook, CLI profile, 계정 접근 경로, break-glass 절차가 모두 사전에 검증되어야 한다.

---

## 10. Detection과 Testing



백서는 DR의 마지막 단계로 detection과 testing을 강조한다.

Detection:

- workload가 비즈니스 결과를 내지 못하는 시점을 빨리 알아야 한다.

- RTO가 1시간이면 감지, 통지, escalation, 분석, 재해 선언, 복구가 모두 1시간 안에 들어와야 한다.

- AWS Service Health Dashboard, AWS Health Dashboard, deep health check, KPI 기반 health check를 활용할 수 있다.

- 자동 failover는 false positive 위험이 있으므로 신중해야 한다.

Testing:

- DR 구현은 정기적으로 테스트해야 한다.

- 거의 실행하지 않는 recovery path는 실제 장애 시 작동하지 않을 가능성이 높다.

- 작은 수의 recovery path를 반복적으로 검증하는 것이 좋다.

- 중요한 recovery path는 production에서 장애 시나리오를 실행해 검증해야 한다.

- DR Region의 configuration drift, AMI, service quota, data 상태를 지속적으로 점검해야 한다.

- AWS Config, Systems Manager Automation, CloudFormation drift detection을 활용할 수 있다.

리뷰:

백서의 가장 강한 문장은 "the only error recovery that works is the path you test frequently"이다. DR 문서는 많지만 실제 failover 훈련이 없는 조직에서는 대부분 RTO/RPO가 문서상 숫자에 머문다. 이 백서는 복구 전략 선택보다 테스트의 반복성과 drift 관리를 더 중요하게 다룬다는 점에서 현실적이다.

---

---

## 12. 실무 적용 체크리스트

### 전략 선택

### 데이터 보호

### 인프라 복구

### 운영과 테스트

---

## 13. 장점 리뷰

1. 비즈니스 중심이다.

- 단순히 AWS 서비스를 나열하지 않고, BIA, risk assessment, RTO/RPO, 비용을 먼저 다룬다.

2. HA와 DR을 명확히 구분한다.

- Multi-AZ와 Multi-Region을 혼동하기 쉬운데, 문서는 availability와 disaster recovery의 측정 방식 차이를 분명히 한다.

3. 데이터 replication의 한계를 잘 지적한다.

- continuous replication은 빠르지만, corruption이나 malicious deletion도 복제할 수 있다. point-in-time backup이 필요하다는 설명이 매우 중요하다.

4. data plane/control plane 구분이 실무적이다.

- 장애 시 control plane에 의존하는 failover는 위험하다는 조언은 실제 DR 설계 리뷰에서 자주 놓치는 부분이다.

5. 테스트의 중요성을 강하게 강조한다.

- 문서화된 DR이 아니라 반복 실행되는 recovery path만 신뢰할 수 있다는 메시지가 명확하다.

---

## 14. 한계와 보완할 점

1. 서비스별 최신 기능 반영은 별도 확인이 필요하다.

- AWS 서비스는 빠르게 변하므로, 백서의 개념은 유효하더라도 각 서비스의 현재 기능, quota, Region 지원 여부, pricing은 최신 문서로 재검증해야 한다.

2. Active/Active의 데이터 일관성 문제는 더 깊은 설계가 필요하다.

- 백서는 write global/local/partitioned 전략을 소개하지만, 실제 구현에서는 conflict resolution, idempotency, ordering, saga, event sourcing, compliance logging까지 검토해야 한다.

3. 보안 재해에 대한 runbook은 더 구체화할 필요가 있다.

- 계정 침해, credential compromise, ransomware-like deletion, insider threat 상황에서는 backup뿐 아니라 IAM isolation, SCP, break-glass account, forensic 절차가 필요하다.

4. 비용 모델링은 예시 수준이다.

- 각 전략별 standby capacity, replication cost, data transfer, backup retention, drill cost를 산정하는 구체적인 템플릿이 있으면 더 실무적일 것이다.

5. 조직 프로세스 관점은 별도 문서가 필요하다.

- 누가 disaster를 선언하는지, business owner와 incident commander가 어떻게 협업하는지, 커뮤니케이션 채널은 무엇인지 등은 BCP/incident management 문서와 연결해야 한다.

---

## 15. 내 결론

이 AWS 백서는 DR을 "기술 아키텍처 선택"이 아니라 "비즈니스 목표, 데이터 보호, 운영 자동화, 반복 테스트를 연결하는 resiliency discipline"으로 다룬다는 점에서 가치가 크다. 특히 HA와 DR의 구분, RTO/RPO 기반 전략 선택, continuous replication의 한계, data plane 중심 failover, 정기 테스트의 필요성은 AWS 환경뿐 아니라 모든 클라우드 DR 설계에 적용할 수 있다.

실무에서 이 문서를 사용할 때는 다음 순서가 적절하다.

1. workload별 BIA와 risk assessment를 먼저 수행한다.

2. RTO/RPO를 정한다.

3. 네 가지 DR 전략 중 하나를 선택한다.

4. IaC, backup, replication, routing, 계정/Region 분리를 설계한다.

5. control plane 의존성을 줄인다.

6. 정기 DR drill과 drift detection을 운영 체계에 넣는다.

결국 좋은 DR 전략은 "가장 비싼 Multi-Region 구조"가 아니라 "비즈니스가 요구한 RTO/RPO를 실제 테스트로 반복 증명할 수 있는 구조"다.

---

## 16. 참고 링크

- AWS PDF: https://docs.aws.amazon.com/pdfs/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-workloads-on-aws.pdf

- AWS HTML: https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-workloads-on-aws.html

- Disaster recovery options in the cloud: https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html

- AWS Well-Architected Framework: https://aws.amazon.com/architecture/well-architected/

- AWS Well-Architected Tool: https://aws.amazon.com/well-architected-tool/
