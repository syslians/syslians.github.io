---
title: "Docker 컨테이너 레벨 Stress Test: CPU·Memory 제한과 cgroup 모니터링"
date: "2026-09-10T12:04:40.720Z"
categories:
  - "linux"
  - "os"
  - "가상화"
author: "현제 김_7254"
slug: "docker_컨테이너_레벨_stress_test_cpumemory_제한과_cgroup_모니터링"
---

이 글은 stress로 컨테이너에 의도적인 CPU·메모리 부하를 발생시키고, Docker의 리소스 제한이 Linux cgroup과 커널 스케줄러에서 어떻게 적용되는지 테스트하고 cAdvisor로 관찰하는 실습이다.

# 1. 실습 목표

컨테이너는 기본적으로 호스트의 CPU, Memory, disk 자원을 쓰게 된다. 명시적으로 리소스 제한을 걸어두지 않으면 하나의 컨테이너에서 호스트의 리소스를 독점하거나 과하게 사용할 우려가 있다. 따라서 이를 cgroup을 통해 리소스들을 제한을 걸어두고, 이를 stress기반 테스트를 통해 관찰하고자 한다.

이번 실습의 목적은 다음 흐름을 직접 확인하는 것이다.

핵심 질문은 하나다. 애플리케이션이 자원을 얼마나 요구하는가와 커널이 실제로 얼마나 허용하는가는 같은가?

# 2. 실습 환경과 Stress 이미지

이번 실습에서는 Debian 기반 이미지에 stress 패키지를 설치한 stressimg 이미지를 사용한다.

```
FROM debian:latest
RUN apt-get update \
    && apt-get install -y stress \
    && rm -rf /var/lib/apt/lists/*
CMD ["stress", "--cpu", "1"]
```

빌드한다.

```
docker image build -t stressimg .
docker image ls stressimg
```

> 

!/assets/image_e5855790-e5b8-47a3-9c12-df8de574aa8e.png

그림 1. Dockerfile 및 이미지 빌드 결과

stress에서 주로 사용할 옵션은 다음과 같다.

# 3. 먼저 제한 없는 컨테이너를 기준값으로 측정한다

리소스 제한을 보기 전에 같은 워크로드를 제한 없이 실행해 기준값을 만든다.

```
docker run -d \
  --name stress-baseline \
  stressimg \
  stress --cpu 1 --timeout 60
```

다른 터미널에서 모니터링한다.

```
docker stats stress-baseline
```

!/assets/image_e5855790-e5b8-47a3-9c12-df8de574aa8e.png

그림2. 제한 없는 CPU 테스트 docker stats 결과

Docker의 stats 화면에서는 CPU 사용률, 메모리 사용량과 제한, 네트워크 I/O, 블록 I/O, PID 수를 함께 볼 수 있다. Linux Docker CLI의 메모리 값은 캐시 처리 방식 때문에 커널의 원시 cgroup 값과 완전히 동일하게 보이지 않을 수 있으므로, 상세 분석에서는 cgroup 파일과 함께 비교하는 편이 좋다.

- --cpu 1은 stress CPU worker를 1개 만든다는 뜻이지 Docker가 CPU를 1개로 제한한다는 뜻이 아니다.

- CPU worker는 가능한 한 계속 연산하려 하므로 CPU 한 논리 코어 수준의 연산 시간을 소비하려 한다.

- 이 시점에는 Docker CPU quota를 지정하지 않았기 때문에 비교 기준값 역할을 한다.

# 4. CPU 제한: stress worker 수와 실제 허용 CPU는 다르다

이번에는 stress worker를 2개 만들지만 컨테이너가 사용할 수 있는 CPU를 0.5 CPU로 제한한다.

```
docker run -d \
  --name stress-cpu-05 \
  --cpus="0.5" \
  stressimg \
  stress --cpu 2 --timeout 120
```

관찰한다.

```
docker stats stress-cpu-05
```

!/assets/image_e5855790-e5b8-47a3-9c12-df8de574aa8e.png

!/assets/image_e5855790-e5b8-47a3-9c12-df8de574aa8e.png

그림 3. docker stats과 htop로 모니터링시 대략 50%씩 쓰는걸 볼 수 있다.

```
stress --cpu 2  (resource request)
└─ CPU를 사용하려는 worker 프로세스 수

Docker --cpus=0.5 (resource limit)
└─ 그 프로세스들이 합쳐서 사용할 수 있는 CPU time의 상한
```

!/assets/image_e5855790-e5b8-47a3-9c12-df8de574aa8e.png

그림 4. 현재 두 개의 프로세스가 프로세스에 할당된 cpu limit을 가지고 경쟁한다. 그림으로 나타내면 위와 같다.

즉 worker가 2개라고 해서 두 CPU를 온전히 사용할 수 있는 것이 아니다. Docker는 컨테이너 cgroup에 CPU quota를 설정하고 Linux 스케줄러가 그 한도에 맞춰 실행 시간을 제한한다.

Docker 공식 문서 기준 --cpus="0.5"는 CPU period/quota 형태의 제한으로 변환된다. 기본적인 예에서는 100000µs period에 대해 50000µs quota와 같은 의미가 된다.

!/assets/image_e5855790-e5b8-47a3-9c12-df8de574aa8e.png

그림 5. Linux CFS 스케쥴링을 기준으로 도식화한 그림.

