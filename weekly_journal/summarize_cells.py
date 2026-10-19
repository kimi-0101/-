# -*- coding: utf-8 -*-
"""SUMMARY 5~7 칸별 정리본 만들기 (1단계: 로컬, 구글에 올리지 않음).

입력  = 부서가 쓴 원문 칸(5 경쟁사 동향 · 6 이번 달 리뷰 · 7 다음 달 전략) + 정량 숫자 블록(ERP)
출력  = {sec5: {부서: {동향:[핵심,보충], 대응:[핵심,보충]}},
         sec6: {부서: {결과:[..], 원인:[..], 조치:[..]}},
         sec7: {부서: [전략 항목, ...]}}  + 숫자 대조 결과(검수 대상 표시)
AI 호출은 PC 의 `claude -p` (도구 없음, 세션 저장 없음). 숫자는 (원문 ∪ 정량 블록)에 있는 값만 허용하고, 어긋난 칸은 flags 에 남긴다.
사용:  python weekly_journal/summarize_cells.py --demo-tw        (시연: 대만 9월 샘플 원문으로 실행)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

STYLE = """너는 영업일지 SUMMARY 정리 담당이다. 부서가 쓴 원문 칸을 아래 규칙으로 정리해 JSON 으로만 답한다.

[구성]
- 5 경쟁사 동향: 부서마다 '동향' 1개, '대응' 1개. (동향 = 시장·경쟁사 현황, 대응 = 경쟁사가 취한 조치)
- 6 이번 달 리뷰: 부서마다 '결과' 1개, '원인' 1개, '조치' 1개.
  · 결과 = 이번 달 숫자로 나타난 성과. 정량 블록의 채널·브랜드별 숫자와 원문 숫자를 함께 써서 어디가 강하고 약한지 드러낸다.
  · 원인 = 원문이 '~때문/~영향/~로 인해' 식으로 밝힌 이유만. 숫자 나열이나 실적 서술은 결과로 보낸다.
  · 조치 = 앞으로 하겠다/해야 한다는 내용 중 그 부서에서 가장 우선순위가 높은 하나. 그 부서의 6번 글과 7번 글을 모두 보고 고른다(7번 글의 첫째 과제를 우선).
  · 어느 칸에 쓸지 헷갈리면: 숫자·실적 서술=결과, 이유=원인, 해야 할 일=조치.
  · 한 라벨에 다른 라벨의 내용을 섞지 않는다. 원문이 길고 여러 주제가 섞인 칸(GM 총평·특이사항 등)은 먼저 문장을 결과/원인/조치로 나눠 배정한 뒤 쓴다:
    '목표 달성·증감·브랜드별 숫자'=결과, '~가 견인/기여/영향/불균형'처럼 이유를 설명한 문장=원인, '~필요/~할 것/~해야'=조치.
  · 한 부서에 6번 글이 여러 칸(총평·특이사항 등)이면 모두 합쳐서 본다.
- 7 다음 달 전략: 부서마다 앞으로 할 전략을 빠짐없이 번호 목록(문자열 배열)으로. 'HQ 요청사항' 칸은 부서 'GM(HQ 요청)' 으로 따로 둔다.
- 각 항목(동향/대응/결과/원인/조치)은 [핵심, null] 두 개짜리 배열이다. 두 번째는 항상 null (보충 설명은 쓰지 않는다. 자세한 내용은 화면의 '부서 원문 보기'에 있다).
  핵심 = 말하려는 요지를 분명하게 쓴 문장(30자 안팎). 같은 맥락이면 한 문장(문자열)으로 합치고, 서로 다른 맥락(예: 채널이 다르거나 주제가 다른 내용)이면 맥락마다 한 문장씩 나눠 문자열 배열로 쓴다(최대 3문장). 억지로 쪼개거나 같은 말을 반복하지 않는다. 핵심이 한 문장이면 문자열, 여러 문장이면 배열.
  숫자·사례는 핵심 문장 안에 넣는다.
- 주간 일지(대상이 'W41' 같은 주차)이면 '이번 달·다음 달'을 '이번 주·다음 주'로 읽는다.
- 같은 라벨을 두 번 쓰지 않는다. 재료가 원문에 없는 라벨은 null (억지로 만들지 않는다).

