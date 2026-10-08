# 조별 저장소 준비 검증 기록

검증일: 2026-10-08, Windows / PowerShell.

## 소스 복사

- 원본: `myeongjundev/flask-board`
- 원본 커밋: `d1801960bd11e074d25b61529a562c90a479617e`
- Git에 등록된 파일 143개를 `flask-board`로 복사했습니다.
- 조별 실행용 `requirements-team.txt`와 루트 협업 문서를 추가했습니다.
- `.env`, 개인키/인증서, 실행 DB, Agent 키, 비공개 백업은 복사하지 않았습니다.
- 원본의 미등록 `templates/attack.php`는 복사 대상에서 제외했습니다.

## 자동 테스트

복사본을 작업 디렉터리로 사용했습니다. 테스트 당시 폴더명은 `_7_board_test`였고, 사용자 요청에 따라 이후 `flask-board`로 변경했습니다. Python은 기존 게시판의 설치된 가상환경(`C:\SKT aleph\flask-board\.venv\Scripts\python.exe`)을 사용했습니다.

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

조장 `myeongjundev`의 [개인 Fork](https://github.com/myeongjundev/flask-board-team)와 [자기소개 PR #1](https://github.com/NoBugs-Aleph/flask-board-team/pull/1)을 확인했습니다. PR 작성자, base `main`, 본인 소개 TXT 하나만 추가한 diff, 충돌 없음(`MERGEABLE`)을 검토한 뒤 Merge했습니다.

- Merge 시각: 2026-10-08 14:52:43 KST.
- Merge 커밋: `73b8b5f3e9a69241cdbe8956506212c6cde01b42`.
- 폴더명 변경 전 PR 경로: `_7_board_test/member_01/introduce.txt`.
- 현재 경로: `flask-board/member_01/introduce.txt`.
- 일반 멤버 초대 전송 확인: chacha1650a, shk12170-dev, whiteclover0542. 세 계정 모두 `direct_member` 초대 대기 상태를 API로 확인했습니다. 아직 수락 완료로 처리하지 않습니다.

폴더를 `flask-board`로 변경한 후 해당 폴더에서 앱 import와 홈페이지 HTTP 200 응답을 다시 확인했습니다. 협업 README와 루트 안내 문서의 로컬 링크도 존재 여부를 검사했습니다. 게시판 코드 내용은 폴더 이동으로 변경하지 않았습니다.

각자의 Fork·자기소개 PR, 조장의 Merge는 실제 GitHub 상태를 확인한 뒤 [제출 체크리스트](SUBMISSION-CHECKLIST.md)에 추가합니다. 이 문서의 로컬 테스트 성공은 팀원 PC의 실행/수집 성공을 증명하지 않습니다.
