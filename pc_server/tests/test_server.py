# -*- coding: utf-8 -*-
"""PC 서버(wj_server.py)·관리 도구(wj_admin.py) 시험 — 실제 HTTP 로 Code.gs 와 같은 요청을 보낸다.
실행:  python -I pc_server/tests/test_server.py
"""
import datetime
import gzip
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import wj_admin as A      # noqa: E402
import wj_server as S     # noqa: E402

PW = 'password-1234'
TW_MD = 'TW|W42|MD|sales_comment|ko'


class ServerCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = S.Store(os.path.join(cls.tmp.name, 'wj.sqlite3'))
        cls.store.init_defaults()
        cls.store.upsert_user('md_tw', '대만 MD', 'TW', 'MD', 'writer')
        cls.store.upsert_user('md_hk', '홍콩 MD', 'HK', 'MD', 'writer')
        cls.store.upsert_user('viewer1', '조회', 'TW', 'ALL', 'viewer')
        for u in ('hk', 'tw', 'hq', 'md_tw', 'md_hk', 'viewer1'):
            cls.store.set_password(u, PW)
        cls.key = cls.store.create_push_key()
        cls.srv = S.make_server(cls.store, '127.0.0.1', 0)
        cls.url = 'http://127.0.0.1:%d/api' % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.store.db.close()
        cls.tmp.cleanup()

    def post(self, body, raw=None):
        data = raw if raw is not None else json.dumps(body).encode('utf-8')
        req = urllib.request.Request(self.url, data=data, headers={'Content-Type': 'text/plain;charset=utf-8'})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode('utf-8'))

    def login(self, uid='md_tw', who='테스터', **kw):
        r = self.post(dict({'a': 'login', 'id': uid, 'password': PW, 'who': who}, **kw))
        self.assertTrue(r['ok'], r)
        return r['token']


class TestAuth(ServerCase):
    def test_login_ok_and_me(self):
        r = self.post({'a': 'login', 'id': 'MD_TW ', 'password': PW, 'who': '홍길동<b>'})
        self.assertTrue(r['ok'])
        self.assertEqual(r['me']['id'], 'md_tw')
        self.assertEqual(r['me']['name'], '홍길동b')
        self.assertEqual(r['me']['role'], 'writer')
        self.assertEqual(len(r['me']['sid']), 12)

    def test_wrong_password_and_lockout(self):
        for _ in range(S.MAX_FAIL):
            r = self.post({'a': 'login', 'id': 'viewer1', 'password': 'x' * 9, 'who': 'a'})
            self.assertFalse(r['ok'])
        r = self.post({'a': 'login', 'id': 'viewer1', 'password': PW, 'who': 'a'})
        self.assertFalse(r['ok'])
        self.assertIn('locked', r['error'])
        self.store.fails.clear()

    def test_site_restriction(self):
        self.assertFalse(self.post({'a': 'login', 'id': 'md_tw', 'password': PW, 'who': 'a', 'site': 'HK'})['ok'])
        self.assertTrue(self.post({'a': 'login', 'id': 'md_tw', 'password': PW, 'who': 'a', 'site': 'TW'})['ok'])
        self.assertTrue(self.post({'a': 'login', 'id': 'hq', 'password': PW, 'who': 'a', 'site': 'HQ'})['ok'])

    def test_requires_name(self):
        self.assertFalse(self.post({'a': 'login', 'id': 'tw', 'password': PW, 'who': ' '})['ok'])

    def test_bad_token_is_auth_error(self):
        r = self.post({'a': 'pull', 'ent': 'TW', 'week': 'W42', 'token': 'nope'})
        self.assertFalse(r['ok'])
        self.assertTrue(r['auth'])

    def test_logout_and_password_change_revoke(self):
        t = self.login('tw')
        self.assertTrue(self.post({'a': 'pull', 'ent': 'TW', 'week': 'W42', 'token': t})['ok'])
        self.post({'a': 'logout', 'token': t})
        self.assertTrue(self.post({'a': 'pull', 'ent': 'TW', 'week': 'W42', 'token': t})['auth'])
        t2 = self.login('hk')
        self.store.set_password('hk', PW)
        self.assertTrue(self.post({'a': 'pull', 'ent': 'HK', 'week': 'W42', 'token': t2})['auth'])

    def test_unknown_action_and_garbage(self):
        t = self.login()
        self.assertIn('알 수 없는', self.post({'a': 'zzz', 'token': t})['error'])
        self.assertFalse(self.post(None, raw=b'not json')['ok'])
        self.assertFalse(self.post(None, raw=b'[1,2]')['ok'])


