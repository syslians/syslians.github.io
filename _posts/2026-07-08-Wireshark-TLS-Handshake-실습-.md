---
title: "Wireshark TLS Handshake 실습  "
date: "2026-07-08T11:09:04.182Z"
categories:
  - "network"
  - "tlshandshake"
  - "3-way_handshake"
author: "현제 김_7254"
slug: "wireshark_tls_handshake_실습"
---

# pcap Hex Dump로 따라가는 TLS 1.3 HandshakE

> 분석 파일: `tlshandshake.pcapng`  
> 대표 세션: `192.168.10.50:50381 → 51.79.152.81:443`  
> 관찰 범위: TCP 3-way handshake → TLS ClientHello/ServerHello → TLS 1.3 Key Share → 암호화 전환 → TLS Application Data → ACK/SACK → FIN/RST 종료

!/assets/image_d563c0da-bd33-4233-9990-e96bdebd40a0.png

그림 1. `192.168.10.50:50381 → 51.79.152.81:443` 세션의 전체 흐름이다. TCP 연결 수립 이후 TLS Handshake가 시작되고, ServerHello 이후 대부분의 데이터는 TLS Application Data로 암호화되어 통신되고 있다.

---

## 1. 왜 이 패킷을 분석하는가

TLS Handshake를 설명하는 글은 많지만, 실제 pcap을 열어보면 처음에는 다음 질문들이 자연스럽게 따라온다

- TCP 3-way handshake와 TLS handshake는 어디서 나뉘는가?
- ClientHello는 왜 TCP 패킷 하나에 딱 들어가지 않는가?
- TLS 1.3의 비대칭 키 교환은 패킷의 어느 부분에 보이는가?
- ServerHello 이후 왜 Certificate나 HTTP 내용이 바로 안 보이고 `Application Data`만 보이는가?
- ACK, SACK, FIN, RST는 TLS와 어떤 관계가 있는가?

이 글은 이 질문들을 `tlshandshake.pcapng` 안의 실제 패킷 번호와 hex dump를 기준으로 하나씩 분석해본다.

대표 세션은 다음 4-tuple이다.

```text
Client: 192.168.10.50:50381
Server: 51.79.152.81:443
```

Wireshark에서는 다음 필터로 볼 수 있다.

```wireshark
ip.addr == 192.168.10.50 and ip.addr == 51.79.152.81 and tcp.port == 50381
```

여기서 `50381`은 클라이언트가 임시로 할당받은 ephemeral port이고, `443`은 서버의 HTTPS 포트다. TCP 커널 스택은 이런 연결을 보통 다음 값들의 조합으로 구성한다. 즉, 위 4가지 tuple들이 반드시 모두 맞아야 같은 커넥션이라고 할 수 있다. 

```text
Source IP
Source Port
Destination IP
Destination Port
```

---

## 2. 대표 세션 타임라인

| 단계 | Frame | 방향 | 요약 |
|---|---:|---|---|
| TCP SYN | 125 | Client → Server | 연결 시작 |
| TCP SYN/ACK | 160 | Server → Client | 서버 연결 수락 |
| TCP ACK | 161 | Client → Server | TCP 연결 수립 완료 |
| ClientHello fragment 1 | 162 | Client → Server | TLS ClientHello 첫 번째 TCP 세그먼트, 1460 bytes |
| ClientHello fragment 2 | 163 | Client → Server | TLS ClientHello 두 번째 TCP 세그먼트, 567 bytes |
| ACK | 183 | Server → Client | ClientHello 전체 수신 확인 |
| ServerHello | 184 | Server → Client | ServerHello + CCS + 암호화된 TLS record |
| Client encrypted data | 185 | Client → Server | CCS + 암호화된 TLS record |
| Client Application Data | 186~190 | Client → Server | 암호화된 TLS records |
| Server Application Data | 246, 248, 249 | Server → Client | 암호화된 응답 TLS records |
| Client ACK | 250 | Client → Server | 서버 Application Data 수신 확인 |
| Client FIN | 1001 | Client → Server | 클라이언트 방향 정상 종료 요청 |
| Server Application Data | 1002 | Server → Client | 종료 직전 암호화 데이터 |
| Server FIN | 1003 | Server → Client | 서버 방향 정상 종료 요청 |
| Client RST/ACK | 1004 | Client → Server | 연결 강제 정리 |
| Client RST | 1005, 1013 | Client → Server | 남은 세그먼트에 대한 reset |

> 주의: 아래의 Sequence/Ack 값은 절대 sequence number 기준이다. Wireshark에서 `Relative sequence numbers` 옵션이 켜져 있으면 화면에는 0, 1, 1461처럼 상대값으로 보일 수 있다.

