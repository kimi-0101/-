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
import copy
import datetime
import hashlib
import json
import os
import re
import sys
import threading

import sheet_reader as R
import summarize_cells as S

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT_DIR = os.path.join(HERE, 'summary_draft')
QUANT_DIR = os.path.join(HERE, 'summary_quant')
LANGS = (('en', '영어'), ('zh', '번체 중국어(대만·홍콩 업무 용어)'))


def src_hash(cells, quant):
    raw = json.dumps([[c['sec'], c['dept'], c['item'], c['text']] for c in cells], ensure_ascii=False) + '|' + quant
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()[:16]


def _owner(key):
    """AI 결과의 부서 키 → 원문 칸의 부서 이름.  'GM(HQ 요청)' 은 GM 칸에서 나온 것이므로 'GM'."""
    return re.split(r'[（(]', str(key or ''))[0].strip()


def dept_hashes(cells, quant):
    """부서마다 원문(섹션·항목·글)과 정량 블록의 해시. 한 부서의 글만 고쳐지면 그 부서 해시만 바뀐다."""
    by = {}
    for c in cells:
        by.setdefault(c['dept'], []).append([c['sec'], c['item'], c['text']])
    return {d: hashlib.sha1((json.dumps(v, ensure_ascii=False) + '|' + quant).encode('utf-8')).hexdigest()[:12] for d, v in by.items()}


def _keys(disp):
    return {(sec, k) for sec in ('sec5', 'sec6', 'sec7') for k in ((disp or {}).get(sec) or {})}


def diff_keys(old_ko, new_ko):
    """화면용 한글에서 새로 생기거나 내용이 바뀐 (섹션, 부서) 와 사라진 것."""
    changed = {(s, k) for s, k in _keys(new_ko) if ((old_ko or {}).get(s) or {}).get(k) != new_ko[s][k]}
    removed = {(s, k) for s, k in _keys(old_ko) if k not in (new_ko.get(s) or {})}
    return changed, removed


def restrict(disp, keys):
    out = {'sec5': {}, 'sec6': {}, 'sec7': {}}
    for s, k in keys:
        if k in (disp.get(s) or {}):
            out[s][k] = disp[s][k]
    return out


def merge_lang(old_lang, part, ko, changed, removed):
    """기존 번역에서 바뀐·사라진 줄을 빼고, 새로 번역한 줄을 넣는다. 한글 화면의 모든 줄이 채워지지 않으면 None(그 언어는 비워 두고 다음에 전체를 번역)."""
    m = copy.deepcopy(old_lang)
    for s, k in changed | removed:
        (m.get(s) or {}).pop(k, None)
    for s in ('sec5', 'sec6', 'sec7'):
        for k, v in (part.get(s) or {}).items():
            m.setdefault(s, {})[k] = v
    for s in ('sec5', 'sec6', 'sec7'):
        for k in list((m.get(s) or {})):
            if k not in (ko.get(s) or {}):
                del m[s][k]
        for k in (ko.get(s) or {}):
            if k not in (m.get(s) or {}):
                return None
    return m


def _norm(t):
    return ''.join(str(t or '').split())


def has_content(ko):
    return any((ko or {}).get(k) for k in ('sec5', 'sec6', 'sec7'))


def _line_bad(t, have, bad_sent):
    nt = _norm(t)
    return any(n not in have for n in S.nums(t)) or any(x and (x == nt or x in nt or nt in x) for x in bad_sent)


def _why(t, have, bad_sent):
    """줄을 뺀 이유(로그용)"""
    miss = sorted(n for n in S.nums(t) if n not in have)
    if miss:
        return f'숫자 {miss} 가 원문·정량에 없음'
    nt = _norm(t)
    if any(x and (x == nt or x in nt or nt in x) for x in bad_sent):
        return '사실 검증 경고'
    return '라벨 전체에 경고'


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
                            dropped.append(f'{sk}/{dept}/{lab}/{t[:20]} ← {_why(t, have, bad_sent)}')
                    lines = ok
                elif label_bad:
                    dropped.append(f'{sk}/{dept}/{lab} ← {_why(lines[0], have, bad_sent)}')
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
                dropped.append(f'sec7/{dept}/{t[:20]} ← {_why(t, have, bad_sent)}')
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


