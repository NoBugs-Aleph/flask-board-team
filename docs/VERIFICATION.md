# 조별 저장소 준비 검증 기록

검증일: 2026-10-08, Windows / PowerShell.

## 소스 복사

- 원본: `myeongjundev/flask-board`
- 원본 커밋: `d1801960bd11e074d25b61529a562c90a479617e`
- Git에 등록된 파일 143개를 `_7_board_test`로 복사했습니다.
- 조별 실행용 `requirements-team.txt`와 루트 협업 문서를 추가했습니다.
- `.env`, 개인키/인증서, 실행 DB, Agent 키, 비공개 백업은 복사하지 않았습니다.
- 원본의 미등록 `templates/attack.php`는 복사 대상에서 제외했습니다.

## 자동 테스트

복사본 `_7_board_test`를 작업 디렉터리로 사용했습니다. Python은 기존 게시판의 설치된 가상환경(`C:\SKT aleph\flask-board\.venv\Scripts\python.exe`)을 사용했습니다.

```text
python -m unittest discover -s tests -v
Ran 69 tests in 12.541s
OK
```

확인 범위: 인증, 게시글, 권한 제어, 보안 API, 계정 잠금/IP 차단 로직, 인시던트 조회, 보안 신호 및 봇 단위 테스트. 새 PC에서 패키지를 처음 설치하는 과정과 외부 Wazuh/Graylog/n8n 통합은 이 검사 범위에 포함되지 않습니다.

## 실제 HTTP 동작

2026-10-08 14:43 KST에 loopback의 임시 포트로 복사본을 실행했습니다. 기존 DB와 분리된 메모리 SQLite를 사용했고, GELF 전송과 보안 파일 기록을 끄고 테스트 후 서버를 종료했습니다.

| 확인 | 결과 |
| --- | --- |
| 게시판 `/` | HTTP 200 |
| 대시보드 `/dashboard` | HTTP 200 |
| 공공데이터 목록 페이지 `/public-post` | HTTP 200 (외부 API 호출 미검증) |
| 회원가입 | HTTP 201 |
| 로그인 및 토큰 발급 | HTTP 200 |
| 게시글 작성 | HTTP 201 |
| 게시글 조회 | HTTP 200, 작성한 제목 확인 |
| 본인 게시글 수정 | HTTP 200, 변경한 제목 확인 |
| 본인 게시글 삭제 | HTTP 200, 목록에서 제거 확인 |

## GitHub 생성 및 업로드

2026-10-08에 아래 실제 GitHub API 응답과 Push 성공을 확인했습니다.

- 조직 `NoBugs-Aleph`: Free, 표시 이름 NoBugs.
- 조직 소유자 `myeongjundev`: membership `active`, role `admin`.
- 원본 저장소: <https://github.com/NoBugs-Aleph/flask-board-team>, 공개(`private: false`), 기본 브랜치 `main`.
- 게시판 복사본과 협업 문서 최초 커밋 `96460c6`을 `main`에 업로드했습니다.

## 아직 필요한 실제 협업 기록

각자의 Fork·자기소개 PR, 조장의 Merge는 실제 GitHub 상태를 확인한 뒤 [제출 체크리스트](SUBMISSION-CHECKLIST.md)에 추가합니다. 이 문서의 로컬 테스트 성공은 팀원 PC의 실행/수집 성공을 증명하지 않습니다.