---

## 3. TCP 3-way Handshake: TLS 이전의 연결 수립

TLS는 TCP 위에서 동작한다. 따라서 TLS ClientHello가 나오기 전에 먼저 TCP 연결이 수립되어야 한다.

!/assets/image_d563c0da-bd33-4233-9990-e96bdebd40a0.png

[TCP 3-way handshake]

!/assets/image_d563c0da-bd33-4233-9990-e96bdebd40a0.png

[TCP syn flag bit]

### 3.1 Frame 125: Client → Server SYN

```text
Frame: 125
Direction: 192.168.10.50:50381 → 51.79.152.81:443
TCP Flags: SYN
Seq: 2249127181
Ack: 0
Window: 64240
TCP Payload Length: 0
```

Hex dump 일부:

```text
0000  70 5d cc 5b 83 1a a8 a1 59 24 3e ca 08 00 45 00
0010  00 34 34 e7 40 00 80 06 2f 62 c0 a8 0a 32 33 4f
0020  98 51 c4 cd 01 bb 86 0e f5 0d 00 00 00 00 80 02
0030  fa f0 9b ff 00 00 02 04 05 b4 01 03 03 08 01 01
0040  04 02
```

이 dump를 계층별로 나누면 다음과 같다.

```text
Ethernet
- Destination MAC: 70:5d:cc:5b:83:1a
- Source MAC     : a8:a1:59:24:3e:ca
- Ethertype      : 0x0800, IPv4

IPv4
- Source IP      : 192.168.10.50
- Destination IP : 51.79.152.81
- Protocol       : TCP

TCP
- Source Port      : 50381
- Destination Port : 443
- Flags            : SYN
- Sequence Number  : 2249127181
- Window           : 64240
```

SYN 패킷에는 TCP payload가 없다. 대신 이후 연결의 성능과 복구 방식에 영향을 주는 TCP 옵션들이 들어 있다.

따라서 filtering을 할때에 tcp.payload.len == 0 옵션으로 handshaking 과정을좀 더 명확하게 필터링할 수 있다. 



그림 3. Client의 SYN 패킷에는 MSS, Window Scale, SACK Permitted가 포함되어 있다.

!/assets/image_d563c0da-bd33-4233-9990-e96bdebd40a0.png

Frame 125의 TCP 옵션은 다음과 같다.

```text
MSS            : 1460
Window Scale   : 8
SACK Permitted : yes
```

여기서 MSS 1460은 이 연결에서 한 TCP 세그먼트에 실을 수 있는 TCP payload 크기의 기준이 된다. 이후 ClientHello가 1460 bytes와 567 bytes로 나뉘는 것도 이 값과 연결된다.

---

### 3.2 Frame 160: Server → Client SYN/ACK

```text
Frame: 160
Direction: 51.79.152.81:443 → 192.168.10.50:50381
TCP Flags: SYN, ACK
Seq: 3054624457
Ack: 2249127182
Window: 42340
TCP Payload Length: 0
```

Hex dump 일부:

```text
0000  a8 a1 59 24 3e ca 70 5d cc 5b 83 1a 08 00 45 00
0010  00 34 00 00 40 00 2f 06 b5 49 33 4f 98 51 c0 a8
0020  0a 32 01 bb c4 cd b6 11 de c9 86 0e f5 0e 80 12
0030  a5 64 5c 9e 00 00 02 04 05 b4 01 01 04 02 01 03
0040  03 09
```

핵심은 ACK 값이다.

```text
Client SYN Seq = 2249127181
Server Ack     = 2249127182
```

SYN은 데이터 payload가 없지만 sequence number를 1 소비한다. 그래서 서버는 `Client SYN Seq + 1`을 ACK로 돌려준다.

서버의 TCP 옵션은 다음과 같다.

```text
MSS            : 1460
Window Scale   : 9
SACK Permitted : yes
```

Client와 Server의 Window Scale 값은 다르다. Client는 8, Server는 9를 광고했다. TCP window scaling은 양방향 수신 윈도우 확장에 대해 독립적으로 적용된다.

---

### 3.3 Frame 161: Client → Server ACK

```text
Frame: 161
Direction: 192.168.10.50:50381 → 51.79.152.81:443
TCP Flags: ACK
Seq: 2249127182
Ack: 3054624458
TCP Payload Length: 0
```

Hex dump 일부:

```text
0000  70 5d cc 5b 83 1a a8 a1 59 24 3e ca 08 00 45 00
0010  00 28 34 e8 40 00 80 06 2f 6d c0 a8 0a 32 33 4f
0020  98 51 c4 cd 01 bb 86 0e f5 0e b6 11 de ca 50 10
0030  04 02 3e d5 00 00
```

