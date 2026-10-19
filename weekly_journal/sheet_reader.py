# -*- coding: utf-8 -*-
"""구글 시트(Apps Script)에서 SUMMARY 5~7번에 쓰이는 부서 글을 읽어 온다 (읽기 전용 계정 summarizer).

로그인 정보: apps_script/weekly_journal/summarizer_login.txt (첫 줄 아이디, 둘째 줄 비밀번호) 또는 환경변수 WJ_SUM_ID / WJ_SUM_PW.
읽기만 한다 — 시트에 쓰는 요청(save 등)은 이 파일에 없다.

사용:  python weekly_journal/sheet_reader.py --ent TW --week M09        (칸별로 글이 있는지 요약 출력 + _sheet_read_TW_M09.json 저장)
"""
import argparse
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CFG_DIR = os.path.join(ROOT, 'apps_script', 'weekly_journal')

# SUMMARY 5~7번 줄 → (섹션, 부서 코드, 항목 코드, 부서 이름, 항목 이름)   (gen_journal4._sum_tail 과 같은 대응)
ROWS = [
    ('5', 'SALES', 'comp', '영업', '경쟁사 동향'), ('5', 'MD', 'pcomp', '상품기획', '경쟁사 상품현황'), ('5', 'EC', 'eccomp', 'EC', '경쟁사 동향'),
    ('5', 'VMD', 'vcomp', 'VMD', '경쟁사 VMD'), ('5', 'MKT', 'mcomp', '마케팅', '경쟁사 마케팅'),
    ('6', 'GM', 'head', 'GM', '총평'), ('6', 'GM', 'special', 'GM', '특이사항'), ('6', 'SALES', 'bch', '영업', '부진 채널 (사유)'),
    ('6', 'SALES', 'sspecial', '영업', '특이사항'), ('6', 'MD', 'bad', '상품기획', '부진 상품 (사유)'), ('6', 'EC', 'ecbad', 'EC', '부진 상품 (사유)'),
    ('6', 'TRADE', 'tissue', '물류', '문제사항'), ('6', 'HR', 'hr1', 'HR', '인력 현황'), ('6', 'HR', 'hr2', 'HR', '채용·이동'),
    ('6', 'FIN', 'fi1', '회계/재무', '재무 현황'), ('6', 'FIN', 'fi2', '회계/재무', '채권·이슈'),
    ('7', 'GM', 'strat', 'GM', '향후전략'), ('7', 'MD', 'strat', '상품기획', '향후전략'), ('7', 'SALES', 'strat', '영업', '향후전략'),
    ('7', 'EC', 'strat', 'EC', '향후전략'), ('7', 'VMD', 'strat', 'VMD', '향후전략'), ('7', 'MKT', 'strat', '마케팅', '향후전략'),
    ('7', 'TRADE', 'strat', '물류', '향후전략'), ('7', 'HR', 'strat', 'HR', '향후전략'), ('7', 'FIN', 'strat', '회계/재무', '향후전략'),
    ('7', 'GM', 'ask', 'GM', 'HQ 요청사항'),
]


def read_cfg(fname, env):
    if os.environ.get(env):
        return os.environ[env].strip()
    p = os.path.join(CFG_DIR, fname)
    return open(p, encoding='utf-8').read().strip() if os.path.exists(p) else ''


def post(url, body, timeout=120):
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'text/plain;charset=utf-8'})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def login():
    url = read_cfg('api_url.txt', 'WJ_API_URL')
    if not url:
        raise RuntimeError('api_url.txt 가 없습니다.')
    uid, pw = os.environ.get('WJ_SUM_ID'), os.environ.get('WJ_SUM_PW')
    if not (uid and pw):
        p = os.path.join(CFG_DIR, 'summarizer_login.txt')
        if not os.path.exists(p):
            raise RuntimeError('summarizer_login.txt 가 없습니다. (첫 줄 아이디, 둘째 줄 비밀번호)')
        lines = [x.strip() for x in open(p, encoding='utf-8-sig').read().splitlines() if x.strip()]
        if len(lines) < 2:
            raise RuntimeError('summarizer_login.txt 형식이 올바르지 않습니다. (두 줄 필요)')
        uid, pw = lines[0], lines[1]
    r = post(url, {'a': 'login', 'id': uid, 'password': pw, 'who': '요약기'})
    if not r.get('ok'):
        raise RuntimeError('로그인 실패: ' + str(r.get('error')))
    return url, r['token'], r.get('me') or {}


def strip_html(h):
    t = re.sub(r'<br\s*/?>|</p>|</div>|</li>', '\n', str(h or ''), flags=re.I)
    t = re.sub(r'<[^>]*>', '', t).replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    return re.sub(r'[ \t]+', ' ', re.sub(r'\n\s*\n+', '\n', t)).strip()


def read_cells(ent, week):
    """(원문 칸 목록, 원본 통계). 칸마다 ko → en → zh 순으로 글이 있는 언어를 쓴다. 반환 칸: {sec, dept, item, text, lang}"""
    url, tok, me = login()
    r = post(url, {'a': 'pullMany', 'ent': ent, 'weeks': [week], 'photos': False, 'token': tok})
    res = (r.get('results') or [{}])[0]
    if not r.get('ok') or not res.get('ok'):
        raise RuntimeError('읽기 실패: ' + str(r.get('error') or res.get('error')))
    cells = res.get('cells') or {}
    out, stat = [], {'role': me.get('role'), 'cells_total': len(cells)}
    for sec, dc, ik, dn, inm in ROWS:
        got = None
        for lang in ('ko', 'en', 'zh'):
            c = cells.get('|'.join([ent, week, dc, ik, lang]))
            t = strip_html(c.get('html')) if c else ''
            if t:
                got = (t, lang, c.get('by'), c.get('at'), c.get('version'))
                break
        if got:
            out.append({'sec': sec, 'dept': dn, 'item': inm, 'text': got[0], 'lang': got[1], 'by': got[2], 'at': got[3], 'version': got[4]})
    stat['cells_used'] = len(out)
    return out, stat


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--ent', required=True, choices=['HK', 'TW'])
    ap.add_argument('--week', required=True, help='예: M09 (월간 9월) 또는 W41')
    a = ap.parse_args()
    cells, stat = read_cells(a.ent, a.week)
    path = os.path.join(HERE, f'_sheet_read_{a.ent}_{a.week}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'stat': stat, 'cells': cells}, f, ensure_ascii=False, indent=1)
    print('읽기 성공 — 권한:', stat['role'], '/ 시트 칸 수:', stat['cells_total'], '/ SUMMARY 5~7 에 쓰이는 칸:', stat['cells_used'])
    for c in cells:
        print(f"  섹션{c['sec']} {c['dept']} · {c['item']} [{c['lang']}] {len(c['text'])}자")
    print('저장:', path)
