"""Flask와 독립 실행 봇이 공유하는 Wazuh 호스트 로그 기록."""
import re
from datetime import datetime
from pathlib import Path


_UNSAFE = re.compile(r'[\s\x00-\x1f\x7f]+')


def clean(value, limit=64):
    return _UNSAFE.sub('_', str(value or '-'))[:limit] or '-'


def write_host_event(path, event, src_ip, *, user=None, request_path=None):
    """밀리초와 한 줄 형식을 유지하며, 파일 장애는 요청 처리를 막지 않는다."""
    if not path:
        return
    first_hop = str(src_ip or '').split(',', 1)[0].strip()
    now = datetime.now()
    stamp = now.strftime('%Y-%m-%d %H:%M:%S.') + f'{now.microsecond // 1000:03d}'
    fields = []
    if user is not None:
        fields.append(f'user={clean(user)}')
    fields.append(f'src_ip={clean(first_hop, 45)}')
    if request_path is not None:
        fields.append(f'path={clean(request_path, 120)}')
    line = f'{stamp} {clean(event)} {" ".join(fields)}\n'
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('a', encoding='utf-8') as stream:
            stream.write(line)
    except (OSError, ValueError):
        pass