서버 SYN에 대한 ACK 값은 다음과 같이 계산된다.

```text
Server SYN Seq = 3054624457
Client Ack     = 3054624458
```

이 시점에서 TCP 연결은 수립되었다. 그러나 아직 TLS는 시작되지 않았다. TLS는 이 TCP 연결 위에서 byte stream으로 흘러간다.

---

## 4. TLS ClientHello: 암호화 협상의 시작

TCP 연결이 수립된 뒤 클라이언트는 TLS ClientHello를 보낸다. 이 패킷에서 클라이언트는 자신이 지원하는 TLS 버전, cipher suite, SNI, ALPN, key share 등을 제안한다.

### 4.1 ClientHello는 하나의 TCP 세그먼트가 아니다.

!/assets/image_d563c0da-bd33-4233-9990-e96bdebd40a0.png

그림 4. ClientHello는 TLS record 하나지만, TCP에서는 Frame 162와 Frame 163 두 세그먼트로 나뉘어 전송된다.

Frame 162와 163의 TCP payload 길이는 다음과 같다.

```text
Frame 162 TCP Payload Length = 1460 bytes
Frame 163 TCP Payload Length = 567 bytes

Total = 1460 + 567 = 2027 bytes
```

Frame 162의 TLS record header는 다음과 같이 시작한다.

```text
16 03 01 07 e6 01 00 07 e2 03 03 ...
```

이를 해석하면 다음과 같다.

```text
16       = TLS Content Type: Handshake
03 01    = Legacy TLS record version
07 e6    = TLS record length: 2022 bytes
01       = Handshake Type: ClientHello
00 07 e2 = Handshake length: 2018 bytes
03 03    = ClientHello legacy_version
```

TLS record 전체 크기는 다음과 같다.

```text
TLS record header  = 5 bytes
TLS record body    = 2022 bytes
Total              = 2027 bytes
```

이 값은 TCP payload 합계와 정확히 일치한다.

```text
Frame 162 1460 bytes + Frame 163 567 bytes = 2027 bytes
```

여기서 중요한 점은 이것이다.

```text
TLS는 ClientHello라는 하나의 handshake message를 만들었지만,
TCP는 그것을 단순한 byte stream으로 보고 MSS에 맞게 여러 segment로 나누어 전송한다.
```

---

### 4.2 Frame 162: ClientHello 시작 hex dump

Frame 162의 Packet Bytes 영역이다. TLS record header와 ClientHello handshake header가 시작된다.

Frame 162 payload 시작 부분:

```text
0000  16 03 01 07 e6 01 00 07 e2 03 03 5e 90 43 7b 04
0010  f6 5b d4 18 c0 55 b8 db b0 40 2c ef 57 3d fe 96
0020  5f 27 0c 0f de 9b 13 be 52 c7 4f 20 4b 3a cb ce
0030  ec 68 ed e0 79 a0 8c 35 71 12 f7 57 d4 c2 d5 b9
```

TLS 1.3에서도 `03 01`, `03 03` 같은 legacy version 값이 보인다. 따라서 이 값만 보고 "TLS 1.0이다" 또는 "TLS 1.2다"라고 단정하면 안 된다. 실제 TLS 1.3 사용 여부는 `supported_versions` extension과 ServerHello의 선택 결과를 봐야 한다.

---

### 4.3 ClientHello 내부 필드: SNI, ALPN, Cipher Suites, Key Share

ClientHello 안에서 확인할 수 있는 대표 필드는 다음과 같다.

```text
SNI: onetag-sys.com
ALPN: h2, http/1.1
TLS 1.3 Cipher Suites:
- 0x1301 TLS_AES_128_GCM_SHA256
- 0x1302 TLS_AES_256_GCM_SHA384
- 0x1303 TLS_CHACHA20_POLY1305_SHA256
Supported Versions:
- TLS 1.3
- TLS 1.2
Key Share extension: 존재
```

#### SNI extension

ClientHello의 SNI 부분 hex는 다음과 같다.

```text
00 00 00 13 00 11 00 00 0e 6f 6e 65 74 61 67 2d 73 79 73 2e 63 6f 6d
```

해석:

```text
00 00 = Extension Type: server_name
00 13 = Extension Length: 19
00 11 = Server Name List Length: 17
00    = Name Type: host_name
00 0e = Hostname Length: 14
6f 6e 65 74 61 67 2d 73 79 73 2e 63 6f 6d = onetag-sys.com
```

