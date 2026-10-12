# 2026-10-12 게시판·Wazuh·Suricata 변경 현황

작성일: 2026-10-12, Asia/Seoul. 이 문서는 이번 대화에서 수행한 작업과 아직 확인하지 않은 작업을 구분합니다.
개인 PC의 상세 DB 증거는 비공개 `aleph-worklog/WORKLOG-2026-10-12.md`에 기록합니다.

## 1. 현재 상태

| 항목 | 변경 및 확인 결과 | 남은 확인 |
| --- | --- | --- |
| 개인 `flask-board` | 최신 수업의 로그·페이징 기능 이식, unittest 84개 통과 | 개인 저장소 변경은 로컬에 있으며 이번 대화에서 커밋·Push하지 않음 |
| 팀 `flask-board-team/flask-board` | 같은 기능 통합, pytest 155개 및 4 subtests 통과 | 팀원 PC에서 설치·실수집 확인 |
| 서버 포트 | 개인 MySQL 5000, 팀 SQLite 5001로 분리 | 14:23 KST 재점검에는 두 포트의 실행 서버가 없었음. 다음 실습 전에 실행 필요 |
| Wazuh Agent | Agent 001 Active, 그룹 `default, flask-board`, synchronized, Windows 서비스 Running | 개별 사건의 Indexer/Dashboard 저장은 별도 확인 |
| 로그·FIM 경로 | 개인·팀의 `security.log`, `suricata_alert.log` 총 4개와 `templates` 2개 등록 | Suricata 파일에 실제 기록이 생기는지 확인 |
| 실제 설정 원본 | `C:\Users\user\wazuh-config`의 `agent.conf`, `local_rules.xml`, `local_decoder.xml` 내용이 Manager와 일치 | 다른 PC에서는 본인 경로·Agent에 맞춤 |
| Suricata 전송 코드 | 두 로그 파일에 기록하는 전체 Python 코드를 대화에서 제공, 아래에도 보관 | 실제 `.py` 저장·Linux/WSL 실행·EVE 재생은 이번 대화에서 확인하지 않음 |

## 2. 최신 수업 반영

강사님 `Python-Lab-ALeph-T`의 최신 확인 기준은 10-11 커밋 `989f1f6`입니다.

- 404 요청을 Graylog와 Wazuh 호스트 로그에 함께 기록합니다.
- 관리자 API 인증 실패, 허가된 골드 열람, 허용목록 밖 관리자 탐지도 호스트 로그에 기록합니다.
- 로그에 밀리초·첫 프록시 IP·길이 제한·개행/제어문자 치환을 적용하고 비밀번호·토큰·API 키·본문은 남기지 않습니다.
- 앱과 봇은 `security_log.py`를 공유하며 `SECURITY_LOG_PATH`가 비면 파일 기록을 끕니다.
- 두 대시보드 목록에 20건 페이징, 머리글 정렬, 심각도 필터를 연결했습니다.
  심각도는 Critical > High > Medium > Low 순서이며 동률은 ID로 고정합니다.
- 기존 `limit/offset`, 학생·출처·검색 필터와 숫자 등급 0/1/2 및 `/gold` 페이지를 유지했습니다.
- 인시던트 갱신 시 심각도를 낮추지 않고, 종료된 사건의 이전 로그가 새 티켓에 다시 포함되는 문제를 수정했습니다.

팀 테스트 의존성은 `requirements-test.txt`에 정리했습니다. 강사 예제 테스트도 팀의 실제 API 계약에 맞췄습니다.
합성 데이터 125건으로 브라우저 페이징·정렬·필터를 확인했고 필터 결과 31건의 마지막 페이지에 11건이 표시됐습니다.
[상세 이식·실행 기록](../flask-board/docs/LESSON-UPDATES-20261012.md)과
[검증 기록](VERIFICATION.md)에 기존 결과가 있습니다.

## 3. DB 기록이 보이지 않던 문제

개인 MySQL 게시판의 `0.0.0.0:5000`과 팀 SQLite 게시판의 `127.0.0.1:5000`이 동시에 실행되고 있었습니다.
n8n의 차단 API는 성공했지만 팀 SQLite에 저장되어, 사용자가 확인한 MySQL에는 해당 IP가 없었습니다.

