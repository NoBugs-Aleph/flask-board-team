"""10-13 수업 이식: 서버 페이징·일괄 회원 관리·티켓 종료 회귀 검증."""
import os
import unittest
from datetime import datetime, timedelta

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['GELF_ENABLED'] = '0'
os.environ['SECURITY_LOG_PATH'] = ''

from flask_jwt_extended import create_access_token
from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
from models import Incident, Post, SecurityEvent, User, ROLE_ADMIN, ROLE_GOLD, ROLE_USER
from test_security_response import TestConfig


class AdminBulkTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app.config['SECURITY_LOG_PATH'] = ''
        self.client = self.app.test_client()
        self.key = {'X-API-Key': TestConfig.ADMIN_API_KEY}
        with self.app.app_context():
            db.session.execute(text('PRAGMA foreign_keys=ON'))
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def users(self, names, role=ROLE_USER, locked=False):
        with self.app.app_context():
            users = [User(username=name, password=generate_password_hash('pw1234'),
                          role=role, is_locked=locked, failed_logins=4 if locked else 0)
                     for name in names]
            db.session.add_all(users)
            db.session.commit()
            return [user.id for user in users]

    def bearer(self, user_id):
        with self.app.app_context():
            return {'Authorization': 'Bearer ' + create_access_token(identity=str(user_id))}

    def post(self, suffix, payload, headers=None):
        return self.client.post('/api/admin/' + suffix, json=payload,
                                headers=self.key if headers is None else headers)

    def tickets(self, count=3, student='lab', severity='High'):
        with self.app.app_context():
            rows = [Incident(src_ip=f'192.0.2.{i}', title=f'ticket {i}',
                             student=student, severity=severity, status='open')
                    for i in range(count)]
            db.session.add_all(rows)
            db.session.commit()
            return [row.id for row in rows]

    def test_paged_users_reach_every_admin_and_bot_still_reads_all(self):
        ids = self.users([f'admin-{i:02}' for i in range(25)], ROLE_ADMIN)
        seen = []
        for page in range(1, 4):
            data = self.client.get(f'/api/admin/users?role=admin&page={page}&per_page=10&sort=id&order=asc', headers=self.key).get_json()
            self.assertEqual((data['total'], data['total_pages']), (25, 3))
            seen.extend(user['id'] for user in data['users'])
        self.assertEqual(seen, ids)
        all_users = self.client.get('/api/admin/users?role=admin', headers=self.key).get_json()
        self.assertEqual(all_users['count'], 25)
        self.assertNotIn('per_page', all_users)

    def test_filters_summary_and_post_counts(self):
        admin, = self.users(['boss'], ROLE_ADMIN)
        gold, = self.users(['gold'], ROLE_GOLD, locked=True)
        self.users(['normal'])
        with self.app.app_context():
            user = db.session.get(User, gold)
            user.role_reason = 'lesson search'
            db.session.add(Post(title='gold post', content='c', author_id=gold))
            db.session.commit()
        data = self.client.get('/api/admin/users?page=1&q=lesson&role=1&locked=1', headers=self.bearer(admin)).get_json()
        self.assertEqual((data['total'], data['users'][0]['post_count']), (1, 1))
        self.assertEqual(data['summary'], {'0': 1, '1': 1, '2': 1})
        self.assertFalse(data['users'][0]['is_me'])
        self.assertEqual(data['me']['id'], admin)

    def test_search_wildcards_are_literal(self):
        self.users(['a_b', 'axb', 'p%q', 'pXq'])
        for term, expected in (('a_b', 'a_b'), ('p%q', 'p%q')):
            data = self.client.get('/api/admin/users', query_string={'page': 1, 'q': term}, headers=self.key).get_json()
            self.assertEqual([user['username'] for user in data['users']], [expected])

    def test_sort_validation_and_paging_cap(self):
        self.users(['z', 'a', 'm'])
        data = self.client.get('/api/admin/users?page=1&sort=username&order=asc', headers=self.key).get_json()
        self.assertEqual([user['username'] for user in data['users']], ['a', 'm', 'z'])
        for query in ('sort=password', 'order=bad', 'role=invalid', 'locked=invalid'):
            self.assertEqual(self.client.get('/api/admin/users?page=1&' + query, headers=self.key).status_code, 400)
        data = self.client.get('/api/admin/users?page=bad&per_page=999', headers=self.key).get_json()
        self.assertEqual((data['page'], data['per_page']), (1, 100))

    def test_all_bulk_writes_require_admin(self):
        normal, = self.users(['normal'])
        gold, = self.users(['gold'], ROLE_GOLD)
        for path in ('users/lock', 'users/unlock', 'users/delete', 'incidents/close'):
            for headers, status in (({}, 401), (self.bearer(normal), 403), (self.bearer(gold), 403)):
                with self.subTest(path=path, status=status):
                    self.assertEqual(self.post(path, {'ids': [normal]}, headers).status_code, status)

    def test_invalid_payloads_do_not_change_data(self):
        user, = self.users(['target'])
        invalid = [None, [], 'x', 7, {}, {'ids': []}, {'ids': '1'},
                   {'ids': [True]}, {'ids': [1.0]}, {'ids': ['1']},
                   {'ids': [0]}, {'ids': [-1]}, {'ids': [user] * 501}, {'all': True}]
        for path in ('users/lock', 'users/unlock', 'users/delete', 'incidents/close'):
            for payload in invalid:
                with self.subTest(path=path, payload=str(payload)[:40]):
                    self.assertEqual(self.post(path, payload).status_code, 400)
        with self.app.app_context():
            self.assertFalse(db.session.get(User, user).is_locked)
            self.assertEqual(SecurityEvent.query.count(), 0)

    def test_lock_deduplicates_reports_missing_and_preserves_existing_lock(self):
        first, second = self.users(['a', 'b'])
        old = datetime(2026, 1, 1)
        with self.app.app_context():
            user = db.session.get(User, second)
            user.is_locked, user.locked_at = True, old
            db.session.commit()
        data = self.post('users/lock', {'ids': [first, first, second, 999]}).get_json()
        self.assertEqual((data['changed'], data['skipped'], data['not_found']), ([first], [second], [999]))
        with self.app.app_context():
            self.assertEqual(db.session.get(User, second).locked_at, old)
            event = SecurityEvent.query.one()
            self.assertEqual((event.source, event.users, event.decision), ('admin-console', 'a', 'deny'))

    def test_bulk_lock_skips_self_and_last_available_admin(self):
        boss, other = self.users(['boss', 'other'], ROLE_ADMIN)
        data = self.post('users/lock', {'ids': [boss, other]}, self.bearer(boss)).get_json()
        self.assertEqual((data['self_skipped'], data['changed']), ([boss], [other]))
        data = self.post('users/lock', {'ids': [boss]}).get_json()
        self.assertEqual((data['changed'], data['last_admin_skipped']), ([], [boss]))

    def test_all_locked_unlock_applies_search_and_role_across_pages(self):
        ids = self.users([f'gold-{i}' for i in range(25)], ROLE_GOLD, locked=True)
        normal, = self.users(['gold-normal'], locked=True)
        other, = self.users(['other-gold'], ROLE_GOLD, locked=True)
        data = self.post('users/unlock', {'all_locked': True, 'q': 'gold-', 'role': 'gold'}).get_json()
        self.assertEqual(data['changed'], ids)
        with self.app.app_context():
            for user_id in ids:
                user = db.session.get(User, user_id)
                self.assertFalse(user.is_locked)
                self.assertEqual(user.failed_logins, 0)
                self.assertIsNone(user.lock_reason)
            self.assertTrue(db.session.get(User, normal).is_locked)
            self.assertTrue(db.session.get(User, other).is_locked)
            self.assertEqual(SecurityEvent.query.one().decision, 'allow')

    def test_selected_unlock_only_changes_locked_selected_users(self):
        first, = self.users(['first'], locked=True)
        second, = self.users(['second'])
        third, = self.users(['third'], locked=True)
        data = self.post('users/unlock', {'ids': [first, second, 999]}).get_json()
        self.assertEqual((data['changed'], data['skipped'], data['not_found']), ([first], [second], [999]))
        with self.app.app_context():
            self.assertTrue(db.session.get(User, third).is_locked)
        self.assertEqual(self.post('users/unlock', {'all_locked': True, 'role': 'bad'}).status_code, 400)

    def test_delete_removes_posts_with_foreign_keys_enabled_and_writes_audit(self):
        first, second = self.users(['delete-me', 'keep-me'])
        with self.app.app_context():
            db.session.add_all([Post(title='a', content='c', author_id=first),
                                Post(title='b', content='c', author_id=first),
                                Post(title='c', content='c', author_id=second)])
            db.session.commit()
        data = self.post('users/delete', {'ids': [first, first, 999]}).get_json()
        self.assertEqual((data['changed'], data['posts_deleted'], data['not_found']), ([first], 2, [999]))
        with self.app.app_context():
            self.assertIsNone(db.session.get(User, first))
            self.assertEqual(Post.query.one().author_id, second)
            self.assertEqual(SecurityEvent.query.one().users, 'delete-me')

    def test_delete_protects_self_system_and_last_admin(self):
        boss, other = self.users(['boss', 'other'], ROLE_ADMIN)
        bot, normal = self.users(['soarbot', 'normal'])
        data = self.post('users/delete', {'ids': [boss, other, bot, normal]}, self.bearer(boss)).get_json()
        self.assertEqual((data['self_skipped'], data['protected'], data['changed']), ([boss], [bot], [other, normal]))
        data = self.post('users/delete', {'ids': [boss]}).get_json()
        self.assertEqual((data['changed'], data['last_admin_skipped']), ([], [boss]))
        self.assertEqual(self.client.delete(f'/api/admin/users/{bot}', headers=self.bearer(boss)).status_code, 400)

    def test_api_key_deleting_all_admins_leaves_one(self):
        ids = self.users(['a', 'b', 'c'], ROLE_ADMIN)
        data = self.post('users/delete', {'ids': ids}).get_json()
        self.assertEqual((data['changed'], data['last_admin_skipped']), (ids[1:], ids[:1]))

    def test_cookie_writes_require_csrf_and_support_admin(self):
        boss, = self.users(['boss'], ROLE_ADMIN)
        target, = self.users(['target'])
        self.client.post('/api/auth/login', json={'username': 'boss', 'password': 'pw1234'})
        self.assertEqual(self.post('users/lock', {'ids': [target]}, {}).status_code, 401)
        csrf = self.client.get_cookie('csrf_access_token').value
        self.assertEqual(self.post('users/lock', {'ids': [boss, target]}, {'X-CSRF-TOKEN': csrf}).get_json()['changed'], [target])

    def test_selected_close_is_idempotent_and_reports_missing(self):
        first, second, third = self.tickets()
        old = datetime(2026, 1, 1)
        with self.app.app_context():
            row = db.session.get(Incident, second)
            row.status, row.closed_at = 'closed', old
            db.session.commit()
        data = self.post('incidents/close', {'ids': [first, first, second, 999]}).get_json()
        self.assertEqual((data['closed'], data['skipped'], data['not_found']), ([first], [second], [999]))
        self.post('incident/close', {'id': second})
        with self.app.app_context():
            self.assertEqual(db.session.get(Incident, second).closed_at, old)
            self.assertEqual(db.session.get(Incident, third).status, 'open')

    def test_all_open_close_applies_filters_across_pages(self):
        ids = self.tickets(25)
        other_student, = self.tickets(1, student='other')
        other_severity, = self.tickets(1, severity='Low')
        data = self.post('incidents/close', {'all_open': True, 'student': 'lab', 'severity': 'High'}).get_json()
        self.assertEqual(data['closed'], ids)
        with self.app.app_context():
            self.assertEqual(db.session.get(Incident, other_student).status, 'open')
            self.assertEqual(db.session.get(Incident, other_severity).status, 'open')
            self.assertEqual(len({db.session.get(Incident, value).closed_at for value in ids}), 1)
        self.assertEqual(self.post('incidents/close', {'all_open': True, 'severity': 'bad'}).status_code, 400)
        self.assertEqual(self.post('incidents/close', {'all_open': True, 'severity': ['High']}).status_code, 400)

    def test_incident_keeps_highest_severity_and_starts_after_last_close(self):
        now = datetime.now()
        with self.app.app_context():
            db.session.add(SecurityEvent(student='lab', src_ip='192.0.2.1', decision='deny', fail_count=1,
                                         severity='Critical', source='test', created_at=now - timedelta(minutes=10)))
            db.session.commit()
        first = self.post('incident', {'src_ip': '192.0.2.1', 'severity': 'Low'}).get_json()['incident']
        self.assertEqual(first['severity'], 'Critical')
        updated = self.post('incident', {'src_ip': '192.0.2.1', 'severity': 'Medium'}).get_json()['incident']
        self.assertEqual(updated['severity'], 'Critical')
        self.post('incidents/close', {'ids': [first['id']]})
        with self.app.app_context():
            closed_at = db.session.get(Incident, first['id']).closed_at
            db.session.add(SecurityEvent(student='lab', src_ip='192.0.2.1', decision='deny', fail_count=1,
                                         severity='Medium', source='test', created_at=closed_at + timedelta(seconds=1)))
            db.session.commit()
        second = self.post('incident', {'src_ip': '192.0.2.1'}).get_json()['incident']
        self.assertNotEqual(second['id'], first['id'])
        self.assertEqual((second['event_count'], second['severity']), (1, 'Medium'))


if __name__ == '__main__':
    unittest.main()
