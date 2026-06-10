---
title: "CKA Workload Section Scinario 10"
date: "2026-06-10T14:48:45.162Z"
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

kget hpa. Cause found. HPA wants to keep Replica number in Deployment from 3 to 5 because maxpods=5 is capped.

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k get hpa
NAME    REFERENCE          TARGETS              MINPODS   MAXPODS   REPLICAS   AGE
nginx   Deployment/nginx   cpu: <unknown>/80m   3         5         5          165m
```

아이콘

k scale deployment nginx --replicas=7 When you run , there are actually seven Deployment. However, the HPA Controller periodically monitors Deployment:> "This Deployment is managed by me, and the maximum Replica is 5." with the judgment thatspec:replicas: 5

and When k get hpa Target cpu rendering  '<unknow>' comes out, it's usually:

- Metrics Server is missing

- Metrics Server Does Not Work

- No CPU request in Pod

It's one of them.

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k top pods
error: Metrics API not available
```

In order for hpa to normally operate we need to either delete or modify the replicas.spec part to raiese upper limit.

```
k delete hpa nginx 
# or
k patch hpa nginx -p '{"spec":{"maxReplicas":10}}’
```

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro 01-configmap % k scale deploy --replicas=7
error: resource(s) were provided, but no name was specified
(base) gimhyeonje@gimhyeonje-ui-MacBookPro 01-configmap % k scale deploy nginx --replicas=7
deployment.apps/nginx scaled
(base) gimhyeonje@gimhyeonje-ui-MacBookPro 01-configmap % k get deploy
NAME    READY   UP-TO-DATE   AVAILABLE   AGE
nginx   7/7     7            7           19h
```

### Create Horizontal Pod Autoscaler named nginx-hpa for the Deployment with an average utiliazation of CPU to 65% and an average utiliazation of memory to 1Gi. Set the minimum number of replicas to 3 and maximum number of replicas 20.

there are several ways to create HPA

### Method 1: Create the YAML directly 

patch the nginx-hpa.yaml file

```
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: nginx-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nginx
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 65
  - type: Resource
    resource:
      name: memory
      target:
        type: AverageValue
        averageValue: 1Gi
```

apply

```
k apply -f nginx-hpa.yaml 
```

verify

```
k get hpa
k describe hpa nginx-hpa
```

### Method 2

if nginx-hpa does not exists, create nginx-hpa deploy first then scale the deployments.

```
k create deploy nginx-hpa --image=nginx 
```

```
k autoscale deploy nginx-hpa \
	--memory=1Gi \
	--cpu=65 \
	--min=3 \
	--max=20 
```

### Method 3: Dry-run YAML generation 

Generation skeleton manifest

```
k autoscale deploy nginx --cpu-percent=65 --min=3 --max=20 --dry-run=client -o yaml > nginx-hpa.yaml
```

### Edit file

```
vi nginx-hpa.yaml 

apiVersion: autoscaleing/v2
metadata:
	name: nginx-hpa
```

and append

```
metrics:
- type: Resource
  resource:
    name: cpu
    target:
      type: Utilization
      averageUtilization: 65
- type: Resource
  resource:
    name: memory
    target:
      type: AverageValue
      averageValue: 1Gi
