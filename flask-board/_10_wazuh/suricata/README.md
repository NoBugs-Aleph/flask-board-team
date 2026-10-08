# 공격 ③ Nmap·SQLmap — Suricata → Wazuh 연동

흐름: Kali → (Nmap/SQLmap) → 대상 서버 → Suricata(Linux VM) → eve.json → Wazuh Agent → Manager(룰 100240/100241) → Active Response(netsh, board-host) → Dashboard

허가된 실습 환경에서만 실행한다.

## 1. Suricata VM 준비
1. Linux VM에 `sudo apt install suricata` 후 `sudo suricata-update`.
2. `suricata.yaml`: `HOME_NET`을 대상 서버 IP로, `af-packet`의 `interface`를 트래픽을 보는 NIC로 설정하고 `rule-files`에 `local.rules` 추가.
3. `local.rules`를 `/var/lib/suricata/rules/`에 복사 후 `sudo suricata -T -c /etc/suricata/suricata.yaml` 로 검사, `sudo systemctl restart suricata`.
4. 트래픽이 이 VM을 지나가거나 미러링돼야 한다(대상 서버와 같은 VMnet/브리지, 또는 대상 서버가 이 VM).

## 2. Wazuh Agent
VM에 Wazuh Agent(4.9.0)를 설치해 Manager에 등록하고 `wazuh-agent-ossec-snippet.xml` 내용을 추가한 뒤 Agent 재시작.

## 3. Manager (이 PC의 컨테이너)
```powershell
docker exec wazuh-manager /var/ossec/bin/wazuh-analysisd -t
docker exec wazuh-manager /var/ossec/bin/wazuh-control restart
```
룰은 `wazuh-manager-rules-snippet.xml`, 차단은 `wazuh-manager-active-response-snippet.xml` 참고.
차단은 board-host(Windows)에서 `netsh`로 수행한다. Manager `global`의 `white_list`에 Kali IP가 있으면 차단되지 않는다.

## 4. 테스트와 확인
Kali에서(허가된 대상에만):
```bash
nmap -sS -p 1-1000 <대상IP>
sqlmap -u "http://<대상IP>:5000/api/posts?id=1" --batch
```
확인:
- VM: `sudo tail -f /var/log/suricata/eve.json | grep '"event_type":"alert"'`
- Manager: `docker exec wazuh-manager grep -E '"id":"10024[01]"' /var/ossec/logs/alerts/alerts.json | tail -3`
- 차단: `docker exec wazuh-manager tail /var/ossec/logs/active-responses.log`, 대상 서버 `netsh advfirewall firewall show rule name=all | findstr -i wazuh`
- Dashboard: Threat Hunting에서 `rule.id:(100240 OR 100241)` 필터, 시간 범위를 테스트 시각으로 지정해 캡처.
