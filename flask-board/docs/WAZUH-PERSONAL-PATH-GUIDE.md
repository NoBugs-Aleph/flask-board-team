# 팀원용 Wazuh 게시판 경로 설정 및 검증

작성일: 2026-10-08 · Windows / PowerShell / Wazuh 4.9.0

**각자의 PC에서 실제 실행 중인 Flask 게시판 폴더를 기준으로 설정합니다.**
김명준 PC의 경로나 강사님의 `E:\...\_7_board_test` 경로를 그대로 사용하지 않습니다.
이 문서는 이미 Manager·Indexer·Dashboard와 Windows Agent가 설치된 환경의 경로 변경 안내입니다.

## 1. 본인의 게시판 폴더와 Agent 확인

`app.py`, `.env`, `templates`가 있는 폴더가 게시판 루트입니다.
저장소 바깥 폴더나 다른 복사본을 선택하지 말고, 현재 서버를 실행하는 폴더를 선택합니다.

아래 변수는 **본인 환경에 맞게 수정**합니다. 이후 명령은 같은 PowerShell 창에서 실행합니다.

```powershell
# 아래 경로는 김명준 PC의 예시입니다. 본인 경로로 바꾸세요.
$BoardRoot = 'C:\SKT aleph\flask-board-team\flask-board'
$ManagerName = 'wazuh-manager'
$AgentId = '001'               # 아래 목록에서 본인 Agent ID 확인 후 변경
$AgentGroup = 'flask-board'    # 본인 Agent가 사용하는 게시판 수집 그룹

Get-Item -LiteralPath (Join-Path $BoardRoot 'app.py')
Get-Item -LiteralPath (Join-Path $BoardRoot 'templates')
docker ps --format 'table {{.Names}}\t{{.Status}}'
docker exec $ManagerName /var/ossec/bin/agent_control -l
docker exec $ManagerName /var/ossec/bin/agent_groups -s -i $AgentId
```

Agent ID가 다른 PC에서도 `001`인 것은 정상일 수 있습니다. 각 Manager의 목록에서 확인합니다.
하나의 Manager를 여러 사람이 공유한다면, 다른 경로를 쓰는 Agent에 같은 그룹 설정을
덮어쓰지 말고 Agent별 적용 대상과 그룹을 먼저 구분합니다.

## 2. 세 곳의 경로를 일치시키기

| 설정 위치 | 본인 PC에서 가리켜야 하는 경로 |
|---|---|
| Flask `.env`의 `SECURITY_LOG_PATH` | `<본인 게시판 루트>\logs\security.log` |
| Manager 그룹 `agent.conf`의 `<location>` | 위와 같은 `security.log` 파일 |
| Manager 그룹 `agent.conf`의 `<directories>` | `<본인 게시판 루트>\templates` |

이 경로는 **Windows Agent가 읽는 Windows 경로**입니다.
Manager가 Docker에서 실행돼도 `/var/ossec/...`로 바꾸지 않습니다.

### 2-1. Flask의 로그 저장 위치

본인 게시판 `.env`를 열어 `SECURITY_LOG_PATH`를 수정하거나 추가합니다.
같은 항목을 중복으로 추가하지 않습니다. 아래는 김명준 PC의 예시입니다.

```dotenv
SECURITY_LOG_PATH=C:\SKT aleph\flask-board-team\flask-board\logs\security.log
```

`logs` 폴더가 없다면 생성합니다.

```powershell
New-Item -ItemType Directory -Path (Join-Path $BoardRoot 'logs') -Force
```

`.env` 변경 후 현재 Flask 서버를 종료하고 **같은 게시판 폴더에서** 재시작합니다.
사용하던 가상환경과 실행 방식을 유지합니다. 이미 실행 중인 서버 위에 두 번째 서버를 띄우지 않습니다.

### 2-2. Manager의 공유 설정 백업 및 수정

설정 위치는 `/var/ossec/etc/shared/<본인 그룹>/agent.conf`입니다.
먼저 기존 파일을 내려받고, 백업 복사본을 남깁니다.

