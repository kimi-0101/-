import json, io, calendar, datetime
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_journal3 import (DEPTS, DEPT_KEY, DEFAULT, HK_T, TW_T, HK_SUB, TW_SUB, EXTRA_CSS)
from gen_journal2 import (CSS, make_weeks, HK_GROUPS, TW_GROUPS, HK_WEEKS, TW_WEEKS, OUT, cls_ach, cls_g)

for _name, _items in DEPTS:
    if _name == '영업':
        _items.append(('특이사항', 'sspecial', ''))
for _name, _items in DEPTS:
    if _name == '상품기획':
        _items.append(('경쟁사 상품현황', 'pcomp', ''))
DEFAULT['sspecial'] = '특이사항 없음'
DEFAULT['pcomp'] = '특이 동향 없음'
HK_T[1]['pcomp'] = 'B사 가을 니트 신상 소량 입고.'
HK_T[3]['pcomp'] = 'B사 FW 경량 다운 라인 출시 (가격은 당사 대비 낮은 수준), 블랙&middot;카키 중심 구성.'
TW_T[1]['pcomp'] = '현지 브랜드 C 가을 니트 신상 입고.'
TW_T[3]['pcomp'] = '현지 브랜드 C가 경량 아우터 신상을 백화점 팝업에서 선판매.'

_ec = ('EC', [('호조 상품 (사유)', 'ecgood', 'good'), ('부진 상품 (사유)', 'ecbad', 'bad'), ('경쟁사', 'eccomp', ''),
              ('프로모션', 'ecpromo', ''), ('특이사항', 'ecspecial', '')])
_i = [n for n, _ in DEPTS].index('영업')
DEPTS.insert(_i + 1, _ec)
DEFAULT.update(eccomp='특이 동향 없음', ecspecial='특이사항 없음')
_tg = lambda s: f'<span class="tag">{s}</span>'
HK_T[1].update(ecgood=f'<p><b>키즈 라인</b> {_tg("트래픽")} 개학 시즌 가족 고객 구매.</p>',
               ecbad=f'<p><b>온라인 잔여 티셔츠</b> {_tg("재고&middot;시즌")} 쿠폰 없이 유입 감소.</p>', ecpromo='개학 프로모션')
HK_T[2].update(ecgood=f'<p><b>이너웨어</b> {_tg("프로모션")} 신학기 프로모션 효과.</p>',
               ecbad=f'<p><b>온라인 잔여 티셔츠</b> {_tg("재고&middot;시즌")} 노출 순위 하락.</p>', ecpromo='개학 프로모션')
HK_T[3].update(ecgood=f'<p><b>HKTV 타임딜 이너 3종</b> {_tg("프로모션")} {_tg("전환")}<br>앱 푸시 쿠폰 발송 직후 주문이 몰렸고, 주말 타임딜이 메인 상단에 노출되면서 유입 대비 구매 비율이 높아짐.</p>',
               ecbad=f'<p><b>온라인 잔여 티셔츠</b> {_tg("재고&middot;시즌")} {_tg("구조적")}<br>노출 순위 하락.</p>',
               eccomp='경쟁 B사 온라인몰 최대 20% 쿠폰 배포', ecpromo='HKTVmall 앱 쿠폰과 주말 타임딜 진행',
               ecspecial='HKTVmall 메인 개편 예정 (10/1), 상품 노출 위치 변동 가능.')
TW_T[1].update(ecgood=f'<p><b>이너웨어</b> {_tg("프로모션")} 신학기 프로모션 효과.</p>',
               ecbad=f'<p><b>여름 상품</b> {_tg("재고&middot;시즌")} 노출 순위 하락.</p>', ecpromo='개학 프로모션')
TW_T[2].update(ecgood=f'<p><b>이너웨어</b> {_tg("프로모션")} 신학기 프로모션으로 검색 노출 상승.</p>',
               ecbad=f'<p><b>여름 상품</b> {_tg("재고&middot;시즌")} 시즌 종료로 진열 축소.</p>', ecpromo='연휴 사전 프로모션')
TW_T[3].update(ecgood=f'<p><b>이너웨어 세트</b> {_tg("프로모션")} {_tg("전환")}<br>더블 포인트 이벤트 기간에 검색 노출이 올라 이너 상품 구매가 몰림.</p>',
               ecbad=f'<p><b>여름 잔여 상품</b> {_tg("재고&middot;시즌")}<br>시즌 종료로 진열 축소.</p>',
               eccomp='경쟁 플랫폼 시즌오프 쿠폰 배포 확인', ecpromo='온라인 몰 더블 포인트 이벤트 (MOMO)',
               ecspecial='MOMO 정산 주기 변경 공지 (10/1부터)')
HK_T[3]['sspecial'] = 'Harbour City 입구 보수 공사로 동선 일부 변경 (10/6까지), 방문객 유입에 영향 가능.'
TW_T[3]['sspecial'] = 'N-SKM TCH 판매 인력 1명 결원 (충원 진행 중, 10월 초 합류 예정).'

DEPTS.append(('물류', [('입고율', 'trate', ''), ('금주 입고 예정', 'tplan', ''), ('문제사항', 'tissue', '')]))
DEPTS.append(('HR', [('인력 현황', 'hr1', ''), ('채용·이동', 'hr2', '')]))                 # 2026-10-07 오웬 확정 (9/30 요청)
DEPTS.append(('회계/재무', [('재무 현황', 'fi1', ''), ('채권·이슈', 'fi2', '')]))

TRADE_HK = [
    dict(trate='FW 발주 대비 입고율 68% (누계)', tplan='이너 라인 2차 입고 (9/3)', tissue='특이사항 없음'),
    dict(trate='72% (누계)', tplan='아우터 1차 입고 (9/10)', tissue='통관 지연 1건 (1일 지연, 입고 완료)'),
    dict(trate='79% (누계)', tplan='경량 다운 재킷 입고 (9/17)', tissue='특이사항 없음'),
    dict(trate='85% (누계)', tplan='니트 2차 입고 (10/1), 경량 다운 재킷 리오더분 납기 협의 중',
         tissue='태풍으로 항만 하역이 지연되어(수&middot;목) 재킷 M 사이즈 입고가 1~2일 늦어질 전망. 리오더 협의는 MD와 진행 (2026-39-02).'),
]
TRADE_TW = [
    dict(trate='FW 발주 대비 입고율 64% (누계)', tplan='니트 가디건 1차 입고 (9/4)', tissue='특이사항 없음'),
    dict(trate='70% (누계)', tplan='아우터 1차 입고 (9/11)', tissue='특이사항 없음'),
    dict(trate='77% (누계)', tplan='이너웨어 입고 (9/18)', tissue='통관 서류 보완 요청 1건 (처리 완료)'),
    dict(trate='82% (누계)', tplan='니트 가디건 2차 (10/2), 이너웨어 세트 추가분 (10/3)',
         tissue='MOMO 이벤트 대응 물량 일부가 입고 지연 (3~4일). 이벤트 기간 재고 부족 우려.'),
]
for _t, _u in zip(HK_T, TRADE_HK):
    _t.update(_u)
for _t, _u in zip(TW_T, TRADE_TW):
    _t.update(_u)

import re
from en_dict import LABELS, DAYS, EN
from zh_text import ZH_TEXT
from zh_dict import DAYS_ZH, ZH_LABELS, ZH_STATIC, ZH_PREFIX, ZH_PATTERNS, WEATHER_ZH, STATUS_ZH

MISSING = set()
MISSING_ZH = set()


def L(k):
    en = LABELS.get(k)
    if en is None:
        MISSING.add(k)
        en = k
    zh = ZH_LABELS.get(k)
    if zh is None:
        MISSING_ZH.add(k)
        zh = en
    return f'<span class="ko">{k}</span><span class="en">{en}</span><span class="zh">{zh}</span>'


def BI(s):
    if not re.search(r'[가-힣]', s):
        return s

    def rep(m):
        pre, txt = m.group(1), m.group(2)
        st = txt.strip()
        if not re.search(r'[가-힣]', st):
            return m.group(0)
        en = EN.get(st)
        if en is None:
            MISSING.add(st)
            en = st
        return pre + txt.replace(st, en)

    en_html = re.sub(r'(^|>)([^<>]+)(?=<|$)', rep, s)

    def rep_zh(m):
        pre, txt = m.group(1), m.group(2)
        st = txt.strip()
        if not re.search(r'[가-힣]', st):
            return m.group(0)
        zh = ZH_TEXT.get(st)
        if zh is None:
            MISSING_ZH.add(st)
            zh = EN.get(st, st)
        return pre + txt.replace(st, zh)

    zh_html = re.sub(r'(^|>)([^<>]+)(?=<|$)', rep_zh, s)
    return f'<div class="ko">{s}</div><div class="en">{en_html}</div><div class="zh">{zh_html}</div>'


CSS2 = """
body[data-lang="ko"] .en,body[data-lang="ko"] .zh{display:none}
body[data-lang="en"] .ko,body[data-lang="en"] .zh{display:none}
body[data-lang="zh"] .ko,body[data-lang="zh"] .en{display:none}
.tp span::before{content:attr(data-ko);display:block;color:#6b7280}
.tp .bw{height:34px;display:flex;align-items:flex-end;justify-content:center;margin:2px 0 1px}
.tp .bw i{display:block;width:62%;max-width:22px;min-height:0;border-radius:3px 3px 0 0}
.tp .bw i.bh{background:#f59e0b}.tp .bw i.bl{background:#60a5fa}.tp .bw i.br{background:#1d4ed8}
tr.wx td.lb{vertical-align:bottom!important}
.xl tr.wx td.lb{background:#e5e7eb;font-weight:600}
.xl tr.wx td.tx{background:#f3f4f6}
tr.wx:not(.dayrow) .tp span::before{display:none}
tr.dayrow td{padding-bottom:0}
tr.dayrow .tp span::before{margin:0}
tr.dayrow .tp .dn{display:block;font-style:normal;font-size:11px;font-weight:400;color:#6b7280;margin-top:1px}
.tp .wi{display:block;font-style:normal;font-size:24px;line-height:34px;margin:2px 0 1px;font-family:"Segoe UI Emoji","Apple Color Emoji","Noto Color Emoji",sans-serif}
.tp .wl{font-size:10.5px;color:#6b7280;font-weight:400}
.tp .bw.ln{position:relative;align-items:stretch}
.tp .bw.ln svg{position:absolute;left:0;top:0;width:100%;height:100%;overflow:visible}
.tp .bw.ln path{fill:none;stroke-width:1.6;stroke-dasharray:3 3;stroke-linecap:round}
.tp .bw.ln path.lh{stroke:#f59e0b}.tp .bw.ln path.ll{stroke:#3b82f6}
.tp .bw.ln .dot{position:absolute;left:calc(50% - 3px);width:6px;height:6px;border-radius:50%}
.tp .bw.ln .dot.lh{background:#f59e0b}.tp .bw.ln .dot.ll{background:#3b82f6}
body[data-lang="en"] .tp span::before{content:attr(data-en)}
body[data-lang="zh"] .tp span::before{content:attr(data-zh)}
.ctrl{display:flex;align-items:center;flex-wrap:wrap;gap:14px}
body{background:#fff}
.head{padding:18px 20px 10px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
.head h1{margin:0;font-size:24px;font-weight:700}
.tabs{display:flex;gap:6px;flex-wrap:wrap}
.tabs button{font:inherit;font-size:12px;padding:4px 12px;border:1px solid #d1d5db;background:#fff;color:#4b5563;border-radius:14px;cursor:pointer}
.tabs button.on{background:#111;color:#fff;border-color:#111}
.scroll{border:none;padding:0 0 8px}
.blk{margin:0 0 56px}
caption{caption-side:top;text-align:left;padding:0 0 10px}
caption h2{position:sticky;left:20px;display:inline-block;font-size:18px;font-weight:700;margin:0;padding:0}
caption h2 small{font-weight:400;color:#6b7280;font-size:12px;margin-left:8px}
.up,.dn{color:inherit}
.xl td.lb.good,.xl td.lb.bad{color:#111}
.xl tr td.ach{background:#e6edf7}
.xl tr td.gr{background:#f1ede2}
.xl th.sw.ach,.xl th.sy.ach{background:#d6e1f2}
.xl th.sw.gr,.xl th.sy.gr{background:#e6dfcb}
.xl td.dp{background:#374151;padding:3px;height:22px}
.xl th.wk.cur{background:#111}
.sum{max-width:1000px;margin:8px 20px 48px;border:1px solid #cfd4dc;border-radius:6px;overflow:hidden}
.sum-h{background:#111;color:#fff;padding:11px 26px;font-size:16px;font-weight:700;letter-spacing:.6px}
.sum-h small{font-weight:400;color:#d1d5db;margin-left:12px;font-size:12px;letter-spacing:0}
.sum-body{padding:6px 28px 6px;font-size:15px;line-height:1.95;color:#111}
.sum-body h3{font-size:13px;font-weight:700;color:#6b7280;margin:20px 0 4px;letter-spacing:.4px}
.sum-body p{margin:0}
.sum-body ul{margin:0;padding-left:20px}.sum-body li{margin:0 0 5px}
mark.k{background:#fef08a;color:inherit;padding:0 3px;border-radius:3px;font-weight:700}
.sum-note{padding:6px 28px 14px;font-size:11px;color:#9ca3af}
.ntc{margin:0 20px 16px;display:inline-block;font-size:12px;color:#4b5563;background:#f3f4f6;border:1px solid #d1d5db;border-radius:14px;padding:3px 14px}
.smp{font-size:11px;font-weight:600;color:#6b7280;background:#f3f4f6;border:1px solid #d1d5db;border-radius:9px;padding:0 8px;margin-left:8px;letter-spacing:0}
.smp.real{color:#111;background:#fff;border-color:#111}
.tabs a{font:inherit;font-size:12px;padding:4px 14px;border:1px solid #d1d5db;background:#fff;color:#4b5563;border-radius:14px;text-decoration:none}
.tabs a.on{background:#111;color:#fff;border-color:#111}
.sumpage .sum{margin:14px auto 22px}
.sumpage .sum-body{font-size:16px}
.gol{max-width:1000px;margin:0 auto 56px;text-align:right}
.gol a{font-size:14px;color:#111;font-weight:600;text-decoration:none;border-bottom:2px solid #111;padding-bottom:2px}
.fxbox{display:flex;align-items:center;gap:6px;font-size:12px;color:#4b5563}
.fxbox input{width:72px;font:inherit;font-size:12px;padding:3px 6px;border:1px solid #d1d5db;border-radius:6px;text-align:right}
.fxbox button{font:inherit;font-size:11px;padding:2px 9px;border:1px solid #d1d5db;background:#fff;border-radius:10px;color:#4b5563;cursor:pointer}
.fxbox.dim{opacity:.45}
#acts button.on{background:#111;color:#fff;border-color:#111}
.st{font-size:11px;color:#6b7280;align-self:center}
.editing{outline:2px solid #facc15;background:#fffbe6;border-radius:4px;min-height:1.4em;cursor:text}
.editing:focus{outline-color:#eab308}
.editing.conflict{outline-color:#dc2626;background:#fef2f2}
.wksel{font:inherit;font-size:12px;padding:4px 8px;border:1px solid #d1d5db;border-radius:14px;background:#fff;color:#4b5563;max-width:190px}
.stat.arch{background:#e5e7eb;color:#374151}.stat .cur-link{color:#1d4ed8;margin-left:8px;font-size:12px}
.arch #bEdit,.arch #bSave{display:none}
.tx div[data-auto="1"]::after{display:block;font-size:10px;color:#9ca3af;margin-top:3px}
body[data-lang="ko"] .tx div[data-auto="1"]::after{content:"자동 번역"}
body[data-lang="en"] .tx div[data-auto="1"]::after{content:"Auto-translated"}
body[data-lang="zh"] .tx div[data-auto="1"]::after{content:"機器翻譯"}
.stat{display:inline-flex;gap:6px;align-items:center;margin:4px 0 6px;padding:3px 12px;border-radius:12px;font-size:12px}
.stat.draft{background:#fef3c7;color:#92400e}.stat.final{background:#dcfce7;color:#166534}
.editing:empty::before{content:"입력하세요";color:#9ca3af}
body[data-lang="en"] .editing:empty::before{content:"Type here"}
td.tx{position:relative}
td[data-pres]::before{content:attr(data-pres);position:absolute;top:2px;right:4px;font-size:10px;line-height:1;padding:3px 7px;border-radius:9px;background:#1D4ED8;color:#fff;z-index:2;white-space:nowrap}
.st .who{font-weight:600;color:#111}
.st a{color:#6b7280;margin-left:6px}
#wjLogin{position:fixed;inset:0;background:rgba(17,17,17,.55);display:flex;align-items:center;justify-content:center;z-index:50;padding:16px}
#wjLogin[hidden]{display:none}
#wjLogin .box{background:#fff;border-radius:12px;padding:22px 24px;width:min(360px,100%);display:flex;flex-direction:column;gap:10px;box-shadow:0 10px 40px rgba(0,0,0,.25)}
#wjLogin h3{margin:0;font-size:17px}
#wjLogin p{margin:0;font-size:13px;color:#4b5563}
#wjLogin input{font:inherit;font-size:14px;padding:8px 10px;border:1px solid #d1d5db;border-radius:8px}
#wjLogin button{font:inherit;font-size:13px;padding:8px 12px;border:0;border-radius:8px;background:#111;color:#fff;cursor:pointer}
#wjLogin #wjStep2{display:flex;flex-direction:column;gap:8px}
#wjLogin #wjStep2[hidden]{display:none}
#wjLogin .msg{font-size:12px;color:#b45309;min-height:16px}
.sum2{max-width:1180px;margin:14px auto 22px;border:1px solid #cfd4dc;border-radius:6px;overflow:hidden;background:#fff}
.sec{padding:22px 28px 26px;border-top:1px solid #e5e7eb}
.sec h3{margin:0 0 12px;font-size:17px;font-weight:700;display:flex;align-items:center;gap:10px}
.sec h3 .no{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%;background:#111;color:#fff;font-size:13px}
.sec p{margin:0 0 8px;font-size:15px;line-height:1.95}
.kp{display:grid;grid-template-columns:96px repeat(5,minmax(0,1fr));gap:8px;align-items:stretch;margin:0 0 10px}
.kp .kl{font-size:12px;font-weight:700;color:#6b7280;align-self:center}
.tiles{margin-top:16px}
.tile{border:1px solid #e5e7eb;border-radius:8px;padding:8px 12px;background:#fafafa}
.tile small{display:block;font-size:11px;color:#6b7280}
.tile b{font-size:19px;font-weight:700}
.t2{width:100%;border-collapse:collapse;font-size:13px}
.t2 th,.t2 td{border:1px solid #e5e7eb;padding:6px 8px}
.t2 th{background:#f3f4f6;font-weight:600;font-size:12px;text-align:center;color:#374151}
.t2 td.n{text-align:right;font-variant-numeric:tabular-nums}
.t2 td.c{text-align:center;font-variant-numeric:tabular-nums}
.t2 td.lb{text-align:left;font-weight:600;background:#fafafa}
.t2 tr.sub td.lb{padding-left:22px;font-weight:500;background:#fff}
.t2 tr.off td{font-weight:700;background:#f3f4f6}
.t2 tr.tot td{font-weight:700;background:#f3f4f6;color:#111;border-top:2px solid #9ca3af}
.t2 tr td.ach{background:#e6edf7}
.t2 tr td.gr{background:#f1ede2}
.t2 tr.tot td.ach,.t2 tr.tot td.gr{color:#111}
.rk-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:10px}
.pn{border:1px solid #e5e7eb;border-radius:8px;overflow:hidden}
.pn h4{margin:0;padding:8px 12px;background:#f3f4f6;font-size:13px;font-weight:700}
.pn ol{list-style:none;margin:0;padding:4px 12px 8px}
.pn li{display:grid;grid-template-columns:20px 1fr auto;gap:2px 6px;padding:6px 0;border-bottom:1px dashed #e5e7eb;font-size:13px}
.pn li:last-child{border-bottom:none}
.pn .rk{color:#9ca3af;font-weight:700}
.pn .vl{font-weight:700}
.pn .sb{grid-column:2/4;font-size:11px;color:#6b7280}
.t3{width:100%;border-collapse:collapse;font-size:14px;line-height:1.75}
.t3 td{border:1px solid #e5e7eb;padding:8px 12px;vertical-align:top}
.t3 td.dp{width:150px;background:#fafafa;font-weight:600;white-space:nowrap}
.t3 td.dp small{display:block;color:#6b7280;font-weight:400;font-size:11px}
.t3 p{margin:0 0 4px;font-size:14px;line-height:1.7}
.dn-note{font-size:11px;color:#9ca3af;margin-top:8px}
.rsn{margin:2px 0 16px;padding:8px 14px;background:#fafafa;border:1px solid #e5e7eb;border-radius:6px;font-size:13px;color:#4b5563}
.rsn .rl{display:block;font-weight:700;font-size:12px;color:#374151;margin-bottom:2px}
.rsn p{margin:0 0 2px;font-size:13px;line-height:1.7}
.cmt{margin:0 0 16px}
.cg{padding:12px 0;border-top:1px dashed #e5e7eb}
.cg:first-child{border-top:none;padding-top:0}
.ct{align-self:start;font-size:12px;font-weight:700;background:#111;color:#fff;border-radius:12px;padding:2px 12px;text-align:center}
.cg p{margin:0 0 6px;font-size:15px;line-height:1.9}
.xl tr.st.cl td.lb{color:#6b7280;font-style:italic}
.sumpage .sum2{margin:14px auto 22px}
@media (max-width:900px){.rk-grid{grid-template-columns:1fr}.kp{grid-template-columns:1fr 1fr}.t2{font-size:11px}}
.tgl{cursor:pointer}
.car{display:inline-block;width:16px;opacity:.7;transition:transform .15s}
tr.closed .car{transform:rotate(-90deg)}
.xl tr.tgl:hover td.lb{filter:brightness(.95)}
.fold{margin-left:14px;font-weight:400}
.fold button{font:inherit;font-size:11px;padding:2px 10px;border:1px solid #d1d5db;background:#fff;border-radius:10px;color:#4b5563;cursor:pointer;margin-right:4px}
table.xl{width:100%;border-top:1px solid #cfd4dc;font-size:12px}
.xl th,.xl td{padding:5px 4px}
.xl th.hw{background:#eef0f3;color:#111;font-size:12px;font-weight:700}
.xl th.hy{background:#d9dde3;color:#111;font-size:12px;font-weight:700}
.xl th.sw{background:#f6f7f8;font-size:11px}
.xl th.sy{background:#eceff3;font-size:11px}
.xl th.wk{font-size:13px}
.xl .wstart{border-left:3px solid #6b7280}
.xl .ystart{border-left:2px solid #9ca3af}
.xl tr.st td.ytd:not(.ach):not(.gr){background:#f9fafb}
.xl tr.gap td{height:14px;padding:0;border:none;background:transparent}
.xl tr.gap td.lb{background:transparent;border:none}
.xl td.tx{padding:8px 10px}
.foot{padding:4px 20px 16px}
"""


for _name, _items in DEPTS:
    for _k, _it in enumerate(_items):
        if _it[0] == '경쟁사':
            _items[_k] = ('경쟁사 동향',) + tuple(_it[1:])
    _items.append(('향후전략', 'strat_' + _name, ''))
    DEFAULT['strat_' + _name] = '미입력'
_STRAT_HK = {'GM': ('4분기 초반 번들 기획전과 FW 재킷 리오더에 집중해 오프라인 트래픽 감소를 만회하고, 온라인은 쿠폰 구조를 확산합니다.', 'In early Q4 we focus on the bundle campaign and the FW jacket reorder to offset lower offline traffic, and spread the coupon structure across online.'), '상품기획': ('FW 경량 다운 재킷 리오더를 확정하고 M 사이즈를 우선 배정하며, 여름 잔여 상품은 아울렛으로 옮겨 소진합니다.', 'Confirm the FW lightweight down jacket reorder with size M prioritized, and move remaining summer items to outlets to clear them.'), '영업': ('경쟁 할인 종료 후 Harbour City 유입 회복을 위해 번들 기획전과 사은 이벤트를 연계합니다.', 'Link the bundle campaign with gift events to recover Harbour City inflow after the competitor discount ends.'), 'EC': ('HKTVmall 쿠폰 구조를 NatgeoHK 자사몰에 확대 적용하고, 메인 개편(10/1) 이후 상품 노출 위치를 점검합니다.', 'Extend the HKTVmall coupon structure to the NatgeoHK own store, and review product placement after the main page revamp (10/1).'), 'VMD': ('번들 기획전용 윈도우 세팅(10/5) 이후 FW 아우터 존을 경량 다운 재킷 중심으로 재편합니다.', 'After the window setup for the bundle campaign (10/5), reorganize the FW outerwear zone around the lightweight down jacket.'), '마케팅': ('번들 기획전 SNS 티저(10/2)와 인플루언서 협업 촬영(10/4)을 시작으로 4분기 캠페인으로 이어갑니다.', 'Start with the bundle campaign SNS teaser (10/2) and influencer collaboration shoot (10/4), then move into the Q4 campaign.'), '물류': ('재킷 M 사이즈 긴급 입고를 우선 진행하고, 4분기 입고 일정은 하역 지연을 반영해 재조정합니다.', 'Prioritize the urgent inbound of jacket size M and readjust the Q4 inbound schedule to reflect unloading delays.')}
_STRAT_TW = {'GM': ('백화점 유입이 회복될 때까지 온라인 프로모션으로 실적을 방어하고, 프로모션 예산 승인을 조속히 확정합니다.', 'Defend results with online promotions until department store inflow recovers, and get the promotion budget approval settled quickly.'), '상품기획': ('니트 가디건은 기온 하락 시점에 맞춰 판매 비중을 확대하고, 이너웨어 세트 추가분을 확보합니다.', 'Raise the sales share of the knit cardigan as temperatures drop, and secure the extra innerwear set volume.'), '영업': ('주말 사은 이벤트로 N-SKM TCH 재방문을 유도하고, 결원 인력 충원을 10월 초까지 완료합니다.', 'Encourage return visits to N-SKM TCH with the weekend gift event, and complete filling the staff vacancy by early October.'), 'EC': ('MOMO 더블 포인트 성과를 Shopee 이벤트(10/7)로 확산하고, MOMO 정산 주기 변경(10/1)에 대응합니다.', 'Spread the MOMO double-point results to the Shopee event (10/7), and prepare for the MOMO settlement cycle change (10/1).'), 'VMD': ('백화점 FW 니트 존을 확대하고 사은 이벤트 배너를 세팅합니다.', 'Expand the department store FW knit zone and set up the gift event banner.'), '마케팅': ('Shopee 이벤트 배너 준비와 4분기 신제품 촬영 컷 확보에 집중합니다.', 'Focus on preparing the Shopee event banner and securing Q4 new product shooting cuts.'), '물류': ('지연된 MOMO 이벤트 물량을 우선 입고하고, 니트 2차와 이너웨어 추가분 일정을 확정합니다.', 'Prioritize inbound of the delayed MOMO event stock, and confirm the schedule for the knit 2nd batch and extra innerwear.')}
for _n, (_ko, _en) in _STRAT_HK.items():
    HK_T[3]['strat_' + _n] = _ko
for _n, (_ko, _en) in _STRAT_TW.items():
    TW_T[3]['strat_' + _n] = _ko


def fmt(x):
    if x is None:
        return '&mdash;'
    return f'{x:,.0f}'


CUR_FX = 185.0


def _set_fx(ent):
    """법인별 고정 환율(HK/MC=185, TW=46). 화면을 만드는 모든 함수가 시작할 때 부른다 — 법인 루프에서 앞 법인 값이 남아 월간 SUMMARY(홍콩)의 현지통화가 4배 틀리던 문제 방지 (2026-10-07)."""
    global CUR_FX
    CUR_FX = 185.0 if ent == 'HK' else 46.0



def wcells(v, w, halves=(0, 1)):
    out = ''
    for half in halves:
        t, a, p = v[3 * half], v[3 * half + 1], v[3 * half + 2]
        ach = (a / t * 100) if t else None
        g = ((a / p - 1) * 100) if p else None
        items = [(fmt(t), 'n', '', t), (fmt(a), 'n', '', a),
                 ('&mdash;' if ach is None else f'{ach:.1f}%', 'c', 'ach', None),
                 (fmt(p), 'n', '', p), ('&mdash;' if g is None else f'{g:+.1f}%', 'c', 'gr', None)]
        for j, (txt, al, cl, raw) in enumerate(items):
            c = [al]
            if half:
                c.append('ytd')
            if cl:
                c.append(cl)
            if j == 0:
                c.append('ystart' if half else 'wstart')
            loc = f' data-loc="{raw * 1000 / CUR_FX:.4f}"' if raw is not None else ''
            out += f'<td data-w="{w}"{loc} class="{" ".join(c)}">{txt}</td>'
    return out


def sums(vs):
    return tuple(sum((v[i] or 0) for v in vs) for i in range(6))


def U(s):
    return f'<mark class="k">{s}</mark>'