Docker --cpus=0.5, period = 100ms, quota  =  50ms

100ms라는 시간 구간(time window)마다 컨테이너 전체 프로세스(현재 worker2개)가 합쳐서
CPU time 50ms를 사용할 수 있다. 컨테이너의 프로세스는 cgroup으로 묶이게 되고, 컨테이너 내에서 생성된 모든 프로세스들은 이 cgroup에 할당된 리소스만큼만 사용할 수 있다.

100ms period
0ms                                                          100ms
│------------------------------------------------│

worker1  █████████████
약 25ms

worker2               █████████████
약 25ms

throttle                           ░░░░░░░░░░░░░░
약 50ms

if (worker1 ≈ 25ms + worker2 ≈ 25ms) > resource quota(50ms)

then throttle container

한 컨테이너는 cgroup에 할당된 quota 만큼의 cpu를 쓸 수 있게 되고, 이 할당량을 초과하게 되면 프로세스는 스케쥴링을 받지 못한다.

CFS가 비교적 공정하게 스케쥴링을 한다면 2개의 프로세스는 50ms 라는 한도내에서 약 25ms씩 실행을 보장받을 수 있게 된다.

# 5. CPU 제한을 cgroup v2에서 직접 확인하기

컨테이너 PID를 확인한다.

```
PID=$(docker inspect -f '{{.State.Pid}}' stress-cpu-05) && echo "$PID" && cat /proc/$PID/cgroup
```

!/assets/image_e5855790-e5b8-47a3-9c12-df8de574aa8e.png

그림 6. 현재 프로세스가 어느 cgroup에 속하는지 확인

환경에 따라 systemd cgroup driver를 사용할 수 있으므로 실제 디렉터리 경로는 시스템마다 다를 수 있다. 확인한 cgroup 디렉터리에서 핵심 파일을 읽는다.

```
cat /sys/fs/cgroup/<CONTAINER_CGROUP_PATH>/cpu.max
cat /sys/fs/cgroup/<CONTAINER_CGROUP_PATH>/cpu.stat
```

cpu.max는 cgroup v2에서 CPU bandwidth 제한을 표현한다. cpu.stat에서는 실제 사용 시간과 throttling 관련 통계를 관찰할 수 있다.

!/assets/image_e5855790-e5b8-47a3-9c12-df8de574aa8e.png

그림 7. cat /sys/fs/cgroup의 출력 결과

cgroup의 형식은 50000us(max), 100000us(period) 이다. 그리고 cpu.stat으로 출력결과를 해석해보면 usage_usec은 총 CPU 사용시간이다. 
user_usec    63683290 은 유저모드에서 대략 63초가량 실행을 했다는것이고
system_usec    514108 systemcall로 커널모드에서 0.5초 가량 실행을했다는 것이다.

CPU 사용 시간 ≈ 64.2초

├─ userspace ≈ 63.7초
└─ kernel    ≈  0.5초

6. 메모리 제한: 256MiB 컨테이너에서 512MiB를 요구하기

메모리 테스트에서는 컨테이너의 제한보다 큰 메모리를 stress가 요구하도록 만든다.

```
docker run -d \
  --name stress-mem-256 \
  --memory=256m \
  stressimg \
  stress --vm 1 --vm-bytes 512M --vm-hang 0
```

동시에 모니터링한다.

```
docker stats stress-mem-256
```

여기서 중요한 점은 --vm-bytes 512M이 메모리를 반드시 성공적으로 512MiB까지 확보한다는 의미가 아니라는 것이다. stress는 그만큼 할당하고 사용하려 시도하지만 컨테이너 cgroup의 제한과 호스트 메모리 상황에 의해 실제 결과가 결정된다.

컨테이너가 종료되었다면 상태를 확인한다.

```
docker ps -a --filter name=stress-mem-256

docker inspect stress-mem-256 \
  --format 'Status={{.State.Status}} ExitCode={{.State.ExitCode}} OOMKilled={{.State.OOMKilled}} Error={{.State.Error}}'
```

> [PLACEHOLDER 08 — OOMKilled / ExitCode 확인 결과]

> 실제 docker inspect 결과를 삽입한다. OOMKilled가 true인지, ExitCode가 무엇인지 함께 기록한다.

### 메모리 제한의 흐름

```
flowchart TD
  A["stress --vm 1 --vm-bytes 512M"] --> B["malloc / page touch"]
  B --> C["Container memory cgroup"]
  C --> D{"memory.max = 256MiB 부근"}
  D -->|"한도 내부"| E["메모리 사용 허용"]
  D -->|"한도 초과 + 회수 실패"| F["cgroup OOM"]
  F --> G["프로세스 종료 가능"]
  G --> H["Docker State.OOMKilled 관찰"]
```

# 7. 메모리 제한을 cgroup v2에서 확인하기

실행 중인 컨테이너라면 CPU 테스트와 같은 방식으로 cgroup 경로를 찾는다.

```
PID=$(docker inspect -f '{{.State.Pid}}' stress-mem-256)
cat /proc/$PID/cgroup
```

그리고 실제 경로에서 다음 파일을 본다.

```
cat /sys/fs/cgroup/<CONTAINER_CGROUP_PATH>/memory.current
cat /sys/fs/cgroup/<CONTAINER_CGROUP_PATH>/memory.max
cat /sys/fs/cgroup/<CONTAINER_CGROUP_PATH>/memory.events
```