```powershell
$BackupDir = Join-Path $BoardRoot ('backup\wazuh-path-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $BackupDir -Force
$OriginalConfig = Join-Path $BackupDir 'agent.conf.original'
$EditedConfig = Join-Path $BackupDir 'agent.conf.edit'
$RemoteConfig = "/var/ossec/etc/shared/$AgentGroup/agent.conf"

docker cp "${ManagerName}:$RemoteConfig" $OriginalConfig
if ($LASTEXITCODE -ne 0) { throw '공유 설정 백업 실패: 그룹과 파일 위치를 확인하세요.' }
Copy-Item -LiteralPath $OriginalConfig -Destination $EditedConfig
```

`$EditedConfig` 파일을 편집기에서 열고, 게시판 수집용 `<location>`과 `<directories>`를
본인 경로로 수정합니다. **다른 수집 항목·옵션·그룹 설정은 보존합니다.**
아래 XML은 두 경로의 예시이며, 기존 파일 전체를 무조건 교체하는 용도가 아닙니다.

```xml
<agent_config os="Windows">
  <localfile>
    <location>C:\SKT aleph\flask-board-team\flask-board\logs\security.log</location>
    <log_format>syslog</log_format>
  </localfile>
  <syscheck>
    <directories realtime="yes" check_all="yes">C:\SKT aleph\flask-board-team\flask-board\templates</directories>
  </syscheck>
</agent_config>
```

UTF-8로 저장한 뒤 문법 검사를 통과한 경우에만 적용합니다.

```powershell
docker cp $EditedConfig "${ManagerName}:/tmp/agent-path-check.conf"
if ($LASTEXITCODE -ne 0) { throw '설정 파일 업로드 실패' }
docker exec $ManagerName /var/ossec/bin/verify-agent-conf -f /tmp/agent-path-check.conf
if ($LASTEXITCODE -ne 0) { throw '문법 검사 실패: 적용하지 마세요.' }
docker exec $ManagerName cp /tmp/agent-path-check.conf $RemoteConfig
if ($LASTEXITCODE -ne 0) { throw '공유 설정 적용 실패' }
docker exec $ManagerName /var/ossec/bin/verify-agent-conf
```

공유 설정은 Manager에서 Agent로 전달됩니다. Windows의 내려받은 공유 파일만 직접 수정하면
다음 동기화 때 덮어써질 수 있으므로 **Manager의 원본을 수정**합니다.
컨테이너 재생성이나 볼륨 삭제는 경로 변경에 필요하지 않습니다.

## 3. Windows Agent에 실제로 적용됐는지 확인

동기화에는 시간이 걸릴 수 있습니다. 다음 출력에서 본인 경로를 확인합니다.
Agent 설치 위치가 다르면 `$AgentInstall`도 수정합니다.

```powershell
$AgentInstall = 'C:\Program Files (x86)\ossec-agent'
Get-Service WazuhSvc
docker exec $ManagerName /var/ossec/bin/agent_groups -S -i $AgentId
Select-String -LiteralPath (Join-Path $AgentInstall 'shared\agent.conf') -Pattern '<location>','<directories'
Get-Content -LiteralPath (Join-Path $AgentInstall 'ossec.log') -Tail 80 |
    Select-String -Pattern 'Analyzing file:','Monitoring path:','Real-time file integrity monitoring started','ERROR'
```

확인할 항목:

- Windows Agent 서비스가 Running이고 Manager에서 Agent가 Active인지
- 공유 파일에 새 `security.log`와 `templates` 경로가 들어왔는지
- Agent 로그에서 새 로그 파일 수집과 새 폴더 감시가 시작됐는지
- 실제 로그인 시도 후 본인 `logs\security.log`가 갱신되는지

로그인 실패·브루트포스 경보는 수업용 커스텀 규칙 `100210`, `100211`을 사용하는 환경의 예입니다.
한 번의 실패로 반복 실패 경보까지 발생하는 것은 아닙니다.

## 4. 본인 templates에서 생성 → 수정 → 삭제 테스트

각 단계 사이에 10~15초 정도 기다리고 경보를 확인한 후 다음 단계로 진행합니다.
세 명령을 연속으로 빠르게 실행하면 중간 변경이 별도 사건으로 잡히지 않을 수 있습니다.
파일 내용은 `test`, `modified`뿐이며 PHP 실행 코드를 넣지 않습니다.

### 생성

