# -*- coding: utf-8 -*-
"""SUMMARY 자동 정리 파이프라인 단위 테스트 (AI·시트 호출은 가짜로 대체)
실행: python -I weekly_journal/tests/test_summary_pipeline.py"""
import datetime, json, os, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import build_summary_draft as B
import summarize_cells as S

REAL_TRANSLATE = S.translate_struct
REAL_CALL_CLAUDE = S.call_claude
REAL_SUMMARIZE = S.summarize
REAL_VERIFY = S.verify_claims

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

    def test_translations_run_concurrently(self):
        import time
        def slow(ko, name):
            time.sleep(0.3)
            return {'tag': name}
        S.translate_struct = slow
        out = {'sec5': {}, 'sec6': {'GM': {'결과': ['매출 100만 달성', None]}}, 'sec7': {}}
        t0 = time.time()
        res, _ = B.build_display_i18n(out, [], [], CELLS, '', say=lambda *_: None)
        self.assertLess(time.time() - t0, 0.55)                    # 순서대로면 0.6초 이상
        self.assertEqual(sorted(res), ['en', 'ko', 'zh'])

    def test_comma_and_plain_numbers_are_the_same_number(self):
        self.assertEqual(S.nums('6,800 와 6800 그리고 10,800'), {'6800', '10800'})
        cells = [{'sec': '5', 'dept': '영업', 'item': '경쟁사 동향', 'text': '노스페이스 6,800 대만달러 이상, AAPE 10,800'}]
        out = {'sec5': {'영업': {'동향': [['노스페이스 6800대만달러 이상', 'AAPE 10800대만달러'], None]}}, 'sec6': {}, 'sec7': {}}
        self.assertEqual(S.check_numbers(out, cells, ''), [])
        disp, dropped = B.make_display(out, [], [], cells, '')
        self.assertEqual(dropped, [])

    def test_dropped_line_reason_is_logged(self):
        cells = [{'sec': '5', 'dept': '영업', 'item': '경쟁사 동향', 'text': '노스페이스 6,800 대만달러'}]
        out = {'sec5': {'영업': {'동향': [['노스페이스 6800대만달러', '출처 없는 9999 증가'], None]}}, 'sec6': {}, 'sec7': {}}
        disp, dropped = B.make_display(out, [], [], cells, '')
        self.assertEqual(len(dropped), 1); self.assertIn('숫자', dropped[0]); self.assertIn('9999', dropped[0])

    def test_auto_codes(self):
        D = datetime.date
        self.assertEqual(B.auto_codes(41, 2026, today=D(2026, 10, 19)), ['W41', 'M10'])          # 중순 이후엔 지난 달을 다시 보지 않는다
        self.assertEqual(B.auto_codes(41, 2026, today=D(2026, 10, 6)), ['W41', 'M10', 'M09'])    # 월초엔 지난 달도
        self.assertEqual(B.auto_codes(2, 2026, today=D(2026, 1, 8)), ['W2', 'M01'])

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
        self.assertEqual(B.build('TW', 'M09', cells=c2, say=lambda *_: None), 'updated')      # 바뀐 부서만 다시 요약

    def test_empty(self):
        self.assertEqual(B.build('TW', 'M09', cells=[{'sec': 'sec6', 'dept': 'GM', 'item': 'x', 'text': '測試'}]), 'empty')

    def test_run_all_stops_after_two_consecutive_failures(self):
        def boom(*a):
            raise RuntimeError('boom')
        S.summarize = boom
        B.R.read_many = lambda ent, codes: {c: (CELLS, {}) for c in codes}
        res = B.run_all(['TW'], ['W41', 'M10', 'M09'], say=lambda *_: None)
        self.assertEqual(res, {'TW W41': 'failed', 'TW M10': 'failed', 'TW M09': 'skipped'})

    def test_run_all_stops_immediately_on_limit_error(self):
        def lim(*a):
            raise RuntimeError("You've hit your session limit")
        S.summarize = lim
        B.R.read_many = lambda ent, codes: {c: (CELLS, {}) for c in codes}
        res = B.run_all(['TW'], ['W41', 'M10', 'M09'], say=lambda *_: None)
        self.assertEqual(res, {'TW W41': 'failed', 'TW M10': 'skipped', 'TW M09': 'skipped'})

    def test_run_all_runs_codes_concurrently(self):
        import time
        def slow(name, period, cells, quant):
            time.sleep(0.3)
            return {'sec5': {}, 'sec6': {'GM': {'결과': ['매출 100만 달성', None]}}, 'sec7': {}}, []
        S.summarize = slow
        B.R.read_many = lambda ent, codes: {c: (CELLS, {}) for c in codes}
        t0 = time.time()
        res = B.run_all(['HK', 'TW'], ['W41', 'M10'], say=lambda *_: None, workers=4)
        self.assertLess(time.time() - t0, 0.7)                       # 차례로 하면 1.2초 이상
        self.assertEqual(sorted(res.values()), ['made'] * 4)
        self.assertEqual(list(res), ['HK W41', 'HK M10', 'TW W41', 'TW M10'])      # 결과 순서는 그대로

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
        h = SR._rows('sec6', {'sec6': {'영업': {'결과': [['가', '나'], None]}}}, 'ko')
        self.assertEqual(h.count('<p>'), 2)                                      # 다른 맥락은 한 배지 아래에서 줄을 나눈다
        self.assertEqual(h.count('<tr>'), 1)
        self.assertIn('<td class="dp">영업</td>', h)                              # 왼쪽 칸은 부서명만
        self.assertIn('<span class="bd">결과</span>', h)                          # 배지는 오른쪽 내용 칸 안

    def test_render_one_row_per_dept_with_badges_in_the_content_cell_and_merge_keeps_raw_table_folded(self):
        import summary_render as SR
        data = {'ko': {'sec5': {}, 'sec6': {'영업': {'결과': ['매출 20% 증가', None], '원인': ['연휴', None]}, 'GM': {'조치': ['집중관리', None]}},
                       'sec7': {'GM': ['11월 행사', '12월 점검'], 'GM(HQ 요청)': ['보고 간소화']}}}
        c6 = SR._rows('sec6', data['ko'], 'ko')
        self.assertEqual(c6.count('<tr>'), 2)                                     # 부서마다 한 행
        self.assertLess(c6.index('<td class="dp">GM</td>'), c6.index('<td class="dp">영업</td>'))   # 부서 순서(GM 먼저)
        self.assertEqual(c6.count('class="bd"'), 3)                               # 영업 2개(결과·원인) + GM 1개(조치)
        self.assertLess(c6.index('>결과<'), c6.index('>원인<'))                       # 한 부서 안에서는 결과 → 원인 순서
        self.assertEqual(c6.count('<td class="dp">영업</td>'), 1)                  # 부서명은 한 번만
        c7 = SR._rows('sec7', data['ko'], 'ko')
        self.assertIn('<p>2. 12월 점검</p>', c7)
        self.assertEqual(c7.count('<td class="dp">GM</td>'), 2)                    # GM 전략 행 + GM HQ 요청 행
        self.assertEqual(c7.count('class="bd"'), 1); self.assertIn('<span class="bd">HQ 요청사항</span>', c7)
        orig = '<div class="sec"><h3>6</h3><table class="t3"><tr><td>원문</td></tr></table></div>'
        merged = SR.merge(orig, '<table class="t3 smt">' + c6 + '</table>')
        self.assertTrue(merged.index('smt') < merged.index('<details class="raw">'))        # 요약 표가 위, 원문은 접힘 아래
        self.assertEqual(merged.count('</details>'), 1)
        self.assertTrue(merged.index('<td>원문</td>') > merged.index('<details class="raw">'))
        self.assertTrue(merged.index('</details>') > merged.index('<td>원문</td>'))        # 원문 표가 details 안에 들어 있다
        self.assertEqual(SR.merge('<div>표 없음</div>', c6), '<div>표 없음</div>')


