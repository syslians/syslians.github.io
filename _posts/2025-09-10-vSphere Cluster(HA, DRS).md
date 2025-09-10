---
layout: post
title: "vSphere HA, DRS"
categories: [네트워크, 가상화, VMware, ESXi, HyperVisor, VMware Cluster, HA, DRS]
author: cotes
published: true
---

## vSphere Cluster의 HA, DRS 이해하기
기업 데이터센터 운영에서 서비스 가용성과 자원의 효율적인 분배는 필수입니다. VMware vSphere
Cluster는 이를 위해 **HA(High Availability)** 와 DRS(Distributed Resource Scheduler)** 라는 
핵심 기능을 제공합니다. 이번 포스팅에서는 두 기능의 개념, 동작 원리, 실무적 고려사항을 시나리오를
통해 정리해보겠습니다.

### vSphere HA (High Availability) 서비스 연속성 확보 및 다운타임 최소화

vSphere HA(High Availiability)는 단순히 VM을 자동으로 다시 켜주는 기능이 아니라, 여러 계층(Host, Guest Os, Application)
을 모니터링하고, 다양한 장애 시나리오에 따라 적절하게 대응하는 분산 관리 시스템 입니다.이번 포스팅에서는 
HA의 아키텍쳐, Master-Slave 메커니즘, 장애 유형별 대응 방식, 그리고 전용 네트워크인 Management Network의
링크가 단절되었을때 Lock 파일을 통한 VM 상태 확인 메커니즘까지 설명합니다.

### vSphere Cluster와 HA 아키텍쳐
vSphere Cluster는 여러 ESXi Host를 하나의 논리적 풀로 묶어 관리합니다. HA 기능은 이 Cluster 위에서 동작하며
, 클러스터 내 자원을 모니터링하고 장애시 서비스 연속성을 보장합니다.

- HA Agent: 각 ESXi Host에 설치되어 Heartbeat 및 상태 정보 수집
- Fault Domain: 장애 전파를 줄이기 위해 네트워크/스토리지 분리 가능
- vCenter: 초기 구성 및 정책 관리 (실시간 HA 동작 자체는 vCenter 없이도 수행됨)
- 클러스터 내 모든 호스트가 Heartbeat을 통해 서로 상태를 모니터링
- 장애(host failure) 감지 시, 해당 호스트에 있던 VM들을 다른 정상 호스트에서 자동으로 재시작
- 네트워크, 스토리지 연결 상태도 모니터링하여 split-brain 방지

### HA Master-Slave 메커니즘
vSphere HA는 클러스터 내에서 한 노드를 Master, 나머지를 Slave로 선출합니다.

- Master
  - 클러스터의 전체 VM 상태관리
  - 장애 호스트 감지 및 VM 재시작 결정
  - Datastore 접근하여 Lock 파일 검사
- Slave
  - 자신의 Host와 VM 상태 보고
  - Master의 지시에 따라 VM 재기동/이동

Master 선출은 네트워크 파티션 상황에서도 독립적으로 진행되며, vCenter가 일시 중단되더라도 기존 Master
가 HA 이벤트를 처리할 수 있습니다.

### 3. 실무 포인트
- 공유 스토리지 필요 (vSAN, NFS, ISCSI 등)
- 전용 네트워크 필요 (product network)
- Admission Control 정책을 통해 클러스터에 항상 여유 자원을 확보해야 안정적 HA

<img width="728" height="455" alt="HA2" src="https://github.com/user-attachments/assets/a1cb4594-f452-45b6-b603-9236c95d3013" />
가능

