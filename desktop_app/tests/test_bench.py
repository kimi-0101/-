# -*- coding: utf-8 -*-
"""속도 실측 도구(bench.py) 시험 — 느린 가짜 서버(구글 흉내)에서 '처음 vs 저장본' 차이가 숫자로 나오는지.
실행:  python -I desktop_app/tests/test_bench.py
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import bench         # noqa: E402
import mock_server   # noqa: E402
import wj_app        # noqa: E402


class TestBench(unittest.TestCase):
    def test_run_shows_cache_speedup_on_slow_server(self):
        mock = mock_server.Mock()
        mock.page_delay, mock.delay = 0.15, 0.3                         # 느린 서버 흉내
        mock.journal['TW|W40|MD|x|ko'] = {'html': 'a', 'version': 1, 'by': 'k', 'at': 'z'}
        srv = mock_server.start(mock)
        saved = wj_app.log
        try:
            lines = []
            rows = bench.run(mock.url, 'tw', 'pw12345678', 'bench', say=lines.append, weeks=['W40', 'W41'])
        finally:
            wj_app.log = saved
            srv.shutdown()
            srv.server_close()
        by = {r[0].split(' (')[0].split(' ')[0]: r for r in rows}
        names = [r[0] for r in rows]
        self.assertEqual(len(rows), 5)
        for name, cold, warm, note in rows[1:]:
            self.assertLess(warm, cold / 5, name)                      # 저장본이 최소 5배 빠름
            self.assertEqual(note if note and '받지' in note else '', '', name)
        self.assertGreater(rows[0][1], 0)
        text = '\n'.join(lines)
        self.assertIn('처음(서버)', text)
        self.assertIn('배', text)

    def test_wrong_password_stops(self):
        mock = mock_server.Mock()
        srv = mock_server.start(mock)
        saved = wj_app.log
        try:
            with self.assertRaises(RuntimeError):
                bench.run(mock.url, 'tw', 'wrong-password', 'bench', say=lambda *_: None)
        finally:
            wj_app.log = saved
            srv.shutdown()
            srv.server_close()

    def test_summarize_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = os.path.join(tmp, 'app.log')
            with open(f, 'w', encoding='utf-8') as fh:
                fh.write('10:00:01 [서버] page journal_TW 2.0초\n10:00:02 [서버] page summary_TW 4.0초\n'
                         '10:00:03 [서버] pullMany  3.0초\n10:00:04 [화면] journal_TW 저장본 0.01초 (저장된 지 3분)\n'
                         '10:00:05 [글] TW W40 0.02초 (저장본 1개 / 서버 0개)\n10:00:06 [서버] save  실패 0.1초: boom\n쓰레기 줄\n')
            out = []
            g = bench.summarize_log(f, say=out.append)
        self.assertEqual(sorted(g), ['글:저장본포함', '서버:page', '서버:pullMany', '서버:save(실패)', '화면:저장본'])
        self.assertEqual(g['서버:page'], [2.0, 4.0])
        self.assertTrue(any('3.00s' in x and 'page' in x for x in out))


if __name__ == '__main__':
    unittest.main(verbosity=2)