memory.current는 현재 메모리 사용량, memory.max는 hard limit, memory.events는 high/max/oom/oom_kill 등의 이벤트를 확인하는 데 유용하다.

> [PLACEHOLDER 09 — memory.current / memory.max / memory.events]

> 메모리 테스트 전후 값을 삽입한다. 특히 oom, oom_kill, max 카운터의 변화가 있으면 표시한다.

# 8. Docker stats와 cgroup 값은 각각 무엇을 보여주는가

docker stats만으로 현상을 보고 끝내기보다 Docker 설정 → 컨테이너 PID → cgroup 경로 → 커널 통계 순으로 내려가면 리소스 제한이 어디에서 발생했는지를 설명할 수 있다.

# 9. CPU와 메모리를 동시에 제한하는 혼합 테스트

실제 애플리케이션은 CPU나 메모리 하나만 사용하는 것이 아니므로 마지막에는 혼합 부하를 실행한다.

```
docker run -d \
  --name stress-mixed \
  --cpus="1.0" \
  --memory=512m \
  stressimg \
  stress \
    --cpu 2 \
    --vm 1 \
    --vm-bytes 384M \
    --timeout 120
```

관찰용 명령은 다음처럼 묶을 수 있다.

```
docker stats stress-mixed

docker inspect stress-mixed \
  --format 'PID={{.State.Pid}} NanoCpus={{.HostConfig.NanoCpus}} Memory={{.HostConfig.Memory}} OOMKilled={{.State.OOMKilled}}'
```

> [PLACEHOLDER 10 — 혼합 테스트 결과]

> CPU %, MEM USAGE / LIMIT, PIDS와 inspect 설정값을 삽입한다.

> [PLACEHOLDER 11 — 혼합 테스트 그래프 또는 스크린샷]

> docker stats 화면이나 별도 모니터링 도구의 CPU/Memory 그래프를 삽입한다.

# 10. 선택 실습: Block I/O 부하 관찰

stress --hdd는 파일 write/unlink 작업을 반복할 수 있다.

```
docker run --rm \
  --name stress-io \
  stressimg \
  stress --hdd 1 --hdd-bytes 512M --timeout 60
```

다른 터미널에서:

```
docker stats stress-io
```

> [PLACEHOLDER 12 — BLOCK I/O 변화]

> 실행 전후의 BLOCK I/O 값을 삽입한다. 컨테이너 writable layer와 호스트 스토리지의 특성에 따라 결과가 달라질 수 있다는 점도 함께 기록한다.

이 테스트에서 보이는 값은 단순히 애플리케이션 write 호출량과 동일하다고 보면 안 된다. 페이지 캐시, OverlayFS, 실제 블록 디바이스 flush 등 여러 계층이 사이에 존재한다.

# 11. 반복 측정을 위한 간단한 수집 명령

실험 결과를 남기려면 docker stats --no-stream을 주기적으로 호출해 파일에 저장할 수 있다.

```
CONTAINER=stress-mixed
OUT="${CONTAINER}-stats.log"

for i in $(seq 1 12); do
  date '+%F %T'
  docker stats --no-stream \
    --format 'name={{.Name}} cpu={{.CPUPerc}} mem={{.MemUsage}} mem_pct={{.MemPerc}} block={{.BlockIO}} pids={{.PIDs}}' \
    "$CONTAINER"
  sleep 5
done | tee "$OUT"
```

> [PLACEHOLDER 13 — 5초 간격 수집 로그]

> 생성된 stress-mixed-stats.log 일부를 삽입한다.

# 12. 실험 결과 정리 템플릿

실습을 끝낸 뒤 아래 표에 실제 측정값을 채운다.

# 13. 실습에서 이해해야 할 핵심

컨테이너의 리소스 제한은 애플리케이션 자체가 스스로 지키는 제한이 아니다. 애플리케이션은 계속 CPU를 요구하거나 메모리를 할당하려 할 수 있다. Docker가 생성한 컨테이너의 cgroup 설정을 통해 Linux 커널이 실행 시간과 메모리 사용량을 통제한다.

따라서 관찰 계층을 다음과 같이 나누면 이해가 쉽다.

```
stress
  └─ 자원을 요구하는 애플리케이션
       ↓
Docker run / HostConfig
  └─ 사용자가 지정한 제한
       ↓
cgroup v2
  └─ cpu.max / memory.max 등 커널 제어값
       ↓
Linux kernel
  └─ CPU throttling / memory reclaim / OOM 처리
       ↓
docker stats / inspect / cgroup metrics
  └─ 결과 관찰
```

CPU 테스트에서는 worker 수와 허용 CPU가 별개라는 점이 핵심이고, 메모리 테스트에서는 요청 메모리와 실제 확보 가능한 메모리가 별개라는 점이 핵심이다.

# 14. 다음 단계

이 실습은 Docker 단일 컨테이너의 cgroup 제한을 이해하기 위한 기반이다. 같은 원리는 이후 Kubernetes의 resources.requests, resources.limits, CPU throttling, OOMKilled, QoS Class, Metrics Server와 연결할 수 있다.

관련 학습 기록:

Minikube에서 OOMKilled 직접 재현하기: Go 컨테이너로 메모리 제한 관찰

