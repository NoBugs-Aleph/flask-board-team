"""네트워크·운영 볼륨 없이 Wazuh 4.9.0의 추가 디코더/규칙을 검증한다."""
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = '\n'.join((
    '2026-10-12 10:22:00.123 http_404 src_ip=192.0.2.50 path=/missing',
    '2026-10-12 10:22:00.124 admin_auth_fail src_ip=192.0.2.51 path=/api/security/events',
    '2026-10-12 10:22:00.125 gold_access user=synthetic-gold src_ip=192.0.2.52',
    '2026-10-12 10:22:00.126 priv_unauthorized_admin user=synthetic-admin src_ip=192.0.2.53',
)) + '\n'


def main():
    command = ['docker', 'run', '--rm', '-i', '--network', 'none', '--entrypoint', '/bin/sh']
    for folder in ('decoders', 'rules'):
        source = ROOT / 'wazuh' / folder / 'flask_board_signals.xml'
        command.extend(['--mount', f'type=bind,source={source},target=/var/ossec/etc/{folder}/flask_board_signals.xml,readonly'])
    command.extend(['wazuh/wazuh-manager:4.9.0', '-c', (
        'set -e\n'
        'cp -a /var/ossec/data_tmp/permanent/var/ossec/. /var/ossec/\n'
        'cp -a /var/ossec/data_tmp/exclusion/var/ossec/. /var/ossec/\n'
        '/var/ossec/bin/wazuh-analysisd -t\n'
        '/var/ossec/bin/wazuh-db\n'
        '/var/ossec/bin/wazuh-analysisd\n'
        'attempt=0\n'
        'while [ ! -S /var/ossec/queue/sockets/logtest ]; do\n'
        '  attempt=$((attempt + 1))\n'
        '  if [ "$attempt" -ge 40 ]; then cat /var/ossec/logs/ossec.log; exit 1; fi\n'
        '  sleep 0.25\n'
        'done\n'
        'exec /var/ossec/bin/wazuh-logtest\n'
    )])
    result = subprocess.run(command, input=SAMPLES, text=True, encoding='utf-8',
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    print(result.stdout)
    rules = re.findall(r"id: '(10023[0-3])'", result.stdout)
    if result.returncode or rules != ['100230', '100231', '100232', '100233']:
        raise SystemExit('FAIL: 네 신호의 기대 규칙이 모두 일치하지 않았습니다.')
    print('PASS: Wazuh 4.9.0 rules 100230, 100231, 100232, 100233')


if __name__ == '__main__':
    main()
