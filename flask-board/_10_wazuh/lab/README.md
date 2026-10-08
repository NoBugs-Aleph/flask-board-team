# 미니실습 — Wazuh 브루트포스 · FIM · 파일 위변조 탐지

실행 환경(로컬, 2026-10-06 검증 완료)

| 구성 | 상태 |
|---|---|
| Wazuh Manager | Docker `wazuh/wazuh-manager:4.9.0` (`wazuh-manager`), 1514/1515 |
| Wazuh Agent | Windows 서비스 `WazuhSvc`, 이름 `board-host`, **Active**, 그룹 `flask-board` |
| 대상 앱 | Flask 게시판 `http://localhost:5000` (`Desktop\Python-aleph-sh\...\_7_board_test`) |
| 감시 설정 | Manager 그룹 설정 `shared/flask-board/agent.conf` → Agent 로 자동 배포 |

> Wazuh Dashboard(Indexer 포함) 컨테이너는 없다. 알림 확인은 `alerts.json` + 게시판 보안 대시보드(`/dashboard`)로 한다.

## 데이터 흐름
```
login 실패 → logs/security.log(1줄) → Agent localfile → Manager
   → Decoder webapp-login(srcip,dstuser) → Rule 100210(L5) → 100211(L10, 120초 6회)
templates 파일 변경 → Agent FIM(realtime) → Manager → Rule 550/553/554 → 100220~100224
```

## 설정 파일
- `local_decoder.xml`, `local_rules.xml` (이 폴더) → 컨테이너 `/var/ossec/etc/{decoders,rules}/`
- 이번에 **추가한 룰**: `100223`(templates 새 파일 생성, L7), `100224`(templates 파일 삭제, L7)
  - 기존 보조 룰 100218/100219(level 0)가 templates 아래 *모든* 생성·삭제를 삼켜서 `.html` 같은 일반 파일은 알림이 없었음
  - 같은 부모 아래에서는 파일 순서대로 먼저 맞는 룰이 이기므로 `100220`/`100222`(실행형 파일) 뒤에 배치

적용:
```powershell
docker cp .\local_rules.xml wazuh-manager:/var/ossec/etc/rules/local_rules.xml
docker exec wazuh-manager chown root:wazuh /var/ossec/etc/rules/local_rules.xml
docker exec wazuh-manager /var/ossec/bin/wazuh-analysisd -t
docker exec wazuh-manager /var/ossec/bin/wazuh-control restart
```

## 실습 순서

### ① Agent 연동 확인
```powershell
docker exec wazuh-manager /var/ossec/bin/agent_control -l
docker exec wazuh-manager /var/ossec/bin/agent_control -i 001
```
결과: `ID 001, board-host, Active`, Wazuh v4.9.0

### ② 브루트포스 (시나리오 1)
```powershell
python .\bruteforce.py --user wz_test --ip 198.51.100.10 --count 8
Get-Content <게시판>\logs\security.log -Tail 8
.\show_alerts.ps1 -Rules 100210,100211
```
결과: 8회 모두 HTTP 401 → security.log 에 `login_failed user=wz_test src_ip=198.51.100.10`
→ Rule **100210**(L5) 반복, **100211**(L10, MITRE T1110) 발생. 게시판 `/dashboard`에도 `[Wazuh] 브루트포스` High 인시던트.

logtest:
```powershell
'2026-10-06 13:54:50.712 login_failed user=wz_test src_ip=198.51.100.10' | docker exec -i wazuh-manager /var/ossec/bin/wazuh-logtest
```
→ decoder `webapp-login`, `dstuser=wz_test`, `srcip=198.51.100.10`, rule 100210 / level 5

### ③④ FIM · 위변조 · 생성/삭제 (시나리오 2·3)
감시 대상: `<게시판>\templates` (realtime). 아래를 `templates` 에서 실행:
```powershell
$t='<게시판>\templates'
Set-Content "$t\wz_fim_test.html" '<h1>normal</h1>'          # 생성
Add-Content "$t\wz_fim_test.html" '<!-- TAMPERED -->'         # 내용 변조
Remove-Item "$t\wz_fim_test.html"                              # 삭제
.\show_alerts.ps1 -Rules 100220,100221,100222,100223,100224
```

| 동작 | 파일 | Rule / Level | event |
|---|---|---|---|
| 생성 | wz_shell_test.php | 100220 / **12** (웹셸 의심) | added |
| 변조 | wz_fim_test.html | 100221 / 8 | modified |
| 삭제 | wz_shell_test.php | 100222 / 10 | deleted |
| 생성 | wz_new_notice.html | 100223 / 7 | added |
| 삭제 | wz_new_notice.html | 100224 / 7 | deleted |

알림 필드: 파일 경로(`syscheck.path`), 종류(`event`), 수정시간(`mtime_after`), 사용자(`uname_after`), 해시 변경(`md5/sha256_before/after`).

## 알려진 한계
- **권한 변경(icacls)** 은 Windows realtime FIM 에서 알림이 나오지 않았다(ACL 변경은 realtime 이벤트를 일으키지 않음). 과제 필수 항목이 아니라서 제외. 필요하면 `frequency`를 짧게 준 스캔 모드로 확인.
- 변경 *내용*(diff)은 Windows 에서 `report_changes` 가 지원되지 않아 해시 before/after 로만 비교한다.
- Agent 서비스 제어(`Restart-Service WazuhSvc`)는 관리자 PowerShell 필요.
- `bruteforce.py` 는 본인 로컬 게시판 전용.
