# 10-14 최신 수업: 차단 IP 검색·페이징·일괄 차단/해제

대상은 팀 저장소의 `flask-board/`입니다. 기능은 개인 `C:\SKT aleph\flask-board`에서 먼저 검증한 뒤 팀 코드에 반영했습니다.
수업 기준은 [Python-Lab-ALeph-T](https://github.com/myeongjundev/Python-Lab-ALeph-T/tree/main)의
[fc5d09b](https://github.com/myeongjundev/Python-Lab-ALeph-T/commit/fc5d09b75116e180287dbb6ba47f59d9e81c9668)입니다.

## 반영한 내용

| 수업 변경 | 팀 반영 |
| --- | --- |
| 차단 IP 목록 검색·페이징 | `/admin`에 "⛔ 차단 IP 목록" 추가. IP·사유·차단자 검색, IP·차단자·차단 시각 머리글 정렬, 10/20/50개씩 보기 |
| 일괄 차단 | 쉼표·공백으로 구분해 여러 IP 입력. 형식 오류·이미 차단·지금 접속한 내 IP는 건너뛰고 결과에 표시 |
| 선택·전체 차단 해제 | 체크한 IP 해제, 행마다 해제 버튼, 검색 조건에 맞는 차단 IP 전부(다른 페이지 포함) 해제 |

10-13 회원 표와 같은 서버 페이징·선택 방식, 1024px 미만 카드 목록, 팀 기본 포트 5001을 유지했습니다.
강사 코드의 공용 파일 `_bulk_select.html`은 가져오지 않았습니다. 대신 이미 있는 `_pager.html`·`_table_sort.html`을 사용합니다.

## 사용 방법

1. 저장소 루트에서 `git pull --ff-only origin main`을 실행합니다.
2. 실행 중인 팀 서버를 종료한 뒤 기존 DB·환경변수로 다시 실행합니다. `--debug` 없이 실행한 서버는 코드 변경이 자동으로 반영되지 않습니다.
3. 관리자 계정으로 `/admin`에 접속하면 회원 목록 아래에 차단 IP 목록이 보입니다.

자기 IP를 차단하면 그 자리에서 `/admin`·로그인 화면이 403이 됩니다. 그래서 서버가 요청자 IP를 `self_skipped`로 제외합니다.
전부 차단(all)은 제공하지 않습니다. 일괄 차단은 IP마다 `admin-console` 감사 이벤트를 남깁니다.

## API

| 호출 | 내용 |
| --- | --- |
| `GET /api/admin/blocked?page=1&per_page=20&q=...&sort=blocked_at\|ip\|blocked_by&order=desc` | 검색과 서버 페이징. page/per_page가 둘 다 없으면 **기존처럼 전체**(최신 차단 먼저) |
| `POST /api/admin/blocked/block` `{ips:[...], reason?}` | 일괄 차단. 응답에 `changed`·`skipped`·`invalid`·`self_skipped` |
| `POST /api/admin/blocked/unblock` `{ips:[...]}` | 고른 IP 차단 해제. 없는 IP는 `not_found` |
| 같은 API `{all:true, q?}` | 검색 조건에 맞는 차단 IP 전부 해제 |

일괄 해제는 `admin-console` 감사 이벤트(decision `allow`) 1건에 해제한 IP를 남깁니다.
같은 IP를 n8n 단건 차단이 동시에 먼저 넣으면 묶음 전체를 되돌리고 409로 다시 시도를 요청합니다.
한 번에 최대 500개를 받습니다. IPv6는 표준 축약형으로 저장합니다(`2001:DB8:0::1` → `2001:db8::1`).
해제는 형식 검사를 하지 않으므로 예전에 잘못 들어간 값도 지울 수 있습니다.
n8n이 쓰는 단건 `POST /api/admin/block`·`/api/admin/unblock`은 바뀌지 않았습니다.

## 검증 기록

2026-10-14 KST, 팀 폴더의 `.venv`로 실행했습니다.

```powershell
$env:GELF_ENABLED = '0'
$env:SECURITY_LOG_PATH = ''
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
git diff --check
```

- 전체 pytest **183 passed, 86 subtests passed**. 기존 짧은 JWT 테스트 키 관련 경고 8건.
- unittest **112개 통과**. 신규 `test_admin_blocked.py` 11개(subtest 14개)는 위 pytest에도 포함됩니다.
- 검증 항목: 무페이징 전체 조회 호환, 페이지 메타, 검색 와일드카드 이스케이프, 형식 오류·이미 차단·자기 IP 제외, 감사 이벤트,
  차단된 IP의 실제 403, 해제 감사 이벤트, 동시 차단 충돌 409, 선택·검색 범위 전체 해제, 잘못된 요청 400, 비로그인 401·일반 회원 403, 화면 정렬 머리글과 서버 허용 목록 일치.
- 브라우저 확인은 임시 SQLite·합성 차단 IP 25건으로 **개인 게시판 소스**에서 했습니다. 팀과 `admin.html`·차단 IP API 코드가 같습니다.
  확인한 동작은 검색, 정렬, 쪽 이동, 선택·행별·검색 결과 전체 해제, 형식 오류·이미 차단·내 IP가 섞인 일괄 차단입니다.
  1440px·375px에서 가로 넘침과 JavaScript 오류가 없었습니다.
- 리뷰 수정 후 **팀 소스**로 다시 확인했습니다. 해제 요청 중 목록을 새로 불러와도 버튼이 잠긴 채 유지되고,
  검색 입력 직후(디바운스 전) 전체 해제가 입력창 검색어 기준으로 동작합니다.

## 적용 범위

이번 변경은 팀 저장소의 코드·문서·테스트입니다. 실행 중인 서버, 실제 DB, Wazuh·Graylog·n8n 설정은 바꾸지 않았습니다.
`member_01`~`member_04` 제출 자료와 기존에 Git에 등록하지 않은 캡처·PHP 파일은 수정하거나 추가하지 않았습니다.
