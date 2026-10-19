# -*- coding: utf-8 -*-
"""저장된 SUMMARY 정리본(summary_draft/{ENT}_{CODE}.json)이 '화면에 올려도 되는 상태'인지 점검한다. AI·시트를 쓰지 않는다.

점검 항목
  [실패로 본다]  파일 없음 / 한글 화면용이 비어 있음 / 영어·중국어 번역 빠짐 / 번역의 구조·숫자가 한글과 어긋남
  [사람이 본다]  원문은 있는데 화면에 한 줄도 없는 부서 / 화면에서 뺀 줄 / 사실 검증 경고
사용:  python weekly_journal/check_summary.py --code M09                 (홍콩·대만 모두)
       python weekly_journal/check_summary.py --code M09 --ent HK
종료코드: 0 통과 / 1 실패 항목 있음
"""
import argparse
import json
import os
import sys

import build_summary_draft as B
import summarize_cells as S

LANG_NAME = {'ko': '한국어', 'en': '영어', 'zh': '중국어'}


def count_lines(disp):
    n = 0
    for sec in ('sec5', 'sec6'):
        for labs in ((disp or {}).get(sec) or {}).values():
            for v in (labs or {}).values():
                core = v[0] if v else None
                n += len([x for x in (core if isinstance(core, list) else [core]) if x])
    for items in ((disp or {}).get('sec7') or {}).values():
        n += len([x for x in (items or []) if x])
    return n


def shown_depts(disp):
    return {B._owner(k) for sec in ('sec5', 'sec6', 'sec7') for k in ((disp or {}).get(sec) or {})}


def check(ent, code, say=print, draft_dir=None):
    """한 법인·한 코드를 점검한다. 반환: (실패 목록, 사람이 볼 목록)"""
    path = os.path.join(draft_dir or B.DRAFT_DIR, f'{ent}_{code}.json')
    fails, notes = [], []
    if not os.path.exists(path):
        return [f'정리본 파일이 없습니다: {path}'], notes
    d = json.load(open(path, encoding='utf-8'))
    disp = d.get('display') or {}
    ko = disp.get('ko')
    if not B.has_content(ko):
        return ['한글 화면용 정리본이 비어 있습니다'], notes
    problem = S.translation_checker(ko)
    for lg in ('en', 'zh'):
        tr = disp.get(lg)
        if not tr:
            fails.append(f'{LANG_NAME[lg]} 번역이 없습니다')
            continue
        why = problem(tr)
        if why:
            fails.append(f'{LANG_NAME[lg]} 번역 불일치: {why}')
    src_depts = {c['dept'] for c in d.get('cells', []) if len(c['text']) > 3}
    gap = sorted(src_depts - shown_depts(ko))
    if gap:
        notes.append(f'원문은 있는데 화면에 줄이 없는 부서: {gap}')
    for x in d.get('dropped', []):
        notes.append(f'화면에서 뺀 줄: {x}')
    for w in d.get('warn', []):
        notes.append(f"사실 검증 경고: {w.get('위치')} — {str(w.get('문제', ''))[:60]}")
    say(f'   {ent} {code}: 부서 {len(src_depts)}개 중 {len(src_depts) - len(gap)}개 표시 / 화면 줄 수 한국어 {count_lines(ko)} · 영어 {count_lines(disp.get("en"))} · 중국어 {count_lines(disp.get("zh"))} / 저장 시각 {d.get("made_at")}')
    return fails, notes


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(errors='replace')
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument('--code', required=True, help='예: M09 (9월 마감), W41')
    ap.add_argument('--ent', choices=['HK', 'TW'])
    a = ap.parse_args(argv)
    bad = 0
    for ent in ([a.ent] if a.ent else ['HK', 'TW']):
        fails, notes = check(ent, a.code)
        print(f'[{"실패" if fails else "통과"}] {ent} {a.code}')
        for f in fails:
            print('   ✗', f)
        for n in notes:
            print('   · ', n)
        bad += bool(fails)
    print('점검 결과: ' + ('모두 통과' if not bad else f'{bad}곳에 실패 항목이 있습니다 (위 ✗ 확인)'))
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
