# 트러블슈팅 기록 — member_04 (2026-10-08)

Wazuh 보안 실습을 진행하며 겪은 오류와 해결 과정을 정리했다.
같은 환경(Windows + Docker + WSL Kali + Wazuh/Graylog/n8n)에서 같은 증상을 만나면 참고.

---

## A. 환경 설정

### A-1. `.env` 작성
- 랜덤 키(JWT/SECURITY/ADMIN)는 `python -c "import secrets;print(secrets.token_urlsafe(36))"`로 생성.
- **미사용 키는 `<...>` placeholder로 두지 말 것** — 코드가 가짜 문자열을 진짜 값으로 읽어 오류. 안 쓰면 **빈 값**(`KEY=`).
- `.env`는 `.gitignore`에 있어 커밋 안 됨(`git check-ignore flask-board/.env`로 확인).

### A-2. `check_wazuh.ps1` [5] Indexer count가 빈 출력
- **증상**: `[5] Actual Indexer alert count`가 아무것도 안 나옴.
- **원인**: 데이터 문제 아님. PowerShell에서 `docker exec -i ... curl --config -`로 **자격증명 stdin 파이프 전달이 실패**함.
- **실제 상태**: Indexer `wazuh-alerts-*`에 경보 1401건 정상 존재. 컨테이너 안에서 base64로 config 파일 만들어 질의하면 정상 응답.

---

## B. 공격 실행 (Kali/WSL)

### B-1. 공격 요청이 전부 `000` (연결 실패)
- **원인**: 명령의 `<BOARD_IP>`를 **실제 IP로 치환 안 함**.
- **해결**: `192.168.3.7`(Windows 호스트 LAN IP, `ipconfig`로 확인)로 교체.

### B-2. PowerShell에서 `curl` 오류 (`SessionVariable ... 누락`)
- **원인**: PowerShell의 `curl`은 `Invoke-WebRequest` 별칭이라 `-s -o -w` 플래그를 못 받음.
- **해결**: 공격/테스트는 **WSL(bash)**에서 실행. PowerShell에서 꼭 쓰려면 `curl.exe` 사용.

### B-3. `docker` 명령이 WSL에서 실행 안 됨
- **증상**: `The command 'docker' could not be found in this WSL 2 distro.`
- **원인**: docker는 Windows에만 있음.
- **해결**: `docker exec ...` 류는 **PowerShell**에서, 공격/스크립트는 WSL에서.

### B-4. `portcheck2.sh: line 2: set:: invalid option name`
- **원인**: `/mnt/d`의 스크립트가 **CRLF(윈도 줄바꿈)** — bash가 `\r`를 못 읽음.
- **해결**: `sed 's/\r$//' 원본 > /tmp/portcheck2.sh` 후 실행.

---

## C. 탐지 파이프라인

### C-1. 공격① 로그가 security.log에 안 보임
- **원인**: 실제 돌아가는 게시판은 저장소 `flask-board`(192.168.3.7:5000)인데 **옛 폴더 `_7_board_test/logs/security.log`**를 보고 있었음. 로그는 `flask-board/logs/security.log`에 정상 기록됨.
- **교훈**: "어느 인스턴스가 포트를 서빙하는지" 먼저 확인.

### C-2. Wazuh 네이티브 Active Response 미작동
- **원인 1**: `ossec.conf`의 `<active-response>` 블록이 **주석 처리(OFF)**.
- **원인 2**: netsh AR을 넣어도 **Agent가 Flask `security.log`를 수집하지 않아**(localfile 미설정) rule 100211이 안 떠 AR 트리거 없음.
- **결론**: Wazuh 네이티브 AR 대신 **app-level 자동 차단**(n8n/Graylog 자동화 → `/api/admin/block`, 동일 IP 5회 실패)으로 충족. 403 응답 + `/api/admin/blocked`로 증명.

### C-3. "Suricata가 없다"는 오판
- **증상**: Windows/Docker 어디에도 Suricata 없음 → ③ 불가로 판단.
- **진실**: Suricata는 **Kali WSL 내부**(`/usr/bin/suricata`, `/etc/suricata`, `eve.json`)에 설치돼 있었음.
- **교훈**: 네트워크 공격 탐지 도구는 **센서(Kali) 쪽**도 확인.