def R(struct, **kw):
    """번역 응답(번호 → 문장)을 번역된 구조에서 만든다 (번역기는 키·구조 없이 번호만 주고받는다)"""
    return json.dumps({str(i + 1): s for i, s in enumerate(S._texts(struct))}, ensure_ascii=False)


def _map_str(x, f):
    if isinstance(x, dict):
        return {k: _map_str(v, f) for k, v in x.items()}
    if isinstance(x, list):
        return [_map_str(v, f) for v in x]
    return f(x) if isinstance(x, str) else x


class Batch(unittest.TestCase):
    """부서 묶음을 동시에 정리·검증"""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        B.DRAFT_DIR = self.tmp
        B.QUANT_DIR = os.path.join(self.tmp, 'q')
        self.calls = []
        S.translate_struct = lambda struct, name: struct
        self.cells = [{'sec': '6', 'dept': d, 'item': '총평', 'text': f'{d} 원문 가나다라'} for d in ('영업', 'GM', 'EC', '마케팅', 'HR')]

    def test_depts_are_split_into_batches_and_merged(self):
        import time
        def summarize(name, period, cells, quant):
            time.sleep(0.3)
            self.calls.append(sorted({c['dept'] for c in cells}))
            return {'sec5': {}, 'sec6': {c['dept']: {'결과': [c['text'], None]} for c in cells}, 'sec7': {}}, [{'x': 1}] if len(cells) == 1 else []
        S.summarize = summarize
        S.verify_claims = lambda out, cells, quant='', model=None: [{'위치': 'sec6/%s/결과' % cells[0]['dept'], '문장': 'x', '문제': 'y'}]
        os.environ['WJ_REPAIR'] = '0'
        os.environ['WJ_BATCH'] = '2'
        try:
            t0 = time.time()
            out, flags, warn = B.summarize_verify('홍콩', 'W41', self.cells, '', say=lambda *_: None)
            dt = time.time() - t0
        finally:
            os.environ.pop('WJ_BATCH', None); os.environ.pop('WJ_REPAIR', None)
        self.assertEqual(len(self.calls), 3)                                   # 5개 부서 → 2+2+1 묶음
        self.assertEqual(sorted(sum(self.calls, [])), ['EC', 'GM', 'HR', '마케팅', '영업'])
        self.assertEqual(sorted(out['sec6']), ['EC', 'GM', 'HR', '마케팅', '영업'])   # 합쳐진 결과
        self.assertEqual(len(warn), 3); self.assertEqual(len(flags), 1)
        self.assertLess(dt, 0.8)                                               # 차례로 하면 0.9초 이상

    def test_one_batch_failure_raises_and_nothing_is_saved(self):
        def summarize(name, period, cells, quant):
            if any(c['dept'] == 'HR' for c in cells):
                raise RuntimeError('boom')
            return {'sec5': {}, 'sec6': {}, 'sec7': {}}, []
        S.summarize = summarize
        S.verify_claims = lambda *a, **k: []
        os.environ['WJ_BATCH'] = '2'
        try:
            with self.assertRaises(RuntimeError):
                B.build('HK', 'W41', cells=self.cells, say=lambda *_: None)
        finally:
            os.environ.pop('WJ_BATCH', None)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'HK_W41.json')))



