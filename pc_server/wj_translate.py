# -*- coding: utf-8 -*-
"""영업일지 PC 서버의 자동 번역 — 지금까지 Code.gs 가 쓰던 구글 번역(LanguageApp.translate)을 그대로 쓰되, PC 서버에서 부른다.

엔진 (앞에서부터 시도, 하나라도 되면 끝):
 1) 구글 번역 — 번역만 하는 작은 Apps Script(pc_server/translate_proxy.gs)를 부른다. 일지 데이터는 저장되지 않고 번역할 글만 오간다.
    주소·열쇠: 환경변수 WJ_TRANSLATE_URL / WJ_TRANSLATE_KEY 또는 <프로젝트>/wj_data/translate_url.txt (첫 줄 주소, 둘째 줄 열쇠)
 2) Gemini(예비) — 구글 번역이 실패했을 때만. 키: 환경변수 GEMINI_API_KEY → <프로젝트>/wj_data/gemini_key.txt → <프로젝트>/apps_script/weekly_journal/gemini_key.txt
    HTML 칸이라 글자만 번역하게 시키고, 결과의 태그 순서가 원문과 다르면 버린다(서식이 깨진 번역을 저장하지 않기 위해).
"""
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KEY_FILES = (os.path.join(ROOT, 'wj_data', 'gemini_key.txt'),
             os.path.join(ROOT, 'apps_script', 'weekly_journal', 'gemini_key.txt'))
MODEL = 'gemini-2.5-flash'
FALLBACK_MODEL = 'gemini-flash-latest'
LANG_NAME = {'ko': 'Korean', 'en': 'English', 'zh': 'Traditional Chinese (Taiwan, zh-TW)'}
TAG = re.compile(r'<[^>]*>')


class TranslateError(Exception):
    pass


def find_key():
    k = os.environ.get('GEMINI_API_KEY', '').strip()
    if k:
        return k
    for p in KEY_FILES:
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                k = f.read().strip()
            if k:
                return k
    return ''


def _tag_shape(html):
    """태그 이름·순서만 비교한다(속성 값이나 대소문자·자기닫힘 표기 차이는 무시)."""
    out = []
    for t in TAG.findall(html):
        m = re.match(r'</?\s*([A-Za-z][A-Za-z0-9]*)', t)
        if m:
            out.append(('/' if t.startswith('</') else '') + m.group(1).lower())
    return out


def _strip_fence(s):
    s = s.strip()
    m = re.match(r'^```[a-zA-Z]*\n([\s\S]*?)\n?```$', s)
    return m.group(1) if m else s


def _http_post(url, headers, body, timeout):
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