### 장애 유형별 대응
| 장애 유형          | 예시                      | 대응 방식                                                                                 |
| -------------- | ----------------------- | ------------------------------------------------------------------------------------- |
| Application 장애 | 애플리케이션 프로세스 Crash | VMware App Monitoring (VMware Tools + App HA) → Guest OS 내 App 재시작 또는 알림              |
| Guest OS 장애    | OS kernel panic, BSOD   | VM Monitoring (VMware Tools heartbeat 소실) → VM 재부팅                                    |
| Host 장애        | ESXi Host 전원 Off, Panic | HA Host Monitoring (Management + Datastore heartbeat 확인) → 해당 Host의 VM을 다른 Host에서 재기동 |

### 관리 네트워크 단절(Management Network Partition) 시동작
HA는 Host간 상태를 주로 Management Network Heartbeat로 감지합니다. 하지만 네트워크 단절 시 Host가 정말 죽은것인지, 단순 네트워크
장애인지 구분해야 합니다. 이를 위해 VMware는 Datastore Heartbeat을 사용합니다.

1. 관리 네트워크 단절 발생
2. HA Master가 Slave들의 Heartbeat 신호를 받지 못함
3. Master가 Datastore에 있는 Lock 파일 접근 시도
   - VM 파일(.vmx, .vmdk)에는 해당 VM을 소유한 Host만 접근 가능한 락이 걸림
   - 다른 Host에서 접근 시 락 상태를 통해 Host 생존 여부 판별
4. Lock이 여전히 활성 -> Host는 살아있지만 네트워크 문제
5. Lock 해제 또는 접근 불가 -> Host 장애로 판단, VM을 다른 Host에서 재기동
  
### 요약 - 계층별 HA 동작
| 계층          | 감지                                              | 조치                   |
| ----------- | ----------------------------------------------- | -------------------- |
| Application | App heartbeat 소실                                | App 재시작 / 관리자 알림     |
| Guest OS    | VMware Tools heartbeat 소실                       | VM 재부팅               |
| Host        | Management + Datastore heartbeat 소실             | 다른 Host에서 VM 재기동     |
| 네트워크 단절| Management heartbeat 소실, Datastore heartbeat 확인 | 락 파일 검사 후 Host 상태 판별 |

### vMotion Migration
vMotion의 Migration은 파일 복사 방식이 아니라 실행 상태(state)의 재현 방식입니다.
1. 실행 중인 VM의 메모리, CPU 상태, 네트워크 연결 정보를 다른 호스트로 실시간 복제
2. 복제 과정 중 변경된 메모리 페이지를 다시 동기화 (Pre-copy migration)
3. 모든 상태가 거의 동기화되면 짧은 순간(수 ms) VM을 잠깐 멈추고 최종 차이분을 복사 -> 새 호스트에서 VM을 제개
4. 원래 호스트의 VM은 제거, 네트워크의 MAC은 동일하게 유지, 외부에서는 끊김 거의 없음
   
| 항목    | snapshot                       | vMotion                   |
| ----- | ------------------------------ | ------------------------- |
| 목적    | 특정 시점 보관, 롤백                   | 호스트 간 라이브 마이그레이션          |
| 데이터   | 디스크 delta(필수), 메모리/CPU 상태(옵션)  | 메모리 + CPU 상태 + 디바이스 연결 정보 |
| 방식    | VM의 실행 중/중단된 상태를 “저장”          | 실행 중인 VM의 상태를 “이동”        |
| 저장 위치 | datastore (vSAN, NFS, iSCSI 등) | 네트워크로 전송, 새 ESXi 호스트에 재현  |



### 1. VM 설정 정보 (Metadata)
- VM의 하드웨어 스펙, 네트워크 정보, 디스크 경로 등
- vCenter가 대상 호스트에 같은 VM 구성을 먼저 만듦 (OS 설치 X, VM 껍데기만)

### 2. 메모리 페이지 복제 (Memory pre-Copy)
- 실행중인 VM의 메모리 전체를 네트워크를 통해 새 호스트로 복사
- 이 과정에서도 VM은 계속 돌아가고 있으므로 계속 바뀜
- 변경된 페이지(Dirty Page)를 추적해서 다시 복사 -> 동기화 될 때까지 반복

