---
layout: post
title: "쿠버네티스 스케쥴러(kube-scheduler)"
date: 2025-07-27 22:00:00 +0900
categories: [k8s]
author: cotes
published: true
---

## Kuberbenetes 스케쥴러 (kube-scheduler) 동작 원리
kube-scheduler는 Pod를 어떤 Node에 배치할지 결정하는 핵심 컴포넌트입니다. 컨테이너를 실행시키는 것은 Node의 kubelet이 담당하지만, 어느 Node에서 실행할지
결정하는 것은 스케쥴러가 담당합니다. 스케쥴러는 컨트롤 플레인의 컴포넌트 중 하나이며, 아직 Node가 할당되지 않은 Pod를 찾아서 적절한 Node를 결정합니다. 단순히
할당만하고 끝이 아니라, 리소스 요구사항.affinity,antiaffinity,taint,toleration,priority,data locality 등 여러 제약 조건을 고려합니다. 

한 마디로 정리하면 스케쥴러는 어떤 Node에 Pod를 배치할지 결정하는 control-plane의 component

이 글에서는 다음을 목표로 합니다. 
1. kube-scheduler가 어떻게 생각하며 결정하는지
2. 내부 파이프라인이 왜 그렇게 설계되었는지
3. 실무에서 반드시 마주치는 시나리오 / 유즈케이스 / 엣지케이스

