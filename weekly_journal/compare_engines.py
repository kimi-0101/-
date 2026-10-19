# -*- coding: utf-8 -*-
"""정리·검증을 Gemini(무료)로 돌렸을 때 결과가 Claude 저장본과 얼마나 다른지 나란히 본다.  Claude 사용량은 쓰지 않는다.

이미 저장된 summary_draft/{ENT}_{CODE}.json 의 원문(cells)을 그대로 Gemini 에 넣는다. 시트는 읽지 않고, 저장본은 건드리지 않는다.
사용:  python weekly_journal/compare_engines.py --ent HK --code W41           (Gemini 정리 + Gemini 검증)
       python weekly_journal/compare_engines.py --ent HK --code W41 --no-verify
결과는 화면에만 나오고, 같은 내용이 summary_draft/{ENT}_{CODE}_gemini.json 으로도 저장된다(비교용, 화면에는 쓰이지 않음).
"""
import argparse
import json
import os
import sys

import build_summary_draft as B
import summarize_cells as S


def lines_of(disp):
    """화면용 구조 → {(섹션, 부서, 라벨): 줄 목록}"""
    out = {}
    for sec in ('sec5', 'sec6'):
        for dept, labs in ((disp or {}).get(sec) or {}).items():
            for lab, v in (labs or {}).items():
                core = v[0] if v else None
                out[(sec, dept, lab)] = [x for x in (core if isinstance(core, list) else [core]) if x]
    for dept, items in ((disp or {}).get('sec7') or {}).items():
        out[('sec7', dept, '전략')] = list(items or [])
    return out


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(errors='replace')
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument('--ent', required=True, choices=['HK', 'TW'])
    ap.add_argument('--code', required=True)
    ap.add_argument('--no-verify', action='store_true')
    a = ap.parse_args(argv)
    path = os.path.join(B.DRAFT_DIR, f'{a.ent}_{a.code}.json')
    if not os.path.exists(path):
        print(f'저장본이 없습니다: {path}')
        return 2
    old = json.load(open(path, encoding='utf-8'))
    cells = [c for c in old['cells'] if len(c['text']) > 3]
    quant = old.get('quant', '')
    name = {'HK': '홍콩', 'TW': '대만'}[a.ent]
    period = f'2026년 {int(a.code[1:])}월' if a.code[0] == 'M' else f'{a.code} 주차'
    os.environ['WJ_SUMMARIZER'] = 'gemini'
    os.environ['WJ_VERIFIER'] = 'none' if a.no_verify else 'gemini'
    import time
    t0 = time.time()
    out, flags = S.summarize(name, period, cells, quant)
    t1 = time.time()
    warn = S.verify_claims(out, cells, quant)
    t2 = time.time()
    disp, dropped = B.make_display(out, flags, warn, cells, quant)
    mine, theirs = lines_of(old['display']['ko']), lines_of(disp)
    print(f'\n===== {a.ent} {a.code}: Claude 저장본 vs Gemini  (Gemini 정리 {t1 - t0:.0f}초, 검증 {t2 - t1:.0f}초) =====')
    for key in sorted(set(mine) | set(theirs), key=lambda k: (k[0], k[1], k[2])):
        m, g = mine.get(key, []), theirs.get(key, [])
        print(f'\n[{key[0]} {key[1]} {key[2]}]')
        print('  Claude :', ' / '.join(m) if m else '(없음)')
        print('  Gemini :', ' / '.join(g) if g else '(없음)')
    n_m, n_g = sum(len(v) for v in mine.values()), sum(len(v) for v in theirs.values())
    print(f'\n--- 요약 ---\n화면에 나오는 줄: Claude {n_m}줄 / Gemini {n_g}줄')
    print(f"뺀 줄: Claude {len(old.get('dropped', []))}개 / Gemini {len(dropped)}개 | 사실 검증 경고: Claude {len(old.get('warn', []))}건 / Gemini {len(warn)}건 | 숫자 검수 대상: Claude {len(old.get('flags', []))}건 / Gemini {len(flags)}건")
    for d_ in dropped:
        print('  Gemini 뺌:', d_)
    for w_ in warn:
        print(f"  Gemini 경고: {w_.get('위치')} — {str(w_.get('문제', ''))[:70]}")
    side = os.path.join(B.DRAFT_DIR, f'{a.ent}_{a.code}_gemini.json')
    with open(side, 'w', encoding='utf-8') as f:
        json.dump({'out': out, 'flags': flags, 'warn': warn, 'display_ko': disp, 'dropped': dropped}, f, ensure_ascii=False, indent=1)
    print('\n비교용 저장:', side)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