```

apply

```
kubectl apply -f nginx-hpa.yaml
```

### Update the Pod template of the Deployment to use the image nginx:1.21.1. Make sure tha the changes are recorded. Inspect the revision history. How many revisions should be rendered? Roll back to the first revision.

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro 01-configmap % k autoscale deploy nginx-hpa --cpu=65% --memory=1Gi --min=3 --max=20
horizontalpodautoscaler.autoscaling/nginx-hpa autoscaled
(base) gimhyeonje@gimhyeonje-ui-MacBookPro 01-configmap % k get deploy
NAME        READY   UP-TO-DATE   AVAILABLE   AGE
nginx       7/7     7            7           20h
nginx-hpa   1/1     1            1           68s
(base) gimhyeonje@gimhyeonje-ui-MacBookPro 01-configmap % k get hpa
NAME        REFERENCE              TARGETS                                     MINPODS   MAXPODS   REPLICAS   AGE
nginx       Deployment/nginx       cpu: <unknown>/80m                          3         10        7          22h
nginx-hpa   Deployment/nginx-hpa   cpu: <unknown>/65%, memory: <unknown>/1Gi   3         20        0          9s
(base) gimhyeonje@gimhyeonje-ui-MacBookPro 01-configmap % k describe deploy nginx-hpa
Name:                   nginx-hpa
Namespace:              default
CreationTimestamp:      Wed, 10 Jun 2026 19:56:06 +0900
Labels:                 app=nginx-hpa
Annotations:            deployment.kubernetes.io/revision: 1
Selector:               app=nginx-hpa
Replicas:               3 desired | 3 updated | 3 total | 3 available | 0 unavailable
StrategyType:           RollingUpdate
MinReadySeconds:        0
RollingUpdateStrategy:  25% max unavailable, 25% max surge
Pod Template:
  Labels:  app=nginx-hpa
  Containers:
   nginx:
    Image:         nginx
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
NewReplicaSet:   nginx-hpa-5dffdf7d5c (3/3 replicas created)
Events:
  Type    Reason             Age   From                   Message
  ----    ------             ----  ----                   -------
  Normal  ScalingReplicaSet  37m   deployment-controller  Scaled up replica set nginx-hpa-5dffdf7d5c from 0 to 1
  Normal  ScalingReplicaSet  36m   deployment-controller  Scaled up replica set nginx-hpa-5dffdf7d5c from 1 to 3
(base) gimhyeonje@gimhyeonje-ui-MacBookPro 01-configmap % k get deploy
NAME        READY   UP-TO-DATE   AVAILABLE   AGE
nginx       7/7     7            7           20h
nginx-hpa   3/3     3            3           37m
```

### Create a new Secret named basic-auth of type kubernetes.io/basic-auth.Assign the key-value pairs username=super password=encrypt? Secret as a volume with the path /etc/secret and read-only permissions to the
Pods controlled by the Deployment.

### Method 1: Decalartively Method (file copy → modify → verify → apply)

Deployment copy

```
k get deploy nginx -o yaml > nginx.yaml
```

edit

```
vi nginx.yaml
```

Pod Spec add

```
spec:
	template:
		spec:
			volumes:
			- name: secret-volume
				secret: 
					secretName: basic-auth
```

Container Spec

```
spec:
	template:
		spec:
			containers:
			- name: nginx
				volumeMounts:
				- name: secret-volume
					mountPath: /etc/secret
					readOnly: true
```

syntax Check

```
k apply --dry-run=client -f nginx.yaml
```

apply

```
k apply -f nginx.yaml
```

check difference

```
k diff -f nginx.yaml
```

### Method 2: Imperative Method (patch spec)

```
k patch deployment nginx --patch '
spec:
	template:
		spec:
			volumes:
			- name: secret-volume
				secret:
					secretName: basic-auth
'

```

add VolumeMount

```
k patch deployment nginx --patch '
spec:
	template:
		spec:
			containers:
			- name: nginx
				volumeMounts:
				- name: secret-volume
					mountPath: /etc/secret
					readOnly: true
'
```

after patch, kubernetes will be merget to original file

Or, more safety way is exists

write to file

```
cat > patch.yaml <<EOF
spec:
	template:
		spec:
			volumes:
			- nmae: secret-volume
				secret:
					secretName: basic-auth
EOF
```

apply

```
k patch deployment nginx --patch-file patch.yaml
```

if use the vi editor

```
echo "set expandtab" >> ~/.vimrc
echo "set tabstop=2" >> ~/.vimrc
echo "set shiftwidth=2" >> ~/.vimrc
echo "set softtabstop=2" >> ~/.vimrc
```

every edit command or  vi edit apply indent=2 after this settings.

```
k create secret generic basic-auth \
	--type=kubernetes.io/basic-auth \
	--from-literal=username=super \
	--from-literal=password=encrypt
```

