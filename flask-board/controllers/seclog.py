"""보안 로그 파일 기록 — Wazuh 에이전트가 읽어 가는 호스트 로그.

GELF(gelf.py)는 앱이 Graylog 로 '직접' 보내는 길이고,
이 파일은 호스트에 설치된 Wazuh 에이전트가 '읽어 가는' 길이다(센서가 하나 더 붙는다).

형식(한 줄 = 사건 1건):
  2026-09-17 14:03:21.457 login_failed user=victim src_ip=203.0.113.50

주의 두 가지
  ① 타임스탬프에 밀리초(.mmm)가 있어야 한다. 없으면 Wazuh 내장 프리디코더
     (windows-date-format)가 먼저 잡아가서 커스텀 디코더에 도달하지 못한다(미탐).
  ② 사용자 입력(username)을 그대로 쓰면 '로그 인젝션'이 된다. 아이디에 줄바꿈을 넣어
     가짜 로그 줄을 만들 수 있으므로 공백·개행 문자를 '_' 로 바꾸고 길이를 자른다.
"""
from flask import current_app
from security_log import write_host_event


def write_seclog(event, user, src_ip):
  """event: login_failed | login_success | login_locked"""
  write_host_event(current_app.config.get('SECURITY_LOG_PATH'), event, src_ip, user=user)


def write_404log(src_ip, path):
  """404 웹 스캔 신호 — Graylog 외에 Wazuh에서도 수집한다."""
  write_host_event(current_app.config.get('SECURITY_LOG_PATH'), 'http_404',
                   src_ip, request_path=path)


def write_auth_fail(src_ip, path):
  """S6 API 인증 실패. 시도된 키는 기록하지 않는다."""
  write_host_event(current_app.config.get('SECURITY_LOG_PATH'), 'admin_auth_fail',
                   src_ip, request_path=path)


def write_gold_access(user, src_ip):
  """S9 골드 열람. 자료 본문은 기록하지 않는다."""
  write_seclog('gold_access', user, src_ip)
