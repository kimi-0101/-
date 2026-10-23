# -*- coding: utf-8 -*-
"""백업 복원·검증(restore_journal.py) 시험 — 실제 HTTP 로 PC 서버에 대해.
실행:  python -I pc_server/tests/test_restore.py
"""
import gzip
import json
import os
import sys
import tempfile
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import restore_journal as R   # noqa: E402
import wj_server as S         # noqa: E402

PW = 'password-1234'
A, B, C, D, E = ('TW|W41|MD|a|ko', 'TW|W41|MD|b|ko', 'TW|W41|MD|c|ko', 'TW|W41|MD|d|en', 'TW|W41|VMD|vthis_p1|ko')


class RestoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = S.Store(os.path.join(self.tmp.name, 'w.sqlite3'))
        self.store.init_defaults()
        for u in ('hq', 'tw'):
            self.store.set_password(u, PW)
        self.srv = S.make_server(self.store, '127.0.0.1', 0)
        self.url = 'http://127.0.0.1:%d/api' % self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.root = os.path.join(self.tmp.name, 'wj_backup')
        self.hq = R.post(self.url, {'a': 'login', 'id': 'hq', 'password': PW, 'who': 'x'})['token']
        # 서버 현재 상태: A 는 다른 내용, B 는 없음, C 는 같음
        self.save(A, '서버가 더 새로움', 0)
        self.save(C, '같은 글', 0)
        self.write('2026-10-20', 'TW_W41.json.gz', {
            A: {'html': '백업의 A', 'version': 1, 'by': 'kim', 'at': 'z', 'auto': False},
            B: {'html': '백업의 B', 'version': 1, 'by': 'kim', 'at': 'z', 'auto': False},
            C: {'html': '같은 글', 'version': 1, 'by': 'kim', 'at': 'z', 'auto': False},
            D: {'html': 'auto translated', 'version': 1, 'by': 'auto-translate', 'at': 'z', 'auto': True},
            E: {'html': None, 'version': 1, 'by': '', 'at': '', 'auto': False},
            'TW|W41|MD|e|ko': {'html': '<p> </p>', 'version': 1, 'by': 'kim', 'at': 'z', 'auto': False}})

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.store.db.close()
        self.tmp.cleanup()

    def write(self, day, name, cells, closed=False):
        os.makedirs(os.path.join(self.root, day), exist_ok=True)
        with gzip.open(os.path.join(self.root, day, name), 'wt', encoding='utf-8') as f:
            json.dump({'ent': name[:2], 'code': name.split('_')[1].split('.')[0], 'closed': closed, 'cells': cells}, f, ensure_ascii=False)

    def save(self, cid, html, base):
        return R.post(self.url, {'a': 'save', 'cellId': cid, 'html': html, 'base': base, 'token': self.hq})

    def live(self, cid):
        return R.post(self.url, {'a': 'pull', 'ent': 'TW', 'week': 'W41', 'photos': True, 'token': self.hq})['cells'].get(cid)

    def run_(self, **kw):
        return R.run(self.url, 'hq', PW, backup=self.root, say=lambda *_: None, **kw)


class TestRestore(RestoreCase):
    def test_verify_changes_nothing(self):
        t = self.run_(verify=True)
        self.assertEqual((t['same'], t['missing'], t['differs']), (1, 1, 1))
        self.assertEqual((t['skipped_photo'], t['skipped_auto'], t['empty']), (1, 1, 1))
        self.assertIsNone(self.live(B))
        self.assertEqual(self.live(A)['html'], '서버가 더 새로움')

    def test_dry_run_changes_nothing(self):
        self.run_(dry_run=True)
        self.assertIsNone(self.live(B))

    def test_default_fills_only_missing(self):
        t = self.run_()
        self.assertEqual(t['restored'], 1)
        self.assertEqual(self.live(B)['html'], '백업의 B')
        self.assertEqual(self.live(A)['html'], '서버가 더 새로움')        # 다른 내용은 건드리지 않음
        self.assertIsNone(self.live(D))                                  # 자동번역 칸은 건너뜀
        self.assertIsNone(self.live(E))
        self.assertEqual(self.live(C)['version'], 1)                     # 같은 칸은 버전도 그대로
        t2 = self.run_()
        self.assertEqual((t2['restored'], t2['missing']), (0, 0))        # 다시 해도 같은 결과

    def test_overwrite_restores_differing(self):
        t = self.run_(mode='overwrite')
        self.assertEqual(t['restored'], 2)
        c = self.live(A)
        self.assertEqual((c['html'], c['version']), ('백업의 A', 2))      # 새 버전으로 기록(이력이 남음)

    def test_include_auto(self):
        self.run_(include_auto=True)
        self.assertEqual(self.live(D)['html'], 'auto translated')

    def test_closed_week_restored_by_hq(self):
        R.post(self.url, {'a': 'close', 'ent': 'TW', 'week': 'W41', 'closed': True, 'token': self.hq})
        self.assertEqual(self.run_()['restored'], 1)

    def test_selects_latest_day_and_filters(self):
        self.write('2026-10-21', 'TW_W41.json.gz', {B: {'html': '최신 백업의 B', 'version': 2, 'by': 'k', 'at': 'z', 'auto': False}})
        self.write('2026-10-21', 'HK_W41.json.gz', {'HK|W41|MD|h|ko': {'html': 'hk', 'version': 1, 'by': 'k', 'at': 'z', 'auto': False}})
        self.run_(ent='TW')
        self.assertEqual(self.live(B)['html'], '최신 백업의 B')           # 가장 최근 날짜
        hk = R.post(self.url, {'a': 'pull', 'ent': 'HK', 'week': 'W41', 'photos': True, 'token': self.hq})
        self.assertEqual(hk['cells'], {})                                  # ent 필터
        t = self.run_(day='2026-10-20', ent='TW', codes=['W41'])
        self.assertEqual(t['missing'], 0)
        with self.assertRaises(RuntimeError):
            self.run_(day='2020-01-01')

    def test_conflict_is_counted_not_overwritten(self):
        orig = R.compare

        def stale_compare(b, live, include_auto=False):
            self.save(B, '그 사이 누가 씀', 0)                            # 비교 직후 서버에서 칸이 생김
            return orig(b, live, include_auto)
        R.compare = stale_compare
        try:
            t = self.run_()
        finally:
            R.compare = orig
        self.assertEqual((t['restored'], t['conflict']), (0, 1))
        self.assertEqual(self.live(B)['html'], '그 사이 누가 씀')

    def test_bad_login_and_missing_backup(self):
        with self.assertRaises(PermissionError):
            R.run(self.url, 'hq', 'wrong-password', backup=self.root, say=lambda *_: None)
        with self.assertRaises(RuntimeError):
            R.run(self.url, 'hq', PW, backup=os.path.join(self.tmp.name, 'none'), say=lambda *_: None)

    def test_cli_exit_codes(self):
        base = ['--api-url', self.url, '--id', 'hq', '--password', PW, '--backup', self.root]
        self.assertEqual(R.main(base + ['--verify']), 1)                 # 되돌릴 것이 남음
        self.assertEqual(R.main(base), 0)
        self.assertEqual(R.main(base + ['--verify']), 1)                 # A 가 아직 다름(missing 모드는 안 건드림)
        self.assertEqual(R.main(base + ['--mode', 'overwrite']), 0)
        self.assertEqual(R.main(base + ['--verify']), 0)                 # 이제 모두 같음
        self.assertEqual(R.main(['--api-url', self.url, '--id', 'hq', '--password', 'bad-bad-bad', '--backup', self.root]), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