![BitOperations](https://blog.techiescamp.com/content/images/2024/09/scheduler-worlkflow-1.gif)
[그림1. 쿠버네티스 스케쥴링]

![BitOperations](https://kubernetes.io/images/docs/scheduling-framework-extensions.png)
[그림2. 쿠버네티스 스케쥴링]

![BitOperations](https://media.licdn.com/dms/image/v2/D5612AQGao4mMQKXCMg/article-cover_image-shrink_720_1280/article-cover_image-shrink_720_1280/0/1700092478326?e=2147483647&t=0WeAP8qKNgHAk40TIZtPgbDj-3hbLu5LaHu_IEHmcBI&v=beta)
[그림3. 쿠버네티스 스케쥴링]



https://claude.ai/public/artifacts/091feec9-9504-46a8-8ede-47b74a6163f1
[쿠버네티스 Kube-schedule algorithm simulator]

## 1. 스케쥴러의 역할을 정의해보자
쿠버네티스에서 "Pod가 실행된다"는 말은 두 단계로 나뉩니다.
1. 어디서 실행할지 결정 -> Scheduler
2. 실제로 실행 -> kubelet

```
Pod 생성
  ↓
[ Scheduler ]  ← 결정만 함
  ↓
Node 지정
  ↓
[ kubelet ]    ← 실행

```

스케쥴러는 컨테이너를 실행하지 않습니다. 오직 Pod.spec.nodeName을 채워주는 역할만 수행합니다.

## 2. 스케쥴러의 본질

https://jvns.ca/blog/2017/07/27/how-does-the-kubernetes-scheduler-work/ 글에서 저자인 julia Evans는 스케쥴러를 아주 단순화한 프로세스로 구분합니다.

1. 아직 노드가 없는(unscheduled)된 Pod를 찾는다
2. 적절한 노드를 하나 고른다
3. Pod에 노드를 할당한다

이 프로세스는 핵심 개념적으로 스케쥴러의 역할을 명료하게 나타냅니다. 
그렇다면
1. 적절한 노드란 무엇인가?
2. 동시에 수천개의 Pod 생성 요청이 들어온다면?
3. 조건을 만족하는 노드가 하나도 없다면?


## 3. 실제 kube-scheduler의 내부 구조

### 3.1 Informer + Cache 기반 설계
스케쥴러는 매번 API Server에 질의하지 않습니다. 
- Node State
- Pod State
- PVC, PV
- Taints, Labels

대규모 클러스터에서 API Server 직접 조회는 병목 + 레이턴시 유발의 이유로 모든 정보는 로컬 캐시에 유지됩니다. 


### 3.2 Scheduling Queue (대기열)
모든 Pod가 동일한 우선순위를 갖습니다.

큐는 크게 세 가지 상태를 가집니다.
| 큐              | 의미            |
| -------------- | ------------- |
| activeQ        | 지금 당장 스케줄링 가능 |
| backoffQ       | 실패 후 대기       |
| unschedulableQ | 현재 조건상 불가능    |

Pod는 Node 상태 변화, 리소스 회수, Pod 종료 등의 이벤트로 unscheduled -> active로 다시 이동할 수 있습니다.

## 4. Scheduling Framework: 파이프라인 사고

현재 kube-scheduler는 Scheduler Framework라는 플러그인 기반 파이프라인을 사용합니다.

```
QueueSort
   ↓
PreFilter
   ↓
Filter
   ↓
PostFilter (optional)
   ↓
Score
   ↓
Reserve
   ↓
Permit (optional)
   ↓
Bind

```

## 5. 단계별로 뜯어보는 스케쥴링 과정

### 5.1 Filter 단계 - 불가능한 노드 제거

이 단계의 질문은 단 하나입니다.
- 이 Pod는 이 Node에서 절대적으로 실행될 수 있는가?

대표적인 필터 조건은
- CPU / Memory 요청량 > Node capacity
- NodeSelector 불일치
- Taint 존재 & Toleration 없음
- PVC가 해당 Node에서 마운트 불가

### Filter Plugin 예제
```go
type GPUFilter struct{}

func (f *GPUFilter) Filter(
  ctx context.Context,
  state *framework.CycleState,
  pod *v1.Pod,
  nodeInfo *framework.NodeInfo,
) *framework.Status {

  if pod.Spec.NodeSelector["gpu"] != "true" {
    return framework.NewStatus(framework.Success)
  }

  if !nodeHasGPU(nodeInfo) {
    return framework.NewStatus(framework.Unschedulable)
  }

  return framework.NewStatus(framework.Success)
}

```

Filter는 Yes OR No 입니다. 하나라도 실패하면 해당 Node는 탈락입니다.


### 5.2 Score 단계 - 가능한 노드 중 최선은?
Filter를 통과한 노드들은 모두 스케쥴링이 가능합니다. 이제 질문이 바뀝니다.
- 어느 Node가 가장 적합한가?

Score 기준
- 리소스 여유가 많은 노드
- Pod affinity 만족
- Data locality
- topology spread

### Score Plugin 예제
```go
func (s *GPUScore) Score(
  ctx context.Context,
  state *framework.CycleState,
  pod *v1.Pod,
  nodeName string,
) (int64, *framework.Status) {

  freeVRAM := getFreeVRAM(nodeName)
  return freeVRAM, framework.NewStatus(framework.Success)
}

```

각 Score plugin은 점수를 계산하고, 최종적으로 가중치 합산으로 Node가 결정됩니다.

### 5.3 Bind 단계 - 결정의 커밋
이 시점에서 스케쥴러는 트랜잭션을 커밋합니다.
- Pod.spec.nodeName = chosen-node
- API Server에 Binding 객체 생성

이 이후는 스케쥴러의 책임이 아닙니다. 실행 실패는 kubelet / runtime 영역입니다.


## 6. 예상 시나리오로 보는 스케쥴러

### 시나리오 1: 리소스는 충분한데 Pod가 Pending

상황
- CPU, Memory 충분
- Pod는 계속 Pending

원인 후보
- Taint + Toleration 불일치
- PVC가 특정 AZ에 묶임
- NodeAffinity 조건 과도

리소스는 Filter 조건의 일부일 뿐입니다.

### 시나리오 2: 특정 노드에만 Pod가 몰림

원인 
- Score 플러그인의 가중치 편향
- PreferredAffinity 과도
- topologySpreadConstraints 미설정

스케쥴러는 균등을 기본으로 보장하지 않습니다.


## 7. 대표적인 유즈케이스

### 7.1 GPU 워크로드
- GPU Node는 희소 자원
- 단순 bin-packing은 비효율

솔루션:
- NodeLael + Affinity
- Custom Score Plugin
- 또는 전용 scheduler profile

### 7.2 멀티 테넌트 클러스터

문제:
- 특정 팀이 리소스를 독식

해결:
- PriorityClass
- ResourceQuota
- Namespace + Scheduler policy 조합


### 7.3 데이터 로컬리티 기반 워크로드
- HDFS, Local PV
- 네트워크 비용이 치명적

솔루션:
- VolumeBinding 고려
- Node-local scoring 강화


## 9. 마무리: 스케쥴러를 더 정확하게 정의하면

"kubernetes Scheduler는 Pod와 Node 사이의 제약조건을 해결하는 정책 엔진" 이다.



















