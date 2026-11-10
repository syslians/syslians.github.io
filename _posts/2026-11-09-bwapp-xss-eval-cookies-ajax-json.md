---
layout: post
title: "bWAPP XSS 실습 — Eval·Cookies·AJAX/JSON"
date: 2026-11-09
categories: ["cyber-security", "bWAPP"]
notion_source: "https://app.notion.com/p/bWAPP-XSS-Eval-Cookies-AJAX-JSON-413aa16a5aa481b2bf02ec358bef7440"
---

## 1. 실습 환경과 기록 방법

범위는 **XSS - Reflected (Eval)**, **XSS - Stored (Cookies)**, **XSS - Reflected (AJAX/JSON)** 세 가지로 제한한다. AJAX/XML은 이번 글에서 제외한다.

- 환경: Kali Firefox/Burp → bee-box bWAPP, 기본 주소 [http://192.168.20.205/bWAPP/](http://192.168.20.205/bWAPP/)
- Security Level을 Low로 설정한다. 각 시나리오가 끝나면 같은 입력으로 Medium·High의 응답과 처리 코드를 비교한다.
- 아래는 실행 가이드이며 실제 성공 여부는 아직 기록하지 않았다. 설치본의 코드와 Network 요청을 기준으로 판단한다.
- 캡처 순서: 정상 동작 → 테스트 요청 → 응답 → 실행 화면 → 원인 코드 → 방어 후 재검증.
- Burp 사용 시 Proxy listener와 Firefox 프록시 포트를 맞춘다. 요청이 멈추면 Intercept를 끄거나 Forward한다.

## 2. Reflected (Eval) — URL 입력이 JavaScript로 실행되는 과정

### 정상 요청 확인

메뉴에서 XSS - Reflected (Eval)을 선택한다. 기본 요청의 date 값을 확인한다.

```txt
http://192.168.20.205/bWAPP/xss_eval.php?date=Date()
```

![Notion 이미지 1]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/01-413aa16a.png' | relative_url }})

![Notion 이미지 2]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/02-413aa16a.png' | relative_url }})

Network의 HTML 응답과 xss_eval.php에서 date가 들어가는 위치를 찾는다. 다음과 같은 구조라면 PHP가 입력을 JavaScript 코드 문자열에 삽입하고, 브라우저의 eval이 이를 실행한다.

![Notion 이미지 3]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/03-413aa16a.png' | relative_url }})

```php
eval("document.write(<?php echo xss($_GET["date"])?>)");
```

이 eval은 브라우저의 JavaScript 함수다. PHP eval 실행이나 서버 명령 실행과 구분한다.

### 테스트

주소창에서 date 값을 아래처럼 바꾸어 접속한다.

```txt
http://192.168.20.205/bWAPP/xss_eval.php?date=alert(101)
```

응답에 다음 구조가 만들어지는지 확인한다.

```javascript
eval("document.write(alert(101))");
```

![Notion 이미지 4]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/04-413aa16a.png' | relative_url }})

![Notion 이미지 5]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/05-413aa16a.png' | relative_url }})

alert(101)이 먼저 실행되고 반환값이 document.write에 전달된다. 화면에 undefined가 나타날 수 있다. 이미 JavaScript 표현식 문맥이므로 script 태그를 붙일 필요가 없다.

high level 설정 후

![Notion 이미지 6]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/06-413aa16a.png' | relative_url }})

 xss_eval.php의 코드

![Notion 이미지 7]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/07-413aa16a.png' | relative_url }})

코드는 `date`라는 이름인지 검사하는 것이 아니라, **그 안의 값이 정확히 `Date()`인지 검사한다.**

```txt
if($_GET["date"] != "Date()")
```

따라서 정상·차단 테스트를 한 쌍으로 진행하면 된다.

| 테스트 | 요청 | High 예상 결과 |
| --- | --- | --- |
| 정상 입력 | `?date=Date()` | 검증 통과 → `xss()` 호출 → 날짜 출력 |
| 비허용 입력 | `?date=alert(101)` | 검증 실패 → 함수 호출 전 차단 |
| 다른 날짜 표현식 | `?date=Date.now()` | 날짜 관련 표현식이어도 허용값과 달라 차단 |

high level설정 후 

![Notion 이미지 8]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/08-413aa16a.png' | relative_url }})

## 3. Stored (Cookies) — 쿠키 저장 후 다른 페이지에서 실행

• Stored XSS: 악성 스크립트가 서버에 저장되고, 다른 사용자가 해당 콘텐츠를 조회할 때 실행되는 취약점

![Notion 이미지 9]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/09-413aa16a.png' | relative_url }})

1. 게시글 입력 POST script
2. PHP에서 입력 처리 xss($_POST\[”entry”\])
3. MySQL blog 테이블에 저장 INSERT INTO BLOG
4. 게시글을 다시 읽어 HTML에 출력

XSS - Stored (Cookies), xss_stored_1.php에서 input box에 script를 작성하고 submit을 누른다.

![Notion 이미지 10]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/10-413aa16a.png' | relative_url }})

![Notion 이미지 11]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/11-413aa16a.png' | relative_url }})

### 2. 응답의 Set-Cookie와 chrome browser Storage → Cookies 값 확인

```text
http://192.168.20.205/bWAPP/xss_stored_1.php?genre=<script>alert('STORED_XSS_TEST')</script>
```

문자열 인코딩은 아래처럼 대응된다.

`<script>alert('STORED_XSS_TEST')</script>`

%3Cscript%3E alert%28%27STORED_XSS_TEST%27%29%3C%2Fscript%3E

| 문자열 | URL 인코딩 |
| --- | --- |
| `<` | %3C |
| `>` | %3E |
| `(` | %28 |
| ‘ | %27 |
| ‘ | %27 |
| `<` | %3C |
| `/` | %2F |
| `>` | %3E |

PHP /xss_stored_1.php에서 처리 로직. 

```php
// 68~69행: 사용자 입력 수신
$entry = xss($_POST["entry"]); // entry :<script>alert('STORED_XSS_TEST')</script>
$owner = $_SESSION["login"];  // session: 859a3c8ae39a29b2f77538a87cbc2226

// 81~83행: DB에 저장
$sql = "INSERT INTO blog (date, entry, owner)
        VALUES (now(),'" . $entry . "','" . $owner . "')";

$recordset = $link->query($sql);

// 253행: DB에 저장된 게시글 조회
$sql = "SELECT * FROM blog WHERE owner = '" . $_SESSION["login"] . "'";

// 287행: 조회 결과 순회
while($row = $recordset->fetch_object())
{
    // ...
}

// 338행: 입력값을 HTML에 필터링 없이 그대로 출력. 
// <script>alert('STORED_XSS_TEST')</script>
<td><?php echo $row->entry; ?></td>
```

![Notion 이미지 12]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/12-413aa16a.png' | relative_url }})

### 4. 다른 사용자가 xss_stored_1.php로 접근

사용자가 페이지에 접근하면 db에서 스크립트 그대로의 문자를 읽어들이고 브라우저로 보내서 스크립트가 실행된다.

![Notion 이미지 13]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/13-413aa16a.png' | relative_url }})

### 방어와 정리

High Level(security_level=2)은 입력값을 DB에 저장할 때가 아니라, DB에서 조회해 HTML에 출력할 때 XSS 필터링을 적용한다.

즉, 입력 → URL 디코딩 → DB 저장 → 조회 → HTML 특수문자 인코딩 → 브라우저 출력 순서

## High Level의 실제 코드

### 입력 처리 (48\~52행)

```php
case "2":

    $data = sqli_check_3($link, $data);
    // $data = xss_check_3($data);
    break;
```

왜인지 모르겠으나 xss_check_3는 주석처리가 되어있다. 

```txt
// $data = xss_check_3($data);
```

따라서 High Level에서도 입력 단계에서는 XSS용 `xss_check_3()`가 실행되지 않는다.

### MySQL INSERT (81행)

```php
$sql = "INSERT INTO blog (date, entry, owner)
        VALUES (now(),'" . $entry . "','" . $owner . "')";
```

SQL 처리 과정에서 다른 변환이 없다면 DB에는 이 HTML 문자열이 그대로 저장된다

### DB 조회 후 출력 (290\~301행)

기존에 확인한 `xss_check_3()`가 `htmlspecialchars(..., ENT_QUOTES)`를 사용하는 함수라면 HTML 특수문자를 다음과 같이 변환한다.

| 원본 문자 | HTML 엔티티 |
| --- | --- |
| `<` | `&lt;` |
| `>` | `&gt;` |
| `"` | `&quot;` |
| `'` | `&#039;` |
| `&` | `&amp;` |

## Low와 High의 차이

Low는 xss_check(0)

- db에 저장할때 아래 문자를 그대로 저장한다.
  - `<script>alert(1)</script>`

HTML 출력

html 출력시 entry, 그러니까 저장된 행을 모두 출력한다. 아래처럼 3개가 저장되어 있으면

for문을 돌면서 html에 3번 출력되고, 결과적으로 스크립트도 3번 실행된다. 

- echo $row->entry

| 입력값 |
| --- |
| `<script>alert(1)</script>` |
| `<script>alert(1)</script>` |
| `<script>alert(1)</script>` |

High 레벨에서는 저장하는것은 똑같으나 html 출력하기 전에 인코딩을해서 출력하기 때문에 텍스트로 처리된다.

High (2)

DB 저장

- echo $row->entry

| 입력값 |
| --- |
| `<script>alert(1)</script>` |
| `<script>alert(1)</script>` |
| `<script>alert(1)</script>` |

HTML 응답 소스에 다음과 같이 들어간다

```txt
&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;
```

브라우저는 이를 JavaScript 태그가 아니라 일반 텍스트로 표시한다. 

### HttpOnly의 핵심 기능

HttpOnly가 설정된 쿠키는 **오직 HTTP(또는 HTTPS) 요청을 통해서만 전송된다**

자바스크립트의 document.coockie 코드를 사용해 해당 쿠키에 접근하거나 읽어오는 행위가 **전면 차단된다. **브라우저가 서버와 통신(예: 로그인 상태 유지, 세션 ID 전송 등)할 때 HTTP 요청 헤더에 자동으로 쿠키가 포함되어 전송되는 기능은 정상적으로 작동한다. 

## 4. Reflected (AJAX/JSON) — 비동기 응답에서 DOM까지 추적

### 정상 AJAX 요청 확인

XSS - Reflected (AJAX/JSON), xss_ajax_2-1.php를 선택한다. Firefox Network에서 XHR 요청을 필터링하고 영화명을 입력한다.

- 입력에 따라 발생하는 xss_ajax_2-2.php 요청과 title 파라미터를 확인한다.
- 정상 영화명과 존재하지 않는 표식 XSS303을 비교한다.
- 응답 Content-Type, JSON 구조, 입력값이 반영되는 필드를 확인한다.
- 주소창이 그대로여도 Network에는 비동기 요청이 나타난다.

**입력값을 약 1초(1000ms)마다 서버로 전송**

```javascript
title = encodeURIComponent(document.getElementById("title").value);

xmlHttp.open("GET", "xss_ajax_2-2.php?title=" + title, true);
xmlHttp.send(null);

// 1초 뒤 다음 요청 시작
setTimeout("process()", 1000);
```

입력란의 값이 title 파라미터로 전송된다. encodeURIComponent()는 URL로 전달하기 위한 인코딩이며, XSS 방어 처리는 아니다.

서버 PHP가 다음 중 **하나만 선택해 브라우저에 내려줍니다.**

| 수준 | 브라우저가 받는 코드 | 동작 |
| --- | --- | --- |
| Low·Medium | eval("(" + xmlHttp.responseText + ")") | 응답을 JavaScript 표현식으로 실행 |
| High | JSON.parse(xmlHttp.responseText) | 응답을 JSON 데이터로 파싱 |

### 테스트

영화명 입력란에 다음 값을 넣어 AJAX 요청을 발생시킨다.

```html
<img src=x onerror=alert(document.cookie)>
```

![Notion 이미지 14]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/14-413aa16a.png' | relative_url }})

실제 처리 경로를 순서대로 관찰한다.

1. title이 요청 파라미터로 인코딩되어 전송된다.

```javascript
title = encodeURIComponent(document.getElementById("title").value);

encodeURIComponent(<img src=x onerror=alert(document.cookie)>)
printf(title);  // %3Cscript%3Ealert(document.cookie)%3C%2Fscript%3E 

xmlHttp.open("GET", "xss_ajax_2-2.php?title=" + title, true);
xmlHttp.send(null);

url 파라미터: php?title=%3Cscript%3Ealert(document.cookie)%3C%2Fscript%3E
```

2. **PHP가 파라미터를 읽는다**

서버에서 PHP는 쿼리 값을 URL 디코딩해 제공합니다.

```txt
$title = $_GET["title"];

title = %3Cscript%3Ealert(document.cookie)%3C%2Fscript%3E
```

따라서 $title은 다시 다음 문자열이 된다.

```txt
<img src=x onerror=alert(document.cookie)>
```

**이후 필터링 없이** 응답에 반영한다고 가정하면, 다음 JSON이 반환될 수 있다.

```txt
{
  "movies": [
    {
      "response": "<img src=x onerror=alert(document.cookie)>"
    }
  ]
}
```

3. **브라우저가 응답을 객체로 변환**

```txt
// 1. 응답을 JavaScript 표현식으로 평가
JSONResponse = eval("(" + xmlHttp.responseText + ")");

// 2. response 문자열 추출
result = JSONResponse.movies[0].response;

// 3. 문자열을 HTML로 해석해 삽입
document.getElementById("result").innerHTML = result;
```

`result`에는 원래 문자열이 들어간다

```txt
<img src=x onerror=alert(document.cookie)>
```

4. **`innerHTML`이 문자열을 실제 HTML 요소로 만든다.**

```txt
document.getElementById("result").innerHTML = result;
```

브라우저가 `<img>`를 생성하고 `src="x"`의 이미지 로딩을 시도합니다. 로딩이 실패하면 다음 이벤트 코드가 실행된다

```txt
alert(document.cookie)
```

![Notion 이미지 15]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/15-413aa16a.png' | relative_url }})

그 결과 **현재 페이지에서 JavaScript로 읽을 수 있는 쿠키**가 경고창에 표시된다. HttpOnly 쿠키는 제외

high level에서의 방어

서버 PHP가 보안 수준을 확인

```txt
if($_COOKIE["security_level"] == "2")
```

브라우저에는 아래 코드를 내려준다

```txt
JSONResponse = JSON.parse(xmlHttp.responseText);
result = JSONResponse.movies[0].response;
document.getElementById("result").innerHTML = result;
```

위 응답처럼 태그가 그대로 들어 있다면 이미지 요소가 생성되고, 이미지 로딩 실패 시 alert(document.cookie)를 그대로 문자열로 출력

![Notion 이미지 16]({{ '/assets/images/posts/2026-11-09-bwapp-xss-eval-cookies-ajax-json/16-413aa16a.png' | relative_url }})

### 방어와 재검증

서버에서는 JSON 직렬화 함수로 응답을 만들고 적절한 JSON Content-Type을 사용한다. 클라이언트에서는 eval 대신 JSON.parse를 사용하고 단순 문구는 textContent로 출력한다. 출력 코드는 실제 응답 구조에 맞춘다.

```javascript
var data = JSON.parse(xhr.responseText);
// response 필드 경로는 설치본의 실제 JSON 구조에 맞춘다.
document.getElementById("result").textContent =
    data.movies[0].response;
```

JSON Content-Type과 JSON.parse만으로 innerHTML 위험이 사라지지는 않는다. 같은 테스트 입력이 텍스트로 표시되고 이벤트가 실행되지 않는지 확인한다.

## 5. 결과 비교

| 시나리오 | 입력·저장 위치 | 실행 지점 | 핵심 개선 | 실습 결과 |
| --- | --- | --- | --- | --- |
| Reflected Eval | URL date | JavaScript eval | 입력을 코드로 실행하지 않기 | 직접 기록 |
| Stored Cookies | genre → movie_genre 쿠키 | 쿠키 출력 페이지의 HTML | 허용값 검증·출력 인코딩 | 직접 기록 |
| Reflected AJAX/JSON | XHR title → JSON 응답 | 응답 처리 코드·DOM 출력 | JSON 직렬화·안전한 파싱·textContent | 직접 기록 |

원본: [Notion](https://app.notion.com/p/413aa16a5aa481b2bf02ec358bef7440)