class Repair(unittest.TestCase):
    """검증이 지적한 줄을 버리지 않고 다시 쓰게 한다"""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        B.DRAFT_DIR = self.tmp
        S.GEMINI_RETRY_WAIT = 0
        self.cells = [{'sec': '6', 'dept': '영업', 'item': '총평', 'text': '시티게이트 +2% (황금연휴 전 관광객 감소), 요호 +8%'},
                      {'sec': '7', 'dept': '영업', 'item': '향후전략', 'text': '10월 프로모션 진행 11월 재고 정리'}]
        self.out = {'sec5': {}, 'sec6': {'영업': {'원인': [['시티게이트 성장 둔화는 황금연휴 전 관광객 감소', '요호는 북행 여행객 증가'], None]}},
                    'sec7': {'영업': ['10월 프로모션 진행', '11월 재고 정리 대성공']}}
        self.warns = [{'위치': 'sec6/영업/원인/핵심', '문장': '시티게이트 성장 둔화는 황금연휴 전 관광객 감소', '문제': "'성장 둔화' 평가는 원문에 없음"},
                      {'위치': 'sec7/영업', '문장': '11월 재고 정리 대성공', '문제': "'대성공' 은 원문에 없음"}]
        self.calls = []

    def _claude(self, answers):
        def f(p, model=None, **kw):
            self.calls.append(p)
            return json.dumps(answers)
        S.call_claude = f

    def test_flagged_lines_are_rewritten_and_reverified(self):
        self._claude({'1': '시티게이트 +2%, 황금연휴 전 관광객 감소', '2': '11월 재고 정리'})
        S.verify_claims = lambda out, cells, quant='', model=None: []
        out, left, n = S.repair_flagged(self.out, self.warns, self.cells)
        self.assertEqual(n, 2); self.assertEqual(left, [])
        self.assertEqual(out['sec6']['영업']['원인'][0], ['시티게이트 +2%, 황금연휴 전 관광객 감소', '요호는 북행 여행객 증가'])   # 다른 줄은 그대로
        self.assertEqual(out['sec7']['영업'], ['10월 프로모션 진행', '11월 재고 정리'])
        self.assertIn('성장 둔화', json.dumps(self.out, ensure_ascii=False))                                               # 원본은 바뀌지 않는다
        self.assertEqual(len(self.calls), 1)

    def test_rewrite_with_new_number_or_null_is_rejected(self):
        self._claude({'1': '시티게이트 +9%', '2': None})
        S.verify_claims = lambda *a, **k: []
        out, left, n = S.repair_flagged(self.out, self.warns, self.cells)
        self.assertEqual(n, 0); self.assertEqual(len(left), 2)

    def test_reverification_failure_keeps_warning(self):
        self._claude({'1': '시티게이트 성장 부진', '2': '11월 재고 정리'})
        S.verify_claims = lambda out, cells, quant='', model=None: [{'위치': 'sec6/영업/원인/핵심', '문장': '시티게이트 성장 부진', '문제': '평가'}]
        out, left, n = S.repair_flagged(self.out, self.warns, self.cells)
        self.assertEqual(n, 2)
        self.assertEqual([w['문장'] for w in left], ['시티게이트 성장 부진'])

    def test_unlocatable_warning_is_left_alone_without_calling_ai(self):
        self._claude({})
        out, left, n = S.repair_flagged(self.out, [{'위치': 'sec6/없는부서/결과', '문장': 'x', '문제': 'y'}], self.cells)
        self.assertEqual((n, len(left), len(self.calls)), (0, 1, 0))

    def test_repair_command_runs_the_check_afterwards(self):
        import io, contextlib
        self._claude({})
        S.verify_claims = lambda *a, **k: []
        S.translate_struct = lambda struct, name: _map_str(struct, lambda s: f'{name[:2]}|{s}')
        ko, dropped = B.make_display(self.out, [], [], self.cells, '')
        draft = {'ent': 'HK', 'code': 'M09', 'cells': self.cells, 'quant': '', 'out': self.out, 'flags': [], 'warn': [], 'dropped': [],
                 'display': {'ko': ko}}                                          # 번역이 아직 없는 상태
        json.dump(draft, open(os.path.join(self.tmp, 'HK_M09.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = B.main(['--repair', '--code', 'M09', '--ent', 'HK'])
        text = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn('--- 점검 ---', text); self.assertIn('[통과] HK M09', text); self.assertIn('점검 결과: 모두 통과', text)

    def test_repair_existing_updates_draft_translations_only_for_changed_lines(self):
        self._claude({'1': '시티게이트 +2%, 황금연휴 전 관광객 감소', '2': '11월 재고 정리'})
        S.verify_claims = lambda *a, **k: []
        seen = []
        def tr(struct, name):
            seen.append(struct)
            return _map_str(struct, lambda s: f'{name[:2]}|{s}')
        S.translate_struct = tr
        ko, dropped = B.make_display(self.out, [], self.warns, self.cells, '')
        draft = {'ent': 'HK', 'code': 'M09', 'cells': self.cells, 'quant': '', 'out': self.out, 'flags': [], 'warn': self.warns, 'dropped': dropped,
                 'display': {'ko': ko, 'en': _map_str(ko, lambda s: f'영어|{s}'), 'zh': _map_str(ko, lambda s: f'중국|{s}')}}
        json.dump(draft, open(os.path.join(self.tmp, 'HK_M09.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        self.assertEqual(B.repair_existing('HK', 'M09', say=lambda *_: None), 'repaired')
        d = json.load(open(os.path.join(self.tmp, 'HK_M09.json'), encoding='utf-8'))
        self.assertEqual(d['warn'], []); self.assertEqual(d['dropped'], [])
        self.assertIn('황금연휴', json.dumps(d['display']['ko'], ensure_ascii=False))
        self.assertEqual(sorted(d['display']), ['en', 'ko', 'zh'])
        self.assertTrue(all(isinstance(s, dict) for s in seen) and len(seen) == 2)           # 영어·중국어 각각 한 번(바뀐 줄만)


class Inc(unittest.TestCase):
    """부서 단위 증분 요약: 바뀐 부서만 다시 요약·검증·번역한다"""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        B.DRAFT_DIR = self.tmp
        B.QUANT_DIR = os.path.join(self.tmp, 'q')
        self.sum_calls, self.ver_calls, self.tr_calls = [], [], []
        self.fail_tr = False
        S.GEMINI_RETRY_WAIT = 0

        def summarize(name, period, cells, quant):
            self.sum_calls.append(sorted({c['dept'] for c in cells}))
            out = {'sec5': {}, 'sec6': {}, 'sec7': {}}
            for c in cells:
                if c['sec'] == '6':
                    out['sec6'].setdefault(c['dept'], {})['결과'] = [f"{c['dept']}:{c['text']}", None]
                if c['sec'] == '7':
                    key = 'GM(HQ 요청)' if c['item'] == 'HQ 요청사항' else c['dept']
                    out['sec7'].setdefault(key, []).append(c['text'])
            return out, []
        S.summarize = summarize
        S.verify_claims = lambda out, cells, quant='', model=None: (self.ver_calls.append(sorted({c['dept'] for c in cells})), [])[1]

        def tr(struct, name):
            if self.fail_tr:
                raise RuntimeError('limit')
            self.tr_calls.append((name, struct))
            return _map_str(struct, lambda s: f'{name[:2]}|{s}')
        S.translate_struct = tr
        self.cells = [{'sec': '6', 'dept': '영업', 'item': '총평', 'text': '영업 원문 가나다라'},
                      {'sec': '6', 'dept': 'GM', 'item': '총평', 'text': 'GM 원문 가나다라'},
                      {'sec': '7', 'dept': 'GM', 'item': '향후전략', 'text': 'GM 전략 하나둘셋'},
                      {'sec': '7', 'dept': 'GM', 'item': 'HQ 요청사항', 'text': 'HQ 요청 하나둘셋'}]
        self.say = lambda *_: None

    def load(self):
        return json.load(open(os.path.join(self.tmp, 'HK_W41.json'), encoding='utf-8'))

    def test_only_changed_dept_is_summarized_verified_and_translated(self):
        self.assertEqual(B.build('HK', 'W41', cells=self.cells, say=self.say), 'made')
        self.assertEqual((self.sum_calls, self.ver_calls), ([['GM', '영업']], [['GM', '영업']]))
        first = self.load()
        self.tr_calls.clear()
        c2 = [dict(c, text='영업 원문 새로 고침') if c['dept'] == '영업' else c for c in self.cells]
        self.assertEqual(B.build('HK', 'W41', cells=c2, say=self.say), 'updated')
        self.assertEqual(self.sum_calls[-1], ['영업'])                                  # 영업만 요약
        self.assertEqual(self.ver_calls[-1], ['영업'])                                  # 영업만 검증
        d = self.load()
        self.assertEqual(d['out']['sec6']['GM'], first['out']['sec6']['GM'])             # GM 은 그대로
        self.assertEqual(d['out']['sec7']['GM(HQ 요청)'], first['out']['sec7']['GM(HQ 요청)'])
        self.assertIn('새로 고침', d['display']['ko']['sec6']['영업']['결과'][0])
        for name, struct in self.tr_calls:                                               # 번역도 바뀐 줄만
            self.assertEqual(list(struct['sec6']), ['영업']); self.assertEqual(struct['sec7'], {})
        self.assertEqual(sorted(d['display']), ['en', 'ko', 'zh'])
        self.assertTrue(d['display']['en']['sec6']['GM']['결과'][0].startswith('영어|'))   # GM 번역은 기존 것을 유지
        self.assertIn('새로 고침', d['display']['zh']['sec6']['영업']['결과'][0])

    def test_hq_request_belongs_to_gm(self):
        B.build('HK', 'W41', cells=self.cells, say=self.say)
        c2 = [dict(c, text='GM 전략 다시 씀 하나') if c['item'] == '향후전략' else c for c in self.cells]
        B.build('HK', 'W41', cells=c2, say=self.say)
        self.assertEqual(self.sum_calls[-1], ['GM'])
        d = self.load()
        self.assertIn('GM(HQ 요청)', d['out']['sec7'])                                    # GM 이 바뀌면 GM(HQ 요청)도 함께 새로 만들어짐
        self.assertEqual(d['out']['sec7']['GM'], ['GM 전략 다시 씀 하나'])

    def test_legacy_draft_without_dept_hash_is_adopted_without_ai(self):
        B.build('HK', 'W41', cells=self.cells, say=self.say)
        d = self.load(); d.pop('dept_hash'); d.pop('hash')                              # 예전 형식 저장본
        json.dump(d, open(os.path.join(self.tmp, 'HK_W41.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        n = (len(self.sum_calls), len(self.ver_calls), len(self.tr_calls))
        self.assertEqual(B.build('HK', 'W41', cells=self.cells, say=self.say), 'skip')
        self.assertEqual((len(self.sum_calls), len(self.ver_calls), len(self.tr_calls)), n)   # AI 호출 0

    def test_legacy_draft_with_test_input_cell_is_still_adopted(self):
        B.build('HK', 'W41', cells=self.cells, say=self.say)
        d = self.load(); d.pop('dept_hash'); d.pop('hash')
        d['cells'] = d['cells'] + [{'sec': '6', 'dept': '영업', 'item': '특이사항', 'text': '測試'}]      # 예전 저장본에 남은 2자 시험 입력
        json.dump(d, open(os.path.join(self.tmp, 'HK_W41.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        n = len(self.sum_calls)
        self.assertEqual(B.build('HK', 'W41', cells=self.cells, say=self.say), 'skip')
        self.assertEqual(len(self.sum_calls), n)

    def test_removed_dept_needs_no_ai_and_is_dropped_everywhere(self):
        B.build('HK', 'W41', cells=self.cells, say=self.say)
        n = (len(self.sum_calls), len(self.ver_calls), len(self.tr_calls))
        c2 = [c for c in self.cells if c['dept'] != '영업']
        self.assertEqual(B.build('HK', 'W41', cells=c2, say=self.say), 'updated')
        self.assertEqual((len(self.sum_calls), len(self.ver_calls), len(self.tr_calls)), n)
        d = self.load()
        for lg in ('ko', 'en', 'zh'):
            self.assertNotIn('영업', d['display'][lg]['sec6'])
            self.assertIn('GM', d['display'][lg]['sec6'])

    def test_translation_failure_in_partial_update_is_filled_later_by_full_translation(self):
        B.build('HK', 'W41', cells=self.cells, say=self.say)
        c2 = [dict(c, text='영업 원문 새로 고침') if c['dept'] == '영업' else c for c in self.cells]
        self.fail_tr = True
        B.build('HK', 'W41', cells=c2, say=self.say)
        self.assertEqual(sorted(self.load()['display']), ['ko'])                          # 낡은 번역을 섞어 두지 않고 비워 둔다
        self.fail_tr = False
        self.assertEqual(B.build('HK', 'W41', cells=c2, say=self.say), 'filled')
        self.assertEqual(sorted(self.load()['display']), ['en', 'ko', 'zh'])

    def test_unchanged_is_skipped_and_force_redoes_everything(self):
        B.build('HK', 'W41', cells=self.cells, say=self.say)
        self.assertEqual(B.build('HK', 'W41', cells=self.cells, say=self.say), 'skip')
        self.assertEqual(B.build('HK', 'W41', cells=self.cells, force=True, say=self.say), 'made')
        self.assertEqual(self.sum_calls[-1], ['GM', '영업'])

    def test_hand_made_translation_survives_unrelated_dept_change(self):
        B.build('HK', 'W41', cells=self.cells, say=self.say)
        d = self.load(); d['display']['en']['sec6']['GM']['결과'][0] = '손으로 다듬은 번역'
        json.dump(d, open(os.path.join(self.tmp, 'HK_W41.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        c2 = [dict(c, text='영업 원문 새로 고침') if c['dept'] == '영업' else c for c in self.cells]
        B.build('HK', 'W41', cells=c2, say=self.say)
        self.assertEqual(self.load()['display']['en']['sec6']['GM']['결과'][0], '손으로 다듬은 번역')


class GeminiCall(unittest.TestCase):
    def setUp(self):
        import urllib.request, urllib.error
        self.ur, self.ue = urllib.request, urllib.error
        self.real_urlopen = urllib.request.urlopen
        S.GEMINI_RETRY_WAIT = 0
        S._GEMINI_DOWN['until'] = 0.0
        os.environ['GEMINI_API_KEY'] = 'k'
        self.urls = []

    def tearDown(self):
        self.ur.urlopen = self.real_urlopen
        S._GEMINI_DOWN['until'] = 0.0
        os.environ.pop('GEMINI_API_KEY', None)

    def _resp(self, text):
        import io
        return io.BytesIO(json.dumps({'candidates': [{'content': {'parts': [{'text': text}]}}]}).encode('utf-8'))

    def _http(self, code):
        import io
        return self.ue.HTTPError('u', code, 'err', {}, io.BytesIO(b'{}'))

    def test_retries_on_429_then_succeeds(self):
        seq = [self._http(429), self._http(503), None]
        def fake(req, timeout=0):
            self.urls.append(req.full_url)
            e = seq.pop(0)
            if e: raise e
            return self._resp('{"ok":1}')
        self.ur.urlopen = fake
        self.assertEqual(S.call_gemini('p'), '{"ok":1}')
        self.assertEqual(len(self.urls), 3)

    def test_model_404_falls_back_to_alias(self):
        def fake(req, timeout=0):
            self.urls.append(req.full_url)
            if 'gemini-flash-latest' not in req.full_url:
                raise self._http(404)
            return self._resp('{}')
        self.ur.urlopen = fake
        S.call_gemini('p')
        self.assertIn('gemini-flash-latest', self.urls[-1])

    def test_gemini_rate_limit_pauses_gemini_for_a_while(self):
        n = []
        def fake(req, timeout=0):
            n.append(1); raise self._http(429)
        self.ur.urlopen = fake
        with self.assertRaises(RuntimeError):
            S.call_gemini('p')
        first = len(n)
        with self.assertRaises(RuntimeError) as cm:
            S.call_gemini('p')
        self.assertEqual(len(n), first)                                          # 두 번째는 호출 없이 바로 실패
        self.assertIn('건너뜀', str(cm.exception))

    def test_gives_up_with_runtime_error_and_other_http_errors_are_not_retried(self):
        self.ur.urlopen = lambda req, timeout=0: (_ for _ in ()).throw(self._http(429))
        with self.assertRaises(RuntimeError) as cm:
            S.call_gemini('p')
        self.assertIn('429', str(cm.exception))
        S._GEMINI_DOWN['until'] = 0.0
        n = []
        def fake(req, timeout=0):
            n.append(1); raise self._http(400)
        self.ur.urlopen = fake
        with self.assertRaises(RuntimeError):
            S.call_gemini('p')
        self.assertEqual(len(n), 1)


class Tr(unittest.TestCase):
    KO = {'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['2단계 20% 확대']}}
    OK = R({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['Stage 2, 20% expansion']}})
    BAD = R({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['Stage 3, 20% expansion']}})

    def setUp(self):
        S.translate_struct = REAL_TRANSLATE
        S.GEMINI_RETRY_WAIT = 0
        os.environ['WJ_TRANSLATOR'] = 'auto'                       # 이 클래스는 Gemini 경로(auto)를 시험한다. 기본값(claude)은 아래 별도 시험
        self.addCleanup(os.environ.pop, 'WJ_TRANSLATOR', None)
        self.claude_calls = 0
        def claude(p, model=None, **kw):
            self.claude_calls += 1
            return self.OK
        S.call_claude = claude

    def test_gemini_ok_no_claude(self):
        S.call_gemini = lambda p, timeout=120: self.OK
        self.assertTrue(S.translate_struct(self.KO, '영어'))
        self.assertEqual(self.claude_calls, 0)

    def test_digit_mismatch_retries_gemini_with_reason_not_claude(self):
        seen = []
        def g(p, timeout=120):
            seen.append(p)
            return self.BAD if len(seen) == 1 else self.OK
        S.call_gemini = g
        self.assertTrue(S.translate_struct(self.KO, '영어'))
        self.assertIn('이전 번역의 문제', seen[1])
        self.assertEqual(self.claude_calls, 0)

    def test_gemini_keeps_failing_falls_back_to_claude_once(self):
        S.call_gemini = lambda p, timeout=120: self.BAD
        self.assertTrue(S.translate_struct(self.KO, '영어'))
        self.assertEqual(self.claude_calls, 1)

    def test_gemini_error_twice_falls_back_to_claude(self):
        def boom(p, timeout=120):
            raise RuntimeError('gemini HTTP 429')
        S.call_gemini = boom
        self.assertTrue(S.translate_struct(self.KO, '영어'))
        self.assertEqual(self.claude_calls, 1)

    def test_fallback_can_be_turned_off(self):
        os.environ['WJ_CLAUDE_FALLBACK'] = '0'
        try:
            S.call_gemini = lambda p, timeout=120: self.BAD
            self.assertIsNone(S.translate_struct(self.KO, '영어'))
            self.assertEqual(self.claude_calls, 0)
        finally:
            os.environ.pop('WJ_CLAUDE_FALLBACK', None)

    def test_no_gemini_key_uses_claude(self):
        def nokey(p, timeout=120):
            raise RuntimeError('gemini 키 없음')
        S.call_gemini = nokey
        self.assertTrue(S.translate_struct(self.KO, '영어'))
        self.assertEqual(self.claude_calls, 1)

    def test_month_digit_may_drop_in_english_but_new_numbers_may_not(self):
        ko = {'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['9월 목표 20% 달성']}}
        S.call_gemini = lambda p, timeout=120: R({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['September target 20% achieved']}})
        self.assertTrue(S.translate_struct(ko, '영어'))
        S.call_gemini = lambda p, timeout=120: R({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['September target 25% achieved']}})
        self.assertIsNone(S.translate_struct(ko, '영어'))

    def test_translator_claude_skips_gemini(self):
        os.environ['WJ_TRANSLATOR'] = 'claude'
        try:
            def g(p, timeout=120):
                raise AssertionError('gemini 를 부르면 안 됨')
            S.call_gemini = g
            self.assertTrue(S.translate_struct(self.KO, '영어'))
            self.assertEqual(self.claude_calls, 1)
        finally:
            os.environ.pop('WJ_TRANSLATOR', None)

    def test_usage_is_metered_from_json_output(self):
        S.usage_reset()
        out = S._meter(json.dumps({'result': '본문', 'total_cost_usd': 0.25, 'usage': {'input_tokens': 10, 'output_tokens': 20, 'cache_read_input_tokens': 300, 'cache_creation_input_tokens': 40}}))
        self.assertEqual(out, '본문')
        self.assertEqual(S.USAGE['calls'], 1); self.assertEqual(S.USAGE['metered'], 1)
        self.assertEqual((S.USAGE['input'], S.USAGE['output'], S.USAGE['cache_read'], S.USAGE['cache_write']), (10, 20, 300, 40))
        self.assertIn('370 토큰', S.usage_report())
        self.assertEqual(S._meter('그냥 글'), '그냥 글')                      # JSON 이 아니면 원문 그대로(측정만 못 함)
        self.assertEqual((S.USAGE['calls'], S.USAGE['metered']), (2, 1))

    def test_spelled_out_small_numbers_and_festival_dates_tolerated(self):
        ko = {'sec5': {}, 'sec6': {}, 'sec7': {'EC': ['11.11 행사 6주 진행, 20% 할인']}}
        S.call_gemini = lambda p, timeout=120: R({'sec5': {}, 'sec6': {}, 'sec7': {'EC': ["Singles' Day event for six weeks, 20% discount"]}})
        self.assertTrue(S.translate_struct(ko, '영어'))
        S.call_gemini = lambda p, timeout=120: R({'sec5': {}, 'sec6': {}, 'sec7': {'EC': ["Singles' Day event for six weeks, discount"]}})   # 20% 가 빠지면 불통과
        self.assertIsNone(S.translate_struct(ko, '영어'))
        S.call_gemini = lambda p, timeout=120: R({'sec5': {}, 'sec6': {}, 'sec7': {'EC': ["Singles' Day event for 7 weeks, 20% discount"]}})   # 새 숫자 7 은 불통과
        self.assertIsNone(S.translate_struct(ko, '영어'))

    def test_half_year_and_quarter_tokens_are_not_counted_as_numbers(self):
        ko = {'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['2026년 하반기 바자회 모색, 3분기 점검']}}
        S.call_gemini = lambda p, timeout=120: R({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['Explore 2026 H2 bazaar, Q3 review']}})
        self.assertTrue(S.translate_struct(ko, '영어'))

    def test_discount_percent_may_become_zhe_when_arithmetic_is_right(self):
        ko = {'sec5': {}, 'sec6': {}, 'sec7': {'EC': ['20% 할인 행사 진행']}}
        def tr(text):
            return R({'sec5': {}, 'sec6': {}, 'sec7': {'EC': [text]}}, ensure_ascii=False)
        os.environ['WJ_CLAUDE_FALLBACK'] = '0'
        try:
            S.call_gemini = lambda p, timeout=120: tr('舉辦8折優惠活動')
            self.assertTrue(S.translate_struct(ko, '번체'))                          # 20% 할인 = 8折
            S.call_gemini = lambda p, timeout=120: tr('舉辦八折優惠活動')
            self.assertTrue(S.translate_struct(ko, '번체'))                          # 한자 숫자도 인식
            S.call_gemini = lambda p, timeout=120: tr('舉辦9折優惠活動')
            self.assertIsNone(S.translate_struct(ko, '번체'))                        # 산수가 틀리면 거부
            S.call_gemini = lambda p, timeout=120: tr('舉辦優惠活動')
            self.assertIsNone(S.translate_struct(ko, '번체'))                        # 할인율이 통째로 빠지면 거부
        finally:
            os.environ.pop('WJ_CLAUDE_FALLBACK', None)
        ko15 = {'sec5': {}, 'sec6': {}, 'sec7': {'EC': ['15% 할인']}}
        S.call_gemini = lambda p, timeout=120: tr('85折')
        self.assertTrue(S.translate_struct(ko15, '번체'))

    def test_claude_fallback_retries_once_with_the_reason(self):
        S.call_gemini = lambda p, timeout=120: self.BAD
        seen = []
        def claude(p, model=None, **kw):
            seen.append(p)
            return self.BAD if len(seen) == 1 else self.OK
        S.call_claude = claude
        self.assertTrue(S.translate_struct(self.KO, '영어'))
        self.assertEqual(len(seen), 2); self.assertIn('이전 번역의 문제', seen[1])

    def test_default_translator_is_claude_and_never_touches_gemini(self):
        os.environ.pop('WJ_TRANSLATOR', None)
        def g(p, timeout=120):
            raise AssertionError('gemini 를 부르면 안 됨')
        S.call_gemini = g
        self.assertTrue(S.translate_struct(self.KO, '영어'))
        self.assertEqual(self.claude_calls, 1)

    def test_translation_is_split_into_chunks_run_in_parallel_and_merged_in_order(self):
        import time
        os.environ.pop('WJ_TRANSLATOR', None)
        ko = {'sec5': {}, 'sec6': {f'부서{i}': {'결과': [f'매출 {i}0% 증가', None]} for i in range(1, 7)}, 'sec7': {}}
        def claude(p, model=None, **kw):
            time.sleep(0.3)
            struct = json.loads(p.split('\n\n')[1] if '[이전' not in p else p.split('\n\n')[1])
            return json.dumps(_map_str(struct, lambda s_: 'EN ' + s_), ensure_ascii=False)
        S.call_claude = claude
        os.environ['WJ_TRANS_CHUNK'] = '2'
        try:
            t0 = time.time()
            out = S.translate_parallel(ko, '영어')
            dt = time.time() - t0
        finally:
            os.environ.pop('WJ_TRANS_CHUNK', None)
        self.assertLess(dt, 0.7)                                                 # 3조각을 차례로 하면 0.9초 이상
        self.assertEqual(list(out['sec6']), [f'부서{i}' for i in range(1, 7)])        # 순서 유지
        self.assertEqual(out['sec6']['부서3']['결과'][0], 'EN 매출 30% 증가')

    def test_if_any_chunk_fails_the_language_is_left_empty(self):
        os.environ.pop('WJ_TRANSLATOR', None)
        ko = {'sec5': {}, 'sec6': {f'부서{i}': {'결과': [f'매출 {i}0% 증가', None]} for i in range(1, 5)}, 'sec7': {}}
        def claude(p, model=None, **kw):
            struct = json.loads(p.split('\n\n')[1] if '[이전' not in p else p.split('\n\n')[1])
            if any('30%' in v for v in struct.values()):
                return json.dumps(_map_str(struct, lambda s_: '숫자 틀림 999'), ensure_ascii=False)
            return json.dumps(_map_str(struct, lambda s_: 'EN ' + s_), ensure_ascii=False)
        S.call_claude = claude
        os.environ['WJ_TRANS_CHUNK'] = '2'
        try:
            self.assertIsNone(S.translate_parallel(ko, '영어'))
        finally:
            os.environ.pop('WJ_TRANS_CHUNK', None)

    def test_digit_first_half_year_tokens_and_trailing_text_in_response(self):
        ko = {'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['2026년 하반기 바자회 모색']}}
        os.environ['WJ_TRANSLATOR'] = 'auto'
        S.call_gemini = lambda p, timeout=120: R({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['Explore 2H 2026 bazaar']}}) + '\n\n참고: {이 설명은 무시}'
        self.assertTrue(S.translate_struct(ko, '영어'))

    def test_parse_json_reads_only_the_first_object(self):
        self.assertEqual(S.parse_json('설명 ```json\n{"a": {"b": 1}}\n``` 그리고 {"c": 2}'), {'a': {'b': 1}})
        with self.assertRaises(ValueError):
            S.parse_json('JSON 없음')

    def test_keys_are_never_sent_and_missing_ids_are_retried_with_reason(self):
        os.environ.pop('WJ_TRANSLATOR', None)
        ko = {'sec5': {'영업': {'동향': ['시장 부진', None], '대응': ['재고 정리 20%', None]}}, 'sec6': {}, 'sec7': {'GM': ['11월 행사', '12월 점검']}}
        seen = []
        def claude(p, model=None, **kw):
            seen.append(p)
            if len(seen) == 1:
                return json.dumps({'1': 'Weak market', '2': 'Clearance 20%', '3': 'Nov event'})       # 4번이 빠짐
            return json.dumps({'1': 'Weak market', '2': 'Clearance 20%', '3': 'Nov event', '4': 'Dec check'})
        S.call_claude = claude
        out = S.translate_struct(ko, '영어')
        self.assertEqual(out['sec5']['영업']['대응'], ['Clearance 20%', None])                      # 키·null 은 원래 구조 그대로
        self.assertEqual(out['sec7']['GM'], ['Nov event', 'Dec check'])
        for key in ('동향', '대응', 'sec5', 'sec7', '영업'):
            self.assertNotIn(key, seen[0].split('\n\n')[1])                                       # 키는 번역기에 보내지 않는다
        self.assertEqual(len(seen), 2); self.assertIn('번호', seen[1].split('[이전 번역의 문제]')[1])

    def test_man_unit_and_two_digit_tolerated(self):
        ko = {'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['3,693만 달성, 두 자릿수 성장']}}
        S.call_gemini = lambda p, timeout=120: R({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['36.93m achieved, double-digit growth']}})
        self.assertTrue(S.translate_struct(ko, '영어'))

    def test_per_call_log_line_and_model_env(self):
        import io, subprocess, shutil, contextlib
        envs = []
        class R:
            returncode, stderr = 0, ''
            stdout = json.dumps({'result': '본문', 'usage': {'output_tokens': 1234}, 'modelUsage': {'claude-test-1': {}}})
        S.call_claude = REAL_CALL_CLAUDE
        old_run, old_which = subprocess.run, shutil.which
        subprocess.run, shutil.which = (lambda cmd, **kw: (envs.append((cmd, kw['env'])), R())[1]), (lambda x: 'claude')
        os.environ['WJ_CLAUDE_MODEL'] = 'sonnet'
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                self.assertEqual(S.call_claude('x', label='요약'), '본문')
        finally:
            subprocess.run, shutil.which = old_run, old_which
            os.environ.pop('WJ_CLAUDE_MODEL', None)
        self.assertIn('[호출]', buf.getvalue()); self.assertIn('요약 ·', buf.getvalue()); self.assertIn('출력 1,234토큰', buf.getvalue()); self.assertIn('claude-test-1', buf.getvalue())
        self.assertNotEqual(envs[0][1].get('MAX_THINKING_TOKENS'), '0')                  # 추론 토큰 환경변수를 코드가 건드리지 않는다
        self.assertIn('sonnet', envs[0][0])

    def test_engine_switches_summarize_and_verify_to_gemini_without_claude(self):
        out = {'sec5': {}, 'sec6': {'영업': {'결과': ['매출 20% 증가', None]}}, 'sec7': {}}
        S.call_claude = lambda *a, **k: (_ for _ in ()).throw(AssertionError('claude 를 부르면 안 됨'))
        S.call_gemini = lambda p, timeout=120: json.dumps(out) if '정리 담당' in p else '[]'
        os.environ['WJ_SUMMARIZER'] = 'gemini'; os.environ['WJ_VERIFIER'] = 'gemini'
        try:
            got, flags = REAL_SUMMARIZE('홍콩', 'W41', [{'sec': '6', 'dept': '영업', 'item': '총평', 'text': '매출 20% 증가'}])
            self.assertEqual(got, out); self.assertEqual(flags, [])
            self.assertEqual(REAL_VERIFY(out, [{'sec': '6', 'dept': '영업', 'item': '총평', 'text': '매출 20% 증가'}]), [])
            os.environ['WJ_VERIFIER'] = 'none'
            self.assertEqual(REAL_VERIFY(out, []), [])
        finally:
            os.environ.pop('WJ_SUMMARIZER', None); os.environ.pop('WJ_VERIFIER', None)

    def test_claude_lean_command_falls_back_to_plain(self):
        import subprocess, shutil
        cmds = []
        class R:
            def __init__(s, rc, out='', err=''): s.returncode, s.stdout, s.stderr = rc, out, err
        def run(cmd, **kw):
            cmds.append((cmd, kw.get('cwd')))
            return R(1, '', 'unknown option --system-prompt') if len(cmds) == 1 else R(0, 'done')
        S.call_claude = REAL_CALL_CLAUDE
        old_run, old_which = subprocess.run, shutil.which
        subprocess.run, shutil.which = run, lambda n: 'claude'
        try:
            self.assertEqual(S.call_claude('x'), 'done')
        finally:
            subprocess.run, shutil.which = old_run, old_which
        c0 = cmds[0][0]
        self.assertIn('--system-prompt', c0); self.assertIn('--disable-slash-commands', c0); self.assertIn('--strict-mcp-config', c0)
        self.assertNotIn('--effort', c0)                                      # 기본은 effort 를 쓰지 않는다
        self.assertIsNotNone(cmds[0][1])

    def test_effort_is_opt_in_with_fallback_ladder(self):
        os.environ['WJ_EFFORT'] = 'low'
        try:
            tiers = S._claude_cmds('claude', None)
        finally:
            os.environ.pop('WJ_EFFORT', None)
        self.assertIn('--effort', tiers[0][0]); self.assertNotIn('--effort', tiers[1][0]); self.assertNotIn('--system-prompt', tiers[2][0])

    def test_verifier_prompt_allows_sec7_content_in_sec6_action(self):
        self.assertIn('7번 향후전략의 내용을 6번 조치로 쓴 것은 오류가 아니다', S.CHECK_PROMPT)

    def test_claude_limit_error_is_not_retried(self):
        import subprocess, shutil
        n = []
        class R:
            returncode, stdout, stderr = 1, '', "You've hit your session limit"
        S.call_claude = REAL_CALL_CLAUDE
        old_run, old_which = subprocess.run, shutil.which
        subprocess.run, shutil.which = (lambda cmd, **kw: (n.append(1), R())[1]), (lambda x: 'claude')
        try:
            with self.assertRaises(RuntimeError):
                S.call_claude('x')
        finally:
            subprocess.run, shutil.which = old_run, old_which
        self.assertEqual(len(n), 1)


class Check(unittest.TestCase):
    def setUp(self):
        import check_summary as C
        self.C = C
        self.tmp = tempfile.mkdtemp()
        B.DRAFT_DIR = self.tmp
        ko = {'sec5': {}, 'sec6': {'영업': {'결과': ['매출 20% 증가', None]}}, 'sec7': {'GM': ['11월 행사 2회 진행']}}
        en = {'sec5': {}, 'sec6': {'영업': {'결과': ['Sales up 20%', None]}}, 'sec7': {'GM': ['2 events in November']}}
        zh = {'sec5': {}, 'sec6': {'영업': {'결과': ['銷售增加20%', None]}}, 'sec7': {'GM': ['11月舉辦2場活動']}}
        self.draft = {'ent': 'HK', 'code': 'M09', 'made_at': 'x', 'cells': [{'sec': '6', 'dept': '영업', 'item': '총평', 'text': '매출 20% 증가'}, {'sec': '7', 'dept': 'GM', 'item': '향후전략', 'text': '11월 행사 2회 진행'}],
                      'display': {'ko': ko, 'en': en, 'zh': zh}, 'dropped': [], 'warn': []}

    def save(self, d):
        json.dump(d, open(os.path.join(self.tmp, 'HK_M09.json'), 'w', encoding='utf-8'), ensure_ascii=False)

    def test_good_draft_passes(self):
        self.save(self.draft)
        fails, notes = self.C.check('HK', 'M09', say=lambda *_: None)
        self.assertEqual((fails, notes), ([], []))

    def test_missing_file_and_missing_language_fail(self):
        self.assertTrue(self.C.check('HK', 'M09', say=lambda *_: None)[0])
        d = self.draft; d['display'].pop('zh'); self.save(d)
        fails, _ = self.C.check('HK', 'M09', say=lambda *_: None)
        self.assertEqual(len(fails), 1); self.assertIn('중국어', fails[0])

    def test_new_number_in_translation_fails(self):
        d = self.draft; d['display']['en']['sec6']['영업']['결과'][0] = 'Sales up 25%'; self.save(d)
        fails, _ = self.C.check('HK', 'M09', say=lambda *_: None)
        self.assertTrue(any('영어 번역 불일치' in f for f in fails))

    def test_uncovered_dept_and_dropped_lines_are_notes_not_failures(self):
        d = self.draft
        d['cells'].append({'sec': '6', 'dept': 'EC', 'item': '총평', 'text': 'EC 원문 가나다라'})
        d['dropped'] = ['sec6/EC/결과']; d['warn'] = [{'위치': 'sec6/EC/결과', '문제': '원문에 없음'}]
        self.save(d)
        fails, notes = self.C.check('HK', 'M09', say=lambda *_: None)
        self.assertEqual(fails, []); self.assertEqual(len(notes), 3)
        self.assertTrue(any('EC' in n and '화면에 줄이 없는' in n for n in notes))


if __name__ == '__main__':
    unittest.main()
