# 공격 ③ Nmap·SQLmap — Suricata → Wazuh 연동 (WSL Kali 구성)

흐름: Kali(WSL)에서 Nmap/SQLmap 실행 → Kali의 Suricata가 트래픽 감시 → `C:\suricata-logs\eve.json` 기록
→ Windows Wazuh Agent(board-host)가 수집 → Manager 룰 100240/100241 → Active Response(`netsh`)로 Kali IP 차단 → Dashboard

허가된 실습 환경(본인 PC의 게시판)에서만 실행한다.

기본 값: Kali IP `172.17.144.170`, Windows(게시판) IP `172.17.144.1`, 게시판 포트 5000. IP는 재부팅하면 바뀔 수 있으니
Kali에서 `ip -4 addr show eth0`, Windows에서 `ipconfig`(WSL 어댑터)로 확인한다.

## 1. Windows: 로그 폴더 만들기 (PowerShell)
```powershell
New-Item -ItemType Directory -Force C:\suricata-logs
```

## 2. Kali(WSL): 규칙 복사 후 Suricata 실행
저장소를 Windows에서 연 PowerShell에서 Kali로 들어간다.
```powershell
wsl -d kali-linux
```
Kali 안에서(저장소 경로의 `local.rules`를 복사; 경로는 본인 PC에 맞게 수정):
```bash
sudo cp "/mnt/c/Users/user/Desktop/flask-board-team/flask-board-team/flask-board/_10_wazuh/suricata/local.rules" /etc/suricata/lab.rules
sudo suricata -T -c /etc/suricata/suricata.yaml -S /etc/suricata/lab.rules -l /tmp
```
`Configuration provided was successfully loaded`가 나오면 검사 통과. Wazuh JSON 디코더는 필드가 너무 많은 줄을 못 읽으므로(`Too many fields for JSON decoder`), eve-log의 `stats` 항목만 뺀 설정 복사본을 만든다(원본은 그대로):
```bash
sed '/^        - stats:$/,/null-values/d' /etc/suricata/suricata.yaml > /tmp/lab.yaml
```
이어서 실행(이 터미널은 계속 켜 둔다):
```bash
sudo suricata -c /tmp/lab.yaml -i eth0 -S /etc/suricata/lab.rules -l /mnt/c/suricata-logs
```
`-S`는 이 규칙 파일만 사용한다는 뜻이다. 중지는 `Ctrl+C`.

## 3. Windows: Agent가 eve.json 읽게 하기 (관리자 PowerShell)
`wazuh-agent-ossec-snippet.xml`의 `<localfile>` 블록을 `C:\Program Files (x86)\ossec-agent\ossec.conf`의 `</ossec_config>` 바로 위에 붙여 넣고 저장한 뒤:
```powershell
Restart-Service -Name WazuhSvc
```

## 4. Manager
이 저장소 작업에서 룰(100240, 100241)과 자동 차단 설정은 이미 적용돼 있다. 다른 PC라면
`wazuh-manager-rules-snippet.xml`, `wazuh-manager-active-response-snippet.xml`을 추가하고 검사 후 재시작한다.
```powershell
docker exec wazuh-manager /var/ossec/bin/wazuh-analysisd -t
docker exec wazuh-manager /var/ossec/bin/wazuh-control restart
```

## 5. 테스트 (Kali, 본인 게시판에만)
```bash
nmap -sS -p 1-1000 172.17.144.1
sqlmap -u "http://172.17.144.1:5000/api/posts?id=1" --batch
```
`id` 파라미터가 없는 경로여도 SQLmap User-Agent 룰(sid 9000002)로 탐지된다.

## 6. 확인
- eve.json 기록: Windows PowerShell `Select-String '"event_type":"alert"' C:\suricata-logs\eve.json | Select -Last 3`
- Wazuh 경보: `docker exec wazuh-manager grep -E '"id":"10024[01]"' /var/ossec/logs/alerts/alerts.json`
- 자동 차단: `docker exec wazuh-manager tail /var/ossec/logs/active-responses.log`
- Windows 방화벽 규칙: `netsh advfirewall firewall show rule name=all | findstr /i wazuh`
- Dashboard: Threat Hunting에서 `rule.id:(100240 OR 100241)`, 시간 범위를 테스트 시각으로 지정해 캡처.

## 주의
- 차단되면 Kali→Windows 접속이 10분간 막힌다(정상). 10분 뒤 풀리며, 급하면 Windows에서 Wazuh가 만든 방화벽 규칙을 삭제한다.
- 룰이 발동하지 않으면 3번 Agent 재시작 여부와 `C:\suricata-logs\eve.json`에 줄이 쌓이는지부터 확인한다.