SUMTXT = {
    'HK': dict(
        ko_key=f'<li>경쟁 B사의 전 채널 {U("20% 할인(9/24~9/30)")}으로 방문객이 이동해 {U("Harbour City가 부진")}했습니다. 담당자는 일시적으로 보고 있습니다.</li>'
               f'<li>{U("HKTVmall")}은 앱 푸시 쿠폰과 주말 타임딜로 주문이 몰려 호조였습니다. 다른 온라인 채널에도 적용을 테스트합니다.</li>'
               f'<li>신상품 {U("FW 경량 다운 재킷")}은 입고 2주 차에 M&middot;L 사이즈가 먼저 소진되어 {U("M 사이즈 결품")}이 발생했고, 태풍으로 인한 하역 지연으로 M 사이즈 입고가 1~2일 늦어질 전망입니다.</li>'
               f'<li>수&middot;목 태풍 경보로 오프라인 영업시간이 단축되었습니다.</li>',
        en_key=f'<li>Visitors moved to competitor B\'s {U("20% discount across all channels (9/24~9/30)")}, so {U("Harbour City was weak")}. The team sees it as temporary.</li>'
               f'<li>{U("HKTVmall")} was strong: orders surged with app push coupons and the weekend time deal. A similar setup will be tested on other online channels.</li>'
               f'<li>New product {U("FW lightweight down jacket")}: M&middot;L sizes sold out first in week 2 after arrival, causing {U("size M stock-out")}; the typhoon delayed port unloading, so size M inbound is expected 1~2 days late.</li>'
               f'<li>A typhoon warning on Wed&middot;Thu shortened offline store hours.</li>',
        ko_next=f'{U("10월 2주차 번들 기획전")} 준비를 진행합니다. (SNS 티저 10/2, 윈도우 세팅 10/5) 재킷 M 사이즈 긴급 배송은 {U("10/3")}까지 요청했습니다.',
        en_next=f'Preparing the {U("bundle campaign for week 2 of October")} (SNS teaser 10/2, window setup 10/5). Urgent shipment of jacket size M is requested by {U("10/3")}.',
        ko_ask=f'<li>{U("번들 프로모션 출고가 마진 한시 지원 승인")} &mdash; 기한 {U("10/8")} (Ask 2026-39-01)</li>'
               f'<li>{U("재킷 M 사이즈 긴급 물량 배정")} &mdash; 기한 {U("10/3")} (Ask 2026-39-02)</li>',
        en_ask=f'<li>{U("Approve temporary HQ ex-factory margin support for the bundle promotion")} &mdash; due {U("10/8")} (Ask 2026-39-01)</li>'
               f'<li>{U("Urgent volume allocation for jacket size M")} &mdash; due {U("10/3")} (Ask 2026-39-02)</li>'),
    'TW': dict(
        ko_key=f'<li>연휴 직후 {U("백화점 유입이 회복되지 않아")} 계획에 못 미쳤습니다. {U("N-SKM TCH")}는 비 오는 날이 이어져 방문객이 줄었습니다. (일시적)</li>'
               f'<li>{U("N-EC MOMO")}는 더블 포인트 이벤트로 검색 노출이 올라 호조였습니다. Shopee에도 같은 이벤트를 신청합니다. (10/7)</li>'
               f'<li>{U("MOMO 이벤트 대응 물량 일부의 입고가 3~4일 지연")}되어 이벤트 기간 재고 부족이 우려됩니다.</li>'
               f'<li>N-SKM TCH 판매 인력 1명이 결원이며 10월 초 충원 예정입니다.</li>',
        en_key=f'<li>Plan was missed as {U("department store inflow did not recover")} after the holiday. Rainy days cut visitors at {U("N-SKM TCH")}. (temporary)</li>'
               f'<li>{U("N-EC MOMO")} was strong as the double-point event raised search exposure. The same event is being applied for on Shopee. (10/7)</li>'
               f'<li>{U("Part of the stock for the MOMO event is 3~4 days late")}, raising the risk of stock shortage during the event.</li>'
               f'<li>N-SKM TCH has one sales staff vacancy; a hire is expected in early October.</li>',
        ko_next=f'{U("진열 개편과 사은 이벤트")}를 10/5까지 진행하고, 니트 가디건 2차(10/2)와 이너웨어 세트 추가분(10/3)이 입고됩니다.',
        en_next=f'{U("Display reorganization and the gift event")} run through 10/5; knit cardigan 2nd inbound (10/2) and extra innerwear sets (10/3) arrive.',
        ko_ask=f'<li>{U("프로모션 예산 한시 승인")} &mdash; 기한 {U("10/3")} (Ask 2026-38-02, {U("지연 중")})</li><li>참고: 4분기 신제품 현지 촬영 컷 지원</li>',
        en_ask=f'<li>{U("Approve temporary promotion budget")} &mdash; due {U("10/3")} (Ask 2026-38-02, {U("delayed")})</li><li>FYI: support for Q4 new product local shooting cuts</li>'),
}


import html as _html

SL = {
    '실적': 'Results', '유통별 실적': 'Results by Channel', '오프라인 실적 BEST / WORST': 'Offline Stores BEST / WORST',
    '상품 실적': 'Product Results', '금주 리뷰': 'This Week Review', '차주 전략': 'Next Week Strategy',
    '매장수': 'Stores', '전년 동기 대비': 'vs LY', '주간 매출': 'Weekly sales', '주간 목표': 'Weekly target',
    '주간 달성률': 'Weekly achv.', '전주 매출': 'Last week', '누계 매출': 'YTD sales', '누계 목표': 'YTD target',
    '누계 달성률': 'YTD achv.', '전년 매출': 'LY sales', '오프라인': 'Offline', '합계': 'Total',
    '달성률 상위 (주간)': 'Top achievement (weekly)', '달성률 하위 (주간)': 'Lowest achievement (weekly)',
    '전년 대비 증가 (누계)': 'Highest YoY growth (YTD)', '전년 대비 감소 (누계)': 'Largest YoY decline (YTD)',
    '전주 대비 증가': 'Largest WoW increase', '전주 대비 감소': 'Largest WoW decrease',
    'BEST 상품': 'BEST Products', 'WORST 상품': 'WORST Products', '신상품 반응 (26시즌)': 'New Product Response (26 season)',
    '구분': 'Category', '내용': 'Detail',
}
LABELS.update(SL)


def _zh_of(ko, en):
    z = ZH_STATIC.get(ko)
    if z is not None:
        return z
    for pre, fn in ZH_PREFIX:
        if ko.startswith(pre):
            return fn(ko)
    for pat, fn in ZH_PATTERNS:
        m = pat.fullmatch(ko)
        if m:
            return fn(m)
    MISSING_ZH.add(re.sub(r'<[^>]+>', '', ko)[:60])
    return en


def B(ko, en, zh=None):
    zh = _zh_of(ko, en) if zh is None else zh
    return f'<span class="ko">{ko}</span><span class="en">{en}</span><span class="zh">{zh}</span>'


def BP(ko, en, tag='p', zh=None):
    zh = _zh_of(ko, en) if zh is None else zh
    return f'<{tag} class="ko">{ko}</{tag}><{tag} class="en">{en}</{tag}><{tag} class="zh">{zh}</{tag}>'


def _amt(loc, en):
    v = loc * CUR_FX / 1000
    txt = f'KRW {fmt(v)}M' if en is True else (f'{fmt(v)}百萬韓元' if en == 'zh' else f'{fmt(v)}백만원')
    return f'<span class="amt" data-loc="{loc:.4f}">{txt}</span>'


def AK(krw, en):
    return _amt(krw * 1000 / CUR_FX, en)


_HL = re.compile(r'(\d{1,2}/\d{1,2}(?:~\d{1,2}/\d{1,2})?|\d+(?:\.\d+)?%|\d{4}-\d{2}-\d{2})')


def HL(s):
    def rep(m):
        return m.group(1) + _HL.sub(lambda x: U(x.group(1)), m.group(2))
    return re.sub(r'(^|>)([^<>]+)(?=<|$)', rep, s)


def _nc(krw, cls='n'):
    if krw is None:
        return f'<td class="{cls}">&mdash;</td>'
    return f'<td class="{cls}" data-loc="{krw * 1000 / CUR_FX:.4f}">{fmt(krw)}</td>'


def _pc(x, cls, signed=False):
    if x is None:
        return f'<td class="c {cls}">&mdash;</td>'
    return f'<td class="c {cls}">' + (f'{x:+.1f}%' if signed else f'{x:.1f}%') + '</td>'


def _row(label, v, cur, ly, cls, wly):
    t, a, lw, yt, ya, yly = v
    ach = a / t * 100 if t else None
    wow = (a / wly - 1) * 100 if wly else None
    yach = ya / yt * 100 if yt else None
    yoy = (ya / yly - 1) * 100 if yly else None
    if cur is None:
        cnt = '<td class="c">&mdash;</td><td class="c">&mdash;</td>'
    else:
        d = cur - ly
        cnt = f'<td class="c">{cur}</td><td class="c">{"0" if d == 0 else f"{d:+d}"}</td>'
    return (f'<tr class="{cls}"><td class="lb">{label}</td>{cnt}{_nc(t)}{_nc(a)}{_pc(ach, "ach")}{_nc(wly)}{_pc(wow, "gr", True)}'
            f'{_nc(yt)}{_nc(ya)}{_pc(yach, "ach")}{_nc(yly)}{_pc(yoy, "gr", True)}</tr>')


def _rank(items, kind):
    out = ''
    for k, (n, v) in enumerate(items, 1):
        t, a, lw, yt, ya, yly = v
        if kind == 'ach':
            val = f'{a / t * 100:.1f}%'
        elif kind == 'yoy':
            val = f'{(ya / yly - 1) * 100:+.1f}%'
        else:
            val = f'{(a / lw - 1) * 100:+.1f}%'
        def nn(x):
            return f'<span data-loc="{x * 1000 / CUR_FX:.4f}">{fmt(x)}</span>'
        if kind == 'ach':
            sub = f'{B("목표", "Target")} {nn(t)} &middot; {B("매출", "Sales")} {nn(a)}'
        elif kind == 'wow':
            sub = f'{B("전주", "Last week")} {nn(lw)} &middot; {B("이번 주", "This week")} {nn(a)}'
        else:
            sub = f'{B("전년", "LY")} {nn(yly)} &middot; {B("올해", "This year")} {nn(ya)}'
        out += (f'<li class="{"more" if k > 3 else ""}"><span class="rk">{k}</span><span class="nm">{_html.escape(n)}</span><b class="vl">{val}</b>'
                f'<span class="sb">{sub}</span></li>')
    return out or f'<li><span class="sb" style="grid-column:1/-1">{B("해당 없음", "N/A")}</span></li>'


def _more_btn(n_items):
    if n_items <= 3:
        return ''
    k = n_items - 3
    return (f'<button type="button" class="pmore"><span class="m1">{B(f"더 보기 (+{k}개)", f"Show more (+{k})", f"展開更多（+{k}）")}</span>'
            f'<span class="m2">{B("접기", "Show less", "收合")}</span></button>')


def _panel(title, items, kind):
    return f'<div class="pn"><h4>{title}</h4><ol>{_rank(items, kind)}</ol>{_more_btn(len(items))}</div>'


def _prod(rows):
    out = ''
    for k, r in enumerate(rows, 1):
        rate = '&mdash;' if r['rate'] is None else f'{r["rate"]:.1f}%'
        ko = f'판매율 {rate} &middot; 재고 {r["stock"]:,}'
        en = f'Sell-through {rate} &middot; Stock {r["stock"]:,}'
        out += (f'<li><span class="rk">{k}</span><span class="nm">{_html.escape(r["name"])}</span>'
                f'<b class="vl">{B(f"{r[chr(119)+chr(107)]}개", f"{r[chr(119)+chr(107)]} pcs")}</b>'
                f'<span class="sb">{B(ko, en)}</span></li>')
    return out or f'<li><span class="sb" style="grid-column:1/-1">{B("해당 없음", "N/A")}</span></li>'


# SUMMARY 5. 경쟁사 동향 맨 첫 줄 서술형 — 샘플 문구 (2026-10-02). 아래 표(영업·상품기획·EC·VMD·마케팅)의 샘플 내용을 한 문단으로 풀어 쓴 것이라
# 담당자 입력이 바뀌면 이 문단도 함께 갱신해야 한다. 숫자·날짜 노랑 하이라이트는 HL() 이 자동으로 건다.
COMP_LEAD = {
    'HK': ('경쟁 B사는 9/24~9/30 전 채널 20% 할인을 진행했고, 온라인몰에서는 최대 20% 쿠폰을 배포했습니다. 상품 측면에서는 B사가 FW 경량 다운 라인을 당사보다 낮은 가격으로 출시했으며 블랙·카키 중심으로 구성했습니다. '
           'Harbour City 매장에서는 할인 배너를 전면에 배치하고 입구 가판 행거를 운영했고, 인스타그램 할인 광고와 인플루언서 착용 컷도 노출했습니다.',
           'Competitor B ran 20% off across all channels (9/24~9/30) and handed out coupons of up to 20% on its online mall. On product, B launched an FW lightweight down line priced below ours, in a black and khaki palette. '
           'At its Harbour City store, B put discount banners up front and ran a sidewalk rack at the entrance, and it also ran Instagram discount ads with influencer wear shots.',
           '競爭對手 B 品牌於 9/24~9/30 全通路推出 20% 折扣，線上商城發放最高 20% 優惠券。商品方面，B 品牌推出價格低於本公司的 FW 輕量羽絨系列，以黑色、卡其色為主。'
           '在 Harbour City 門市，B 品牌將折扣看板擺在最前方並於入口設置推車掛架，同時投放 Instagram 折扣廣告並露出網紅穿搭照。'),
    'TW': ('현지 브랜드들이 시즌오프를 시작해 문자 발송과 경쟁 플랫폼의 쿠폰 배포가 확인되었습니다. 현지 브랜드 C는 경량 아우터 신상을 백화점 팝업에서 선판매했고, 팝업에서는 시즌오프 배너와 가판 행거를 입구에 집중 배치했습니다. '
           'SNS에서는 시즌오프 광고를 집행했습니다.',
           'Local brands have started their season-off sales: text messages and competing platforms\' season-off coupons were observed. Local brand C pre-sold new lightweight outerwear at a department-store pop-up, '
           'where season-off banners and a sidewalk rack were concentrated at the entrance. Season-off ads were also running on social media.',
           '當地品牌已開始季末特賣，確認有簡訊發送及競爭平台發放季末特賣優惠券。當地品牌 C 於百貨快閃店預售輕量外套新品，快閃店入口集中擺放季末特賣看板與推車掛架。'
           '社群媒體上亦投放季末特賣廣告。'),
}

def _lead_html(cl):
    """(ko, en, zh) 서술형 → 문장마다 단락을 나눈 3개 국어 HTML (ko: '…다. ', en: '. 대문자', zh: '。'). 세 언어의 문장 수가 같아야 줄이 맞는다."""
    if not cl:
        return ''
    sp = [re.split(r'(?<=다\.)\s+', cl[0]), re.split(r'(?<=\.)\s+(?=[A-Z])', cl[1]), [x for x in re.split(r'(?<=。)', cl[2]) if x]]
    sp = [[y.strip() for x in lst for y in x.split('¦')] for lst in sp]     # 한 줄을 넘는 문장만 표시 자리에서 한 번 더 나눈다
    n = min(len(x) for x in sp)
    return '<div class="comp-lead">' + ''.join(BP(HL(sp[0][i]), HL(sp[1][i]), zh=HL(sp[2][i])) for i in range(n)) + '</div>'


# SUMMARY 6. 금주 리뷰 맨 첫 줄 서술형 — 샘플 문구 (2026-10-02). 아래 표(GM 총평·특이사항, 영업 부진 채널, 상품기획·EC 부진 상품, 물류 입고율·문제사항)의 샘플을 풀어 쓴 것.
REVIEW_LEAD = {
    'HK': ('경쟁 B사의 할인 여파로 Harbour City 트래픽이 빠졌지만 HKTVmall이 받쳐 전체는 계획에 소폭 미달했습니다. 수·목 태풍 경보로 오프라인 영업시간이 단축되었고,¦ Harbour City 입구 보수 공사로 동선 일부가 변경되어(10/6까지) 방문객 유입에 영향이 있을 수 있습니다. '
           '여름 잔여 티셔츠는 시즌 종료로 신규 수요가 거의 없고, FW 경량 다운 재킷은 M 사이즈가 조기 소진되어 판매 기회를 놓쳤습니다. 입고율은 누계 85%이며, 태풍으로 항만 하역이 지연되어 재킷 M 사이즈 입고가 1~2일 늦어질 전망입니다.',
           'Harbour City traffic dropped after competitor B’s discounts, but HKTVmall held up, leaving the total slightly below plan. Typhoon warnings on Wednesday and Thursday shortened offline store hours,¦ and entrance repairs at Harbour City partly changed foot-traffic routes (until 10/6), which may affect visitor inflow. '
           'Leftover summer T-shirts have almost no new demand as the season ends, and the FW lightweight down jacket lost sales opportunities when size M sold out early. The inbound rate is 85% cumulative, and port unloading delays from the typhoon are expected to push jacket size M arrivals back by 1~2 days.',
           '受競爭對手 B 品牌折扣影響，Harbour City 客流下滑，但 HKTVmall 撐住整體，業績略低於計畫。週三、週四颱風警報使線下營業時間縮短，¦且 Harbour City 入口維修導致部分動線變更（至 10/6），可能影響來客數。'
           '夏季剩餘 T 恤因季節結束幾乎沒有新需求，FW 輕量羽絨外套 M 尺寸提早售罄而錯失銷售機會。到貨率累計 85%，颱風造成港口卸貨延遲，外套 M 尺寸預計延後 1~2 天到貨。'),
    'TW': ('연휴 직후 백화점 유입이 회복되지 않아 계획에 미달했고, 온라인은 프로모션 효과로 전년을 웃돌았습니다. 주중 비가 이어져 백화점 방문객이 전반적으로 줄었고, 그 영향으로 주력 재킷 판매도 함께 감소했습니다. '
           'N-SKM TCH는 판매 인력 1명이 결원이며(10월 초 합류 예정) 온라인 여름 잔여 상품은 시즌 종료로 진열이 축소되었습니다. 입고율은 누계 82%이며, MOMO 이벤트 대응 물량 일부가 3~4일 늦게 입고되어 이벤트 기간 재고 부족이 우려됩니다.',
           'Department-store traffic had not recovered right after the holiday, so sales fell short of plan, while online beat last year on promotions. Rain continued through the week, reducing department-store visitors overall and pulling down sales of the core jackets as well. '
           'N-SKM TCH is one sales staff short (a replacement is expected to join in early October), and leftover summer items online had their display reduced as the season ended. The inbound rate is 82% cumulative, and part of the volume for the MOMO event arrived 3~4 days late, raising a risk of stock shortage during the event.',
           '連假後百貨客流尚未恢復，業績未達計畫，線上則因促銷效果超越去年。週間持續下雨，百貨來客整體減少，主力外套銷售也隨之下滑。'
           'N-SKM TCH 銷售人力短缺 1 名（10 月初到職），線上夏季剩餘商品因季節結束縮減陳列。到貨率累計 82%，MOMO 活動備貨有一部分延遲 3~4 天到貨，活動期間有缺貨疑慮。'),
}


# SUMMARY 7. 차주 전략 맨 첫 줄 서술형 — 샘플 문구 (2026-10-02). 아래 표(부서별 향후전략 + GM HQ 요청사항)의 샘플을 풀어 쓴 것.
STRAT_LEAD = {
    'HK': ('4분기 초반에는 번들 기획전과 FW 재킷 리오더에 집중해 오프라인 트래픽 감소를 만회하고, 온라인은 쿠폰 구조를 확산합니다. '
           '상품은 FW 경량 다운 재킷 리오더를 확정해 M 사이즈를 우선 배정하고, 긴급 입고를 먼저 진행하며 4분기 입고 일정은 하역 지연을 반영해 재조정합니다. '
           '영업은 경쟁 할인 종료 후 Harbour City 유입 회복을 위해 번들 기획전과 사은 이벤트를 연계하고,¦ HKTVmall 쿠폰 구조는 NatgeoHK 자사몰에 확대 적용합니다. '
           '번들 기획전용 윈도우를 10/5에 세팅한 뒤 FW 아우터 존을 경량 다운 재킷 중심으로 재편하고,¦ SNS 티저(10/2)와 인플루언서 협업 촬영(10/4)으로 4분기 캠페인을 시작합니다. '
           '본사에는 번들 프로모션용 출고가 마진 한시 지원 승인(기한 10/8)과 재킷 M 사이즈 긴급 물량 배정(기한 10/3)을 요청합니다.',
           'In early Q4 we will focus on the bundle promotion and the FW jacket reorder to recover the offline traffic decline, and spread the coupon structure online. '
           'On product, we will confirm the FW lightweight down jacket reorder with priority allocation to size M, push the urgent inbound first, and reschedule Q4 inbound to reflect the unloading delay. '
           'Sales will link the bundle promotion with gift events to win back Harbour City traffic once the competitor discount ends,¦ and extend the HKTVmall coupon structure to the NatgeoHK own mall. '
           'After setting up the bundle-promotion windows on 10/5, VMD will rework the FW outerwear zone around lightweight down jackets,¦ and marketing will start the Q4 campaign with an SNS teaser (10/2) and an influencer shoot (10/4). '
           'We ask HQ to approve a temporary supply-price margin support for the bundle promotion (due 10/8) and to allocate urgent size M jacket volume (due 10/3).',
           '第四季初將集中推出組合企劃檔期與 FW 外套追加，彌補線下客流減少，線上則擴大優惠券結構。'
           '商品方面，確定 FW 輕量羽絨外套追加並優先配給 M 尺寸，先行緊急到貨，第四季到貨日程依卸貨延遲重新調整。'
           '營業在競爭折扣結束後，以組合企劃檔期搭配贈品活動恢復 Harbour City 客流，¦並將 HKTVmall 優惠券結構擴大套用至 NatgeoHK 自家商城。'
           '組合企劃專用櫥窗於 10/5 佈置完成後，將 FW 外套區改以輕量羽絨外套為主，¦並以社群預告（10/2）與網紅合作拍攝（10/4）啟動第四季活動。'
           '請總部核准組合促銷出貨價毛利暫時支援（期限 10/8），並配給外套 M 尺寸緊急貨量（期限 10/3）。'),
    'TW': ('백화점 유입이 회복될 때까지 온라인 프로모션으로 실적을 방어하고, 프로모션 예산 승인을 조속히 확정합니다. '
           '상품은 니트 가디건을 기온 하락 시점에 맞춰 판매 비중을 확대하고 이너웨어 세트 추가분을 확보하며,¦ 지연된 MOMO 이벤트 물량을 우선 입고하고 니트 2차와 이너웨어 추가분 일정을 확정합니다. '
           '영업은 주말 사은 이벤트로 N-SKM TCH 재방문을 유도하고 결원 인력 충원을 10월 초까지 완료하며,¦ 온라인은 MOMO 더블 포인트 성과를 Shopee 이벤트(10/7)로 확산하고 MOMO 정산 주기 변경(10/1)에 대응합니다. '
           '백화점 FW 니트 존을 확대하고 사은 이벤트 배너를 세팅하며, Shopee 이벤트 배너 준비와 4분기 신제품 촬영 컷 확보에 집중합니다. '
           '본사에는 프로모션 예산 한시 승인(기한 10/3)을 요청합니다.',
           'Until department-store traffic recovers we will defend results with online promotions and finalize the promotion budget approval quickly. '
           'On product, we will raise the sales share of knit cardigans as temperatures fall and secure additional innerwear sets,¦ receive the delayed MOMO event volume first, and fix the schedule for the second knit run and the extra innerwear. '
           'Sales will use weekend gift events to bring customers back to N-SKM TCH and fill the vacant position by early October,¦ while online spreads the MOMO double-point results to the Shopee event (10/7) and responds to the MOMO settlement cycle change (10/1). '
           'VMD will expand the department-store FW knit zone and set up gift-event banners, and marketing will focus on preparing Shopee event banners and securing Q4 new-product shoot cuts. '
           'We ask HQ for a temporary approval of the promotion budget (due 10/3).',
           '在百貨客流恢復前，以線上促銷守住業績，並儘速確定促銷預算核准。'
           '商品方面，配合氣溫下降提高針織開襟衫銷售占比並確保內衣組合追加量，¦優先收貨延遲的 MOMO 活動貨量，並確定針織第二批與內衣追加量日程。'
           '營業以週末贈品活動引導顧客回訪 N-SKM TCH，並於 10 月初完成人力補實；¦線上則將 MOMO 雙倍點數成果擴大至 Shopee 活動（10/7），並因應 MOMO 結算週期變更（10/1）。'
           '擴大百貨 FW 針織區並佈置贈品活動看板，行銷集中準備 Shopee 活動看板與確保第四季新品拍攝素材。'
           '請總部暫時核准促銷預算（期限 10/3）。'),
}

EXTRAS = {}
EXTRAS_B = {}      # (법인, 'NG'|'MG') → 브랜드별 상품·매장 부가 자료
WLYD = {}


# SUMMARY 5~7 채우기 (2026-10-07 오웬 지시): 담당자가 상세 일지(주간 W.. / 월간 M..)에 저장한 글을 화면이 열릴 때 읽어 같은 줄에 넣는다.
# 줄마다 data-sd(부서 코드)·data-sk(항목 코드)가 일지 칸 주소(법인|주차|부서|항목|언어)와 같다. 저장된 글이 없는 줄은 만들어 둔 문구를 그대로 둔다.
SUMFILL_JS = """(function(){
var box=document.getElementById('sumfill');if(!box)return;
var ENT=box.getAttribute('data-ent'),WEEK=box.getAttribute('data-week'),API='__API__';
if(!API)return;
var tk='';try{tk=localStorage.getItem('wj_tok_HK')||localStorage.getItem('wj_tok_TW')||'';}catch(e){}
if(!tk)return;
function clean(html){var d=new DOMParser().parseFromString('<body>'+html+'</body>','text/html');
  d.body.querySelectorAll('script,style,iframe,object,embed,link,meta,form').forEach(function(e){e.remove();});
  d.body.querySelectorAll('*').forEach(function(e){[].slice.call(e.attributes).forEach(function(a){if(/^on/i.test(a.name)||/^\\s*javascript:/i.test(a.value))e.removeAttribute(a.name);});});
  return d.body.innerHTML;}
function txt(h){return String(h||'').replace(/<[^>]*>|&nbsp;/g,'').trim();}
fetch(API,{method:'POST',headers:{'Content-Type':'text/plain;charset=utf-8'},body:JSON.stringify({a:'pull',ent:ENT,week:WEEK,photos:true,token:tk})})
.then(function(r){return r.json();}).then(function(r){
  if(!r.ok)return;if(window.wjRole&&r.me)window.wjRole(r.me.role);var cells=r.cells||{};
  function g(code,ik,L){var c=cells[[ENT,WEEK,code,ik,L].join('|')];return c&&txt(c.html)?c.html:'';}
  document.querySelectorAll('tr[data-sd]').forEach(function(tr){
    var code=tr.getAttribute('data-sd'),ik=tr.getAttribute('data-sk'),td=tr.querySelector('td.sv');if(!td)return;
    var by={ko:g(code,ik,'ko'),en:g(code,ik,'en'),zh:g(code,ik,'zh')},any=by.ko||by.en||by.zh,h='';
    var ph=tr.getAttribute('data-sph');
    if(ph){for(var n=1;n<=4;n++){var c=cells[[ENT,WEEK,code,ph+'_p'+n,'ko'].join('|')];if(c&&c.html&&c.html.indexOf('<img')===0)h+='<span class="sph">'+clean(c.html)+'</span>';}}
    if(!any&&!h)return;
    var tx='';
    if(any){['ko','en','zh'].forEach(function(L){tx+='<div class="'+L+'">'+clean(by[L]||any)+'</div>';});}
    td.innerHTML=tx+(h?'<div class="sphs">'+h+'</div>':'');
  });
}).catch(function(){});
/* 사진을 누르면 크게 보기 (바깥을 누르거나 Esc 로 닫기) */
var zb=document.createElement('div');zb.id='sphZoom';zb.hidden=true;zb.innerHTML='<img alt="">';document.body.appendChild(zb);
function zclose(){zb.hidden=true;}
zb.addEventListener('click',zclose);
document.addEventListener('keydown',function(e){if(e.key==='Escape')zclose();});
document.addEventListener('click',function(e){var im=e.target&&e.target.closest?e.target.closest('.sphs .sph img'):null;if(!im)return;zb.firstChild.src=im.src;zb.hidden=false;});
})();"""
SUMFILL_CSS = ('.sphs{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}.sphs .sph img{display:block;max-width:150px;max-height:150px;border-radius:4px;cursor:zoom-in}'
               '#sphZoom{position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.78);display:flex;align-items:center;justify-content:center;padding:16px;cursor:zoom-out}'
               '#sphZoom[hidden]{display:none}#sphZoom img{max-width:94vw;max-height:92vh;object-fit:contain;border-radius:6px;background:#fff}')


def _sum_tail(head, val, ent, week, live, leads, titles=None):
    """SUMMARY 5~7 (경쟁사 동향 / 리뷰 / 전략) 표. 줄마다 일지 칸 주소를 달아 두면 화면이 열릴 때 SUMFILL_JS 가 저장된 글을 넣는다."""
    def row(dept, label, key):
        code = DEPT_CODE.get(dept, dept)
        ik = 'strat' if key.startswith('strat_') else key
        ph = ' data-sph="vcomp"' if key == 'vcomp' else ''
        return f'<tr data-sd="{code}" data-sk="{ik}"{ph}><td class="dp">{L(dept)}<small>{L(label)}</small></td><td class="sv">{val(key)}</td></tr>'
    t5, t6, t7 = titles or (('경쟁사 동향', 'Competitor Trends'), ('금주 리뷰', 'This Week Review'), ('차주 전략', 'Next Week Strategy'))
    badge = 'real' if live else 'smp'
    l5, l6, l7 = ('', '', '') if live else leads
    box = (f'<div id="sumfill" data-ent="{ent}" data-week="{week}" hidden></div>'
           f'<style>{SUMFILL_CSS}</style>')
    sec5 = (f'<div class="sec">{box}{head(5, t5[0], t5[1], badge)}{l5}<table class="t3">'
            + row('영업', '경쟁사 동향', 'comp') + row('상품기획', '경쟁사 상품현황', 'pcomp') + row('EC', '경쟁사 동향', 'eccomp')
            + row('VMD', '경쟁사 VMD', 'vcomp') + row('마케팅', '경쟁사 마케팅', 'mcomp') + '</table></div>')
    sec6 = (f'<div class="sec">{head(6, t6[0], t6[1], badge)}{l6}<table class="t3">'
            + row('GM', '총평', 'head') + row('GM', '특이사항', 'special') + row('영업', '부진 채널 (사유)', 'bch')
            + row('영업', '특이사항', 'sspecial') + row('상품기획', '부진 상품 (사유)', 'bad') + row('EC', '부진 상품 (사유)', 'ecbad')
            + row('물류', '문제사항', 'tissue') + row('HR', '인력 현황', 'hr1') + row('HR', '채용·이동', 'hr2')
            + row('회계/재무', '재무 현황', 'fi1') + row('회계/재무', '채권·이슈', 'fi2') + '</table></div>')    # 물류 입고율은 SUMMARY 에서 뺌 (오웬 2026-10-07, 상세 일지에는 그대로)
    strat = ''.join(row(d, '향후전략', 'strat_' + d) for d, _items in DEPTS)
    sec7 = (f'<div class="sec">{head(7, t7[0], t7[1], badge)}{l7}<table class="t3">'
            + strat + row('GM', 'HQ 요청사항', 'ask') + '</table>'
            + '<script>' + SUMFILL_JS.replace('__API__', CFG.get('api_url') or '') + '</script></div>')
    return sec5, sec6, sec7