### C-4. Kali eve.json이 Wazuh로 안 감
- **원인**: Kali에 **Wazuh 에이전트가 없어** eve.json을 Manager로 보낼 주체가 없음.
- **해결**: Kali에 wazuh-agent 4.9.0 설치(`WAZUH_MANAGER=192.168.3.7`), ossec.conf에 `/var/log/suricata/eve.json` localfile 추가 → agent 002(kali-suricata) 등록. → Wazuh rule 86601로 수집.

### C-5. Suricata systemd 서비스가 바로 죽음
- **증상**: `systemctl` 상태 `deactivating (Result: protocol)`.
- **원인**: 서비스 유닛의 notify 프로토콜 불일치로 시작 직후 종료.
- **해결**: systemd 대신 **수동 데몬** 실행 `suricata -c /etc/suricata/suricata.yaml -i eth0 -D`. (`pgrep -a suricata`로 확인)

### C-6. n8n `/webhook/vuln-scan` 404
- **증상**: `The requested webhook "POST vuln-scan" is not registered.`
- **원인**: 해당 워크플로가 **Active(게시) 상태 아님**.
- **해결**: n8n UI에서 워크플로(`2 - kali-hping-기본테스트`, 웹훅 경로 `vuln-scan`) **Active 토글** ON.

### C-7. relocate_environment.ps1 실패 (`primary ... not found`)
- **증상**: 감사/적용 스크립트가 `TypeError: Cannot read properties of undefined (reading 'nodes')`.
- **원인**: 스크립트가 원작자 워크플로 ID(`xmRPw40G5rzskSwx`, `fl7ouxwqMiENm56O`)를 **하드코딩**하는데, 현재 n8n의 9개 워크플로는 ID가 전부 다름.
- **결론**: 이 환경엔 스크립트가 안 맞음. 억지로 `-Apply`하면 실패. 필요한 워크플로는 **Active 토글**로 개별 활성화해 해결.

### C-8. Graylog `login_failed` 검색 0건
- **원인**: `login_failed`는 **파일 로그 표현**. Graylog로 가는 GELF 메시지 문구는 `failed login for '...' from <ip>`, 필드 `rule=login-bruteforce`.
- **해결**: 검색어를 **`203.0.113.200`(공격 IP)** 또는 `rule:login-bruteforce` / `"failed login"`로.

### C-9. FIM(웹셸) 탐지가 안 뜸
- **증상 1**: 대시보드에 100220/100221/100222 없음.
- **원인 1**: 대시보드가 **엉뚱한 에이전트로 필터**됨. FIM은 board-host(001), Suricata는 kali-suricata(002). 에이전트 전환 필요.
- **증상 2**: 에이전트 바꿔도 없음. alerts.log엔 있으나 전부 **옛 타임스탬프**.
- **원인 2**: 에이전트는 **`_7_board_test\templates`를 실시간 감시** 중인데 테스트는 `flask-board\templates`에서 함(미감시). 게다가 룰 100221 경로를 `flask-board`로 바꿔 **_7_board_test 매칭까지 깨뜨림**.
- **해결**: 룰을 `_7_board_test`로 되돌리고, **에이전트가 감시하는 `_7_board_test\templates`에서** test.php 생성/수정/삭제 → 즉시 탐지(100220 lv12 웹셸 / 100222 삭제) + Discord 알림.
- **교훈**: FIM은 **에이전트가 실제 감시하는 경로**와 **룰의 경로 정규식**이 일치해야 함.

---

## 공통 교훈
1. 변경/명령 전에 **"어느 인스턴스/경로/에이전트"**인지 먼저 확인 (게시판·로그·감시 대상).
2. 탐지가 안 뜨면 **수집(agent localfile) → Manager(rule) → Indexer → Dashboard** 순서로 끊긴 지점을 짚는다.
3. 도구 실행 위치 구분: **docker=PowerShell, 공격/스크립트=WSL(bash)**.
4. 모든 환경 설정 변경은 **본인 PC 로컬**. 비밀값은 캡처·커밋 금지.