class GeminiTranslator:
    def __init__(self, key, model=None, post=None, sleep=time.sleep, retry_wait=4, max_attempts=4, timeout=60, concurrency=2):
        self.key = key
        self.models = [model or os.environ.get('GEMINI_MODEL', MODEL), FALLBACK_MODEL]
        self.post = post or _http_post
        self.sleep = sleep
        self.retry_wait = retry_wait
        self.max_attempts = max_attempts
        self.timeout = timeout
        self.sem = threading.Semaphore(concurrency)          # 무료 키는 분당 호출 수 제한이 작아서 동시에 몇 개만

    @classmethod
    def from_env(cls, **kw):
        key = find_key()
        return cls(key, **kw) if key else None

    def _prompt(self, html, src, dst):
        return ('Translate the visible text of the following HTML fragment from %s to %s.\n'
                'Rules: keep every HTML tag, attribute and the tag order exactly as they are; translate only the text between tags. '
                'Keep numbers, units, currencies, percent signs, dates, product codes, store names and brand names (e.g. TNH, NATGEO) unchanged. '
                'Write natural business language. Output ONLY the translated HTML fragment: no explanation, no code fence.\n\n%s'
                % (LANG_NAME[src], LANG_NAME[dst], html))

    def _call(self, prompt):
        body = json.dumps({'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'temperature': 0}}).encode('utf-8')
        mi, attempt, last = 0, 0, ''
        while mi < len(self.models) and attempt < self.max_attempts:
            url = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent' % self.models[mi]
            try:
                with self.sem:
                    res = self.post(url, {'Content-Type': 'application/json', 'x-goog-api-key': self.key}, body, self.timeout)
            except urllib.error.HTTPError as ex:
                last = 'gemini HTTP %d' % ex.code
                if ex.code == 404 and mi + 1 < len(self.models):
                    mi += 1                                  # 모델 이름이 사라졌으면 별칭으로
                    continue
                if ex.code in (429, 500, 502, 503, 504):
                    attempt += 1
                    self.sleep(self.retry_wait * attempt)
                    continue
                raise TranslateError(last)
            except (urllib.error.URLError, TimeoutError, OSError) as ex:
                last = 'gemini 연결 실패: %r' % (ex,)
                attempt += 1
                self.sleep(self.retry_wait)
                continue
            try:
                return res['candidates'][0]['content']['parts'][0]['text']
            except (KeyError, IndexError, TypeError):
                raise TranslateError('gemini 응답 없음: ' + json.dumps(res, ensure_ascii=False)[:200])
        raise TranslateError(last or 'gemini 호출 실패')

    def translate(self, html, src, dst):
        """html 의 글자를 src → dst 로 번역해 같은 태그 구조의 html 로 돌려준다. 실패하면 TranslateError."""
        if src not in LANG_NAME or dst not in LANG_NAME or src == dst:
            raise TranslateError('언어 코드가 올바르지 않습니다.')
        want = _tag_shape(html)
        for _ in range(2):                                   # 태그 구조가 틀어지면 한 번 더
            out = _strip_fence(self._call(self._prompt(html, src, dst)))
            if out and _tag_shape(out) == want:
                return out
        raise TranslateError('번역 결과의 태그 구조가 원문과 달라 버렸습니다.')


TRANSLATE_URL_FILE = os.path.join(ROOT, 'wj_data', 'translate_url.txt')
GOOGLE_LANG = {'ko': 'ko', 'en': 'en', 'zh': 'zh-TW'}


def find_google_proxy():
    """(주소, 열쇠) — 없으면 ('', '')"""
    url, key = os.environ.get('WJ_TRANSLATE_URL', '').strip(), os.environ.get('WJ_TRANSLATE_KEY', '').strip()
    if not url and os.path.exists(TRANSLATE_URL_FILE):
        with open(TRANSLATE_URL_FILE, encoding='utf-8') as f:
            lines = [x.strip() for x in f.read().splitlines() if x.strip()]
        url, key = (lines + ['', ''])[:2]
    return url, key


class GoogleTranslator:
    """구글 번역(LanguageApp)을 부르는 Apps Script 웹앱(translate_proxy.gs)을 통해 번역한다."""

    def __init__(self, url, key, post=None, timeout=60):
        self.url, self.key, self.timeout = url, key, timeout
        self.post = post or (lambda u, h, b, t: _http_post(u, h, b, t))

    @classmethod
    def from_env(cls, **kw):
        url, key = find_google_proxy()
        return cls(url, key, **kw) if url and key else None

    def translate(self, html, src, dst):
        if src not in GOOGLE_LANG or dst not in GOOGLE_LANG or src == dst:
            raise TranslateError('언어 코드가 올바르지 않습니다.')
        body = json.dumps({'key': self.key, 'text': html, 'src': GOOGLE_LANG[src], 'dst': GOOGLE_LANG[dst]}).encode('utf-8')
        try:
            res = self.post(self.url, {'Content-Type': 'text/plain;charset=utf-8'}, body, self.timeout)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as ex:
            raise TranslateError('구글 번역 연결 실패: %r' % (ex,))
        if not isinstance(res, dict) or not res.get('ok'):
            raise TranslateError('구글 번역 실패: ' + str((res or {}).get('error') if isinstance(res, dict) else res)[:200])
        out = str(res.get('text') or '')
        if not out.strip():
            raise TranslateError('구글 번역 결과가 비어 있습니다.')
        return out


class ChainTranslator:
    """앞 엔진이 실패하면 다음 엔진으로. 모두 실패하면 마지막 오류를 올린다."""

    def __init__(self, engines):
        self.engines = list(engines)

    def translate(self, html, src, dst):
        last = None
        for e in self.engines:
            try:
                return e.translate(html, src, dst)
            except TranslateError as ex:
                last = ex
        raise last or TranslateError('번역 엔진이 없습니다.')

    def names(self):
        return [{'GoogleTranslator': '구글 번역', 'GeminiTranslator': 'Gemini'}.get(type(e).__name__, type(e).__name__) for e in self.engines]


def build_translator():
    """설정된 엔진을 묶어 돌려준다. 하나도 없으면 None(자동 번역 꺼짐)."""
    engines = [e for e in (GoogleTranslator.from_env(), GeminiTranslator.from_env()) if e]
    if not engines:
        return None
    return engines[0] if len(engines) == 1 else ChainTranslator(engines)


def engine_names(tr):
    if tr is None:
        return []
    return tr.names() if isinstance(tr, ChainTranslator) else ChainTranslator([tr]).names()