def make_summary(ent, data, groups, weeks_meta, tx, brand='ALL', part='all'):
    _set_fx(ent)
    import real_data as _rdw
    w = data[-1]
    # build() 가 3번째 칸을 '전년 동주'로 바꿔 두므로, 전주 대비는 직전 주 데이터의 주간 매출(2번째 칸)로 따로 만든다
    if len(data) > 1:
        _pw = data[-2]
        w = _rdw.wk_like(w, {k: (v[0], v[1], (_pw[k][1] if k in _pw else None), v[3], v[4], v[5]) for k, v in w.items()})
    lab = weeks_meta[-1]['label']
    mm = re.match(r'(\d+/\d+)~(\d+/\d+) \(W(\d+)\)', lab)
    d0, d1 = mm.group(1), mm.group(2)
    ex = EXTRAS_B.get((ent, brand)) or EXTRAS.get(ent, {})
    gsum = {g: sums([w[r[0]] for r in rows]) for g, rows in groups if g != '기타'}
    other = w['기타']
    tot = sums(list(w.values()))
    import real_data as _rd1
    _wk1 = int(mm.group(3))
    _wls1 = _rd1.WLY_STORE.get(ent, {}).get(_wk1, {})
    wl = {g: sum((_wls1.get(r[0]) or 0.0) for r in rows) for g, rows in groups if g != '기타'}
    wl['기타'] = ((_wls1.get('기타') or 0.0) if brand == 'ALL' else (_rd1.WLY_OTHER.get(ent, {}).get(_wk1, {}).get(brand) or 0.0))
    g_wly = {g: wl.get(g, 0.0) for g in ('백화점', '아울렛', '팝업', '온라인', '기타')}
    tot_wly = sum(wl.values())
    off_g = [g for g in ('백화점', '아울렛', '팝업') if g in gsum]
    off = tuple(sum(gsum[g][i] for g in off_g) for i in range(6))
    off_wly = sum(g_wly[g] for g in off_g)
    t, a, lw, yt, ya, yly = tot
    ach = a / t * 100 if t else 0.0
    wow = (a / lw - 1) * 100 if lw else 0.0
    wyoy = (a / tot_wly - 1) * 100 if tot_wly else 0.0
    yach = ya / yt * 100 if yt else 0.0
    yoy = (ya / yly - 1) * 100 if yly else 0.0
    real_b = B('실제 ERP 값', 'Real ERP values')
    smp_b = B('샘플 문구', 'Sample text')
    unit = ('<span class="unitcap"><span class="ko">단위 백만원(KRW)</span><span class="en">Unit: KRW million</span><span class="zh">單位：百萬韓元(KRW)</span></span>')

    def head(no, ko, en, badge):
        tag = '' if badge == 'real' else f'<span class="smp">{smp_b}</span>'
        return f'<h3><span class="no">{no}</span>{B(ko, en)}{tag}</h3>'

    # 1. 실적
    ko1 = (f'이번 주({d0}~{d1}) 매출은 {U(AK(a, False))}, 목표 {AK(t, False)} 대비 {U(f"{ach:.1f}%")} 달성했고, 전년 매출 {AK(tot_wly, False)} 대비 {U(f"{wyoy:+.1f}%")}이며 전주 대비 {U(f"{wow:+.1f}%")}입니다.',
           f'{d1} 기준 누계 매출은 {U(AK(ya, False))}, 목표 {AK(yt, False)} 대비 {U(f"{yach:.1f}%")} 달성했으며, 전년 매출 {AK(yly, False)} 대비 {U(f"{yoy:+.1f}%")}입니다.')
    en1 = (f'This week ({d0}~{d1}) sales were {U(AK(a, True))}, {U(f"{ach:.1f}%")} of the {AK(t, True)} target, {U(f"{wyoy:+.1f}%")} vs LY sales of {AK(tot_wly, True)} and {U(f"{wow:+.1f}%")} vs last week.',
           f'YTD sales as of {d1} are {U(AK(ya, True))}, {U(f"{yach:.1f}%")} of the {AK(yt, True)} target and {U(f"{yoy:+.1f}%")} vs LY sales of {AK(yly, True)}.')

    zh1 = (f'本週（{d0}~{d1}）銷售額為 {U(AK(a, "zh"))}，與目標 {AK(t, "zh")} 相比達成率 {U(f"{ach:.1f}%")}，與去年銷售額 {AK(tot_wly, "zh")} 相比 {U(f"{wyoy:+.1f}%")}，與上週相比 {U(f"{wow:+.1f}%")}。',
           f'截至 {d1} 累計銷售額為 {U(AK(ya, "zh"))}，與目標 {AK(yt, "zh")} 相比達成率 {U(f"{yach:.1f}%")}，與去年銷售額 {AK(yly, "zh")} 相比 {U(f"{yoy:+.1f}%")}。')

    def tile(lk, ko, en, krw=None, txt=None):
        if krw is not None:
            val = f'<b data-loc="{krw * 1000 / CUR_FX:.4f}">{fmt(krw)}</b>'
        else:
            val = f'<b>{txt}</b>'
        return f'<div class="tile"><small>{B(ko, en)}</small>{val}</div>'

    kp1 = ('<div class="kp"><div class="kl">' + B('이번 주', 'This week') + '</div>'
           + tile('', '주간 목표', 'Weekly target', t) + tile('', '주간 매출', 'Weekly sales', a)
           + tile('', '주간 달성률', 'Weekly achv.', txt=f'{ach:.1f}%') + tile('', '전년 매출', 'LY sales', tot_wly)
           + tile('', '전년비', 'YoY %', txt=f'{wyoy:+.1f}%') + '</div>')
    kp2 = ('<div class="kp"><div class="kl">' + B(f'누계 ({d1})', f'YTD ({d1})') + '</div>'
           + tile('', '누계 목표', 'YTD target', yt) + tile('', '누계 매출', 'YTD sales', ya)
           + tile('', '누계 달성률', 'YTD achv.', txt=f'{yach:.1f}%') + tile('', '전년 매출', 'LY sales', yly)
           + tile('', '전년비', 'YoY %', txt=f'{yoy:+.1f}%') + '</div>')
    sec1 = (f'<div class="sec">{head(1, "실적", "Results", "real")}<div class="dn-note" style="margin:-6px 0 8px">{unit}</div>'
            f'{BP(ko1[0], en1[0], zh=zh1[0])}{BP(ko1[1], en1[1], zh=zh1[1])}<div class="tiles">{kp1}{kp2}</div></div>')

    # 2. 유통별 실적
    import real_data as _rd0
    _wls = _rd0.WLY_STORE.get(ent, {}).get(int(mm.group(3)), {})
    ly_c = {g: len([r for r in rows if (_wls.get(r[0]) or 0) > 0]) for g, rows in groups if g != '기타'}
    cur_c = {g: len([r for r in rows if w[r[0]][1] > 0]) for g, rows in groups if g != '기타'}      # 표에 이번 주 매출이 찍힌 매장 수 (폐점 포함)
    off_cur = sum(cur_c.get(g, 0) for g in off_g)
    off_ly = sum(ly_c.get(g, 0) for g in off_g)
    thead = ('<tr><th rowspan="2">' + B('구분', 'Category') + '</th><th colspan="2">' + B('매장수', 'Stores') + '</th><th colspan="5">'
             + B('주간', 'Weekly') + '</th><th colspan="5">' + B('누계 (YTD)', 'YTD') + '</th></tr><tr><th>' + B('현재', 'Now')
             + '</th><th>' + B('전년 동기 대비', 'vs LY') + '</th><th>' + B('목표', 'Target') + '</th><th>' + B('매출', 'Sales')
             + '</th><th>' + B('달성률', 'Achv. %') + '</th><th>' + B('전년 매출', 'LY sales') + '</th><th>' + B('전년비', 'YoY %') + '</th><th>' + B('목표', 'Target')
             + '</th><th>' + B('매출', 'Sales') + '</th><th>' + B('달성률', 'Achv. %') + '</th><th>' + B('전년 매출', 'LY sales')
             + '</th><th>' + B('전년비', 'YoY %') + '</th></tr>')
    rows2 = _row(L('오프라인'), off, off_cur, off_ly, 'off', off_wly)
    for g in ('백화점', '아울렛', '팝업', '온라인'):
        if g in gsum and (cur_c.get(g, 0) or ly_c.get(g, 0)):
            rows2 += _row(L(g), gsum[g], cur_c.get(g, 0), ly_c.get(g, 0), 'off' if g == '온라인' else 'sub', g_wly[g])   # 온라인은 오프라인처럼 회색 굵게
    rows2 += _row(B('기타 (B2B&middot;직원구매 등)', 'Other (B2B, employee purchase, etc.)'), other, None, None, 'sub', g_wly['기타'])
    rows2 += _row(L('합계'), tot, None, None, 'tot', tot_wly)
    note2 = BP('유통별 실적에는 폐점 매장의 실적도 해당 유통에 포함됩니다. 매장수는 이번 주 실적 또는 목표가 있는 활성 매장 기준이고, 전년 동기는 2025년 9월에 매출이 발생한 매장 기준입니다. 주간 전년은 ERP 누계 전년의 주차 차분(추정치)입니다. 점평균 매출 = 오프라인 매출 ÷ 매출이 있는 매장 수이며, 점포 수 변화의 영향을 걷어내고 매장당 매출을 보기 위한 지표입니다. 이번 주는 이번 주 매출이 있는 매장 수와 2025년 9월 매출이 발생한 매장 수, 누계는 올해·전년 누계 매출이 있는 매장 수(폐점 매장 포함)로 나눕니다.',
               'Channel results include closed stores in their channel. Store counts are active stores with sales or target this week; the LY comparison uses stores that had sales in September 2025. Weekly LY is the week-over-week difference of ERP cumulative LY (estimate). Average sales per store = offline sales / number of stores with sales, to remove the effect of changes in store count. Weekly uses stores with sales this week and stores with sales in September 2025; YTD uses stores with YTD sales this year and last year (closed stores included).', 'div')

    def diff_ko(n, l):
        d = n - l
        return '변동이 없습니다' if d == 0 else f'{U(str(abs(d)) + "개")} {"증가" if d > 0 else "감소"}했습니다'

    def diff_en(n, l):
        d = n - l
        return 'unchanged' if d == 0 else f'{"up" if d > 0 else "down"} {U(str(abs(d)))}'

    def chan_sents(v, wly_v, tag_ko, tag_en, tag_zh):
        t_, a_, lw_, yt_, ya_, yly_ = v
        a1 = a_ / t_ * 100 if t_ else 0.0
        w1 = (a_ / wly_v - 1) * 100 if wly_v else 0.0
        a2 = ya_ / yt_ * 100 if yt_ else 0.0
        y2 = (ya_ / yly_ - 1) * 100 if yly_ else 0.0
        ko_ = (f'{tag_ko} 이번 주 매출은 {U(AK(a_, False))}, 목표 대비 {U(f"{a1:.1f}%")} 달성, 전년 매출 {AK(wly_v, False)} 대비 {U(f"{w1:+.1f}%")}입니다.',
               f'{tag_ko} 누계 매출은 {U(AK(ya_, False))}, 목표 대비 {U(f"{a2:.1f}%")} 달성, 전년 매출 {AK(yly_, False)} 대비 {U(f"{y2:+.1f}%")}입니다.')
        en_ = (f'{tag_en} sales this week were {U(AK(a_, True))}, {U(f"{a1:.1f}%")} of target and {U(f"{w1:+.1f}%")} vs LY sales of {AK(wly_v, True)}.',
               f'{tag_en} YTD sales are {U(AK(ya_, True))}, {U(f"{a2:.1f}%")} of target and {U(f"{y2:+.1f}%")} vs LY sales of {AK(yly_, True)}.')
        zh_ = (f'{tag_zh}本週銷售額為 {U(AK(a_, "zh"))}，達成率 {U(f"{a1:.1f}%")}，與去年銷售額 {AK(wly_v, "zh")} 相比 {U(f"{w1:+.1f}%")}。',
               f'{tag_zh}累計銷售額為 {U(AK(ya_, "zh"))}，達成率 {U(f"{a2:.1f}%")}，與去年銷售額 {AK(yly_, "zh")} 相比 {U(f"{y2:+.1f}%")}。')
        return ko_, en_, zh_

    off_ko, off_en, off_zh = chan_sents(off, off_wly, '오프라인', 'Offline', '線下')
    # 점평균 매출 = 매출 / 매출이 있는 매장 수 (올해와 전년 각각의 매장 수로 나눠 점포 수 변화의 영향을 제거)
    yc = ex.get('ytd_cnt', {})
    cur_sales_cnt = sum(1 for g in off_g for r in dict(groups)[g] if not _closed(r[0]) and w[r[0]][1] > 0)
    n26 = sum(yc.get(g, [0, 0])[0] for g in off_g)
    n25 = sum(yc.get(g, [0, 0])[1] for g in off_g)
    avg_now = off[1] / cur_sales_cnt if cur_sales_cnt else 0.0
    avg_ly = off_wly / off_ly if off_ly else 0.0
    yavg_now = off[4] / n26 if n26 else 0.0
    yavg_ly = off[5] / n25 if n25 else 0.0
    avg_pct = (avg_now / avg_ly - 1) * 100 if avg_ly else 0.0
    yavg_pct = (yavg_now / yavg_ly - 1) * 100 if yavg_ly else 0.0
    off_ko = (off_ko[0] + f' 점평균 매출은 {U(AK(avg_now, False))}, 전년 {AK(avg_ly, False)} 대비 {U(f"{avg_pct:+.1f}%")}입니다.',
              off_ko[1] + f' 점평균 매출은 {U(AK(yavg_now, False))}, 전년 {AK(yavg_ly, False)} 대비 {U(f"{yavg_pct:+.1f}%")}입니다.')
    off_en = (off_en[0] + f' Average sales per store were {U(AK(avg_now, True))}, {U(f"{avg_pct:+.1f}%")} vs the LY average of {AK(avg_ly, True)}.',
              off_en[1] + f' Average sales per store are {U(AK(yavg_now, True))}, {U(f"{yavg_pct:+.1f}%")} vs the LY average of {AK(yavg_ly, True)}.')
    off_zh = (off_zh[0] + f' 平均單店銷售額為 {U(AK(avg_now, "zh"))}，與去年 {AK(avg_ly, "zh")} 相比 {U(f"{avg_pct:+.1f}%")}。',
              off_zh[1] + f' 平均單店銷售額為 {U(AK(yavg_now, "zh"))}，與去年 {AK(yavg_ly, "zh")} 相比 {U(f"{yavg_pct:+.1f}%")}。')
    on_ko, on_en, on_zh = chan_sents(gsum.get('온라인', (0.0,) * 6), g_wly['온라인'], '온라인', 'Online', '線上')
    cmt = ('<div class="cmt"><div class="cg"><div>'
           + BP(off_ko[0], off_en[0], zh=off_zh[0]) + BP(off_ko[1], off_en[1], zh=off_zh[1]) + '</div></div>'
           '<div class="cg"><div>'
           + BP(on_ko[0], on_en[0], zh=on_zh[0]) + BP(on_ko[1], on_en[1], zh=on_zh[1]) + '</div></div></div>')
    sec2 = (f'<div class="sec">{head(2, "유통별 실적", "Results by Channel", "real")}<div class="dn-note" style="margin:-6px 0 8px">{unit}</div>'
            f'{cmt}<table class="t2">{thead}{rows2}</table><div class="dn-note">{note2}</div></div>')

    # 3. 오프라인 BEST / WORST
    offs = [(r[0], w[r[0]]) for g, rows in groups if g not in ('온라인', '기타') for r in rows if not _closed(r[0])]
    tgt = [x for x in offs if x[1][0] and x[1][0] > 0]
    n_hit = sum(1 for n, v in tgt if v[1] / v[0] >= 1)
    full_b = ex.get('full_both', set())
    cm_ = ex.get('full_months', 9)
    _by = {}
    for r_ in ex.get('lfl', []):
        k_ = r_['nm'].replace(' (Closure)', '').strip()
        a_ = _by.setdefault(k_, [0.0, 0.0])
        a_[0] += r_['ytd']
        a_[1] += r_['ytd_ly']
    yp = [(n, (0, 0, 0, 0, _by[nk][0], _by[nk][1])) for n, v in offs
          for nk in [n.replace(' (Closure)', '').strip()] if nk in full_b and nk in _by and _by[nk][1] > 0]
    n_up = sum(1 for n, v in yp if v[4] > v[5])
    wp = [x for x in offs if x[1][2] and x[1][2] > 0]
    lwp = wp
    n_wow = sum(1 for n, v in lwp if v[1] > v[2])
    ko3 = (f'오프라인 {U(f"{len(tgt)}개")} 매장 중 {U(f"{n_hit}개")}가 주간 목표를 달성했고(달성률 100% 이상), '
           f'전주 대비 {U(f"{n_wow}개")} 매장 증가했으며, '
           f'전년·올해 모두 1~{cm_}월 운영한 {len(yp)}개 매장 중 {U(f"{n_up}개")}가 전년 대비 증가했습니다.')
    en3 = (f'{U(f"{n_hit} of {len(tgt)}")} offline stores reached the weekly target (100% or more), '
           f'{U(f"{n_wow}")} stores grew vs last week, and '
           f'{U(f"{n_up} of {len(yp)}")} stores that operated in every month of Jan~{cm_} in both years grew YoY.')
    zh3 = (f'線下 {U(f"{len(tgt)} 家")}門市中有 {U(f"{n_hit} 家")}達成本週目標（達成率 100% 以上），較上週成長的門市有 {U(f"{n_wow} 家")}，'
           f'去年與今年皆於 1~{cm_} 月營運的 {len(yp)} 家門市中，有 {U(f"{n_up} 家")}較去年成長。')
    ach_key = lambda x: x[1][1] / x[1][0]
    yoy_key = lambda x: x[1][4] / x[1][5]
    wow_key = lambda x: x[1][1] / x[1][2]
    up_ach = _panel('&#9650; ' + B('달성률 상위 (주간)', 'Top achievement (weekly)'), sorted(tgt, key=lambda x: -ach_key(x))[:10], 'ach')
    dn_ach = _panel('&#9660; ' + B('달성률 하위 (주간)', 'Lowest achievement (weekly)'), sorted(tgt, key=ach_key)[:10], 'ach')
    up_yoy = _panel('&#9650; ' + B('전년 대비 증가 (누계)', 'Highest YoY growth (YTD)'), sorted([x for x in yp if yoy_key(x) > 1], key=lambda x: -yoy_key(x))[:10], 'yoy')
    dn_yoy = _panel('&#9660; ' + B('전년 대비 감소 (누계)', 'Largest YoY decline (YTD)'), sorted([x for x in yp if yoy_key(x) < 1], key=yoy_key)[:10], 'yoy')
    up_wow = _panel('&#9650; ' + B('전주 대비 증가', 'Largest WoW increase'), sorted([x for x in wp if wow_key(x) > 1], key=lambda x: -wow_key(x))[:10], 'wow')
    dn_wow = _panel('&#9660; ' + B('전주 대비 감소', 'Largest WoW decrease'), sorted([x for x in wp if wow_key(x) < 1], key=wow_key)[:10], 'wow')
    grid3 = '<div class="rk-grid">' + up_ach + up_wow + up_yoy + dn_ach + dn_wow + dn_yoy + '</div>'
    note3 = BP(f'달성률은 목표가 있는 전 매장, 전주 대비는 전주 실적이 있는 전 매장 기준입니다. 전년 대비(누계)는 올해와 전년 모두 1~{cm_}월 매출이 매월 있는 매장만 비교합니다(신규·폐점·재오픈 매장 제외).',
               f'Achievement covers every store with a target and WoW covers every store with last-week sales. YoY (YTD) compares only stores with sales in every month of Jan~{cm_} in both years (new, closed and reopened stores excluded).', 'div')
    sec3 = (f'<div class="sec">{head(3, "오프라인 실적 BEST / WORST", "Offline Stores BEST / WORST", "real")}'
            f'{BP(ko3, en3, zh=zh3)}{grid3}<div class="dn-note">{note3}</div></div>')

    # 4. 상품 실적
    fi, ci = ex.get('fwinfo', {}), ex.get('carryinfo', {})

    def nm_(r):
        return _html.escape(r['name'])

    good_ko = ', '.join(f'{nm_(r)}({r["wk"]}개, 판매율 {r["rate"]:.0f}%)' for r in fi.get('top', [])[:3] if r['rate'] is not None)
    good_en = ', '.join(f'{nm_(r)} ({r["wk"]} pcs, {r["rate"]:.0f}% sell-through)' for r in fi.get('top', [])[:3] if r['rate'] is not None)
    weak_ko = ', '.join(f'{nm_(r)}(판매율 {r["rate"]:.1f}%, 재고 {r["stock"]:,}개)' for r in fi.get('worst', [])[:3])
    weak_en = ', '.join(f'{nm_(r)} ({r["rate"]:.1f}% sell-through, {r["stock"]:,} in stock)' for r in fi.get('worst', [])[:3])
    c_pct = (ci['wk'] / ci['lw'] - 1) * 100 if ci.get('lw') else 0.0
    lead_ko = ', '.join(f'{nm_(r)}({r["wk"]}개)' for r in ci.get('top', [])[:3])
    lead_en = ', '.join(f'{nm_(r)} ({r["wk"]} pcs)' for r in ci.get('top', [])[:3])
    inc_ko = ', '.join(f'{nm_(r)}({r["lw"]}→{r["wk"]}개)' for r in ci.get('inc', []))
    inc_en = ', '.join(f'{nm_(r)} ({r["lw"]}→{r["wk"]} pcs)' for r in ci.get('inc', []))
    p1_ko = (f'신상품 26FW는 입고된 {U(f"{fi["n"]}개")} 스타일 중 {U(f"{fi["n_sold"]}개")} 스타일에서 판매가 발생했으며, '
             f'입고수량 {U(f"{fi["inq"]:,}개")}, 판매수량 {U(f"{fi["sold"]:,}개")}, 판매율 {U(f"{fi["rate"]:.1f}%")}입니다.')
    p1_en = (f'26FW new products: {U(str(fi["n_sold"]))} of the {U(str(fi["n"]))} styles received have sold, with {U(f"{fi["inq"]:,}")} units received, '
             f'{U(f"{fi["sold"]:,}")} units sold, and sell-through of {U(f"{fi["rate"]:.1f}%")}.')
    p2_ko = f'신상품 중 반응이 좋은 아이템은 {good_ko}입니다. 반면 {weak_ko}는 판매가 부진합니다.'
    p2_en = f'Strong new items are {good_en}. In contrast, {weak_en} are selling poorly.'
    p3_ko = (f'그 밖에 이월 상품(26SS 및 이전 시즌)은 이번 주 {U(f"{ci["wk"]:,}개")}가 판매되어 전주 대비 {U(f"{c_pct:+.1f}%")}이며 '
             f'전체 판매수량의 {U(f"{ci["share"]:.1f}%")}를 차지합니다. {lead_ko}가 판매를 이끌었고, 증가폭이 큰 상품은 {inc_ko}입니다.')
    p3_en = (f'Carry-over items (26SS and earlier) sold {U(f"{ci["wk"]:,}")} units this week, {U(f"{c_pct:+.1f}%")} vs last week and '
             f'{U(f"{ci["share"]:.1f}%")} of total units sold. Led by {lead_en}; biggest gains: {inc_en}.')

    good_zh = '、'.join(f'{nm_(r)}（{r["wk"]} 件，銷售率 {r["rate"]:.0f}%）' for r in fi.get('top', [])[:3] if r['rate'] is not None)
    weak_zh = '、'.join(f'{nm_(r)}（銷售率 {r["rate"]:.1f}%，庫存 {r["stock"]:,} 件）' for r in fi.get('worst', [])[:3])
    lead_zh = '、'.join(f'{nm_(r)}（{r["wk"]} 件）' for r in ci.get('top', [])[:3])
    inc_zh = '、'.join(f'{nm_(r)}（{r["lw"]}→{r["wk"]} 件）' for r in ci.get('inc', []))
    p1_zh = (f'新品 26FW 已到貨 {U(f"{fi["n"]} 款")}中，{U(f"{fi["n_sold"]} 款")}已有銷售，'
             f'到貨數量 {U(f"{fi["inq"]:,} 件")}、銷售數量 {U(f"{fi["sold"]:,} 件")}、銷售率 {U(f"{fi["rate"]:.1f}%")}。')
    p2_zh = f'新品中反應良好的商品為 {good_zh}。反之，{weak_zh} 銷售低迷。'
    p3_zh = (f'此外，往年商品（26SS 及更早季節）本週售出 {U(f"{ci["wk"]:,} 件")}，較上週 {U(f"{c_pct:+.1f}%")}，'
             f'占整體銷售數量的 {U(f"{ci["share"]:.1f}%")}。{lead_zh} 帶動銷售，增幅較大的商品為 {inc_zh}。')

    def rsn(label_ko, label_en, key):
        v = tx.get(key, DEFAULT.get(key, '해당 없음'))
        v = re.sub(r'<div class="ph">.*?</div>', '', v)
        return f'<div class="rsn"><span class="rl">{B(label_ko, label_en)}</span>{HL(BI(v))}</div>'

    grid4 = ('<div class="rk-grid">'
             + f'<div class="pn"><h4>&#9650; {B("신상품 26FW 호조 (주간 판매 상위)", "26FW new - strong (top weekly units)")}</h4><ol>{_prod(fi.get("top", []))}</ol></div>'
             + f'<div class="pn"><h4>&#9660; {B("신상품 26FW 부진 (판매율 하위)", "26FW new - weak (lowest sell-through)")}</h4><ol>{_prod(fi.get("worst", []))}</ol></div>'
             + f'<div class="pn"><h4>&#9650; {B("이월 상품 BEST (주간 판매 상위)", "Carry-over BEST (top weekly units)")}</h4><ol>{_prod(ci.get("top", []))}</ol></div></div>')
    note4 = BP('신상품 26FW = 26시즌 FW(시즌코드 3·4) 스타일입니다. 입고수량 = ERP 누적 입고(마감일 기준), 판매율 = 누적판매 &divide; 입고수량입니다. 부진은 입고 300개 이상 스타일 중 판매율 하위이고, 이월은 26SS 및 이전 시즌입니다. 사은품은 제외했습니다. 호조·부진 사유는 상세 일지(상품기획)에 담당자가 작성합니다.',
               '26FW new products = 26 season FW styles (season code 3 or 4). Units received = ERP cumulative receipts as of the cut-off; sell-through = cumulative sold / units received. Weak items are the lowest sell-through among styles with 300+ units received; carry-over means 26SS and earlier. Gifts are excluded. Reasons for strong and weak items are written by the Merchandising owner in the detailed journal.', 'div')
    sec4 = (f'<div class="sec">{head(4, "상품 실적", "Product Results", "real")}'
            f'{BP(p1_ko, p1_en, zh=p1_zh)}{BP(p2_ko, p2_en, zh=p2_zh)}{BP(p3_ko, p3_en, zh=p3_zh)}'
            f'{grid4}<div class="dn-note">{note4}</div></div>')
    # 새 구성(2026-10-02 오웬 확정): 서술형 + 진행현황 + 제품 서술 + BEST 표. 자료가 없거나 오류면 위의 기존 구성을 그대로 쓴다.
    try:
        import product_summary as _psm
        import product_section as _pse
        _ps = _psm.build(ent, None if brand == 'ALL' else brand, _wk1)
        if _ps:
            sec4 = _pse.render(_ps, B, BP, U, head(4, "상품 실적", "Product Results", "real"))
    except Exception as _e:
        print('WARN 상품 실적(새 구성) 실패 — 기존 구성 사용:', _e)

    # 5~7 (일지 입력 요약, 현재 샘플)
    def val(key):
        v = tx.get(key, DEFAULT.get(key, '해당 없음'))
        v = re.sub(r'<div class="ph">.*?</div>', '', v)
        return HL(BI(v))

    live = bool(CFG.get('served'))      # 구글에 올리는 화면: 5~7 은 담당자가 상세 일지에 저장한 글로 채운다 (샘플 서술 문단은 쓰지 않음)
    sec5, sec6, sec7 = _sum_tail(head, val, ent, f'W{_wk1}', live,
                                 [_lead_html(COMP_LEAD.get(ent)), _lead_html(REVIEW_LEAD.get(ent)), _lead_html(STRAT_LEAD.get(ent))])

    if part == 'head':
        return f'{sec1}{sec2}{sec3}{sec4}'
    if part == 'tail':
        return f'{sec5}{sec6}{sec7}'
    return (f'<section class="sum2"><div class="sum-h">SUMMARY<small><span class="ko">{lab} 주간 요약</span>'
            f'<span class="en">{lab} weekly summary</span><span class="zh">{lab} 每週摘要</span></small></div>'
            f'{sec1}{sec2}{sec3}{sec4}{sec5}{sec6}{sec7}</section>')


def make_summary_brands(ent, data, groups, weeks_meta, tx):
    """주간 SUMMARY: 전체/NG/MG 세 벌을 한 페이지에 담고 상단 브랜드 버튼으로 보이는 쪽만 바꾼다. 담당자 글(5~7)은 브랜드와 무관해 한 번만."""
    import real_data as rd_
    lab = weeks_meta[-1]['label']
    out = ''
    for b in ('ALL', 'NG', 'MG'):
        g_b, d_b = rd_.filter_brand(ent, groups, data, b)
        out += f'<div class="bv" data-bv="{b}">{make_summary(ent, d_b, g_b, weeks_meta, tx, brand=b, part="head")}</div>'
    tail = make_summary(ent, data, groups, weeks_meta, tx, brand='ALL', part='tail')
    return (f'<section class="sum2"><div class="sum-h">SUMMARY<small><span class="ko">{lab} 주간 요약</span>'
            f'<span class="en">{lab} weekly summary</span><span class="zh">{lab} 每週摘要</span></small></div>{out}{tail}</section>')


def _rank_kind(items, kind):
    """월간/연간 SUMMARY 용 순위 항목 (mly = 전년 동월 대비, mom = 전월 대비). 그 밖의 kind 는 _rank 그대로."""
    if kind not in ('mly', 'mom'):
        return _rank(items, kind)
    out = ''
    for k, (n, v) in enumerate(items, 1):
        t, a, base_, yt, ya, yly = v
        val = f'{(a / base_ - 1) * 100:+.1f}%'

        def nn(x):
            return f'<span data-loc="{x * 1000 / CUR_FX:.4f}">{fmt(x)}</span>'
        lab = B('전년 동월', 'Same month LY') if kind == 'mly' else B('전월', 'Last month')
        sub = f'{lab} {nn(base_)} &middot; {B("이번 달", "This month")} {nn(a)}'
        out += (f'<li class="{"more" if k > 3 else ""}"><span class="rk">{k}</span><span class="nm">{_html.escape(n)}</span><b class="vl">{val}</b>'
                f'<span class="sb">{sub}</span></li>')
    return out or f'<li><span class="sb" style="grid-column:1/-1">{B("해당 없음", "N/A")}</span></li>'