verify

Secret check

```
k get secret basic-auth

NAME         TYPE                       DATA   AGE
basic-auth   kubernetes.io/basic-auth   2      37m
```

type check

```
k get secret basic-auth -o jsonpath='{.type}'

kubernetes.io/basic-auth%
```

Secret Value check

username

```
kubectl get secret basic-auth \
-o jsonpath='{.data.username}' | base64 -d

super%
```

password

```
kubectl get secret basic-auth \
-o jsonpath='{.data.password}' | base64 -d

encrypt%
```

Deployment Volume add check

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k get deploy nginx -o yaml | grep -A5 volumes:
      volumes:
      - name: secret-volume
        secret:
          defaultMode: 420
          secretName: basic-auth
status:
```

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k describe deploy
Name:                   nginx
Namespace:              default
CreationTimestamp:      Tue, 09 Jun 2026 23:51:51 +0900
Labels:                 app=nginx
Annotations:            deployment.kubernetes.io/revision: 3
Selector:               app=nginx
Replicas:               7 desired | 7 updated | 7 total | 7 available | 0 unavailable
StrategyType:           RollingUpdate
MinReadySeconds:        0
RollingUpdateStrategy:  25% max unavailable, 25% max surge
Pod Template:
  Labels:  app=nginx
  Containers:
   nginx:
    Image:        nginx:1.17.0
    Port:         <none>
    Host Port:    <none>
    Environment:  <none>
    Mounts:
      /etc/secret from secret-volume (ro)
  Volumes:
   secret-volume:
    Type:          Secret (a volume populated by a Secret)
    SecretName:    basic-auth
    Optional:      false
  Node-Selectors:  <none>
  Tolerations:     <none>
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Available      True    MinimumReplicasAvailable
  Progressing    True    NewReplicaSetAvailable
OldReplicaSets:  nginx-98786b5c4 (0/0 replicas created), nginx-ccb68cb4f (0/0 replicas created)
NewReplicaSet:   nginx-6d6766dd76 (7/7 replicas created)
Events:
  Type    Reason             Age                From                   Message
  ----    ------             ----               ----                   -------
  Normal  ScalingReplicaSet  26m                deployment-controller  Scaled up replica set nginx-6d6766dd76 from 0 to 2
  Normal  ScalingReplicaSet  26m                deployment-controller  Scaled down replica set nginx-ccb68cb4f from 7 to 6
  Normal  ScalingReplicaSet  26m                deployment-controller  Scaled up replica set nginx-6d6766dd76 from 2 to 3
  Normal  ScalingReplicaSet  26m                deployment-controller  Scaled down replica set nginx-ccb68cb4f from 6 to 5
  Normal  ScalingReplicaSet  26m                deployment-controller  Scaled up replica set nginx-6d6766dd76 from 3 to 4
  Normal  ScalingReplicaSet  26m                deployment-controller  Scaled down replica set nginx-ccb68cb4f from 5 to 4
  Normal  ScalingReplicaSet  26m                deployment-controller  Scaled up replica set nginx-6d6766dd76 from 4 to 5
  Normal  ScalingReplicaSet  26m                deployment-controller  Scaled down replica set nginx-ccb68cb4f from 4 to 3
  Normal  ScalingReplicaSet  26m                deployment-controller  Scaled up replica set nginx-6d6766dd76 from 5 to 6
  Normal  ScalingReplicaSet  26m (x8 over 62m)  deployment-controller  (combined from similar events): Scaled down replica set nginx-ccb68cb4f from 1 to 0


Name:                   nginx-hpa
Namespace:              default
CreationTimestamp:      Wed, 10 Jun 2026 19:56:06 +0900
Labels:                 app=nginx-hpa
Annotations:            deployment.kubernetes.io/revision: 1
Selector:               app=nginx-hpa
Replicas:               3 desired | 3 updated | 3 total | 3 available | 0 unavailable
StrategyType:           RollingUpdate
MinReadySeconds:        0
RollingUpdateStrategy:  25% max unavailable, 25% max surge
Pod Template:
  Labels:  app=nginx-hpa
  Containers:
   nginx:
    Image:         nginx
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
NewReplicaSet:   nginx-hpa-5dffdf7d5c (3/3 replicas created)
Events:          <none>
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ %
```

