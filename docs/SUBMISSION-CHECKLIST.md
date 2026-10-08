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
| shk12170-dev | 조직 저장소 브랜치에서 작업(개인 Fork 아님) | member_03/introduce.txt | [PR #5](https://github.com/NoBugs-Aleph/flask-board-team/pull/5) | Merged, `55d50ac`; 추가 [PR #6](https://github.com/NoBugs-Aleph/flask-board-team/pull/6) Merged(Wazuh 실습 자료), `f5e5b59` |
| whiteclover0542 | 미확인 | member_04/introduce.txt | 미확인 | 미확인 |

- [ ] 각자의 Fork·Commit·Push·PR 기록 확인
- [ ] 조장의 PR 변경 범위·충돌 검토 및 Merge 완료
- [ ] 최종 `main`에 소개 TXT 4개 반영
- [ ] 조직 저장소 URL, 개인 Fork, PR 기록, Merge 화면, 최종 폴더 화면 제출

조장의 Fork 제출이 생략 가능한지는 강사 요구사항을 확인합니다. 표의 모든 사용자를 포함하는 기본 제출 기준으로 준비합니다.

## Wazuh 보안 실습

원본 프로젝트에서 로그인 경보와 FIM 이벤트를 확인한 기록/캡처가 포함되어 있습니다. 이를 팀원 PC의 수집 성공이나 이번 공격 3종의 전체 검증으로 간주하지 않습니다. 새 테스트에는 PC/Agent·테스트 시간·rule.id·차단 근거를 함께 남깁니다.

환경: Kali(WSL, `172.17.144.170`) → Windows 게시판(`172.17.144.1`). 공격 ①② Flask 로그 기반(Agent 직접 수집), 공격 ③ Suricata 기반.

| 제출 항목 | 현재 근거와 남은 확인 | 제출 증빙 |
| --- | --- | --- |
| Manager/Agent 상태 | 2026-10-08 확인: Manager 서비스 정상, Agent 001 board-host Active | 상태 화면, Agent 이름/ID |
| 보안 이벤트 수집 | fast.log·eve.json·security.log·webaccess.log 수집 확인 | 이벤트 상세, 발생 시간 |
| 공격 ① Hydra 무차별 대입 | 룰 100210/100211 구성됨; 이번 실습 재실행·탐지 대응 미확인 | 테스트 시간, 로그인 실패 경보, 출발지 |
| 공격 ② Nikto·디렉터리 탐색 | 룰 100230/100231 구성됨; 이번 Wazuh 탐지 대응 미확인 | 웹 요청 기록과 Wazuh 이벤트 |
| 공격 ③ Nmap | **확인(2026-10-08 17:02, 17:25)**: 룰 100252 발동, srcip 172.17.144.170 | Dashboard rule.id 100252 화면 |
| 공격 ③ SQLmap | Suricata 탐지(sid 9000002/9000003)·룰 100251 구성됨; 최종 차단 재확인 필요 | 각 도구 실행과 대응 이벤트 |
| Active Response 자동 차단 | **확인(Nmap)**: netsh add srcip=172.17.144.170, 방화벽 BLOCK 규칙 생성, Kali→게시판 curl 타임아웃, 600초 후 자동 해제 | AR 로그(rule 657), 방화벽 규칙, 차단 전후 curl |
| 공격별/시간대별 대시보드 | 이번 테스트 시간 범위로 캡처 필요 | 필터/시간 범위/경보 그래프 |

- [x] 공격 ③ Nmap: 탐지(100252) + 자동 차단(netsh, 방화벽 규칙) + 실제 접속 차단 확인
- [ ] 공격 ③ SQLmap: 룰 100251 탐지·차단 재확인
- [ ] 공격 ① Hydra: 룰 100211 탐지·차단 확인
- [ ] 공격 ② Nikto/gobuster: 룰 100231 탐지·차단 확인
- [ ] Wazuh 화면에서 현재 Manager/Agent 상태와 보안 이벤트 확인
- [ ] 공격별 Alert, 시간대별 이벤트 발생 화면 제출

수집되지 않는 팀원 PC는 [flask-board/docs/WAZUH-LLM-VERIFICATION-GUIDE.md](../flask-board/docs/WAZUH-LLM-VERIFICATION-GUIDE.md) 순서대로 진단합니다. n8n 성공 표시만으로 Wazuh 수집·공격 탐지·자동 차단이 모두 검증된 것은 아닙니다.