즉 클라이언트는 TLS Handshake 초기에 서버에게 "나는 `onetag-sys.com`에 접속하려고 한다"는 정보를 전달한다. HTTPS 서버는 하나의 IP에서 여러 도메인을 서비스할 수 있기 때문에, SNI는 서버가 어떤 인증서와 설정을 선택할지 결정하는 데 중요하다.

#### ALPN extension

ALPN 부분 hex:

```text
00 10 00 0e 00 0c 02 68 32 08 68 74 74 70 2f 31 2e 31
```

해석:

```text
00 10 = Extension Type: ALPN
00 0e = Extension Length: 14
00 0c = ALPN Protocol Name List Length: 12
02 68 32 = "h2"
08 68 74 74 70 2f 31 2e 31 = "http/1.1"
```

즉 클라이언트는 HTTP/2인 `h2`와 HTTP/1.1을 모두 지원한다고 제안한다.

#### Key Share extension

ClientHello에는 `key_share` extension도 포함되어 있다.

```text
Extension Type: 0x0033 key_share
```

TLS 1.3에서 key share는 매우 중요하다. 클라이언트는 자신의 ECDHE public key material을 ClientHello에 담아 보낸다. 서버는 이 중 하나의 그룹을 선택하고 ServerHello에서 자신의 key share를 돌려준다.

---

## 5. ServerHello: 서버의 선택

ClientHello는 제안서다. ServerHello는 그 제안에 대한 서버의 선택이다.

!/assets/image_d563c0da-bd33-4233-9990-e96bdebd40a0.png

!/assets/image_d563c0da-bd33-4233-9990-e96bdebd40a0.png

그림 6. Frame 184에서 ServerHello, ChangeCipherSpec, 암호화된 TLS record가 함께 보인다.

### 5.1 Frame 184 요약

```text
Frame: 184
Direction: 51.79.152.81:443 → 192.168.10.50:50381
TCP Flags: PSH, ACK
Seq: 3054624458
Ack: 2249129209
Window: 83
TCP Payload Length: 238
```

Frame 184 payload 시작:

```text
0000  16 03 03 00 80 02 00 00 7c 03 03 61 69 d9 fc d7
0010  6c 89 e1 51 cf cf 73 e5 23 c1 72 64 42 ff 33 97
0020  5b 79 9a bb e2 77 14 ac 73 0d 21 20 4b 3a cb ce
0030  ec 68 ed e0 79 a0 8c 35 71 12 f7 57 d4 c2 d5 b9
...
0080  ca 58 13 01 00 00 34 00 2b 00 02 03 04 00 33 00
0090  24 00 1d 00 20 97 4c 23 00 a1 05 7a 92 12 43 a6
00a0  e2 10 1f c2 e9 e4 ba a2 f1 1a bf 9c 75 34 9c 31
00b0  24 6e 7f 30 0c
```

TLS record header:

```text
16 03 03 00 80
```

해석:

```text
16    = Handshake record
03 03 = Legacy record version
00 80 = Record length 128
```

Handshake header:

```text
02 00 00 7c
```

해석:

```text
02       = ServerHello
00 00 7c = Handshake length 124
```

서버가 선택한 cipher suite는 다음 부분에서 확인된다.

```text
13 01
```

해석:

```text
0x1301 = TLS_AES_128_GCM_SHA256
```

Supported Versions extension:

```text
00 2b 00 02 03 04
```

해석:

```text
00 2b = Extension Type: supported_versions
00 02 = Length: 2
03 04 = Selected Version: TLS 1.3
```

Key Share extension:

```text
00 33 00 24 00 1d 00 20 ...
```

해석:

```text
00 33 = Extension Type: key_share
00 24 = Extension Length: 36
00 1d = Group: x25519
00 20 = Key Exchange Length: 32 bytes
```

따라서 이 ServerHello에서 서버는 다음을 선택했다.

```text
TLS Version  : TLS 1.3
Cipher Suite : TLS_AES_128_GCM_SHA256
Key Exchange : X25519 key share
```

---

## 6. TLS 1.3의 키 교환: 비대칭키와 대칭키의 역할 구분

여기서 자주 헷갈리는 부분이 있다.

> "비대칭키로 데이터를 암호화해서 보내는 것 아닌가?"

TLS 1.3에서는 일반적인 애플리케이션 데이터를 비대칭키로 직접 암호화하지 않는다. 비대칭 키 교환은 shared secret을 만들기 위한 과정이고, 실제 데이터 암호화는 그 secret에서 파생된 대칭키로 수행된다.

흐름을 단순화하면 다음과 같다.

```text
ClientHello
- client key_share public key 전송

ServerHello
- server key_share public key 전송

Client
- client private key + server public key
- shared secret 계산

Server
- server private key + client public key
- 같은 shared secret 계산

HKDF 기반 key schedule
- handshake traffic secret
- application traffic secret
- AEAD encryption key 파생

Application Data
- 대칭키 기반으로 암호화
```

