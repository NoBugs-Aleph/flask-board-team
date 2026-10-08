# 미니실습 — Gobuster·Hydra 트래픽 발생 및 Wazuh 웹 위협 탐지

실행 환경 (로컬, 2026-10-06 검증 완료)

| 구성 | 값 |
|---|---|
| Wazuh Manager | Docker `wazuh-manager` 4.9.0, 1514/1515 |
| Wazuh Agent | Windows `WazuhSvc`, 이름 `board-host`, Active, 그룹 `flask-board` |
| 대상 앱 | Flask 게시판 `http://localhost:5000` (`Desktop\...\_7_board_test`) |
| 공격 도구 | Kali(WSL2) `172.17.144.170` — gobuster / hydra 설치됨 |
| 게시판에서 본 공격자 IP | `172.17.144.1` 로 보낼 때 앱에는 `172.17.144.170`(Kali eth0)로 기록 |
| SIEM/SOAR | Graylog `gl-graylog`, n8n(자동 차단·인시던트 생성) |

## 데이터 흐름
```
gobuster(디렉터리 스캔)                     hydra(로그인 무차별 대입)
   ↓ 없는 경로 다량 요청(404)                   ↓ /api/auth/login 반복 실패
앱 after_request → logs/webaccess.log      앱 login() → logs/security.log
   ↓                                           ↓
          Wazuh Agent (localfile 2개)  ────────┘
   ↓
Wazuh Manager  Decoder → Rule 매칭
   ├ webapp-access → 100230(개별 404,L3) → 100231(스캔,L10, 30초 10회, T1595.003)
   └ webapp-login  → 100210(실패,L5)     → 100211(브루트포스,L10, 120초 6회, T1110)
   ↓ syslog_output(100211,100220~222,100231) → Graylog → n8n
   ↓
게시판 보안 대시보드 인시던트 티켓 / 자동 IP 차단(active response)
```

## 이번 실습에서 추가/수정한 것

### 1) 앱 — 웹 액세스 로그 + 폼 로그인 수용
- `controllers/weblog.py` (신규): 모든 요청을 `logs/webaccess.log` 에 한 줄씩 기록
  (밀리초 타임스탬프 — Wazuh 프리디코더 회피). 예:
  `2026-10-06 15:55:07.046 web_access src_ip=172.17.144.170 method=GET path=/uploader code=404`
- `config.py`: `WEBACCESS_LOG_PATH` 추가
- `app.py` `_web_scan_probe`: 모든 요청을 `write_weblog` 로 기록(기존 404→GELF 유지)
- `controllers/auth_controller.py` `login()`:
  `request.get_json(...) or request.form or {}` — JSON(SPA) 과 form-urlencoded(hydra·curl)
  양쪽을 받는다. hydra `http-post-form`(콜론 없는 폼 인코딩)이 깔끔하게 동작하게 하기 위함.

### 2) Wazuh — 디코더 + 룰 (이 폴더 `local_decoder.xml`, `local_rules.xml`)
- 디코더 `webapp-access` / `webapp-access-fields`: `srcip, extra_data(method), url(path), id(code)`
- 룰 `100230`(L3): 개별 404 — **level 0 이면 frequency 집계에 안 잡혀 L3 로 둠(실측)**
- 룰 `100231`(L10, frequency=10 timeframe=30 same_source_ip): 디렉터리 스캐닝 의심
- `ossec.conf syslog_output rule_id` 에 `100231` 추가 → Graylog 전달

적용(이미 반영됨, 재적용 시):
```powershell
docker cp .\local_decoder.xml wazuh-manager:/var/ossec/etc/decoders/local_decoder.xml
docker cp .\local_rules.xml   wazuh-manager:/var/ossec/etc/rules/local_rules.xml
docker cp "<board>\wazuh_config\agent.conf" wazuh-manager:/var/ossec/etc/shared/flask-board/agent.conf
docker exec wazuh-manager sh -c "chown root:wazuh /var/ossec/etc/rules/local_rules.xml /var/ossec/etc/decoders/local_decoder.xml /var/ossec/etc/shared/flask-board/agent.conf"
docker exec wazuh-manager /var/ossec/bin/wazuh-analysisd -t   # 문법 검사
docker exec wazuh-manager /var/ossec/bin/wazuh-control restart
Restart-Service WazuhSvc -Force   # Agent 가 webaccess.log 를 처음부터 tail 하도록
```

