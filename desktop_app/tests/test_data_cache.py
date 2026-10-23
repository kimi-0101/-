# -*- coding: utf-8 -*-
"""앱의 글 데이터 저장본·미리 받기·저장 기록 시험 (브라우저 없이 앱의 /api 에 직접 요청).
실행:  python -I desktop_app/tests/test_data_cache.py
"""
import http.client
import json
import os
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import mock_server   # noqa: E402
import wj_app        # noqa: E402

CELL = 'TW|W40|MD|sales|ko'
PHOTO = 'TW|W40|VMD|vthis_p1|ko'
IMG = '<img src="data:image/png;base64,iVBORw0KGgo=" alt="x">'


def wait(cond, sec=4.0):
    t = time.time()
    while time.time() - t < sec:
        if cond():
            return True
        time.sleep(0.03)
    return cond()


class AppCase(unittest.TestCase):
    def setUp(self):
        self._prefetch = wj_app.prefetch
        wj_app.prefetch = lambda *a, **k: None           # 로그인 뒤 자동 미리 받기는 끄고, 시험에서 직접 부른다
        self.mock = mock_server.Mock()
        self.msrv = mock_server.start(self.mock)
        self.tmp = tempfile.TemporaryDirectory()
        self.st = wj_app.State(self.mock.url, root=self.tmp.name)
        self.srv = wj_app.start_server(self.st)
        self.mock.journal[CELL] = {'html': '원본', 'version': 1, 'by': 'kim (k)', 'at': '2026-10-22T01:00:00.000Z'}
        self.mock.journal[PHOTO] = {'html': IMG, 'version': 1, 'by': 'kim (k)', 'at': '2026-10-22T01:00:00.000Z'}
        r = self.api('/app/login', {'id': 'tw', 'password': 'pw12345678', 'who': 't'})
        self.assertTrue(r['ok'], r)

    def tearDown(self):
        wj_app.prefetch = self._prefetch
        self.srv.shutdown()
        self.srv.server_close()
        self.msrv.shutdown()
        self.msrv.server_close()
        self.tmp.cleanup()

    def api(self, path, body):
        c = http.client.HTTPConnection('127.0.0.1', self.st.port, timeout=20)
        c.request('POST', path, json.dumps(body), {'Cookie': 'wjk=' + self.st.key})
        out = json.loads(c.getresponse().read().decode('utf-8'))
        c.close()
        return out

    def pull(self, week='W40', photos=True, ent='TW'):
        return self.api('/api', {'a': 'pull', 'ent': ent, 'week': week, 'photos': photos})

    def pm(self, weeks, photos=False, ent='TW'):
        return self.api('/api', {'a': 'pullMany', 'ent': ent, 'weeks': weeks, 'photos': photos})

    def age(self, key, sec):
        e = self.st.data_get(key)
        self.st.data_put(key, {'closed': e['closed'], 'cells': e['cells']} if 'cells' in e else {'weeks': e['weeks']}, at=time.time() - sec)

    def make_open(self, key):
        self.st.last_req[key] = time.time() - 3600       # 한참 뒤에 다시 연 것처럼


