"""10월 수업 이식: 실제 요청의 이중 출력과 100건 이후 페이징 회귀 검증."""
import os
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['JWT_SECRET_KEY'] = 'test-only-jwt-secret-at-least-32-bytes'
os.environ['GELF_ENABLED'] = '0'
os.environ['SECURITY_LOG_PATH'] = ''

from app import create_app
from controllers import security_controller
from extensions import db
from models import Incident, SecurityEvent, User, ROLE_GOLD
import privilege_revoke_bot as bot
from security_log import write_host_event
from test_security_response import TestConfig


class LessonUpdateTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / 'logs' / 'security.log'
        self.app = create_app(TestConfig)
        self.app.config['SECURITY_LOG_PATH'] = str(self.log)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        self.tmp.cleanup()

    def lines(self):
        return self.log.read_text(encoding='utf-8').splitlines() if self.log.exists() else []

    def test_404_writes_both_sensors_and_first_forwarded_ip(self):
        with patch('app.send_gelf') as gelf:
            response = self.client.get('/missing', headers={'X-Forwarded-For': '192.0.2.50, 10.0.0.1'})
        self.assertEqual(response.status_code, 404)
        self.assertRegex(self.lines()[0], r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3} http_404 src_ip=192\.0\.2\.50 path=/missing$')
        self.assertEqual(gelf.call_args.kwargs['rule'], 'web-scan')

    def test_404_sensor_failures_are_independent_and_preserve_response(self):
        with patch('app.write_404log', side_effect=OSError), patch('app.send_gelf') as gelf:
            self.assertEqual(self.client.get('/missing').status_code, 404)
            gelf.assert_called_once()
        with patch('app.send_gelf', side_effect=OSError):
            self.assertEqual(self.client.get('/missing').status_code, 404)
        self.assertEqual(len(self.lines()), 1)

    def test_admin_404_is_excluded(self):
        with patch('app.send_gelf') as gelf:
            self.assertEqual(self.client.get('/api/admin/missing').status_code, 404)
        self.assertFalse(self.lines())
        gelf.assert_not_called()

    def test_auth_failures_log_without_attempted_key(self):
        for path in ('/api/security/events', '/api/admin/blocked'):
            with self.subTest(path=path):
                response = self.client.post(path, headers={'X-API-Key': 'secret-attempt'}, json={}) if path.endswith('events') else self.client.get(path, headers={'X-API-Key': 'secret-attempt'})
                self.assertEqual(response.status_code, 401)
        self.assertEqual(len(self.lines()), 2)
        self.assertTrue(all('admin_auth_fail' in line for line in self.lines()))
        self.assertNotIn('secret-attempt', '\n'.join(self.lines()))

    def test_security_missing_key_logs_but_valid_key_does_not(self):
        self.assertEqual(self.client.post('/api/security/events', json={}).status_code, 401)
        self.assertEqual(self.client.post('/api/security/events', json={}, headers={'X-API-Key': TestConfig.SECURITY_API_KEY}).status_code, 400)
        self.assertEqual(len(self.lines()), 1)

    def test_gold_log_only_after_authorization(self):
        self.assertEqual(self.client.get('/gold').status_code, 401)
        self.client.post('/api/auth/register', json={'username': 'gold-reader', 'password': 'pw1234'})
        self.client.post('/api/auth/login', json={'username': 'gold-reader', 'password': 'pw1234'})
        self.log.unlink()
        self.assertEqual(self.client.get('/gold').status_code, 403)
        self.assertFalse(self.lines())
        with self.app.app_context():
            user = User.query.filter_by(username='gold-reader').one()
            user.role = ROLE_GOLD
            db.session.commit()
        with patch('controllers.page_controller.send_gelf') as gelf:
            self.assertEqual(self.client.get('/gold').status_code, 200)
        self.assertIn('gold_access user=gold-reader src_ip=127.0.0.1', self.lines()[0])
        self.assertEqual(gelf.call_args.kwargs['rule'], 'gold-access')

    def test_host_writer_sanitizes_injection_and_caps_fields(self):
        write_host_event(self.log, 'gold_access', '192.0.2.1, 10.0.0.1', user='attacker\nlogin_success user=admin\x00', request_path='/' + 'x' * 200)
        lines = self.lines()
        self.assertEqual(len(lines), 1)
        self.assertIn('user=attacker_login_success_user=admin_', lines[0])
        self.assertNotIn('10.0.0.1', lines[0])
        self.assertEqual(len(lines[0].split('path=')[1]), 120)

    def test_disabled_or_unwritable_path_does_not_break_requests(self):
        for path in ('', str(Path(self.tmp.name))):
            self.app.config['SECURITY_LOG_PATH'] = path
            self.assertEqual(self.client.get('/missing').status_code, 404)
        self.assertFalse(self.lines())

    def test_bot_logs_even_if_gelf_fails_and_dry_run_is_quiet(self):
        config = {'key': 'test-key', 'src_ip': '192.0.2.99', 'security_log_path': str(self.log)}
        users = [{'username': 'rogue-admin'}]
        with patch.object(bot, 'cfg', return_value=config), patch.object(bot, 'find_violations', return_value=users), patch.object(bot, 'send_gelf', side_effect=OSError), patch('sys.argv', ['bot']):
            self.assertEqual(bot.main(), 0)
        self.assertIn('priv_unauthorized_admin user=rogue-admin src_ip=192.0.2.99', self.lines()[0])
        self.log.unlink()
        with patch.object(bot, 'cfg', return_value=config), patch.object(bot, 'find_violations', return_value=users), patch.object(bot, 'send_gelf') as gelf, patch('sys.argv', ['bot', '--dry-run']):
            self.assertEqual(bot.main(), 0)
        self.assertFalse(self.lines())
        gelf.assert_not_called()

    def seed(self, count=125):
        with self.app.app_context():
            for i in range(count):
                severity = ('Low', 'Medium', 'High', 'Critical')[i % 4]
                common = dict(student='lab', src_ip=f'192.0.2.{i + 1}', severity=severity, created_at=datetime(2026, 10, 1))
                db.session.add(SecurityEvent(**common, decision='deny' if i % 2 == 0 else 'allow', fail_count=i, source='lesson', users='target', reason='seed'))
                db.session.add(Incident(**common, title=f'ticket {i}', event_count=i, status='open' if i % 2 == 0 else 'closed'))
            db.session.commit()

    def test_all_records_including_after_100_are_reachable_without_overlap(self):
        self.seed()
        for endpoint, key in (('events', 'events'), ('incidents', 'incidents')):
            ids = []
            for page in range(1, 8):
                result = self.client.get(f'/api/security/{endpoint}?page={page}').get_json()
                self.assertEqual(result['total'], 125)
                self.assertEqual(result['total_pages'], 7)
                self.assertEqual(result['count'], 5 if page == 7 else 20)
                ids.extend(row['id'] for row in result[key])
            self.assertEqual(len(set(ids)), 125)
            self.assertEqual(ids, list(range(125, 0, -1)))

    def test_severity_order_uses_rank_in_both_directions(self):
        self.seed(4)
        for endpoint in ('events', 'incidents'):
            for order, expected in (('desc', ['Critical', 'High', 'Medium', 'Low']), ('asc', ['Low', 'Medium', 'High', 'Critical'])):
                data = self.client.get(f'/api/security/{endpoint}?sort=severity&order={order}').get_json()
                self.assertEqual([row['severity'] for row in data[endpoint]], expected)

    def test_filters_affect_total_and_preserve_existing_search(self):
        self.seed()
        event = self.client.get('/api/security/events?student=lab&source=lesson&q=target&decision=deny&severity=High').get_json()
        incident = self.client.get('/api/security/incidents?student=lab&status=open&severity=High').get_json()
        for result in (event, incident):
            self.assertEqual(result['total'], 31)
            self.assertEqual(result['total_pages'], 2)
        self.assertEqual(self.client.get('/api/security/events?student=absent').get_json()['total'], 0)

    def test_legacy_offset_and_explicit_page_priority(self):
        self.seed(25)
        data = self.client.get('/api/security/events?limit=3&offset=1').get_json()
        self.assertEqual([row['id'] for row in data['events']], [24, 23, 22])
        self.assertEqual((data['limit'], data['offset']), (3, 1))
        data = self.client.get('/api/security/events?page=2&per_page=3&limit=1&offset=0').get_json()
        self.assertEqual([row['id'] for row in data['events']], [22, 21, 20])

    def test_invalid_sort_and_order_rejected_and_paging_normalized(self):
        self.seed()
        for endpoint in ('events', 'incidents'):
            for query in ('sort=password', 'sort=id;DROP TABLE users', 'order=random'):
                self.assertEqual(self.client.get(f'/api/security/{endpoint}?{query}').status_code, 400)
            for page in ('0', '-1', 'bad'):
                data = self.client.get(f'/api/security/{endpoint}?page={page}&per_page=999').get_json()
                self.assertEqual((data['page'], data['per_page'], data['count']), (1, 100, 100))
            self.assertEqual(self.client.get(f'/api/security/{endpoint}?page=999').get_json()['count'], 0)

    def test_dashboard_headers_match_server_allowlist(self):
        html = self.client.get('/dashboard').get_data(as_text=True)
        for name, allowed in (('event', security_controller._EVENT_SORTS), ('incident', security_controller._INCIDENT_SORTS)):
            head = re.search(rf'<thead id="{name}-head".*?</thead>', html, re.S).group()
            self.assertLessEqual(set(re.findall(r'data-sort="([^"]+)"', head)), set(allowed))
        for marker in ('id="incident-pager"', 'id="event-severity"', 'id="incident-severity"', "params.set('page'", 'bindSortHeaders'):
            self.assertIn(marker, html)


if __name__ == '__main__':
    unittest.main()
