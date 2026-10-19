# -*- coding: utf-8 -*-
"""SUMMARY 5~7 핵심 정리 만들기 (자동, 검수 없음): 시트에서 부서 글 읽기 → 정리(AI) → 숫자 대조·사실 검증 → 화면용 핵심만 추려 영·중 번역
→ summary_draft/{ENT}_{CODE}.json  (summary_render 가 이 파일의 'display' 를 SUMMARY 화면에 쓴다)

화면에는 라벨마다 '핵심'만 보인다(같은 맥락이면 한 줄, 다른 맥락이면 여러 줄)(자세한 내용은 '부서 원문 보기'). 숫자 대조·사실 검증에서 걸린 줄은 화면에서 뺀다(원문 보기로 확인).
사용:  python weekly_journal/build_summary_draft.py --ent TW --code M09 [--force] [--redo-display]
       python weekly_journal/build_summary_draft.py --auto-week 42            (그 주의 주간·이번 달·지난 달 코드를 양쪽 법인 모두)
       --code 는 월간 M09, 주간 W41.   원문이 지난번과 같으면(해시 동일) 다시 만들지 않는다. --force 로 강제.
정량 블록은 summary_quant/{ENT}_{CODE}.txt 가 있으면 자동으로 쓴다.

번역이 한도·오류로 빠진 채 저장돼도 다음 실행에서 '번역만' 채운다(정리·검증은 다시 부르지 않는다).
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
LANGS = (('en', '영어'), ('zh', '번체 중국어(대만·홍콩 업무 용어)'))


def src_hash(cells, quant):
    raw = json.dumps([[c['sec'], c['dept'], c['item'], c['text']] for c in cells], ensure_ascii=False) + '|' + quant
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()[:16]


def _norm(t):
    return ''.join(str(t or '').split())


def has_content(ko):
    return any((ko or {}).get(k) for k in ('sec5', 'sec6', 'sec7'))


def _line_bad(t, have, bad_sent):
    nt = _norm(t)
    return any(n not in have for n in S.nums(t)) or any(x and (x == nt or x in nt or nt in x) for x in bad_sent)


def make_display(out, flags, warn, cells, quant):
    """화면용: 라벨마다 핵심 한 줄만. 숫자 대조·사실 검증에 걸린 줄은 뺀다. 전략(7번)은 항목마다 숫자 대조 + 사실 검증에 걸린 문장은 뺀다."""
    bad = {(f[0], f[1], f[2]) for f in flags}
    bad_sent = []
    for w in warn or []:
        parts = str(w.get('위치', '')).split('/')
        if len(parts) >= 3:
            bad.add((parts[0], parts[1], parts[2]))
        elif len(parts) == 2:
            bad.add((parts[0], parts[1], None))
        if w.get('문장'):
            bad_sent.append(_norm(w['문장']))
    have = S.allowed_numbers(cells, quant)
    disp = {'sec5': {}, 'sec6': {}, 'sec7': {}}
    dropped = []
    for sk in ('sec5', 'sec6'):
        for dept, labs in (out.get(sk) or {}).items():
            row = {}
            for lab, v in (labs or {}).items():
                if not v or not v[0]:
                    continue
                lines = [x for x in (v[0] if isinstance(v[0], list) else [v[0]]) if x]
                if not lines:
                    continue
                label_bad = (sk, dept, lab) in bad or (sk, dept, None) in bad
                if len(lines) > 1:                       # 여러 줄이면 걸린 줄만 뺀다(걸린 줄을 못 찾으면 라벨 전체를 뺀다)
                    ok = [t for t in lines if not _line_bad(t, have, bad_sent)]
                    if label_bad and len(ok) == len(lines):
                        ok = []
                    for t in lines:
                        if t not in ok:
                            dropped.append(f'{sk}/{dept}/{lab}/{t[:20]}')
                    lines = ok
                elif label_bad:
                    dropped.append(f'{sk}/{dept}/{lab}')
                    continue
                if lines:
                    row[lab] = [lines if len(lines) > 1 else lines[0], None]
            if row:
                disp[sk][dept] = row
    for dept, items in (out.get('sec7') or {}).items():
        keep = []
        for t in items or []:
            if not t:
                continue
            nt = _norm(t)
            flagged = any(s and (s == nt or s in nt or nt in s) for s in bad_sent)       # 사실 검증이 지목한 문장(7번 위치 표기가 달라도 문장으로 찾는다)
            if any(n not in have for n in S.nums(t)) or ('sec7', dept, None) in bad or flagged:
                dropped.append(f'sec7/{dept}/{t[:20]}')
                continue
            keep.append(t)
        if keep:
            disp['sec7'][dept] = keep
    return disp, dropped


def missing_langs(display):
    ko = (display or {}).get('ko')
    if not has_content(ko):
        return []
    return [lg for lg, _ in LANGS if lg not in display]


def build_display_i18n(out, flags, warn, cells, quant, have=None, say=print):
    """화면용(ko) + 번역(en·zh). have 에 이미 있는 언어는 다시 번역하지 않는다. 번역 실패는 그 언어만 비워 두고(한글로 대체 표시) 계속한다."""
    ko, dropped = make_display(out, flags, warn, cells, quant)
    res = {'ko': ko}
    for lg in (have or {}):
        if lg != 'ko' and have[lg]:
            res[lg] = have[lg]
    if has_content(ko):
        for lg, name in LANGS:
            if lg in res:
                continue
            tr = None
            for attempt in (1, 2):                      # 구조가 어긋나 None 이 오는 경우가 있어 한 번 더 시도
                try:
                    tr = S.translate_struct(ko, name)
                except Exception as ex:
                    say(f'[경고] {name} 번역 실패({attempt}/2) — {ex!r}')
                    tr = None
                    break                               # 호출 자체가 실패(한도 등)면 재시도하지 않는다
                if tr:
                    break
            if tr:
                res[lg] = tr
    return res, dropped


def _save(path, d):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)                               # 쓰는 도중 꺼져도 반쪽 파일이 남지 않게 교체 방식으로 저장


def build(ent, code, cells=None, force=False, redo_display=False, quant_file=None, say=print):
    """한 법인·한 코드의 정리본을 만든다. 반환: 'made'(새로 만듦) | 'filled'(번역만 보충) | 'redo'(화면용 다시) | 'skip'(원문 같음) | 'empty'(요약할 글 없음)
    호출 자체가 실패하면 예외를 그대로 올린다(호출하는 쪽이 건너뛸지 정한다)."""
    path = os.path.join(DRAFT_DIR, f'{ent}_{code}.json')
    qp = quant_file or os.path.join(QUANT_DIR, f'{ent}_{code}.txt')
    quant = open(qp, encoding='utf-8').read() if os.path.exists(qp) else ''
    old = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else None

    if redo_display and old:
        disp, dropped = build_display_i18n(old['out'], old.get('flags', []), old.get('warn', []), old['cells'], old.get('quant', ''), say=say)
        old['display'], old['dropped'] = disp, dropped
        _save(path, old)
        say(f'화면용 갱신: {path} / 뺀 줄 {len(dropped)}')
        return 'redo'

    if cells is None:
        cells, _stat = R.read_cells(ent, code)
    cells = [c for c in cells if len(c['text']) > 3]          # '測試' 같은 시험 입력(2자)은 제외
    if not cells:
        return 'empty'
    h = src_hash(cells, quant)
    if old and old.get('hash') == h and old.get('display') and not force:
        miss = missing_langs(old['display'])
        if not miss:
            return 'skip'
        disp, dropped = build_display_i18n(old['out'], old.get('flags', []), old.get('warn', []), old['cells'], old.get('quant', ''), have=old['display'], say=say)
        old['display'], old['dropped'] = disp, dropped
        _save(path, old)
        left = missing_langs(disp)
        say(f'번역 보충: {ent} {code} — 채움 {len(miss) - len(left)}개 / 아직 빠짐 {left}')
        return 'filled'

    name = {'HK': '홍콩', 'TW': '대만'}[ent]
    period = (f'2026년 {int(code[1:])}월' if code[0] == 'M' else f'{code} 주차')
    out, flags = S.summarize(name, period, cells, quant)
    say(f'{ent} {code}: 숫자 검수 대상 {len(flags)}건 — 사실 검증 중…')
    warn = S.verify_claims(out, cells, quant)
    disp, dropped = build_display_i18n(out, flags, warn, cells, quant, say=say)
    _save(path, {'ent': ent, 'code': code, 'made_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'hash': h,
                 'quant': quant, 'cells': cells, 'out': out, 'flags': flags, 'warn': warn, 'display': disp, 'dropped': dropped})
    say(f'저장: {path} / 사실 검증 경고 {len(warn)}건, 화면에서 뺀 줄 {len(dropped)}개 / 번역 빠짐 {missing_langs(disp)}')
    for d_ in dropped:
        say(f'   뺌: {d_}')
    for w_ in warn:
        say(f"   경고: {str(w_.get('위치', ''))} — {str(w_.get('문제', ''))[:60]}")
    return 'made'


def auto_codes(week, year=None, today=None):
    """그 주(ISO)의 주간 코드 + 그 주가 속한 달 (+ 월초(14일까지)엔 지난 달).  예) 10/19 에 41주 → ['W41', 'M10'], 11/3 에 44주 → ['W44', 'M11', 'M10']"""
    today = today or datetime.date.today()
    year = year or today.year
    mon = datetime.date.fromisocalendar(year, int(week), 1)
    sun = mon + datetime.timedelta(days=6)
    codes = [f'W{int(week)}', f'M{sun.month:02d}']
    if sun.month > 1 and today.day <= 14:               # 지난 달 마감 글은 월초에만 고쳐진다 — 실행하는 날이 중순 이후면 다시 보지 않는다(사용량 절약)
        codes.append(f'M{sun.month - 1:02d}')
    return list(dict.fromkeys(codes))


def run_all(ents, codes, say=print, force=False, max_fail=2):
    """여러 법인·코드를 차례로. 시트는 법인당 한 번만 읽고, 한 건이 실패해도 나머지는 계속한다.
    연속으로 max_fail 번 실패하면(사용 한도 등) 나머지는 건너뛴다. 반환: {'TW M09': '상태', ...}"""
    res, fails = {}, 0
    S.usage_reset()
    for ent in ents:
        try:
            got = R.read_many(ent, codes)
        except Exception as ex:
            say(f'[경고] {ent} 시트 읽기 실패 — 건너뜀: {ex!r}')
            for c in codes:
                res[f'{ent} {c}'] = 'read-failed'
            continue
        for code in codes:
            key = f'{ent} {code}'
            if fails >= max_fail:
                res[key] = 'skipped'
                continue
            try:
                cells = got[code][0] if code in got else []
                res[key] = build(ent, code, cells=cells, force=force, say=say)
                if res[key] != 'empty':
                    fails = 0                                   # 성공하면 연속 실패 횟수를 되돌린다
            except Exception as ex:
                fails += 1
                res[key] = 'failed'
                say(f'[경고] {key} 정리 실패({fails}/{max_fail}) — {ex!r}')
                if fails >= max_fail:
                    say('[경고] 연속 실패 — 사용 한도 등으로 보고 나머지 정리는 건너뜁니다 (다음 실행에서 이어서 만듦)')
    say('[사용량] ' + S.usage_report())
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ent', choices=['HK', 'TW'])
    ap.add_argument('--code')
    ap.add_argument('--auto-week', type=int, help='그 주의 주간·이번 달·지난 달 코드를 한 번에 (--ent 없으면 양쪽 법인)')
    ap.add_argument('--quant-file')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--redo-display', action='store_true', help='저장된 정리본에서 화면용(핵심+번역)만 다시 만든다')
    a = ap.parse_args(argv)
    if a.auto_week:
        res = run_all([a.ent] if a.ent else ['HK', 'TW'], auto_codes(a.auto_week), force=a.force)
        print(json.dumps(res, ensure_ascii=False))
        return 1 if any(v in ('failed', 'read-failed') for v in res.values()) else 0
    if not (a.ent and a.code):
        ap.error('--ent 와 --code (또는 --auto-week) 가 필요합니다')
    st = build(a.ent, a.code, force=a.force, redo_display=a.redo_display, quant_file=a.quant_file)
    msg = {'skip': '원문이 지난번과 같아 건너뜀 (--force 로 다시 만들기)', 'empty': '요약할 글이 없습니다.'}.get(st)
    if msg:
        print(msg)
    return 1 if st == 'empty' else 0


if __name__ == '__main__':
    raise SystemExit(main())