class TestPull(AppCase):
    def test_first_live_then_cached(self):
        r = self.pull()
        self.assertTrue(r['ok'])
        self.assertEqual(r['cells'][CELL]['html'], '원본')
        self.assertNotIn('cached', r)
        n = self.mock.count('pullMany')
        self.assertEqual(n, 1)                                          # 단일 pull 도 pullMany 로 받아 저장본을 만든다
        r2 = self.pull()
        self.assertTrue(r2['cached'])
        self.assertEqual(r2['cells'][CELL]['html'], '원본')
        self.assertEqual(self.mock.count('pullMany'), n)               # 서버를 다시 부르지 않음
        self.assertEqual(r2['me']['id'], 'tw')
        self.assertEqual(r2['presence'], {})

    def test_reopen_serves_stale_instantly_and_refreshes_behind(self):
        self.pull()
        self.mock.journal[CELL] = {'html': '남이 고침', 'version': 2, 'by': 'lee (l)', 'at': 'x'}
        self.mock.delay = 1.5                                           # 구글이 느린 상황
        self.age(wd := 'pull|TW|W40|1', 120)
        self.make_open(wd)
        t0 = time.time()
        r = self.pull()
        self.assertLess(time.time() - t0, 0.8)                          # 느린 서버를 기다리지 않음
        self.assertEqual(r['cells'][CELL]['html'], '원본')              # 먼저는 저장본
        self.assertTrue(wait(lambda: self.st.data_get(wd)['cells'][CELL]['html'] == '남이 고침', 6))   # 뒤에서 새로 받아 둠
        self.mock.delay = 0
        self.assertEqual(self.pull()['cells'][CELL]['html'], '남이 고침')

    def test_repeated_polls_go_live_when_older_than_fresh(self):
        self.pull()
        self.mock.journal[CELL] = {'html': '새 글', 'version': 2, 'by': 'lee (l)', 'at': 'x'}
        key = 'pull|TW|W40|1'
        self.age(key, 60)                                               # 오래됐지만 방금 요청이 있었음 → 화면의 주기적 확인으로 본다
        self.st.last_req[key] = time.time() - 5
        r = self.pull()
        self.assertEqual(r['cells'][CELL]['html'], '새 글')
        self.assertNotIn('cached', r)

    def test_pull_many_mixes_cache_and_live(self):
        self.mock.journal['TW|W41|MD|sales|ko'] = {'html': '41주', 'version': 1, 'by': 'a', 'at': 'x'}
        self.pm(['W40'])
        before = len(self.mock.pulls)
        r = self.pm(['W40', 'W41'])
        self.assertTrue(r['ok'])
        self.assertEqual([x['ok'] for x in r['results']], [True, True])
        self.assertEqual(r['results'][1]['cells']['TW|W41|MD|sales|ko']['html'], '41주')
        self.assertEqual(self.mock.pulls[before:], [('TW', ['W41'], False)])   # 없는 주만 서버에서 받음
        self.assertTrue(r['results'][0]['cached'])

    def test_photos_are_separate(self):
        a = self.pm(['W40'], photos=False)['results'][0]
        self.assertIsNone(a['cells'][PHOTO]['html'])
        b = self.pm(['W40'], photos=True)['results'][0]
        self.assertEqual(b['cells'][PHOTO]['html'], IMG)
        c = self.pm(['W40'], photos=False)['results'][0]
        self.assertIsNone(c['cells'][PHOTO]['html'])

    def test_offline_falls_back_to_stale(self):
        self.pull()
        key = 'pull|TW|W40|1'
        self.age(key, 3600)
        self.st.last_req[key] = time.time() - 5
        self.mock.offline = True
        r = self.pull()
        self.assertTrue(r['ok'] and r.get('stale'))
        self.assertEqual(r['cells'][CELL]['html'], '원본')
        r = self.pull(week='W30')                                       # 저장본이 없는 주는 오류
        self.assertFalse(r['ok'])

    def test_other_user_does_not_see_cache(self):
        self.pull()
        self.st.session['me'] = dict(self.st.session['me'], id='someone_else')
        n = self.mock.count('pullMany')
        r = self.pull()
        self.assertNotIn('cached', r)
        self.assertEqual(self.mock.count('pullMany'), n + 1)

    def test_odd_requests_are_forwarded(self):
        n = self.mock.count('pull')
        self.assertTrue(self.api('/api', {'a': 'pull', 'ent': 'XX', 'week': 'W40'})['ok'])       # 모양이 이상하면 서버가 판단
        self.assertEqual(self.mock.count('pull'), n + 1)

    def test_auth_error_clears_session(self):
        self.mock.expire = True
        r = self.pull(week='W22')
        self.assertTrue(r.get('auth'))
        self.assertIsNone(self.st.session)