def _translate_many(jobs, say):
    """jobs: [(언어코드, 언어이름, 번역할 구조)] → {언어코드: 번역 또는 None}. 서로 독립이라 동시에 부른다."""
    def one(job):
        lg, name, struct = job
        tr = None
        for attempt in (1, 2):                          # 구조가 어긋나 None 이 오는 경우가 있어 한 번 더 시도
            try:
                tr = S.translate_struct(struct, name)
            except Exception as ex:
                say(f'[경고] {name} 번역 실패({attempt}/2) — {ex!r}')
                tr = None
                break                                   # 호출 자체가 실패(한도 등)면 재시도하지 않는다
            if tr:
                break
        return lg, tr
    if len(jobs) > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=len(jobs)) as ex_:
            return dict(ex_.map(one, jobs))
    return dict(one(j) for j in jobs)


def build_display_i18n(out, flags, warn, cells, quant, have=None, say=print, old_ko=None):
    """화면용(ko) + 번역(en·zh). have 에 이미 있는 언어는 다시 번역하지 않는다. 번역 실패는 그 언어만 비워 두고(한글로 대체 표시) 계속한다.
    old_ko(이전 화면용 한글)를 주면 '바뀐 줄만' 번역해서 기존 번역에 합친다."""
    ko, dropped = make_display(out, flags, warn, cells, quant)
    res = {'ko': ko}
    keep = {lg: have[lg] for lg in (have or {}) if lg != 'ko' and have[lg]}
    if not has_content(ko):
        res.update(keep)
        return res, dropped
    changed = removed = set()
    partial = old_ko is not None and bool(keep)
    if partial:
        changed, removed = diff_keys(old_ko, ko)
    jobs, merged = [], {}
    for lg, name in LANGS:
        if lg in keep and partial:
            if changed:
                jobs.append((lg, name, restrict(ko, changed)))       # 바뀐 줄만 번역
            else:
                m = merge_lang(keep[lg], {}, ko, changed, removed)   # 번역할 게 없으면 사라진 줄만 정리
                if m:
                    merged[lg] = m
        elif lg in keep:
            res[lg] = keep[lg]
        else:
            jobs.append((lg, name, ko))                              # 아직 없는 언어는 전체 번역
    got = _translate_many(jobs, say) if jobs else {}
    for lg, name, struct in jobs:
        tr = got.get(lg)
        if not tr:
            continue
        if lg in keep and partial:
            m = merge_lang(keep[lg], tr, ko, changed, removed)
            if m:
                merged[lg] = m
        else:
            res[lg] = tr
    res.update(merged)
    return res, dropped


def _save(path, d):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)                               # 쓰는 도중 꺼져도 반쪽 파일이 남지 않게 교체 방식으로 저장


