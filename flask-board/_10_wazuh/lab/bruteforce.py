"""시나리오 1 — 게시판 로그인 브루트포스 시뮬레이션 (본인 로컬 게시판 대상 전용).

사용: python bruteforce.py [--user wz_test] [--ip 198.51.100.10] [--count 8]
- 같은 IP(X-Forwarded-For)로 같은 계정에 틀린 비밀번호를 반복 시도한다.
- 게시판은 실패 때마다 logs/security.log 에 login_failed 한 줄을 남기고,
  Wazuh Agent → Manager 가 rule 100210(5) → 100211(10, 120초 내 6회) 로 탐지한다.
"""
import argparse
import json
import time
import urllib.error
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument('--url', default='http://localhost:5000/api/auth/login')
ap.add_argument('--user', default='wz_test')
ap.add_argument('--ip', default='198.51.100.10')
ap.add_argument('--count', type=int, default=8)
a = ap.parse_args()

for i in range(1, a.count + 1):
  body = json.dumps({'username': a.user, 'password': f'wrong-{i}'}).encode()
  req = urllib.request.Request(a.url, body, {
      'Content-Type': 'application/json', 'X-Forwarded-For': a.ip})
  try:
    code = urllib.request.urlopen(req).status
  except urllib.error.HTTPError as e:
    code = e.code
  print(f'[{i}/{a.count}] user={a.user} src_ip={a.ip} -> HTTP {code}')
  time.sleep(0.3)