class TestWrites(AppCase):
    def test_save_updates_cache_without_refetch(self):
        self.pull()
        n = self.mock.count('pullMany')                                  # 저장 '전' 기준 (뒤에서 새로 받기가 저장 응답보다 먼저 나갈 수 있어서)
        r = self.api('/api', {'a': 'save', 'cellId': CELL, 'html': '내가 고침', 'base': 1})
        self.assertEqual((r['ok'], r['version']), (True, 2))
        got = self.pull()
        c = got['cells'][CELL]
        self.assertEqual((c['html'], c['version'], c['by']), ('내가 고침', 2, 'tw (t)'))
        self.assertTrue(got['cached'])
        self.assertTrue(wait(lambda: self.mock.count('pullMany') > n))   # 번역 등 서버가 더 바꿨을 수 있어 뒤에서 한 번 새로 받음

    def test_save_many_conflict_updates_with_current(self):
        self.pull()
        self.mock.journal[CELL] = {'html': '남의 글', 'version': 5, 'by': 'lee (l)', 'at': 'z'}
        r = self.api('/api', {'a': 'saveMany', 'items': [{'cellId': CELL, 'html': 'x', 'base': 1}, {'cellId': 'TW|W40|MD|new|ko', 'html': '새칸', 'base': 0}]})
        self.assertTrue(r['results'][0]['conflict'])
        self.assertTrue(r['results'][1]['ok'])
        e = self.st.data_get('pull|TW|W40|1')
        self.assertEqual((e['cells'][CELL]['html'], e['cells'][CELL]['version']), ('남의 글', 5))
        self.assertEqual(e['cells']['TW|W40|MD|new|ko']['html'], '새칸')

    def test_photo_save_keeps_photo_hidden_in_no_photo_cache(self):
        self.pm(['W40'], photos=False)
        self.pm(['W40'], photos=True)
        self.api('/api', {'a': 'save', 'cellId': PHOTO, 'html': IMG, 'base': 1})
        self.assertIsNone(self.st.data_get('pull|TW|W40|0')['cells'][PHOTO]['html'])
        self.assertEqual(self.st.data_get('pull|TW|W40|1')['cells'][PHOTO]['html'], IMG)

    def test_close_updates_cache(self):
        self.pull()
        self.assertFalse(self.pull()['closed'])
        self.assertTrue(self.api('/api', {'a': 'close', 'ent': 'TW', 'week': 'W40', 'closed': True})['ok'])
        self.assertTrue(self.pull()['closed'])

    def test_write_log_keeps_typed_text(self):
        self.api('/api', {'a': 'save', 'cellId': CELL, 'html': '기록될 글', 'base': 1})
        self.api('/api', {'a': 'saveMany', 'items': [{'cellId': PHOTO, 'html': IMG, 'base': 1}, {'cellId': CELL, 'html': '충돌 글', 'base': 1}]})
        self.mock.offline = True
        r = self.api('/api', {'a': 'save', 'cellId': CELL, 'html': '못 보낸 글', 'base': 2})
        self.assertFalse(r['ok'])
        f = next((self.st.root / 'backup').glob('saves_*.jsonl'))
        recs = [json.loads(x) for x in f.read_text(encoding='utf-8').splitlines()]
        self.assertEqual(len(recs), 3)
        self.assertEqual(recs[0]['items'][0]['html'], '기록될 글')
        self.assertEqual(recs[0]['results'], ['ok:2'])
        self.assertIsNone(recs[1]['items'][0]['html'])                  # 사진 내용은 기록하지 않음(길이만)
        self.assertGreater(recs[1]['items'][0]['htmlLen'], 0)
        self.assertEqual(recs[1]['results'], ['ok:2', 'conflict'])
        self.assertEqual((recs[2]['items'][0]['html'], recs[2]['results']), ('못 보낸 글', ['connection-failed']))


