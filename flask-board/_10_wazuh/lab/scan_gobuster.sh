#!/usr/bin/env bash
# 시나리오 1 — Gobuster 디렉터리 스캔 (Kali/WSL 에서 실행, 본인 로컬 게시판 대상 전용)
# 사용: wsl -d kali-linux -- bash scan_gobuster.sh [TARGET_URL] [WORDLIST]
TARGET="${1:-http://172.17.144.1:5000}"
WORDLIST="${2:-/usr/share/wordlists/dirb/common.txt}"
echo "[*] gobuster dir -> $TARGET (wordlist: $WORDLIST)"
gobuster dir -u "$TARGET" -w "$WORDLIST" -t 30 -q \
  --no-error -s 200,204,301,302,307,401,403 -b "" 2>/dev/null | head -40
echo "[*] done"
