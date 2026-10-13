# NoBugs 팀 작업 기록

팀원들이 함께 확인하는 변경·실습·PR 기록입니다. 날짜, 작성자, 작업 폴더, 확인한 결과와 PR 링크를 남깁니다.
각자의 비밀번호·API 키·Agent 등록 키·비공개 작업 로그는 여기에 넣지 않습니다.

## 기록 방법

- 자신의 `member_01`~`member_04` 폴더에서 작업하고 개인 Fork의 브랜치로 PR을 제출합니다.
- 이 문서에는 자기 작업의 확인된 결과를 적습니다. 다른 팀원의 완료 상태는 대신 판단하지 않습니다.
- 예정·진행·완료를 구분하고, PR 상태는 연결된 GitHub 기록으로 확인합니다.
- 설정 예제는 본인 PC 경로를 사용합니다. 다른 사람이 적용할 때는 자신의 경로로 변경합니다.

## 2026-10-13

### 공통 게시판 — 회원 일괄 관리·티켓 종료

작성자: 김명준 / `myeongjundev`. 작업 브랜치: `codex/lesson-updates-20261013`.
PR: [#15](https://github.com/NoBugs-Aleph/flask-board-team/pull/15).
구현 커밋: [818c97f](https://github.com/myeongjundev/flask-board-team/commit/818c97f).
PR의 진행·Merge 상태와 최종 커밋은 연결된 GitHub 기록에서 확인합니다.

- 개인 `flask-board`에 검증한 수업 최신 `1aabb25` 기능을 팀 `flask-board/`에 이식했습니다.
- 회원 서버 검색·페이징·상태 필터·선택 차단/해제/삭제, 티켓 선택·전체 종료와 반응형 화면을 추가했습니다.
- 자기 계정·마지막 관리자·시스템 계정 보호와 회수봇의 관리자 전원 조회를 유지했습니다.
- 팀 전체 pytest 172개, 72 subtests 및 unittest 101개 통과. 임시 DB 브라우저 검증도 통과했습니다.
- 팀 기본 포트 5001·기존 설정·조원 제출 자료를 유지했습니다.
  [사용·검증 기록](flask-board/docs/LESSON-UPDATES-20261013.md).

## 2026-10-12

### member_01 — ② GitHub 협업 실습 2-4 제출

작성자: 김명준 / `myeongjundev` / member_01.

| 항목 | 제출 내용 |
| --- | --- |
| 오늘 미니실습 PNG | Hydra 2장, Gobuster 3장, Nikto 3장, SQLmap 2장, Suricata 3장 — 총 13장 |
| 개인 Agent 설정 예제 | `agent.conf` 1개. 개인·팀의 보안/Suricata 로그 4개와 templates 폴더 2개 |
| 작업 폴더 | [member_01 오늘 실습 폴더](flask-board/member_01/팀실습_1조_김명준_1012/) |
| 협업 경로 | 개인 Fork `myeongjundev/flask-board-team` → 조직 원본 `NoBugs-Aleph/flask-board-team`의 `main` |
| 제출 PR | [PR #11](https://github.com/NoBugs-Aleph/flask-board-team/pull/11), Merged |
| 제출 커밋 | [659dc6e](https://github.com/myeongjundev/flask-board-team/commit/659dc6e) |
| Merge 확인 | 2026-10-12 15:20:04 KST, [582b9a5](https://github.com/NoBugs-Aleph/flask-board-team/commit/582b9a5) |

PR의 작성자와 Fork 소유자가 `myeongjundev`인지, base가 조직 원본 `main`인지,
변경 파일 16개가 본인 제출 자료와 요청된 공유 문서인지 확인한 뒤 Merge했습니다.
설정 문법 검사와 캡처 검토가 통과했고 PR은 충돌 없음(`MERGEABLE`, `CLEAN`) 상태였습니다.

캡처에서 확인한 범위:

- Hydra: Graylog/Wazuh의 로그인 실패 100210, 반복 실패 탐지 100211.
- Gobuster·Nikto: 터미널의 요청 결과, Graylog의 차단 후 재시도, Wazuh의 HTTP 404 경보 100230.
- SQLmap: 테스트 실행 터미널과 당시 대시보드 화면. 이 대시보드 캡처 자체가 SQL Injection 성공을 입증하지는 않습니다.
- Suricata: 전송 스크립트 실행 화면, Graylog/Wazuh의 IDS 100240 및 SQL Injection 탐지 100242.

로그인 비밀번호가 표시된 Hydra 터미널 PNG 1장은 공개 제출에서 제외했고 로컬 원본은 보존했습니다.
나머지 캡처는 이미지 내용을 직접 확인했으며 결과를 수정하거나 새 증거를 만들지 않았습니다.
`agent.conf`는 XML 구조와 Wazuh 4.9.0 문법 검사를 확인했습니다. 이 예제 파일 제출로 다른 팀원 PC의 설치 완료를 뜻하지는 않습니다.

### 공통 게시판 코드 업데이트

- 최신 수업의 404·관리자 API 인증 실패·골드 열람·과잉권한 호스트 로그를 개인·팀 게시판에 이식했습니다.
- 대시보드에 페이징·정렬·심각도 필터를 연결했고 인시던트 갱신 문제 두 가지를 수정했습니다.
- 팀 전체 테스트는 155 passed, 4 subtests passed였습니다. 코드와 검증 상세는 [전체 변경 현황](docs/CHANGE-STATUS-20261012.md)에 있습니다.

| 커밋 | 내용 |
| --- | --- |
| [4b0a4b0](https://github.com/NoBugs-Aleph/flask-board-team/commit/4b0a4b0) | 수업 코드와 대시보드 기능 통합 |
| [b635cf7](https://github.com/NoBugs-Aleph/flask-board-team/commit/b635cf7) | 개인·팀 Wazuh 동시 수집 설정 예시 |
| [541dbd1](https://github.com/NoBugs-Aleph/flask-board-team/commit/541dbd1) | 팀 기본 실행 포트 5001로 분리 |
| [3304e09](https://github.com/NoBugs-Aleph/flask-board-team/commit/3304e09) | 변경 현황과 Suricata 전체 코드 기록 |

### 실행 환경에서 확인할 것

| 구분 | 기본 포트 / 저장소 |
| --- | --- |
| 개인 보안 실습 게시판·n8n 대응 API | 5000 / MySQL `my_new_board_db` |
| 팀 협업 확인 게시판 | 5001 / SQLite `instance/team-board.sqlite3` |

두 게시판을 같은 5000 포트로 실행해 n8n 차단 기록이 SQLite에 저장되던 문제를 확인하고 분리했습니다.
실습 시작 전 서버가 실행 중인지와 API가 사용하는 DB를 확인합니다.

각 PC의 실제 `agent.conf`와 Manager 그룹 설정, Agent의 내려받은 공유 설정을 일치시킵니다.
같은 Suricata 경보를 두 파일에 기록하고 둘 다 수집하면 중복 집계될 수 있습니다.
추가 규칙 예시는 현재 운영의 100230·100231과 번호가 겹칠 수 있어 충돌 확인 후 적용합니다.

다른 조원의 실습 제출·PR 완료 상태는 각자의 PR에서 확인합니다.
