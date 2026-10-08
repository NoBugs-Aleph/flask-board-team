# ============================================================================
#  미니실습 제출 캡처 도우미 (Gobuster · Hydra · Wazuh)
#  실행:  cd C:\Users\user\Python-Lab-ALeph-T\_10_wazuh\lab ;  .\capture_all.ps1
#
#  이 스크립트는 공격 → 탐지를 순서대로 돌리면서, 캡처할 때마다 멈춥니다.
#  화면에 "📸 지금 스크린샷 ...  (Enter)" 가 보이면 그 창을 캡처하고 Enter 를 누르세요.
#  총 5장(①~⑤)을 찍으면 됩니다. ⑥⑦ 은 문서라 캡처 불필요.
# ============================================================================
chcp 65001 > $null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'

$LAB   = "C:\Users\user\Python-Lab-ALeph-T\_10_wazuh\lab"
$BOARD = "C:\Users\user\Desktop\Python-aleph-sh\Python-Lab-ALeph-T\_7_board_test"
$KALI  = "172.17.144.170"
$TGT   = "172.17.144.1"
Set-Location $LAB

function Pause-Shot($n, $msg) {
  Write-Host ""
  Write-Host ("  📸 지금 [$n] 스크린샷: $msg") -ForegroundColor Yellow
  Read-Host "     (캡처 후 Enter)"
}
function Title($t) { Write-Host ""; Write-Host ("="*70) -ForegroundColor Cyan; Write-Host "  $t" -ForegroundColor Cyan; Write-Host ("="*70) -ForegroundColor Cyan }

# ── 준비: 차단/계정 초기화 + 자동차단(n8n) 잠시 정지 ──
Title "준비 — 차단목록/계정 초기화, n8n(자동차단) 정지"
python lab_dbtool.py reset
docker stop n8n | Out-Null
Write-Host "  n8n 정지 완료 (깨끗한 탐지 캡처용). 끝나면 자동으로 다시 켭니다."

# ── ① 디렉터리 스캔 (Gobuster) ──
Title "① Gobuster 디렉터리 스캔 실행"
Write-Host "  Kali 에서 gobuster 가 경로를 훑습니다(1~2분). 결과가 멈추면 캡처하세요."
wsl -d kali-linux -- gobuster dir -u "http://$TGT`:5000" -w /usr/share/wordlists/dirb/common.txt -t 20 -q --no-error
Pause-Shot "①" "위 gobuster 실행 결과 화면"

# ── ② 웹 액세스 로그 연속 요청 ──
Title "② 웹 서버 액세스 로그 — 동일 IP 404 연속"
Get-Content "$BOARD\logs\webaccess.log" | Select-String "src_ip=$KALI" | Select-Object -Last 25
Pause-Shot "②" "위 webaccess.log (code=404 연속) 화면"

# ── ③ Wazuh 스캔 Alert 집계 ──
Title "③ Wazuh 디렉터리 스캔 Alert (rule 100231)"
& "$LAB\show_web_alerts.ps1" -Ip $KALI
Pause-Shot "③" "위 100230/100231 집계 + 샘플 화면"

# ── ④ 브루트포스 (Hydra) ──
Title "④ Hydra 웹 브루트포스 실행"
python lab_dbtool.py reset | Out-Null
Write-Host "  Hydra 가 wz_test 계정에 사전 대입(10초). 401 ERROR 가 뜨는 게 정상입니다(교재 동일)."
$mnt  = "/mnt/c/Users/user/Python-Lab-ALeph-T/_10_wazuh/lab/scan_hydra.sh"
$pwsl = "/mnt/c/Users/user/Python-Lab-ALeph-T/_10_wazuh/lab/wzpass.txt"
wsl -d kali-linux -- bash -c "tr -d '\r' < '$pwsl' > /tmp/wzpass.txt; rm -f /tmp/hydra.restore; tr -d '\r' < '$mnt' > /tmp/h.sh; timeout 10 bash /tmp/h.sh"
wsl -d kali-linux -- bash -c "pkill -9 hydra 2>/dev/null; true" | Out-Null
Write-Host ""
Write-Host "  --- Wazuh 브루트포스 탐지 집계 ---" -ForegroundColor Green
& "$LAB\show_web_alerts.ps1" -Ip $KALI
Pause-Shot "④" "위 Hydra 실행 + 100210/100211 집계 화면"

# ── ⑤ 반복 로그인 실패 로그 ──
Title "⑤ 반복 로그인 실패 로그 (security.log)"
Get-Content "$BOARD\logs\security.log" | Select-String "user=wz_test src_ip=$KALI" | Select-Object -Last 25
Pause-Shot "⑤" "위 security.log (login_failed 반복) 화면"

# ── ⑥⑦ 문서 열기 ──
Title "⑥ 이벤트 분석 요약 · ⑦ 식별정보 표 — 보고서 문서"
$doc = "$LAB\submission\제출_Gobuster_Hydra_Wazuh탐지.md"
Write-Host "  아래 보고서의 6절(분석요약)·7절(표) 이 제출항목 ⑥⑦ 입니다. 문서를 엽니다."
Start-Process $doc
Write-Host "  (파일: $doc)"

# ── 마무리: n8n 복구 ──
Title "마무리 — n8n(자동차단) 재가동 + 상태 정리"
docker start n8n | Out-Null
python lab_dbtool.py reset
Write-Host ""
Write-Host "  ✅ 완료! 캡처 ①~⑤ 가 준비됐고, ⑥⑦ 은 문서입니다." -ForegroundColor Green
Write-Host "  캡처 이미지는 원하는 폴더에 저장하세요. 증적 텍스트는 submission 폴더에 있습니다."
Write-Host "CAPTURE_SCRIPT_DONE"