containerd·runc·dockershim 구조 완전 정리: Docker와 Kubernetes의 실행 경로

# 참고 자료

- Docker Docs — Resource constraints

- Docker Docs — docker container stats

- Docker Docs — Runtime metrics

> 💡 작성 후 보완 체크: PLACEHOLDER 01~13을 실제 터미널 출력, 스크린샷, 측정값으로 교체하고 CPU 제한 전후 및 OOM 발생 전후를 비교해 최종 결론을 업데이트한다.

# 실습 목표

같은 클라이언트 IP가 같은 서버로 가는지, 서버 한 대를 제외했을 때 얼마나 많은 IP의 목적지가 바뀌는지 직접 측정한다. roundrobin, source + map-based, source + consistent를 같은 조건으로 비교한다.

제공된 설정을 기반으로 설계한 실습 가이드다. 실제 서버에서 실행한 결과는 아직 없으며, 아래 PLACEHOLDER에 측정 출력과 스크린샷을 첨부한다.

# 1. 현재 아키텍처와 테스트 범위

```
flowchart TD
    E["외부 클라이언트"] --> F["docker2 HAProxy :80"]
    L["docker2 로컬 테스트 클라이언트"] -->|"출발지 127.0.0.2 ~ 127.0.0.201"| F
    F --> A{"url_static ACL"}
    A -->|"정적 경로 또는 확장자"| S["static: 127.0.0.1:4331"]
    A -->|"그 외 경로 /"| B["backend app"]
    subgraph HOST["192.168.2.10의 서비스 엔드포인트"]
        P1["app1 :8081"]
        P2["app2 :8082"]
        P3["app3 :8083"]
    end
    B --> P1
    B --> P2
    B --> P3
```

docker2의 LAN IP는 제공되지 않았으므로 임의로 지정하지 않는다. 192.168.2.10은 세 backend가 공유하는 목적지 IP다. docker2와 같은 호스트인지, 각 포트 뒤에 어떤 컨테이너가 있는지는 별도 확인이 필요하다. 위 그림은 확인된 서비스 주소만 표현한다.

서버 세 대가 아니라 서로 다른 포트의 서비스 세 개다. 같은 호스트에 있다면 호스트 장애 시 모두 영향을 받으며 물리적 고가용성 테스트와 구분해야 한다.

테스트 URL은 / 를 사용한다. /static, /images, /javascript, /stylesheets 또는 .jpg/.gif/.png/.css/.js로 끝나는 요청은 static backend로 빠진다. static의 서버는 한 개이므로 app 알고리즘 비교 대상이 아니다.

> 📷 PLACEHOLDER-01 — 현재 haproxy.cfg, docker2 IP, 8081~8083 서비스 또는 Docker 포트 매핑 출력

# 2. 사전 점검과 원본 보관

docker2에서 root로 실행한다.

```
haproxy -vv
ip -br addr
ss -lntp
cp -a /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.before-hash-lab

for port in 8081 8082 8083; do
    curl --noproxy '*' -sS -o /dev/null -w "$port HTTP=%{http_code}\n"       --connect-timeout 3 --max-time 10 "http://192.168.2.10:$port/"
done
```

백업 파일 이름이 이미 존재하면 다른 이름으로 보관한다. 세 서비스가 같은 Host 헤더와 / 경로에서 정상 응답하는지 확인한다. 기존 check는 기본적으로 TCP 연결 검사이므로 UP이 HTTP 200을 보장하지는 않는다.

> 📷 PLACEHOLDER-02 — HAProxy 버전 및 각 backend 직접 접근 결과

# 3. 관측 가능한 실습 설정

기존 global에 다음 한 줄을 추가한다. global 구간 자체를 새로 중복 생성하지 않는다.

```
stats socket /run/haproxy-hash-lab.sock mode 600 level admin
```

frontend main에 출발지 IP 기록용 규칙을 추가한다.

```
http-request set-var(txn.lab_src) src
```

기존 backend app만 다음으로 교체한다. defaults, frontend의 ACL과 static backend는 유지한다.

```
backend app
    balance roundrobin

    http-response set-header X-Lab-Backend %[srv_name]
    http-response set-header X-Lab-Source %[var(txn.lab_src)]

    server app1 192.168.2.10:8081 id 1 weight 1 check inter 2s fall 3 rise 2
    server app2 192.168.2.10:8082 id 2 weight 1 check inter 2s fall 3 rise 2
    server app3 192.168.2.10:8083 id 3 weight 1 check inter 2s fall 3 rise 2
```

진단 헤더는 실습 후 제거한다. 서버 id, 순서, weight는 비교 중 고정한다. 기존 option redispatch는 연결 실패 시 선택에 영향을 줄 수 있으므로 안정된 서버 상태에서 측정한다. cookie나 stick on 설정이 추가되어 있다면 순수 알고리즘 비교에 영향을 준다.

```
haproxy -c -f /etc/haproxy/haproxy.cfg && systemctl reload haproxy
curl --noproxy '*' -sS -D - -o /dev/null http://127.0.0.1/
```

문법 검사는 설치 버전 기준이다. 오류가 있으면 reload하지 않고 해당 지시어를 점검한다. socat과 python3가 없다면 설치한다.

```
dnf install -y socat python3
printf 'show stat\n' | socat - UNIX-CONNECT:/run/haproxy-hash-lab.sock
```

