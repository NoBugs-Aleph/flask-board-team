# member_04 작업 진행 현황

작업자: whiteclover0542 (반소람)
작업 범위: `flask-board/member_04/` 폴더 내부만

## 이모지 범례
- ✅ 완료
- 🟡 진행중
- ⬜ 미완료

---

## 해야 할 것 (제출 항목)

### ① Wazuh 보안 실습
- Wazuh Dashboard 화면 (Manager/Agent 상태, 이벤트 수집 현황)
- 공격 3종 탐지 결과 (Hydra 무차별 대입 / Nikto·디렉터리 탐색 / Nmap·SQLmap)
- Active Response 자동 차단 결과 (출발지 IP 차단)
- 대시보드 공격별 Alert·시간대별 이벤트

### ② GitHub 협업 실습
- 개인 작업 브랜치
- `member_04/introduce.md` 자기소개
- Commit / Push 기록
- Pull Request 생성
- 조장 Merge 완료
- 최종 저장소에 member_04 파일 반영

---

## 작업 순서

### ① Wazuh 보안 실습
| 순서 | 할 일 | 상태 |
| --- | --- | --- |
| 1 | Wazuh Manager / Dashboard / Agent 정상 동작 및 접속 확인 | ⬜ |
| 2 | 로그·이벤트 수집 상태, 탐지 Rule / Active Response 설정 확인 | ⬜ |
| 3 | 공격① Hydra 로그인 무차별 대입 — 탐지 Alert·자동 차단·대시보드 확인 | ⬜ |
| 4 | 공격② Nikto·디렉터리 탐색 — 404 급증 탐지·자동 차단·대시보드 확인 | ⬜ |
| 5 | 공격③ Nmap·SQLmap (Suricata→Wazuh) — 탐지 이벤트·자동 차단·대시보드 확인 | ⬜ |
| 6 | 최종 대시보드 점검 (공격별 Alert, 출발지/대상 IP, Severity, 시간대, 차단 결과) | ⬜ |
| 7 | 제출용 화면 캡처 정리 | ⬜ |

### ② GitHub 협업 실습
| 순서 | 할 일 | 상태 |
| --- | --- | --- |
| 1 | `whiteclover0542` 로컬 브랜치 생성 | ✅ |
| 2 | `member_04/introduce.md` 자기소개 작성 (6개 항목) | ✅ |
| 3 | 소개 파일 커밋 | ✅ |
| 4 | 조장에게 저장소 Write 권한 요청 | ✅ |
| 5 | 권한 받은 뒤 `git push -u origin whiteclover0542` | ✅ |
| 6 | GitHub에서 PR 생성 (PR #3) | ✅ |
| 7 | PR URL 조장에게 전달 | ✅ |
| 8 | 조장 Merge (PR #3 merged) 후 main 최신화 | ✅ |
| 9 | 제출 증빙 캡처 (PR Files changed / Merged 표시) | ⬜ |

---

## 완료한 일
- `whiteclover0542` 브랜치 생성 (로컬)
- `member_04/introduce.md` 작성: 이름/닉네임/역할/관심분야/기술/한마디 6개 항목 채움
- 커밋 완료: `62efaf9 docs: add whiteclover0542 introduction`

## 막힌 것 / 메모
- `git push` 시 403 발생 (`denied to whiteclover0542`) — 저장소 Write 권한 없음
  - 해결: 조직 초대 수락 + 조장이 Collaborator(Write)로 추가하거나 base permission을 Write로 변경
- 과제 예시 파일명은 `introduce.txt`이나 팀 합의로 `.md` 사용 중