def _panel_kind(title, items, kind):
    return f'<div class="pn"><h4>{title}</h4><ol>{_rank_kind(items, kind)}</ol>{_more_btn(len(items))}</div>'


def _row_y(label, v, cur, ly, cls):
    """연간(누계 한 장) 표의 한 줄: 매장수 + 누계 5열"""
    t, a, _lw, yt, ya, yly = v
    yach = ya / yt * 100 if yt else None
    yoy = (ya / yly - 1) * 100 if yly else None
    if cur is None:
        cnt = '<td class="c">&mdash;</td><td class="c">&mdash;</td>'
    else:
        d = cur - ly
        cnt = f'<td class="c">{cur}</td><td class="c">{"0" if d == 0 else f"{d:+d}"}</td>'
    return (f'<tr class="{cls}"><td class="lb">{label}</td>{cnt}{_nc(yt)}{_nc(ya)}{_pc(yach, "ach")}{_nc(yly)}{_pc(yoy, "gr", True)}</tr>')


_WK_WORDS = [
    ('전년 동월', '전년 동주'), ('전월', '전주'), ('월 목표', '주간 목표'), ('월 매출', '주간 매출'), ('월 달성률', '주간 달성률'),
    ('이번 달', '이번 주'), ('월간', '주간'),
    ('same month LY', 'same week LY'), ('Same month LY', 'Same week LY'), ('last month', 'last week'), ('Last month', 'Last week'),
    ('monthly target', 'weekly target'), ('Monthly target', 'Weekly target'), ('Monthly sales', 'Weekly sales'),
    ('Monthly achv.', 'Weekly achv.'), ('This month', 'This week'), ('Monthly', 'Weekly'), ('monthly', 'weekly'),
    ('MoM', 'WoW'), ('(month)', '(week)'),
    ('去年同月', '去年同週'), ('上月', '上週'), ('月目標', '週目標'), ('月銷售額', '週銷售額'), ('月達成率', '週達成率'), ('本月', '本週'),
    ('月度', '週')]


def _weekly_words(html):
    """월간 SUMMARY 틀을 주간으로 쓸 때 용어를 바꾼다 (월→주)."""
    for a_, b_ in _WK_WORDS:
        html = html.replace(a_, b_)
    return html


_PM_WORDS = [('이번주', '이번 달'), ('전주', '전월'), ('금주', '이번 달'), ('주간', '월간'),
             ('This week', 'This month'), ('this week', 'this month'), ('Last week', 'Last month'), ('last week', 'last month'),
             ('Weekly', 'Monthly'), ('weekly', 'monthly'), ('week', 'month'),
             ('本週', '本月'), ('上週', '上月'), ('週增幅', '月增幅'), ('週銷售', '月銷售'), ('週', '月')]


def _monthly_product(ent, brand, n, mt, head):
    """월간 SUMMARY 4. 상품 실적. 주간과 같은 구성이고 주→월 단어만 바꾼다. 원장을 못 읽으면 ''."""
    try:
        import product_summary as _psm
        import product_section as _pse
        wbm = mt.get('wbm') or {}
        ps = _psm.build_month(ent, None if brand in (None, 'ALL') else brand, n, wbm.get(n), wbm.get(n - 1), mt.get('year') or 2026, partial=not mt.get('closed', True))
        if not ps:
            return ''
        html = _pse.render(ps, B, BP, U, head(4, '상품 실적', 'Product Results'))
        a, sep, b = html.partition('<script type="application/json" class="ps-img">')     # 사진 데이터(base64)는 건드리지 않는다
        for x, y in _PM_WORDS:
            a = a.replace(x, y)
        if not mt.get('closed', True):
            a += ('<div class="dn-note">' + BP('진행 중인 달이라 판매수량은 월초부터 마감일까지이고, 전월 비교는 전월의 같은 주 수(앞에서부터)와 합니다.',
                                              'The month is in progress: units are month-to-date, compared with the same number of weeks at the start of last month.', 'div') + '</div>')
        return a + sep + b
    except Exception as _e:
        print('WARN 월간 상품 실적 실패 — 숫자 부분만 표시:', _e)
        return ''


def _pnl_section(ent, per, n, head):
    """월간·연간 SUMMARY 0. P&L (2026-10-07 오웬 요청): 전략기획팀 TNH 글로벌 대시보드 결산(원화) 값에서 핵심 계정(매출액·매출원가·매출이익·판관비·영업이익)만.
    서술형(사실만) + 도표. 월간: 당월·누계(1월~그 달), 연간: 누계(마감 월까지). 결산 전 달은 실적 없이 계획·전년만. 데이터가 없으면 ''."""
    try:
        d = bep_data(ent)
    except Exception as _e:
        print('WARN P&L 데이터 읽기 실패 — 섹션 생략:', _e)
        return ''
    keys, mons, closed_m = d['rows'], d['months'], d['closed']
    idx = {k: i for i, k in enumerate(keys)}
    CORE = [('sales', '매출액', 'Net sales', '營業收入'), ('cogs', '매출원가', 'COGS', '銷貨成本'), ('gross', '매출이익', 'Gross profit', '銷貨毛利'),
            ('sga', '판관비', 'SG&A', '銷管費用'), ('direct', '직접성과이익', 'Direct profit', '直接績效利益'),
            ('com', '공통비배부', 'Allocated common cost', '共同費用分攤'), ('op', '영업이익', 'Operating profit', '營業利益')]
    PROFIT = {'direct', 'com', 'op'}      # 이익·배부 줄은 비율 대신 계획·전년과의 차이(백만원)

    def cum(m):          # 1월~m월 누계 [실적, 계획, 전년] (실적은 한 달이라도 없으면 None)
        if m == closed_m and d.get('ytd'):
            return [list(x) for x in d['ytd']]
        out = []
        for i in range(len(keys)):
            t, known = [0, 0, 0], True
            for k in range(1, m + 1):
                v = mons[str(k)][i]
                if v[0] is None:
                    known = False
                else:
                    t[0] += v[0]
                t[1] += v[1]
                t[2] += v[2]
            out.append([t[0] if known else None, t[1], t[2]])
        return out
    if per == 'm':
        if str(n) not in mons:
            return ''
        mv, yv = mons[str(n)], cum(n)
        cap = (f'{n}월', f'{MON_EN[n - 1]}', f'{n}月')
        ycap = (f'누계 (1~{n}월)', f'YTD (Jan-{MON_EN[n - 1][:3]})', f'累計（1～{n}月）')
    else:
        n = closed_m
        mv, yv = None, cum(n)
        ycap = (f'누계 (1~{n}월 결산)', f'YTD (Jan-{MON_EN[n - 1][:3]}, closed)', f'累計（1～{n}月 決算）')

    def sh(a, b):
        return (a / b * 100) if (a is not None and b) else None

    def ratio(a, b):
        r = sh(a, b)
        return f'{r:.1f}%' if r is not None else '&mdash;'

    def dif(a, b):
        if a is None:
            return '&mdash;'
        d = round(a - b)
        return '0' if d == 0 else f'{d:+,}'

    def cells(v, key):      # [실적, 계획, 계획比, 전년, 전년比]
        a, p, y = v
        prof = key in PROFIT
        c1 = dif(a, p) if prof else ratio(a, p)
        c2 = dif(a, y) if prof else ratio(a, y)
        return _nc(a) + _nc(p) + f'<td class="c ach">{c1}</td>' + _nc(y) + f'<td class="c gr">{c2}</td>'
    rows = ''
    for k, ko, en, zh in CORE:
        i = idx[k]
        cls = 'tot' if k in ('op', 'sales', 'direct') else 'sub'
        rows += (f'<tr class="{cls}"><td class="lb">{B(ko, en, zh)}</td>' + (cells(mv[i], k) if mv else '') + cells(yv[i], k) + '</tr>')
    sub = ('<th>' + B('실적', 'Actual', '實績') + '</th><th>' + B('계획', 'Plan', '計畫') + '</th><th>' + B('계획比', 'vs Plan', '對計畫') + '</th><th>'
           + B('전년', 'Last year', '去年') + '</th><th>' + B('전년比', 'vs LY', '對去年') + '</th>')
    th1 = ('<th colspan="5">' + B(*cap) + '</th>' if mv else '') + '<th colspan="5">' + B(*ycap) + '</th>'
    table = (f'<table class="t2 pnl"><tr><th rowspan="2">{B("계정", "Account", "科目")}</th>{th1}</tr><tr>{sub * (2 if mv else 1)}</tr>{rows}</table>')

    def txt(v, ko_pre, en_pre, zh_pre):
        """한 구간(당월 또는 누계)의 서술 3개 국어. 결산 전이면 계획·전년만."""
        s_, c_, sg_, o_ = (v[idx[k]] for k in ('sales', 'cogs', 'sga', 'op'))
        if s_[0] is None:
            return (f'{ko_pre}은 결산 전이라 실적은 없고, 매출액 계획은 {U(AK(s_[1], False))}, 전년 {AK(s_[2], False)}, 영업이익 계획은 {U(AK(o_[1], False))}, 전년 {AK(o_[2], False)}입니다.',
                    f'{en_pre}: not closed yet, so there are no actuals. Net sales plan {U(AK(s_[1], True))}, LY {AK(s_[2], True)}; operating profit plan {U(AK(o_[1], True))}, LY {AK(o_[2], True)}.',
                    f'{zh_pre}尚未結算，無實績。營業收入計畫 {U(AK(s_[1], "zh"))}，去年 {AK(s_[2], "zh")}；營業利益計畫 {U(AK(o_[1], "zh"))}，去年 {AK(o_[2], "zh")}。')
        ps_, ys_ = sh(s_[0], s_[1]), sh(s_[0], s_[2])
        pc_, pg_ = sh(c_[0], c_[1]), sh(sg_[0], sg_[1])
        od_p, od_y = o_[0] - o_[1], o_[0] - o_[2]

        def f1(x):
            return '—' if x is None else f'{x:.1f}%'
        return (f'{ko_pre} 매출액은 {U(AK(s_[0], False))}으로 계획 {AK(s_[1], False)} 대비 {U(f1(ps_))}, 전년 {AK(s_[2], False)} 대비 {U(f1(ys_))}입니다. '
                f'매출원가는 {AK(c_[0], False)}(계획 대비 {U(f1(pc_))}), 판관비는 {AK(sg_[0], False)}(계획 대비 {U(f1(pg_))})이고, '
                f'영업이익은 {U(AK(o_[0], False))}으로 계획 대비 {U(f"{od_p:+,.0f}백만원")}, 전년 대비 {U(f"{od_y:+,.0f}백만원")}입니다.',
                f'{en_pre}: net sales were {U(AK(s_[0], True))}, {U(f1(ps_))} of the {AK(s_[1], True)} plan and {U(f1(ys_))} of LY ({AK(s_[2], True)}). '
                f'COGS was {AK(c_[0], True)} ({U(f1(pc_))} of plan) and SG&A {AK(sg_[0], True)} ({U(f1(pg_))} of plan); '
                f'operating profit was {U(AK(o_[0], True))}, {U(f"{od_p:+,.0f}M")} vs plan and {U(f"{od_y:+,.0f}M")} vs LY (KRW).',
                f'{zh_pre}營業收入為 {U(AK(s_[0], "zh"))}，為計畫 {AK(s_[1], "zh")} 的 {U(f1(ps_))}、去年 {AK(s_[2], "zh")} 的 {U(f1(ys_))}。'
                f'銷貨成本 {AK(c_[0], "zh")}（計畫的 {U(f1(pc_))}），銷管費用 {AK(sg_[0], "zh")}（計畫的 {U(f1(pg_))}）；'
                f'營業利益為 {U(AK(o_[0], "zh"))}，較計畫 {U(f"{od_p:+,.0f}百萬韓元")}、較去年 {U(f"{od_y:+,.0f}百萬韓元")}。')
    paras = []
    if mv:
        paras.append(txt(mv, f'{n}월', f'{MON_EN[n - 1]}', f'{n}月'))
    paras.append(txt(yv, f'누계(1~{n}월)' if mv else f'누계(1~{n}월 결산)', f'YTD (Jan-{MON_EN[n - 1][:3]})', f'累計（1～{n}月）'))
    unit_ = ('<span class="unitcap"><span class="ko">단위 백만원(KRW)</span><span class="en">Unit: KRW million</span><span class="zh">單位：百萬韓元(KRW)</span></span>')
    note = BP('숫자는 전략기획팀 TNH 글로벌 대시보드의 결산(원화) 값입니다. 부가세·환율 기준이 달라 ERP 일지 숫자(1~3)와 다릅니다. 영업이익은 계획·전년과의 차이(백만원)로 표시합니다. 결산 전 달은 실적 없이 계획·전년만 나옵니다.',
              'Figures are settlement (KRW) values from the Strategic Planning TNH Global dashboard; VAT and FX bases differ, so they do not match the ERP figures in 1 to 3. Operating profit shows the difference (KRW million) from plan and LY. Months not yet closed show plan and LY only.', 'div')
    return (f'<div class="sec">{head(0, "P&L (손익)", "P&L")}<div class="dn-note" style="margin:-6px 0 8px">{unit_}</div>'
            + ''.join(BP(k, e, zh=z) for k, e, z in paras) + table + f'<div class="dn-note">{note}</div></div>')


def make_summary_period(ent, data, groups, meta, per, parts=False, brand=None):
    _set_fx(ent)
    """월간(per='m')·연간(per='y') SUMMARY 1~4 중 ERP 숫자 부분(1 실적, 2 유통별 실적, 3 오프라인 BEST/WORST).
    상품 실적과 담당자 글 요약(4~7)은 준비 중. 숫자는 data(원장 기반 월 데이터)에서만 계산하고 해석·추측 문구는 쓰지 않는다."""
    mon = per in ('m', 'w')
    wk_ = per == 'w'
    w = data[-1]
    prev = data[-2] if (mon and len(data) > 1) else None
    mt = meta[-1]
    span, asof, n = mt.get('span', ''), mt.get('asof', ''), mt.get('month', 0)
    closed = mt.get('closed', True)
    gsum = {g: sums([w[r[0]] for r in rows]) for g, rows in groups if g != '기타'}
    other = w['기타']
    tot = sums(list(w.values()))
    off_g = [g for g in ('백화점', '아울렛', '팝업') if g in gsum]
    off = tuple(sum(gsum[g][i] for g in off_g) for i in range(6))
    unit = ('<span class="unitcap"><span class="ko">단위 백만원(KRW)</span><span class="en">Unit: KRW million</span><span class="zh">單位：百萬韓元(KRW)</span></span>')

    def head(no, ko, en):
        return f'<h3><span class="no">{no}</span>{B(ko, en)}</h3>'

    t, a, ly, yt, ya, yly = tot
    ach = a / t * 100 if t else 0.0
    yoym = (a / ly - 1) * 100 if ly else 0.0
    pa = sum(prev[k][1] for k in prev) if prev else 0.0
    mom = (a / pa - 1) * 100 if pa else 0.0
    yach = ya / yt * 100 if yt else 0.0
    yoy = (ya / yly - 1) * 100 if yly else 0.0
    yr_lbl = f'{asof} '

    # ---- 1. 실적
    if mon:
        if wk_:
            pre_ko, pre_en, pre_zh = f'W{mt.get("wk", "")}({span})', f'W{mt.get("wk", "")} ({span})', f'W{mt.get("wk", "")}（{span}）'
        else:
            pre_ko = f'{n}월({span})' if closed else f'{n}월 월누계({span})'
            pre_en = f'{MON_EN[n - 1]} ({span})' if closed else f'{MON_EN[n - 1]} month-to-date ({span})'
            pre_zh = f'{n}月（{span}）' if closed else f'{n}月 月累計（{span}）'
        s1 = [(f'{pre_ko} 매출은 {U(AK(a, False))}, 목표 {AK(t, False)} 대비 {U(f"{ach:.1f}%")} 달성했고, 전년 동월 매출 {AK(ly, False)} 대비 {U(f"{yoym:+.1f}%")}이며 전월 대비 {U(f"{mom:+.1f}%")}입니다.',
               f'{pre_en} sales were {U(AK(a, True))}, {U(f"{ach:.1f}%")} of the {AK(t, True)} target, {U(f"{yoym:+.1f}%")} vs the same month LY ({AK(ly, True)}) and {U(f"{mom:+.1f}%")} vs last month.',
               f'{pre_zh}銷售額為 {U(AK(a, "zh"))}，與目標 {AK(t, "zh")} 相比達成率 {U(f"{ach:.1f}%")}，與去年同月 {AK(ly, "zh")} 相比 {U(f"{yoym:+.1f}%")}，與上月相比 {U(f"{mom:+.1f}%")}。')]
    else:
        s1 = []
    s1.append((f'{asof} 기준 누계 매출은 {U(AK(ya, False))}, 목표 {AK(yt, False)} 대비 {U(f"{yach:.1f}%")} 달성했으며, 전년 매출 {AK(yly, False)} 대비 {U(f"{yoy:+.1f}%")}입니다.',
               f'YTD sales as of {asof} are {U(AK(ya, True))}, {U(f"{yach:.1f}%")} of the {AK(yt, True)} target and {U(f"{yoy:+.1f}%")} vs LY sales of {AK(yly, True)}.',
               f'截至 {asof} 累計銷售額為 {U(AK(ya, "zh"))}，與目標 {AK(yt, "zh")} 相比達成率 {U(f"{yach:.1f}%")}，與去年銷售額 {AK(yly, "zh")} 相比 {U(f"{yoy:+.1f}%")}。'))

    def tile(ko, en, krw=None, txt=None):
        val = f'<b data-loc="{krw * 1000 / CUR_FX:.4f}">{fmt(krw)}</b>' if krw is not None else f'<b>{txt}</b>'
        return f'<div class="tile"><small>{B(ko, en)}</small>{val}</div>'
    kp = ''
    if mon:
        kp += ('<div class="kp"><div class="kl">' + (B(f'W{mt.get("wk", "")}', f'W{mt.get("wk", "")}', f'W{mt.get("wk", "")}') if wk_ else B(f'{n}월' + ('' if closed else ' 월누계'), f'{MON_EN[n - 1]}' + ('' if closed else ' MTD'))) + '</div>'
               + tile('월 목표', 'Monthly target', t) + tile('월 매출', 'Monthly sales', a) + tile('월 달성률', 'Monthly achv.', txt=f'{ach:.1f}%')
               + tile('전년 동월', 'Same month LY', ly) + tile('전년비', 'YoY %', txt=f'{yoym:+.1f}%') + '</div>')
    kp += ('<div class="kp"><div class="kl">' + B(f'누계 ({asof})', f'YTD ({asof})') + '</div>'
           + tile('누계 목표', 'YTD target', yt) + tile('누계 매출', 'YTD sales', ya) + tile('누계 달성률', 'YTD achv.', txt=f'{yach:.1f}%')
           + tile('전년 매출', 'LY sales', yly) + tile('전년비', 'YoY %', txt=f'{yoy:+.1f}%') + '</div>')
    sec1 = (f'<div class="sec">{head(1, "실적", "Results")}<div class="dn-note" style="margin:-6px 0 8px">{unit}</div>'
            + ''.join(BP(k, e, zh=z) for k, e, z in s1) + f'<div class="tiles">{kp}</div></div>')

    # ---- 2. 유통별 실적
    def cnt_now(rows):
        return len([r for r in rows if (w[r[0]][1] > 0 if mon else w[r[0]][4] > 0)])      # 표에 매출이 찍힌 매장 수 (폐점 포함)

    def cnt_ly(rows):
        return len([r for r in rows if (w[r[0]][2] > 0 if mon else w[r[0]][5] > 0)])    # 전년에 운영했던 매장은 지금 폐점이어도 포함
    cur_c = {g: cnt_now(rows) for g, rows in groups if g != '기타'}
    ly_c = {g: cnt_ly(rows) for g, rows in groups if g != '기타'}
    off_cur, off_ly = sum(cur_c.get(g, 0) for g in off_g), sum(ly_c.get(g, 0) for g in off_g)
    th_mon = (('<th colspan="5">' + B('월간', 'Monthly') + '</th>') if mon else '')
    th_sub = (('<th>' + B('목표', 'Target') + '</th><th>' + B('매출', 'Sales') + '</th><th>' + B('달성률', 'Achv. %') + '</th><th>'
               + B('전년 동월', 'Same month LY') + '</th><th>' + B('전년비', 'YoY %') + '</th>') if mon else '')
    thead = ('<tr><th rowspan="2">' + B('구분', 'Category') + '</th><th colspan="2">' + B('매장수', 'Stores') + '</th>' + th_mon
             + '<th colspan="5">' + B('누계 (YTD)', 'YTD') + '</th></tr><tr><th>' + B('현재', 'Now') + '</th><th>' + B('전년 동기 대비', 'vs LY') + '</th>'
             + th_sub + '<th>' + B('목표', 'Target') + '</th><th>' + B('매출', 'Sales') + '</th><th>' + B('달성률', 'Achv. %')
             + '</th><th>' + B('전년 매출', 'LY sales') + '</th><th>' + B('전년비', 'YoY %') + '</th></tr>')

    def row(label, v, cur, ly_, cls):
        return _row(label, v, cur, ly_, cls, v[2]) if mon else _row_y(label, v, cur, ly_, cls)
    rows2 = row(L('오프라인'), off, off_cur, off_ly, 'off')
    for g in ('백화점', '아울렛', '팝업', '온라인'):
        if g in gsum and (cur_c.get(g, 0) or ly_c.get(g, 0)):
            rows2 += row(L(g), gsum[g], cur_c.get(g, 0), ly_c.get(g, 0), 'off' if g == '온라인' else 'sub')
    rows2 += row(B('기타 (B2B&middot;직원구매 등)', 'Other (B2B, employee purchase, etc.)'), other, None, None, 'sub')
    rows2 += row(L('합계'), tot, None, None, 'tot')

    per_ko = '주간' if wk_ else f'{n}월'
    per_en = 'this week' if wk_ else f'in {MON_EN[n - 1] if n else ""}'
    per_zh = '本週' if wk_ else f'{n}月'

    def ch(v, tag_ko, tag_en, tag_zh):
        t_, a_, ly_, yt_, ya_, yly_ = v
        a1 = a_ / t_ * 100 if t_ else 0.0
        y1 = (a_ / ly_ - 1) * 100 if ly_ else 0.0
        a2 = ya_ / yt_ * 100 if yt_ else 0.0
        y2 = (ya_ / yly_ - 1) * 100 if yly_ else 0.0
        out = []
        if mon:
            out.append((f'{tag_ko} {per_ko} 매출은 {U(AK(a_, False))}, 목표 대비 {U(f"{a1:.1f}%")} 달성, 전년 동월 매출 {AK(ly_, False)} 대비 {U(f"{y1:+.1f}%")}입니다.',
                        f'{tag_en} sales {per_en} were {U(AK(a_, True))}, {U(f"{a1:.1f}%")} of target and {U(f"{y1:+.1f}%")} vs the same month LY of {AK(ly_, True)}.',
                        f'{tag_zh}{per_zh}銷售額為 {U(AK(a_, "zh"))}，達成率 {U(f"{a1:.1f}%")}，與去年同月 {AK(ly_, "zh")} 相比 {U(f"{y1:+.1f}%")}。'))
        out.append((f'{tag_ko} 누계 매출은 {U(AK(ya_, False))}, 목표 대비 {U(f"{a2:.1f}%")} 달성, 전년 매출 {AK(yly_, False)} 대비 {U(f"{y2:+.1f}%")}입니다.',
                    f'{tag_en} YTD sales are {U(AK(ya_, True))}, {U(f"{a2:.1f}%")} of target and {U(f"{y2:+.1f}%")} vs LY sales of {AK(yly_, True)}.',
                    f'{tag_zh}累計銷售額為 {U(AK(ya_, "zh"))}，達成率 {U(f"{a2:.1f}%")}，與去年銷售額 {AK(yly_, "zh")} 相比 {U(f"{y2:+.1f}%")}。'))
        return out
    cmt = '<div class="cmt">'
    for v, tk, te, tz in ((off, '오프라인', 'Offline', '線下'), (gsum.get('온라인', (0,) * 6), '온라인', 'Online', '線上')):
        cmt += '<div class="cg"><div>' + ''.join(BP(k, e, zh=z) for k, e, z in ch(v, tk, te, tz)) + '</div></div>'
    cmt += '</div>'
    note2 = BP('유통별 실적에는 폐점 매장의 실적도 해당 유통에 포함됩니다. 매장수는 표에서 해당 기간에 매출이 있는 매장(폐점 표시 매장 포함) 수이고, 전년 동기 대비는 전년 같은 기간에 매출이 있었던 매장 수와의 차이입니다. 모든 숫자는 ERP 일별 원장(최신 조회값)에서 계산했습니다.',
               'Channel results include closed stores in their channel. Store counts are the stores in the table with sales in the period (closed stores included); the LY comparison uses stores that had sales in the same period last year. All figures are calculated from the ERP daily ledger (latest values).', 'div')
    sec2 = (f'<div class="sec">{head(2, "유통별 실적", "Results by Channel")}<div class="dn-note" style="margin:-6px 0 8px">{unit}</div>'
            f'{cmt}<table class="t2">{thead}{rows2}</table><div class="dn-note">{note2}</div></div>')

    # ---- 3. 오프라인 BEST / WORST
    offs = [(r[0], w[r[0]]) for g, rows in groups if g not in ('온라인', '기타') for r in rows if not _closed(r[0])]
    if mon:
        tgt = [x for x in offs if x[1][0] and x[1][0] > 0]
        n_hit = sum(1 for _n, v in tgt if v[1] / v[0] >= 1)
        lyl = [x for x in offs if x[1][2] and x[1][2] > 0 and x[1][1] > 0]
        n_up = sum(1 for _n, v in lyl if v[1] > v[2])
        momv = [(nm, (v[0], v[1], prev[nm][1] if nm in prev else 0.0, v[3], v[4], v[5])) for nm, v in offs] if prev else []
        momv = [x for x in momv if x[1][2] > 0 and x[1][1] > 0]
        n_mom = sum(1 for _n, v in momv if v[1] > v[2])
        ko3 = (f'오프라인 {U(f"{len(tgt)}개")} 매장 중 {U(f"{n_hit}개")}가 월 목표를 달성했고(달성률 100% 이상), 전년 동월 매출이 있는 {len(lyl)}개 매장 중 {U(f"{n_up}개")}가 전년 동월 대비 증가했으며, '
               f'전월 매출이 있는 {len(momv)}개 매장 중 {U(f"{n_mom}개")}가 전월 대비 증가했습니다.')
        en3 = (f'{U(f"{n_hit} of {len(tgt)}")} offline stores reached the monthly target (100% or more); {U(f"{n_up} of {len(lyl)}")} stores with sales in the same month LY grew; '
               f'{U(f"{n_mom} of {len(momv)}")} stores with sales last month grew vs last month.')
        zh3 = (f'線下 {len(tgt)} 家門市中有 {U(f"{n_hit} 家")}達成月目標（達成率 100% 以上），去年同月有銷售的 {len(lyl)} 家中有 {U(f"{n_up} 家")}較去年同月成長，'
               f'上月有銷售的 {len(momv)} 家中有 {U(f"{n_mom} 家")}較上月成長。')
        ak = lambda x: x[1][1] / x[1][0]
        panels = (_panel_kind('&#9650; ' + B('달성률 상위 (월간)', 'Top achievement (monthly)'), sorted(tgt, key=lambda x: -ak(x))[:10], 'ach')
                  + _panel_kind('&#9650; ' + B('전월 대비 증가', 'Largest MoM increase'), sorted([x for x in momv if x[1][1] > x[1][2]], key=lambda x: -(x[1][1] / x[1][2]))[:10], 'mom')
                  + _panel_kind('&#9650; ' + B('전년 동월 대비 증가', 'Highest YoY growth (month)'), sorted([x for x in lyl if x[1][1] > x[1][2]], key=lambda x: -(x[1][1] / x[1][2]))[:10], 'mly')
                  + _panel_kind('&#9660; ' + B('달성률 하위 (월간)', 'Lowest achievement (monthly)'), sorted(tgt, key=ak)[:10], 'ach')
                  + _panel_kind('&#9660; ' + B('전월 대비 감소', 'Largest MoM decrease'), sorted([x for x in momv if x[1][1] < x[1][2]], key=lambda x: x[1][1] / x[1][2])[:10], 'mom')
                  + _panel_kind('&#9660; ' + B('전년 동월 대비 감소', 'Largest YoY decline (month)'), sorted([x for x in lyl if x[1][1] < x[1][2]], key=lambda x: x[1][1] / x[1][2])[:10], 'mly'))
        note3 = BP('달성률은 월 목표가 있는 전 매장, 전월 대비는 전월 매출이 있는 전 매장, 전년 동월 대비는 전년 같은 달에 매출이 있었던 매장 기준입니다(신규·폐점 매장은 비교 대상이 있을 때만 포함).',
                   'Achievement covers every store with a monthly target, MoM covers stores with sales last month, and YoY covers stores with sales in the same month last year (new and closed stores only when a comparison base exists).', 'div')
    else:
        ytgt = [(nm, (v[3], v[4], 0.0, 0.0, 0.0, 0.0)) for nm, v in offs if v[3] and v[3] > 0]
        yp = [(nm, v) for nm, v in offs if v[5] and v[5] > 0 and v[4] > 0]
        n_hit = sum(1 for _n, v in ytgt if v[1] / v[0] >= 1)
        n_up = sum(1 for _n, v in yp if v[4] > v[5])
        ko3 = f'오프라인 {U(f"{len(ytgt)}개")} 매장 중 {U(f"{n_hit}개")}가 누계 목표를 달성했고, 전년 누계 매출이 있는 {len(yp)}개 매장 중 {U(f"{n_up}개")}가 전년 대비 증가했습니다.'
        en3 = f'{U(f"{n_hit} of {len(ytgt)}")} offline stores reached the YTD target, and {U(f"{n_up} of {len(yp)}")} stores with LY YTD sales grew YoY.'
        zh3 = f'線下 {len(ytgt)} 家門市中有 {U(f"{n_hit} 家")}達成累計目標，去年累計有銷售的 {len(yp)} 家中有 {U(f"{n_up} 家")}較去年成長。'
        ak = lambda x: x[1][1] / x[1][0]
        yk = lambda x: x[1][4] / x[1][5]
        panels = (_panel_kind('&#9650; ' + B('달성률 상위 (누계)', 'Top achievement (YTD)'), sorted(ytgt, key=lambda x: -ak(x))[:10], 'ach')
                  + _panel_kind('&#9650; ' + B('전년 대비 증가 (누계)', 'Highest YoY growth (YTD)'), sorted([x for x in yp if yk(x) > 1], key=lambda x: -yk(x))[:10], 'yoy')
                  + _panel_kind('&#9660; ' + B('달성률 하위 (누계)', 'Lowest achievement (YTD)'), sorted(ytgt, key=ak)[:10], 'ach')
                  + _panel_kind('&#9660; ' + B('전년 대비 감소 (누계)', 'Largest YoY decline (YTD)'), sorted([x for x in yp if yk(x) < 1], key=yk)[:10], 'yoy'))
        note3 = BP('달성률은 누계 목표가 있는 전 매장, 전년 대비는 전년 누계 매출이 있는 전 매장 기준입니다(올해 매출이 있는 매장만).',
                   'Achievement covers every store with a YTD target; YoY covers stores with LY YTD sales (and sales this year).', 'div')
    sec3 = (f'<div class="sec">{head(3, "오프라인 실적 BEST / WORST", "Offline Stores BEST / WORST")}'
            f'{BP(ko3, en3, zh=zh3)}<div class="rk-grid">{panels}</div><div class="dn-note">{note3}</div></div>')

    soon = ('<div class="sec"><div class="dn-note">' + BP('상품 실적과 담당자 글 요약(4~7)은 준비 중입니다.', 'Product results and the owners\' journal summary (4 to 7) are coming soon.', 'div') + '</div></div>')
    if mon:       # 월간·지난 주: 5~7 은 담당자가 월간(M..)/그 주(W..) 일지에 저장한 글로 채운다 (상품 실적 4 는 준비 중)
        _tag = f'W{mt.get("wk", "")}' if wk_ else f'M{n:02d}'
        _s5, _s6, _s7 = _sum_tail(lambda no, ko, en, badge: head(no, ko, en), lambda key: '—', ent, _tag, True, ['', '', ''],
                                  (('경쟁사 동향', 'Competitor Trends'),
                                   ('금주 리뷰', 'This Week Review') if wk_ else ('이번 달 리뷰', 'Month Review'),
                                   ('차주 전략', 'Next Week Strategy') if wk_ else ('다음 달 전략', 'Next Month Strategy')))
        soon = ('' if (per == 'm' and mt.get('wbm')) else '<div class="sec"><div class="dn-note">' + BP('상품 실적(4)은 준비 중입니다.', 'Product results (4) are coming soon.', 'div') + '</div></div>') + _s5 + _s6 + _s7
    if wk_:
        title_ko, title_en, title_zh = f'{span} (W{mt.get("wk", "")}) 주간 요약', f'{span} (W{mt.get("wk", "")}) weekly summary', f'{span} (W{mt.get("wk", "")}) 週報摘要'
    else:
        title_ko = f'{n}월 월간 요약' if mon else f'{asof} 연간 누계 요약'
        title_en = f'{MON_EN[n - 1]} monthly summary' if mon else f'Year-to-date summary as of {asof}'
        title_zh = f'{n}月 月報摘要' if mon else f'{asof} 年度累計摘要'
    hdr_ = (f'<div class="sum-h">SUMMARY<small><span class="ko">{title_ko}</span>'
            f'<span class="en">{title_en}</span><span class="zh">{title_zh}</span></small></div>')
    sec4 = _monthly_product(ent, brand, n, mt, head) if (per == 'm' and mt.get('wbm')) else ''
    inner_ = f'{sec1}{sec2}{sec3}{sec4}'
    sec0 = _pnl_section(ent, per, n, head) if per in ('m', 'y') else ''
    if wk_:
        hdr_, inner_, soon = _weekly_words(hdr_), _weekly_words(inner_), _weekly_words(soon)
    hdr_ += sec0      # P&L 은 브랜드와 무관(법인 전체) — 브랜드 전환 바깥 맨 위에 둔다
    if parts:
        return hdr_, inner_, soon
    return f'<section class="sum2">{hdr_}{inner_}{soon}</section>'


