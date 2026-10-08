# Wazuh 수업 환경

강사님 저장소의 2026-10-07 커밋 `341605a`에 있는 구성을
`docker-compose.yml`로 옮겼습니다. Wazuh 4.9.0 Manager·Indexer·Dashboard를
실행하고, 대시보드 접속 포트는 `443`입니다.

현재 PC의 Graylog와 기존 Wazuh Manager가 연결된 네트워크는
`9_graylog_default`이므로 강사님 코드의 `graylog_default`를 이 이름으로
맞췄습니다. 기존 Manager 전용 구성은 `docker-compose-manager-only.yml`에
보존했습니다. Manager 전용 파일은 변경 전 원본 참고용입니다.
설정 이전 후 운영에는 `docker-compose.yml`을 사용합니다.

## 설정 파일 위치

수업에서 생성한 파일은 게시판 루트의 `config/`에 있습니다.
`wazuh/docker-compose.yml`의 상대 경로는 `../config/`로 맞췄습니다.
인증서 생성 파일 `generate-indexer-certs.yml`도 게시판 루트에 있습니다.
다음 구조는 게시판 프로젝트 루트 기준입니다.

```text
config/
├─ wazuh_indexer_ssl_certs/
│  ├─ root-ca-manager.pem
│  ├─ root-ca.pem
│  ├─ wazuh.manager.pem
│  ├─ wazuh.manager-key.pem
│  ├─ wazuh.indexer.pem
│  ├─ wazuh.indexer-key.pem
│  ├─ admin.pem
│  ├─ admin-key.pem
│  ├─ wazuh.dashboard.pem
│  └─ wazuh.dashboard-key.pem
├─ wazuh_indexer/
│  ├─ wazuh.indexer.yml
│  └─ internal_users.yml
└─ wazuh_dashboard/
   ├─ opensearch_dashboards.yml
   └─ wazuh.yml
```

인증서와 설정은 Compose의 서비스 별칭(`wazuh.manager`, `wazuh.indexer`,
`wazuh.dashboard`) 및 계정 정보와 일치해야 합니다.
저장소의 계정 설정은 Wazuh 수업용 데모 값입니다. 개인 운영 계정의 비밀번호,
인증서 및 TLS 개인키는 커밋하지 않습니다. 각 PC에서 생성한 파일은 Git 제외 경로에 둡니다.

인증서가 없는 환경에서는 `config/certs.yml`의 노드 이름을 확인하고 다음 생성 명령을
실행합니다. 기존 인증서가 있는 환경에서는 다시 생성하지 않고 현재 연결에 사용 중인
인증서를 보존합니다.

```powershell
docker compose -f generate-indexer-certs.yml run --rm generator
```

이 명령은 인증서를 생성하며 Manager 설정·Agent 등록·외부 저장 볼륨을 복원하지는 않습니다.

## 기존 Manager 전환 준비

이전 Manager는 `/var/ossec/logs`만 볼륨에 저장했습니다.
수업에서 생성한 `backup/wazuh_etc_20261008_101911.tar.gz`는 빈 볼륨의 백업이므로
복원용으로 사용하지 않습니다.

실제 Manager 설정은 `backups/wazuh-manager/migration_*/`에 Linux 소유권과
권한을 보존한 tar.gz로 백업합니다. Agent 키, 사용자 규칙·디코더·공유 설정,
API 설정, Agent DB와 Filebeat registry를 포함합니다. Agent DB는 SQLite
무결성 검사를 수행합니다. 대용량 취약점 피드 캐시는 별도로 새 queue 볼륨에
직접 복사하므로 이 tar.gz 백업에는 포함되지 않습니다.

새 Compose에는 Wazuh 4.9.0 공식 구성의 저장 볼륨을 추가했습니다.
`wazuh_etc`, `wazuh_api_configuration`, `wazuh_queue`, `wazuh_var_multigroups`,
사용자 스크립트 경로와 Filebeat registry를 유지합니다. 기존 `wazuh_logs`
볼륨은 계속 사용합니다.
이전한 볼륨은 `external: true`로 지정해 Compose가 재생성하거나 삭제하지
않도록 했습니다. 다른 PC에서는 기존 볼륨을 복원한 뒤 이 구성을 실행합니다.

실행 중인 Manager의 설정 파일을 별도로 복사하는 예:

```powershell
New-Item -ItemType Directory -Force backups/wazuh-manager
docker cp wazuh-manager:/var/ossec/etc backups/wazuh-manager/etc
```

## 실행과 확인

기존 Manager 설정 이전을 마친 뒤, 게시판 프로젝트 루트에서 실행합니다.

```powershell
docker network inspect 9_graylog_default
docker compose -f wazuh/docker-compose.yml config --quiet
docker compose -f wazuh/docker-compose.yml up -d
docker compose -f wazuh/docker-compose.yml ps
docker exec wazuh-manager /var/ossec/bin/agent_control -l
docker exec wazuh-manager /var/ossec/bin/agent_groups -s -i 001
docker exec wazuh-manager filebeat test output -c /etc/filebeat/filebeat.yml
docker compose -f wazuh/docker-compose.yml logs --tail 100
```

대시보드 주소: `https://localhost/`