즉 이 패킷에서 "비대칭 키 교환이 보이는 위치"는 ClientHello와 ServerHello의 `key_share` extension이다. 하지만 이후 실제 TLS Application Data는 `TLS_AES_128_GCM_SHA256` 같은 대칭키 기반 AEAD cipher suite로 암호화된다.

---

## 7. 암호화 전환: ChangeCipherSpec와 Application Data

Frame 184의 ServerHello 뒤에는 다음 TLS records가 이어진다.

```text
14 03 03 00 01 01
17 03 03 00 24 ...
17 03 03 00 35 ...
```

해석:

```text
14 = ChangeCipherSpec
17 = Application Data
```

TLS 1.3에서는 호환성 목적의 ChangeCipherSpec가 보일 수 있고, 이후 Certificate, CertificateVerify, Finished 같은 후속 handshake 메시지가 암호화되어 Application Data record type으로 보인다. 복호화 키가 없는 상태의 Wireshark에서는 내부 내용을 볼 수 없고, 단지 `Application Data`로만 표시된다.

---

### 7.1 Frame 185: Client 측 암호화 전환

```text
Frame: 185
Direction: 192.168.10.50:50381 → 51.79.152.81:443
TCP Flags: PSH, ACK
TCP Payload Length: 64
TLS Records:
- ChangeCipherSpec, len=1
- Application Data, len=53
```

Hex dump 일부:

```text
0000  14 03 03 00 01 01 17 03 03 00 35 5e e1 5e 54 23
0010  da 13 65 85 94 8d cb e4 a9 a1 03 68 58 09 4e 07
0020  a0 84 f0 5e b5 8d 58 55 6f d5 46 ac 41 97 f3 00
0030  94 44 fd 2e 4b 4b d9 0e 18 72 39 f7 5f 97 71 17
```

여기서 `14 03 03 00 01 01`은 ChangeCipherSpec record이고, 그 뒤의 `17 03 03 00 35 ...`는 암호화된 TLS record다.

---

## 8. 암호화 이후: TLS Application Data만 보이는 이유

!/assets/image_d563c0da-bd33-4233-9990-e96bdebd40a0.png

그림 7. Frame 187은 TLS Application Data record다. 내부 HTTP/2 frame 또는 HTTP 요청 내용은 복호화 키 없이는 보이지 않는다.

!/assets/image_d563c0da-bd33-4233-9990-e96bdebd40a0.png

내부 페이로드를 확인해보면, 암호화 되어 있는것을 확인할 수 있다.

### Frame 187 예시

```text
Frame: 187
Direction: 192.168.10.50:50381 → 51.79.152.81:443
TCP Flags: PSH, ACK
Seq: 2249129365
Ack: 3054624696
TCP Payload Length: 522
```

TLS record 시작:

```text
17 03 03 02 05 ...
```

해석:

```text
17    = TLS Content Type: Application Data
03 03 = Legacy record version
02 05 = Encrypted record length 517 bytes
```

즉 TCP payload 522 bytes 중 TLS record header 5 bytes를 제외한 517 bytes가 암호화된 record body다.

이후 Client는 여러 개의 Application Data record를 이어서 보낸다.

| Frame | 방향 | TCP Payload Length | TLS record 시작 |
|---:|---|---:|---|
| 186 | Client → Server | 92 | `17 03 03 00 57` |
| 187 | Client → Server | 522 | `17 03 03 02 05` |
| 188 | Client → Server | 185 | `17 03 03 00 b4` |
| 189 | Client → Server | 244 | `17 03 03 00 ef` |
| 190 | Client → Server | 196 | `17 03 03 00 bf` |

서버도 암호화된 응답을 보낸다.

| Frame | 방향 | TCP Payload Length | TLS record 시작 |
|---:|---|---:|---|
| 246 | Server → Client | 97 | `17 03 03 00 5c` |
| 248 | Server → Client | 285 | `17 03 03 01 18` |
| 249 | Server → Client | 246 | `17 03 03 00 f1` |

여기서 TCP는 TLS 내부 구조를 이해하지 않는다. TCP에게 이 데이터는 단순한 byte stream이다. TLS record가 HTTP/2를 담고 있든, 암호화된 handshake 메시지를 담고 있든, TCP는 sequence number, ACK, window만 관리한다.

---

## 9. TCP ACK 흐름: TLS record를 byte stream으로 확인한다

ClientHello 구간을 계산해보자.