def period_brands(ent, data_list, groups, meta, per):
    """월간·연간·지난 주 SUMMARY: 전체/NG/MG 세 벌을 한 페이지에 담는다 (상단 브랜드 버튼으로 전환)"""
    import real_data as rd_
    hdr, soon, body = '', '', ''
    for b in ('ALL', 'NG', 'MG'):
        g_b, d_b = rd_.filter_brand(ent, groups, data_list, b)
        hdr, inner, soon = make_summary_period(ent, d_b, g_b, meta, per, parts=True, brand=b)
        body += f'<div class="bv" data-bv="{b}">{inner}</div>'
    return f'<section class="sum2">{hdr}{body}{soon}</section>'


_API_FILE = os.path.join(OUT, '..', '..', '..', 'apps_script', 'weekly_journal', 'api_url.txt')
API_URL = (io.open(_API_FILE, encoding='utf-8').read().strip() if os.path.exists(_API_FILE) else '') or os.environ.get('WJ_API_URL', '')
EDIT_JS = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wj_edit.js'), encoding='utf-8').read()

CHART_CSS = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chart.css'), encoding='utf-8').read()
CHART_JS = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chart.js'), encoding='utf-8').read()


FOLD_JS = """(function(){
function setRow(tr,closed){
  tr.classList.toggle('closed',closed);
  var g=tr.getAttribute('data-g'),d=tr.getAttribute('data-d');
  var sel=(g!==null)?'tr[data-gm="'+g+'"]':'tr[data-dm="'+d+'"]';
  document.querySelectorAll(sel).forEach(function(r){r.style.display=closed?'none':'';});
}
document.querySelectorAll('tr[data-g],tr[data-d]').forEach(function(tr){
  tr.addEventListener('click',function(){setRow(tr,!tr.classList.contains('closed'));});
});
document.querySelectorAll('.fold button').forEach(function(b){
  b.addEventListener('click',function(ev){
    ev.stopPropagation();
    var attr=(b.getAttribute('data-t')==='g')?'tr[data-g]':'tr[data-d]',closed=(b.getAttribute('data-f')==='close');
    document.querySelectorAll(attr).forEach(function(tr){setRow(tr,closed);});
  });
});
document.querySelectorAll('tr[data-g]').forEach(function(tr){setRow(tr,true);});
document.querySelectorAll('tr[data-d]').forEach(function(tr){var d=tr.getAttribute('data-d');setRow(tr,!(d==='wx'||d==='0'));});
})();"""


CUR_JS = """(function(){
var ENT='__ENT__',LC='__LC__',DEF=__DEF__,mode='krw',rate=DEF;
try{mode=localStorage.getItem('wj_cur')||'krw';var r=parseFloat(localStorage.getItem('wj_fx_'+ENT));if(r>0)rate=r;}catch(e){}
if(mode!=='krw'&&mode!=='loc')mode='krw';
var cb=document.querySelectorAll('#cur button'),fx=document.getElementById('fx'),fxb=document.getElementById('fxbox'),fxr=document.getElementById('fxr');
function f(x){return Math.round(x).toLocaleString('en-US');}
function apply(){
  document.querySelectorAll('[data-loc]').forEach(function(e){
    var loc=parseFloat(e.getAttribute('data-loc'));
    var v=(mode==='krw')?loc*rate/1000:loc;
    if(e.classList.contains('amt')){
      var lcx=e.closest('.ko,.en,.zh'),lg=lcx?(lcx.classList.contains('en')?'en':(lcx.classList.contains('zh')?'zh':'ko')):'ko';
      e.textContent=(mode==='krw')?(lg==='en'?('KRW '+f(v)+'M'):(lg==='zh'?(f(v)+'百萬韓元'):(f(v)+'백만원'))):(lg==='en'?(LC+' '+f(v)+'K'):(lg==='zh'?(f(v)+'千 '+LC):(f(v)+'천 '+LC)));
    }else{e.textContent=f(v);}
  });
  document.querySelectorAll('.unitcap').forEach(function(u){
    var k=u.querySelector('.ko'),n=u.querySelector('.en'),z=u.querySelector('.zh');
    if(mode==='krw'){k.textContent='단위 백만원(KRW)';n.textContent='Unit: KRW million';if(z)z.textContent='單位：百萬韓元(KRW)';}
    else{k.textContent='단위 천 '+LC;n.textContent='Unit: '+LC+' thousand';if(z)z.textContent='單位：千 '+LC;}
  });
  cb.forEach(function(b){b.classList.toggle('on',b.getAttribute('data-c')===mode);});
  fx.value=rate;fxb.classList.toggle('dim',mode!=='krw');
}
cb.forEach(function(b){b.addEventListener('click',function(){mode=b.getAttribute('data-c');try{localStorage.setItem('wj_cur',mode);}catch(e){}apply();});});
fx.addEventListener('input',function(){var x=parseFloat(fx.value);if(x>0){rate=x;try{localStorage.setItem('wj_fx_'+ENT,String(x));}catch(e){}apply();fx.value=fx.value;}});
fxr.addEventListener('click',function(){rate=DEF;try{localStorage.setItem('wj_fx_'+ENT,String(DEF));}catch(e){}apply();});
window.wjApplyCur=apply;
apply();
})();"""


def cur_ctl(ent):
    lc = 'HKD' if ent == 'HK' else 'TWD'
    return (f'<div class="tabs cur" id="cur"><button class="on" data-c="krw">KRW</button><button data-c="loc">{lc}</button></div>'
            f'<div class="fxbox" id="fxbox"><span class="ko">적용환율</span><span class="en">Rate</span><span class="zh">適用匯率</span> 1 {lc} = '
            f'<input id="fx" type="number" min="0.0001" step="0.1" value="{int(CUR_FX)}"> KRW '
            f'<button id="fxr"><span class="ko">초기화</span><span class="en">Reset</span><span class="zh">重設</span></button></div>')


def cur_js(ent):
    _set_fx(ent)
    lc = 'HKD' if ent == 'HK' else 'TWD'
    return CUR_JS.replace('__ENT__', ent).replace('__LC__', lc).replace('__DEF__', str(int(CUR_FX)))


LANG_JS = """var lb=document.querySelectorAll('#lang button');
function setLang(l){document.body.setAttribute('data-lang',l);document.documentElement.lang=l;lb.forEach(function(b){b.classList.toggle('on',b.getAttribute('data-l')===l);});try{localStorage.setItem('wj_lang',l);}catch(e){}}
lb.forEach(function(b){b.addEventListener('click',function(){setLang(b.getAttribute('data-l'));});});
var sv='ko';try{sv=localStorage.getItem('wj_lang')||'ko';}catch(e){}
setLang(sv);"""


LABELS.update({'월간 일지': 'Monthly journal', '월간실적': 'Monthly', '월간영업일지': 'Monthly Sales Journal',
               '4개월 비교': '4-month view', '1. 이번달 실적': '1. This month results',
               '3. 월간 일지': '3. Monthly department journal'})
ZH_LABELS.update({'월간 일지': '月報日誌', '월간실적': '本月實績', '월간영업일지': '每月營業日誌',
                  '4개월 비교': '4 個月比較', '1. 이번달 실적': '1. 本月實績', '3. 월간 일지': '3. 各部門月報'})


LABELS.update({'국가': 'Country', '브랜드': 'Brand', '전체': 'All', '영업일지': 'Sales Journal', '기간': 'Period', '주간': 'Weekly', '월간': 'Monthly', '연간': 'Yearly',
               '통화': 'Currency', '언어': 'Language', '데이터 기준': 'Data as of', '보기 설정': 'View settings',
               '연간 전체': 'Full year', '1. 연간 실적': '1. Year results', '3. 연간 일지': '3. Yearly'})
ZH_LABELS.update({'국가': '國家', '브랜드': '品牌', '전체': '全部', '영업일지': '營業日誌', '기간': '期間', '주간': '週', '월간': '月', '연간': '年',
                  '통화': '幣別', '언어': '語言', '데이터 기준': '資料基準', '보기 설정': '檢視設定',
                  '연간 전체': '全年', '1. 연간 실적': '1. 年度實績', '3. 연간 일지': '3. 年度'})

# 상단 막대 (A안): 1줄 제목 / 2줄 SUMMARY·상세 일지 / 3줄 기간·통화·언어·작업·데이터 기준 — 색은 기존 페이지(흰 바탕, 검정 선택, 회색 테두리) 그대로
HDR_CSS = """
.hd{padding:16px 20px 8px}
.hd h1{margin:0 0 16px;font-size:24px;font-weight:700}
.hd .nav{margin:0 0 14px}
.tabs a.dis{opacity:.4;cursor:not-allowed;pointer-events:none}
.tabs[hidden]{display:none}
.bh{display:none!important}
.bv{display:none}
.bv[data-bv="ALL"]{display:block}
body[data-brand="NG"] .bv[data-bv="ALL"],body[data-brand="MG"] .bv[data-bv="ALL"]{display:none}
body[data-brand="NG"] .bv[data-bv="NG"],body[data-brand="MG"] .bv[data-bv="MG"]{display:block}
.bar{display:flex;flex-wrap:wrap;align-items:center;gap:8px 26px;padding:8px 12px;background:#f3f4f6;border:1px solid #e5e7eb;border-radius:12px}
.hg{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.hg[hidden]{display:none}
.persel{min-width:170px}
.pn:not(.open) li.more{display:none}
.pmore{display:block;margin:6px auto 10px;font:inherit;font-size:12px;padding:3px 14px;border:1px solid #d1d5db;background:#fff;color:#4b5563;border-radius:14px;cursor:pointer}
.pmore:hover{border-color:#9ca3af}
.pn:not(.open) .pmore .m2,.pn.open .pmore .m1{display:none}
.gl{font-size:11px;font-weight:600;color:#6b7280;white-space:nowrap}
.asof{margin-left:auto;font-size:11.5px;color:#6b7280;display:inline-flex;gap:8px;align-items:center;flex-wrap:wrap}
.asof .stat{margin:0;padding:1px 10px;font-size:11px}
.pop{position:relative;display:inline-block}
.gear{font:inherit;font-size:13px;line-height:1;padding:4px 8px;border:1px solid #d1d5db;background:#fff;border-radius:14px;cursor:pointer;color:#4b5563}
.gear[aria-expanded="true"]{background:#111;color:#fff;border-color:#111}
#fxbox.panelbox{position:absolute;z-index:20;top:32px;left:0;background:#fff;border:1px solid #d1d5db;border-radius:10px;padding:10px 12px;box-shadow:0 8px 24px rgba(0,0,0,.15);white-space:nowrap}
#fxbox[hidden]{display:none}
.barToggle{display:none;font:inherit;font-size:12px;padding:4px 12px;border:1px solid #d1d5db;background:#fff;color:#4b5563;border-radius:14px;cursor:pointer}
@media (max-width:820px){
  .barToggle{display:inline-block}
  .bar.collapsed .hg,.bar.collapsed .asof{display:none}
  .asof{margin-left:0}
  .hd{padding-inline:14px}
}
"""

HDR_JS = """(function(){
window.wjRole=function(role){try{if(role)localStorage.setItem('wj_role',role);}catch(e){}var g=document.getElementById('entGrp');if(g&&!g.hasAttribute('data-local'))g.hidden=(role||'')!=='hq';};
(function(){var r='';try{r=localStorage.getItem('wj_role')||'';}catch(e){}window.wjRole(r);})();
var bar=document.getElementById('bar'),bt=document.getElementById('barToggle');
if(bar&&bt){if(window.innerWidth<=820)bar.classList.add('collapsed');
  bt.addEventListener('click',function(){var c=bar.classList.toggle('collapsed');bt.setAttribute('aria-expanded',c?'false':'true');});}
document.querySelectorAll('.pmore').forEach(function(b){b.addEventListener('click',function(){b.closest('.pn').classList.toggle('open');});});
var ps=document.getElementById('perSel');
if(ps){
  var lt=function(){var l=document.body.getAttribute('data-lang')||'ko';[].forEach.call(ps.options,function(o){var t=o.getAttribute('data-'+l);if(t)o.textContent=t;});};
  lt();
  document.querySelectorAll('#lang button').forEach(function(x){x.addEventListener('click',function(){setTimeout(lt,0);});});
  ps.addEventListener('change',function(){var v=ps.value;if(v.indexOf('go')===0){var o=ps.options[ps.selectedIndex];if(window.wjGo){window.wjGo(o.getAttribute('data-go'));}else{location.href=o.getAttribute('data-href');}return;}if(v.indexOf('A:')===0||v==='cur')return;var bt2=document.querySelector('#tabs button[data-k="'+v+'"]');if(bt2)bt2.click();});
}
var g=document.getElementById('fxgear'),b=document.getElementById('fxbox');
if(g&&b){g.addEventListener('click',function(e){b.hidden=!b.hidden;g.setAttribute('aria-expanded',b.hidden?'false':'true');e.stopPropagation();});
  document.addEventListener('click',function(e){if(!b.hidden&&!b.contains(e.target)&&e.target!==g){b.hidden=true;g.setAttribute('aria-expanded','false');}});}
})();"""


_PAGE = {('journal', 'w'): 'journal', ('journal', 'm'): 'monthly', ('journal', 'y'): 'yearly',
         ('summary', 'w'): 'summary', ('summary', 'm'): 'msummary', ('summary', 'y'): 'ysummary', ('bep', 'm'): 'bep', ('store', 'm'): 'store'}


def _href(ent, kind, per, sfx=''):
    name = _PAGE[(kind, per)]
    if CFG['served']:
        return f'href="#" data-go="{name}_{ent}{sfx if per == "w" else ""}"'
    fname = {'journal': 'weekly_journal', 'monthly': 'weekly_monthly', 'yearly': 'weekly_yearly',
             'summary': 'weekly_summary', 'msummary': 'weekly_msummary', 'ysummary': 'weekly_ysummary', 'bep': 'weekly_bep', 'store': 'weekly_store'}[name]
    return f'href="{fname}_{ent}.html"'


def _tabper(active):
    if active == 'bep':
        return 'bep', 'm'
    if active == 'store':
        return 'store', 'm'
    tab = 'summary' if active in ('summary', 'msummary', 'ysummary') else 'journal'
    per = 'm' if active in ('monthly', 'msummary') else ('y' if active in ('yearly', 'ysummary') else 'w')
    return tab, per


def period_links(ent, per, tab='journal'):
    on = lambda k: 'on' if per == k else ''
    return (f'<a {_href(ent, tab, "w")} class="{on("w")}">{L("주간")}</a>'
            f'<a {_href(ent, tab, "m")} class="{on("m")}">{L("월간")}</a>'
            f'<a {_href(ent, tab, "y")} class="{on("y")}">{L("연간")}</a>')


def asof_html():
    st = CFG.get('status')
    badge = ''
    if not CFG['arch'] and st in ('draft', 'final'):
        ko, en = ('임시 숫자', 'Draft figures') if st == 'draft' else ('최종 숫자', 'Final figures')
        badge = f'<span class="stat {st}"><span class="ko">{ko}</span><span class="en">{en}</span><span class="zh">{STATUS_ZH[st]}</span></span>'
    return f'<span class="asof">{badge}<span>{L("데이터 기준")} {CFG["asof"]}</span></span>'


def _nav_hint(ent, kind):
    """다음에 열 가능성이 큰 화면(앞·뒤 주, 같은 주의 다른 탭)의 이름 목록 → 로더가 보는 동안 미리 받아 둔다. 주간 상세 일지·SUMMARY 만."""
    if not CFG.get('served') or kind not in ('journal', 'summary'):
        return ''
    top = int(CFG.get('top') or 0)
    m = re.match(r'@?W(\d+)', CFG.get('sfx') or (('@' + CFG['arch']) if CFG.get('arch') else ''))
    n = int(m.group(1)) if m else top
    if not top or not n:
        return ''
    if n != top:                         # 지난 주 보관본(더 이상 쓰지 않음)에서는 미리 받지 않는다
        return ''
    other = 'summary' if kind == 'journal' else 'journal'
    cand = [f'{other}_{ent}', f'bep_{ent}', f'monthly_{ent}' if kind == 'journal' else f'msummary_{ent}']
    return '<script>window.WJ_NAV=' + json.dumps(cand) + ';</script>'


def head_block(ent, kind, per, tabs='', acts=False, selkind=None, opts=None, brand=False):
    """kind: journal | summary | monthly | yearly,  per: w | m | y"""
    lc = 'HKD' if ent == 'HK' else 'TWD'
    h1 = f'<h1>{ent} {L("영업일지")}</h1>'
    nav = f'<div class="tabs nav">{nav_html(ent, kind)}</div>'
    sel = period_select(ent, selkind or kind, opts or [])
    tb = f'<div class="tabs" id="tabs" hidden>{tabs}</div>' if tabs else ''
    g_per = '' if kind in ('bep', 'store') else f'<div class="hg"><span class="gl">{L("기간")}</span><div class="tabs per">{period_links(ent, per, _tabper(kind)[0])}</div>{sel}{tb}</div>'
    if kind == 'bep':
        g_per = (f'<div class="hg"><span class="gl">{L("기간")}</span><div class="tabs per"><a class="on">{L("월간")}</a></div>'
                 + BEP_SEL + '</div>')
    if kind == 'store':
        g_per = ''
    fx = (f'<span class="pop"><button type="button" class="gear" id="fxgear" aria-expanded="false" aria-label="Exchange rate">&#9881;</button>'
          f'<div class="fxbox panelbox" id="fxbox" hidden><span class="ko">적용환율</span><span class="en">Rate</span><span class="zh">適用匯率</span> 1 {lc} = '
          f'<input id="fx" type="number" min="0.0001" step="0.1" value="{int(CUR_FX)}"> KRW '
          f'<button id="fxr"><span class="ko">초기화</span><span class="en">Reset</span><span class="zh">重設</span></button></div></span>')
    # 국가 선택(본사 계정 전용, 2026-10-08 오웬 요청): 같은 화면·같은 기간의 다른 법인 화면으로 이동. 본사가 아니면 숨김(JS 가 역할을 보고 연다)
    _sfx = CFG.get('sfx') or (('@' + CFG['arch']) if CFG.get('arch') else '')
    _oth = 'TW' if ent == 'HK' else 'HK'

    def _ent_a(e):
        if e == ent:
            return f'<a class="on">{e}</a>'
        pg = f'{kind}_{e}{_sfx}'
        return (f'<a href="#" data-go="{pg}">{e}</a>' if CFG['served'] else f'<a href="{_local_name(pg)}">{e}</a>')
    g_ent = (f'<div class="hg" id="entGrp"{' data-local="1"' if not CFG["served"] else ' hidden'}><span class="gl">{L("국가")}</span><div class="tabs" id="entsel">'
             + _ent_a('HK') + _ent_a('TW') + '</div></div>')
    g_brand = (f'<div class="hg"><span class="gl">{L("브랜드")}</span><div class="tabs brand" id="brand"><button class="on" data-b="ALL">{L("전체")}</button>'
               f'<button data-b="NG">NG</button><button data-b="MG">MG</button></div></div>') if brand else ''
    g_cur = (f'<div class="hg"><span class="gl">{L("통화")}</span><div class="tabs cur" id="cur"><button class="on" data-c="krw">KRW</button>'
             f'<button data-c="loc">{lc}</button></div>{fx}</div>')
    if kind == 'store':                 # 매장 화면: 통화 버튼은 언어 옆(부모 화면)에 두고, 안쪽 화면(iframe)을 조작한다
        g_cur = (f'<div class="hg"><span class="gl">{L("통화")}</span><div class="tabs cur" id="stCur"><button class="on" data-c="KRW" type="button">KRW</button>'
                 f'<button data-c="LOC" type="button">{lc}</button></div></div>')
    g_lang = ('<div class="hg"><span class="gl">' + L("언어") + '</span><div class="tabs lang" id="lang"><button class="on" data-l="ko">한글</button>'
              '<button data-l="en">EN</button><button data-l="zh">繁中</button></div></div>')
    g_act = ''
    if acts:
        g_act = ('<div class="hg"><div class="tabs" id="acts"><button type="button" id="bEdit"><span class="ko">편집</span><span class="en">Edit</span><span class="zh">編輯</span></button>'
                 '<button type="button" id="bSave"><span class="ko">저장</span><span class="en">Save</span><span class="zh">儲存</span></button>'
                 '<button type="button" id="bXls"><span class="ko">다운로드</span><span class="en">Download</span><span class="zh">下載</span></button></div>'
                 '<span id="st" class="st"></span></div>')
    toggle = f'<button type="button" class="barToggle" id="barToggle" aria-expanded="true">&#9776; {L("보기 설정")}</button>'
    return (f'<div class="hd">{h1}{nav}<div class="bar" id="bar">{toggle}{g_ent}{g_per}{g_brand}{g_cur}{g_lang}{g_act}{asof_html()}</div></div>\n'
            f'{status_banner()}{_nav_hint(ent, kind)}')


def nav_html(ent, active):
    """2줄: SUMMARY · 상세 일지. 현재 기간(주간/월간/연간)을 유지한 채 서로 오간다."""
    tab, per = _tabper(active)
    sfx = '@' + CFG['arch'] if (CFG['served'] and CFG['arch']) else ''
    return (f'<a {_href(ent, "summary", per, sfx)} class="{"on" if tab == "summary" else ""}">SUMMARY</a>'
            f'<a {_href(ent, "journal", per, sfx)} class="{"on" if tab == "journal" else ""}">{L("상세 일지")}</a>'
            f'<a {_href(ent, "bep", "m")} class="{"on" if tab == "bep" else ""}">BEP</a>'
            f'<a {_href(ent, "store", "m")} class="{"on" if tab == "store" else ""}">{L("매장")}</a>')


# 파이프라인 설정 (generate() 가 채운다)
CFG = dict(served=False, status='final', asof='', blank=False, api_url='', arch='', top=None, sfx='')
PAGES = {}


def loader_tag():
    return ('<script>' + LOADER_JS.replace('__API__', CFG['api_url']) + '</script>') if CFG['served'] else ''


def arch_cls():
    return ' arch' if CFG['arch'] else ''


MON_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def period_opts(label, mon, yr):
    """기간 선택 한 줄: (ko, en, zh). 주간 'W39 · 9/21–9/27', 월간 '9월 마감', 연간 '1월'"""
    if not (mon or yr):
        m = re.match(r'(\d+/\d+)~(\d+/\d+) \((W\d+)\)', label)
        t = f'{m.group(3)} · {m.group(1)}–{m.group(2)}' if m else label
        return t, t, t
    m = re.match(r'(\d+)월', label)
    n = int(m.group(1)) if m else 0
    if label.endswith('마감'):
        return f'{n}월 마감', f'{MON_EN[n - 1]} closed', f'{n}月 結算'
    mm = re.search(r'~(\d+/\d+)', label)
    tail = f' ~{mm.group(1)}' if mm else ''
    return f'{n}월{tail}', f'{MON_EN[n - 1]}{tail}', f'{n}月{tail}'


def period_select(ent, kind, opts):
    """상단 막대의 기간 선택 바(드롭다운). 로컬 옵션 + (서빙 모드) 지난 주 보관본은 화면이 열릴 때 서버에서 받아 덧붙인다."""
    if not opts or kind in ('yearly', 'ysummary'):
        return ''
    h = ''.join(f'<option value="{o[0]}" data-ko="{o[1]}" data-en="{o[2]}" data-zh="{o[3]}"{(" " + o[4]) if len(o) > 4 else ""}>{o[1]}</option>' for o in opts)
    static = ' data-static="1"' if (kind == 'journal' and opts and len(opts[0]) > 4 and 'data-go' in str(opts[0][4])) else ''
    return (f'<select id="perSel" class="wksel persel" data-kind="{kind}" data-ent="{ent}" data-arch="{CFG["arch"]}"{static} aria-label="period">{h}</select>')


def status_banner():
    """보관본(지난 주) 안내만 남긴다. 임시/최종 숫자 표시는 상단 막대의 '데이터 기준' 옆 배지로 이동."""
    if CFG['arch']:
        w = CFG['arch']
        return (f'<div class="stat arch"><b><span class="ko">보관본</span><span class="en">Archive</span><span class="zh">封存</span></b>'
                f'<span> · {w} · {CFG["asof"]}</span> <a href="#" data-go="__current__" class="cur-link">'
                f'<span class="ko">현재 화면으로</span><span class="en">Back to current</span><span class="zh">回到目前畫面</span></a></div>')
    return ''


# 페이지 이동 (서빙 모드): 로그인 토큰으로 서버에서 다음 페이지를 받아 문서를 통째로 바꾼다
LOADER_JS = """(function(){
var API='__API__';
/* 화면 미리 받아 두기 (2026-10-08): window 는 화면을 바꿔 써도(document.write) 그대로라서 받아 둔 화면이 다음 화면에도 남는다 */
var gen=(window.__wjGen=(window.__wjGen||0)+1);
window.__wjC=window.__wjC||{};
var TTL=900000,MAXC=8;
function tok(){var t='';try{t=localStorage.getItem('wj_tok_HK')||localStorage.getItem('wj_tok_TW')||'';}catch(e){}return t;}
function fetchPage(name){
  return fetch(API,{method:'POST',headers:{'Content-Type':'text/plain;charset=utf-8'},body:JSON.stringify({a:'page',name:name,token:tok()})}).then(function(r){return r.json();});
}
function keep(name,html){
  window.__wjC[name]={html:html,at:Date.now()};
  var ks=Object.keys(window.__wjC);
  if(ks.length>MAXC){ks.sort(function(a,b){return window.__wjC[a].at-window.__wjC[b].at;});delete window.__wjC[ks[0]];}
}
function show(html){document.open();document.write(html);document.close();window.scrollTo(0,0);}
window.wjGo=function(name){
  var c=window.__wjC[name];
  if(c&&Date.now()-c.at<TTL){show(c.html);return Promise.resolve();}
  return fetchPage(name).then(function(r){
      if(!r.ok){if(r.auth){location.reload();}else{alert(r.error||'error');}return;}
      keep(name,r.html);show(r.html);
    }).catch(function(){alert('서버에 연결하지 못했습니다.');});
};
(function(){
  var nav=(window.WJ_NAV||[]).slice();
  function pf(){
    if(gen!==window.__wjGen)return;                       // 다른 화면으로 넘어갔으면 이 화면의 미리 받기는 멈춘다
    var n=nav.shift();if(!n)return;
    var c=window.__wjC[n];
    if(c&&Date.now()-c.at<TTL){pf();return;}
    if(document.hidden){nav.unshift(n);setTimeout(pf,4000);return;}
    fetchPage(n).then(function(r){if(r&&r.ok)keep(n,r.html);}).catch(function(){}).then(function(){setTimeout(pf,2000);});
  }
  setTimeout(pf,3000);
})();
document.addEventListener('click',function(ev){
  var a=ev.target.closest&&ev.target.closest('a[data-go]');if(!a)return;
  ev.preventDefault();
  var g=a.getAttribute('data-go');
  if(g==='__current__'){var s0=document.getElementById('perSel');g=(s0.getAttribute('data-kind')+'_'+s0.getAttribute('data-ent'));}
  window.wjGo(g);
});
var PAST={ko:'── 지난 주 ──',en:'── Past weeks ──',zh:'── 過去週別 ──'};
function fillSel(){
  var sel=document.getElementById('perSel');if(!sel)return;
  var tk='';try{tk=localStorage.getItem('wj_tok_HK')||localStorage.getItem('wj_tok_TW')||'';}catch(e){}
  var kind=sel.getAttribute('data-kind'),ent=sel.getAttribute('data-ent');
  if(kind==='monthly'||kind==='yearly'||kind==='journal'||kind==='summary'||sel.getAttribute('data-static'))return;
  fetch(API,{method:'POST',headers:{'Content-Type':'text/plain;charset=utf-8'},body:JSON.stringify({a:'archive',token:tk})})
    .then(function(r){return r.json();}).then(function(r){
      if(!r.ok)return;
      var cur=sel.getAttribute('data-arch'),lg=document.body.getAttribute('data-lang')||'ko';
      var h='<option disabled data-ko="'+PAST.ko+'" data-en="'+PAST.en+'" data-zh="'+PAST.zh+'">'+PAST[lg]+'</option>',n=0;
      r.weeks.forEach(function(w){
        if(w.pages.indexOf(kind+'_'+ent+'@'+w.week)<0)return;
        var t=w.week+' · '+(w.asOf||'')+(w.closed[ent]?' 🔒':'');n++;
        h+='<option value="A:'+w.week+'" data-ko="'+t+'" data-en="'+t+'" data-zh="'+t+'"'+(w.week===cur?' selected':'')+'>'+t+'</option>';
      });
      if(n)sel.insertAdjacentHTML('beforeend',h);
    }).catch(function(){});
  sel.addEventListener('change',function(){
    var v=sel.value;
    if(v.indexOf('A:')===0){window.wjGo(kind+'_'+ent+'@'+v.slice(2));}
    else if(v==='cur'){window.wjGo(kind+'_'+ent);}
  });
}
fillSel();
})();"""