def summarize_verify(name, period, cells, quant, say=print):
    """부서를 WJ_BATCH(기본 3)개씩 묶어 묶음마다 정리·검증을 동시에 돌리고 합친다. 한 건이 '가장 느린 묶음 하나'의 시간으로 끝난다.
    한 묶음이라도 실패하면 예외를 그대로 올린다(반쪽짜리 결과는 저장하지 않는다)."""
    depts = list(dict.fromkeys(c['dept'] for c in cells))
    n = max(1, int(os.environ.get('WJ_BATCH', '3')))
    groups = [depts[i:i + n] for i in range(0, len(depts), n)]

    def one(g):
        part = [c for c in cells if c['dept'] in g]
        out, flags = S.summarize(name, period, part, quant)
        warn = S.verify_claims(out, part, quant)
        if warn and os.environ.get('WJ_REPAIR', '1') != '0':           # 지적된 줄은 버리지 않고 지적 이유를 알려 주며 다시 쓰게 한다
            try:
                out, warn, n = S.repair_flagged(out, warn, part, quant)
                if n:
                    flags = S.check_numbers(out, part, quant)
            except Exception as ex:
                say(f'[경고] 보정 단계 실패 — 지적된 줄은 그대로 뺍니다: {ex!r}')
        return out, flags, warn
    if len(groups) > 1:
        from concurrent.futures import ThreadPoolExecutor
        ctx = getattr(S._CTX, 'v', '')

        def run(g):
            S.set_ctx(ctx)
            return one(g)
        with ThreadPoolExecutor(max_workers=len(groups)) as ex_:
            parts = list(ex_.map(run, groups))
    else:
        parts = [one(groups[0])]
    out, flags, warn = {'sec5': {}, 'sec6': {}, 'sec7': {}}, [], []
    for o, f, w in parts:
        for sec in out:
            out[sec].update((o or {}).get(sec) or {})
        flags += f
        warn += w
    say(f'   요약·검증 {len(groups)}묶음(부서 {len(depts)}개) 처리 — 숫자 검수 대상 {len(flags)}건, 사실 검증 경고 {len(warn)}건')
    return out, flags, warn


