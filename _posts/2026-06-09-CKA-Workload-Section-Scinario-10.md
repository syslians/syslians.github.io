---
title: "CKA Workload Section Scinario 10"
date: "2026-06-09T15:34:13.484Z"
categories:
  - "k8s"
  - "k8s-scheduler"
  - "쿠버네티스"
  - "cka"
author: "현제 김_7254"
slug: "cka_workload_section_scinario_10"
---

### Create a Deployment named nginx that uses the image nginx:1.17.0 Set two replicas to begin with

high-level Plan.

this scenaris is quiet simple. it handle it one-command line.

1. create nginx yaml 

```
k crreate deployment nginx --image=nginxL1.17.0 --replicas=2 --dry-run=client -o yaml > nginx.yaml
```

1. result

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k run deployment nginx --image=nginx:1.17.0 --replicas=2
error: unknown flag: --replicas
See 'kubectl run --help' for usage.
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k create deployment nginx --image=nginx:1.17.0 --replicas=2
deployment.apps/nginx created
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k get deployments
NAME    READY   UP-TO-DATE   AVAILABLE   AGE
nginx   0/2     2            0           5s
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k describe deployment
Name:                   nginx
Namespace:              default
CreationTimestamp:      Tue, 09 Jun 2026 23:51:51 +0900
Labels:                 app=nginx
Annotations:            deployment.kubernetes.io/revision: 1
Selector:               app=nginx
Replicas:               2 desired | 2 updated | 2 total | 0 available | 2 unavailable
StrategyType:           RollingUpdate
MinReadySeconds:        0
RollingUpdateStrategy:  25% max unavailable, 25% max surge
Pod Template:
  Labels:  app=nginx
  Containers:
   nginx:
    Image:         nginx:1.17.0
    Port:          <none>
    Host Port:     <none>
    Environment:   <none>
    Mounts:        <none>
  Volumes:         <none>
  Node-Selectors:  <none>
  Tolerations:     <none>
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Available      False   MinimumReplicasUnavailable
  Progressing    True    ReplicaSetUpdated
OldReplicaSets:  <none>
NewReplicaSet:   nginx-98786b5c4 (2/2 replicas created)
Events:
  Type    Reason             Age   From                   Message
  ----    ------             ----  ----                   -------
  Normal  ScalingReplicaSet  10s   deployment-controller  Scaled up replica set nginx-98786b5c4 from 0 to 2
```

### Scale the Deployment to seven replicas using the scale command. Ensure tha the correct number of Pods exist.

high-level plan

first, check the vpa

second, if the vpa checked, scale command with replicas option.

finally, Ensure correct number of Pods exist.

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k autoscale deployment --replicas=7
error: unknown flag: --replicas
See 'kubectl autoscale --help' for usage.
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k scale deployment --replicas=7
error: resource(s) were provided, but no name was specified
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k scale deployment nginx --replicas=7
deployment.apps/nginx scaled
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k get rs
NAME              DESIRED   CURRENT   READY   AGE
nginx-98786b5c4   5         5         5       17m
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k get pods app=nginx
Error from server (NotFound): pods "app=nginx" not found
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k get pods -l app=nginx
NAME                    READY   STATUS    RESTARTS   AGE
nginx-98786b5c4-cs884   1/1     Running   0          18m
nginx-98786b5c4-d9dz5   1/1     Running   0          61s
nginx-98786b5c4-km62t   1/1     Running   0          17m
nginx-98786b5c4-lp4hs   1/1     Running   0          18m
nginx-98786b5c4-rdsbz   1/1     Running   0          61s
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k get pods -l app=nginx --no-headers | wc -l
       5
```

sacle up is pass. but something wrong. i desired nginx seven replicas but current pods just 5. what happened?

first check the nginx deployments sepc.

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k get deploy nginx -o yaml | grep replicas
  replicas: 5
  replicas: 5