class TestJournal(ServerCase):
    def test_save_pull_and_conflict(self):
        t = self.login()
        cid = 'TW|W10|MD|a_item|ko'
        r = self.post({'a': 'save', 'cellId': cid, 'html': '<b>안녕</b>', 'base': 0, 'token': t})
        self.assertEqual((r['ok'], r['version'], r['translated']), (True, 1, []))
        r = self.post({'a': 'save', 'cellId': cid, 'html': '둘째', 'base': 1, 'token': t})
        self.assertEqual(r['version'], 2)
        r = self.post({'a': 'save', 'cellId': cid, 'html': '충돌', 'base': 1, 'token': t})
        self.assertTrue(r['conflict'])
        self.assertEqual((r['current']['html'], r['current']['version']), ('둘째', 2))
        pulled = self.post({'a': 'pull', 'ent': 'TW', 'week': 'W10', 'token': t})
        c = pulled['cells'][cid]
        self.assertEqual((c['html'], c['version'], c['auto']), ('둘째', 2, False))
        self.assertIn('md_tw (테스터)', c['by'])
        self.assertFalse(pulled['closed'])

    def test_permissions(self):
        cid = 'TW|W11|MD|a_item|ko'
        self.assertFalse(self.post({'a': 'save', 'cellId': cid, 'html': 'x', 'base': 0, 'token': self.login('viewer1')})['ok'])
        self.assertFalse(self.post({'a': 'save', 'cellId': cid, 'html': 'x', 'base': 0, 'token': self.login('md_hk')})['ok'])      # 다른 법인
        other_dept = 'TW|W11|EC|a_item|ko'
        self.assertIn('권한', self.post({'a': 'save', 'cellId': other_dept, 'html': 'x', 'base': 0, 'token': self.login('md_tw')})['error'])
        hq_item = 'TW|W11|GM|hq|ko'
        self.assertFalse(self.post({'a': 'save', 'cellId': hq_item, 'html': 'x', 'base': 0, 'token': self.login('tw')})['ok'])
        self.assertTrue(self.post({'a': 'save', 'cellId': hq_item, 'html': 'x', 'base': 0, 'token': self.login('hq')})['ok'])
        bep = 'TW|W11|BEP|bep_note|ko'
        self.assertTrue(self.post({'a': 'save', 'cellId': bep, 'html': 'x', 'base': 0, 'token': self.login('md_tw')})['ok'])

    def test_sanitize_and_limits(self):
        t = self.login()
        cid = 'TW|W12|MD|a_item|ko'
        self.post({'a': 'save', 'cellId': cid, 'html': 'a<script>alert(1)</script><p onclick="x()">b</p><a href="javascript:z">c</a>', 'base': 0, 'token': t})
        html = self.post({'a': 'pull', 'ent': 'TW', 'week': 'W12', 'token': t})['cells'][cid]['html']
        self.assertNotIn('script', html.lower())
        self.assertNotIn('onclick', html)
        self.assertNotIn('javascript:', html)
        r = self.post({'a': 'save', 'cellId': cid, 'html': 'x' * (S.MAX_HTML + 1), 'base': 3, 'token': t})
        self.assertIn('너무 깁니다', r['error'])
        self.assertIn('올바르지', self.post({'a': 'save', 'cellId': 'bad', 'html': 'x', 'base': 0, 'token': t})['error'])

    def test_save_many_partial(self):
        t = self.login()
        items = [{'cellId': 'TW|W13|MD|i1|ko', 'html': 'a', 'base': 0},
                 {'cellId': 'TW|W13|EC|i2|ko', 'html': 'b', 'base': 0},          # 권한 없음
                 {'cellId': 'TW|W13|MD|i3|ko', 'html': 'c', 'base': 5}]          # 충돌
        res = self.post({'a': 'saveMany', 'items': items, 'token': t})['results']
        self.assertEqual([x['ok'] for x in res], [True, False, False])
        self.assertTrue(res[2]['conflict'])
        self.assertFalse(self.post({'a': 'saveMany', 'items': [], 'token': t})['ok'])

    def test_photo_cells(self):
        t = self.login('md_tw')
        cid = 'TW|W14|VMD|vthis_p1|ko'
        vmd = self.login('tw')
        img = '<img src="data:image/png;base64,iVBORw0KGgo=" alt="x">'
        self.assertTrue(self.post({'a': 'save', 'cellId': cid, 'html': img, 'base': 0, 'token': vmd})['ok'])
        self.assertFalse(self.post({'a': 'save', 'cellId': cid, 'html': '<b>not img</b>', 'base': 1, 'token': vmd})['ok'])
        no = self.post({'a': 'pullMany', 'ent': 'TW', 'weeks': ['W14'], 'photos': False, 'token': t})['results'][0]
        self.assertIsNone(no['cells'][cid]['html'])
        yes = self.post({'a': 'pullMany', 'ent': 'TW', 'weeks': ['W14'], 'photos': True, 'token': t})['results'][0]
        self.assertEqual(yes['cells'][cid]['html'], img)

    def test_pull_many_and_bad_week(self):
        t = self.login()
        r = self.post({'a': 'pullMany', 'ent': 'TW', 'weeks': ['W1', 'BAD'], 'token': t})
        self.assertTrue(r['ok'])
        self.assertTrue(r['results'][0]['ok'])
        self.assertFalse(r['results'][1]['ok'])

    def test_close_week(self):
        cid = 'TW|W15|MD|a_item|ko'
        w = self.login('md_tw')
        hq = self.login('hq')
        self.assertFalse(self.post({'a': 'close', 'ent': 'TW', 'week': 'W15', 'closed': True, 'token': w})['ok'])
        self.assertTrue(self.post({'a': 'close', 'ent': 'TW', 'week': 'W15', 'closed': True, 'token': hq})['closed'])
        self.assertIn('마감', self.post({'a': 'save', 'cellId': cid, 'html': 'x', 'base': 0, 'token': w})['error'])
        self.assertTrue(self.post({'a': 'pull', 'ent': 'TW', 'week': 'W15', 'token': w})['closed'])
        self.assertTrue(self.post({'a': 'save', 'cellId': cid, 'html': 'x', 'base': 0, 'token': hq})['ok'])          # 본사는 마감 후에도
        self.post({'a': 'close', 'ent': 'TW', 'week': 'M03', 'closed': True, 'token': hq})
        self.assertTrue(self.post({'a': 'save', 'cellId': 'TW|M03|MD|a_item|ko', 'html': 'x', 'base': 0, 'token': w})['ok'])   # 월간은 마감 후에도 작성자가 쓴다
        self.post({'a': 'close', 'ent': 'TW', 'week': 'W15', 'closed': False, 'token': hq})
        self.assertTrue(self.post({'a': 'save', 'cellId': cid, 'html': 'y', 'base': 1, 'token': w})['ok'])

    def test_presence(self):
        a, b = self.login('md_tw', '가'), self.login('tw', '나')
        self.assertTrue(self.post({'a': 'presence', 'ent': 'TW', 'week': 'W16', 'cell': TW_MD.replace('W42', 'W16'), 'token': a})['ok'])
        pres = self.post({'a': 'pull', 'ent': 'TW', 'week': 'W16', 'token': b})['presence']
        self.assertEqual([v['n'] for v in pres.values()], ['가'])
        self.post({'a': 'presence', 'ent': 'TW', 'week': 'W16', 'cell': '', 'token': a})
        self.assertEqual(self.post({'a': 'pull', 'ent': 'TW', 'week': 'W16', 'token': b})['presence'], {})

    def test_translate_is_noop(self):
        t = self.login()
        self.assertEqual(self.post({'a': 'translate', 'cellIds': ['TW|W1|MD|a|ko'], 'token': t}), {'ok': True, 'results': []})

    def test_concurrent_saves_one_wins(self):
        t = self.login()
        cid = 'TW|W17|MD|race|ko'
        out = []

        def go(i):
            out.append(self.post({'a': 'save', 'cellId': cid, 'html': 'v%d' % i, 'base': 0, 'token': t}))
        th = [threading.Thread(target=go, args=(i,)) for i in range(8)]
        [x.start() for x in th]
        [x.join() for x in th]
        self.assertEqual(sum(1 for r in out if r['ok']), 1)
        self.assertEqual(sum(1 for r in out if r.get('conflict')), 7)


