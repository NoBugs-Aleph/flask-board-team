# 제출 — Gobuster·Hydra 트래픽 발생 및 Wazuh 웹 위협 탐지

- 작성일: 2026-10-06
- 실습 환경: Wazuh Manager 4.9.0(Docker) + Agent `board-host`(Windows) + Flask 게시판(`localhost:5000`)
- 공격 호스트: Kali(WSL2) `172.17.144.170` → 게시판(`172.17.144.1:5000`)
- SIEM/SOAR: Graylog `gl-graylog`, n8n(자동 차단·인시던트 생성)

> 화면 캡처 항목은 아래 **수집된 텍스트 증적 파일**과 함께, 각 항목에 적힌 명령/화면을
> 직접 캡처해 첨부하면 됩니다. 수치·로그·Alert 는 모두 실제 실행 결과입니다.

---

## 1) 디렉터리 스캔 탐지 화면

**공격(도구측):** `evidence_gobuster_console.txt`
```
gobuster dir -u http://172.17.144.1:5000 -w /usr/share/wordlists/dirb/common.txt -t 20 -q --no-error
```
gobuster 가 사전 파일의 경로를 대량 요청 → 존재하지 않는 경로는 404.

**탐지(Wazuh 집계):** `evidence_alert_summary.txt`
```
rule 100230  개별 404 (경로 탐색)      : 4121건
rule 100231  디렉터리 스캔 (T1595.003) : 472건
```
→ 캡처 화면: Kali 의 gobuster 실행 창 + PowerShell `.\show_web_alerts.ps1 -Ip 172.17.144.170` 출력.

## 2) 웹 서버 액세스 로그 내 연속된 요청 기록

**파일:** `evidence_webaccess.log` (게시판 `logs/webaccess.log` 발췌)
```
2026-10-06 15:54:40.659 web_access src_ip=172.17.144.170 method=GET path=/.bash_history code=404
2026-10-06 15:54:40.681 web_access src_ip=172.17.144.170 method=GET path=/.htaccess     code=404
... (동일 IP 에서 수천 건의 404 가 밀리초 간격으로 연속) ...
```
→ 캡처 화면: `Get-Content <board>\logs\webaccess.log -Tail 30` (동일 src_ip, 404 연속).

## 3) Wazuh 디렉터리 탐색/스캐닝 관련 Alert

**파일:** `evidence_alerts.txt` — rule 100231 대표 Alert (총 472건)
```json
{
  "rule": { "id": "100231", "level": 10,
            "description": "연습 웹앱 디렉터리 스캐닝 의심 (동일 IP 단시간 404 다수 - gobuster/dirb)",
            "mitre": { "id": ["T1595.003"], "tactic": ["Reconnaissance"],
                       "technique": ["Wordlist Scanning"] },
            "frequency": 10 },
  "agent": { "id": "001", "name": "board-host" },
  "decoder": { "name": "webapp-access" },
  "data": { "srcip": "172.17.144.170", "id": "404", "url": "/layouts", "extra_data": "GET" }
}
```
→ 캡처 화면: Wazuh Dashboard(또는 alerts.json) 에서 rule **100231** 검색 결과.
  (본 환경엔 Wazuh Indexer/Dashboard 가 없어 `alerts.json` 과 게시판 대시보드로 대체 — `evidence_dashboard_incident.txt`.)

## 4) 브루트포스 탐지 화면

**공격(도구측):** `evidence_hydra_console.txt`
```
hydra -l wz_test -P wzpass.txt -s 5000 172.17.144.1 \
  http-post-form "/api/auth/login:username=^USER^&password=^PASS^:msg" -t 4
```
**탐지(Wazuh):** `evidence_alerts.txt` — rule 100211 대표 Alert (총 354건)
```json
{
  "rule": { "id": "100211", "level": 10,
            "description": "연습 웹앱 브루트포스 의심 (동일 IP 다수 실패)",
            "mitre": { "id": ["T1110"], "tactic": ["Credential Access"],
                       "technique": ["Brute Force"] }, "frequency": 6 },
  "agent": { "name": "board-host" },
  "decoder": { "name": "webapp-login" },
  "data": { "srcip": "172.17.144.170", "dstuser": "wz_test" }
}
```
→ 캡처 화면: Kali hydra 실행 창 + `.\show_web_alerts.ps1` 의 100210/100211 집계.

## 5) 반복된 로그인 실패 로그 수집 내역