### 3. CPU/장치 상태 동기화 (CPU & Device State Transfer)
- CPU 레지스터, 가상 장치의 내부 상태(가상 NIC, 가상 디스크 컨트롤러 등) 복제
- 이 단계에서 거의 동일한 "실행 상태"가 새 호스트에 준비됨

### 4. 네트워크 스위치
- 아주 짧은 순간 VM을 잠깐 멈추고 (수 ms)
- 마지막 변경된 메모리와 CPU 레지스터를 옮김
- 네트워크(포트 그룹, MAC 주소)도 동일하게 새 호스트에 바인딩
- 그 후 새 호스트에서 VM을 resume -> 클라이언트 입장에서는 거의 끊김 없이 연결 유지

### 5. 원본 호스트 정리
- 원본 호스트에 있던 VM 프로세스 종료
- 필요하면 스토리지나 경로나 기타 리소스 해제

형태적으로 보면 file move가 아니라, VM의 동작 state를 실시간 복제하고 마지막 순간 Context Switching 하는것



### vSphere DRS (Distributed Resource Scheduler) 자원 최적화
DRS는 클러스터 내 여러 호스트의 CPU, 메모리 사용량을 실시간 모니터링하고, 부하가 몰린 호스트의 VM을 부하가
적은 호스트로 자동 vMotion하여 리소스를 균형있게 배분합니다.

### 동작 원리
- vCenter가 클러스터의 실시간 리소스 사용량 분석
- 사전 정의된 automation level에 따라
  - Manual: 관리자에게 권고만
  - Partially Automated: 초기 배치 자동, 이후 권고
  - Fully Automated: 자동으로 vMotion 수행
- SLA(우선순위 정책)에 따라 특정 VM의 자원을 우선 보장

### 3. 실무 포인트
- vMotion이 필수 전제 조건 (네트워크/스토리지 vMotion 환경 준비 필요)
- CPU 호환성(EVC) 설정 필수
- 자동화 정책은 서비스 특성에 따라 조정 필요 (DB 서버는 자동 이동 제한)

### HA와 DRS 관계 정리

 ┌─────────────────────────────┐
 │         vCenter Server       │
 │  - HA 관리                    │
 │  - DRS 스케줄링               │
 └─────────────────────────────┘
   │
   ▼
 ┌─────────┬─────────┬─────────┐
 │ Host A  │ Host B  │ Host C  │  ← vSphere Cluster
 │  VM1    │  VM3    │  VM5    │
 │  VM2    │  VM4    │  VM6    │
 └─────────┴─────────┴─────────┘
 
 장애 발생 시 (Host A down)
 → VM1, VM2 자동으로 Host B, C에서 부팅 (HA)
 부하 증가 시 (Host B 과부하)
 → VM3, VM4를 Host C로 자동 vMotion (DRS)

<img width="1317" height="521" alt="HA" src="https://github.com/user-attachments/assets/3e1fe653-8de3-4170-88fa-6fd88b7a4164" />
[그림 1 vSphere HA]


<img width="885" height="372" alt="migrating vms for optimal placement" src="https://github.com/user-attachments/assets/4fd7c6e0-4e03-40c7-b75a-a207251c46df" />

<img width="1020" height="351" alt="thresold" src="https://github.com/user-attachments/assets/37467495-4da4-42d5-9f78-9c1aae9897a8" />

<img width="1112" height="334" alt="DRS and vSphere HA" src="https://github.com/user-attachments/assets/458b9aee-0351-42a4-8a7b-8f515f1dae5b" />

<img width="1115" height="336" alt="Fault Tolerent" src="https://github.com/user-attachments/assets/31a4f915-1784-452b-9d22-8da4a74c1293" />

<img width="967" height="332" alt="sevm" src="https://github.com/user-attachments/assets/9be91975-b86c-4014-b781-fd6db8b5b0f6" />