중복된 팀 5000 서버를 종료하고, n8n 컨테이너에서 기존 URL과 API 키로 개인 MySQL 게시판에 연결되는 것을 확인했습니다.
실제 차단 기록이 확인된 IP는 개인 게시판의 `/api/admin/block` API로 MySQL에도 반영했고 SQL로 저장을 확인했습니다.
기존 SQLite 데이터는 보존했으며 메신저 발송 워크플로를 재실행하지 않았습니다.

| 실행 목적 | 포트 | DB |
| --- | --- | --- |
| 개인 보안 실습 및 n8n 대응 API | 5000 | MySQL `my_new_board_db` |
| 팀 협업 확인 | 5001 | SQLite `instance/team-board.sqlite3` |

팀 폴더의 `python app.py` 기본 포트와 `.flaskenv`의 Flask CLI 기본 포트를 5001로 맞췄습니다.
`--port 5000` 또는 기존 `FLASK_RUN_PORT=5000`은 기본값을 덮어쓸 수 있으므로 실행 전에 확인합니다.

## 4. Wazuh 실제 설정

실제 편집 대상은 `C:\Users\user\wazuh-config\agent.conf`입니다.
Manager의 `/var/ossec/etc/shared/flask-board/agent.conf`에 반영하고 Windows Agent의 내려받은 공유 파일까지 확인했습니다.

| 구분 | Windows 수집·감시 경로 |
| --- | --- |
| 팀 보안 로그 | `C:\SKT aleph\flask-board-team\flask-board\logs\security.log` |
| 개인 보안 로그 | `C:\SKT aleph\flask-board\logs\security.log` |
| 팀 Suricata 로그 | `C:\SKT aleph\flask-board-team\flask-board\logs\suricata_alert.log` |
| 개인 Suricata 로그 | `C:\SKT aleph\flask-board\logs\suricata_alert.log` |
| 팀 FIM | `C:\SKT aleph\flask-board-team\flask-board\templates` |
| 개인 FIM | `C:\SKT aleph\flask-board\templates` |

`verify-agent-conf` 문법 검사가 통과했습니다. 11:42 KST Agent 로그에서 두 `security.log`의 `Analyzing file`,
두 폴더의 `Monitoring path`, 실시간 FIM 시작을 확인했습니다.
14:23 이후 재점검에서는 현재 원본에 로그 항목 4개·디렉터리 2개가 있고 Manager 설정과도 일치함을 확인했습니다.
Suricata 경보의 실제 신규 파일 기록·수집·Dashboard 표시는 이번 코드 제공만으로 완료 처리하지 않습니다.

기존 일부 한글 예제 파일명에는 non-UTF8 이름 경고가 있었습니다. 디렉터리 감시 등록이 해당 파일 모두의 정상 감시를 뜻하지는 않습니다.
설정 변경 전 백업은 PC 로컬의 `backup/wazuh-dual-board-*` 및 `wazuh-config/agent.conf.*.bak`에 보존했습니다.
백업 및 키·인증 정보는 공유 문서에 포함하지 않습니다.

## 5. 추가 규칙 설치 전 충돌 확인

저장소에 준비한 `wazuh/rules/flask_board_signals.xml`의 100230~100233은 격리된 Wazuh 4.9.0에서 검증한 **추가 규칙 예시**입니다.
현재 이 PC의 실제 `local_rules.xml`에는 다음 규칙이 이미 있습니다.

| 규칙 번호 | 현재 실제 용도 |
| --- | --- |
| 100230 | Flask HTTP 404 발생 |
| 100231 | Flask HTTP 404 폭주 |
| 100240 | Suricata 기본 경보 |
| 100241 | Suricata Nmap 포트 스캔 |
| 100242 | Suricata SQL Injection |
| 100243 | 동일 IP Suricata 경보 폭주 |

따라서 예시의 100230·100231과 현재 규칙 번호가 겹칩니다. 추가 규칙 파일을 현재 Manager에 그대로 설치하지 않습니다.
먼저 번호를 재배정하거나 기존 규칙에 통합하고, 4.9.0의 `analysisd -t`와 `wazuh-logtest`로 검증해야 합니다.
격리 검증 성공과 운영 규칙 설치 완료는 별개의 상태입니다.

