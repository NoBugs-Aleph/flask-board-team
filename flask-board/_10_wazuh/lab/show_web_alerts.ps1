# Gobuster/Hydra 실습용 알림 요약 (컨테이너 wazuh-manager 사용)
# 사용: .\show_web_alerts.ps1 [-Ip 172.17.144.170] [-Last 5]
param(
  [string]$Ip = '172.17.144.170',
  [int]$Last = 5
)
$py = @'
import sys, json
ip = sys.argv[1]; last = int(sys.argv[2])
rows = []
for l in open('/var/ossec/logs/alerts/alerts.json', errors='ignore'):
    l = l.strip()
    if not l.startswith('{'): continue
    try: j = json.loads(l)
    except Exception: continue
    if j['rule']['id'] not in ('100210','100211','100230','100231'): continue
    d = j.get('data', {})
    if ip and d.get('srcip') != ip: continue
    rows.append((j['rule']['id'], j))
from collections import Counter
c = Counter(r[0] for r in rows)
names = {'100210':'로그인 실패','100211':'브루트포스(T1110)',
         '100230':'404 경로탐색','100231':'디렉터리 스캔(T1595.003)'}
print('=== src_ip=%s 집계 ===' % ip)
for rid in ('100230','100231','100210','100211'):
    print('  rule %s %-22s : %d' % (rid, names[rid], c.get(rid, 0)))
print('=== 샘플(각 최근 %d건) ===' % last)
for rid in ('100231','100211'):
    sample = [j for (r, j) in rows if r == rid][-last:]
    for j in sample:
        d = j['data']
        print('  %s | rule %s L%s | srcip=%s user=%s url=%s' % (
            j['timestamp'][:19], j['rule']['id'], j['rule']['level'],
            d.get('srcip','-'), d.get('dstuser','-'), d.get('url','-')))
'@
$py | docker exec -i wazuh-manager python3 - $Ip $Last