class TestArchiveAndPrefetch(AppCase):
    def test_archive_cached(self):
        a = self.api('/api', {'a': 'archive'})
        self.assertTrue(a['ok'] and 'cached' not in a)
        n = self.mock.count('archive')
        b = self.api('/api', {'a': 'archive'})
        self.assertTrue(b['cached'])
        self.assertEqual(b['weeks'][0]['week'], 'W40')
        self.assertEqual(self.mock.count('archive'), n)
        self.age('archive', 300)
        self.make_open('archive')
        self.mock.delay = 1.0
        t0 = time.time()
        self.assertTrue(self.api('/api', {'a': 'archive'})['cached'])
        self.assertLess(time.time() - t0, 0.6)
        self.mock.delay = 0
        self.assertTrue(wait(lambda: self.mock.count('archive') > n))

    def test_page_with_sumfill_prefetches_its_data(self):
        self.mock.pages['summary_TW'] = ('<!doctype html><html><head></head><body><div id="sumfill" data-ent="TW" data-week="W40" hidden></div>'
                                          + 'x' * 50 + '</body></html>')
        r = self.api('/api', {'a': 'page', 'name': 'summary_TW'})
        self.assertTrue(r['ok'])
        self.assertTrue(wait(lambda: self.st.data_get('pull|TW|W40|1') is not None))      # 요청이 도착한 뒤 저장본이 기록될 때까지
        n = len(self.mock.pulls)
        got = self.pull()                                              # 화면이 열릴 때 보내는 요청(photos:true)
        self.assertTrue(got['cached'])
        self.assertEqual(len(self.mock.pulls), n)

    def test_refresh_button_refreshes_all_cached_data(self):
        self.pull()
        self.pm(['W41'], photos=False)
        self.mock.journal[CELL] = {'html': '최신', 'version': 9, 'by': 'x', 'at': 'y'}
        r = self.api('/app/refresh', {'name': 'journal_TW'})
        self.assertTrue(r['ok'])
        self.assertEqual(self.st.data_get('pull|TW|W40|1')['cells'][CELL]['html'], '최신')

    def test_refresh_all_data_groups_requests(self):
        self.pm(['W40', 'W41'], photos=False)
        before = len(self.mock.pulls)
        self.assertEqual(wj_app.refresh_all_data(self.st), 2)
        self.assertEqual(len(self.mock.pulls) - before, 1)              # 법인·사진 여부별로 한 번에
        self.assertEqual(sorted(self.mock.pulls[-1][1]), ['W40', 'W41'])

    def test_reset_clears_data_cache(self):
        self.pull()
        self.assertTrue(list((self.st.root / 'cache').glob('data_*.json')))
        self.st.cache_clear()
        self.assertFalse(list((self.st.root / 'cache').glob('data_*.json')))


class TestParallelPrefetch(AppCase):
    def test_prefetch_gets_all_pages_in_parallel(self):
        self.mock.page_delay = 0.4
        names = [f'{k}_TW' for k in wj_app.PREFETCH]
        t0 = time.time()
        self._prefetch(self.st, delay=0)
        self.assertTrue(wait(lambda: all(self.st.cache_get(n) for n in names if n != 'journal_TW'), 6))
        took = time.time() - t0
        sequential = 0.4 * (len(names) - 1)
        self.assertLess(took, sequential * 0.7)                         # 하나씩 받을 때(2.4초)보다 확실히 빠름
        self.assertEqual(len(names) - 1, len(set(self.mock.pagenames)))

    def test_prefetch_also_refreshes_cached_data(self):
        self.pull()
        self.mock.journal[CELL] = {'html': '미리 받은 새 글', 'version': 3, 'by': 'x', 'at': 'y'}
        self._prefetch(self.st, delay=0)
        self.assertTrue(wait(lambda: self.st.data_get('pull|TW|W40|1')['cells'][CELL]['html'] == '미리 받은 새 글', 6))