```text
Frame 162 Seq = 2249127182
Frame 162 Len = 1460

Frame 163 Seq = 2249128642
Frame 163 Len = 567
```

Frame 163의 시작 sequence number는 Frame 162의 끝과 일치한다. MTU 사이즈 1500 상한에 걸려서

두 개의 패킷으로 세그멘테이션 된것이다.

!/assets/image_d563c0da-bd33-4233-9990-e96bdebd40a0.png

```text
2249127182 + 1460 = 2249128642
```

두 세그먼트 전체 길이는 2027 bytes다.

```text
1460 + 567 = 2027
```

따라서 서버가 ClientHello 전체를 받았다면 다음에 기대하는 바이트는 다음과 같다.

```text
2249127182 + 2027 = 2249129209
```

Frame 183에서 서버는 ACK를 이렇게 보낸다.

```text
Frame: 183
Direction: 51.79.152.81:443 → 192.168.10.50:50381
TCP Flags: ACK
Seq: 3054624458
Ack: 2249129209
TCP Payload Length: 0
```

즉 ACK 번호는 "마지막으로 받은 바이트 번호"가 아니라 "다음에 받고 싶은 바이트 번호"다. SYN

> 캡처 파일의 짧은 ACK/FIN 프레임은 Ethernet 최소 프레임 크기를 맞추기 위한 padding이 Packet Bytes 하단에 `00`으로 보일 수 있다. TCP payload 여부는 Packet Bytes의 남은 바이트가 아니라 IPv4 Total Length와 TCP Header Length를 기준으로 판단해야 한다. Frame 183, 245, 261, 1003, 1012는 IP Total Length 기준으로 TCP payload가 0이다.

---

!/assets/image_d563c0da-bd33-4233-9990-e96bdebd40a0.png

## 10. SACK: 메인 세션에서는 협상, 다른 세션에서 실제 block 확인

메인 세션의 SYN/SYN-ACK에서는 SACK 사용 가능 여부가 협상된다.

```text
Frame 125: SACK Permitted
Frame 160: SACK Permitted
```

이는 손실이나 out-of-order가 발생했을 때 SACK option을 사용할 수 있다는 뜻이다. 다만 이 대표 세션에서는 SACK block이 핵심적으로 등장하지 않는다. 

SACK은 cumulative ACK를 대체하는 것이 아니다. ACK는 여전히 "연속적으로 받은 마지막 지점 다음"만 가리킨다. 대신 SACK block은 "앞쪽 gap 때문에 ACK는 못 올리지만, 뒤쪽 이 구간은 받았다"는 정보를 추가로 알려준다

기존 TCP의 cumulative ACK만으로는 중간 세그먼트가 손실되었을 때 그 뒤쪽 세그먼트들이 수신측에 도착했는지 송신측이 알기 어렵다. 그래서 송신측은 손실 지점 이후의 데이터를 보수적으로 재전송하거나, 여러 손실을 한 번에 복구하지 못하고 RTT마다 하나씩 복구해야 할 수 있다. SACK은 수신측이 out-of-order로 받은 byte range를 TCP option으로 알려주기 때문에, 송신측은 이미 도착한 구간은 재전송하지 않고 실제로 빠진 hole만 선택적으로 재전송할 수 있다.

예를 들어,  예를 들어 frame 162가 유실되고 frame 163만 도착했다고 하자.

Sender                                                                           Receiver

Frame 162: SEQ=X, LEN=1460  ─────X 유실

Frame 163: SEQ=X+1460,LEN=567 ───────────▶

SACK이 있으면 수신측은 cumulative ACK에 추가 정보를 붙인다.

Segment 2가 유실되고 Segment 3, 4, 5가 도착한 상황

[1000~1099] [1100~1199] [1200~1299] [1300~1399] [1400~1499]
받음                 유실              받음                 받음               받음

기본 ACK는 여전히 ACK=1100 이다. 1100부터 아직 못 받았기 때문이다.

tcp는 통신에서 순서, 신뢰를 가장 중요시하기 때문에 패킷이 뒤바뀌지 않게 항상 정렬한 다음 프로세스에게 전달한다. SACK이 없다면 같은 ack를 계속 전달한다. 즉, duplicated ack가 발생하고, 송신측에서는 이 신호를 네트워크 혼잡신호로 판단하고 전부 재전송하거나,

ACK=1100
SACK=[1200,1500)

의미는 나는 1100부터 기다리고 있어. 그런데 1200~1499는 이미 받았어.

이걸 받은 송신측은 1100~1199만 다시 보내면 된다는것을 정확히 알 수 있다. 
1200~1499는 다시 보낼 필요 없음

그림으로 보자면 SACK이 없는 환경에서는 아래와 같다면,