**파일:** `evidence_security.log` (게시판 `logs/security.log` 발췌)
```
2026-10-06 16:12:22.623 login_failed user=wz_test src_ip=172.17.144.170
2026-10-06 16:12:22.651 login_failed user=wz_test src_ip=172.17.144.170
... (동일 IP·동일 계정 반복 실패 수천 건) ...
```
→ 캡처 화면: `Get-Content <board>\logs\security.log -Tail 30`.

## 6) 이벤트 분석 결과 요약

- **정찰(Gobuster):** `172.17.144.170` 이 사전(common.txt, 4,600여 경로)으로 디렉터리를
  열거. 존재하지 않는 경로에서 **4,121건의 404** 발생. 동일 IP 가 30초 내 404 를 10회
  이상 유발하는 패턴을 Wazuh 가 **rule 100231(L10, T1595.003)** 로 **472회** 탐지.
  액세스 로그(webaccess.log)가 Agent localfile 로 수집 → `webapp-access` 디코더가
  `srcip/method/url/code` 추출 → 빈도 룰이 스캐닝으로 판정.
- **인증 공격(Hydra):** 동일 IP 가 `wz_test` 계정에 비밀번호 사전 대입. 앱이 실패를
  `security.log` 에 기록(**누적 2,431건**), `webapp-login` 디코더가 `dstuser/srcip`
  추출 → **rule 100210(L5)** 개별 실패 **1,741건**, **rule 100211(L10, T1110)**
  브루트포스 **354회** 탐지.
- **탐지→대응 연계:** Wazuh 경보(100211/100231)가 syslog_output 으로 Graylog 전달 →
  n8n(SOAR)이 공격 IP `172.17.144.170` 을 **자동 차단(active response)**,
  게시판 보안 대시보드에 **인시던트 티켓 #63(High)** 생성. 차단 이후 공격자의 요청은
  앱에 닿기 전 403 으로 반려(`evidence_dashboard_incident.txt` 타임라인 참조).
- **공격 흔적(Artifact) 정리:** 디렉터리 스캔은 *짧은 간격의 대량 404* 로, 브루트포스는
  *동일 IP·동일 계정의 반복 인증 실패* 로 로그에 남으며, 두 패턴 모두 "동일 출발지 +
  단시간 임계치 초과"라는 빈도 기반 룰로 중앙(Manager)에서 식별된다.

## 7) 공격 유형별 식별 정보 표

| 공격 유형 | 도구 | 출발지 IP | 대상 경로/계정 | 탐지 Rule ID | Level | MITRE | 탐지 건수 |
|---|---|---|---|---|---|---|---|
| 디렉터리 스캔 | Gobuster | 172.17.144.170 | 다수 404 경로(`/.htaccess`,`/layouts`,`/phpmyadmin`…) | 100230 | 3 | — | 4,121 |
| 디렉터리 스캔 | Gobuster | 172.17.144.170 | 동일 IP 30초 10회↑ 404 | **100231** | 10 | T1595.003 | 472 |
| 웹 브루트포스 | Hydra | 172.17.144.170 | `POST /api/auth/login`, 계정 `wz_test` | 100210 | 5 | — | 1,741 |
| 웹 브루트포스 | Hydra | 172.17.144.170 | 동일 IP 120초 6회↑ 실패 | **100211** | 10 | T1110 | 354 |

- 게시판 보안 대시보드 인시던트: **#63 / 172.17.144.170 / High / event_count 7**
  (ip-guard 자동차단×4 + Wazuh 경보×2 + wazuh-block×1 통합)

---

## 첨부 파일 목록 (이 폴더)
| 파일 | 내용 | 대응 제출 항목 |
|---|---|---|
| `evidence_gobuster_console.txt` | Gobuster 실행 콘솔 | ① |
| `evidence_webaccess.log` | 웹 액세스 로그 연속 404 발췌 | ② |
| `evidence_alerts.txt` | Wazuh 100231/100211 대표 Alert(JSON) | ③④ |
| `evidence_alert_summary.txt` | rule별 탐지 집계 | ①③④ |
| `evidence_hydra_console.txt` | Hydra 실행/증적 요약 | ④ |
| `evidence_security.log` | 반복 로그인 실패 로그 발췌 | ⑤ |
| `evidence_dashboard_incident.txt` | 게시판 대시보드 인시던트 #63 상세 | ③⑥ |

> 구축/운영 상세는 상위 폴더 `README_gobuster_hydra.md` 참조.