기존 `test.php`가 있으면 사용 중인 파일일 수 있으므로 다른 테스트 파일명을 선택합니다.

```powershell
$TestFile = Join-Path $BoardRoot 'templates\test.php'
if (Test-Path -LiteralPath $TestFile) { throw '기존 파일이 있습니다. 다른 테스트 파일명을 선택하세요.' }
Set-Content -LiteralPath $TestFile -Value 'test'
```

### 수정

```powershell
Add-Content -LiteralPath $TestFile -Value 'modified'
```

### 삭제

```powershell
Remove-Item -LiteralPath $TestFile
Test-Path -LiteralPath $TestFile   # False이면 정리 완료
```

## 5. Wazuh Dashboard에서 확인

Dashboard의 **File Integrity Monitoring → Events**에서 본인 Agent를 선택합니다.
시간 범위를 **Last 1 hour** 또는 **Last 24 hours**로 설정하고 새로고침합니다.
경보의 `syscheck.path`가 본인의 새 경로인지 확인합니다.

수업용 커스텀 규칙이 설치된 김명준 PC의 실제 결과는 다음과 같습니다.
다른 PC에서도 본인 테스트 결과로 따로 확인해야 합니다.

| 동작 | syscheck.event | 규칙 | 김명준 PC 확인 시각 |
|---|---|---|---|
| 생성 | added | 100220 | 2026-10-08 16:23:24 |
| 수정 | modified | 100220 | 2026-10-08 16:23:40 |
| 삭제 | deleted | 100222 | 2026-10-08 16:23:53 |

Threat Hunting → Events에서도 조회할 수 있습니다. 아래 `001`은 본인 Agent ID로 바꿉니다.

```text
agent.id:"001" AND (rule.id:"100220" OR rule.id:"100222")
```

경보 번호는 커스텀 규칙 설치 여부에 따라 달라집니다. 기본 FIM 경보만 보이면
Manager의 `/var/ossec/etc/rules/local_rules.xml`에서 `100221`의 경로 조건도 확인합니다.
김명준 PC의 조건 `(?i)flask-board.templates.`는 `flask-board\templates\`를 대상으로 합니다.
게시판 폴더명이 `_7_board_test`처럼 다르면 이 조건도 본인 폴더에 맞아야 합니다.
기존 규칙 ID를 중복 추가하지 말고, 변경이 필요하면 백업·문법 검사 후 적용합니다.

`.env`, 개인키, API 토큰, Agent 등록 키와 설정 백업 원문은 공유하지 않습니다.
이 저장소는 `backup/`를 Git에서 제외하지만, 다른 저장소에서도 제외되는지 확인합니다.
상세 진단은 [Wazuh LLM 검증 길라잡이](WAZUH-LLM-VERIFICATION-GUIDE.md)를 참고합니다.

## 6. 팀원이 LLM에 전달할 요청문

```text
이 문서를 기준으로 내 PC의 Flask 게시판과 Wazuh 경로를 확인하고 맞춰 줘.
실제 서버가 실행 중인 폴더, Windows Agent 설치 위치, Manager 컨테이너 이름,
Agent ID와 게시판 수집 그룹을 먼저 확인해 줘.
김명준 PC의 경로나 Agent ID를 내 PC에 그대로 적용하지 마.

.env의 SECURITY_LOG_PATH, Manager 공유 설정의 location과 directories,
Windows Agent가 받은 공유 설정, FIM 커스텀 규칙의 경로 조건을 비교해 줘.
설정 변경 전 백업하고 기존 설정의 다른 항목과 Agent 등록·규칙·볼륨을 보존해 줘.
내 PC에 맞는 설정을 적용하고 동기화 여부를 확인해 줘.

기존 파일과 겹치지 않는 무해한 PHP 테스트 파일로 생성·수정·삭제를 각각 확인해 줘.
Manager 경보와 Indexer 저장을 같은 Agent·시각·파일 경로로 비교해 줘.
Dashboard에 표시된 사실과 아직 확인하지 못한 내용을 구분해 줘.
검증 파일을 정리하고 비밀번호·토큰·개인키·Agent 키는 출력하지 마.
내 PC를 직접 사용할 수 없으면 필요한 명령과 결과 확인 방법을 단계별로 알려 줘.
```