송신측                              수신측

Seg1 1000~1099  ───────────────▶  받음
Seg2 1100~1199  ─────X 유실
Seg3 1200~1299  ───────────────▶  out-of-order 보관
Seg4 1300~1399  ───────────────▶  out-of-order 보관
Seg5 1400~1499  ───────────────▶  out-of-order 보관

◀──────────────  ACK=1100

◀──────────────  ACK=1100

◀──────────────  ACK=1100

송신측은1100부터 문제가 있다는것은 알 수 있다. 하지만, 1200 이후 패킷들은 정상적으로 도착했는지 알 수 없다. 일일히 서버에 물어보는것말고는 방법이 없었기 때문에, duplicated ack 기준으로 보낸 패킷들을 전부 다시 보내는 식으로 밖에 할 수 밖에 없었다. 여러 패킷 손실에서는 이 차이가 더 두드러진다.

SACK의 진짜 효과는 한 윈도우 안에서 여러 개가 손실되었을 때 크게 나타난다. 예를 들어서 아래와 같이

seq1(ok) seg2(miss) seg3(miss) seg4(ok) seg5(miss) seg6(miss)

여러 패킷들이 중간중간에 한 윈도우 내에서 손실되는 경우, SACK이 없다면 ACK=Seg2 시작점에서 계속 기다리고 있는다. 하지만 SACK이 있다면, 정확히 어떤 패킷이 손실되었는지 정확히 client에 재요청할 수 있다.


Linux TCP 수신측은 이런 out-of-order segment를 `out_of_order_queue`에 보관하고, gap이 채워지면 sequence number 순서대로 receive queue로 이동시킨다. 즉 Wireshark에서는 RB-tree 내부 자료구조가 보이지 않지만, `Duplicate ACK`, `SACK`, `Out-of-Order`, `Retransmission` 같은 흔적으로 내부 동작을 추론할 수 있다.

---

### 송신측 내부에서는 SACK scoreboard를 만든다

SACK을 받은 송신측은 내부적으로 이런 식으로 상태를 만든다.

```
송신 큐:

1000      1100      1200      1300      1400      1500
|---------|---------|---------|---------|---------|
  ACKed     missing    SACKed    SACKed    SACKed
```

이런 기록을 흔히 SACK scoreboard라고 한다.

송신측은 scoreboard를 보고 SACKed 블록은 재전송하지 않고, 
missing hole만 재전송하게 된다.

## 11. FIN 기반 정상 종료와 RST

TLS Application Data 교환 이후 연결은 종료 단계로 들어간다.

!/assets/image_d563c0da-bd33-4233-9990-e96bdebd40a0.png

그림 10. Frame 1001에서 Client가 FIN/ACK를 보내고, Frame 1003에서 Server도 FIN/ACK를 보낸다. 이후 Client가 RST/ACK와 RST를 보낸다.

### 11.1 Frame 1001: Client FIN/ACK

```text
Frame: 1001
Direction: 192.168.10.50:50381 → 51.79.152.81:443
TCP Flags: FIN, ACK
Seq: 2249130543
Ack: 3054625363
TCP Payload Length: 0
```

Hex dump 일부:

```text
0000  70 5d cc 5b 83 1a a8 a1 59 24 3e ca 08 00 45 00
0010  00 28 34 f3 40 00 80 06 2f 62 c0 a8 0a 32 33 4f
0020  98 51 c4 cd 01 bb 86 0f 02 2f b6 11 e2 53 50 11
0030  03 ff 2e 2d 00 00
```

FIN은 한 방향의 데이터 송신 종료를 의미한다. FIN도 SYN처럼 sequence number를 1 소비한다.

---

### 11.2 Frame 1002: Server Application Data

Client가 FIN을 보낸 뒤에도 Server가 암호화된 TLS record를 하나 더 보낸다.

```text
Frame: 1002
Direction: 51.79.152.81:443 → 192.168.10.50:50381
TCP Flags: PSH, ACK
Seq: 3054625363
Ack: 2249130543
TCP Payload Length: 24
TLS record 시작: 17 03 03 00 13
```

이 부분은 TCP half-close 관점에서 볼 수 있다. Client가 "나는 더 보낼 데이터가 없다"고 FIN을 보냈더라도, 서버 방향 데이터가 즉시 끝났다는 뜻은 아니다. 서버는 자신의 방향으로 남은 데이터를 보낼 수 있다.

---

### 11.3 Frame 1003: Server FIN/ACK

```text
Frame: 1003
Direction: 51.79.152.81:443 → 192.168.10.50:50381
TCP Flags: FIN, ACK
Seq: 3054625387
Ack: 2249130543
TCP Payload Length: 0
```

