# -*- coding: utf-8 -*-
"""승인된 SUMMARY 정리본(summary_approved/{ENT}_{CODE}.json)을 5·6·7번 화면 조각으로 만든다.

승인본이 있는 섹션에는 부서별 카드(핵심 한 줄 + 보충)를 맨 위에 보여 주고, 부서가 쓴 원문 표는 '원문 보기'로 접어 둔다.
승인본이 없으면 아무것도 바꾸지 않는다(기존 화면 그대로).
파일 형식: {"ko": {"sec5": {...}, "sec6": {...}, "sec7": {...}}, "en": {...}, "zh": {...}}   (en/zh 가 없으면 한글을 그대로 쓴다)
"""
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
APPROVED_DIR = os.path.join(HERE, 'summary_approved')

LABELS = {'동향': ('Trend', '動向'), '대응': ('Response', '因應'), '결과': ('Result', '結果'), '원인': ('Cause', '原因'), '조치': ('Action', '措施')}
ORDER = ['GM', 'GM(HQ 요청)', '영업', '상품기획', 'EC', 'VMD', '마케팅', '물류', 'HR', '회계/재무']
DEPT_NAMES = {'GM': ('GM', 'GM'), 'GM(HQ 요청)': ('GM (HQ requests)', 'GM（總部需求）'), '영업': ('Sales', '業務'), '상품기획': ('Merchandising', '商品企劃'),
              'EC': ('EC', 'EC'), 'VMD': ('VMD', 'VMD'), '마케팅': ('Marketing', '行銷'), '물류': ('Logistics', '物流'), 'HR': ('HR', '人資'), '회계/재무': ('Finance', '財務')}
SEC_LABELS = {'sec5': ('동향', '대응'), 'sec6': ('결과', '원인', '조치')}

CSS = ('<style>.smt{margin:0 0 10px}'
       '.smt .ln{display:flex;gap:10px;align-items:flex-start;margin:0 0 6px}.smt .ln:last-child{margin-bottom:0}'
       '.smt .bd{flex:0 0 auto;min-width:46px;box-sizing:border-box;text-align:center;margin-top:2px;padding:1px 10px;background:#f3f4f6;border:1px solid #e5e7eb;border-radius:6px;color:#111;font-size:12.5px;font-weight:700;line-height:1.6;white-space:nowrap}'
       '.smt .tx{flex:1 1 auto;min-width:0}.smt .tx p{margin:0 0 4px}.smt .tx p:last-child{margin-bottom:0}'
       '.smt b.k{background:#fff3b0;color:#111;padding:0 2px;border-radius:2px;font-weight:inherit}'
       '.smt td.sv>p{margin:0 0 4px}.smt td.sv>p:last-child{margin-bottom:0}'
       'details.raw{margin:8px 0 0}details.raw>summary{cursor:pointer;color:#6b7280;font-size:12.5px;padding:4px 0}'
       '@media (prefers-color-scheme:dark){.smt b.k{background:#4a4220;color:#fff}.smt .bd{background:#2a2d33;border-color:#3a3e45;color:#f3f4f6}}</style>')
STRAT_LABEL = {'ko': '향후전략', 'en': 'Next strategy', 'zh': '後續策略'}
ASK_LABEL = {'ko': 'HQ 요청사항', 'en': 'HQ requests', 'zh': '總部需求'}
BOLD = re.compile(r'(\d[\d,.]*(?:~\d+)?%|\d[\d,.]*만 TWD|\d[\d,.]*달러)')


def path_for(ent, code):
    return os.path.join(APPROVED_DIR, f'{ent}_{code}.json')


def load(ent, code):
    """승인본(summary_approved)이 있으면 그것, 없으면 자동 정리본(summary_draft/*.json 의 display)을 쓴다."""
    for p, key in ((path_for(ent, code), None), (os.path.join(HERE, 'summary_draft', f'{ent}_{code}.json'), 'display')):
        if not os.path.exists(p):
            continue
        try:
            d = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        d = d.get(key) if key else d
        if d and d.get('ko'):
            return d
    return None


def fmt(t):
    return BOLD.sub(r'<b class="k">\1</b>', html.escape(str(t or '')))


def _dept_label(dept, lang):
    n = DEPT_NAMES.get(dept)
    return n[0] if lang == 'en' and n else n[1] if lang == 'zh' and n else dept


def _label(lab, lang):
    n = LABELS.get(lab)
    return n[0] if lang == 'en' and n else n[1] if lang == 'zh' and n else lab


def _rows(sec_key, data, lang):
    """부서마다 한 행: 왼쪽은 부서명만, 오른쪽에는 '[배지] 내용' 줄이 항목 수만큼 쌓인다(기존 5·6·7번 표(.t3)와 같은 모양).
    같은 맥락은 한 줄, 다른 맥락은 한 배지 아래에서 줄을 나눠 보인다."""
    sec = (data or {}).get(sec_key) or {}
    depts = sorted(sec, key=lambda d: ORDER.index(d) if d in ORDER else 99)
    rows = ''
    for d in depts:
        val = sec[d]
        if not val:
            continue
        ask = d == 'GM(HQ 요청)'
        name = html.escape(_dept_label('GM' if ask else d, lang))
        if sec_key == 'sec7':
            items = [x for x in val if x]
            if not items:
                continue
            body = ''.join(f'<p>{n}. {fmt(x)}</p>' for n, x in enumerate(items, 1))
            if ask:                                                        # GM 은 전략 행과 HQ 요청 행이 따로 있어 구분 배지를 단다
                body = f'<div class="ln"><span class="bd">{html.escape(ASK_LABEL[lang])}</span><span class="tx">{body}</span></div>'
            rows += f'<tr><td class="dp">{name}</td><td class="sv">{body}</td></tr>'
            continue
        lines = ''
        for lab in SEC_LABELS[sec_key]:
            v = val.get(lab)
            if not v or not v[0]:
                continue
            core = v[0]
            ps = ''.join(f'<p>{fmt(x)}</p>' for x in (core if isinstance(core, list) else [core]) if x)
            if ps:
                lines += f'<div class="ln"><span class="bd">{html.escape(_label(lab, lang))}</span><span class="tx">{ps}</span></div>'
        if lines:
            rows += f'<tr><td class="dp">{name}</td><td class="sv">{lines}</td></tr>'
    return rows


def cards(ent, code):
    """{'5': html, '6': html, '7': html} 또는 None (승인본이 없을 때). 언어별 div(.ko/.en/.zh)로 묶어 언어 전환을 따른다."""
    data = load(ent, code)
    if not data or not data.get('ko'):
        return None
    res = {}
    for n in ('5', '6', '7'):
        parts = ''
        for lang in ('ko', 'en', 'zh'):
            d = data.get(lang) or data['ko']
            c = _rows('sec' + n, d, lang)
            if c:
                parts += f'<div class="{lang}"><table class="t3 smt">{c}</table></div>'
        if parts:
            res[n] = CSS + parts
    return res or None


def merge(sec_html, cards_html):
    """섹션 HTML 의 부서 원문 표(<table class="t3">)를 '원문 보기'로 접고, 그 위에 요약 표를 넣는다."""
    if not cards_html or '<table class="t3">' not in sec_html:
        return sec_html
    s = sec_html.replace('<table class="t3">', '@@SUMMARY@@<details class="raw"><summary>부서 원문 보기</summary><table class="t3">', 1)
    s = s.replace('</table>', '</table></details>', 1)
    return s.replace('@@SUMMARY@@', cards_html, 1)