Runtime API의 show stat은 CSV 통계를 제공한다. 출력에서 app1~app3의 status를 확인한다. show stat 공식 문서

> 📷 PLACEHOLDER-03 — 문법 검사 성공, X-Lab-Backend/X-Lab-Source, 세 서버 UP 상태

# 4. 비교할 알고리즘

source는 HAProxy가 보는 실제 접속 출발지 IP를 사용한다. option forwardfor는 그 정보를 backend에 전달하는 기능이며, 클라이언트가 임의로 넣은 X-Forwarded-For를 source 알고리즘의 입력으로 바꾸지 않는다. NAT 뒤의 여러 사용자는 하나의 IP로 보일 수 있다.

consistent hashing의 목표는 완벽한 균등 분배보다 서버 구성 변경 시 매핑 변화의 축소다. 서버 복귀 시 일부 IP가 원래 서버로 돌아갈 수 있으며, 이것이 애플리케이션 세션 데이터 복제를 의미하지는 않는다. HAProxy IP hashing 설명

```
flowchart TD
    I["동일한 IP 집합"] --> H["IP 해시 계산"]
    H --> V["서버별 여러 가상 지점에 매핑"]
    V --> ALL["app1 / app2 / app3 정상"]
    ALL --> REMOVE["app2를 선택 대상에서 제외"]
    REMOVE --> KEEP["영향받지 않은 IP: 목적지 유지"]
    REMOVE --> MOVE["영향받은 IP: app1 또는 app3"]
    KEEP --> RESTORE["app2 복귀 후 다시 매핑 비교"]
    MOVE --> RESTORE
```

위 그림은 개념도다. 실제 가상 지점과 이동 비율을 임의의 IP 예시로 확정하지 않는다.

# 5. 같은 IP로 반복 요청

docker2에서 실행한다.

```
for i in $(seq 1 30); do
    curl --noproxy '*' --interface 127.0.0.2 -sS       --connect-timeout 3 --max-time 10 -D - -o /dev/null       http://127.0.0.1/ |
      tr -d '\r' | grep -i '^X-Lab-Backend:'
done
```

roundrobin으로 측정한 뒤 balance source와 hash-type consistent로 교체하고 문법 검사·reload 후 반복한다. 각 curl은 새 연결을 사용한다. roundrobin의 엄격한 출력 순서는 다른 트래픽 등에 영향을 받을 수 있어 전체 분포를 본다.

source 모드에서 같은 IP가 한 서버로 향하더라도 그것만으로 consistent hashing의 효과를 증명한 것은 아니다. map-based도 정상 상태에서는 IP별 매핑이 고정된다.

> 📷 PLACEHOLDER-04 — 같은 IP 30회 요청의 roundrobin/consistent 결과 비교

# 6. 실제 출발지 IP 200개로 매핑 수집

Linux docker2의 loopback 주소를 이용해 127.0.0.2~127.0.0.201을 출발지로 바인딩한다. 목적지는 반드시 같은 호스트의 127.0.0.1이다. 이 주소들을 원격 서버 접속용 IP로 사용하지 않는다.

이 방법은 IP 해시 선택을 재현하는 로컬 실험이며 LAN·NAT 경로 성능을 측정하지 않는다. 별도 LAN IP를 무단 할당할 필요가 없다. 먼저 X-Lab-Source가 지정 주소와 일치하는지 확인한다.

```
curl --noproxy '*' --interface 127.0.0.20 -sS -D -   -o /dev/null http://127.0.0.1/
```

docker2에 다음을 collect-hash.py로 저장한다.

```
import csv
import subprocess
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: python3 collect-hash.py OUTPUT.csv")

rows = []
for n in range(2, 202):
    ip = f"127.0.0.{n}"
    p = subprocess.run(
        ["curl", "--noproxy", "*", "--interface", ip, "-sS",
         "--connect-timeout", "3", "--max-time", "10",
         "-D", "-", "-o", "/dev/null", "http://127.0.0.1/"],
        capture_output=True, text=True
    )
    headers = {}
    status = ""
    for line in p.stdout.splitlines():
        if line.startswith("HTTP/"):
            headers = {}
            status = line.split()[1]
        elif ":" in line:
            k, v = line.split(":", 1)
            headers[k.lower()] = v.strip()
    backend = headers.get("x-lab-backend", "")
    seen = headers.get("x-lab-source", "")
    if p.returncode or status != "200" or seen != ip or backend not in {
        "app1", "app2", "app3"
    }:
        raise SystemExit(
            f"Invalid sample: ip={ip}, seen={seen}, backend={backend}, "
            f"HTTP={status}, error={p.stderr.strip()}"
        )
    rows.append((ip, backend))

# 모든 샘플이 성공한 경우에만 새 파일로 저장한다.
with open(sys.argv[1], "x", newline="") as f:
    w = csv.writer(f)
    w.writerow(["source_ip", "backend"])
    w.writerows(rows)
print(f"Saved {len(rows)} samples to {sys.argv[1]}")
```

스크립트는 HTTP 200과 출발지·backend 헤더를 검증한다. / 가 원래 200을 반환하지 않는 서비스면 app으로 향하는 정상 경로를 먼저 정해서 URL을 변경한다. 기존 출력 파일이 있으면 덮어쓰지 않으므로 새 파일명으로 실행한다.

# 7. 서버 제외·복구 전후의 재매핑 측정

