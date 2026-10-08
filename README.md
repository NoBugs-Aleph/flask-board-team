# NoBugs — Flask 게시판 조별 협업 실습

기존 Flask 게시판을 `_7_board_test`에 복사하고, 각자가 Fork에서 자기소개 파일을 작성한 뒤 Pull Request로 통합하는 실습입니다.

조직: [NoBugs](https://github.com/NoBugs-Aleph) · 조별 원본 저장소: [NoBugs-Aleph/flask-board-team](https://github.com/NoBugs-Aleph/flask-board-team)

GitHub Free의 공개 저장소입니다. 조장 `myeongjundev`가 조직을 관리합니다. 조원은 개인 Fork에서 작업한 뒤 이 저장소의 `main`으로 PR을 제출합니다.

## 조원과 작업 폴더

| 구분 | GitHub 사용자 | 본인 작업 폴더 |
| --- | --- | --- |
| 조장 | myeongjundev | `_7_board_test/member_01` |
| 조원 | chacha1650a | `_7_board_test/member_02` |
| 조원 | shk12170-dev | `_7_board_test/member_03` |
| 조원 | whiteclover0542 | `_7_board_test/member_04` |

각자 자신의 폴더에 `introduce.txt`를 만들어 제출합니다. 다른 조원의 폴더와 게시판 소스는 이번 자기소개 PR에서 수정하지 않습니다. 팀원 폴더는 해당 조원의 PR로 처음 생성됩니다.

## 먼저 읽을 문서

- [Fork → Clone → 자기소개 → PR → Merge 길라잡이](docs/COLLABORATION-GUIDE.md)
- [자기소개 양식](docs/INTRODUCE-TEMPLATE.txt)
- [최종 제출 체크리스트](docs/SUBMISSION-CHECKLIST.md)
- [기존 게시판 전체 README](./_7_board_test/README.md)
- [팀원 PC Wazuh 수집 문제 검증 가이드](./_7_board_test/docs/WAZUH-LLM-VERIFICATION-GUIDE.md)

## 게시판 빠른 실행 — 협업 기능 확인용

Windows PowerShell에서 저장소 루트 기준으로 실행합니다. 이 모드는 로컬 SQLite를 사용하고 보안 로그 전송을 끕니다. Wazuh·Graylog 수집 실습은 기존 README의 별도 설정을 사용하세요.

```powershell
Set-Location .\_7_board_test
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-team.txt
$env:DATABASE_URL = 'sqlite:///team-board.sqlite3'
$env:JWT_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
$env:GELF_ENABLED = '0'
$env:SECURITY_LOG_PATH = ''
.\.venv\Scripts\python.exe -m flask --app app:app run --host 127.0.0.1 --port 5001
```

접속 주소: <http://127.0.0.1:5001>. 회원가입, 로그인, 게시글 작성·조회·수정·삭제를 확인합니다. 중지할 때는 `Ctrl+C`를 누릅니다. 위 환경변수는 현재 PowerShell 창에만 적용됩니다. 기본 실행에는 관리자 API 키를 부여하지 않습니다.

기존 MySQL/Wazuh 컨테이너가 있는 PC에서 복사본의 `docker compose up`을 그대로 실행하면 `flask_mysql` 등의 이름과 포트가 충돌할 수 있습니다. 기존 보안 실습 환경은 유지하고, 자기소개 협업 확인에는 위 실행 방법을 사용하세요. 새 PC의 보안 실습은 인증서·Agent 등록·외부 Docker 네트워크·볼륨 준비가 추가로 필요합니다.

## 자동 검증

실행 서버를 종료한 뒤 `_7_board_test` 폴더에서 실행합니다.

```powershell
$env:GELF_ENABLED = '0'
$env:SECURITY_LOG_PATH = ''
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

실제 검증 결과는 [검증 기록](docs/VERIFICATION.md)에 남깁니다.

## 소스 출처와 공유 범위

원본: <https://github.com/myeongjundev/flask-board>

복사 기준 커밋: `d1801960bd11e074d25b61529a562c90a479617e`. Git에 등록된 143개 파일을 복사했으며 상세 기록은 [source-copy.json](source-copy.json)에 있습니다. `.env`, 실행 DB, 생성 인증서/개인키, Agent 등록 키, 비공개 백업은 복사하지 않았습니다. 포함된 보안 설정의 실습용 기본 계정 값은 실제 운영용 비밀번호로 사용하지 마세요.

개인 이메일, 비밀번호, API 키, 원본 알림 URL은 자기소개·PR·공개 캡처에 넣지 않습니다. 원본 프로젝트의 추가 도구 전체가 필요할 때는 `_7_board_test/requirements.txt`를 사용하세요.