class TestPages(ServerCase):
    HTML = '<html><body>' + '화면' * 600 + '</body></html>'

    def test_push_info_get_archive(self):
        bad = self.post({'a': 'pushPage', 'key': 'wrong', 'name': 'journal_TW', 'html': self.HTML})
        self.assertIn('반영 키', bad['error'])
        self.assertFalse(self.post({'a': 'pageInfo', 'key': self.key, 'name': 'journal_TW@W30'})['found'])
        self.assertFalse(self.post({'a': 'pushPage', 'key': self.key, 'name': '../etc', 'html': self.HTML})['ok'])
        self.assertIn('비어', self.post({'a': 'pushPage', 'key': self.key, 'name': 'journal_TW', 'html': 'x'})['error'])
        html = self.HTML.replace('\n', '\r\n') + '\r\n'
        r = self.post({'a': 'pushPage', 'key': self.key, 'name': 'journal_TW@W30', 'html': html, 'status': 'draft', 'asof': '2026-10-20', 'pid': 'p1'})
        self.assertEqual((r['ok'], r['status']), (True, 'draft'))
        info = self.post({'a': 'pageInfo', 'key': self.key, 'name': 'journal_TW@W30'})
        self.assertEqual((info['found'], info['pushId'], info['verified']), (True, 'p1', True))
        t = self.login()
        pg = self.post({'a': 'page', 'name': 'journal_TW@W30', 'token': t})
        self.assertEqual((pg['ok'], pg['status'], pg['asOf'], pg['html']), (True, 'draft', '2026-10-20', html.replace('\r\n', '\n')))
        self.assertFalse(self.post({'a': 'page', 'name': 'journal_TW@W31', 'token': t})['ok'])
        self.assertTrue(self.post({'a': 'page', 'name': 'journal_TW@W30', 'token': 'bad'})['auth'])
        self.post({'a': 'pushPage', 'key': self.key, 'name': 'summary_HK@W30', 'html': self.HTML})
        self.post({'a': 'close', 'ent': 'TW', 'week': 'W30', 'closed': True, 'token': self.login('hq')})
        wk = [w for w in self.post({'a': 'archive', 'token': t})['weeks'] if w['week'] == 'W30'][0]
        self.assertEqual(sorted(wk['pages']), ['journal_TW@W30', 'summary_HK@W30'])
        self.assertEqual(wk['closed'], {'HK': False, 'TW': True})

    def test_push_key_lockout(self):
        for _ in range(S.PUSH_FAIL_MAX):
            self.post({'a': 'pageInfo', 'key': 'nope', 'name': 'journal_TW'})
        self.assertIn('잠시 잠겼', self.post({'a': 'pageInfo', 'key': self.key, 'name': 'journal_TW'})['error'])
        self.store.push_fails = [0, 0.0]

    def test_shell_and_health(self):
        base = self.url[:-len('api')]
        with urllib.request.urlopen(base + '?p=bep_HK') as r:
            body = r.read().decode('utf-8')
        self.assertIn('PAGE="bep_HK"', body)
        with urllib.request.urlopen(base + '?p=../../x') as r:
            self.assertIn('PAGE="journal_TW"', r.read().decode('utf-8'))
        with urllib.request.urlopen(base + 'healthz') as r:
            self.assertEqual(r.read(), b'ok')