```

is 5. why my replicas set 5? check the describe command and analyze cause

as we watch the log, my k scale deployment nginx —replicas=7 is work. and actually deployment controller incerease the replicaset seven. but, 4 scond later, another controller scale down replicaset seven to five. why?

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k describe deploy nginx
Name:                   nginx
Namespace:              default
CreationTimestamp:      Tue, 09 Jun 2026 23:51:51 +0900
Labels:                 app=nginx
Annotations:            deployment.kubernetes.io/revision: 1
Selector:               app=nginx
Replicas:               5 desired | 5 updated | 5 total | 5 available | 0 unavailable
StrategyType:           RollingUpdate
MinReadySeconds:        0
RollingUpdateStrategy:  25% max unavailable, 25% max surge
Pod Template:
  Labels:  app=nginx
  Containers:
   nginx:
    Image:         nginx:1.17.0
    Port:          <none>
    Host Port:     <none>
    Environment:   <none>
    Mounts:        <none>
  Volumes:         <none>
  Node-Selectors:  <none>
  Tolerations:     <none>
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Progressing    True    NewReplicaSetAvailable
  Available      True    MinimumReplicasAvailable
OldReplicaSets:  <none>
NewReplicaSet:   nginx-98786b5c4 (5/5 replicas created)
Events:
  Type    Reason             Age   From                   Message
  ----    ------             ----  ----                   -------
  Normal  ScalingReplicaSet  24m   deployment-controller  Scaled up replica set nginx-98786b5c4 from 0 to 2
  Normal  ScalingReplicaSet  24m   deployment-controller  Scaled up replica set nginx-98786b5c4 from 2 to 3
  Normal  ScalingReplicaSet  7m5s  deployment-controller  Scaled up replica set nginx-98786b5c4 from 3 to 7
  Normal  ScalingReplicaSet  7m1s  deployment-controller  Scaled down replica set nginx-98786b5c4 from 7 to 5
```

this is not problem like insufficence Node resource. because if that case maybe wath the below log. but our case current replica set number is scale down to five some cause . maybe hpa do that

```
FailedScheduling
0/1 nodes are available: Insufficient cpu
```

k get hpa. 원인을 찾았습니다. maxpods=5 로 상한선이 설정되어 있기 때문에 HPA는 Deployments의 Replica수를 3~5로 유지하려고 합니다.

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k get hpa
NAME    REFERENCE          TARGETS              MINPODS   MAXPODS   REPLICAS   AGE
nginx   Deployment/nginx   cpu: <unknown>/80m   3         5         5          165m
```

k scale deployment nginx --replicas=7

를 실행하면 Deployment는 실제로 7개가 됩니다.

하지만 HPA Controller는 주기적으로 Deployment를 감시하면서:

> "이 Deployment는 내가 관리하는데, 최대 Replica는 5개야."

라고 판단하고

spec:
replicas: 5

처럼 현재 CPU 사용량이 보입니다.

<unknown>이 나온다는 것은 대개:

- Metrics Server가 없음

- Metrics Server가 동작하지 않음

- Pod에 CPU request가 없음

중 하나입니다.

(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k top pods
error: Metrics API not available

k delete hpa nginx

k patch hpa nginx -p '{"spec":{"maxReplicas":10{% raw %}}}{% endraw %}'

or another controller ? nope

```
k get deploy nginx -o yaml | grep -A5 managedFields
```

### Create Horizontal Pod Autoscaler named nginx-hpa for the Deployment with an average utiliazation of CPU to 65% and an average utiliazation of memory to 1Gi. Set the minimum number of replicas to 3 and maximum number of replicas 20.

### Update the Pod template of the Deployment to use the image nginx:1.21.1. Make sure tha the changes are recorded. Inspect the revision history. How many revisions should be rendered? Roll back to the first revision.

### Create a new Secret named basic-auth of type kubernetes.io/basic-auth.Assign the key-value pairs username=super password=encrypt? Secret as a volume with the path /etc/secret and read-only permissions to the
Pods controlled by the Deployment.