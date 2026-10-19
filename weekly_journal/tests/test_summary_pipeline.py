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


def _map_str(x, f):
    if isinstance(x, dict):
        return {k: _map_str(v, f) for k, v in x.items()}
    if isinstance(x, list):
        return [_map_str(v, f) for v in x]
    return f(x) if isinstance(x, str) else x


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


class Tr(unittest.TestCase):
    KO = {'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['2단계 20% 확대']}}
    OK = json.dumps({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['Stage 2, 20% expansion']}})
    BAD = json.dumps({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['Stage 3, 20% expansion']}})

    def setUp(self):
        S.translate_struct = REAL_TRANSLATE
        S.GEMINI_RETRY_WAIT = 0
        self.claude_calls = 0
        def claude(p, model=None):
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

    def test_gemini_keeps_failing_returns_none_without_claude(self):
        S.call_gemini = lambda p, timeout=120: self.BAD
        self.assertIsNone(S.translate_struct(self.KO, '영어'))
        self.assertEqual(self.claude_calls, 0)

    def test_gemini_error_twice_returns_none_without_claude(self):
        def boom(p, timeout=120):
            raise RuntimeError('429')
        S.call_gemini = boom
        self.assertIsNone(S.translate_struct(self.KO, '영어'))
        self.assertEqual(self.claude_calls, 0)

    def test_no_gemini_key_uses_claude(self):
        def nokey(p, timeout=120):
            raise RuntimeError('gemini 키 없음')
        S.call_gemini = nokey
        self.assertTrue(S.translate_struct(self.KO, '영어'))
        self.assertEqual(self.claude_calls, 1)

    def test_month_digit_may_drop_in_english_but_new_numbers_may_not(self):
        ko = {'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['9월 목표 20% 달성']}}
        S.call_gemini = lambda p, timeout=120: json.dumps({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['September target 20% achieved']}})
        self.assertTrue(S.translate_struct(ko, '영어'))
        S.call_gemini = lambda p, timeout=120: json.dumps({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['September target 25% achieved']}})
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
        S.call_gemini = lambda p, timeout=120: json.dumps({'sec5': {}, 'sec6': {}, 'sec7': {'EC': ["Singles' Day event for six weeks, 20% discount"]}})
        self.assertTrue(S.translate_struct(ko, '영어'))
        S.call_gemini = lambda p, timeout=120: json.dumps({'sec5': {}, 'sec6': {}, 'sec7': {'EC': ["Singles' Day event for six weeks, discount"]}})   # 20% 가 빠지면 불통과
        self.assertIsNone(S.translate_struct(ko, '영어'))
        S.call_gemini = lambda p, timeout=120: json.dumps({'sec5': {}, 'sec6': {}, 'sec7': {'EC': ["Singles' Day event for 7 weeks, 20% discount"]}})   # 새 숫자 7 은 불통과
        self.assertIsNone(S.translate_struct(ko, '영어'))

    def test_man_unit_and_two_digit_tolerated(self):
        ko = {'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['3,693만 달성, 두 자릿수 성장']}}
        S.call_gemini = lambda p, timeout=120: json.dumps({'sec5': {}, 'sec6': {}, 'sec7': {'GM': ['36.93m achieved, double-digit growth']}})
        self.assertTrue(S.translate_struct(ko, '영어'))

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
        self.assertIn('--system-prompt', cmds[0][0]); self.assertIn('--disable-slash-commands', cmds[0][0]); self.assertIn('--strict-mcp-config', cmds[0][0]); self.assertIsNotNone(cmds[0][1])
        self.assertNotIn('--system-prompt', cmds[1][0]); self.assertIsNone(cmds[1][1])

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


if __name__ == '__main__':
    unittest.main()