[문체]
- 음슴체(명사형 종결): '~함', '~임', '~확대', '~확보', '~모색', '~진행', '~달성' 처럼 끝낸다. 존댓말·'~다' 종결 금지. '~추진함'·'~대상' 처럼 어색한 끝맺음은 피하고 원문 동사에 가깝게 쓴다(예: '확대', '확보', '모니터링').
- 시즌 표기(26FW, SS 등)는 원문 표기 그대로 쓴다('2026 FW' 를 '26FW' 로 줄이지 않는다). 영어·중국어 원문은 한글로 옮긴다. 매장명·브랜드명·약어(NGA, MG, UPT, ATV, SS, FW 등)는 그대로 둔다.

[사실 규칙 — 가장 중요]
- 원문과 정량 블록에 없는 사실·숫자·이유를 만들지 않는다. 해석·추측·평가 금지.
- 숫자는 원문 또는 정량 블록에 있는 값만 쓴다(단위·소수점 그대로). 계산해서 새 숫자를 만들지 않는다.
- 원문이 모호하면 모호한 그대로 옮기고 '(원문 표현)' 을 붙인다.
- '測試', 'test' 처럼 시험 입력뿐인 칸은 무시한다.
- 결과에는 정량 블록의 채널·브랜드별 숫자를 활용해도 된다. 원인과 조치는 부서 원문에서만 가져온다.
- 원인은 원문이 이유로 쓴 것만. 데이터로 뒷받침되는지는 판단하지 않는다(방문객·교통량 같은 담당자 의견도 그대로 원인으로 쓴다).