volumemount check

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % kubectl get deploy nginx -o yaml | grep -A10 volumeMounts:
        volumeMounts:
        - mountPath: /etc/secret
          name: secret-volume
          readOnly: true
      dnsPolicy: ClusterFirst
      restartPolicy: Always
      schedulerName: default-scheduler
      securityContext: {}
      terminationGracePeriodSeconds: 30
      volumes:
      - name: secret-volume
```

Pod Recreate check

A new ReplicaSet must be created because the Pod Template changes when you modify Pod Deployment

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k rollout status deploy/nginx
deployment "nginx" successfully rolled out
```

Pod inside check

```
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k get pods
NAME                         READY   STATUS    RESTARTS   AGE
backend                      1/1     Running   0          29h
demo-pod                     1/1     Running   0          3d23h
nginx-6d6766dd76-5h75n       1/1     Running   0          30m
nginx-6d6766dd76-7w9gh       1/1     Running   0          30m
nginx-6d6766dd76-c6pz7       1/1     Running   0          30m
nginx-6d6766dd76-f722f       1/1     Running   0          30m
nginx-6d6766dd76-fkzf4       1/1     Running   0          30m
nginx-6d6766dd76-h4k8t       1/1     Running   0          30m
nginx-6d6766dd76-hd5mz       1/1     Running   0          30m
nginx-hpa-5dffdf7d5c-9x5k8   1/1     Running   0          3h27m
nginx-hpa-5dffdf7d5c-ff6xk   1/1     Running   0          3h26m
nginx-hpa-5dffdf7d5c-vw7hl   1/1     Running   0          3h26m
redis-0                      1/1     Running   0          46m
redis-1                      1/1     Running   0          46m
redis-2                      1/1     Running   0          46m
(base) gimhyeonje@gimhyeonje-ui-MacBookPro ~ % k exec -it nginx-6d6766dd76-5h75n -- sh
# ls -l /etc/secret
total 0
lrwxrwxrwx 1 root root 15 Jun 10 13:53 password -> ..data/password
lrwxrwxrwx 1 root root 15 Jun 10 13:53 username -> ..data/username

# ls -l /etc/secret
total 0
lrwxrwxrwx 1 root root 15 Jun 10 13:53 password -> ..data/password
lrwxrwxrwx 1 root root 15 Jun 10 13:53 username -> ..data/username

# cat /etc/secret/username
super#

# cat /etc/secret/password
encrypt#

# echo test > /etc/secret/test
sh: 9: cannot create /etc/secret/test: Read-only file system
```

```
kubectl get secret basic-auth

kubectl get deploy nginx -o yaml | grep -A10 volumeMounts

kubectl rollout status deploy/nginx

kubectl exec deploy/nginx -- ls /etc/secret

kubectl exec deploy/nginx -- cat /etc/secret/username
```

read-only check

```
kubectl exec deploy/nginx -- sh -c 'echo test > /etc/secret/test'
```

# Scenario 1: Emergency Rollback of a Production Deployment

### Context

The e-commerce checkout service is currently running in the namespace production.

A new version was deployed 15 minutes ago and customers are reporting payment failures.

### Existing Resources

```
Namespace: production

Deployment: checkout-api

Current Image:
registry.company.com/checkout:v2.3.0
```

### Tasks

1. Identify the rollout history of the Deployment.

1. Roll back the Deployment to the previous working revision.

1. Wait until the rollback has completed successfully.

1. Verify that all Pods are running the previous image version.

1. Save the rollout history to:

```
/opt/course/results/checkout-history.txt
```

### Validation Criteria

The examiner will verify:

```
- Deployment revision was changed
- Pods are healthy
- Previous image is running
- Rollout history file exists
```

Skills Being Tested

