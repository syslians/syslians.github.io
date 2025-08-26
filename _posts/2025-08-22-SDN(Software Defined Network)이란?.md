## SDN 
SDN(Software Defined Network) SDN의 핵심은 **Control Plane(제어 영역)과 **Data Plane(데이터 전송 영역)을 분리하는 것입니다.
- Control Plane -> 네트워크 전체를 바라보고 최적의 경로를 계산하고 정책을 수립하는 두뇌 역할
- Data Plane -> 단순히 패킷을 전달하는 실행부 역할

기존 라우터는 이 두 기능을 하나의 장비 안에서 처리했지만, SDN은 제어 기능을 중앙 집중화하여 네트워크 전반을 통합 관리합니다.

예를 들어, 전통적인 라우터 환경에서는 각 장비가 OSPF같은 라우팅 프로토콜을 통해 개별적으로 최적 경로를 계산합니다. 반면 SDN 
에서는 중앙 컨트롤러가 전체 네트워크 토폴로지를 기준으로 최적 경로를 결정하고, 그 결과를 각 장비에 전달하여 단순히 포워딩 역할만
하게 합니다.

![Bit Operations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FUx31d%2FbtrastS3hRc%2FAAAAAAAAAAAAAAAAAAAAAEeIbfql0QRtfaWGnH6knexPdnLFXMl5B48fpIrwsWkb%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1756652399%26allow_ip%3D%26allow_referer%3D%26signature%3D8uqQ02puZOI%252FAp37GwNSFiBhQac%253D)