[출력] 설명 없이 JSON 한 개만:
{"sec5": {"부서": {"동향": ["핵심 또는 [핵심1,핵심2]",null], "대응": [..]}}, "sec6": {"부서": {"결과": [..], "원인": [..], "조치": [..]}}, "sec7": {"부서": ["항목1","항목2"]}}
라벨을 만들 재료가 없으면 해당 키는 null, 칸이 없는 섹션은 빈 객체 {}."""


def nums(s):
    return set(re.findall(r'\d[\d,.]*\d|\d', s or ''))


def build_prompt(ent, period, cells, quant_text):
    """cells: [{sec: '5'|'6'|'7', dept, item, text}]"""
    lines = [STYLE, '', f'[대상] {ent} {period}', '', '[정량 블록 — ERP 숫자]', quant_text.strip() or '(없음)', '', '[원문 칸]']
    for c in cells:
        lines.append(f"- 섹션{c['sec']} / {c['dept']} / {c['item']}: {c['text']}")
    return '\n'.join(lines)


import threading
_ULOCK = threading.Lock()
USAGE = {'calls': 0, 'input': 0, 'output': 0, 'cache_read': 0, 'cache_write': 0, 'cost': 0.0, 'metered': 0}


def usage_reset():
    for k in USAGE:
        USAGE[k] = 0.0 if k == 'cost' else 0


def usage_report():
    u = USAGE
    if not u['calls']:
        return 'Claude 호출 없음'
    tot = u['input'] + u['output'] + u['cache_read'] + u['cache_write']
    return (f"Claude 호출 {u['calls']}번(측정 {u['metered']}번) — 입력 {u['input']:,} · 출력 {u['output']:,} · 캐시읽기 {u['cache_read']:,} · 캐시쓰기 {u['cache_write']:,} "
            f"(합계 {tot:,} 토큰, 환산 약 ${u['cost']:.2f})")


def _meter(stdout, label='', secs=None):
    """claude --output-format json 결과에서 본문과 토큰을 꺼내 합산하고, 호출마다 한 줄 남긴다. JSON 이 아니면 원문 그대로."""
    try:
        d = json.loads(stdout)
        text = d['result']
        us = d.get('usage') or {}
    except (ValueError, KeyError, TypeError):
        with _ULOCK:
            USAGE['calls'] += 1
        return stdout
    out_tok = int(us.get('output_tokens') or 0)
    with _ULOCK:                                                  # 영어·중국어를 동시에 부르므로 합산은 잠그고 한다
        USAGE['calls'] += 1
        USAGE['metered'] += 1
        USAGE['input'] += int(us.get('input_tokens') or 0)
        USAGE['output'] += out_tok
        USAGE['cache_read'] += int(us.get('cache_read_input_tokens') or 0)
        USAGE['cache_write'] += int(us.get('cache_creation_input_tokens') or 0)
        USAGE['cost'] += float(d.get('total_cost_usd') or 0)
    if label:
        models = ','.join((d.get('modelUsage') or {}).keys()) or '?'
        sec = f'{secs:.0f}초 · ' if secs is not None else ''
        print(f'   [호출] {label} · {sec}출력 {out_tok:,}토큰 · 모델 {models}', flush=True)
    return text


LEAN_SYSTEM = '너는 영업일지 정리 도우미다. 요청한 형식의 출력만 낸다.'


def _claude_cmds(exe, model):
    base = [exe, '-p', '--output-format', 'json', '--no-session-persistence', '--tools', '']
    if model:
        base += ['--model', model]
    plain = (base, None)
    if os.environ.get('WJ_CLAUDE_LEAN', '1') == '0':
        return [plain]
    import tempfile
    neutral = os.path.join(tempfile.gettempdir(), 'wj_claude_cwd')       # 프로젝트 폴더의 CLAUDE.md·메모리가 매번 딸려 들어가지 않게 빈 폴더에서 부른다
    os.makedirs(neutral, exist_ok=True)
    # 기본 시스템 프롬프트(코딩 도구용)도 쓰지 않고, 스킬 목록(--disable-slash-commands)·MCP 도구 설명(--strict-mcp-config)도 싣지 않는다.
    # 2026-10-19 실측: 한 줄짜리 호출도 입력이 약 4.95만 토큰이었는데 위 두 옵션으로 약 4천 토큰(1/12)으로 줄었다.
    lean = (base + ['--system-prompt', LEAN_SYSTEM, '--disable-slash-commands', '--strict-mcp-config'], neutral)
    return [lean, plain]                                                  # 가벼운 방식이 안 되면(구버전·신뢰 문제 등) 예전 방식으로 한 번 더


def call_claude(prompt, model=None, timeout=300, label=''):
    import shutil
    exe = shutil.which('claude') or shutil.which('claude.cmd')      # Windows 는 npm 이 claude.cmd 로 설치함
    if not exe:
        raise RuntimeError('claude 명령을 찾지 못함 (PATH 확인)')
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    if os.environ.get('WJ_THINKING', '0') != '1':
        env['MAX_THINKING_TOKENS'] = '0'                             # 긴 '추론'은 출력 토큰·시간을 크게 늘린다. 정리·번역은 규칙이 정해져 있고 숫자 검사가 따로 있어 끈다 (되돌리려면 WJ_THINKING=1)
    model = model or os.environ.get('WJ_CLAUDE_MODEL') or None       # 예: WJ_CLAUDE_MODEL=sonnet
    tries = _claude_cmds(exe, model)
    for k, (cmd, cwd) in enumerate(tries):
        t0 = time.time()
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding='utf-8', env=env, timeout=timeout, cwd=cwd)
        if r.returncode == 0:
            return _meter(r.stdout, label, time.time() - t0)
        err = (r.stderr or r.stdout)[-300:]
        if k == len(tries) - 1 or 'limit' in err.lower():                 # 사용 한도면 다시 불러도 소용없다
            raise RuntimeError(f'claude 종료코드 {r.returncode}: {err}')


GEMINI_MODEL = 'gemini-2.5-flash'
GEMINI_RETRY_WAIT = 5                                                      # 호출 실패(한도 등) 뒤 잠깐 쉬었다가 한 번 더


def _gemini_key():
    k = os.environ.get('GEMINI_API_KEY', '').strip()
    if k:
        return k
    p = os.path.join(os.path.dirname(HERE), 'apps_script', 'weekly_journal', 'gemini_key.txt')
    return open(p, encoding='utf-8').read().strip() if os.path.exists(p) else ''


def call_gemini(prompt, timeout=120):
    """번역용 Gemini 호출(무료 키). 키가 없거나 실패하면 예외 → 호출하는 쪽이 Claude 로 넘어간다."""
    import urllib.request
    key = _gemini_key()
    if not key:
        raise RuntimeError('gemini 키 없음')
    model = os.environ.get('GEMINI_MODEL', GEMINI_MODEL)
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
    body = json.dumps({'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'temperature': 0, 'responseMimeType': 'application/json'}}).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
    res = json.load(urllib.request.urlopen(req, timeout=timeout))
    try:
        return res['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError):
        raise RuntimeError('gemini 응답 없음: ' + json.dumps(res, ensure_ascii=False)[:200])


def parse_json(txt):
    m = re.search(r'\{.*\}', txt, re.S)
    if not m:
        raise ValueError('JSON 을 찾지 못함: ' + txt[:200])
    return json.loads(m.group(0))


def allowed_numbers(cells, quant_text):
    """정리본에 쓸 수 있는 숫자: (원문 ∪ 정량 블록). 영어 월 이름(Sep 등)·시즌 약어(2026 → 26)는 허용."""
    src_all = ' '.join(c['text'] for c in cells) + ' ' + quant_text
    have = nums(src_all)
    have |= {n[2:] for n in list(have) if len(n) == 4 and n.startswith('20')}
    months = {'Jan': '1', 'Feb': '2', 'Mar': '3', 'Apr': '4', 'May': '5', 'Jun': '6', 'Jul': '7', 'Aug': '8', 'Sep': '9', 'Oct': '10', 'Nov': '11', 'Dec': '12'}
    for k, v in months.items():
        if k in src_all:
            have.add(v)
    return have


def check_numbers(out, cells, quant_text):
    """정리본 숫자 중 (원문 ∪ 정량 블록)에 없는 것 → [(섹션, 부서, 라벨, [숫자])]. 영어 월 이름(Sep 등)을 숫자로 옮긴 경우는 허용."""
    src_all = ' '.join(c['text'] for c in cells) + ' ' + quant_text
    have = nums(src_all)
    have |= {n[2:] for n in list(have) if len(n) == 4 and n.startswith('20')}      # 2026 FW → 26FW 같은 시즌 약어 허용
    months = {'Jan': '1', 'Feb': '2', 'Mar': '3', 'Apr': '4', 'May': '5', 'Jun': '6', 'Jul': '7', 'Aug': '8', 'Sep': '9', 'Oct': '10', 'Nov': '11', 'Dec': '12'}
    for k, v in months.items():
        if k in src_all:
            have.add(v)
    flags = []
    for sec, depts in (out or {}).items():
        for dept, val in (depts or {}).items():
            if val is None:
                continue
            items = val.items() if isinstance(val, dict) else [('전략', val)]
            for lab, v in items:
                if not v:
                    continue
                texts = v if isinstance(v, list) else [v]
                flat = []
                for t in texts:
                    flat += t if isinstance(t, list) else [t]
                bad = sorted({n for t in flat if t for n in nums(t) if n not in have})
                if bad:
                    flags.append((sec, dept, lab, bad))
    return flags


CHECK_PROMPT = """너는 영업일지 정리본의 사실 검증 담당이다. 아래 [원문]과 [정량]만 근거로 [정리본]의 각 문장을 검사한다.
원문·정량에 직접 나오지 않는 내용(원문에 없는 범주·원인·평가·결론·범위 확대, 예: '모두', '전 채널', '~판매 부진'처럼 원문이 말하지 않은 표현)이 있는 문장만 찾아 JSON 배열로 답한다.
숫자·고유명사가 같아도 의미를 바꾸거나 일반화하거나 이유를 덧붙였으면 문제로 본다. 문제가 없으면 [].
형식: [{"위치": "sec6/영업/결과/핵심", "문장": "...", "문제": "원문에 없는 ~", "원문근거": "가장 가까운 원문 구절 또는 없음"}]
설명 없이 JSON 배열만."""


def verify_claims(out, cells, quant_text='', model=None):
    """2차 호출: 정리본 문장이 원문에 근거하는지 검사. 숫자 관문이 못 잡는 '말 바꿈·범위 확대'를 사람이 검수할 항목으로 올린다."""
    src = '\n'.join(f"- 섹션{c['sec']} / {c['dept']} / {c['item']}: {c['text']}" for c in cells)
    q = quant_text.strip() or '(없음)'
    prompt = '\n\n'.join([CHECK_PROMPT, '[정량]\n' + q, '[원문]\n' + src, '[정리본]\n' + json.dumps(out, ensure_ascii=False)])
    txt = call_claude(prompt, model=model, label='검증')
    m = re.search(r'\[.*\]', txt, re.S)
    return json.loads(m.group(0)) if m else []


def summarize(ent, period, cells, quant_text='', model=None):
    prompt = build_prompt(ent, period, cells, quant_text)
    out = parse_json(call_claude(prompt, model=model, label='요약'))
    return out, check_numbers(out, cells, quant_text)


TRANS_PROMPT = """아래는 한국어 영업일지 정리본(JSON)이다. 문자열 값만 {lang} 로 번역해 같은 구조의 JSON 한 개만 출력한다.
- 키, 구조, 배열 길이, 숫자, 퍼센트, 고유명사(매장명·브랜드·약어 NGA·MG·UPT·ATV·SS·FW·B2B·EC 등)는 그대로 둔다.
- 의미를 바꾸거나 덧붙이거나 줄이지 않는다. null 은 null 로 둔다.
- 업무 보고서 문체로 간결하게."""


def _texts(x):
    if isinstance(x, dict):
        return [t for v in x.values() for t in _texts(v)]
    if isinstance(x, list):
        return [t for v in x for t in _texts(v)]
    return [x] if isinstance(x, str) else []


def translate_struct(ko_struct, lang_name, model=None):
    """한글 정리본(sec5/sec6/sec7 구조)을 다른 언어로 번역. 구조와 숫자가 원본과 같을 때만 반환, 아니면 None.
    번역은 Gemini 우선. 걸리면 이유를 알려 Gemini 로 한 번 더(Claude 로 넘기지 않음), Gemini 키가 없을 때만 Claude."""
    prompt = base_prompt = TRANS_PROMPT.format(lang=lang_name) + '\n\n' + json.dumps(ko_struct, ensure_ascii=False)
    def shape(x):
        if isinstance(x, dict):
            return {k: shape(v) for k, v in x.items()}
        if isinstance(x, list):
            return [shape(v) for v in x]
        return None
    ko_text = ' '.join(_texts(ko_struct))
    want = nums(ko_text)
    months = set(re.findall(r'(\d{1,2})\s*월', ko_text))              # '9월' 은 영어에서 'September' 로 숫자가 사라지는 것이 자연스럽다

    if '두 자릿수' in ko_text:                                          # 'two-digit'·'double-digit'·'2-digit' 어느 쪽으로 번역해도 허용 (HK 9월 영어 번역이 '2' 때문에 계속 걸렸음)
        want.add('2')
        months.add('2')
    man_src, man_ok = set(), set()                                    # '3,693만' 은 영어·중국어에서 36,930,000 / 36.93m / 3,693萬 처럼 단위가 바뀐다 (값은 같음)
    for m_ in re.findall(r'(\d[\d,]*(?:\.\d+)?)\s*만', ko_text):
        try:
            v_ = float(m_.replace(',', '')) * 10000
        except ValueError:
            continue
        man_src.add(m_)
        man_ok |= {f'{v_:,.0f}', f'{v_ / 1e6:g}', f'{v_ / 1e6:.2f}', f'{v_ / 1e3:,.0f}', f'{v_ / 1e3:g}', f'{v_ / 1e4:,.0f}', m_}
    pct = set(re.findall(r'(\d[\d,.]*)\s*%', ko_text))                  # 퍼센트 숫자는 빠지면 안 된다
    spelled = set()                                                   # 'six weeks'·'Singles Day'·'雙11' 처럼 풀어쓰면 숫자가 사라진다 — 의미는 같으므로 빠져도 허용
    for n_ in want:
        if re.fullmatch(r'\d{1,2}\.\d{1,2}', n_) or (n_.isdigit() and int(n_) <= 12 and n_ not in pct):
            spelled.add(n_)

    def problem(out):
        """번역이 원본과 어긋난 점. 없으면 ''. 숫자는 새로 생기면 안 되고, 월(月) 숫자만 빠져도 된다."""
        if shape(out) != shape(ko_struct):
            return '구조(키·배열 길이)가 다름'
        got = nums(' '.join(_texts(out)))
        extra, missing = sorted(got - want - man_ok), sorted(n for n in want - got if n not in months and n not in man_src and n not in spelled)
        if extra or missing:
            return f'숫자 늘어남 {extra} / 빠짐 {missing}'
        return ''
    use_claude = os.environ.get('WJ_TRANSLATOR', 'auto').lower() == 'claude'
    ask = (lambda p: call_claude(p, model=model, label=f'번역({lang_name[:2]})')) if use_claude else call_gemini
    who = 'Claude' if use_claude else 'Gemini'
    key_missing = False
    for attempt in (1, 2):
        try:
            out = parse_json(ask(prompt))
        except RuntimeError as ex:
            if use_claude:
                raise                                                      # 사용 한도 등은 위에서 처리한다
            if 'gemini 키 없음' in str(ex):
                key_missing = True
                break
            print(f'[알림] Gemini 호출 실패({attempt}/2): {ex!r}'[:200])
            time.sleep(GEMINI_RETRY_WAIT)
            continue
        except Exception as ex:                                           # 응답이 JSON 이 아닌 경우 등
            print(f'[알림] {who} 응답 해석 실패({attempt}/2): {ex!r}'[:200])
            continue
        why = problem(out)
        if not why:
            return out
        print(f'[알림] {who} 번역이 검사에 걸림({attempt}/2) — {why}')
        prompt = base_prompt + f'\n\n[이전 번역의 문제] {why}. 숫자와 구조를 원문과 똑같이 맞춰 다시 번역한다.'
    if not key_missing:
        print(f'[알림] 번역을 채우지 못함 — {who} 재시도 한계. 다른 번역기로 넘기지 않음(사용량 절약). 다음 실행에서 번역만 다시 시도합니다.')
        return None
    out = parse_json(call_claude(base_prompt, model=model, label=f'번역({lang_name[:2]})'))               # Gemini 키가 없을 때만 Claude 로 번역
    why = problem(out)
    if why:
        print(f'[알림] Claude 번역이 검사에 걸려 버림 — {why}')
        return None
    return out


def demo_tw():
    import _sum_sample as S
    import _sum_sample_v4 as V
    cells = [{'sec': c[0], 'dept': c[2], 'item': c[3], 'text': c[4]} for c in S.CELLS]
    quant = ('대만 9월 유통별 실적(백만 TWD가 아니라 천 TWD 단위 표 기준 달성률): 전체 목표 대비 86.5%, 전년 대비 +2.8%. '
             '백화점 71.6% (전년 -24.5%), 아울렛 134.7% (전년 +34.0%), 팝업 139.9%, 온라인 70.7% (전년 -10.8%).')
    out, flags = summarize('대만', '2026년 9월', cells, quant)
    path = os.path.join(HERE, '_summary_demo_tw.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'out': out, 'flags': flags}, f, ensure_ascii=False, indent=1)
    print('저장:', path, '/ 숫자 검수 대상:', flags)
    return out


def demo_hk():
    import _sum_sample_hk as HK
    cells = [{'sec': c[0], 'dept': c[2], 'item': c[3], 'text': c[4]} for c in HK.CELLS]
    out, flags = summarize('홍콩', '2026년 9월', cells, '')
    path = os.path.join(HERE, '_summary_demo_hk.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'out': out, 'flags': flags}, f, ensure_ascii=False, indent=1)
    print('저장:', path, '/ 숫자 검수 대상:', flags)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--demo-tw', action='store_true')
    ap.add_argument('--demo-hk', action='store_true')
    ap.add_argument('--check-hk', action='store_true')
    a = ap.parse_args()
    if a.demo_tw:
        demo_tw()
    elif a.demo_hk:
        demo_hk()
    elif a.check_hk:
        import _sum_sample_hk as HK
        cells = [{'sec': c[0], 'dept': c[2], 'item': c[3], 'text': c[4]} for c in HK.CELLS]
        out = json.load(open(os.path.join(HERE, '_summary_demo_hk.json'), encoding='utf-8'))['out']
        w = verify_claims(out, cells)
        json.dump(w, open(os.path.join(HERE, '_summary_demo_hk_warn.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('경고', len(w), '건')
    else:
        print(__doc__)
