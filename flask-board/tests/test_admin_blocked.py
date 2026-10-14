"""10-14 수업 이식(fc5d09b): 차단 IP 검색·페이징·일괄 차단/해제 회귀 검증."""
import os
import re
import unittest
from unittest import mock

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['GELF_ENABLED'] = '0'
os.environ['SECURITY_LOG_PATH'] = ''

from flask_jwt_extended import create_access_token
from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app import create_app
from controllers.admin_controller import _BLOCKED_SORTS, _USER_SORTS
from extensions import db
from models import ROLE_ADMIN, ROLE_USER, BlockedIP, SecurityEvent, User
from test_security_response import TestConfig

LIST, BLOCK, UNBLOCK = '/api/admin/blocked', '/api/admin/blocked/block', '/api/admin/blocked/unblock'


class AdminBlockedTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app.config['SECURITY_LOG_PATH'] = ''
        self.client = self.app.test_client()
        self.key = {'X-API-Key': TestConfig.ADMIN_API_KEY}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def block(self, *ips, reason=None, headers=None):
        body = {'ips': list(ips), **({'reason': reason} if reason else {})}
        res = self.client.post(BLOCK, json=body, headers=headers or self.key)
        self.assertEqual(res.status_code, 200, res.get_data(as_text=True))
        return res.get_json()

    def blocked_ips(self):
        return sorted(row['ip'] for row in self.client.get(LIST, headers=self.key).get_json()['blocked'])

    def bearer(self, username, role):
        with self.app.app_context():
            user = User(username=username, password=generate_password_hash('pw1234'), role=role)
            db.session.add(user)
            db.session.commit()
            return {'Authorization': 'Bearer ' + create_access_token(identity=str(user.id))}

    def test_list_without_paging_returns_all_and_paging_meta(self):
        self.block(*[f'198.51.100.{i}' for i in range(1, 26)])
        self.assertEqual(self.client.get(LIST, headers=self.key).get_json()['count'], 25)
        page = self.client.get(LIST + '?page=3&per_page=10&sort=ip&order=asc', headers=self.key).get_json()
        self.assertEqual((page['count'], page['total'], page['total_pages']), (5, 25, 3))
        self.assertEqual(self.client.get(LIST + '?page=1&sort=reason', headers=self.key).status_code, 400)

    def test_search_ip_reason_and_literal_wildcards(self):
        self.block('198.51.100.1', '198.51.100.2', reason='nikto scan')
        self.block('203.0.113.9', reason='brute force')
        by_ip = self.client.get(LIST + '?q=203.0&page=1', headers=self.key).get_json()
        self.assertEqual([row['ip'] for row in by_ip['blocked']], ['203.0.113.9'])
        self.assertEqual(self.client.get(LIST + '?q=nikto&page=1', headers=self.key).get_json()['total'], 2)
        self.assertEqual(self.client.get(LIST + '?q=%25&page=1', headers=self.key).get_json()['total'], 0)

    def test_bulk_block_normalizes_skips_and_audits(self):
        self.block('198.51.100.1')
        body = self.block('198.51.100.1', 'not-an-ip', '999.1.1.1', '198.51.100.2', '2001:DB8:0::1')
        self.assertEqual(body['changed'], ['198.51.100.2', '2001:db8::1'])
        self.assertEqual(body['skipped'], ['198.51.100.1'])
        self.assertEqual(body['invalid'], ['999.1.1.1', 'not-an-ip'])
        with self.app.app_context():
            audited = {e.src_ip for e in SecurityEvent.query.filter_by(source='admin-console')}
        self.assertEqual(audited, {'198.51.100.1', '198.51.100.2', '2001:db8::1'})
        self.assertEqual(self.client.get('/api/posts', headers={'X-Forwarded-For': '198.51.100.2'}).status_code, 403)

    def test_cannot_block_own_ip(self):
        body = self.block('198.51.100.50', '198.51.100.51', headers={**self.key, 'X-Forwarded-For': '198.51.100.50'})
        self.assertEqual((body['changed'], body['self_skipped']), (['198.51.100.51'], ['198.51.100.50']))
        self.assertEqual(self.blocked_ips(), ['198.51.100.51'])

    def test_unblock_selected_all_and_search_scoped_all(self):
        self.block('198.51.100.1', '198.51.100.2', '198.51.100.3')
        self.block('203.0.113.9')
        body = self.client.post(UNBLOCK, headers=self.key, json={'ips': ['198.51.100.1', '198.51.100.99']}).get_json()
        self.assertEqual((body['changed'], body['not_found']), (['198.51.100.1'], ['198.51.100.99']))
        self.client.post(UNBLOCK, headers=self.key, json={'all': True, 'q': '198.51'})
        self.assertEqual(self.blocked_ips(), ['203.0.113.9'])
        self.assertEqual(self.client.post(UNBLOCK, headers=self.key, json={'all': True}).get_json()['count'], 1)
        self.assertEqual(self.blocked_ips(), [])

    def test_unblock_records_one_allow_audit_event(self):
        self.block('198.51.100.1', '198.51.100.2')
        self.client.post(UNBLOCK, headers=self.key, json={'all': True})
        self.client.post(UNBLOCK, headers=self.key, json={'ips': ['198.51.100.99']})  # 없는 IP는 기록하지 않는다
        with self.app.app_context():
            allowed = SecurityEvent.query.filter_by(source='admin-console', decision='allow').all()
        self.assertEqual(len(allowed), 1)
        self.assertIn('198.51.100.1, 198.51.100.2', allowed[0].reason)

    def test_concurrent_insert_of_same_ip_returns_409_without_partial_rows(self):
        def other_request_blocks_first():
            # 중복 확인이 끝난 직후 n8n 단건 차단이 같은 IP를 넣은 상황
            db.session.execute(text("INSERT INTO blocked_ips (ip, blocked_at) VALUES ('198.51.100.7', CURRENT_TIMESTAMP)"))
            return 'apikey'
        with mock.patch('controllers.admin_controller._security_actor', side_effect=other_request_blocks_first):
            res = self.client.post(BLOCK, headers=self.key, json={'ips': ['198.51.100.6', '198.51.100.7']})
        self.assertEqual(res.status_code, 409)
        self.assertEqual(self.blocked_ips(), [])

    def test_unblock_removes_legacy_malformed_rows(self):
        with self.app.app_context():
            db.session.add(BlockedIP(ip='legacy typo', reason='old'))
            db.session.commit()
        self.client.post(UNBLOCK, headers=self.key, json={'ips': ['legacy typo']})
        self.assertEqual(self.blocked_ips(), [])

    def test_bad_payloads_change_nothing(self):
        self.block('198.51.100.1')
        for url in (BLOCK, UNBLOCK):
            for payload in ({}, {'ips': []}, {'ips': '1.2.3.4'}, {'ips': [1]}, {'ips': ['  ']},
                            {'all': False}, {'ips': ['198.51.100.9'] * 501}):
                with self.subTest(url=url, payload=str(payload)[:40]):
                    self.assertEqual(self.client.post(url, headers=self.key, json=payload).status_code, 400)
        self.assertEqual(self.client.post(BLOCK, headers=self.key, json={'all': True}).status_code, 400)
        self.assertEqual(self.blocked_ips(), ['198.51.100.1'])

    def test_requires_admin(self):
        self.block('198.51.100.1')
        plain = self.bearer('plain', ROLE_USER)
        for url in (BLOCK, UNBLOCK):
            self.assertEqual(self.client.post(url, json={'ips': ['198.51.100.1']}).status_code, 401)
            self.assertEqual(self.client.post(url, headers=plain, json={'ips': ['198.51.100.1']}).status_code, 403)
        self.assertEqual(self.client.get(LIST + '?page=1', headers=plain).status_code, 403)
        self.block('198.51.100.2', headers=self.bearer('boss', ROLE_ADMIN))
        self.assertEqual(self.blocked_ips(), ['198.51.100.1', '198.51.100.2'])

    def test_admin_page_sort_headers_match_server_whitelists(self):
        html = self.client.get('/admin', headers=self.bearer('boss', ROLE_ADMIN)).get_data(as_text=True)
        for head_id, allowed in (('member-head', _USER_SORTS), ('blocked-head', _BLOCKED_SORTS)):
            thead = re.search(rf'<thead id="{head_id}".*?</thead>', html, re.S).group(0)
            sorts = re.findall(r'data-sort="([^"]+)"', thead)
            self.assertTrue(sorts and set(sorts) <= set(allowed), (head_id, sorts))


if __name__ == '__main__':
    unittest.main()