class TestAutoLogin(AppCase):
    def setUp(self):
        super().setUp()
        self._p, self._u = wj_app.protect_bytes, wj_app.unprotect_bytes
        wj_app.protect_bytes = lambda b: b'ENC:' + bytes(x ^ 0x5A for x in b)       # 윈도우 암호화(DPAPI) 흉내: 되돌릴 수 있는 가짜
        wj_app.unprotect_bytes = lambda b: bytes(x ^ 0x5A for x in b[4:]) if b.startswith(b'ENC:') else None

    def tearDown(self):
        wj_app.protect_bytes, wj_app.unprotect_bytes = self._p, self._u
        super().tearDown()

    def get_root(self):
        c = http.client.HTTPConnection('127.0.0.1', self.st.port, timeout=20)
        c.request('GET', '/', headers={'Cookie': 'wjk=' + self.st.key})
        r = c.getresponse()
        body = r.read().decode('utf-8')
        c.close()
        return r.status, body

    def login(self, remember):
        return self.api('/app/login', {'id': 'tw', 'password': 'pw12345678', 'who': 't', 'remember': remember})

    def test_remember_then_silent_login(self):
        self.login(True)
        raw = (self.st.root / 'cred.bin').read_bytes()
        self.assertNotIn(b'pw12345678', raw)                              # 파일에 비밀번호가 그대로 있지 않음
        self.st.clear_session()                                         # 다음 날 앱을 켠 상황
        n = self.mock.count('login')
        status, body = self.get_root()
        self.assertEqual(status, 200)
        self.assertNotIn('<form id="f">', body)                         # 로그인 화면이 아니라 일지 화면
        self.assertEqual(self.mock.count('login'), n + 1)
        self.assertIsNotNone(self.st.session)

    def test_not_remembered_by_default(self):
        self.login(False)
        self.assertFalse((self.st.root / 'cred.bin').exists())
        self.st.clear_session()
        status, body = self.get_root()
        self.assertIn('<form id="f">', body)
        self.assertIn('id="rm"', body)                                  # 자동 로그인 선택 칸이 보임

    def test_wrong_saved_password_is_forgotten(self):
        self.st.save_cred('tw', 'changed-password', 't')
        self.st.clear_session()
        status, body = self.get_root()
        self.assertIn('<form id="f">', body)
        self.assertFalse((self.st.root / 'cred.bin').exists())

    def test_offline_keeps_saved_login(self):
        self.login(True)
        self.st.clear_session()
        self.mock.offline = True
        status, body = self.get_root()
        self.assertIn('<form id="f">', body)
        self.assertTrue((self.st.root / 'cred.bin').exists())           # 인터넷 문제로는 지우지 않음

    def test_logout_forgets(self):
        self.login(True)
        self.api('/api', {'a': 'logout'})
        self.assertFalse((self.st.root / 'cred.bin').exists())

    def test_no_checkbox_when_encryption_unavailable(self):
        wj_app.protect_bytes = lambda b: None
        self.st.clear_session()
        status, body = self.get_root()
        self.assertNotIn('id="rm"', body)


class TestConsoleEncoding(AppCase):
    """윈도우 콘솔(cp1252)에서 한글 로그 줄이 요청 처리를 죽이지 않는지 (실제 윈도우 CI 에서 27개 시험이 전부 이 때문에 죽었음)."""

    def test_requests_survive_a_console_that_cannot_print_korean(self):
        import io
        real = sys.stdout
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding='cp1252', errors='strict')
        try:
            r = self.api('/app/login', {'id': 'tw', 'password': 'pw12345678', 'who': 't'})
            p = self.pull()
        finally:
            sys.stdout = real
        self.assertTrue(r['ok'])
        self.assertTrue(p['ok'])

    def test_log_and_notify_never_raise(self):
        import io
        real = sys.stdout
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding='cp1252', errors='strict')
        try:
            wj_app.log(self.st, '[서버] page 한글 0.1초')
            wj_app.notify('한글 메시지')
        finally:
            sys.stdout = real


if __name__ == '__main__':
    unittest.main(verbosity=2)
