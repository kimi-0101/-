# -*- coding: utf-8 -*-
"""백업 도구 단위 테스트 (시트·로그인은 가짜). 실행: python -I pc_server/tests/test_backup.py"""
import datetime, gzip, json, os, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import backup_journal as B


class T(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()
        self.calls = []
        B.R.login = lambda: ('http://x', 'tok', {})
        B.R.post = self._post
        self.fail_chunk = None

    def _post(self, url, body, timeout=120):
        self.calls.append(body)
        if self.fail_chunk and body['weeks'][0] == self.fail_chunk:
            return {'ok': False, 'error': 'boom'}
        res = []
        for w in body['weeks']:
            if w in ('W41', 'M09') and body['ent'] == 'TW':
                res.append({'ok': True, 'cells': {f'TW|{w}|gm|a|ko': {'html': '<p>글</p>', 'version': 1}}, 'closed': False})
            else:
                res.append({'ok': True, 'cells': {}, 'closed': False})
        return {'ok': True, 'results': res}

    def test_saves_only_weeks_with_cells(self):
        now = datetime.datetime(2026, 10, 19, 5, 0)
        st = B.run(self.out, now=now, say=lambda *_: None)
        self.assertEqual(st['saved'], 2)
        self.assertEqual(st['failed'], 0)
        p = os.path.join(self.out, '2026-10-19', 'TW_W41.json.gz')
        d = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        self.assertEqual(d['ent'], 'TW')
        self.assertIn('TW|W41|gm|a|ko', d['cells'])
        self.assertEqual(st['empty'], 65 * 2 - 2)

    def test_rerun_same_day_skips_done(self):
        now = datetime.datetime(2026, 10, 19, 5, 0)
        B.run(self.out, now=now, say=lambda *_: None)
        n = len(self.calls)
        st = B.run(self.out, now=now, say=lambda *_: None)
        self.assertEqual(st['saved'], 0)
        self.assertGreater(len(self.calls), n)       # 글 없는 코드는 파일이 없어 다시 묻지만 저장본은 다시 받지 않는다

    def test_chunk_failure_counted_and_others_continue(self):
        self.fail_chunk = 'W9'
        st = B.run(self.out, now=datetime.datetime(2026, 10, 19), say=lambda *_: None)
        self.assertEqual(st['failed'], 8 * 2)
        self.assertEqual(st['saved'], 2)

    def test_prune_keeps_recent_and_ignores_other_folders(self):
        for n in ('2026-08-01', '2026-10-10', 'notes'):
            os.makedirs(os.path.join(self.out, n))
        removed = B.prune(self.out, 30, datetime.date(2026, 10, 19))
        self.assertEqual(removed, ['2026-08-01'])
        self.assertTrue(os.path.isdir(os.path.join(self.out, 'notes')))

    def test_codes_cover_weeks_and_months(self):
        c = B.all_codes()
        self.assertIn('W53', c); self.assertIn('M09', c); self.assertNotIn('M9', c); self.assertEqual(len(c), 65)


if __name__ == '__main__':
    unittest.main()