def build(ent, code, cells=None, force=False, redo_display=False, quant_file=None, say=print):
    """한 법인·한 코드의 정리본을 만든다. 반환: 'made'(새로 만듦) | 'updated'(바뀐 부서만 다시 요약) | 'filled'(번역만 보충) | 'redo'(화면용 다시) | 'skip'(원문 같음) | 'empty'(요약할 글 없음)
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
    cur = dept_hashes(cells, quant)
    name = {'HK': '홍콩', 'TW': '대만'}[ent]
    period = (f'2026년 {int(code[1:])}월' if code[0] == 'M' else f'{code} 주차')
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

    if old and old.get('display') and not force:
        old_dh = old.get('dept_hash') or dept_hashes([c for c in old.get('cells', []) if len(c['text']) > 3], old.get('quant', ''))     # 예전 저장본도 다시 만들지 않고 원문에서 계산해 이어받는다(시험 입력 칸은 같은 기준으로 제외)
        changed_d = sorted(d for d in cur if old_dh.get(d) != cur[d])
        removed_d = sorted(d for d in old_dh if d not in cur)
        if not changed_d and not removed_d:
            miss = missing_langs(old['display'])
            if not miss:
                return 'skip'
            disp, dropped = build_display_i18n(old['out'], old.get('flags', []), old.get('warn', []), old['cells'], old.get('quant', ''), have=old['display'], say=say)
            old['display'], old['dropped'], old['dept_hash'] = disp, dropped, cur
            _save(path, old)
            left = missing_langs(disp)
            say(f'번역 보충: {ent} {code} — 채움 {len(miss) - len(left)}개 / 아직 빠짐 {left}')
            return 'filled'
        # 바뀐 부서만 다시 요약한다
        gone = set(changed_d) | set(removed_d)
        part_cells = [c for c in cells if c['dept'] in changed_d]
        out_new, flags_new, warn_new = {}, [], []
        if part_cells:
            say(f'{ent} {code}: 바뀐 부서 {changed_d} 만 다시 요약 (그대로 둔 부서 {len(cur) - len(changed_d)}개, 사라진 부서 {removed_d})')
            out_new, flags_new, warn_new = summarize_verify(name, period, part_cells, quant, say=say)
        else:
            say(f'{ent} {code}: 사라진 부서 {removed_d} 만 정리 (AI 호출 없음)')
        out = {}
        for sec in ('sec5', 'sec6', 'sec7'):
            out[sec] = {k: v for k, v in ((old.get('out') or {}).get(sec) or {}).items() if _owner(k) not in gone}
            for k, v in ((out_new or {}).get(sec) or {}).items():
                if _owner(k) in changed_d:
                    out[sec][k] = v
        flags = [f for f in old.get('flags', []) if _owner(f[1]) not in gone] + [f for f in flags_new if _owner(f[1]) in changed_d]
        warn = [w for w in old.get('warn', []) if _owner((str(w.get('위치', '')).split('/') + ['', ''])[1]) not in gone] \
            + [w for w in warn_new if _owner((str(w.get('위치', '')).split('/') + ['', ''])[1]) in changed_d]
        disp, dropped = build_display_i18n(out, flags, warn, cells, quant, have=old['display'], say=say, old_ko=old['display'].get('ko'))
        _save(path, {'ent': ent, 'code': code, 'made_at': now, 'hash': h, 'dept_hash': cur, 'quant': quant, 'cells': cells, 'out': out,
                     'flags': flags, 'warn': warn, 'display': disp, 'dropped': dropped})
        say(f'저장(부분 갱신): {path} / 사실 검증 경고 {len(warn)}건, 화면에서 뺀 줄 {len(dropped)}개 / 번역 빠짐 {missing_langs(disp)}')
        _log_detail(say, dropped, warn_new)
        return 'updated'

    out, flags, warn = summarize_verify(name, period, cells, quant, say=say)
    disp, dropped = build_display_i18n(out, flags, warn, cells, quant, say=say)
    _save(path, {'ent': ent, 'code': code, 'made_at': now, 'hash': h, 'dept_hash': cur,
                 'quant': quant, 'cells': cells, 'out': out, 'flags': flags, 'warn': warn, 'display': disp, 'dropped': dropped})
    say(f'저장: {path} / 사실 검증 경고 {len(warn)}건, 화면에서 뺀 줄 {len(dropped)}개 / 번역 빠짐 {missing_langs(disp)}')
    _log_detail(say, dropped, warn)
    return 'made'


def repair_existing(ent, code, say=print):
    """이미 저장된 정리본의 '검증에서 지적된 줄'을 다시 쓰게 하고(버리지 않고), 바뀐 줄만 다시 번역하며, 빠진 번역도 채운다. 시트는 읽지 않는다.
    반환: 'repaired' | 'none'(저장본 없음)"""
    path = os.path.join(DRAFT_DIR, f'{ent}_{code}.json')
    if not os.path.exists(path):
        return 'none'
    old = json.load(open(path, encoding='utf-8'))
    cells = [c for c in old.get('cells', []) if len(c['text']) > 3]
    quant = old.get('quant', '')
    out, warn, n = S.repair_flagged(old['out'], old.get('warn', []), cells, quant)
    flags = S.check_numbers(out, cells, quant)
    disp, dropped = build_display_i18n(out, flags, warn, cells, quant, have=old.get('display'), say=say, old_ko=(old.get('display') or {}).get('ko'))
    old.update(out=out, flags=flags, warn=warn, display=disp, dropped=dropped, dept_hash=old.get('dept_hash') or dept_hashes(cells, quant),
               made_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    _save(path, old)
    say(f'보정 {ent} {code}: 고친 줄 {n}개 / 아직 뺀 줄 {len(dropped)}개 / 사실 검증 경고 {len(warn)}건 / 번역 빠짐 {missing_langs(disp)}')
    _log_detail(say, dropped, warn)
    return 'repaired'


def _log_detail(say, dropped, warn):
    for d_ in dropped:
        say(f'   뺌: {d_}')
    for w_ in warn:
        say(f"   경고: {str(w_.get('위치', ''))} — {str(w_.get('문제', ''))[:60]}")


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


def run_all(ents, codes, say=print, force=False, max_fail=2, workers=1):
    """여러 법인·코드를 처리한다. 시트는 법인당 한 번만 읽고, 한 건이 실패해도 나머지는 계속한다.
    workers>1 이면 서로 독립인 (법인, 코드)를 동시에 돌려 전체 시간을 줄인다.
    사용 한도(limit) 오류가 나면 바로 나머지를 건너뛰고, 그 밖의 오류는 max_fail 번 연속이면 건너뛴다. 반환: {'TW M09': '상태', ...}"""
    S.usage_reset()
    res, tasks = {}, []
    for ent in ents:
        try:
            got = R.read_many(ent, codes)
        except Exception as ex:
            say(f'[경고] {ent} 시트 읽기 실패 — 건너뜀: {ex!r}')
            for c in codes:
                res[f'{ent} {c}'] = 'read-failed'
            continue
        for code in codes:
            tasks.append((ent, code, got[code][0] if code in got else []))
    lock, stop, state = threading.Lock(), threading.Event(), {'fails': 0}

    def work(t):
        ent, code, cells = t
        key = f'{ent} {code}'
        if stop.is_set():
            return key, 'skipped'
        S.set_ctx(key)
        try:
            st = build(ent, code, cells=cells, force=force, say=say)
            if st != 'empty':
                with lock:
                    state['fails'] = 0                          # 성공하면 연속 실패 횟수를 되돌린다
            return key, st
        except Exception as ex:
            with lock:
                state['fails'] += 1
                n = state['fails']
            say(f'[경고] {key} 정리 실패({n}/{max_fail}) — {ex!r}')
            if 'limit' in str(ex).lower() or n >= max_fail:
                if not stop.is_set():
                    say('[경고] 사용 한도 등으로 보고 나머지 정리는 건너뜁니다 (다음 실행에서 이어서 만듦)')
                stop.set()
            return key, 'failed'

    if workers > 1 and len(tasks) > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(workers, len(tasks))) as ex_:
            done = list(ex_.map(work, tasks))
    else:
        done = [work(t) for t in tasks]
    res.update(done)
    say('[사용량] ' + S.usage_report())
    return res


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):                    # 로그를 파일·파이프로 보내면 한글 윈도우(cp949)가 '—' 같은 글자를 못 써서 죽는다 → 못 쓰는 글자는 ?로 바꿔 계속 진행
        try:
            _s.reconfigure(errors='replace')
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument('--ent', choices=['HK', 'TW'])
    ap.add_argument('--code')
    ap.add_argument('--auto-week', type=int, help='그 주의 주간·이번 달·지난 달 코드를 한 번에 (--ent 없으면 양쪽 법인)')
    ap.add_argument('--quant-file')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--workers', type=int, default=3, help='동시에 돌릴 건수(법인×코드). 1 이면 차례로')
    ap.add_argument('--repair', action='store_true', help='저장된 정리본에서 검증이 지적한 줄을 다시 쓰고(버리지 않고), 바뀐 줄만 다시 번역하며 빠진 번역도 채운다 (--code 필요, --ent 없으면 양쪽)')
    ap.add_argument('--redo-display', action='store_true', help='저장된 정리본에서 화면용(핵심+번역)만 다시 만든다')
    a = ap.parse_args(argv)
    if a.auto_week:
        res = run_all([a.ent] if a.ent else ['HK', 'TW'], auto_codes(a.auto_week), force=a.force, workers=a.workers)
        print(json.dumps(res, ensure_ascii=False))
        return 1 if any(v in ('failed', 'read-failed') for v in res.values()) else 0
    if a.repair:
        if not a.code:
            ap.error('--repair 는 --code 가 필요합니다')
        S.usage_reset()
        rc = 0
        for ent in ([a.ent] if a.ent else ['HK', 'TW']):
            S.set_ctx(f'{ent} {a.code}')
            try:
                print(ent, a.code, repair_existing(ent, a.code))
            except Exception as ex:
                rc = 1
                print(f'[경고] {ent} {a.code} 보정 실패 — {ex!r}')
        print('[사용량] ' + S.usage_report())
        return rc
    if not (a.ent and a.code):
        ap.error('--ent 와 --code (또는 --auto-week) 가 필요합니다')
    st = build(a.ent, a.code, force=a.force, redo_display=a.redo_display, quant_file=a.quant_file)
    msg = {'skip': '원문이 지난번과 같아 건너뜀 (--force 로 다시 만들기)', 'empty': '요약할 글이 없습니다.'}.get(st)
    if msg:
        print(msg)
    return 1 if st == 'empty' else 0


if __name__ == '__main__':
    raise SystemExit(main())