먼저 map-based로 다음 실험을 끝낸 뒤 consistent로 똑같이 반복한다. 각 모드 사이에는 세 서버를 모두 ready/UP으로 복원한다.

## 7-1. map-based 기준선

```
balance source
hash-type map-based
```

검사·reload 후 세 서버 UP을 확인하고 수집한다.

```
python3 collect-hash.py map-before.csv
```

## 7-2. app2를 계획적으로 제외

서비스를 실제로 중단하지 않고 HAProxy 선택 대상에서 제외한다. 이 단계는 장애 감지 시간 실험과 구분한다.

```
printf 'set server app/app2 state maint\n' | socat - UNIX-CONNECT:/run/haproxy-hash-lab.sock
printf 'show stat\n' | socat - UNIX-CONNECT:/run/haproxy-hash-lab.sock
python3 collect-hash.py map-down.csv
```

status가 MAINT인지 확인한다. app2가 수집 결과에 남으면 상태 적용 또는 다른 HAProxy 인스턴스 접속 여부를 점검한다.

## 7-3. app2 복귀

```
printf 'set server app/app2 state ready\n' | socat - UNIX-CONNECT:/run/haproxy-hash-lab.sock
printf 'show stat\n' | socat - UNIX-CONNECT:/run/haproxy-hash-lab.sock
```

ready는 서비스 정상화를 보장하는 명령이 아니다. health check가 통과해서 실제 UP이 된 후 수집한다.

```
python3 collect-hash.py map-restored.csv
```

Runtime 상태 변경은 메모리상의 조작이며 reload 후 유지된다고 가정하지 않는다. set server 공식 문서

## 7-4. consistent에서 동일하게 반복

```
balance source
hash-type consistent
```

검사·reload와 UP 확인 후:

```
python3 collect-hash.py consistent-before.csv
printf 'set server app/app2 state maint\n' | socat - UNIX-CONNECT:/run/haproxy-hash-lab.sock
python3 collect-hash.py consistent-down.csv
printf 'set server app/app2 state ready\n' | socat - UNIX-CONNECT:/run/haproxy-hash-lab.sock
```

다시 UP임을 확인한 후:

```
python3 collect-hash.py consistent-restored.csv
```

> 📷 PLACEHOLDER-05 — map-based의 before/MAINT/복귀 출력과 CSV

> 📷 PLACEHOLDER-06 — consistent의 before/MAINT/복귀 출력과 CSV

# 8. 재매핑 비율 계산

다음을 compare-hash.py로 저장한다.

```
import csv
import sys
from collections import Counter

def read(path):
    with open(path, newline="") as f:
        return {r["source_ip"]: r["backend"] for r in csv.DictReader(f)}

if len(sys.argv) != 3:
    raise SystemExit("usage: python3 compare-hash.py BEFORE.csv AFTER.csv")
a, b = map(read, sys.argv[1:])
if not a or a.keys() != b.keys():
    raise SystemExit("Source IP sets differ or are empty")

changed = [ip for ip in a if a[ip] != b[ip]]
unaffected = [ip for ip in a if a[ip] != "app2"]
extra = sum(a[ip] != b[ip] for ip in unaffected)
print("Before:", dict(Counter(a.values())))
print("After :", dict(Counter(b.values())))
print(f"Remapped: {len(changed)}/{len(a)} = {len(changed)/len(a):.2%}")
print(f"Originally outside app2, changed: {extra}/{len(unaffected)}")
for ip in changed[:20]:
    print(ip, a[ip], "->", b[ip])
```

```
python3 compare-hash.py map-before.csv map-down.csv
python3 compare-hash.py consistent-before.csv consistent-down.csv
python3 compare-hash.py map-before.csv map-restored.csv
python3 compare-hash.py consistent-before.csv consistent-restored.csv
```

중요한 지표는 전체 변경 비율과 원래 app2가 아니었던 IP까지 바뀌었는지다. 알고리즘 간 비교는 각자의 기준선 대비 수행한다. map-before와 consistent-before를 직접 비교한 차이는 장애 영향이 아니라 알고리즘 자체의 매핑 차이다.

균등한 이상 모델에서 app2가 약 1/3을 담당하면 그에 가까운 IP가 영향을 받을 수 있지만 실제 비율을 33.3%로 단정하지 않는다. 200개의 연속된 loopback IP는 제한된 표본이다. 해시 함수, weight, 서버 식별자, health 상태, 재시도 등의 조건도 기록한다.

> 📷 PLACEHOLDER-07 — 비교 스크립트 출력과 완성한 측정 표

> 📝 PLACEHOLDER-08 — 실측 결론: 가설 일치 여부, 예상과 다른 매핑, 원인 분석

# 9. 선택 실험: 실제 장애와 기타 알고리즘

실제 app2 프로세스 또는 해당 컨테이너만 중지하고 check가 DOWN을 감지하는 동안 요청 실패와 재배치를 관찰한다. 실제 컨테이너 이름이 제공되지 않았으므로 임의의 docker stop 명령은 쓰지 않는다. inter/fall/rise가 감지·복귀 지연에 영향을 주며 정확한 시간은 측정한다. 다른 서비스나 공용 호스트 전체를 중지하지 않는다.