DEPT_CODE = {'GM': 'GM', '상품기획': 'MD', '영업': 'SALES', 'EC': 'EC', 'VMD': 'VMD', '마케팅': 'MKT', '물류': 'TRADE', 'HR': 'HR', '회계/재무': 'FIN'}


MON_HINT = ('<span class="ko">월간 부서별 일지는 주간 일지와 별개로 직접 작성합니다. 지난 달부터 이번 달까지 편집할 수 있습니다.</span>'
            '<span class="en">The monthly department journal is written on its own, separate from the weekly journals. The previous month and the current month can be edited.</span>'
            '<span class="zh">月報各部門日誌與週報分開，由負責人另行填寫。可編輯上個月與本月。</span>')
MON_NOTICE = ('<span class="ko">월간 숫자는 ERP 값입니다. 지난 달은 월 마감 기준, 최신 달은 최신 주 마감일까지의 월누계입니다. 부서별 일지는 주간 일지와 별개로 담당자가 직접 작성합니다. (주는 마감일이 속한 달에 넣습니다)</span>'
              '<span class="en">Monthly figures are ERP values: closed months at month-end, the latest month month-to-date up to the latest week-end. The department journal is written by the owners on its own, separate from the weekly journals. (Each week belongs to the month of its end date.)</span>'
              '<span class="zh">月度數字為 ERP 數值：已結束月份以月底為準，最新月份為截至最新週結束日的月累計。各部門月報由負責人另行填寫，與週報分開。（每週歸入其結束日所屬的月份）</span>')
MON_FOOT = ''
YR_NOTICE = ('<span class="ko">연간 화면은 1/1부터 기준일까지의 누계 한 장입니다. ERP 값이며 마감된 달은 월말까지, 마지막 달은 기준일까지 포함합니다. 부서별 일지는 월간 화면에서 작성합니다.</span>'
             '<span class="en">The yearly screen is one year-to-date page (Jan 1 to the as-of date), ERP values. Department journals are written on the monthly screen.</span>'
             '<span class="zh">年度畫面為 1/1 至基準日的累計單頁（ERP 數值）。部門日誌請至月報畫面填寫。</span>')


L_PLAIN = {'4주 비교': ('4주 비교', '4-week view', '4 週比較'), '4개월 비교': ('4개월 비교', '4-month view', '4 個月比較'),
           '연간 전체': ('연간 전체', 'Full year', '全年')}
SUM_CUR = ('이번 주 (최신)', 'This week (latest)', '本週（最新）')


def _closed(n):
    return n.endswith(' (폐점)')


BRAND_JS = '(function(){\nvar bar=document.getElementById(\'brand\');if(!bar)return;\nvar tables=document.querySelectorAll(\'table.xl\');var t1=tables[0],t2=tables[1];\nfunction mark(b){document.body.setAttribute(\'data-brand\',b);[].forEach.call(bar.querySelectorAll(\'button\'),function(x){x.classList.toggle(\'on\',x.getAttribute(\'data-b\')===b);});try{localStorage.setItem(\'wj_brand\',b);}catch(e){}}\nif(!t2){bar.addEventListener(\'click\',function(ev){var x=ev.target.closest(\'button\');if(x)mark(x.getAttribute(\'data-b\'));});var s0=\'ALL\';try{s0=localStorage.getItem(\'wj_brand\')||\'ALL\';}catch(e){}if(s0!==\'NG\'&&s0!==\'MG\')s0=\'ALL\';mark(s0);return;}\nfunction cells(tr){return [].filter.call(tr.cells,function(c){return c.hasAttribute(\'data-w\');});}\nfunction save(tr){cells(tr).forEach(function(c){if(!c.hasAttribute(\'data-o-t\')){c.setAttribute(\'data-o-t\',c.textContent);if(c.hasAttribute(\'data-loc\'))c.setAttribute(\'data-o-loc\',c.getAttribute(\'data-loc\'));}});}\nfunction restore(tr){cells(tr).forEach(function(c){if(c.hasAttribute(\'data-o-loc\'))c.setAttribute(\'data-loc\',c.getAttribute(\'data-o-loc\'));c.textContent=c.getAttribute(\'data-o-t\');});}\nfunction halves(cs){var blocks=[],cur=null,w=null;cs.forEach(function(c){var k=c.getAttribute(\'data-w\');if(k!==w){w=k;cur=[];blocks.push(cur);}cur.push(c);});var hs=[];blocks.forEach(function(blk){for(var i=0;i<blk.length;i+=5)hs.push(blk.slice(i,i+5));});return hs;}\nfunction fillSum(tr,rows){\n  var tc=halves(cells(tr)),rc=rows.map(function(r){return halves(cells(r));});\n  tc.forEach(function(h,hi){\n    var s=[0,0,0,0];\n    [0,1,3].forEach(function(j){var sum=0;rc.forEach(function(r){var c=r[hi]&&r[hi][j];if(c&&c.hasAttribute(\'data-loc\'))sum+=parseFloat(c.getAttribute(\'data-loc\'))||0;});h[j].setAttribute(\'data-loc\',String(sum));s[j]=sum;});\n    var ach=s[0]?s[1]/s[0]*100:null,yoy=s[3]?(s[1]/s[3]-1)*100:null;\n    h[2].textContent=ach===null?\'\\u2014\':ach.toFixed(1)+\'%\';\n    h[4].textContent=yoy===null?\'\\u2014\':(yoy>=0?\'+\':\'\')+yoy.toFixed(1)+\'%\';\n  });\n}\nfunction apply(b){\n  [].forEach.call(t2.querySelectorAll(\'tr\'),save);\n  var tt=t1&&t1.querySelector(\'tr.tt\');if(tt)save(tt);\n  t2.querySelectorAll(\'tr.st\').forEach(function(r){r.classList.toggle(\'bh\',b!==\'ALL\'&&r.getAttribute(\'data-brand\')!==b);});\n  t2.querySelectorAll(\'tr.oth\').forEach(function(r){r.classList.toggle(\'bh\',r.getAttribute(\'data-bv\')!==b);});\n  t2.querySelectorAll(\'tr.grp.tgl\').forEach(function(g){\n    var gi=g.getAttribute(\'data-g\');\n    var kids=[].filter.call(t2.querySelectorAll(\'tr.st[data-gm="\'+gi+\'"]\'),function(r){return !r.classList.contains(\'bh\');});\n    if(b===\'ALL\'){restore(g);g.classList.remove(\'bh\');}\n    else if(!kids.length){g.classList.add(\'bh\');}\n    else{g.classList.remove(\'bh\');fillSum(g,kids);}\n  });\n  var vis=[].filter.call(t2.querySelectorAll(\'tr.grp\'),function(r){return !r.classList.contains(\'bh\');});\n  if(tt){if(b===\'ALL\')restore(tt);else fillSum(tt,vis);}\n  if(window.wjApplyCur)window.wjApplyCur();\n  [].forEach.call(bar.querySelectorAll(\'button\'),function(x){x.classList.toggle(\'on\',x.getAttribute(\'data-b\')===b);});\n  mark(b);\n}\nbar.addEventListener(\'click\',function(ev){var x=ev.target.closest(\'button\');if(x)apply(x.getAttribute(\'data-b\'));});\nvar b0=\'ALL\';try{b0=localStorage.getItem(\'wj_brand\')||\'ALL\';}catch(e){}\nif(b0!==\'NG\'&&b0!==\'MG\')b0=\'ALL\';\napply(b0);\n})();'

PHOTO_ITEMS = ('vcomp', 'vthis')       # 사진을 올릴 수 있는 항목: 경쟁사 VMD, 금주 VMD (항목마다 최대 4장, 칸 이름 vcomp_p1~p4)
_PSD = os.path.dirname(os.path.abspath(__file__))
PS_CSS = open(os.path.join(_PSD, 'product_summary.css'), encoding='utf-8').read()
PS_JS = open(os.path.join(_PSD, 'product_summary.js'), encoding='utf-8').read()
CSS2 += PS_CSS
CSS2 += open(os.path.join(_PSD, 'journal_photo.css'), encoding='utf-8').read()
BRAND_JS += '\n' + PS_JS


def _rd_brand(n):
    import real_data as _r
    return _r.brand_of(n)


def _tab_tag(label):
    m = re.search(r'[WM]\d+', label)
    return m.group(0) if m else ''


def _tab_short(label):
    """상단 막대 기간 버튼에 쓰는 짧은 이름: 주간 = W36, 월간 = 9월, 연간 = 그대로 (긴 이름은 마우스를 올리면 title 로 보임)"""
    m = re.search(r'W\d+', label)
    if m:
        return m.group(0)
    m = re.match(r'(\d+월)\s*\(M\d+\)', label)
    return m.group(1) if m else label


ANN_CSS = ('.ann{border-collapse:collapse;font-size:12px;min-width:560px}.ann th,.ann td{border:1px solid #e5e7eb;padding:6px 10px;text-align:right}'
           '.ann th{background:#f3f4f6;font-weight:600;color:#4b5563}.ann td.lb,.ann th.lb{text-align:left;min-width:150px}'
           '.ann tr.tot td{background:#111;color:#fff;font-weight:700}.ann td.pc{background:#eaf1ff;font-weight:700}.ann td.rm{color:#6b7280}'
           '.ann caption{text-align:left;padding:0 0 6px}.ann caption h2{display:inline;font-size:15px;margin:0}.ann caption small{color:#6b7280;margin-left:6px}')


def annual_target_block(ent, groups, data):
    """연간 화면 맨 위: 연간 전체 목표(ERP 월판매목표 원장, 폐점 매장 목표 포함) 대비 지금까지 누계 달성 (2026-10-12 오웬 요청).
    목표 = fact_target_ledger 의 올해 연간 합, 누계 매출 = 아래 표와 같은 원장 값. 브랜드 선택과 무관하게 전체 기준."""
    import real_data as rd
    import db_wait
    srcs = ['HK', 'MC'] if ent == 'HK' else ['TW']
    year = 2026
    con = db_wait.connect_wait(os.path.join(rd.ROOT, 'erp_warehouse.duckdb'), read_only=True, max_wait_min=10, tag=' annual_target')
    try:
        rows = []
        for s in srcs:
            for nm, tot in con.execute("SELECT shop_nm, tot FROM fact_target_ledger WHERE ent_code=? AND biz_year=?", [s, year]).fetchall():
                rows.append((nm, (tot or 0.0) * rd.FX[s] / 1e6))
    finally:
        con.close()
    active = {r[0] for _g, rs in groups for r in rs}
    EXCL = ('B2B', 'EMPLOYEE', 'DEFECTIVE', 'MARKETING')
    tgt = {}
    for nm, v in rows:
        n0 = nm.replace(' (Closure)', '').strip()
        if nm in active:
            k = nm
        elif n0 in active:
            k = n0
        elif any(x in nm.upper() for x in EXCL):
            k = '기타'
        else:
            k = n0 + ' (폐점)'
        tgt[k] = tgt.get(k, 0.0) + v
    d = data[-1]
    tot_t = sum(tgt.values())
    tot_a = sums(list(d.values()))[4]

    def row(label, t, a, cls=''):
        pc = f'{a / t * 100:.1f}%' if t >= 0.5 else '&mdash;'          # 목표가 없는 줄(기타 등)은 % 대신 —
        rem = max(t - a, 0.0) if t >= 0.5 else None
        return (f'<tr class="{cls}"><td class="lb">{label}</td>{_nc(t)}{_nc(a)}<td class="pc">{pc}</td>'
                f'<td class="rm" data-loc="{(rem or 0) * 1000 / CUR_FX:.4f}">{fmt(rem)}</td></tr>')

    body = row(B('전체', 'Total', '合計'), tot_t, tot_a, 'tot')
    used = 0.0
    for gname, rs in groups:
        if gname == '기타':
            continue
        t = sum(tgt.get(r[0], 0.0) for r in rs)
        a = sums([d[r[0]] for r in rs])[4]
        used += t
        body += row(L(gname), t, a)
    oth_a = d['기타'][4] if '기타' in d else 0.0
    oth_t = tot_t - used
    if abs(oth_t) < 0.5:
        oth_t = 0.0                                  # 부동소수 찌꺼기(-0)는 0 으로
    if oth_t or abs(oth_a) >= 0.5:
        body += row(B('기타 (B2B·직원구매 등)', 'Other (B2B, employee purchase, etc.)', '其他（B2B・員工購買等）'), oth_t, oth_a)
    head = ('<tr><th class="lb">' + L('구분') + '</th>'
            f'<th>{B("연간 목표", "Annual target", "全年目標")}</th><th>{B("누계 매출", "YTD sales", "累計銷售")}</th>'
            f'<th>{B("연간 달성률", "% of annual", "全年達成率")}</th><th>{B("남은 목표", "Remaining", "剩餘目標")}</th></tr>')
    cap = (f'<caption><h2>{B("연간 전체 목표 대비", "Against the full-year target", "全年目標達成")}</h2>'
           f'<small>{B("ERP 월판매목표 기준 (폐점 매장 목표 포함) &middot; 단위 백만원(KRW) &middot; 브랜드 선택과 무관하게 전체", "ERP monthly sales targets (incl. closed stores) &middot; KRW million &middot; all brands", "ERP 月銷售目標（含結束營業門市）・百萬韓元・全品牌")}</small></caption>')
    return f'<style>{ANN_CSS}</style><table class="ann">{cap}{head}{body}</table>'


def build(ent, groups, weeks_meta, texts, submits, real=None, monthly=None):
    global CUR_FX
    CUR_FX = 185.0 if ent == 'HK' else 46.0
    mon = monthly is not None
    yr = bool(monthly and monthly.get('year'))
    n = len(weeks_meta)
    if mon:
        data = monthly['data']
    elif real:
        groups, data = real
        import real_data as _rd
        _ws = _rd.WLY_STORE.get(ent, {})
        _data2 = []
        for _i, _d in enumerate(data):
            _m = _ws.get(_rd.WEEKS[_i], {})
            _data2.append(_rd.wk_like(_d, {_nm: (_v[0], _v[1], _m.get(_nm, None), _v[3], _v[4], _v[5]) for _nm, _v in _d.items()}))
        data = _data2
    else:
        data = make_weeks(groups, n, 7 if ent == 'HK' else 11)
    HW = L("월간실적") if mon else L("주간실적")
    HALVES = (1,) if yr else (0, 1)
    CPW = 5 * len(HALVES)                      # 한 기간이 차지하는 열 수
    ncol = 1 + CPW * n
    ORDER = list(range(n))                # 화면 순서: 오래된 주 → 최신 주
    colg = '<colgroup><col style="width:150px">' + ''.join(
        ''.join(f'<col data-w="{i}" style="width:54px">' for _ in range(CPW)) for i in ORDER) + '</colgroup>'

    def full_head():
        h1 = '<tr><th class="lb" rowspan="3">' + L('구분') + '</th>'
        h2 = '<tr>'
        h3 = '<tr>'
        for i, wm in [(k_, weeks_meta[k_]) for k_ in ORDER]:
            cur = 'cur' if i == n - 1 else ''
            h1 += f'<th data-w="{i}" class="wk wstart {cur}" colspan="{CPW}">{wm["label"]}</th>'
            if not yr:
                h2 += f'<th data-w="{i}" class="hw wstart" colspan="5">{HW}</th>'
            h2 += f'<th data-w="{i}" class="hy ystart" colspan="5">{L("누계 (YTD)")}</th>'
            for half in HALVES:
                for j, nm in enumerate(['목표', '매출', '달성률', '전년', '전년비']):
                    cls = ('sy' if half else 'sw') + (' ystart' if (half and j == 0) else '') + (' wstart' if (not half and j == 0) else '') + (' ach' if j == 2 else '') + (' gr' if j == 4 else '')
                    h3 += f'<th data-w="{i}" class="{cls}">{L(nm)}</th>'
        return h1 + '</tr>' + h2 + '</tr>' + h3 + '</tr>'

    def slim_head():
        h = '<tr><th class="lb">' + L('구분') + '</th>'
        for i, wm in [(k_, weeks_meta[k_]) for k_ in ORDER]:
            cur = 'cur' if i == n - 1 else ''
            h += f'<th data-w="{i}" class="wk wstart {cur}" colspan="10">{wm["label"]}</th>'
        return h + '</tr>'

    # 1. 이번주 실적
    t1 = f'<table class="xl"><caption><h2>{L("1. 연간 실적") if yr else (L("1. 이번달 실적") if mon else L("1. 이번주 실적"))} <small>{L("실제 ERP 값 (최신 주 기준)")} &middot; <span class="unitcap"><span class="ko">단위 백만원(KRW)</span><span class="en">Unit: KRW million</span><span class="zh">單位：百萬韓元(KRW)</span></span></small></h2></caption>{colg}{full_head()}<tr class="tt"><td class="lb">Total</td>'
    for i, w in [(k_, data[k_]) for k_ in ORDER]:
        t1 += wcells(sums(list(w.values())), i, HALVES)
    t1 += '</tr></table>'

    # 2. 유통별 실적
    body = ''
    for gi, (gname, rows) in enumerate(groups):
        if gname == '기타':
            _olab = B("기타 (B2B&middot;직원구매 등)", "Other (B2B, employee purchase, etc.)")
            body += f'<tr class="grp oth" data-bv="ALL"><td class="lb">{_olab}</td>'
            for i, w in [(k_, data[k_]) for k_ in ORDER]:
                body += wcells(w[rows[0][0]], i, HALVES)
            body += '</tr>'
            if all(getattr(data[k_], 'other_by_brand', None) for k_ in ORDER):          # 브랜드별 기타 (필터용, 처음엔 숨김)
                for _b in ('NG', 'MG'):
                    body += f'<tr class="grp oth bh" data-bv="{_b}"><td class="lb">{_olab}</td>'
                    for i, w in [(k_, data[k_]) for k_ in ORDER]:
                        body += wcells(w.other_by_brand[_b], i, HALVES)
                    body += '</tr>'
            continue
        body += f'<tr class="grp tgl" data-g="{gi}"><td class="lb"><span class="car">&#9662;</span>{L(gname)}</td>'
        for i, w in [(k_, data[k_]) for k_ in ORDER]:
            body += wcells(sums([w[r[0]] for r in rows]), i, HALVES)
        body += '</tr>'
        for r in rows:
            _cl = _closed(r[0])
            if r[0] == '전년 보정 (폐점)':
                _lab = B('폐점 매장 전년 보정', 'Closed stores LY adjustment', '結束營業門市去年補正')
            else:
                _lab = (r[0][:-5].strip() + ' ' + B('(폐점)', '(closed)', '(結束營業)')) if _cl else (L(r[0]) if r[0] in LABELS else r[0])
            body += f'<tr class="st{" cl" if _cl else ""}" data-gm="{gi}" data-brand="{_rd_brand(r[0])}"><td class="lb">{_lab}</td>'
            for i, w in [(k_, data[k_]) for k_ in ORDER]:
                body += wcells(w[r[0]], i, HALVES)
            body += '</tr>'
    t2 = f'<table class="xl"><caption><h2>{L("2. 유통별 실적")} <small>{L("실제 ERP 값")}</small><span class="fold"><button type="button" data-t="g" data-f="open">{L("모두 펼치기")}</button><button type="button" data-t="g" data-f="close">{L("모두 접기")}</button></span></h2></caption>{colg}{full_head()}{body}</table>'

    # 3. 부서별 일지
    days = ['월', '화', '수', '목', '금', '토', '일']

    def gap():
        return f'<tr class="gap"><td class="lb"></td><td colspan="{ncol - 1}" data-span></td></tr>'

    b3 = ''
    _tall = [t[0] for w_ in weeks_meta for t in w_['temps']] + [t[1] for w_ in weeks_meta for t in w_['temps']] or [0]
    _tlo, _thi = min(_tall) - 4, max(_tall) + 1                  # 막대 기준선은 최저값보다 4도 아래
    _rmax = max([10.0] + [r_ for w_ in weeks_meta for r_ in w_['rain']])   # 강수량 축은 최소 10mm

    def _bar(cls, pct):
        return f'<div class="bw"><i class="{cls}" style="height:{max(pct, 0):.1f}%"></i></div>'

    def _seg(cls, vals, i, lo, hi):
        def _ypct(v):
            return 8 + (v - lo) / max(hi - lo, 1) * 84
        y = _ypct(vals[i])
        yp = (_ypct(vals[i - 1]) + y) / 2 if i > 0 else y
        yn = (_ypct(vals[i + 1]) + y) / 2 if i < len(vals) - 1 else y
        d = f'M0 {100 - yp:.1f} L50 {100 - y:.1f} L100 {100 - yn:.1f}'
        return (f'<div class="bw ln"><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
                f'<path d="{d}" class="{cls}" vector-effect="non-scaling-stroke"/></svg>'
                f'<i class="dot {cls}" style="bottom:calc({y:.1f}% - 3px)"></i></div>')

    def _dn(wi_, k_):
        try:
            m0 = re.match(r'(\d+)/(\d+)', weeks_meta[wi_]['label'])
            y_ = datetime.date.today().year
            d0 = datetime.date(y_, int(m0.group(1)), int(m0.group(2))) + datetime.timedelta(days=k_)
            return f'{d0.month}/{d0.day}'
        except Exception:
            return ''

    b3 += '' if mon else '<tr class="wx dayrow"><td class="lb"></td>'
    for wi in ([] if mon else ORDER):
        b3 += f'<td class="tx wstart" data-w="{wi}" colspan="10"><div class="tp">' + ''.join(
            f'<span data-ko="{d}" data-en="{DAYS[d]}" data-zh="{DAYS_ZH[d]}"><i class="dn">{_dn(wi, k_)}</i></span>' for k_, d in enumerate(days)) + '</div></td>'
    b3 += '' if mon else '</tr>'
    for label, idx, cls in (() if mon else (('최고온도', 0, 'lh'), ('최저온도', 1, 'll'))):
        _all = [tv[idx] for w_ in weeks_meta for tv in w_['temps']]
        _lo, _hi = min(_all), max(_all)      # 줄마다 자기 범위(4주)로 눈금을 잡아 오르내림이 보이게 함
        b3 += f'<tr class="wx"><td class="lb" style="vertical-align:top">{L(label)}</td>'
        for wi in ORDER:
            vals = [tv[idx] for tv in weeks_meta[wi]['temps']]
            b3 += f'<td class="tx wstart" data-w="{wi}" colspan="10"><div class="tp">' + ''.join(
                f'<span data-ko="{d}" data-en="{DAYS[d]}" data-zh="{DAYS_ZH[d]}">{_seg(cls, vals, k, _lo, _hi)}<b>{vals[k]}&deg;</b></span>'
                for k, d in enumerate(days)) + '</div></td>'
        b3 += '</tr>'
    def _wicon(code):
        c = int(code)
        if c == 0: return '\u2600\ufe0f', '맑음', 'Clear'
        if c == 1: return '\U0001F324\ufe0f', '대체로 맑음', 'Mostly clear'
        if c == 2: return '\u26C5', '구름 조금', 'Partly cloudy'
        if c == 3: return '\u2601\ufe0f', '흐림', 'Overcast'
        if c in (45, 48): return '\U0001F32B\ufe0f', '안개', 'Fog'
        if c in (51, 53, 55, 80): return '\U0001F326\ufe0f', '약한 비', 'Light rain'
        if c in (56, 57, 61, 63, 65, 66, 67, 81, 82): return '\U0001F327\ufe0f', '비', 'Rain'
        if c in (71, 73, 75, 77, 85, 86): return '\U0001F328\ufe0f', '눈', 'Snow'
        if c in (95, 96, 99): return '\u26C8\ufe0f', '뇌우', 'Thunderstorm'
        return '\u2601\ufe0f', '흐림', 'Overcast'

    b3 += '' if mon else f'<tr class="wx"><td class="lb" style="vertical-align:middle">{L("날씨")}</td>'
    for wi in ([] if mon else ORDER):
        cells_ = ''
        for k, d in enumerate(days):
            ic, ko_, en_ = _wicon(weeks_meta[wi]['wcode'][k])
            rv = weeks_meta[wi]['rain'][k]
            mm = f'{rv:.1f}mm' if rv >= 0.05 else '0mm'
            cells_ += (f'<span data-ko="{d}" data-en="{DAYS[d]}" data-zh="{DAYS_ZH[d]}" title="{ko_} / {en_} / {WEATHER_ZH.get(ko_, en_)} ({mm})"><em class="wi">{ic}</em>'
                       f'<b class="wl"><span class="ko">{ko_}</span><span class="en">{en_}</span><span class="zh">{WEATHER_ZH.get(ko_, en_)}</span></b></span>')
        b3 += f'<td class="tx wstart" data-w="{wi}" colspan="10"><div class="tp">{cells_}</div></td>'
    b3 += '' if mon else '</tr>'
    for di, (dname, items) in enumerate(DEPTS):
        b3 += gap()
        b3 += f'<tr class="tgl" data-d="{di}"><td class="lb dept"><span class="car">&#9662;</span>{L(dname)}</td>'
        for i in ORDER:
            b3 += f'<td class="dp wstart" data-w="{i}" colspan="10"></td>'
        b3 += '</tr>'
        for label, key, kind in items:
            lbcls = 'lb ' + (kind if kind in ('good', 'bad') else '')
            _ik = 'strat' if label == '향후전략' else key
            b3 += f'<tr data-dm="{di}" data-dk="{DEPT_CODE.get(dname, dname)}" data-ik="{_ik}"><td class="{lbcls}" style="vertical-align:top;padding-left:14px">{L(label)}</td>'
            for wi, t in [(k_, texts[k_]) for k_ in ORDER]:
                v = t.get(key, '' if CFG['blank'] else DEFAULT.get(key, '해당 없음'))
                _pho = '<div class="pho"></div>' if (key in PHOTO_ITEMS and not mon and not yr) else ''     # VMD 사진 올리기 칸 (JS 가 채움)
                b3 += f'<td class="tx {kind} wstart" data-w="{wi}" colspan="10">{BI(v) if v else '<div class="ko"></div><div class="en"></div><div class="zh"></div>'}{_pho}</td>'
            b3 += '</tr>'
    t3 = f'<table class="xl"><caption><h2>{L("3. 월간 일지") if mon else L("3. 부서별 일지")} <small>{MON_HINT if mon else ('' if CFG['served'] else L("샘플 문구"))}</small><span class="fold"><button type="button" data-t="d" data-f="open">{L("모두 펼치기")}</button><button type="button" data-t="d" data-f="close">{L("모두 접기")}</button></span></h2></caption>{colg}{slim_head()}{b3}</table>'

    RECENT = 4 if (mon and not yr and len(ORDER) > 4) else len(ORDER)      # 월간: 기본 화면은 최근 4개월 (옛 달이 왼쪽에 반쯤 잘려 보이지 않게)
    tabs = '<button class="on" data-k="all">' + (L('연간 전체') if yr else (L('4개월 비교') if mon else L('4주 비교'))) + '</button>' + (
        f'<button data-k="full">{L("올해 전체")}</button>' if (FULL_YEAR_OPTION and RECENT < len(ORDER)) else '') + ''.join(
        f'<button data-k="{i}" data-tag="{_tab_tag(wm["label"])}" title="{wm["label"]}">{_tab_short(wm["label"])}</button>' for i, wm in [(k_, weeks_meta[k_]) for k_ in ORDER])

    _all = L_PLAIN['연간 전체'] if yr else (L_PLAIN['4개월 비교'] if mon else L_PLAIN['4주 비교'])
    _first, _last = weeks_meta[ORDER[0]]['label'], weeks_meta[ORDER[-1]]['label']
    if yr:
        _rng = _rng_en = _rng_zh = ''
    elif not mon:
        _rng = ' · ' + re.search(r'W\d+', _first).group(0) + '–' + re.search(r'W\d+', _last).group(0)
        _rng_en = _rng_zh = _rng
    else:
        _a, _b = int(re.match(r'(\d+)', _first).group(1)), int(re.match(r'(\d+)', _last).group(1))
        _a_r = int(re.match(r'(\d+)', weeks_meta[ORDER[-RECENT]]['label']).group(1)) if RECENT < len(ORDER) else _a        # 최근 4개월의 첫 달
        _rng, _rng_en, _rng_zh = f' · {_a_r}–{_b}월', f' · {MON_EN[_a_r - 1]}–{MON_EN[_b - 1]}', f' · {_a_r}–{_b}月'
    opts = [('all', _all[0] + _rng, _all[1] + _rng_en, _all[2] + _rng_zh)]
    if FULL_YEAR_OPTION and mon and not yr and RECENT < len(ORDER):
        opts.append(('full', f'올해 전체 · {_a}–{_b}월', f'Whole year · {MON_EN[_a - 1]}–{MON_EN[_b - 1]}', f'全年 · {_a}–{_b}月'))
    opts += [(str(i),) + period_opts(weeks_meta[i]['label'], mon, yr) for i in reversed(ORDER)]
    if CFG['served'] and not mon and not yr and PAST_WEEK_PICKER:
        _pn = int(re.search(r'W(\d+)', weeks_meta[-1]['label']).group(1))
        _top = int(CFG.get('top') or _pn)
        if CFG.get('arch'):                                       # 지난 주 보관본 화면: 최신 포함 전체 목록(이동용)
            opts = _week_pick_opts(ent, _pn)
        elif _top - 4 >= 5:                                       # 최신 화면: 4주 안은 즉시 이동 + 그 아래 지난 주 목록
            opts = opts + _week_pick_opts(ent, _pn, start=_top - 4, header=True)
    if yr:
        opts, tabs = [], ''
    MON_JSON = json.dumps(monthly['wbm_tags'], separators=(',', ':')) if mon else 'null'
    summ = '' if mon else make_summary_brands(ent, data, groups, weeks_meta, texts[-1])
    html = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{ent} {"연간영업일지" if yr else ("월간영업일지" if mon else "주간영업일지")}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<style>{CSS}{EXTRA_CSS}{CSS2}{HDR_CSS}{CHART_CSS}</style></head><body data-lang="ko" class="wj{arch_cls()}">
{head_block(ent, 'yearly' if yr else ('monthly' if mon else 'journal'), 'y' if yr else ('m' if mon else 'w'), tabs, acts=not yr, selkind='yearly' if yr else ('monthly' if mon else 'journal'), opts=opts, brand=True)}
<div class="ntc">{YR_NOTICE if yr else MON_NOTICE if mon else '<span class="ko">실적 표와 SUMMARY 1~4는 실제 ERP 값(최신 주 기준)입니다. 부서별 일지와 SUMMARY 5~7은 담당자가 작성한 내용입니다. 기온·날씨는 Open-Meteo 실측값(홍콩·타이베이)입니다.</span><span class="en">' + LABELS["NOTICE"] + '</span><span class="zh">' + ZH_LABELS["NOTICE"] + '</span>'}</div>
<div class="scroll" id="sc">
{"<div class=\"blk\">" + annual_target_block(ent, groups, data) + "</div>" if yr else ""}
<div class="blk">{t1}</div>
<div class="blk">{t2}</div>
{"" if yr else "<div class=\"blk\">" + t3 + "</div>"}
</div>
<div class="foot">{MON_FOOT if mon else ""}<span class="ko">{"" if mon else "주간 전년 = 전년 동주 매출 추정치 (ERP 누계 전년 값의 주간 증가분, 매장코드 변경 등으로 개별 매장은 왜곡될 수 있음) &middot; 누계 전년 = ERP 누계 전년 (매장코드 변경 등으로 일부 매장은 0일 수 있음) &middot; 누계 목표 = 월별 계획을 마감일까지 일할 누계 &middot; 폐점&middot;기타 = 폐점, B2B, 직원구매 매장 합계"}</span><span class="en">{"" if mon else LABELS["METH"]}</span><span class="zh">{"" if mon else ZH_LABELS["METH"]}</span></div>
<script>window.MON={MON_JSON};</script>
<script>
var N={n},RC={RECENT},sc=document.getElementById('sc'),btns=document.querySelectorAll('#tabs button');
function show(k){{
  document.querySelectorAll('[data-w]').forEach(function(e){{var w=e.getAttribute('data-w');e.style.display=(k==='full'||(k==='all'&&(+w>=N-RC))||w===k)?'':'none';}});
  var v=(k==='full')?N:((k==='all')?Math.min(RC,N):1);
  document.querySelectorAll('table.xl').forEach(function(t){{t.style.width=(150+540*v)+'px';}});
  document.querySelectorAll('[data-span]').forEach(function(e){{e.colSpan=10*v;}});
  btns.forEach(function(b){{b.classList.toggle('on',b.getAttribute('data-k')===k);}});
  sc.scrollLeft=(k==='all'||k==='full')?sc.scrollWidth:0;
}}
btns.forEach(function(b){{b.addEventListener('click',function(){{show(b.getAttribute('data-k'));}});}});
show('all');
var lb=document.querySelectorAll('#lang button');
function setLang(l){{
  document.body.setAttribute('data-lang',l);document.documentElement.lang=l;
  lb.forEach(function(b){{b.classList.toggle('on',b.getAttribute('data-l')===l);}});
  try{{localStorage.setItem('wj_lang',l);}}catch(e){{}}
}}
lb.forEach(function(b){{b.addEventListener('click',function(){{setLang(b.getAttribute('data-l'));}});}});
var sv='ko';try{{sv=localStorage.getItem('wj_lang')||'ko';}}catch(e){{}}
setLang(sv);
</script>
<script>{cur_js(ent)}</script>
<script>{HDR_JS}</script>
<script>{FOLD_JS}</script>
<script>{BRAND_JS}</script>
<script>{CHART_JS}</script>
{"" if yr else '<script>' + EDIT_JS.replace('__ENT__', ent).replace('__API__', CFG['api_url']) + '</script>'}
{loader_tag()}
</body></html>'''
    PAGES[('yearly_' if yr else ('monthly_' if mon else 'journal_')) + ent] = html
    if mon:
        return ent

    sum_html = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{ent} SUMMARY</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<style>{CSS}{EXTRA_CSS}{CSS2}{HDR_CSS}</style></head><body data-lang="ko" class="sumpage{arch_cls()}">
{head_block(ent, 'summary', 'w', '', False, 'summary', brand=True, opts=_week_opts(ent, int(re.search(r'W(\d+)', weeks_meta[-1]['label']).group(1)), None))}
<div class="ntc"><span class="ko">실적 표와 SUMMARY 1~4는 실제 ERP 값(최신 주 기준)입니다. 부서별 일지와 SUMMARY 5~7은 담당자가 작성한 내용입니다. 기온·날씨는 Open-Meteo 실측값(홍콩·타이베이)입니다.</span><span class="en">{LABELS["NOTICE"]}</span><span class="zh">{ZH_LABELS["NOTICE"]}</span></div>
{summ}
<div class="gol"><a href="{"#" if CFG["served"] else "weekly_journal_" + ent + ".html"}" data-go="journal_{ent}"><span class="ko">상세 일지 보기 &rarr;</span><span class="en">View detailed journal &rarr;</span><span class="zh">查看詳細日誌 &rarr;</span></a></div>
<script>{LANG_JS}</script>
<script>{cur_js(ent)}</script>
<script>{HDR_JS}</script>
<script>{BRAND_JS}</script>
{loader_tag()}
</body></html>'''
    PAGES['summary_' + ent] = sum_html
    return ent


