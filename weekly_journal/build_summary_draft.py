# -*- coding: utf-8 -*-
"""SUMMARY 5~7 핵심 정리 만들기 (자동, 검수 없음): 시트에서 부서 글 읽기 → 정리(AI) → 숫자 대조·사실 검증 → 화면용 핵심만 추려 영·중 번역
→ summary_draft/{ENT}_{CODE}.json  (summary_render 가 이 파일의 'display' 를 SUMMARY 화면에 쓴다)

화면에는 라벨마다 '핵심 한 줄'만 보인다(자세한 내용은 '부서 원문 보기'). 숫자 대조·사실 검증에서 걸린 줄은 화면에서 뺀다(원문 보기로 확인).
사용:  python weekly_journal/build_summary_draft.py --ent TW --code M09 [--force] [--redo-display]
       --code 는 월간 M09, 주간 W41.   원문이 지난번과 같으면(해시 동일) 다시 만들지 않는다. --force 로 강제.
정량 블록은 summary_quant/{ENT}_{CODE}.txt 가 있으면 자동으로 쓴다.
"""
import argparse
import datetime
import hashlib
import json
import os

import sheet_reader as R
import summarize_cells as S

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT_DIR = os.path.join(HERE, 'summary_draft')
QUANT_DIR = os.path.join(HERE, 'summary_quant')


def src_hash(cells, quant):
    raw = json.dumps([[c['sec'], c['dept'], c['item'], c['text']] for c in cells], ensure_ascii=False) + '|' + quant
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()[:16]


def make_display(out, flags, warn, cells, quant):
    """화면용: 라벨마다 핵심 한 줄만. 숫자 대조·사실 검증에 걸린 줄은 뺀다. 전략(7번)은 항목마다 숫자 대조."""
    bad = {(f[0], f[1], f[2]) for f in flags}
    for w in warn or []:
        parts = str(w.get('위치', '')).split('/')
        if len(parts) >= 3:
            bad.add((parts[0], parts[1], parts[2]))
        elif len(parts) == 2:
            bad.add((parts[0], parts[1], None))
    have = S.allowed_numbers(cells, quant)
    disp = {'sec5': {}, 'sec6': {}, 'sec7': {}}
    dropped = []
    for sk in ('sec5', 'sec6'):
        for dept, labs in (out.get(sk) or {}).items():
            row = {}
            for lab, v in (labs or {}).items():
                if not v or not v[0]:
                    continue
                if (sk, dept, lab) in bad or (sk, dept, None) in bad:
                    dropped.append(f'{sk}/{dept}/{lab}')
                    continue
                row[lab] = [v[0], None]
            if row:
                disp[sk][dept] = row
    for dept, items in (out.get('sec7') or {}).items():
        keep = []
        for t in items or []:
            if not t:
                continue
            if any(n not in have for n in S.nums(t)) or ('sec7', dept, None) in bad:
                dropped.append(f'sec7/{dept}/{t[:20]}')
                continue
            keep.append(t)
        if keep:
            disp['sec7'][dept] = keep
    return disp, dropped


def build_display_i18n(out, flags, warn, cells, quant):
    ko, dropped = make_display(out, flags, warn, cells, quant)
    res = {'ko': ko}
    has = any(ko[k] for k in ko)
    if has:
        for lang, name in (('en', '영어'), ('zh', '번체 중국어(대만·홍콩 업무 용어)')):
            try:
                tr = S.translate_struct(ko, name)
            except Exception as ex:
                print(f'[경고] {name} 번역 실패 — 한글로 대체 표시: {ex!r}')
                tr = None
            if tr:
                res[lang] = tr
    return res, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ent', required=True, choices=['HK', 'TW'])
    ap.add_argument('--code', required=True)
    ap.add_argument('--quant-file')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--redo-display', action='store_true', help='저장된 정리본에서 화면용(핵심+번역)만 다시 만든다')
    a = ap.parse_args()
    os.makedirs(DRAFT_DIR, exist_ok=True)
    path = os.path.join(DRAFT_DIR, f'{a.ent}_{a.code}.json')
    qp = a.quant_file or os.path.join(QUANT_DIR, f'{a.ent}_{a.code}.txt')
    quant = open(qp, encoding='utf-8').read() if os.path.exists(qp) else ''
    old = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else None

    if a.redo_display and old:
        d = old
        disp, dropped = build_display_i18n(d['out'], d.get('flags', []), d.get('warn', []), d['cells'], d.get('quant', ''))
        d['display'], d['dropped'] = disp, dropped
        json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('화면용 갱신:', path, '/ 뺀 줄', len(dropped))
        return 0

    cells, stat = R.read_cells(a.ent, a.code)
    cells = [c for c in cells if len(c['text']) > 3]          # '測試' 같은 시험 입력(2자)은 제외
    print(f'시트에서 읽음: 요약 대상 칸 {len(cells)}개')
    if not cells:
        print('요약할 글이 없습니다.')
        return 1
    h = src_hash(cells, quant)
    if old and old.get('hash') == h and old.get('display') and not a.force:
        print('원문이 지난번과 같아 건너뜀 (--force 로 다시 만들기)')
        return 0
    name = {'HK': '홍콩', 'TW': '대만'}[a.ent]
    period = (f'2026년 {int(a.code[1:])}월' if a.code[0] == 'M' else f'{a.code} 주차')
    out, flags = S.summarize(name, period, cells, quant)
    print('숫자 검수 대상:', len(flags), '건 — 사실 검증 중…')
    warn = S.verify_claims(out, cells, quant)
    disp, dropped = build_display_i18n(out, flags, warn, cells, quant)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'ent': a.ent, 'code': a.code, 'made_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'hash': h,
                   'quant': quant, 'cells': cells, 'out': out, 'flags': flags, 'warn': warn, 'display': disp, 'dropped': dropped},
                  f, ensure_ascii=False, indent=1)
    print('저장:', path, f'/ 사실 검증 경고 {len(warn)}건, 화면에서 뺀 줄 {len(dropped)}개')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
