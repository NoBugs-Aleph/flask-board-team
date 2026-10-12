# member_04 작업 진행 현황

작업자: whiteclover0542 (반소람)
작업 범위: `flask-board/member_04/` 폴더 내부만
상태: **전체 완료** ✅ (2026-10-08)

범례: ✅ 완료 · 🟡 진행중 · ⬜ 미완료

---

## 작업 순서 ① Wazuh 보안 실습
| 순서 | 할 일 | 상태 |
| --- | --- | --- |
| 0 | 준비: `flask-board/.env` 본인 값 작성 (키 생성, 미사용 공란, gitignore) | ✅ |
| 1 | Manager/Dashboard/Agent 정상·접속 확인 (agent 000/001/002 active) | ✅ |
| 2 | 수집 상태·탐지 Rule·자동 차단 설정 확인 | ✅ |
| 3 | 공격① Hydra 로그인 무차별 → 탐지·자동 차단 | ✅ |
| 4 | 공격② Nikto 웹 스캐너 → Suricata 탐지 | ✅ |
| 5 | 공격③ Nmap/SQLmap → Suricata→Wazuh 탐지 | ✅ |
| 6 | 최종 대시보드 점검 (공격별 Alert·시간대·Severity) | ✅ |
| 7 | (보너스) FIM 웹셸 테스트 → rule 100220/100222 + Discord | ✅ |

## 작업 순서 ② GitHub 협업 실습
| 순서 | 할 일 | 상태 |
| --- | --- | --- |
| 1 | `whiteclover0542` 브랜치 생성 | ✅ |
| 2 | `introduce.md` 자기소개 작성 | ✅ |
| 3~5 | 커밋 · Write 권한 · Push | ✅ |
| 6~8 | PR #3 생성 · 전달 · 조장 Merge · main 최신화 | ✅ |
| 9 | 제출 증빙 캡처 | ✅ |

---

## 완료한 일
- **② GitHub**: 브랜치→커밋→PR #3→Merge→증빙 캡처까지 전부 완료.
- **① Wazuh**: 환경·설정 확인, 공격 ①②③ 탐지, 최종 대시보드, 보너스 FIM까지 전부 캡처 완료.

## 제출 캡처 (`screanshot/`)
| 파일 | 항목 |
| --- | --- |
| `atk0_wazuh_agents_status` | ①-1 Agent 상태 |
| `atk1_hydra_1~6` | ①-2 Hydra + ①-3 자동차단 (wazuh·n8n·게시판·discord·차단IP·graylog) |
| `atk2_nikto_wazuh` | ①-2 Nikto |
| `atk3_nmap_1_wazuh` | ①-2 Nmap/SQLmap |
| `최종대시보드` | ①-4 보안 대시보드 |
| `fim_webshell_wazuh·discord·graylog` | 보너스 FIM |
| `pr_증빙` | ② GitHub PR #3 |

## 핵심 메모 (환경/방식)
- **공격①(Hydra)**: 게시판(192.168.3.7:5000) 로그인 실패 유발 → **app-level 자동 차단**(n8n/Graylog 자동화가 `/api/admin/block` 호출, 동일 IP 5회 실패 시). 제출 증거 = 403 응답 + 차단목록 + Graylog/디스코드.
- **공격②③(Nikto·Nmap·SQLmap)**: Suricata(**Kali WSL 내부** 설치)로 탐지. Kali에 **Wazuh agent 002(kali-suricata)** 설치·등록 + `eve.json` 수집 연결 → Wazuh rule 86601. Suricata는 수동 데몬(`-i eth0 -D`)으로 실행.
- **FIM**: 에이전트가 `_7_board_test\templates`를 실시간 감시 → 거기서 `test.php` 생성/수정/삭제 → rule 100220(웹셸,lv12)/100222(삭제) + Discord 알림.
- 참고: Wazuh 네이티브 netsh AR은 미사용(app-level 자동차단으로 충족). 모든 설정 변경은 본인 PC 로컬(저장소/member_04 밖).

## 과제와 다른 점 (조장/강사 설명용)
- Fork 대신 **브랜치** 방식 / `introduce.txt` 대신 **`.md`** / 폴더 `_7_board_test`→`flask-board`.
- 자동 차단이 Wazuh 네이티브 AR이 아니라 **n8n/Graylog 자동화 + app-level 차단**.