Hex dump 일부:

```text
0000  a8 a1 59 24 3e ca 70 5d cc 5b 83 1a 08 00 45 00
0010  00 28 a9 e7 40 00 2f 06 0b 6e 33 4f 98 51 c0 a8
0020  0a 32 01 bb c4 cd b6 11 e2 6b 86 0f 02 2f 50 11
0030  00 53 31 c1 00 00
```

서버도 FIN을 보내며 서버 방향 송신 종료를 알린다.

---

### 11.4 Frame 1004 이후: Client RST/ACK, RST

```text
Frame: 1004
Direction: 192.168.10.50:50381 → 51.79.152.81:443
TCP Flags: RST, ACK
Seq: 2249130544
Ack: 3054625387
Window: 0
TCP Payload Length: 0
```

Hex dump 일부:

```text
0000  70 5d cc 5b 83 1a a8 a1 59 24 3e ca 08 00 45 00
0010  00 28 34 f4 40 00 80 06 2f 61 c0 a8 0a 32 33 4f
0020  98 51 c4 cd 01 bb 86 0f 02 30 b6 11 e2 6b 50 14
0030  00 00 32 10 00 00
```

FIN은 정상 종료 절차이고, RST는 연결 상태를 즉시 폐기하라는 신호다. 이 세션에서는 FIN 교환 이후 Client 쪽에서 RST/ACK와 RST가 추가로 보인다.

이런 RST는 반드시 애플리케이션 장애를 의미하지는 않는다. 종료 타이밍, FIN과의 순서, 남은 세그먼트 도착 여부, 소켓 상태 정리 시점에 따라 나타날 수 있다. 따라서 RST를 해석할 때는 다음을 함께 봐야 한다.

```text
1. 누가 RST를 보냈는가?
2. RST 직전에 FIN이 있었는가?
3. RST 직전에 TLS Alert 또는 Application Data가 있었는가?
4. 상대방이 이미 FIN을 보냈는가?
5. ACK 번호가 어떤 데이터를 확인하고 있는가?
```

이 세션에서는 Client가 먼저 FIN을 보내고, Server가 남은 Application Data와 FIN을 보낸 뒤, Client가 RST로 연결을 정리하는 흐름이다.

---

## 12. 전체 흐름 요약 다이어그램

```text
Client                                      Server
192.168.10.50:50381                         51.79.152.81:443
    |                                             |
    | SYN                                         |  Frame 125
    |-------------------------------------------->|
    | SYN, ACK                                    |  Frame 160
    |<--------------------------------------------|
    | ACK                                         |  Frame 161
    |-------------------------------------------->|
    | ClientHello fragment #1                     |  Frame 162, 1460 bytes
    |-------------------------------------------->|
    | ClientHello fragment #2                     |  Frame 163, 567 bytes
    |-------------------------------------------->|
    | ACK                                         |  Frame 183
    |<--------------------------------------------|
    | ServerHello + CCS + Encrypted Data          |  Frame 184
    |<--------------------------------------------|
    | CCS + Encrypted Data                        |  Frame 185
    |-------------------------------------------->|
    | TLS Application Data                        |  Frame 186~190
    |-------------------------------------------->|
    | TLS Application Data                        |  Frame 246, 248, 249
    |<--------------------------------------------|
    | ACK                                         |  Frame 250
    |-------------------------------------------->|
    | FIN, ACK                                    |  Frame 1001
    |-------------------------------------------->|
    | Encrypted TLS Data                          |  Frame 1002
    |<--------------------------------------------|
    | FIN, ACK                                    |  Frame 1003
    |<--------------------------------------------|
    | RST, ACK                                    |  Frame 1004
    |-------------------------------------------->|
```

---

## 13. Wireshark 필터 모음

대표 세션만 보기:

```wireshark
ip.addr == 192.168.10.50 and ip.addr == 51.79.152.81 and tcp.port == 50381
```

TCP 3-way handshake:

```wireshark
frame.number == 125 or frame.number == 160 or frame.number == 161
```

SYN 계열:

```wireshark
tcp.flags.syn == 1
```

ClientHello:

```wireshark
tls.handshake.type == 1
```

ServerHello:

```wireshark
tls.handshake.type == 2
```

TLS Application Data:

```wireshark
tls.record.content_type == 23
```

FIN:

```wireshark
tcp.flags.fin == 1
```

RST:

```wireshark
tcp.flags.reset == 1
```

SACK:

```wireshark
tcp.options.sack
```

재전송:

```wireshark
tcp.analysis.retransmission
```

Duplicate ACK:

```wireshark
tcp.analysis.duplicate_ack
```

---