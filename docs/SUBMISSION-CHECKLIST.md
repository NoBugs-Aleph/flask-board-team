# 실습 최종 제출 체크리스트

준비 완료와 제출 완료를 구분합니다. 아래 칸은 실제 URL/화면/로그를 확인한 뒤 채웁니다. 예정 주소와 과거 캡처만으로 새 실습을 완료 처리하지 않습니다.

## GitHub 협업 실습

- [x] 조직 생성: `NoBugs-Aleph` (표시 이름 NoBugs), GitHub Free, 관리자 `myeongjundev`
- [x] 조직 원본 저장소 생성 및 업로드 — <https://github.com/NoBugs-Aleph/flask-board-team>
- [x] `flask-board`에 기존 게시판 소스 복사
- [x] 복사본 게시판 정상 실행 및 기본 기능 확인 — [검증 기록](VERIFICATION.md)
- [ ] 조원에게 저장소 주소와 [길라잡이](COLLABORATION-GUIDE.md) 공유

조직 멤버 초대는 세 조원 모두 전송 완료(2026-10-08), 수락 여부는 미확인입니다. 각자 [조직 페이지](https://github.com/NoBugs-Aleph)에 접속해 수락해야 합니다.

| 사용자 | Fork URL | 소개 파일 | PR URL | Merged/커밋 및 캡처 |
| --- | --- | --- | --- | --- |
| myeongjundev | [Fork](https://github.com/myeongjundev/flask-board-team) | member_01/introduce.txt | [PR #1](https://github.com/NoBugs-Aleph/flask-board-team/pull/1) | Merged, `73b8b5f`; 캡처 별도 확보 |
| chacha1650a | 미확인 | member_02/introduce.txt | 미확인 | 미확인 |
| shk12170-dev | 조직 저장소 브랜치에서 작업(개인 Fork 아님) | member_03/introduce.txt | [PR #5](https://github.com/NoBugs-Aleph/flask-board-team/pull/5) | Merged, `55d50ac`; 추가 PR #6 Merged(`f5e5b59`, Wazuh 실습 자료) |
| whiteclover0542 | 미확인 | member_04/introduce.txt | 미확인 | 미확인 |

- [ ] 각자의 Fork·Commit·Push·PR 기록 확인
- [ ] 조장의 PR 변경 범위·충돌 검토 및 Merge 완료
- [ ] 최종 `main`에 소개 TXT 4개 반영
- [ ] 조직 저장소 URL, 개인 Fork, PR 기록, Merge 화면, 최종 폴더 화면 제출

조장의 Fork 제출이 생략 가능한지는 강사 요구사항을 확인합니다. 표의 모든 사용자를 포함하는 기본 제출 기준으로 준비합니다.

## Wazuh 보안 실습

2026-10-08 실습에서 공격 3종을 모두 실행해 탐지·자동 차단을 확인했습니다. 환경: Kali(WSL, `172.17.144.170`) → 게시판(`172.17.144.1:5000`). 보드·로그·Wazuh 감시 경로·공격 스크립트를 모두 `flask-board-team\flask-board`로 이전했습니다(공격 ①② Flask 로그 기반, 공격 ③ Suricata 기반).

| 제출 항목 | 확인 결과 (2026-10-08) | 제출 증빙 |
| --- | --- | --- |
| Manager/Agent 상태 | Manager 서비스 정상, Agent 001 board-host Active | 상태 화면, Agent 이름/ID |
| 보안 이벤트 수집 | security.log·webaccess.log·fast.log·eve.json 수집 확인 | 이벤트 상세, 발생 시간 |
| 공격 ① Hydra 무차별 대입 | **확인**: rule 100210→**100211**(T1110), srcip 172.17.144.170 | 로그인 실패 경보, Wazuh 이벤트 화면 |
| 공격 ② Nikto·디렉터리 탐색(gobuster) | **확인(18:46)**: rule 100230(404 다수)→**100231**(디렉터리 스캔 의심) | webaccess 404, rule.id 100231 화면 |
| 공격 ③ Nmap | **확인**: Suricata sid 9000001→rule **100252** | rule.id 100252 화면 |
| 공격 ③ SQLmap | **확인**: Suricata sid 9000002/9000003→rule **100251** | rule.id 100251 화면 |
| Active Response 자동 차단 | **확인(3종 모두)**: rule 657 netsh add, Windows 방화벽 `WAZUH ACTIVE RESPONSE BLOCKED IP`(Inbound/Block/172.17.144.170), Kali→게시판 curl 타임아웃, 600초 후 자동 해제 | AR 로그(657), 방화벽 규칙, 차단 전후 curl |
| 공격별/시간대별 대시보드 | 공격별 rule.id 필터 + 시간대별 그래프 캡처 | 필터/시간 범위/경보 그래프 |
| (보너스) FIM 웹셸 | rule 100220/100221/100222, FIM 감시 경로 `flask-board\templates` | test.php 생성/삭제 이벤트, 3채널 알림 |

- [x] 허가된 실습 대상에서 공격 시나리오 3종 실행 및 탐지 확인 (Hydra 100211 / gobuster 100231 / Nmap 100252 · SQLmap 100251)
- [x] 자동 차단 실행 기록(rule 657)과 실제 차단 결과(방화벽 규칙 + Kali curl 타임아웃)를 연결해 확인
- [x] Wazuh 화면에서 현재 Manager/Agent 상태와 보안 이벤트 확인
- [ ] 공격별 Alert, 시간대별 이벤트 발생 화면 최종 캡처 제출

수집되지 않는 팀원 PC는 [flask-board/docs/WAZUH-LLM-VERIFICATION-GUIDE.md](../flask-board/docs/WAZUH-LLM-VERIFICATION-GUIDE.md) 순서대로 진단합니다. n8n 성공 표시만으로 Wazuh 수집·공격 탐지·자동 차단이 모두 검증된 것은 아닙니다.
