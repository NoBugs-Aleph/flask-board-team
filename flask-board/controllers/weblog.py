"""웹 액세스 로그 파일 기록 — Wazuh 에이전트가 읽어 가는 호스트 로그.

seclog.py(인증 사건)와 같은 길을 '웹 요청'에 대해 하나 더 연다. 디렉터리 스캐닝
(gobuster·dirbuster)은 없는 경로에 404 를 대량 유발하는데, 이 흔적을 호스트 파일에
남겨야 Wazuh 가 읽어 룰(같은 IP 가 단시간에 404 다수)로 탐지할 수 있다.

형식(한 줄 = 요청 1건):
  2026-10-06 14:03:21.457 web_access src_ip=172.17.144.170 method=GET path=/admin code=404

주의
  ① 타임스탬프 밀리초(.mmm)가 있어야 커스텀 디코더에 도달한다(seclog 와 동일 이유).
  ② path 는 사용자 입력이므로 공백·제어문자를 '_' 로 바꾸고 길이를 자른다(로그 인젝션 방지).
"""
import os
import re
from datetime import datetime

from flask import current_app

_UNSAFE = re.compile(r'[\s\x00-\x1f\x7f]+')


def _clean(value, limit=120):
  text = _UNSAFE.sub('_', str(value or '-'))
  return text[:limit] or '-'


def write_weblog(src_ip, method, path, code):
  """웹 요청 1건을 webaccess.log 에 이어 쓴다(실패해도 요청 흐름을 막지 않는다)."""
  logpath = current_app.config.get('WEBACCESS_LOG_PATH')
  if not logpath:
    return
  first_hop = str(src_ip or '').split(',')[0].strip()
  now = datetime.now()
  stamp = now.strftime('%Y-%m-%d %H:%M:%S.') + f'{now.microsecond // 1000:03d}'
  line = (f'{stamp} web_access src_ip={_clean(first_hop, 45)} '
          f'method={_clean(method, 8)} path={_clean(path)} code={code}\n')
  try:
    os.makedirs(os.path.dirname(logpath), exist_ok=True)
    with open(logpath, 'a', encoding='utf-8') as f:
      f.write(line)
  except OSError:
    pass
