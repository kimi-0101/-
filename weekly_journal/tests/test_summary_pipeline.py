# -*- coding: utf-8 -*-
"""SUMMARY 자동 정리 파이프라인 단위 테스트 (AI·시트 호출은 가짜로 대체)
실행: python -I weekly_journal/tests/test_summary_pipeline.py"""
import json, os, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import build_summary_draft as B
import summarize_cells as S

REAL_TRANSLATE = S.translate_struct

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

    def test_multiline_core_drops_only_bad_line(self):
        cells = CELLS + [{'sec': 'sec6', 'dept': '영업', 'item': '결과', 'text': '온라인 20% 증가, 오프라인 5% 감소'}]
        out = {'sec5': {}, 'sec6': {'영업': {'결과': [['온라인 20% 증가', '오프라인 5% 감소', '전 채널 777% 성장'], None]}}, 'sec7': {}}
        disp, dropped = B.make_display(out, [('sec6', '영업', '결과', ['777'])], [], cells, '')
        self.assertEqual(disp['sec6']['영업']['결과'][0], ['온라인 20% 증가', '오프라인 5% 감소'])
        self.assertEqual(len(dropped), 1)

    def test_multiline_unlocatable_flag_drops_label(self):
        cells = [{'sec': 'sec6', 'dept': '영업', 'item': '결과', 'text': '온라인 20% 증가, 오프라인 5% 감소'}]
        out = {'sec5': {}, 'sec6': {'영업': {'결과': [['온라인 20% 증가', '오프라인 5% 감소'], None]}}, 'sec7': {}}
        disp, _ = B.make_display(out, [], [{'위치': 'sec6/영업/결과/핵심'}], cells, '')
        self.assertEqual(disp['sec6'], {})

    def test_render_multiline(self):
        import summary_render as SR
        h = SR._cards('sec6', {'sec6': {'영업': {'결과': [['가', '나'], None]}}}, 'ko')
        self.assertEqual(h.count('class="cr"'), 2)


class Tr(unittest.TestCase):
    KO = {'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['2단계 20% 확대']}}

    def setUp(self):
        S.translate_struct = REAL_TRANSLATE

    def test_gemini_ok_no_claude(self):
        S.call_gemini = lambda p, timeout=120: json.dumps({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['Stage 2, 20% expansion']}})
        S.call_claude = lambda p, model=None: (_ for _ in ()).throw(AssertionError('claude'))
        self.assertTrue(S.translate_struct(self.KO, '영어'))

    def test_digit_mismatch_falls_back_to_claude(self):
        S.call_gemini = lambda p, timeout=120: json.dumps({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['Stage two, 20% expansion']}})
        S.call_claude = lambda p, model=None: json.dumps({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['Stage 2, 20% expansion']}})
        self.assertEqual(S.translate_struct(self.KO, '영어')['sec7']['GM'], ['Stage 2, 20% expansion'])

    def test_month_digit_may_drop_in_english_but_new_numbers_may_not(self):
        ko = {'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['9월 목표 20% 달성']}}
        S.call_gemini = lambda p, timeout=120: json.dumps({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['September target 20% achieved']}})
        S.call_claude = lambda p, model=None: (_ for _ in ()).throw(AssertionError('claude'))
        self.assertTrue(S.translate_struct(ko, '영어'))                       # 9 가 사라져도 통과
        S.call_gemini = lambda p, timeout=120: json.dumps({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['September target 25% achieved']}})
        S.call_claude = lambda p, model=None: json.dumps({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['target 21% achieved']}})
        self.assertIsNone(S.translate_struct(ko, '영어'))                     # 새 숫자는 불통과

    def test_gemini_error_and_claude_bad_returns_none(self):
        def boom(p, timeout=120):
            raise RuntimeError('429')
        S.call_gemini = boom
        S.call_claude = lambda p, model=None: json.dumps({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['no digits']}})
        self.assertIsNone(S.translate_struct(self.KO, '영어'))


if __name__ == '__main__':
    unittest.main()