leastconn 비교는 balance leastconn으로 바꾸고 장시간 응답하는 실제 경로에 동시 요청을 보낸다. 빠른 순차 요청만으로 차이를 판단하지 않는다. weighted roundrobin은 app1/app2/app3 weight를 1/2/3으로 바꿔 요청 분포를 측정한다. 두 실험 후에는 consistent 비교를 위해 weight를 모두 1로 복원한다.

> 📷 PLACEHOLDER-09 — 실제 장애 시 DOWN 전환 시각, 실패 요청, 복구 출력

> 📷 PLACEHOLDER-10 — 선택 실험: leastconn 또는 weight 1:2:3 결과

# 10. 해석 시 주의할 점과 원복

- 같은 서버로 간다는 것은 요청 경로의 친화성이다. 로그인 세션·파일·DB 상태를 서버 간 공유해 주지 않는다.

- IP 하나에서 요청 수만 늘리는 실험으로는 IP 간 분포를 판단할 수 없다.

- 503 또는 헤더 누락을 정상 서버 매핑으로 집계하지 않는다.

- 외부 클라이언트 검증은 docker2의 실제 LAN IP로 접속하고 X-Lab-Source로 NAT 여부를 확인한다.

- 이 글의 원본 defaults는 HTTP 모드다. MySQL TCP 로드밸런싱 설정과 섞지 않는다.

원본으로 되돌릴 경우:

```
cp -a /etc/haproxy/haproxy.cfg.before-hash-lab /etc/haproxy/haproxy.cfg
haproxy -c -f /etc/haproxy/haproxy.cfg && systemctl reload haproxy
```

실제 중지한 서비스가 있다면 별도로 다시 시작한다. 원본 복원 시 실험 이후의 다른 설정 변경도 되돌아가므로 차이를 확인한다.

# 참고 자료

HAProxy 설정 매뉴얼: balance, hash-type, health check

HAProxy: Client IP Persistence and Source IP Hash

Runtime API: set server

Runtime API: show stat

nmcli con mod ens33 \
ipv4.dns ""

names\

permiisive mode

enforcing  selinux 모드 활성화
disable

nmcli con mod ens33 ipv4.address 192.168.2.20/24

nmcli con up ens33 && systemctl restart NetworkManager

nmcli con mod ens33 ipv4.address 192.168.2.30/24

nmcli con up ens33 && systemctl restart NetworkManager

curl -fsSl http://get.docker.com -o get-docker.sh
sudo sh ./get-docker.sh --dry-run

1. dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

1. rm -f /etc/yum.repos.d/docker-ce- docker-ce-cli conatinerd.io docker-compose-plugin docker-ce-rootless-extras docker docker-buildx-plugion
docker-model-plugin

systemctl enable --noew docker.service 2>/dev/null

docker 이미지 파일 생성 후 테스트
docker run --name some-nginx -v /some/content:/usr/share/nginx/html:ro -d nginx

systemctl enable --now docker
systemctl status docker

/var/lib/docker -----> docker root 디렉토리

"Entrypoint": [
"/docker-entrypoint.sh"
],
"Cmd": [
"nginx",
"-g",
"daemon off;"
]

docker run nginx:latest

docker는 Entrypoint와 CMD를 결합

/docker-entrypoint.sh nginx -g "daemon off;"

1. 컨테이너 시작

1. /docker-entrypoint.sh 실행

1. nginx 설정 초기화

1. nginx -g "daemon off;" 실행

1. nginx가 컨테이너의 메인 프로세스로 유지

daemon off;는 nginx를 백그라운드로 보내지 않고 포그라운드로 실행
이 프로세스가 종료되면 컨테이너도 종료

"StopSignal" : "SIGQUIT" --> docker stop으로 컨테이너를 중지시 docker는
SIGQUIT signal을 보내 정상 종료 요청. nginx는 기존 연결등을 정리한 뒤
종료.

docker run -it --name centos9 \
quay.io/centos/centos:stream9 \
/bin/bash

docker image inspect --format="{% raw %}{{{% endraw %}.Config.Cmd{% raw %}}}{% endraw %}" ubuntu

https://checkip.amazonaws.com/

# 핵심 개념

containerd는 컨테이너 관리자, runc는 실제 실행을 담당하는 하위 런타임, dockershim은 과거 Kubernetes와 Docker 사이의 API 변환 계층이다. containerd-shim은 컨테이너 프로세스를 감독하는 별도 구성 요소다.

이 글은 Linux의 일반적인 runc 기반 구성을 설명한다. 구조도의 화살표는 요청·호출 관계이며, 모두 OS 부모·자식 프로세스 관계를 뜻하지 않는다.

# 1. 이름과 역할부터 분리하기

containerd와 runc를 모두 런타임이라고 부르는 이유는 용어의 범위가 넓기 때문이다. containerd는 관리 계층, runc는 OCI 실행 계층에 해당한다. containerd 공식 소개

# 2. 과거와 현재 구조 비교

```
flowchart TD
  subgraph OLD["과거 Kubernetes의 Docker 경로"]
    K1["kubelet"] --> DS["내장 dockershim"]
    DS -->|"Docker Engine API"| D1["dockerd"]
    D1 --> C1["containerd"]
  end
  subgraph NOW["현재의 containerd 직접 연동"]
    K2["kubelet"] -->|"CRI / gRPC"| CRI["containerd의 CRI 구현"]
    CRI --> C2["containerd 내부 기능"]
  end
  C1 --> S1["containerd-shim"]
  C2 --> S2["containerd-shim-runc-v2"]
  S1 -->|"필요할 때 호출"| R1["runc"]
  S2 -->|"필요할 때 호출"| R2["runc"]
```