def generate(latest, api_url='', served=False, status='final', blank=True, asof=None, out_dir=None, only=None, arch='', top=None, nweeks=4):
    """latest 주차까지 4주 화면을 만든다. 반환: {페이지 이름: html}. out_dir 가 있으면 파일로도 저장한다."""
    import datetime
    import real_data as rd
    rd.WEEKS[:] = list(range(latest - nweeks + 1, latest + 1))      # 보관본을 한 주만 담으면(nweeks=1) 화면이 가벼워진다
    CFG.update(served=served, status=status, blank=blank, api_url=api_url, arch=arch, top=top or latest,
               asof=asof or datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    PAGES.clear()
    import weather
    for ent, wm_src, tx_src, sub in (('HK', HK_WEEKS, HK_T, HK_SUB), ('TW', TW_WEEKS, TW_T, TW_SUB)):
        if only and ent not in only:
            continue
        groups, wd, raws, wly = rd.load_entity(ent)
        WLYD[ent] = wly
        EXTRAS[ent] = rd.extras(ent)
        EXTRAS_B[(ent, 'ALL')] = EXTRAS[ent]
        for _b in ('NG', 'MG'):
            EXTRAS_B[(ent, _b)] = rd.extras(ent, _b)
        wm = [dict(label='', submit='', temps=[], rain=[], wcode=[]) for _ in rd.WEEKS]
        for m_, w_ in zip(wm, rd.WEEKS):
            cs, ce = raws[w_]['cutoff_start'], raws[w_]['cutoff_end']
            _st = datetime.datetime.strptime(cs, '%Y%m%d').date() + datetime.timedelta(days=1)   # 주 시작(월요일)
            m_['label'] = f"{_st.month}/{_st.day}~{int(ce[4:6])}/{int(ce[6:8])} (W{w_})"
        start = datetime.datetime.strptime(raws[rd.WEEKS[0]]['cutoff_start'], '%Y%m%d').date() + datetime.timedelta(days=1)
        end = datetime.datetime.strptime(raws[rd.WEEKS[-1]]['cutoff_end'], '%Y%m%d').date()
        wx = weather.fetch(ent, start, end)
        for i_, m_ in enumerate(wm):
            sl = slice(7 * i_, 7 * i_ + 7)
            m_['temps'] = [(round(a), round(b)) for a, b in zip(wx['tmax'][sl], wx['tmin'][sl])]
            m_['rain'] = [float(x or 0) for x in wx['rain'][sl]]
            m_['wcode'] = [int(x if x is not None else 3) for x in wx['code'][sl]]
        texts = [dict() for _ in rd.WEEKS] if blank else tx_src
        build(ent, groups, wm, texts, sub, real=(groups, wd))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        for name, html in PAGES.items():
            kind, ent = name.split('_')
            with open(os.path.join(out_dir, f'weekly_{kind}_{ent}.html'), 'w', encoding='utf-8') as f:
                f.write(html)
    return dict(PAGES)


SUM_NOTICE = {
    'w': ('<span class="ko">주간 SUMMARY의 1~3은 ERP 일별 원장 값입니다(지난 주 숫자 요약). 상품 실적(4)과 담당자 글 요약(5~7)은 그 주에 저장한 경우에만 있습니다.</span>'
          '<span class="en">Parts 1 to 3 of this past-week SUMMARY are ERP daily-ledger values. Product results (4) and the owners\' journal summary (5 to 7) exist only if saved that week.</span>'
          '<span class="zh">過去週別摘要的第 1～3 項為 ERP 每日帳本數值。商品實績（4）與負責人日誌摘要（5～7）僅在當週有保存時才有。</span>'),
    'm': ('<span class="ko">월간 SUMMARY의 1~3은 ERP 일별 원장 값입니다. 지난 달은 월 마감, 최신 달은 기준일까지의 월누계입니다. 5~7은 담당자가 월간 일지에 저장한 글입니다.</span>'
          '<span class="en">Parts 1 to 3 of the monthly SUMMARY are ERP daily-ledger values: closed months at month-end, the latest month month-to-date. Parts 5 to 7 are what the owners saved in the monthly journal.</span>'
          '<span class="zh">月報摘要第 1～3 項為 ERP 每日帳本數值：已結束月份以月底為準，最新月份為月累計。第 5～7 項為負責人在月報日誌中儲存的內容。</span>'),
    'y': ('<span class="ko">연간 SUMMARY의 1~3은 1/1부터 기준일까지의 ERP 일별 원장 값입니다. 상품 실적(4)과 담당자 글 요약(5~7)은 준비 중입니다.</span>'
          '<span class="en">Parts 1 to 3 of the yearly SUMMARY are ERP daily-ledger values from Jan 1 to the as-of date. Product results (4) and the owners\' journal summary (5 to 7) are coming soon.</span>'
          '<span class="zh">年度摘要第 1～3 項為 1/1 至基準日的 ERP 每日帳本數值。商品實績（4）與負責人日誌摘要（5～7）準備中。</span>')}


def _local_name(page):
    """'msummary_TW@M08' → 'weekly_msummary_TW_M08.html'"""
    return 'weekly_' + page.replace('@', '_') + '.html'


def _go_opt(idx, page, ko, en, zh, selected=False):
    href = _local_name(page)
    return (f'go{idx}', ko, en, zh, f'data-go="{page}" data-href="{href}"' + (' selected' if selected else ''))


FULL_YEAR_OPTION = False     # 월간 화면의 '올해 전체' 선택 (오웬 2026-10-08: 연간 화면이 따로 있어 뺌)
PAST_WEEK_PICKER = True      # 최신 4주는 화면 안에서 즉시 이동, 그 아래 '지난 주' 목록은 그 주 보관본(한 주짜리)으로 이동 (2026-10-08 오웬: 지난 주도 보여 주기로)


def _wk_range(year, n):
    """ISO 주차 n → '9/21–9/27' (월~일)"""
    import datetime
    a = datetime.date.fromisocalendar(year, n, 1)
    b = datetime.date.fromisocalendar(year, n, 7)
    return f'{a.month}/{a.day}\u2013{b.month}/{b.day}'


def _week_pick_opts(ent, page_n, start=None, header=False):
    """상세 일지 '지난 주' 목록(서빙 모드): W{start}~W5 를 골라서 그 주 보관본으로 이동. 보관본은 W5 부터 있다(4주 표가 필요해서).
    start=None 이면 최신 주부터(보관본 화면용), header=True 면 '── 지난 주 ──' 구분 줄을 맨 앞에 둔다."""
    top = int(CFG.get('top') or page_n)
    try:
        year = int(str(CFG.get('asof') or '')[:4])
    except ValueError:
        year = 2026
    if year < 2000:
        year = 2026
    opts = [('hdr', '── 지난 주 ──', '── Past weeks ──', '── 過去週別 ──', 'disabled')] if header else []
    for k, n in enumerate(range(top if start is None else start, 4, -1)):
        pg = f'journal_{ent}' if n == top else f'journal_{ent}@W{n}'
        r = _wk_range(year, n)
        ko = f'W{n} · {r}' + (' · 최신' if n == top else '')
        en = f'W{n} \u00b7 {r}' + (' \u00b7 latest' if n == top else '')
        zh = f'W{n} \u00b7 {r}' + (' \u00b7 \u6700\u65b0' if n == top else '')
        opts.append(_go_opt(k, pg, ko, en, zh, selected=(n == page_n)))
    return opts


def _week_opts(ent, latest, cur_w):
    """주간 SUMMARY 의 기간 선택 옵션. 서빙 모드는 보관본 목록을 서버에서 받아 덧붙이고, 로컬 미리보기는 파일 이동 옵션을 쓴다."""
    if CFG['served']:
        top = int(CFG.get('top') or latest)
        try:
            yr_ = int(str(CFG.get('asof') or '')[:4])
        except ValueError:
            yr_ = 2026
        if yr_ < 2000:
            yr_ = 2026
        o = [_go_opt(0, f'summary_{ent}', f'W{top} · 최신', f'W{top} \u00b7 latest', f'W{top} \u00b7 \u6700\u65b0', selected=(cur_w is None)),
             ('hdr', '── 지난 주 ──', '── Past weeks ──', '── 過去週別 ──', 'disabled')]
        for k, n in enumerate(range(top - 1, 0, -1), 1):
            r_ = _wk_range(yr_, n)
            o.append(_go_opt(k, f'summary_{ent}@W{n}', f'W{n} · {r_}', f'W{n} \u00b7 {r_}', f'W{n} \u00b7 {r_}', selected=(cur_w == n)))
        return o
    opts = [_go_opt(0, f'summary_{ent}', f'W{latest} · 최신', f'W{latest} · latest', f'W{latest} · 最新', selected=(cur_w is None))]
    for k, w_ in enumerate(range(latest - 1, max(1, latest - 13), -1), 1):
        opts.append(_go_opt(k, f'summary_{ent}@W{w_}', f'W{w_}', f'W{w_}', f'W{w_}', selected=(cur_w == w_)))
    return opts


def summary_page(ent, kind, per, summ, opts=None):
    link = _href(ent, 'journal', per).replace('href=', 'href=', 1)
    return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{ent} SUMMARY ({'주간' if per == 'w' else ('월간' if per == 'm' else '연간')})</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<style>{CSS}{EXTRA_CSS}{CSS2}{HDR_CSS}</style></head><body data-lang="ko" class="sumpage">
{head_block(ent, kind, per, '', False, kind, opts or [], brand=True)}
<div class="ntc">{SUM_NOTICE[per]}</div>
{summ}
<div class="gol"><a {link}><span class="ko">상세 일지 보기 &rarr;</span><span class="en">View detailed journal &rarr;</span><span class="zh">查看詳細日誌 &rarr;</span></a></div>
<script>{LANG_JS}</script>
<script>{cur_js(ent)}</script>
<script>{HDR_JS}</script>
<script>{BRAND_JS}</script>
{loader_tag()}
</body></html>'''


def generate_summary_months(latest, api_url='', served=False, status='final', asof=None, out_dir=None, only=None):
    """월 선택용 월간 SUMMARY: 1월부터 기준 월까지 각 달의 SUMMARY (msummary_HK@M08 …). 최신 달은 msummary_HK(현재) 이름을 쓴다."""
    import datetime
    import real_data as rd
    rd.WEEKS[:] = [latest - 3, latest - 2, latest - 1, latest]
    CFG.update(served=served, status=status, blank=True, api_url=api_url, arch='',
               asof=asof or datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    out = {}
    for ent in ('HK', 'TW'):
        if only and ent not in only:
            continue
        groups, _wd, _raws, _wly = rd.load_entity(ent)
        _, _, _, last_as_of, _ = rd.load_monthly_ledger(ent, latest, groups, 1)
        months_all = list(range(1, last_as_of.month + 1))
        for m in months_all:
            as_of = datetime.date(last_as_of.year, m, calendar.monthrange(last_as_of.year, m)[1])
            if as_of > last_as_of:
                as_of = last_as_of
            months, mdata, wbm, a_o, closed = rd.load_monthly_ledger(ent, latest, groups, 2, as_of=as_of)
            groups_m = rd.extend_groups(ent, groups, mdata)
            c = closed[-1]
            _end = a_o
            meta = [dict(label='', month=m, closed=c, span=f"{m}/1~{_end.month}/{_end.day}", asof=f"{_end.month}/{_end.day}", wbm=wbm, year=last_as_of.year)] * len(months)
            page = f'msummary_{ent}' if m == last_as_of.month else f'msummary_{ent}@M{m:02d}'
            opts = []
            for k, mm in enumerate(reversed(months_all)):
                pg = f'msummary_{ent}' if mm == last_as_of.month else f'msummary_{ent}@M{mm:02d}'
                done = mm != last_as_of.month or last_as_of.day == calendar.monthrange(last_as_of.year, mm)[1]
                ko = f'{mm}월 마감' if done else f'{mm}월 ~{last_as_of.month}/{last_as_of.day}'
                en = f'{MON_EN[mm - 1]} closed' if done else f'{MON_EN[mm - 1]} ~{last_as_of.month}/{last_as_of.day}'
                zh = f'{mm}月 結算' if done else f'{mm}月 ~{last_as_of.month}/{last_as_of.day}'
                opts.append(_go_opt(k, pg, ko, en, zh, selected=(mm == m)))
            CFG['sfx'] = '' if m == last_as_of.month else f'@M{m:02d}'
            out[page] = summary_page(ent, 'msummary', 'm', period_brands(ent, mdata, groups_m, meta, 'm'), opts)
            CFG['sfx'] = ''
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        for name, html in out.items():
            with open(os.path.join(out_dir, _local_name(name)), 'w', encoding='utf-8') as f:
                f.write(html)
    return out


def generate_summary_weeks(latest, nweeks=12, api_url='', served=False, status='final', asof=None, out_dir=None, only=None):
    """지난 주 숫자 SUMMARY(1~3, ERP 원장): latest-nweeks ~ latest-1 주 (summary_HK@W36 …). 최신 주는 기존 전체 SUMMARY 가 맡는다."""
    import datetime
    import real_data as rd
    rd.WEEKS[:] = [latest - 3, latest - 2, latest - 1, latest]
    CFG.update(served=served, status=status, blank=True, api_url=api_url, arch='', top=latest,
               asof=asof or datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    out = {}
    for ent in ('HK', 'TW'):
        if only and ent not in only:
            continue
        groups, _wd, raws, _wly = rd.load_entity(ent)
        latest_end = datetime.datetime.strptime(raws[latest]['cutoff_end'], '%Y%m%d').date()
        for w_ in range(max(1, latest - nweeks), latest):
            we = latest_end - datetime.timedelta(days=7 * (latest - w_))
            cur, prev = rd.load_week_ledger(ent, groups, we)
            groups_w = rd.extend_groups(ent, groups, [prev, cur])
            ws = we - datetime.timedelta(days=6)
            meta = [dict(label='', wk=w_, closed=True, span=f"{ws.month}/{ws.day}~{we.month}/{we.day}", asof=f"{we.month}/{we.day}", month=we.month)] * 2
            page = f'summary_{ent}@W{w_}'
            CFG['sfx'] = f'@W{w_}'
            out[page] = summary_page(ent, 'summary', 'w', period_brands(ent, [prev, cur], groups_w, meta, 'w'), _week_opts(ent, latest, w_))
            CFG['sfx'] = ''
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        for name, html in out.items():
            with open(os.path.join(out_dir, _local_name(name)), 'w', encoding='utf-8') as f:
                f.write(html)
    return out


# ============================================================ BEP 화면 (레이아웃만, 숫자는 GL 매핑 확정 후)
BEP_SEL = ('<select id="bepMon" class="persel" aria-label="month">' + ''.join(
    f'<option value="{m}">{m}월 ' + ('(마감 전)' if m == 9 else '마감') + '</option>' for m in (9, 8, 7, 6, 5, 4, 3, 2, 1)) + '</select>')

BEP_CSS = """
.bp{padding:0 20px 60px}
.bp h2{font-size:15px;margin:22px 0 8px;display:flex;gap:8px;align-items:baseline}.bp h2 small{font-size:11.5px;color:#6b7280;font-weight:400}
.bp .bpw{overflow-x:auto;border:1px solid #e5e7eb;border-radius:10px}
.bp table.bpt{border-collapse:collapse;width:100%;min-width:1100px;font-variant-numeric:tabular-nums}
.bp .bpt th,.bp .bpt td{padding:5px 8px;border-bottom:1px solid #e5e7eb;text-align:right;white-space:nowrap}
.bp .bpt thead th{background:#f3f4f6;font-weight:600;text-align:center;color:#6b7280}
.bp .bpt thead th.g0{background:#111;color:#fff}.bp .bpt thead th.gp{background:#e6edf7;color:#1d4ed8}.bp .bpt thead th.gy{background:#f1ede2;color:#92400e}
.bp .bpt td.lb{text-align:left;font-weight:600;position:sticky;left:0;background:#fff;min-width:150px}
.bp .bpt tr.l1 td.lb{padding-left:22px;font-weight:500}
.bp .bpt tr.sub td{background:#f3f4f6;font-weight:700}.bp .bpt tr.sub td.lb{background:#f3f4f6}
.bp .bpt tr.hl td,.bp .bpt tr.hl td.lb{background:#e8f5ee;font-weight:700}
.bp .bpt tr.op td,.bp .bpt tr.op td.lb{background:#fdf3d9;font-weight:700}
.bp .bpt td.p{background:#f4f7fc}.bp .bpt td.y{background:#faf8f3}
.bp .bpt td.na{color:#9ca3af}
.bp .bpt tr.hide{display:none}
.bp .car{display:inline-block;width:14px;color:#6b7280;cursor:pointer;user-select:none}
.bp .grph{margin:14px 0 8px;font-weight:700;font-size:12.5px}.bp .grph small{font-weight:400;color:#6b7280;margin-left:6px}
.bp .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px}
.bp .bcard{border:1px solid #e5e7eb;border-radius:10px;padding:10px 12px;background:#fff}
.bp .bcard.key{border-color:#d1d5db;box-shadow:0 0 0 1px #d1d5db inset}
.bp .bcard h3{margin:0 0 6px;font-size:13px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.bp .chip{font-size:11px;padding:1px 8px;border-radius:10px;border:1px solid #d1d5db;color:#6b7280;font-weight:400}
.bp .chip.up{color:#DC2626;border-color:#DC2626}.bp .chip.dn{color:#1D4ED8;border-color:#1D4ED8}
.bp .chips{display:inline-flex;gap:6px;flex-wrap:wrap}
.bp .st2{font-size:11px;padding:1px 8px;border-radius:10px;background:#f3f4f6;color:#6b7280;font-weight:400}
.bp .meta{font-size:11px;color:#6b7280;margin:0 0 6px}
.bp textarea{width:100%;min-height:74px;font:inherit;font-size:12px;border:1px solid #d1d5db;border-radius:8px;padding:6px 8px;background:#fff;color:#111;resize:vertical}
.bp .bcard.key textarea{min-height:92px}
.bp .btns{display:flex;gap:6px;margin-top:6px}
.bp .btns button{font:inherit;font-size:11.5px;padding:3px 12px;border:1px solid #d1d5db;border-radius:14px;background:#fff;color:#6b7280}
.bp .bpc{border-collapse:collapse;width:100%;min-width:760px}.bp .bpc th,.bp .bpc td{padding:6px 10px;border-bottom:1px solid #e5e7eb;vertical-align:top;text-align:left}
.bp .bpc thead th{background:#f3f4f6;color:#6b7280;font-weight:600}.bp .bpc td.n{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}.bp .bpc td.sm{font-size:11px;color:#6b7280}
.bp .bpc td.lb{font-weight:600;white-space:nowrap}.bp .bpc tr.keyr td.lb{color:#111}.bp .bpc th.cmh,.bp .bpc td.tx{min-width:320px;width:45%}
#bXls{display:none}
.bp .bcard .tx{margin-top:4px;min-height:74px;padding:6px 8px;border:1px solid #d1d5db;border-radius:8px;background:#fff;font-size:12px;line-height:1.5}
.bp .bcard.key .tx{min-height:92px}
.bp .bcard .tx div.editing{min-height:64px}.bp .bcard.key .tx div.editing{min-height:82px}
.bp .bcard .tx div:empty::before{content:attr(data-ph);color:#9ca3af}
.bp .bcard .tx div.editing:empty::before{content:attr(data-ph);color:#9ca3af}
.bp .st2[data-st="1"]{background:#dcfce7;color:#166534}
.bp .btns .pri{background:#f3f4f6;color:#374151;border-color:#d1d5db;cursor:pointer;font-weight:600}.bp .btns .pri:hover{background:#e5e7eb}
.bp .soon{margin-top:18px;padding:10px 12px;border:1px dashed #d1d5db;border-radius:10px;color:#6b7280}
"""

BEP_JS = """(function(){
var D=window.BEP_DATA,ROWS=D.rows,META=D.meta,DRAFT=D.draft;
var LANGS={ko:0,en:1,zh:2};
function lang(){return LANGS[document.body.getAttribute('data-lang')||'ko']||0}
function n0(x){return Math.round(x).toLocaleString('en-US')}
function pc(a,b){return b?(a/b*100).toFixed(1)+'%':'\\u2014'}
function pp(x){return (x>=0?'+':'\\u2212')+Math.abs(x).toFixed(1)+'%p'}
function sg(x){return (x>=0?'+':'\\u2212')+Math.abs(Math.round(x)).toLocaleString('en-US')}
var DASH='\\u2014';
/* 현지통화 보기: 대시보드 원화(결산)를 고정환율로 나눈 참고값 (임시 — 9월 마감 후 대시보드 현지통화 값으로 교체). 비율·차이(%p)는 같은 값이라 그대로. */
function curMode(){var m='krw';try{m=localStorage.getItem('wj_cur')||'krw'}catch(e){}return m==='loc'?'loc':'krw'}
function curRate(){var r=window.BEP_FX||1;try{var x=parseFloat(localStorage.getItem('wj_fx_'+D.ent));if(x>0)r=x}catch(e){}return r}
function sc(a){if(curMode()!=='loc')return a;var f=1/curRate();return a.map(function(t){return t.map(function(v){return (v===null||v===undefined)?v:v*f})})}
function month(m){var o=[];for(var i=0;i<ROWS.length;i++){o.push(D.months[String(m)][i])}return sc(o)}
function ytd(m){
  var o=[];
  for(var i=0;i<ROWS.length;i++){
    var t=[0,0,0],known=true;
    for(var k=1;k<=m;k++){var v=D.months[String(k)][i];if(v[0]===null)known=false;else t[0]+=v[0];t[1]+=v[1];t[2]+=v[2]}
    if(!known)t[0]=null;
    if(m===D.closed&&D.ytd)t=D.ytd[i];
    o.push(t);
  }
  return sc(o);
}
function cell(i,vals,sales){
  var a=vals[i][0],p=vals[i][1],y=vals[i][2],sa=sales[0],sp=sales[1],sy=sales[2],profit=META[i].profit;
  var ps=sp?p/sp*100:null,ys=sy?y/sy*100:null,has=(a!==null&&a!==undefined);
  var as=(has&&sa)?a/sa*100:null;
  var d1=!has?DASH:(profit?sg(a-p):pc(a,p)),d2=!has?DASH:(profit?sg(a-y):pc(a,y));
  var f1=function(x){return x===null?DASH:x.toFixed(1)+'%'};
  var sd=function(x,b){return (x===null||b===null)?DASH:pp(x-b)};
  return '<td>'+(has?n0(a):DASH)+'</td><td>'+f1(as)+'</td>'
   +'<td class="p">'+n0(p)+'</td><td class="p">'+d1+'</td><td class="p">'+f1(ps)+'</td><td class="p">'+sd(as,ps)+'</td>'
   +'<td class="y">'+n0(y)+'</td><td class="y">'+d2+'</td><td class="y">'+f1(ys)+'</td><td class="y">'+sd(as,ys)+'</td>';
}
function drawTable(m){
  var mv=month(m),yv=ytd(m),tb=document.getElementById('bepBody'),h='';
  var openSga=tb.getAttribute('data-open')!=='0';
  ROWS.forEach(function(k,i){
    var mt=META[i],car=(k==='sga')?'<span class="car" data-t="sga" data-o="'+(openSga?1:0)+'">'+(openSga?'&#9662;':'&#9656;')+'</span>':'';
    h+='<tr class="'+mt.cls+(mt.par&&!openSga?' hide':'')+'" data-k="'+k+'"'+(mt.par?' data-p="'+mt.par+'"':'')+'><td class="lb">'+car+mt.name[lang()]+'</td>'+cell(i,mv,mv[0])+cell(i,yv,yv[0])+'</tr>';
  });
  tb.innerHTML=h;
  tb.querySelectorAll('.car').forEach(function(c){c.addEventListener('click',function(){var op=c.getAttribute('data-o')!=='0';tb.setAttribute('data-open',op?'0':'1');drawTable(+document.getElementById('bepMon').value);});});
}
function sgn(x){return (x>=0?'+':'\\u2212')+Math.abs(x)}
function drawChips(){
  var mv=month(DRAFT);
  document.querySelectorAll('.bcard[data-ik]').forEach(function(card){
    var k=(card.getAttribute('data-ik')||'').replace('bep_',''),i=ROWS.indexOf(k);if(i<0)return;
    var a=mv[i][0],p=mv[i][1],y=mv[i][2],mt=META[i],rev=(k==='sales'||k==='gross'||k==='direct'||k==='op');
    [['p',p,['\\uacc4\\ud68d \\ub300\\ube44','vs Plan','\\u5c0d\\u8a08\\u756b']],['y',y,['\\uc804\\ub144 \\ub300\\ube44','vs LY','\\u5c0d\\u53bb\\u5e74']]].forEach(function(c){
      var el=card.querySelector('.chip[data-c="'+c[0]+'"]');if(!el)return;
      var txt=DASH,cls='chip';
      if(a!==null&&a!==undefined){
        var d=a-c[1];txt=mt.profit?sgn(Math.round(d)):(c[1]?((a/c[1]-1)*100>=0?'+':'\\u2212')+Math.abs((a/c[1]-1)*100).toFixed(1)+'%':DASH);
        var bad=rev?d<0:d>0,big=mt.profit?Math.abs(d)>5:(c[1]&&Math.abs(a/c[1]-1)>0.05);
        if(big)cls+=bad?' up':' dn';
      }
      el.className=cls;el.innerHTML='<span class="ko">'+c[2][0]+'</span><span class="en">'+c[2][1]+'</span><span class="zh">'+c[2][2]+'</span> '+txt;
    });
  });
}
function drawStatus(){
  document.querySelectorAll('.bcard[data-ik]').forEach(function(card){
    var has=[].some.call(card.querySelectorAll('.tx div'),function(d){return d.textContent.trim()!==''});
    var st=card.querySelector('.st2');if(!st)return;
    st.setAttribute('data-st',has?'1':'0');
    st.innerHTML=has?'<span class="ko">\\uc791\\uc131\\ub428</span><span class="en">Written</span><span class="zh">\\u5df2\\u586b\\u5beb</span>':'<span class="ko">\\ubbf8\\uc791\\uc131</span><span class="en">Not written</span><span class="zh">\\u672a\\u586b\\u5beb</span>';
  });
}
document.addEventListener('input',function(){setTimeout(drawStatus,0)});
setInterval(drawStatus,3000);
function sayst(h){var st=document.getElementById('st');if(st)st.innerHTML=h}
function say(ko,en,zh){sayst('<span class="ko">'+ko+'</span><span class="en">'+en+'</span><span class="zh">'+zh+'</span>')}
document.querySelectorAll('.bpPrev').forEach(function(b){b.addEventListener('click',function(){
  var card=b.closest('.bcard'),ik=card.getAttribute('data-ik'),pm=DRAFT-1,wk='M'+(pm<10?'0':'')+pm;
  var eb=document.getElementById('bEdit');
  if(eb&&!eb.classList.contains('on'))eb.click();      // 편집 모드로 (로그인 전이면 로그인 창이 뜸)
  if(!window.wjPrev){return}
  window.wjPrev(wk).then(function(cells){
    var ENTK=document.body.getAttribute('data-ent')||D.ent,got=0,L=['ko','en','zh'];
    if(!cells){say('\\uc774\\uc804 \\ub2ec('+pm+'\\uc6d4) \\ucf54\\uba58\\ud2b8\\ub97c \\ubd88\\ub7ec\\uc62c \\uc218 \\uc5c6\\uc2b5\\ub2c8\\ub2e4. \\ub85c\\uadf8\\uc778 \\ud6c4 \\ub2e4\\uc2dc \\ub204\\ub974\\uc138\\uc694.','Cannot load last month ('+pm+') comments. Sign in and try again.','\\u7121\\u6cd5\\u8f09\\u5165\\u4e0a\\u6708\\u8a55\\u8ad6\\uff0c\\u8acb\\u767b\\u5165\\u5f8c\\u518d\\u8a66\\u3002');return}
    var prev={};L.forEach(function(l){var c=cells[D.ent+'|'+wk+'|BEP|'+ik+'|'+l];if(c&&c.html&&c.html.replace(/<[^>]*>/g,'').trim())prev[l]=c.html});
    if(!Object.keys(prev).length){say(pm+'\\uc6d4 \\ucf54\\uba58\\ud2b8\\uac00 \\uc5c6\\uc2b5\\ub2c8\\ub2e4.','No comment found for month '+pm+'.',pm+'\\u6708\\u6c92\\u6709\\u8a55\\u8ad6\\u3002');return}
    var tx=card.querySelector('.tx'),cur=[].some.call(tx.querySelectorAll('div'),function(d){return d.textContent.trim()!==''});
    if(cur&&!window.confirm('\\uc774\\ubbf8 \\uc791\\uc131\\ub41c \\ub0b4\\uc6a9\\uc774 \\uc788\\uc2b5\\ub2c8\\ub2e4. \\uc774\\uc804 \\ub2ec \\ub0b4\\uc6a9\\uc73c\\ub85c \\ubc14\\uafc9\\ub2c8\\ub2e4\\u003f / Replace with last month\\u0027s text?'))return;
    L.forEach(function(l){var d=tx.querySelector('div.'+l);if(d&&prev[l]!==undefined){d.innerHTML=prev[l];d.dispatchEvent(new Event('input',{bubbles:true}));got++}});
    say(pm+'\\uc6d4 \\ub0b4\\uc6a9\\uc744 \\uac00\\uc838\\uc654\\uc2b5\\ub2c8\\ub2e4. \\uace0\\uce5c \\ub4a4 \\uc800\\uc7a5\\uc744 \\ub204\\ub974\\uc138\\uc694.','Copied month '+pm+'. Edit it and press Save.',pm+'\\u6708\\u5167\\u5bb9\\u5df2\\u5e36\\u5165\\uff0c\\u4fee\\u6539\\u5f8c\\u8acb\\u6309\\u300c\\u5132\\u5b58\\u300d\\u3002');
  });
})});
document.querySelectorAll('.bpSave').forEach(function(b){b.addEventListener('click',function(){var s=document.getElementById('bSave');if(s)s.click()})});
function drawUnit(){
  var loc=curMode()==='loc',lc=D.ent==='HK'?'HKD':'TWD',r=curRate();
  var sm=document.querySelector('.bp > h2 small');
  if(sm){if(!sm.hasAttribute('data-o'))sm.setAttribute('data-o',sm.innerHTML);
    sm.innerHTML=loc?'<span class="ko">당월 · 누계 · 실적 / 계획 / 전년 · 단위 백만 '+lc+'</span><span class="en">Month / YTD · Actual / Plan / Last year · '+lc+' million</span><span class="zh">當月 / 累計 · 實績 / 計畫 / 去年 · 單位 百萬 '+lc+'</span>':sm.getAttribute('data-o');}
  var nt=document.getElementById('bepFxNote');
  if(nt){nt.hidden=!loc;if(loc){var ks=nt.querySelectorAll('.rt');for(var q=0;q<ks.length;q++)ks[q].textContent=r;}}
}
function draw(){
  var m=+document.getElementById('bepMon').value;
  drawUnit();
  drawChips();drawStatus();
  drawTable(m);
  var lbl=document.getElementById('bepMonLbl');if(lbl)lbl.textContent=m;
  var cs=document.getElementById('bepCm'),ns=document.getElementById('bepCmOff');
  if(cs)cs.hidden=(m!==DRAFT);if(ns)ns.hidden=(m===DRAFT);
}
document.getElementById('bepMon').addEventListener('change',draw);
document.getElementById('bepMon').value=String(DRAFT);
document.getElementById('lang').addEventListener('click',function(){setTimeout(draw,30)});
[].forEach.call(document.querySelectorAll('#cur button,#fxr'),function(b){b.addEventListener('click',function(){setTimeout(draw,0)})});
var fxi=document.getElementById('fx');if(fxi)fxi.addEventListener('input',function(){setTimeout(draw,0)});
draw();
})();"""

# (키, 한글, 영어, 번체, 줄 종류, 접는 묶음 부모, 비용 카드 여부, 핵심 카드, 담당 부서 키)
BEP_ROWS = [
    ('sales', '매출액', 'Net sales', '營業收入', 'sub', '', 1, 1, 'sales'),
    ('cogs', '총매출원가', 'Total COGS', '總銷貨成本', 'l1', '', 1, 1, 'plan'),
    ('gross', '매출이익', 'Gross profit', '銷貨毛利', 'sub', '', 0, 0, ''),
    ('sga', '판관비', 'SG&A', '銷管費用', 'sub', '', 0, 0, ''),
    ('labor', '인건비', 'Labor', '人事費', 'l1', 'sga', 1, 0, 'mgmt'),
    ('dist', '유통비용', 'Distribution', '通路費用', 'l1', 'sga', 1, 0, 'sales'),
    ('advt', '광고판촉', 'Advertising & promotion', '廣告促銷', 'l1', 'sga', 1, 0, 'mkt'),
    ('depr', '감가상각', 'Depreciation', '折舊', 'l1', 'sga', 1, 0, 'mgmt'),
    ('roy', '로열티', 'Royalty', '權利金', 'l1', 'sga', 1, 0, 'mgmt'),
    ('ship', '물류+운반비', 'Logistics & freight', '物流運費', 'l1', 'sga', 1, 0, 'trade'),
    ('etc', '기타판관비', 'Other SG&A', '其他銷管費', 'l1', 'sga', 1, 0, 'mgmt'),
    ('direct', '직접성과이익', 'Direct profit', '直接績效利益', 'hl', '', 0, 0, ''),
    ('com', '공통비배부', 'Allocated common cost', '共同費用分攤', 'l1', '', 0, 0, ''),
    ('op', '영업이익', 'Operating profit', '營業利益', 'op', '', 1, 1, 'strat'),
]
BEP_DEPT = {'sales': ('영업', 'Sales', '營業'), 'plan': ('상품기획', 'Merchandising', '商品企劃'), 'mgmt': ('경영지원', 'Management support', '管理支援'),
            'mkt': ('마케팅', 'Marketing', '行銷'), 'trade': ('물류', 'Logistics', '物流'), 'strat': ('전략기획', 'Strategic planning', '策略企劃')}


def bep_data(ent):
    import json
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bep_dashboard_2026.json')
    d = json.load(open(p, encoding='utf-8'))
    meta = []
    for k, ko, en, zh, cls, par, cost, key, dept in BEP_ROWS:
        meta.append(dict(name=[ko, en, zh], cls=cls, par=par, profit=k in ('direct', 'op')))
    keys = [r[0] for r in BEP_ROWS]
    assert keys == d['rows'], (keys, d['rows'])
    months = {m: v for m, v in d['months'][ent].items()}
    out = (d.get('outlook') or {}).get('months', {}).get(ent, {})
    draft = d['closed_month']
    for m, rows in sorted(out.items(), key=lambda x: int(x[0])):
        if m not in months:                              # 마감 전 달: 실적 없음, 계획·전년만
            months[m] = [[None, r[0], r[1]] for r in rows]
    if out:
        draft = d['closed_month'] + 1                     # 작성 중인 달 = 마감 다음 달
    return dict(rows=keys, meta=meta, months=months, ytd=d['ytd'][ent], closed=d['closed_month'], draft=draft, ent=ent)


def bep_page(ent):
    _set_fx(ent)
    import json
    data = bep_data(ent)
    draft = data['draft']
    th_sub = ''.join(f'<th>{B("금액", "Amount", "金額")}</th><th>{B("비중", "Share", "占比")}</th>'
                     f'<th class="gp">{B("금액", "Amount", "金額")}</th><th class="gp">{B("대비", "Ratio", "對比")}</th><th class="gp">{B("비중", "Share", "占比")}</th><th class="gp">{B("차이", "Diff.", "差異")}</th>'
                     f'<th class="gy">{B("금액", "Amount", "金額")}</th><th class="gy">{B("대비", "Ratio", "對比")}</th><th class="gy">{B("비중", "Share", "占比")}</th><th class="gy">{B("차이", "Diff.", "差異")}</th>' for _ in (0, 1))
    head = (f'<thead><tr><th rowspan="3" style="min-width:150px">{B("계정", "Account", "科目")}</th>'
            f'<th colspan="10" class="g0">{B("당월", "Month", "當月")} (<span id="bepMonLbl">{draft}</span>{B("월", "", "月")})</th><th colspan="10" class="g0">{B("누계 (1월~당월)", "YTD", "累計")}</th></tr><tr>'
            + ''.join(f'<th colspan="{2 if i % 3 == 0 else 4}" class="{["", "gp", "gy"][i % 3]}">{B(*[("실적", "Actual", "實績"), ("계획", "Plan", "計畫"), ("전년", "Last year", "去年")][i % 3])}</th>' for i in range(6))
            + f'</tr><tr>{th_sub}</tr></thead>')
    # 코멘트 입력 카드: 일지와 같은 칸 구조(카드 안에 div.tx > div.ko/en/zh)라서 일지의 편집·저장·번역·충돌 확인 기능이 그대로 동작한다.
    mrows = data['months'][str(draft)]
    idx = {k: i for i, k in enumerate(data['rows'])}

    def n0(x):
        return f'{x:,.0f}'

    def pct(a_, b_):
        return f'{a_ / b_ * 100:.1f}%' if b_ else '&mdash;'
    sales_p, sales_y = mrows[0][1], mrows[0][2]

    PH_KEY = ('이 계정의 핵심 코멘트를 한두 줄로 적어 주세요', 'Write the key comment for this account in a line or two', '請用一兩行寫下此科目的重點評論')
    PH_ITEM = ('무엇 때문에 늘었/줄었는지, 계획과 다른 이유를 적어 주세요', 'Why it rose / fell, and why it differs from plan', '請寫明增減原因，以及與計畫不同的原因')

    def tx(ph):
        return ('<div class="tx" data-w="0">' + ''.join(f'<div class="{l}" data-ph="{ph[i]}"></div>' for i, l in enumerate(('ko', 'en', 'zh'))) + '</div>')

    def ccard(r):
        k, ko, en, zh, cls, par, cost, key, dept = r
        p, y = mrows[idx[k]][1], mrows[idx[k]][2]
        d = BEP_DEPT[dept]
        return (f'<div class="bcard{" key" if key else ""}" data-dm="bep" data-dk="BEP" data-ik="bep_{k}">'
                f'<h3>{B(ko, en, zh)} <span class="st2" data-st="0">{B("미작성", "Not written", "未填寫")}</span>'
                f'<span class="chip" data-c="p">{B("계획 대비", "vs Plan", "對計畫")} &mdash;</span><span class="chip" data-c="y">{B("전년 대비", "vs LY", "對去年")} &mdash;</span></h3>'
                f'<div class="meta">{B("담당 부서", "Owner", "負責部門")}: {B(*d)} &middot; {B("당월", "Month", "當月")} &mdash; / {B("계획", "Plan", "計畫")} {n0(p)} / {B("전년", "LY", "去年")} {n0(y)} {B("백만원", "KRW m", "百萬韓元")}' + (f' &middot; {B("핵심 코멘트", "Key comment", "重點評論")}' if key else '') + '</div>'
                + tx(PH_KEY if key else PH_ITEM) +
                f'<div class="btns"><button type="button" class="pri bpSave">{B("저장", "Save", "儲存")}</button>'
                f'<button type="button" class="bpPrev">{B("이전 달 가져오기", "Copy last month", "帶入上月")}</button></div></div>')
    keycards = ''.join(ccard(r) for r in BEP_ROWS if r[6] and r[7])
    sgacards = ''.join(ccard(r) for r in BEP_ROWS if r[6] and not r[7])
    special = (f'<div class="bcard" data-dm="bep" data-dk="BEP" data-ik="bep_special"><h3>{B("특이 비용 이유", "Unusual costs", "特殊費用原因")} <span class="st2" data-st="0">{B("미작성", "Not written", "未填寫")}</span></h3>'
               f'<div class="meta">{B("작성: 전략기획팀 · 당월 계획·전년과 크게 다른 일회성 비용이나 이슈", "By Strategic planning · one-off costs or issues far from plan / last year", "填寫：策略企劃部 · 與計畫、去年差異大的一次性費用或事項")}</div>'
               + tx(('특이 비용이 없으면 \'특이 비용 없습니다\'로 저장', "If none, save 'No unusual costs'", '若無特殊費用，請儲存「無特殊費用」')) +
               f'<div class="btns"><button type="button" class="pri bpSave">{B("저장", "Save", "儲存")}</button>'
                f'<button type="button" class="bpPrev">{B("이전 달 가져오기", "Copy last month", "帶入上月")}</button></div></div>')
    cmt = (f'<div id="bepCm"><h2>{B(f"{draft}월 증감 이유 · 핵심 코멘트", f"Month {draft}: reasons for changes", f"{draft}月 增減原因 · 重點評論")} '
           f'<small>{B("법인 담당자가 비용이 왜 늘었/줄었는지 직접 입력 · 편집 버튼을 누른 뒤 노란 칸에 입력하고 저장", "Entered by the entity owner: press Edit, type in the yellow cells, then Save", "由法人負責人填寫：按「編輯」後在黃色欄位輸入並儲存")}</small></h2>'
           f'<div class="grph">{B("핵심 계정", "Key accounts", "核心科目")} <small>{B("매출액 · 매출원가 · 영업이익", "Net sales · COGS · Operating profit", "營業收入 · 銷貨成本 · 營業利益")}</small></div>'
           f'<div class="cards">{keycards}</div>'
           f'<div class="grph">{B("판관비 항목", "SG&A items", "銷管費項目")} <small>{B("인건비 · 유통비용 · 광고판촉 · 감가상각 · 로열티 · 물류+운반비 · 기타", "Labor · Distribution · Advertising · Depreciation · Royalty · Logistics · Other", "人事 · 通路 · 廣告 · 折舊 · 權利金 · 物流 · 其他")}</small></div>'
           f'<div class="cards">{sgacards}</div>'
           f'<div class="grph">{B("특이 비용", "Unusual costs", "特殊費用")}</div><div class="cards">{special}</div></div>'
           f'<div id="bepCmOff" class="soon" hidden>{B(f"코멘트는 작성 중인 {draft}월에만 입력합니다. 이전 달 코멘트 보기는 다음 단계에서 연결합니다.", f"Comments are entered for month {draft} only. Viewing past comments will be added in a later step.", f"僅可輸入 {draft} 月的評論。過往月份的評論檢視將於下一階段連結。")}</div>')
    note = (f'<div class="ntc">{B(f"숫자(실적·계획·전년)는 전략기획팀 TNH 글로벌 대시보드 기준(결산, 원화)이며 검증은 거기서 합니다. 이 화면은 {draft}월 마감 전에 법인이 비용 증감 사유를 입력하는 용도입니다. {draft}월 실적은 마감 후 채워집니다.", f"Figures (actual / plan / last year) follow the Strategic Planning TNH Global dashboard (settlement basis, KRW), which is where they are verified. This screen is for entities to enter reasons for cost changes before the month {draft} close; actuals are filled after the close.", f"數字（實績／計畫／去年）依策略企劃部 TNH 全球儀表板（決算基準，韓元），並於該處驗證。本畫面供法人在 {draft} 月結帳前輸入費用增減原因；實績將於結帳後填入。")}</div>')
    cn = lambda ko, en, zh: B(ko, en, zh)
    lc_ = 'HKD' if ent == 'HK' else 'TWD'
    fxnote = (f'<div class="ntc" id="bepFxNote" hidden>{B(f"현지통화는 대시보드 결산 원화를 고정환율(1 {lc_} = ", f"Local currency is the dashboard KRW (settlement) divided by a fixed rate (1 {lc_} = ", f"當地貨幣為儀表板決算韓元除以固定匯率（1 {lc_} = ")}<span class="rt"></span>{B(" KRW)로 나눈 참고값입니다. 9월 마감 후 대시보드 현지통화 값으로 바꿉니다.", " KRW). It is a reference value and will be replaced by the dashboard local-currency figures after the September close.", " KRW）的參考值，9 月結帳後將改為儀表板的當地貨幣數值。")}</div>')
    tabs = f'<button data-k="0" data-tag="M{draft:02d}">{draft}월</button>'
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{ent} BEP</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<style>{CSS}{EXTRA_CSS}{CSS2}{HDR_CSS}{BEP_CSS}</style></head><body data-lang="ko" class="sumpage">
{head_block(ent, 'bep', 'm', tabs, True, 'bep', [], brand=False)}
{note}
{fxnote}
<div class="bp">
<h2>{cn("손익", "Profit & loss", "損益")} <small>{cn("당월 · 누계 · 실적 / 계획 / 전년 · 단위 백만원(KRW)", "Month / YTD · Actual / Plan / Last year · KRW million", "當月 / 累計 · 實績 / 計畫 / 去年 · 單位 百萬韓元")}</small></h2>
<div class="bpw"><table class="bpt">{head}<tbody id="bepBody"></tbody></table></div>
{cmt}
<div class="soon">{cn("하반기 전망·계획은 별도 화면(연간 예측 시뮬레이션)에서 다룹니다. 다음 단계입니다.", "H2 outlook and plan will be handled on a separate screen (annual forecast simulation) in a later step.", "下半年展望與計畫將在另一畫面（全年預測模擬）處理，為下一階段。")}</div>
</div>
<script>window.BEP_DATA={json.dumps(data, ensure_ascii=False)};window.BEP_FX={int(CUR_FX)};var N=1;</script>
<script>{LANG_JS}</script>
<script>{cur_js(ent)}</script>
<script>{HDR_JS}</script>
<script>{BEP_JS}</script>
<script>{EDIT_JS.replace('__ENT__', ent).replace('__API__', CFG['api_url'])}</script>
{loader_tag()}
</body></html>"""


STORE_TPL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'superpowers', 'mockups', 'store_board.tpl.html')


def store_page(ent):
    """매장 화면(store_HK / store_TW): 4분면·표(1-1, 1-2). 손익 자료는 store_board_{ent}.json 스냅샷(홍콩만 있음)을 쓴다."""
    import html as _h
    here = os.path.dirname(os.path.abspath(__file__))
    jp = os.path.join(here, f'store_board_{ent}.json')
    head = head_block(ent, 'store', 'm', '', False, 'store', [], brand=False)
    if not os.path.exists(jp) or not os.path.exists(STORE_TPL):
        body = (f'<div class="ntc">{B("이 법인의 매장 손익 자료가 아직 연결되지 않았습니다. 자료가 준비되면 같은 화면(매출×이익 4분면·전년 대비 4분면)이 열립니다.", "Store P&L data for this entity is not connected yet. The same screens (sales x profit quadrant, YoY quadrant) open once the data is ready.", "此法人的門市損益資料尚未連結。資料備妥後將開啟相同畫面（銷售×利潤四象限、年增四象限）。")}</div>')
        frame = ''
    else:
        t = io.open(STORE_TPL, encoding='utf-8').read()
        data = io.open(jp, encoding='utf-8').read()
        t = t.replace('__DATA__', data)
        a = t.index('<div class="hd">')
        b = t.index('<div class="bar" id="bar">')
        t = t[:a] + t[b:]
        a = t.index('<div class="hg"><span class="gl"><span class="ko">언어')
        b = t.index('</div></div>', a) + len('</div></div>')
        t = t[:a] + t[b:]
        a = t.index('<div class="hg"><span class="gl"><span class="ko">통화')
        b = t.index('</div></div>', a) + len('</div></div>')
        t = t[:a] + t[b:]
        body = ''
        frame = (f'<iframe id="stFrame" title="store" srcdoc="{_h.escape(t, quote=True)}" style="width:100%;border:0;height:2400px;display:block" scrolling="no"></iframe>'
                 '<script>(function(){var f=document.getElementById("stFrame");if(!f)return;'
                 'function vp(){var r=f.getBoundingClientRect(),top=Math.max(0,-r.top),h=Math.max(200,Math.min(window.innerHeight-Math.max(r.top,0),r.height-top));try{f.contentWindow.postMessage({wjVp:{top:top,h:h}},"*")}catch(x){}}'
                 'window.addEventListener("scroll",vp,{passive:true});window.addEventListener("resize",vp);'
                 'window.addEventListener("message",function(e){if(e.data&&e.data.wjStoreH)f.style.height=(e.data.wjStoreH+6)+"px";if(e.data&&e.data.wjNeedVp)vp()});'
                 'function sync(){try{if(f.contentWindow.setLang)f.contentWindow.setLang(document.body.getAttribute("data-lang")||"ko")}catch(x){}}'
                 'f.addEventListener("load",sync);new MutationObserver(sync).observe(document.body,{attributes:true,attributeFilter:["data-lang"]});'
                 'var c=document.getElementById("stCur");if(c)c.addEventListener("click",function(e){var b=e.target.closest("button");if(!b)return;[].forEach.call(c.children,function(x){x.classList.toggle("on",x===b)});try{f.contentWindow.setCur(b.getAttribute("data-c"))}catch(x){}})})();</script>')
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{ent} Stores</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<style>{CSS}{EXTRA_CSS}{CSS2}{HDR_CSS}</style></head><body data-lang="ko" class="sumpage">
{head}
{body}{frame}
<script>var N=1;</script>
<script>{LANG_JS}</script>
<script>{HDR_JS}</script>
{loader_tag()}
</body></html>"""


def generate_store(latest, api_url='', served=False, status='final', asof=None, out_dir=None, only=None):
    """매장 화면(store_HK / store_TW)."""
    import datetime
    CFG.update(served=served, status=status, blank=True, api_url=api_url, arch='',
               asof=asof or datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    out = {}
    for ent in ('HK', 'TW'):
        if only and ent not in only:
            continue
        out['store_' + ent] = store_page(ent)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        for name, html in out.items():
            kind, ent = name.split('_')
            with open(os.path.join(out_dir, f'weekly_{kind}_{ent}.html'), 'w', encoding='utf-8') as f:
                f.write(html)
    return out


def generate_bep(latest, api_url='', served=False, status='final', asof=None, out_dir=None, only=None):
    """BEP 화면(bep_HK / bep_TW): 레이아웃만 (숫자는 GL 매핑 확정 후)."""
    import datetime
    CFG.update(served=served, status=status, blank=True, api_url=api_url, arch='',
               asof=asof or datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    out = {}
    for ent in ('HK', 'TW'):
        if only and ent not in only:
            continue
        out['bep_' + ent] = bep_page(ent)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        for name, html in out.items():
            kind, ent = name.split('_')
            with open(os.path.join(out_dir, f'weekly_{kind}_{ent}.html'), 'w', encoding='utf-8') as f:
                f.write(html)
    return out




def generate_yearly(latest, api_url='', served=False, status='final', asof=None, out_dir=None, only=None):
    """연간 화면(yearly_HK / yearly_TW): 1월~기준일 달까지 월별 숫자 (ERP 원장). 부서별 일지는 없음."""
    import datetime
    import real_data as rd
    rd.WEEKS[:] = [latest - 3, latest - 2, latest - 1, latest]
    CFG.update(served=served, status=status, blank=True, api_url=api_url, arch='',
               asof=asof or datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    out = {}
    for ent in ('HK', 'TW'):
        if only and ent not in only:
            continue
        groups, _wd, _raws, _wly = rd.load_entity(ent)
        months, mdata, wbm, as_of, closed = rd.load_monthly_ledger(ent, latest, groups, 1)
        groups = rd.extend_groups(ent, groups, mdata)
        meta = [dict(label=f"{as_of.year} 누계 (1/1~{as_of.month}/{as_of.day})", temps=[], rain=[], wcode=[], submit='',
                     month=as_of.month, closed=True, span=f"1/1~{as_of.month}/{as_of.day}", asof=f"{as_of.month}/{as_of.day}") for _m in months]
        PAGES.pop('yearly_' + ent, None)
        build(ent, groups, meta, [dict() for _ in months], [], monthly=dict(months=months, data=mdata, wbm_tags={}, year=True))
        out['yearly_' + ent] = PAGES['yearly_' + ent]
        out['ysummary_' + ent] = summary_page(ent, 'ysummary', 'y', period_brands(ent, mdata, groups, meta, 'y'))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        for name, html in out.items():
            kind, ent = name.split('_')
            with open(os.path.join(out_dir, f'weekly_{kind}_{ent}.html'), 'w', encoding='utf-8') as f:
                f.write(html)
    return out


def generate_monthly(latest, api_url='', served=False, status='final', asof=None, out_dir=None, only=None, nmonths=None):
    """월간 화면(monthly_HK / monthly_TW). 숫자는 ERP(지난 달 = 월 마감, 최신 달 = 월누계), 글은 그 달 주간 일지를 화면에서 모은 초안."""
    import datetime
    import real_data as rd
    rd.WEEKS[:] = [latest - 3, latest - 2, latest - 1, latest]
    CFG.update(served=served, status=status, blank=True, api_url=api_url, arch='',
               asof=asof or datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    out = {}
    for ent in ('HK', 'TW'):
        if only and ent not in only:
            continue
        groups, _wd, _raws, _wly = rd.load_entity(ent)
        _n = nmonths
        if not _n:                               # 올해 1월부터 지금 달까지 전부 (월 이동이 화면 안에서 즉시)
            _n = rd.load_monthly_ledger(ent, latest, groups, 1)[3].month
        months, mdata, wbm, as_of, closed = rd.load_monthly_ledger(ent, latest, groups, _n)   # 숫자는 ERP 원장 기준
        groups = rd.extend_groups(ent, groups, mdata)
        meta = []
        for m, c in zip(months, closed):
            _end = datetime.date(as_of.year, m, calendar.monthrange(as_of.year, m)[1]) if c else as_of
            meta.append(dict(label=(f"{m}월 (M{m:02d}) 마감" if c else f"{m}월 (M{m:02d}) ~{as_of.month}/{as_of.day}"),
                             temps=[], rain=[], wcode=[], submit='', month=m, closed=c,
                             span=f"{m}/1~{_end.month}/{_end.day}", asof=f"{_end.month}/{_end.day}"))
        tags = {f'M{m:02d}': wbm.get(m, []) for m in months}
        PAGES.pop('monthly_' + ent, None)
        build(ent, groups, meta, [dict() for _ in months], [], monthly=dict(months=months, data=mdata, wbm_tags=tags))
        out['monthly_' + ent] = PAGES['monthly_' + ent]
        out['msummary_' + ent] = summary_page(ent, 'msummary', 'm', period_brands(ent, mdata, groups, meta, 'm'))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        for name, html in out.items():
            kind, ent = name.split('_')
            with open(os.path.join(out_dir, f'weekly_{kind}_{ent}.html'), 'w', encoding='utf-8') as f:
                f.write(html)
    return out


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='주간영업일지 화면 생성')
    ap.add_argument('--week', type=int, default=39)
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--samples', action='store_true', help='시안용 샘플 문구를 넣는다 (기본은 비움)')
    ap.add_argument('--status', default='final', choices=['draft', 'final', 'none'])
    a_ = ap.parse_args()
    generate(a_.week, api_url=API_URL, status=a_.status, blank=not a_.samples, out_dir=a_.out)
    print('MISSING:', sorted(MISSING))
    print('MISSING_ZH:', sorted(MISSING_ZH))
