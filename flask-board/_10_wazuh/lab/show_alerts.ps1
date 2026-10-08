# Manager 의 alerts.json 에서 실습 관련 알림만 요약 출력 (컨테이너 wazuh-manager 사용)
# 사용: .\show_alerts.ps1 [-Rules 100210,100211] [-Last 10]
param(
  [string[]]$Rules = @('100210','100211','100220','100221','100222','550','553','554','555'),
  [int]$Last = 10
)
$py = @'
import sys, json
rules = set(sys.argv[1].split(',')); last = int(sys.argv[2]); out = []
for l in open('/var/ossec/logs/alerts/alerts.json', errors='ignore'):
    try: j = json.loads(l)
    except Exception: continue
    if j['rule']['id'] not in rules: continue
    d = j.get('data', {}); s = j.get('syscheck', {})
    out.append('%s | rule %s (L%s) | %s | agent=%s | srcip=%s user=%s | path=%s event=%s uid=%s mtime=%s perm=%s' % (
        j['timestamp'][:19], j['rule']['id'], j['rule']['level'], j['rule']['description'],
        j['agent']['name'], d.get('srcip', '-'), d.get('dstuser', s.get('uname_after', '-')),
        s.get('path', '-'), s.get('event', '-'), s.get('uname_after', '-'), s.get('mtime_after', '-'),
        s.get('perm_after', '-')))
print('\n'.join(out[-last:]))
'@
$py | docker exec -i wazuh-manager python3 - ($Rules -join ',') $Last