## 6. Suricata 두 파일 출력 코드

아래는 대화에서 제공한 전체 코드입니다. WSL의 `/mnt/c`로 Windows 폴더에 접근하는 실행 환경을 전제로 합니다.
`gw`와 `EVE`는 사용자가 제공한 값이며, 실제 실행 환경에서의 유효성은 추가 확인이 필요합니다.

```python
import json
import socket
import os
import re
import sys
from contextlib import ExitStack
from datetime import datetime

gw = "172.23.16.1"

WAZUH_LOGS = [
    "/mnt/c/SKT aleph/flask-board-team/flask-board/logs/suricata_alert.log",
    "/mnt/c/SKT aleph/flask-board/logs/suricata_alert.log",
]

EVE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ids/recovered/eve.json"
_UNSAFE = re.compile(r"[\r\n\t\x00-\x1f\x7f]+")


def clean(v, limit=200):
    return _UNSAFE.sub(" ", str(v or "")).strip()[:limit] or "-"


with ExitStack() as stack:
    sock = stack.enter_context(
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    )

    log_files = []
    for path in WAZUH_LOGS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        log_files.append(
            stack.enter_context(open(path, "a", encoding="utf-8"))
        )

    with open(EVE, encoding="utf-8") as f:
        for line in f:
            event = json.loads(line)
            if event.get("event_type") != "alert":
                continue

            alert = event.get("alert", {})
            sig = alert.get("signature", "")
            if sig.startswith("SURICATA "):
                continue

            gelf = {
                "version": "1.1",
                "host": "suricata",
                "short_message": f"IDS: {sig}",
                "level": 4,
                "_rule": "ids-alert",
                "_src_ip": event.get("src_ip", ""),
                "_dst_ip": event.get("dest_ip", ""),
                "_signature": sig,
                "_category": alert.get("category", ""),
                "_sid": alert.get("signature_id", 0),
            }

            sock.sendto(json.dumps(gelf).encode("utf-8"), (gw, 12201))

            now = datetime.now()
            ts = (
                now.strftime("%Y-%m-%d %H:%M:%S.")
                + f"{now.microsecond // 1000:03d}"
            )
            log_line = (
                f"{ts} suricata_alert "
                f"src_ip={clean(event.get('src_ip', ''), 45)} "
                f"sid={clean(alert.get('signature_id', 0), 15)} "
                f"signature={clean(sig)}\n"
            )

            for log_file in log_files:
                log_file.write(log_line)
                log_file.flush()
```

`ExitStack`이 종료 시 두 로그 파일과 소켓을 닫습니다. 같은 경보를 두 파일에 기록하고 Agent가 둘 다 읽으면
Wazuh에서는 같은 사건이 두 건으로 집계될 수 있습니다. 반복 경보 임계값에도 영향을 줄 수 있으므로 실제 수집 후 확인합니다.
이 코드는 EVE 파일 전체를 읽는 재생 방식이므로 같은 파일을 다시 실행하면 이전 경보도 다시 전송합니다.

## 7. Git 공유 상태와 다음 작업

| 팀 저장소 커밋 | 내용 | 공유 상태 |
| --- | --- | --- |
| [4b0a4b0](https://github.com/NoBugs-Aleph/flask-board-team/commit/4b0a4b0) | 수업 로그·대시보드 기능 통합 | `origin/main` Push 완료 |
| [b635cf7](https://github.com/NoBugs-Aleph/flask-board-team/commit/b635cf7) | 개인·팀 동시 Wazuh 수집 설정 예시 | `origin/main` Push 완료 |
| [541dbd1](https://github.com/NoBugs-Aleph/flask-board-team/commit/541dbd1) | 팀 기본 포트 5001 분리 | `origin/main` Push 완료 |

팀원 소개·진행·캡처 파일과 미등록 `templates/test.php`, `templates/test2.php`는 이번 작업에서 변경하거나 커밋하지 않았습니다.

다음 작업은 서버 실행 상태 확인 → 추가 규칙 ID 정리 → Suricata 코드 저장·실행 → 파일/Agent/Indexer/Dashboard 확인 순서입니다.
과제 제출·메신저 전달 완료 여부는 이번 변경 현황 문서의 완료 항목에 포함하지 않습니다.
