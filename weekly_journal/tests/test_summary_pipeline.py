# -*- coding: utf-8 -*-
"""SUMMARY 자동 정리 파이프라인 단위 테스트 (AI·시트 호출은 가짜로 대체)
실행: python -I weekly_journal/tests/test_summary_pipeline.py"""
import json, os, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import build_summary_draft as B
import summarize_cells as S

CELLS = [{'sec': 'sec6', 'dept': 'GM', 'item': '결과', 'text': '매출 100만 달성'},
         {'sec': 'sec7', 'dept': 'GM', 'item': '전략', 'text': '11월 행사 2회 진행'}]


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        B.DRAFT_DIR = self.tmp
        B.QUANT_DIR = os.path.join(self.tmp, 'q')
        self.calls = {'sum': 0, 'ver': 0, 'tr': 0}
        S.summarize = self._sum
        S.verify_claims = self._ver
        S.translate_struct = self._tr
        self.tr_fail = False

    def _sum(self, name, period, cells, quant):
        self.calls['sum'] += 1
        return {'sec5': {}, 'sec6': {'GM': {'결과': ['매출 100만 달성', None]}}, 'sec7': {'GM': ['11월 행사 2회 진행', '매출 999만 목표']}}, []

    def _ver(self, out, cells, quant):
        self.calls['ver'] += 1
        return []

    def _tr(self, ko, name):
        self.calls['tr'] += 1
        if self.tr_fail:
            raise RuntimeError('limit')
        return {'tag': name}

    def test_auto_codes(self):
        self.assertEqual(B.auto_codes(41, 2026), ['W41', 'M10', 'M09'])
        self.assertEqual(B.auto_codes(2, 2026), ['W2', 'M01'])

    def test_made_then_skip(self):
        self.assertEqual(B.build('TW', 'M09', cells=CELLS, say=lambda *_: None), 'made')
        self.assertEqual(self.calls, {'sum': 1, 'ver': 1, 'tr': 2})
        self.assertEqual(B.build('TW', 'M09', cells=CELLS, say=lambda *_: None), 'skip')
        self.assertEqual(self.calls['sum'], 1)

    def test_sec7_number_dropped(self):
        B.build('TW', 'M09', cells=CELLS, say=lambda *_: None)
        d = json.load(open(os.path.join(self.tmp, 'TW_M09.json'), encoding='utf-8'))
        self.assertEqual(d['display']['ko']['sec7']['GM'], ['11월 행사 2회 진행'])

    def test_translation_failure_then_filled(self):
        self.tr_fail = True
        B.build('HK', 'M09', cells=CELLS, say=lambda *_: None)
        self.tr_fail = False
        self.assertEqual(B.build('HK', 'M09', cells=CELLS, say=lambda *_: None), 'filled')
        self.assertEqual(self.calls['sum'], 1)          # 정리는 다시 부르지 않는다
        self.assertEqual(B.build('HK', 'M09', cells=CELLS, say=lambda *_: None), 'skip')

    def test_changed_source_rebuilds(self):
        B.build('TW', 'M09', cells=CELLS, say=lambda *_: None)
        c2 = [dict(CELLS[0], text='매출 100만 달성 후 유지')] + CELLS[1:]
        self.assertEqual(B.build('TW', 'M09', cells=c2, say=lambda *_: None), 'made')

    def test_empty(self):
        self.assertEqual(B.build('TW', 'M09', cells=[{'sec': 'sec6', 'dept': 'GM', 'item': 'x', 'text': '測試'}]), 'empty')

    def test_run_all_stops_after_two_failures(self):
        def boom(*a):
            raise RuntimeError('limit')
        S.summarize = boom
        B.R.read_many = lambda ent, codes: {c: (CELLS, {}) for c in codes}
        res = B.run_all(['TW'], ['W41', 'M10', 'M09'], say=lambda *_: None)
        self.assertEqual(res, {'TW W41': 'failed', 'TW M10': 'failed', 'TW M09': 'skipped'})

    def test_run_all_read_failure(self):
        def bad(ent, codes):
            raise RuntimeError('net')
        B.R.read_many = bad
        res = B.run_all(['HK'], ['M09'], say=lambda *_: None)
        self.assertEqual(res, {'HK M09': 'read-failed'})


if __name__ == '__main__':
    unittest.main()