```
kubectl rollout history
kubectl rollout undo
kubectl rollout status
kubectl describe deployment
```

### Scenario 2: Traffic Surge and Autoscaling

### Context

The recommendation service experiences heavy traffic during lunch hours.

Management wants automatic scaling based on CPU usage.

### Existing Resources

```
Namespace: analytics

Deployment: recommendation-api

Current Replicas: 2
```

### Tasks

1. Configure the Deployment so that each container has:

```
CPU Request: 250m
CPU Limit: 500m
Memory Request: 256Mi
Memory Limit: 512Mi
```

1. Create a Horizontal Pod Autoscaler named:

```
recommendation-hpa
```

1. Configure the HPA:

```
Minimum Pods: 2
Maximum Pods: 12
Target CPU Utilization: 70%
```

1. Verify that the HPA is able to read CPU metrics.

### Validation Criteria

The examiner will verify:

```
- Resource requests exist
- HPA exists
- HPA references the Deployment
- CPU target is 70%
```

Skills Being Tested

```
kubectl autoscale
kubectl edit deployment
kubectl get hpa
kubectl describe hpa
```

### Scenario 3: Externalizing Application Configuration

### Context

The application team wants to remove environment-specific values from container images.

### Existing Resources

```
Namespace: backend

Deployment: customer-api
```

### Tasks

Create a ConfigMap named:

```
customer-config
```

with the following data:

```
APP_MODE=production
LOG_LEVEL=warn
CACHE_ENABLED=true
```

Modify the Deployment so that all keys from the ConfigMap are injected into the container as environment variables.

Use the most concise method possible.

After applying the changes:

1. Restart the Pods.

1. Verify that the environment variables are available inside a running container.

### Validation Criteria

The examiner will verify:

```
APP_MODE=production
LOG_LEVEL=warn
CACHE_ENABLED=true
```

inside the container.

Skills Being Tested

```
ConfigMap creation
envFrom
Deployment rollout
kubectl exec
```

### Scenario 4: Securing Database Credentials

### Context

A security audit found that database credentials are stored directly in the Deployment manifest.

The credentials must be moved to a Secret.

### Existing Resources

```
Namespace: production

Deployment: orders-api
```

### Tasks

Create a Secret named:

```
orders-db-secret
```

with the following credentials:

```
username=ordersuser
password=Sup3rSecret!
```

Modify the Deployment so that:

```
username -> DB_USERNAME
password -> DB_PASSWORD
```

username -> DB_USERNAME
password -> DB_PASSWORD

### Validation Criteria

The examiner will verify:

```
DB_USERNAME
DB_PASSWORD
```

inside the container.

inside the container.

```
kubectl create secret generic
secretKeyRef
env
kubectl exec
```

### Scenario 5: ConfigMap + Secret + Rolling Update

### Context

A new release of the payment platform must be deployed.

The application requires both configuration data and credentials.

The update must be performed using a rolling Deployment strategy.

### Existing Resources

```
Namespace: finance

Deployment: payment-api

Image:
payment-api:v1
```

### Tasks

Create a ConfigMap named:

```
payment-config
```

with

```
PAYMENT_MODE=live
LOG_LEVEL=info
```

Create a Secret named:

```
payment-secret
```

with:

```
api-key=abc123xyz
```

Modify the Deployment so that:

- ConfigMap values are injected as environment variables using envFrom

- Secret is mounted at:

```
/etc/payment-secret
```

- The Secret volume must be read-only

Update the Deployment image:

```
payment-api:v2
```

Scale the Deployment:

```
3 -> 6 replicas
```

Verify that the rollout completed successfully.

### Validation Criteria

The examiner will verify:

```
- Deployment image updated
- 6 replicas available
- ConfigMap injected
- Secret mounted
- Secret is read-only
- New ReplicaSet created
```

```
Deployment Lifecycle
    ↓
Scale
    ↓
Rollout
    ↓
Rollback
    ↓
ConfigMap Injection
    ↓
Secret Injection
    ↓
HPA
```