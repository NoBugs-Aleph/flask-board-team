"""임시 DB·임시 포트로 10-13 관리자/티켓 UI를 검증한다. Playwright 필요."""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['JWT_SECRET_KEY'] = 'ui-test-only-jwt-secret-at-least-32-bytes'
os.environ['GELF_ENABLED'] = '0'
os.environ['SECURITY_LOG_PATH'] = ''

from playwright.sync_api import sync_playwright, expect
from werkzeug.security import generate_password_hash
from werkzeug.serving import WSGIRequestHandler, make_server

from app import create_app
from extensions import db
from models import Incident, Post, SecurityEvent, User


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        pass


def run(output):
    with tempfile.TemporaryDirectory(prefix='board-ui-') as directory:
        class Config:
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite:///' + (Path(directory) / 'test.sqlite').as_posix()
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            JWT_SECRET_KEY = os.environ['JWT_SECRET_KEY']
            JWT_TOKEN_LOCATION = ['headers', 'cookies']
            JWT_COOKIE_CSRF_PROTECT = True
            JWT_COOKIE_SECURE = False
            JWT_COOKIE_SAMESITE = 'Lax'
            SECURITY_API_KEY = 'ui-test-security-key'
            ADMIN_API_KEY = 'ui-test-admin-key'
            ADMIN_ALLOWLIST = ['ui-admin']
            AUTO_POST_ON_DENY = False
            GELF_ENABLED = False
            SECURITY_LOG_PATH = ''
            PUBLIC_API_KEY = ''
            PUBLIC_API_URL = 'https://example.invalid'

        app = create_app(Config)
        with app.app_context():
            password = generate_password_hash('ui-password')
            db.session.add(User(username='ui-admin', password=password, role=2))
            for index in range(45):
                user = User(username=f'member-{index:02}', password=password, role=index % 3,
                            is_locked=index % 4 == 0, failed_logins=4 if index % 4 == 0 else 0,
                            role_reason='합성 UI 검증 데이터', role_granted_by='ui-admin')
                db.session.add(user)
                db.session.flush()
                if index == 0:
                    db.session.add_all([Post(title='delete-test', content='c', author_id=user.id),
                                        Post(title='delete-test2', content='c', author_id=user.id)])
            for index in range(45):
                student = 'lab' if index < 42 else 'other'
                severity = 'High' if index < 42 else 'Low'
                db.session.add(Incident(src_ip=f'192.0.2.{index + 1}', student=student,
                    title=f'합성 티켓 {index} · 긴 제목과 조치 표시 확인', severity=severity,
                    status='open', summary='브라우저 회귀 검증용 합성 데이터', actions='계정 잠금 · IP 차단', event_count=1))
                db.session.add(SecurityEvent(student=student, src_ip=f'192.0.2.{index + 1}',
                    decision='deny', fail_count=1, severity=severity, source='ui-test',
                    reason='브라우저 검증용 합성 로그'))
            db.session.commit()

        server = make_server('127.0.0.1', 0, app, request_handler=QuietHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f'http://127.0.0.1:{server.server_port}'
        errors, checks = [], []
        output.mkdir(parents=True, exist_ok=True)
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={'width': 1440, 'height': 1000})
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('dialog', lambda dialog: dialog.accept())
                page.goto(url + '/dashboard')
                expect(page.locator('#incident-total')).to_have_text('45건')
                expect(page.locator('#inc-actions')).to_be_hidden()
                checks.append('anonymous dashboard hides writes')
                page.evaluate("""async () => {
                    const response = await fetch('/api/auth/login', {method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username: 'ui-admin', password: 'ui-password'})});
                    if (!response.ok) throw new Error('test login failed');
                    localStorage.clear();
                }""")
                page.goto(url + '/admin')
                expect(page.locator('#member-total')).to_have_text('46명')
                expect(page.locator('#user-rows tr')).to_have_count(10)
                page.locator('#member-check-all').check()
                expect(page.locator('#member-selected-count')).not_to_have_text('0')
                page.locator('#member-pager button[data-page="2"]').first.click()
                expect(page.locator('#member-pager [aria-current="page"]')).to_have_text('2')
                expect(page.locator('#member-selected-count')).to_have_text('0')
                page.locator('#member-head th[data-sort="username"] button').click()
                expect(page.locator('#member-pager [aria-current="page"]')).to_have_text('1')
                checks.append('server pagination, sorting and selection reset')

                for width in (1440, 1024, 768, 390):
                    page.set_viewport_size({'width': width, 'height': 1000})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'admin overflow at {width}'
                    if width in (1440, 390):
                        page.evaluate('window.scrollTo(0, 0)')
                        page.screenshot(path=str(output / f'admin-{width}.png'), full_page=True)
                page.set_viewport_size({'width': 1440, 'height': 1000})
                page.locator('#member-search').fill('member-01')
                expect(page.locator('#member-total')).to_have_text('1명')
                page.locator('#user-rows .member-check').check()
                page.locator('#member-lock-selected').click()
                expect(page.locator('#flash')).to_contain_text('1명 차단')
                expect(page.locator('#user-rows')).to_contain_text('차단됨')
                page.locator('#user-rows .member-check').check()
                page.locator('#member-unlock-selected').click()
                expect(page.locator('#flash')).to_contain_text('1명 차단 해제')
                expect(page.locator('#user-rows')).to_contain_text('정상')
                checks.append('cookie-only login with CSRF, selected lock and unlock')

                page.locator('#member-search').fill('member-00')
                expect(page.locator('#user-rows')).to_contain_text('member-00')
                page.locator('#user-rows .member-check').check()
                page.locator('#member-delete-selected').click()
                expect(page.locator('#flash')).to_contain_text('게시글 2건 포함')
                expect(page.locator('#member-total')).to_have_text('0명')
                checks.append('selected deletion also removes posts')

                page.goto(url + '/dashboard')
                expect(page.locator('#inc-actions')).to_be_visible()
                expect(page.locator('#incident-total')).to_have_text('45건')
                for width in (1440, 1024, 768, 390):
                    page.set_viewport_size({'width': width, 'height': 1000})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'dashboard overflow at {width}'
                    if width in (1440, 390):
                        page.evaluate('window.scrollTo(0, 0)')
                        page.screenshot(path=str(output / f'dashboard-{width}.png'), full_page=True)
                page.set_viewport_size({'width': 390, 'height': 1000})
                page.locator('#incident-cards .inc-check').first.check()
                expect(page.locator('#inc-sel-count')).to_have_text('1')
                page.locator('#inc-close-selected').click()
                expect(page.locator('#inc-action-msg')).to_have_text('인시던트 1건 종료')
                expect(page.locator('#inc-closed')).to_have_text('1')
                page.locator('#incident-cards .inc-check').first.check()
                page.locator('#incident-severity').select_option('High')
                expect(page.locator('#incident-total')).to_have_text('42건')
                expect(page.locator('#inc-sel-count')).to_have_text('0')
                page.locator('#student-filter').select_option('lab')
                expect(page.locator('#inc-open')).to_have_text('42')
                page.locator('#inc-close-all').click()
                expect(page.locator('#inc-action-msg')).to_have_text('인시던트 42건 종료')
                expect(page.locator('#inc-open')).to_have_text('0')
                checks.append('mobile selection, filter reset and close all beyond current page')
                with app.app_context():
                    assert Incident.query.filter_by(student='other', status='open').count() == 2
                assert not errors, errors
                checks.append('1440/1024/768/390px layouts have no horizontal overflow or JS errors')
                browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
        print(json.dumps({'checks': checks, 'js_errors': errors, 'screenshots': str(output)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'image' / 'lesson_updates_20261013')
    run(parser.parse_args().output)