## 실행 순서

### 시나리오 1 — Gobuster 디렉터리 스캔
```bash
# Kali(WSL)에서
wsl -d kali-linux -- bash /tmp/hydra2.sh   # (아래 hydra 와 혼동 주의 - 스캔은 gobuster)
gobuster dir -u http://172.17.144.1:5000 -w /usr/share/wordlists/dirb/common.txt -t 20 -q --no-error
```
또는 동봉 스크립트:
```bash
wsl -d kali-linux -- bash /mnt/c/.../scan_gobuster.sh
```
확인:
```powershell
.\show_web_alerts.ps1 -Ip 172.17.144.170
Get-Content <board>\logs\webaccess.log -Tail 10
```

### 시나리오 2 — Hydra 웹 브루트포스
대상 계정 `wz_test` (정답 `Correct#123`). 패스워드 목록으로 반복 실패 유도:
```bash
# Kali: 패스워드 목록
printf '123456\npassword\nadmin\nletmein\nqwerty\nwelcome\nmonkey\ndragon\n...\n' > /tmp/wzpass.txt
hydra -l wz_test -P /tmp/wzpass.txt -s 5000 172.17.144.1 \
  http-post-form "/api/auth/login:username=^USER^&password=^PASS^:msg" -t 4
```
- 필드 구분자(:)와 충돌을 피하려고 **form-urlencoded** 사용(콜론 없음).
- 실패 조건 `msg` = 실패(401) 응답 JSON 에만 있는 키.
확인:
```powershell
.\show_web_alerts.ps1 -Ip 172.17.144.170
Get-Content <board>\logs\security.log -Tail 10
```

## 탐지 결과 (2026-10-06 실측, src_ip=172.17.144.170)

| 공격 유형 | 대상 경로/계정 | 탐지 Rule ID | Level | 발생 건수 |
|---|---|---|---|---|
| 디렉터리 스캔 (gobuster) | 다수 404 경로 (`/admin.php`, `/phpmyadmin`, …) | 100230 (개별 404) | 3 | 4121 |
| 디렉터리 스캔 (gobuster) | 동일 IP 단시간 404 다수 | **100231 (디렉터리 스캔, T1595.003)** | 10 | 472 |
| 웹 브루트포스 (hydra) | `POST /api/auth/login`, 계정 `wz_test` | 100210 (로그인 실패) | 5 | 1741 |
| 웹 브루트포스 (hydra) | 동일 IP 120초 6회↑ 실패 | **100211 (브루트포스, T1110)** | 10 | 354 |

- 게시판 보안 대시보드 인시던트 티켓: **#63 (172.17.144.170, High, event_count 7)** — ip-guard 재시도 + Wazuh 경보가 묶여 생성.
- SOAR(n8n) active response: 공격 중/후 Graylog 경보 기반으로 `172.17.144.170` 자동 차단 확인(이후 요청 403).

## 주의 / 운영 메모
- **SOAR 자동 차단과 스캔의 상호작용:** n8n 이 켜져 있으면 스캔 초반 404 폭주를 보고 공격
  IP 를 즉시 차단해, 이후 요청이 404→403 으로 바뀌어 404 집계가 끊긴다. Wazuh 디렉터리
  스캔 룰만 깨끗이 보려면 n8n 을 잠시 멈추고(`docker stop n8n`) 스캔 후 다시 켠다
  (`docker start n8n`). 공격↔방어를 함께 보려면 켠 채로 진행(차단 로그가 방어 증적).
- **Agent 파일 tail 타이밍:** `webaccess.log` 가 없던 상태로 에이전트가 떠 있으면, 파일
  최초 생성분을 놓칠 수 있다. 파일을 만든 뒤 `Restart-Service WazuhSvc` 하면 처음부터 읽는다.
- **차단 해제 / 계정 잠금 해제:** 반복 실측 시 `blocked_ips` 와 `users.is_locked` 를 비워야 한다
  (동봉 `dbtool.py` 또는 관리자 API). hydra 는 대상 계정을 잠그므로 재시도 전 해제 필요.
- 모든 공격 스크립트는 본인 로컬 게시판(`172.17.144.1:5000`) 전용.