`config --quiet`는 Compose 구문 검증이며 인증서 존재나 서비스 기동을
보장하지 않습니다. Flask의 `/dashboard`와 Wazuh Dashboard는 별도 화면입니다.
현재 `board-host`의 ID는 `001`이고 `default, flask-board` 그룹을 사용합니다.
수업 자료의 `002` 대신 `001`로 검색합니다. 기존 그룹 설정은
`C:\SKT aleph\flask-board-team\flask-board\logs\security.log` 수집 및
`C:\SKT aleph\flask-board-team\flask-board\templates` 실시간
감시를 포함합니다. FIM 경보는 `100220`, `100221`, `100222` 규칙으로 확인합니다.

### 팀 게시판의 Agent 공유 설정

[agent.conf](agent.conf)는 이 PC의 팀 게시판 경로를 사용하는 설정 원본입니다.
다른 팀원은 본인 PC의 경로로 수정한 뒤 적용합니다. Manager의 `flask-board` 그룹
공유 설정과 게시판 `.env`의 `SECURITY_LOG_PATH`가 같은 로그 파일을 가리켜야 합니다.

기존 공유 설정에 다른 수집 항목이 있다면
[개인 경로 설정 안내](../docs/WAZUH-PERSONAL-PATH-GUIDE.md)의 백업·부분 수정 절차를 사용합니다.
아래 명령은 이 PC의 게시판 전용 그룹에 원본을 검사하고 적용하는 예시입니다.

```powershell
docker cp .\wazuh\agent.conf wazuh-manager:/tmp/flask-board-agent.conf
if ($LASTEXITCODE -ne 0) { throw '설정 파일 업로드 실패' }
docker exec wazuh-manager /var/ossec/bin/verify-agent-conf -f /tmp/flask-board-agent.conf
if ($LASTEXITCODE -ne 0) { throw '문법 검사 실패: 적용하지 않습니다.' }
# 위 검사 성공 후 기존 공유 설정을 백업하고 적용
docker exec wazuh-manager cp -p /var/ossec/etc/shared/flask-board/agent.conf /var/ossec/etc/shared/flask-board/agent.conf.before-team-path
if ($LASTEXITCODE -ne 0) { throw '공유 설정 백업 실패: 적용하지 않습니다.' }
docker exec wazuh-manager cp /tmp/flask-board-agent.conf /var/ossec/etc/shared/flask-board/agent.conf
```

로컬 `.env` 설정:

```dotenv
SECURITY_LOG_PATH=C:\SKT aleph\flask-board-team\flask-board\logs\security.log
```

`.env` 변경 후 Flask를 재시작합니다. Manager가 공유 설정을 배포한 뒤 Windows의
`C:\Program Files (x86)\ossec-agent\shared\agent.conf`에 새 경로가 들어왔는지 확인합니다.
Manager 컨테이너를 재생성하는 것만으로는 감시 경로가 변경되지 않습니다.

2026-10-08 팀 경로 적용 후 확인한 결과:

- Agent `001`의 공유 설정 동기화 완료 및 Active 상태 확인
- 게시판 HTTP 200 및 새 `logs/security.log` 기록 확인
- 16:07:20 로그인 실패 테스트 경보 `100210`의 새 `location`을 Indexer에서 확인
- 16:07:49 새 `templates`의 임시 TXT 생성 경보 `100221`을 Indexer에서 확인
- 검증용 TXT 파일 삭제 완료; 원래 게시판의 로그와 기존 경보는 보존

이 변경은 Agent 감시 경로와 게시판 로그 출력 경로를 맞춘 것입니다.
실행 중인 컨테이너의 인증서 bind mount는 기존 게시판의 `config/`를 계속 사용합니다.
팀 폴더에서 Compose를 재실행하려면 Git에서 제외된 인증서가 해당 폴더에도 있어야 합니다.

실제 TLS 개인키와 Agent 키가 포함된 백업은 `.gitignore`로 제외합니다.
수업 자료: https://app.notion.com/p/wazuh_4-9_-d730741730ea82ed95b881c8f214105f
볼륨 구성 참고: https://github.com/wazuh/wazuh-docker/blob/v4.9.0/single-node/docker-compose.yml

## 2026-10-08 기동 검증

Manager·Indexer·Dashboard 모두 실행 중이며 `9_graylog_default`에 연결됩니다.
`board-host`(001)는 Active입니다. Filebeat의 TLS 검증 및 Indexer 연결 테스트가
`talk to server... OK`로 통과했고, Indexer에서 Agent 001 경보와 테스트 FIM
규칙 100220 경보가 조회됐습니다. 생성·수정·삭제 테스트 파일은 삭제했습니다.
Dashboard는 443 포트에서 실행됩니다.

읽기 전용 점검 스크립트와 개인별 진단 절차:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_wazuh.ps1 -AgentId 001
```

다른 PC의 Agent ID는 명령 출력에서 확인한 실제 값을 사용합니다. 스크립트 종료 코드만으로
전체 정상 여부를 판단하지 않고 각 단계의 출력과 실제 경보를 확인합니다.
[LLM 검증 길라잡이](../docs/WAZUH-LLM-VERIFICATION-GUIDE.md)와
[Graylog Alerts 설정 기록](../graylog/exports/README.md)을 함께 참고하세요.