과거 경로의 아래쪽은 이해를 위해 단순화했다. 실제 shim 이름과 버전은 당시 배포판에 따라 다르다. 현재 경로의 CRI 구현과 containerd 내부 기능은 별도 데몬 두 개를 뜻하지 않는다.

Docker Engine이 CRI를 직접 구현하지 않았기 때문에 dockershim이 필요했다. containerd는 CRI를 제공하므로 kubelet이 Docker Engine을 거치지 않고 연결할 수 있다. 내장 dockershim은 Kubernetes 1.24에서 제거됐다. Docker Engine을 계속 연동하려면 외부 어댑터인 cri-dockerd를 사용하는 경로가 있다. Docker로 만든 이미지 자체가 사용 불가능해진 것은 아니다. Kubernetes Dockershim FAQ

일반 Docker CLI 사용 경로는 Docker CLI → dockerd → containerd → containerd-shim → runc다. 여기에 kubelet이나 dockershim은 필요하지 않다.

# 3. dockershim과 containerd-shim은 무엇이 다른가

dockershim 제거는 containerd-shim 제거를 의미하지 않는다. 이름의 shim은 중간 연결 계층이라는 공통 의미일 뿐, 위치와 책임은 다르다. Dockershim FAQ, Runtime V2

# 4. runc가 종료돼도 컨테이너는 실행된다

```
sequenceDiagram
  participant C as containerd
  participant S as containerd-shim
  participant R as runc 명령
  participant P as 컨테이너 초기 프로세스
  C->>S: 태스크 생성 요청
  S->>R: runc create
  R->>P: 격리 환경 준비 및 대기
  R-->>S: create 명령 반환
  C->>S: 시작 요청
  S->>R: 별도의 runc start 호출
  R->>P: 실행 대기 해제
  P->>P: exec로 애플리케이션 실행
  R-->>S: start 명령 반환
  Note over S,P: shim과 애플리케이션은 계속 실행
  P-->>S: 애플리케이션 종료
  S-->>C: 종료 상태 보고
```

이는 create/start를 나눈 일반적인 분리 실행의 개념도다. 두 명령이 하나의 장기 실행 runc 프로세스인 것은 아니다. 초기 프로세스가 exec로 프로그램을 교체하며, 이후 애플리케이션이 계속 실행된다.

반대로 foreground 방식의 runc run은 애플리케이션 종료를 기다릴 수 있다. 따라서 "runc는 언제나 즉시 종료한다"도 정확하지 않다. runc 실행 모드

# 5. shim이 계속 살아 있어야 하는 이유

containerd가 업데이트나 장애로 재시작돼도, shim이 실행 태스크의 감독과 입출력 연결을 유지하도록 설계되어 있다. containerd가 복귀하면 shim에 다시 연결한다.

다만 containerd가 내려간 동안 모든 관리 기능이 정상 동작한다는 의미는 아니다. 새 실행이나 관리 API 요청은 영향을 받을 수 있다. 또한 shim 종료, 호스트 재부팅, 서비스 관리자의 강제 종료는 별도 문제다.

shim은 하위 런타임을 연결하는 확장 지점이기도 하다. 런타임에 따라 여러 컨테이너를 한 shim으로 묶을 수 있으므로, shim 수와 컨테이너 수가 항상 같다고 가정하지 않는다. containerd Runtime V2

# 6. 노드에서 확인하기

아래는 조회용 명령이다. 이 문서 작성 과정에서 실제 OCI 인스턴스에서 실행한 결과는 아니다.

```
# Kubernetes가 보고하는 노드 런타임
kubectl get nodes -o custom-columns='NAME:.metadata.name,RUNTIME:.status.nodeInfo.containerRuntimeVersion'

# Linux 노드의 프로세스 확인
ps -eo pid,ppid,comm,args | grep -E '[c]ontainerd|[r]unc|[d]ockerd|[k]ubelet'

# containerd 서비스 상태
systemctl status containerd --no-pager

# crictl이 설치되어 있고 일반적인 containerd 소켓을 사용하는 경우
sudo crictl --runtime-endpoint unix:///run/containerd/containerd.sock ps -a
```

- runc가 목록에 없더라도 컨테이너는 정상 실행 중일 수 있다. 명령이 이미 반환된 경우다.

- containerd-shim-runc-v2는 실행 감독 프로세스를 확인하는 단서다.

- 과거 dockershim은 kubelet 내부 코드였으므로 독립 프로세스 이름으로 보일 것을 기대하면 안 된다.

- 소켓 경로는 배포판·설정에 따라 다를 수 있다.

# 7. 관련 학습 기록과 참고 자료

OCI E5 절약형 Kubernetes 구축: 필요할 때만 실행하고 cloud-init 실패 복구하기

이 문서는 아래 학습 글을 출발점으로 구조를 재정리하고, 버전 및 실행 모드 설명을 공식 자료로 보완했다.

- iximiuz: Journey From Containerization To Orchestration And Beyond

- Kubernetes: Dockershim Removal FAQ

- containerd: Runtime V2

- runc: Terminal and detached mode

- containerd 공식 저장소