class TestAdmin(unittest.TestCase):
    def test_import_backup_and_db_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = S.Store(os.path.join(tmp, 'a.sqlite3'))
            root = os.path.join(tmp, 'wj_backup')

            def write(day, name, data):
                os.makedirs(os.path.join(root, day), exist_ok=True)
                with gzip.open(os.path.join(root, day, name), 'wt', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False)
            cell = 'TW|W41|MD|x|ko'
            write('2026-10-14', 'TW_W41.json.gz', {'ent': 'TW', 'code': 'W41', 'closed': False,
                  'cells': {cell: {'html': '옛', 'version': 1, 'by': 'a', 'at': '2026-10-14T01:00:00Z', 'auto': False}}})
            write('2026-10-21', 'TW_W41.json.gz', {'ent': 'TW', 'code': 'W41', 'closed': True,
                  'cells': {cell: {'html': '새', 'version': 2, 'by': 'b', 'at': '2026-10-21T01:00:00Z', 'auto': False},
                            'TW|W41|MD|y|en': {'html': '번역', 'version': 1, 'by': 'auto-translate', 'at': 'z', 'auto': True},
                            'TW|W41|VMD|vthis_p1|ko': {'html': None, 'version': 1, 'by': '', 'at': '', 'auto': False},
                            'broken': {'html': 'x', 'version': 1}}})
            with open(os.path.join(root, '2026-10-21', 'HK_W41.json.gz'), 'wb') as f:
                f.write(b'not gzip')
            st = A.import_backup(store, root, say=lambda *_: None)
            self.assertEqual((st['files'], st['bad'], st['closed']), (2, 1, 1))
            r = store.db.execute('SELECT * FROM journal WHERE cell_id=?', (cell,)).fetchone()
            self.assertEqual((r['html'], r['version'], r['updated_by']), ('새', 2, 'b'))
            self.assertEqual(store.db.execute("SELECT auto FROM journal WHERE cell_id='TW|W41|MD|y|en'").fetchone()['auto'], 'auto')
            self.assertEqual(store.db.execute('SELECT COUNT(*) c FROM journal').fetchone()['c'], 2)
            self.assertTrue(store.week_closed('TW', 'W41'))
            # 다시 가져와도 같은 결과(멱등), 더 높은 버전이 DB 에 있으면 덮어쓰지 않는다
            store.db.execute("UPDATE journal SET version=9, html='현장 수정' WHERE cell_id=?", (cell,))
            A.import_backup(store, root, say=lambda *_: None)
            self.assertEqual(store.db.execute('SELECT html FROM journal WHERE cell_id=?', (cell,)).fetchone()['html'], '현장 수정')
            # DB 백업 + 보관 일수
            out = os.path.join(tmp, 'bk')
            os.makedirs(out)
            old = os.path.join(out, '2026-01-01.sqlite3')
            open(old, 'w').close()
            dst, removed = A.backup_db(store, out, keep=30, today=datetime.date(2026, 10, 23))
            self.assertEqual(removed, ['2026-01-01.sqlite3'])
            import sqlite3
            c = sqlite3.connect(dst)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM journal').fetchone()[0], 2)
            c.close()
            store.db.close()

    def test_cli_user_and_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, 'c.sqlite3')
            self.assertEqual(A.main(['--db', db, 'init']), 0)
            self.assertEqual(A.main(['--db', db, 'add-user', 'Kim', '--ent', 'tw', '--dept', 'MD']), 0)
            self.assertEqual(A.main(['--db', db, 'set-password', 'kim', '--password', 'short']), 1)
            self.assertEqual(A.main(['--db', db, 'set-password', 'kim', '--password', PW]), 0)
            self.assertEqual(A.main(['--db', db, 'set-password', 'nobody', '--password', PW]), 1)
            self.assertEqual(A.main(['--db', db, 'push-key']), 0)
            self.assertEqual(A.main(['--db', db, 'list-users']), 0)
            s = S.Store(db)
            self.assertEqual(s.handle({'a': 'login', 'id': 'KIM', 'password': PW, 'who': 'k'})['me']['ent'], 'TW')
            s.db.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