![Bit Operations](https://juniper-prod.scene7.com/is/image/junipernetworks/1300x525_what-is-sdn_dgm_29MAR21?network=on&wid=1000&dpr=off)

### SDN 의 장점
1. 운영 효율성
   - 중앙 집중화된 제어로 인해 장비별 개별 설정이 줄어듭니다.
   - 필요에 따라 기능별로 최적화된 장비를 활용할 수 있어 비용 절감 효과가 있습니다.
2. 확장성과 유연성
   - 가상화를 통해 네트워크를 손쉽게 확장하거나 축소할 수 있습니다.
   - 네트워크를 애플리케이션처럼 다룰 수 있어 새로운 서비스 적용이나 보안 정책변경도 유연하게 대응할 수 있습니다.
3. 중앙 집중식 가시성 및 보안성
   - 네트워크 전반을 중앙에서 모니터링 할 수 있어 장애 대응이 빠르고, 트래픽 제어를 통해 보안 위협에도 효과적으로 대처할 수 있습니다.
   - 복잡한 네트워크 토폴리지에 대한 통합적 뷰를 제공
   - 네트워크를 일관되게 관리할 수 있음.

또한 최적의 로드밸런싱이 가능해집니다. 기존에는 라우터와 스위치 등의 장비가 경로를 결정했습니다. 이 장비들은 주로 최단 경로 알고리즘을
통해 패킷을 전달하기 때문에, 네트워크 관리자가 특정 경로를 원하는대로 설정하기엔 어려움이 있었습니다.
수많은 라우터와 스위치들을 static하게 설정하기에는 현실적으로 어려우니까요. 즉, 로드밸런싱이 어려웠습니다. 하지만, SDN은 이런 상황의 변화를
가져왔습니다.

![Bit Operations](https://camo.githubusercontent.com/4f13234e2ec7bba259c578e63453a394a77b9a8e76c8d7646260595853cfedc7/68747470733a2f2f706f737466696c65732e707374617469632e6e65742f4d6a41794e44417a4d6a6c664d5463782f4d4441784e7a45784e6a517a4e6a63334d6a41792e523647584f755f556e62634e76564637375243776e637274724b634a763646334745536e715f4c2d643230672e4a397278527531515364686f44617659355145414864704932324d305574516b734a554a6b5a7073354b59672e504e472f392e706e673f747970653d77373733)

예를 들어보겠습니다. 기존에는 경로 정보가 있을때 U에서 나가는 트래픽을  V와 X에 각각 분산시키고
싶을 경우, 기존의 최단 알고리즘을 통하면 항상 최단의 경로로만 라우팅할 수 있었습니다.

하지만 위 [그림]처럼 SDN을 사용하면 네트워크 관리자는 전체 네트워크의 상태를 실시간으로 파악하고, 트래픽을 V와 X로
균등하게 분산시키는 등 세밀한 조정을 할 수 있습니다. 이를 통해 네트워크의 효율성을 극대화하고, 트래픽 과부하나
장애 발생 시 빠르게 대응할 수 있게 되었습니다.

### SDN의 주요 활용 사례
SDN은 특히 대규모 데이터센터에서 주로 활용됩니다. 데이터센터는 서버와 네트워크 장비가 집중된 공간으로, 대규모 트래픽 관리가 필요하기 때문에
SDN의 중앙 집중적 관리가 큰 이점을 줍니다. 또한, 하이브리드 클라우드 환경에서도 SDN은 강력합니다. 하드웨어 종속성이 적기 때문에 클라우드
소프트웨어와 쉽게 연동할 수 있고, 벤더 종속성을 줄여 다양한 환경을 하나로 통합할 수 있습니다.

### 구글 G-Scale 사례
G-Scale은 구글이 2010년에 시작한 OpenFlow 프로젝트로 전 세계에 흩어져있는 구글 데이터센터 백본(Backbone) 구간을
SDN 기반으로 전환환 프로젝트 입니다.

> 백본(Backbone) 네트워크는 사용자 네트워크와 다르게 한번에 대용량 데이터가 전송됩니다. 
![Bit Operations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FbT2wVS%2FbtraoDoNLHu%2FAAAAAAAAAAAAAAAAAAAAAAKeM77gKNykcSfzmrJF11DtoglXpHUNyECxBFzkkppS%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1756652399%26allow_ip%3D%26allow_referer%3D%26signature%3DDhfIfNWsN7P6zmGfhBwqc7zpVlE%253D)
> 
(참고 : 백본 네트워크 - 데이터센터 간 연결망, 사용자 네트워크 - 사용자와 구글 서비스의 연결망)

> 구글은 자체적으로 네트워크 장비를 제작하고 OpenFlow를 도입하여 SDN을 구현하고 이를 해결하였습니다.

SDN 적용으로 구글은 아래 3가지 부분에서 크게 이득을 볼 수 있었습니다.

1. 인프라 리소스의 최적 활용

구글은 OpenFlow를 기반으로 한 SDN을 적용해 기존에 40~50% 수준에 머물렀던 네트워크 인프라의 활용도를 거의 100% 가까이 끌어올렸습니다. 
기존 네트워크 시스템에서는 다양한 벤더의 장비들이 서로 완벽하게 호환되지 않은 문제로 인해, 전체 네트워크 장비의 효율성이 제한되곤 했었죠.
하지만 구글의 SDN 구현은 이러한 한계를 넘어서, 네트워크 자원을 훨씬 유연하게 관리할 수 있는 방법을 제시할 수 있게 했습니다.

2. WAN 대역의 경로 최적화
**WAN(Wide Area Network)에서의 데이터 전송 속도와 효율성은, 전 세계 사용자들에게 고품질의 서비스를 제공하는 데 핵심적인 요소인데요.
구글은 SDN을 통해 이러한 WAN 대역의 데이터 전송 경로를 최적화하여, 사용자 경험을 크게 향상시킬 수 있었습니다.
이는 전 세계 서비스를 제공하는 구글에게 있어 대단히 중요한 성과였죠.​

3. 네트워크 구축 비용의 절감
구글은 SDN 컨트롤러와 화이트박스 스위치의 조합을 통해, 데이터센터 내 네트워크 구축 비용을 대폭 낮출 수 있었습니다.
화이트박스 스위치는 사용자가 네트워크 장비의 동작방식을 직접 결정할 수 있게 하는 개방형 장비로, 구글은 이를 통해 더 효율적이고 경제적인 네트워크 인프라를 구축할 수 있게 됐습니다.
또한 구축  비용의 절감 뿐 아니라 전반적인 서비스 품질의 향상 효과도 거둘 수 있었습니다.

![Bit Operations](https://camo.githubusercontent.com/694de70facdb05446ae0a7afb1c29f7012025ac712b329c67c86be8eca39fea2/68747470733a2f2f706f737466696c65732e707374617469632e6e65742f4d6a41794e44417a4d6a6c664d6a59302f4d4441784e7a45784e6a63784e7a45774e6a41322e4e71444a4d4d55375a4c6b6279474169614d4e5652457961656d625661724e7375627772656f746d53636f672e634578416e69776554665f676e4d5a4a6c306c72746c764b544e786979504a415f4a445f6c794f45634e6b672e504e472f2545422542382539342545422541312539432545412542372542385f25454325383425414325454225383425413425454325394425424328323331303330295f2831292e706e673f747970653d77373733)

[그림]구글의 다양한 SDN 기술
​
이처럼 구글의 'G-Scale SDN 프로젝트'는 단순히 기술적 성공을 넘어서, 전 세계 통신사와 네트워크 장비 제조사들이 SDN을 도입하고 네트워크 가상화에 뛰어들게 만든 결정적 계기가 되었습니다. 
구글은 여기서 한 발자국 더 나아가 BGP, Espresso, B4, Andromeda, Jupiter 등 다양한 SDN 기술을 적극적으로 활용하고 있습니다.

### SDN Architecture
1. Application Layer -> 라우팅, 보안정책, 로드밸런싱 등 네트워크 제어를 구현하는 소프트웨어 계층
2. Control Layer -> 중앙 집중적으로 네트워크 리소스를 제어하고 관리하는 두뇌 역할
3. Data Plane -> 실제 패킷 전달을 수행하는 장비(화이트박스 스위치 등)

계층 간 통신을 위해 **Southbound Interface(ex: OpenFlow)와 **Northbound interface(API 제공)가 사용됩니다.

![Bit Operations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FbzRIri%2Fbtrav8nirjG%2FAAAAAAAAAAAAAAAAAAAAAITtmNuco65kJjrbTWjTqCVg84wPPUifGOiun5Fs5ESt%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1756652399%26allow_ip%3D%26allow_referer%3D%26signature%3DBD8Vlxqa8nUHfFmkL3zxhK2aejg%253D)
![Bit Operations](https://www.landatel.com/web/image/4116341/image_01_001.png?access_token=ffb7062e-b1d2-43c0-89ad-504954a2b1aa)

출처 : Unveil the Myths About SDN Switch FS Community

### OpenFlow 프로토콜
기존 레거시 장비에서는 Control Plane과 Data Plane이 하나의 장비 내에 같이 탑재되었기 때문에 통신이 필요없었습니다.
하지만 SDN에서는 Control Plane과 Data Plane이 구분되면, SDN 컨트롤러는 Data Plane 계층에 대한 포워딩을 제어
(Match & Action) 하고 정보를 수집하기 위해 SouthBoung 인터페이스를 사용합니다.
이 표준 통신(RPC) 규격 중 하나가 바로 ONF에서 정의하고 있는 OpenFlow Protocol 입니다.

![Bit Operations](https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2FKWBfC%2Fbtrax7n8IXO%2FAAAAAAAAAAAAAAAAAAAAAKHbZyBorDKQV0xAqCZr89hWxIGPLypfHIgoeL_9KOOs%2Fimg.png%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1756652399%26allow_ip%3D%26allow_referer%3D%26signature%3D4lgy8ck2Iq9HR5Igv2nq04UJsTU%253D)

즉, OpenFlow는 이론으로만 가능했던 SDN을 구현하기 위해 처음으로 제정된 최초의 표준 통신 인터페이스입니다.

### 정리
OpenFlow는 OpenFlow 컨트롤러로 구성되며, 흐름(flow) 정보를 제어하여 패킷의 전달 경로 및 방식을 결정합니다.
OpenFlow 스위치 내부에는 패킷 전달 경로와 방식에 대한 정보를 가지고 있는 FlowTable 이라는 것이 존재합니다.
패킷이 발생하면 제일먼저 FlowTabl이 해당 패킷에 대한 정보를 가지고 있는지 확인하고, 없다면 패킷에 대한 정보를 OpenFlow 
Controller에 요청하는 것입니다. OpenFlow Controller 내의 패킷 제어 정보는 외부에서 API를 통해 입력할 수 있습니다.

출처: https://suyeon96.tistory.com/48, 
      https://www.juniper.net/kr/ko/research-topics/what-is-sdn.html,
      https://www.landatel.com/en_US/blog/landatel-s-blog-1/post/what-sdn-are-13?srsltid=AfmBOorLrBFJv9sdLxYM4h102xoDQFs1Oma7ISCCoUZZ2Dod45U1o08H,
      https://blog.naver.com/brainzsquare/223399199778
