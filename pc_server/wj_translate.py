# -*- coding: utf-8 -*-
"""영업일지 PC 서버의 자동 번역 — Code.gs 의 LanguageApp.translate 를 대신한다.

엔진은 Gemini(기존 요약기와 같은 키). 키 위치(앞에서부터):
  환경변수 GEMINI_API_KEY → <프로젝트>/wj_data/gemini_key.txt → <프로젝트>/apps_script/weekly_journal/gemini_key.txt
HTML 칸이므로 글자만 번역하고 태그 구조는 그대로 두게 시키며, 결과의 태그 순서가 원문과 다르면 버린다(서식이 깨진 번역을 저장하지 않기 위해).
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
