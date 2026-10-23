# -*- coding: utf-8 -*-
"""주간영업일지 데스크톱 앱 (시제품 v0.1)

구조
  앱 창(pywebview) ──▶ 내 PC 안의 작은 서버(127.0.0.1) ──▶ 기존 서버(Apps Script)
  · 화면(HTML)은 한 번 받으면 PC에 저장해 두고 바로 연다 (서버를 다시 부르지 않음 → 빠름)
  · 화면 안의 서버 주소는 이 앱의 주소(/api)로 바꿔 보낸다 → 기존 화면 코드는 고치지 않는다
  · 로그인 열쇠(토큰)는 앱(파이썬)만 들고 있고, 화면 안의 자바스크립트에는 넘기지 않는다
  · 글·사진 저장 등은 기존 서버로 그대로 전달한다 (나중에 서버가 바뀌면 이 파일의 주소만 바꾸면 됨)

실행:  python wj_app.py                 (앱 창)
       python wj_app.py --browser       (앱 창 대신 기본 브라우저로 열기: 시험용)
"""
import argparse
import datetime
import hashlib
import http.cookies
import http.server
import json
import os
import re
import secrets
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

APP_VERSION = '0.4.0'
APP_TITLE = '주간영업일지'
SESSION_HOURS = 24            # 서버의 로그인 유지(1일)와 맞춤
PAGE_TTL = 3 * 24 * 3600      # 저장해 둔 화면을 이 기간까지는 '먼저 바로' 열어 준다 (숫자는 화면 위의 '데이터 기준'에 표시됨)
REFRESH_AFTER = 5 * 60        # 저장된 지 이보다 오래된 화면은 열어 주면서 뒤에서 새로 받아 둔다
DATA_FRESH = 15               # 글 데이터 저장본이 이 초보다 새것이면 서버를 부르지 않고 그대로 준다
OPEN_GAP = 30                 # 같은 데이터를 이 초 넘게 안 불렀다가 부르면 '화면을 새로 연 것'으로 보고, 오래된 저장본이라도 먼저 주고 뒤에서 새로 받는다
                              # (그 안에 되풀이되는 요청은 화면이 주기적으로 확인하는 것으로 보고, DATA_FRESH 보다 오래됐으면 서버에서 받는다)
DATA_TTL = 14 * 24 * 3600     # 이 기간이 지난 저장본은 쓰지 않는다
WEEK_RE = re.compile(r'^[WM]\d{1,2}$')
PHOTO_CELL = re.compile(r'\|(vcomp|vthis)_p[1-4]\|ko$')
SUMFILL_RE = re.compile(r'<[^>]*\bid="sumfill"[^>]*>')
PAGE_RE = re.compile(r'^(journal|summary|monthly|yearly|msummary|ysummary|bep)_(HK|TW)(@(W|M)\d{1,2})?$')
PREFETCH = ('journal', 'summary', 'monthly', 'msummary', 'yearly', 'ysummary', 'bep')


def safe_console():
    """콘솔(윈도우 cp1252/cp949 등)이 한글을 못 쓰는 글자로 만나도 앱이 죽지 않게, 못 쓰는 글자는 ?로 바꿔 출력한다.
    바로가기(pythonw)로 켠 경우처럼 콘솔이 없으면(sys.stdout 이 None) 할 일이 없다."""
    for s_ in (sys.stdout, sys.stderr):
        try:
            if s_ is not None:
                s_.reconfigure(errors='replace')
        except Exception:
            pass


def atomic_write(path, text):
    """반쪽 파일이 남지 않게 임시 파일에 쓴 뒤 교체한다. 임시 파일 이름은 호출마다 달라서(스레드·프로세스 구분) 같은 칸을 동시에 갱신해도 서로 덮어쓰지 않는다.
    윈도우는 읽는 중인 파일 위로 교체하면 잠깐 PermissionError 가 나므로 짧게 다시 시도한다."""
    path = Path(path)
    tmp = path.with_name(f'{path.name}.{os.getpid()}.{threading.get_ident()}.{secrets.token_hex(3)}.tmp')
    tmp.write_text(text, encoding='utf-8')
    try:
        for i in range(8):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if i == 7:
                    raise
                time.sleep(0.05 * (i + 1))
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def data_dir():
    base = os.environ.get('LOCALAPPDATA') or os.path.join(str(Path.home()), '.local', 'share')
    d = Path(base) / 'WJApp'
    d.mkdir(parents=True, exist_ok=True)
    return d


def _dpapi(data, protect):
    """윈도우 사용자 계정으로 암호화/복호화(DPAPI). 윈도우가 아니면 None 을 돌려준다(= 자동 로그인 사용 불가)."""
    if sys.platform != 'win32':
        return None
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]
    buf = ctypes.create_string_buffer(data, len(data))
    inp, out = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), BLOB()
    fn = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    if not fn(ctypes.byref(inp), None, None, None, None, 0, ctypes.byref(out)):
        return None
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def protect_bytes(b):
    return _dpapi(b, True)


def unprotect_bytes(b):
    return _dpapi(b, False)


class UpstreamError(Exception):
    pass


def notify(msg):
    """오류를 화면에 알린다. 바로가기(pythonw)로 켠 경우엔 콘솔이 없어서 print 만으로는 보이지 않으므로 윈도우 메시지 창도 띄운다."""
    try:
        print(msg)
    except Exception:
        pass
    if sys.stdout is None or not getattr(sys.stdout, 'isatty', lambda: False)():
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, str(msg), APP_TITLE, 0x10)
        except Exception:
            pass                                                # 윈도우가 아니면(시험 환경 등) 메시지 창 없이 넘어간다


def log(st, msg):
    """걸린 시간 등을 화면에 찍고 app.log 에도 남긴다 (느릴 때 어디서 걸리는지 보려는 용도)."""
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    try:
        print(line, flush=True)
    except Exception:                                           # 콘솔이 한글을 못 쓰거나(cp1252 등) 닫혀 있어도 로그 한 줄 때문에 요청 처리가 죽지 않게
        try:
            print(line.encode('ascii', 'replace').decode('ascii'), flush=True)
        except Exception:
            pass
    try:
        with open(st.root / 'app.log', 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except OSError:
        pass


class State:
    def __init__(self, api_url, root=None):
        self.api_url = api_url.strip()
        self.root = Path(root) if root else data_dir()
        (self.root / 'cache').mkdir(parents=True, exist_ok=True)
        self.key = secrets.token_urlsafe(24)       # 이 앱을 연 창만 아는 열쇠 (같은 PC의 다른 프로그램이 내 로그인을 쓰지 못하게)
        self.lock = threading.Lock()
        self.session = self._load_session()
        self.page_ttl = PAGE_TTL
        self.inflight = {}
        self.dinflight = set()                     # 뒤에서 새로 받는 중인 글 데이터 (같은 것을 겹쳐 받지 않게)
        self.last_req = {}                         # 글 데이터 이름 → 마지막으로 요청받은 시각
        self.port = 0

    # ---- 로그인 상태 ----
    def _load_session(self):
        p = self.root / 'session.json'
        try:
            s = json.loads(p.read_text(encoding='utf-8'))
            if time.time() - s.get('at', 0) < SESSION_HOURS * 3600 and s.get('token'):
                return s
        except Exception:
            pass
        return None

    def set_session(self, token, me, who):
        self.session = dict(token=token, me=me, who=who, at=time.time())
        (self.root / 'session.json').write_text(json.dumps(self.session, ensure_ascii=False), encoding='utf-8')
        try:
            os.chmod(self.root / 'session.json', 0o600)
        except OSError:
            pass

    # ---- 자동 로그인 (선택): 아이디·비밀번호를 이 윈도우 계정으로만 풀 수 있게 암호화해 저장 ----
    def can_remember(self):
        return protect_bytes(b'x') is not None

    def save_cred(self, uid, pw, who):
        blob = protect_bytes(json.dumps({'id': uid, 'password': pw, 'who': who}, ensure_ascii=False).encode('utf-8'))
        if blob is None:
            return False
        (self.root / 'cred.bin').write_bytes(blob)
        try:
            os.chmod(self.root / 'cred.bin', 0o600)
        except OSError:
            pass
        return True

    def load_cred(self):
        try:
            raw = unprotect_bytes((self.root / 'cred.bin').read_bytes())
            return json.loads(raw.decode('utf-8')) if raw else None
        except Exception:
            return None

    def forget_cred(self):
        try:
            (self.root / 'cred.bin').unlink()
        except OSError:
            pass

    def clear_session(self):
        self.session = None
        try:
            (self.root / 'session.json').unlink()
        except OSError:
            pass

    # ---- 화면 저장소 ----
    def _cpath(self, name):
        return self.root / 'cache' / (name.replace('@', '_at_') + '.json')

    def cache_get(self, name):
        for _ in range(25):
            try:
                return json.loads(self._cpath(name).read_text(encoding='utf-8'))
            except PermissionError:                                   # 윈도우: 다른 스레드가 저장본을 교체하는 순간에는 잠깐 열 수 없다 → 없는 것으로 보지 말고 다시 시도
                time.sleep(0.03)
            except Exception:
                return None
        return None

    def cache_put(self, name, r):
        c = dict(name=name, html=r['html'], status=r.get('status', ''), asOf=r.get('asOf', ''), at=time.time())
        atomic_write(self._cpath(name), json.dumps(c, ensure_ascii=False))     # 쓰는 도중 꺼져도 반쪽 파일이 남지 않게 교체 방식으로 저장

    def cache_clear(self):
        for f in (self.root / 'cache').glob('*.json'):
            f.unlink()

    # ---- 글 데이터 저장소 (일지 글·사진 pull, 보관 목록 archive) ----
    def uid(self):
        return ((self.session or {}).get('me') or {}).get('id', '')

    def _dpath(self, key):
        return self.root / 'cache' / ('data_' + hashlib.sha1(key.encode('utf-8')).hexdigest()[:20] + '.json')

    def data_get(self, key):
        """저장본. 다른 사람이 저장한 것이거나 너무 오래됐으면 None (같은 PC 를 여러 명이 쓸 때 남의 권한으로 받은 글이 보이지 않게)."""
        e = None
        for _ in range(25):
            try:
                e = json.loads(self._dpath(key).read_text(encoding='utf-8'))
                break
            except PermissionError:                                   # 윈도우: 다른 스레드가 교체하는 순간
                time.sleep(0.02)
            except Exception:
                return None
        if e is None:
            return None
        if e.get('key') != key or e.get('uid') != self.uid() or time.time() - e.get('at', 0) > DATA_TTL:
            return None
        return e

    def data_put(self, key, fields, at=None):
        e = dict(fields, key=key, uid=self.uid(), at=time.time() if at is None else at)
        atomic_write(self._dpath(key), json.dumps(e, ensure_ascii=False))
        return e

    def data_keys(self):
        """저장해 둔 글 데이터의 이름 목록 (내 것만)"""
        out = []
        for f in (self.root / 'cache').glob('data_*.json'):
            try:
                e = json.loads(f.read_text(encoding='utf-8'))
            except Exception:
                continue
            if e.get('uid') == self.uid() and time.time() - e.get('at', 0) <= DATA_TTL:
                out.append(e['key'])
        return out

    # ---- 내가 쓴 글의 기록 (서버가 안 되거나 충돌이 나도 입력한 글이 남도록) ----
    def save_log(self, rec):
        try:
            d = self.root / 'backup'
            d.mkdir(exist_ok=True)
            f = d / ('saves_' + datetime.date.today().strftime('%Y-%m') + '.jsonl')
            with open(f, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
        except OSError:
            pass


def upstream(st, body, retries=1, timeout=120):
    """기존 서버(Apps Script)에 요청. 읽기 요청만 재시도한다 (저장은 재시도하면 '이미 저장됨'이 충돌로 보일 수 있어 하지 않음)."""
    data = json.dumps(body).encode('utf-8')
    last = None
    for i in range(retries + 1):
        t0 = time.time()
        try:
            req = urllib.request.Request(st.api_url, data=data, headers={'Content-Type': 'text/plain;charset=utf-8'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.loads(r.read().decode('utf-8'))
            log(st, f"[서버] {body.get('a')} {body.get('name', '')} {time.time() - t0:.1f}초" + (f" (재시도 {i}번째)" if i else ''))
            return out
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as ex:
            last = ex
            log(st, f"[서버] {body.get('a')} {body.get('name', '')} 실패 {time.time() - t0:.1f}초: {repr(ex)[:80]}")
            if i < retries:
                time.sleep(1.5 * (i + 1))
    raise UpstreamError(repr(last)[:200])


def load_now(st, name):
    """서버에서 화면을 받아 저장한다. 같은 화면을 동시에 여러 곳에서 부르면 한 번만 받고 나머지는 기다린다."""
    with st.lock:
        ev = st.inflight.get(name)
        owner = ev is None
        if owner:
            ev = st.inflight[name] = threading.Event()
    if not owner:
        ev.wait(130)
        c = st.cache_get(name)
        if c:
            return {'ok': True, 'html': c['html'], 'status': c['status'], 'asOf': c['asOf'], 'cached': True}
        return {'ok': False, 'auth': not st.session, 'error': '화면을 받지 못했습니다.'}
    try:
        tok = (st.session or {}).get('token', '')
        r = upstream(st, {'a': 'page', 'name': name, 'token': tok}, retries=2)
        if r.get('ok'):
            st.cache_put(name, r)
            prefetch_data_for_html(st, r.get('html', ''))
        elif r.get('auth'):
            st.clear_session()
        return r
    finally:
        with st.lock:
            st.inflight.pop(name, None)
        ev.set()


def fetch_page(st, name, fresh=False):
    """화면 하나를 가져온다. 서버가 돌려주는 모양({ok, html, ...}) 그대로 반환.
    저장해 둔 화면이 있으면 서버를 기다리지 않고 바로 내주고, 오래됐으면 뒤에서 새로 받아 둔다."""
    t0 = time.time()
    if not (st.session or {}).get('token'):
        return {'ok': False, 'auth': True, 'error': '다시 로그인하세요.'}
    c = st.cache_get(name)
    age = time.time() - c['at'] if c else None
    if c and not fresh and age < st.page_ttl:
        if age > REFRESH_AFTER:
            refresh_later(st, name)
        log(st, f"[화면] {name} 저장본 {time.time() - t0:.2f}초 (저장된 지 {int(age // 60)}분)")
        return {'ok': True, 'html': c['html'], 'status': c['status'], 'asOf': c['asOf'], 'cached': True}
    try:
        r = load_now(st, name)
    except UpstreamError:
        if c:                                         # 인터넷이 안 되면 저장해 둔 화면(조금 오래된 것)이라도 연다
            return {'ok': True, 'html': c['html'], 'status': c['status'], 'asOf': c['asOf'], 'cached': True, 'stale': True}
        return {'ok': False, 'error': '서버에 연결하지 못했습니다.'}
    log(st, f"[화면] {name} 서버에서 받음 {time.time() - t0:.1f}초")
    return r


def refresh_later(st, name):
    def run():
        try:
            load_now(st, name)
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


def prefetch(st, delay=3.0, workers=3):
    """뒤에서 자주 여는 화면과 글 데이터를 미리 받아 둔다 (첫 화면을 여는 동안은 방해하지 않도록 잠깐 뒤에 시작).
    화면은 workers 개씩 동시에 받는다 — 하나씩 받으면 처음 설치한 날·로그인 직후에 모두 받아지기까지 오래 걸린다."""
    me = (st.session or {}).get('me') or {}
    ents = ['HK', 'TW'] if me.get('ent') in ('ALL', '', None) else [me['ent']]
    first = default_page(st)

    def pages():
        time.sleep(delay)
        names = [f'{k}_{e}' for e in ents for k in PREFETCH]

        def one(n):
            if n == first or not st.session:
                return
            c = st.cache_get(n)
            if c and time.time() - c['at'] < REFRESH_AFTER:
                return
            try:
                load_now(st, n)
            except Exception:
                pass
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(one, names))

    def data():
        time.sleep(delay)
        try:
            refresh_all_data(st)                                       # 지난번에 쓴 글 데이터를 새로 받아 둔다 (화면 받기와 동시에)
        except Exception:
            pass
    threading.Thread(target=pages, daemon=True).start()
    threading.Thread(target=data, daemon=True).start()


# ---------------------------------------------------------------------------------------------------------
# 글 데이터(일지 글·사진, 보관 목록) 저장본: 화면을 바꿀 때마다 화면 안의 스크립트가 구글에 새로 묻던 것을 PC 에서 바로 답한다.
# 저장·마감 같은 쓰기는 항상 서버로 가고(버전 충돌 검사는 서버가 함), 저장본은 그 결과로 바로 고쳐 둔다.
# ---------------------------------------------------------------------------------------------------------
def pull_key(ent, week, photos):
    return f'pull|{ent}|{week}|{1 if photos else 0}'


def fetch_weeks(st, ent, weeks, photos, retries=2):
    """서버에서 여러 주를 한 번에(pullMany) 받아 저장본을 고치고, {주: 결과} 로 돌려준다. 서버가 안 되면 UpstreamError."""
    r = upstream(st, {'a': 'pullMany', 'ent': ent, 'weeks': list(weeks), 'photos': bool(photos), 'token': (st.session or {}).get('token', '')}, retries=retries)
    if r.get('auth'):
        st.clear_session()
        return {w: r for w in weeks}
    got = {}
    res = r.get('results') if r.get('ok') else None
    for i, w in enumerate(weeks):
        one = res[i] if res and i < len(res) else {'ok': False, 'error': r.get('error', '받지 못했습니다.')}
        got[w] = one
        if one.get('ok'):
            st.data_put(pull_key(ent, w, photos), {'closed': one.get('closed', False), 'cells': one.get('cells', {})})
    return got


def as_pull_result(st, e):
    return {'ok': True, 'me': (st.session or {}).get('me') or {}, 'closed': e.get('closed', False), 'cells': e.get('cells', {}),
            'presence': {}, 'now': int(time.time() * 1000), 'cached': True}


def refresh_data_later(st, ent, weeks, photos):
    todo = [w for w in weeks if (ent, w, photos) not in st.dinflight]
    if not todo:
        return
    with st.lock:
        st.dinflight.update((ent, w, photos) for w in todo)

    def run():
        try:
            fetch_weeks(st, ent, todo, photos)
        except Exception:
            pass
        finally:
            with st.lock:
                for w in todo:
                    st.dinflight.discard((ent, w, photos))
    threading.Thread(target=run, daemon=True).start()


def handle_pull(st, body):
    """pull / pullMany. 저장본이 있으면 서버를 기다리지 않고 답한다 (규칙은 위 DATA_FRESH / OPEN_GAP 설명)."""
    a, ent, photos = body.get('a'), body.get('ent'), bool(body.get('photos'))
    weeks = body.get('weeks') if a == 'pullMany' else [body.get('week')]
    if ent not in ('HK', 'TW') or not isinstance(weeks, list) or not 0 < len(weeks) <= 60 or not all(isinstance(w, str) and WEEK_RE.match(w) for w in weeks):
        return None                                                  # 모양이 이상하면 저장본을 쓰지 않고 서버가 판단하게 한다
    now = t0 = time.time()
    out, live, stale = {}, [], []
    for w in dict.fromkeys(weeks):
        key = pull_key(ent, w, photos)
        opened = now - st.last_req.get(key, 0) > OPEN_GAP
        st.last_req[key] = now
        e = st.data_get(key)
        if e and now - e['at'] < DATA_FRESH:
            out[w] = as_pull_result(st, e)
        elif e and opened:
            out[w] = as_pull_result(st, e)
            stale.append(w)
        else:
            live.append(w)
    if live:
        try:
            got = fetch_weeks(st, ent, live, photos, retries=1)          # 사용자가 기다리는 요청이라 재시도는 한 번만
        except UpstreamError:
            got = {}
            for w in live:                                          # 인터넷이 안 되면 오래된 저장본이라도 준다
                e = st.data_get(pull_key(ent, w, photos))
                got[w] = dict(as_pull_result(st, e), stale=True) if e else {'ok': False, 'error': '서버에 연결하지 못했습니다.'}
        for w in live:
            if got[w].get('auth'):
                return got[w]
        out.update(got)
    if stale:
        refresh_data_later(st, ent, stale, photos)
    log(st, f"[글] {ent} {','.join(dict.fromkeys(weeks))} {time.time() - t0:.2f}초 (저장본 {len(out) - len(live)}개 / 서버 {len(live)}개)")
    if a == 'pull':
        return out[weeks[0]]
    return {'ok': True, 'results': [out[w] for w in weeks]}


def handle_archive(st, body):
    now = time.time()
    opened = now - st.last_req.get('archive', 0) > OPEN_GAP
    st.last_req['archive'] = now
    e = st.data_get('archive')
    if e and (now - e['at'] < DATA_FRESH or opened):
        if now - e['at'] >= DATA_FRESH and 'archive' not in st.dinflight:
            st.dinflight.add('archive')

            def run():
                try:
                    refresh_archive(st)
                except Exception:
                    pass
                finally:
                    st.dinflight.discard('archive')
            threading.Thread(target=run, daemon=True).start()
        return {'ok': True, 'weeks': e.get('weeks', []), 'cached': True}
    try:
        return refresh_archive(st)
    except UpstreamError:
        if e:
            return {'ok': True, 'weeks': e.get('weeks', []), 'cached': True, 'stale': True}
        return {'ok': False, 'error': '서버에 연결하지 못했습니다.'}


def refresh_archive(st):
    r = upstream(st, {'a': 'archive', 'token': (st.session or {}).get('token', '')}, retries=2)
    if r.get('auth'):
        st.clear_session()
    elif r.get('ok'):
        st.data_put('archive', {'weeks': r.get('weeks', [])})
    return r


def prefetch_data_for_html(st, html):
    """받아 온 화면 안의 'sumfill' 표시(법인·주차)를 읽어, 그 화면이 열릴 때 요청할 글 데이터를 미리 받아 둔다."""
    m = SUMFILL_RE.search(html or '')
    if not m:
        return
    ent = re.search(r'data-ent="(HK|TW)"', m.group(0))
    week = re.search(r'data-week="([WM]\d{1,2})"', m.group(0))
    if not (ent and week):
        return
    key = pull_key(ent.group(1), week.group(1), True)                    # 화면은 사진까지(photos:true) 요청한다
    e = st.data_get(key)
    if e and time.time() - e['at'] < DATA_FRESH:
        return
    refresh_data_later(st, ent.group(1), [week.group(1)], True)


def refresh_all_data(st):
    """저장해 둔 글 데이터를 모두 서버에서 새로 받는다 (법인·사진 여부별로 묶어서 한 번에). 새로 받은 주 수를 돌려준다."""
    groups = {}
    for key in st.data_keys():
        if key == 'archive':
            continue
        _, ent, week, ph = key.split('|')
        groups.setdefault((ent, ph == '1'), []).append(week)
    n = 0
    for (ent, ph), weeks in groups.items():
        for i in range(0, len(weeks), 60):
            try:
                got = fetch_weeks(st, ent, weeks[i:i + 60], ph)
                n += sum(1 for r in got.values() if r.get('ok'))
            except UpstreamError:
                pass
    if 'archive' in st.data_keys():
        try:
            refresh_archive(st)
        except UpstreamError:
            pass
    return n


def apply_writes(st, body, r):
    """저장·마감이 서버에서 성공한 뒤 저장본을 바로 고치고, 번역 등 서버가 더 바꾼 칸은 뒤에서 새로 받는다."""
    a = body.get('a')
    me = (st.session or {}).get('me') or {}
    who = f"{me.get('id', '')} ({(st.session or {}).get('who', '')})"
    iso = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    weeks = set()
    if a in ('save', 'saveMany'):
        items = body.get('items') if a == 'saveMany' else [{'cellId': body.get('cellId'), 'html': body.get('html')}]
        results = r.get('results') if a == 'saveMany' else [r]
        for it, res in zip(items or [], results or []):
            cid = str(it.get('cellId', ''))
            parts = cid.split('|')
            if len(parts) != 5 or not isinstance(res, dict):
                continue
            ent, week = parts[0], parts[1]
            if res.get('ok'):
                cell = {'html': str(it.get('html') or ''), 'version': res.get('version'), 'by': who, 'at': iso, 'auto': False}
            elif res.get('conflict') and isinstance(res.get('current'), dict):
                c = res['current']
                cell = {'html': c.get('html', ''), 'version': c.get('version'), 'by': c.get('by', ''), 'at': c.get('at', ''), 'auto': False}
            else:
                continue
            for ph in (False, True):
                e = st.data_get(pull_key(ent, week, ph))
                if e:
                    e['cells'][cid] = dict(cell, html=None) if (not ph and PHOTO_CELL.search(cid)) else cell
                    st.data_put(pull_key(ent, week, ph), {'closed': e.get('closed', False), 'cells': e['cells']}, at=e['at'])
            weeks.add((ent, week))
    elif a == 'close' and r.get('ok'):
        for ph in (False, True):
            e = st.data_get(pull_key(body.get('ent'), body.get('week'), ph))
            if e:
                st.data_put(pull_key(body.get('ent'), body.get('week'), ph), {'closed': bool(body.get('closed')), 'cells': e['cells']}, at=e['at'])
        weeks.add((body.get('ent'), body.get('week')))
    elif a == 'translate':
        for cid in body.get('cellIds') or []:
            parts = str(cid).split('|')
            if len(parts) == 5:
                weeks.add((parts[0], parts[1]))
    for ent, week in weeks:                                              # 번역으로 다른 언어 칸이 바뀌었을 수 있으니 그 주는 뒤에서 새로 받는다
        for ph in (False, True):
            if st.data_get(pull_key(ent, week, ph)):
                refresh_data_later(st, ent, [week], ph)


def log_write(st, body, r, failed=False):
    a = body.get('a')
    me = (st.session or {}).get('me') or {}
    items = body.get('items') if a == 'saveMany' else [{'cellId': body.get('cellId'), 'html': body.get('html'), 'base': body.get('base')}]
    rec_items = []
    for it in items or []:
        cid = str(it.get('cellId', ''))
        photo = bool(PHOTO_CELL.search(cid)) or bool(re.search(r'_p\d+\|', cid))
        rec_items.append({'cellId': cid, 'base': it.get('base'), 'html': None if photo else it.get('html'), 'htmlLen': len(str(it.get('html') or ''))})
    results = ['connection-failed'] if failed else [('ok:%s' % x.get('version') if x.get('ok') else ('conflict' if x.get('conflict') else 'error:%s' % x.get('error')))
                                                    for x in ((r.get('results') if a == 'saveMany' else [r]) or []) if isinstance(x, dict)]
    st.save_log({'t': datetime.datetime.now().isoformat(timespec='seconds'), 'who': f"{me.get('id', '')} ({(st.session or {}).get('who', '')})",
                 'a': a, 'items': rec_items, 'results': results})


def auto_login(st):
    """저장해 둔 아이디·비밀번호로 조용히 로그인한다. 비밀번호가 바뀌어 거절당하면 저장본을 지우고 로그인 화면으로 보낸다."""
    c = st.load_cred()
    if not c:
        return False
    try:
        r = upstream(st, {'a': 'login', 'id': c.get('id', ''), 'password': c.get('password', ''), 'who': c.get('who', '')}, retries=1)
    except UpstreamError:
        return False                                                  # 인터넷 문제면 저장해 둔 정보는 그대로 두고 로그인 화면을 보여 준다
    if r.get('ok'):
        st.set_session(r['token'], r.get('me') or {}, str(c.get('who', ''))[:30])
        prefetch(st, delay=0.3)
        return True
    st.forget_cred()
    return False


def default_page(st):
    me = (st.session or {}).get('me') or {}
    ent = me.get('ent') if me.get('ent') in ('HK', 'TW') else 'TW'
    return f'journal_{ent}'


def js(x):
    return json.dumps(x, ensure_ascii=False).replace('<', '\\u003c')


def rewrite(st, html, name=''):
    """화면 안의 서버 주소를 이 앱의 /api 로 바꾸고, 로그인 열쇠 자리표시자를 넣는다 (진짜 열쇠는 화면에 넘기지 않는다).
    오른쪽 아래에 작은 '↻ 최신 데이터 받기' 버튼도 붙인다."""
    h = html.replace(st.api_url, '/api') if st.api_url else html
    s = st.session or {}
    inj = ('<script>try{localStorage.setItem("wj_tok_HK","app");localStorage.setItem("wj_tok_TW","app");'
           'localStorage.setItem("wj_who",%s);localStorage.setItem("wj_role",%s);}catch(e){}</script>'
           % (js(s.get('who', '')), js((s.get('me') or {}).get('role', ''))))
    h = h.replace('<head>', '<head>' + inj, 1) if '<head>' in h else inj + h
    bar = ('<div id="wjapp" style="position:fixed;right:10px;bottom:8px;z-index:99999;font:11px sans-serif;background:rgba(17,17,17,.82);'
           'color:#fff;padding:4px 10px;border-radius:12px;opacity:.8">앱 v' + APP_VERSION + ' · <a href="#" id="wjrf" style="color:#9cf;text-decoration:none">↻ 최신 데이터 받기</a></div>'
           '<script>(function(){var nm=%s,a=document.getElementById("wjrf");if(!a)return;a.onclick=function(e){e.preventDefault();a.textContent="받는 중…";'
           'fetch("/app/refresh",{method:"POST",body:JSON.stringify({name:nm})}).then(function(){if(window.__wjC)delete window.__wjC[nm];'
           'if(window.wjGo&&nm){return window.wjGo(nm);}location.reload();}).then(function(){a.textContent="↻ 최신 데이터 받기";});};})();</script>' % js(name))
    i = h.rfind('</body>')
    return h[:i] + bar + h[i:] if i >= 0 else h + bar


LOGIN_HTML = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>주간영업일지</title>
<style>body{margin:0;font-family:"Malgun Gothic",system-ui,sans-serif;background:#f4f5f7;display:flex;min-height:100vh;align-items:center;justify-content:center}
form{background:#fff;border-radius:12px;padding:24px;width:340px;display:flex;flex-direction:column;gap:10px;box-shadow:0 10px 40px rgba(0,0,0,.12)}
h3{margin:0}input{font:inherit;padding:9px 10px;border:1px solid #d1d5db;border-radius:8px}
button{font:inherit;padding:9px;border:0;border-radius:8px;background:#111;color:#fff;cursor:pointer}#m{color:#b45309;font-size:12px;min-height:16px}small{color:#6b7280}</style></head><body>
<form id="f"><h3>Weekly Sales Journal</h3><small>앱 v__VER__</small>
<input id="i" placeholder="ID" autocomplete="username"><input id="w" type="password" placeholder="Password" autocomplete="current-password">
<input id="n" placeholder="이름 (화면에 표시)" maxlength="30">__REM__<button type="submit" id="b">로그인</button><div id="m"></div></form>
<script>var n=document.getElementById('n');try{n.value=localStorage.getItem('wj_name')||''}catch(e){}
document.getElementById('f').addEventListener('submit',function(ev){ev.preventDefault();
var id=i.value.trim(),pw=w.value,who=n.value.trim(),m=document.getElementById('m');
if(!id||!pw||!who){m.textContent='아이디, 비밀번호, 이름을 입력하세요.';return;}
b.disabled=true;m.textContent='로그인 중…';
var rm=document.getElementById('rm');fetch('/app/login',{method:'POST',body:JSON.stringify({id:id,password:pw,who:who,remember:!!(rm&&rm.checked)})}).then(function(r){return r.json()}).then(function(r){
 if(r.ok){try{localStorage.setItem('wj_name',who)}catch(e){}location.href='/';}else{m.textContent=r.error||'로그인 실패';b.disabled=false;}
}).catch(function(){m.textContent='앱 내부 오류';b.disabled=false;});});</script></body></html>"""


def make_handler(st):
    class H(http.server.BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *a):
            pass

        def _send(self, code, body=b'', ctype='text/html; charset=utf-8', extra=None):
            if isinstance(body, str):
                body = body.encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, ensure_ascii=False), 'application/json; charset=utf-8')

        def _guard(self):
            host = (self.headers.get('Host') or '').lower()
            if host not in (f'127.0.0.1:{st.port}', f'localhost:{st.port}'):
                self._send(403, 'forbidden')
                return False
            ck = http.cookies.SimpleCookie(self.headers.get('Cookie') or '')
            if not (ck.get('wjk') and secrets.compare_digest(ck['wjk'].value, st.key)):
                self._send(403, 'forbidden')
                return False
            return True

        def do_GET(self):
            path, _, qs = self.path.partition('?')
            if path == '/' and ('k=' + st.key) in qs.split('&'):         # 앱 창이 처음 열릴 때 열쇠를 쿠키로 심는다
                host = (self.headers.get('Host') or '').lower()
                if host in (f'127.0.0.1:{st.port}', f'localhost:{st.port}'):
                    return self._send(302, '', extra={'Location': '/', 'Set-Cookie': f'wjk={st.key}; Path=/; HttpOnly; SameSite=Strict'})
            if path == '/favicon.ico':
                return self._send(204)
            if not self._guard():
                return
            if path != '/login' and not st.session and auto_login(st):    # 저장해 둔 로그인 정보가 있으면 입력 없이 들어간다
                pass
            if path == '/login' or not st.session:
                rem = ('<label style="font-size:12px;color:#4b5563"><input type="checkbox" id="rm"> 이 PC 에서 자동 로그인 (암호화해 저장)</label>'
                       if st.can_remember() else '')
                return self._send(200, LOGIN_HTML.replace('__VER__', APP_VERSION).replace('__REM__', rem))
            if path == '/':
                m = re.search(r'(?:^|&)p=([^&]+)', qs)
                name = m.group(1) if m and PAGE_RE.match(m.group(1)) else default_page(st)
                r = fetch_page(st, name)
                if not r.get('ok'):
                    if r.get('auth'):
                        return self._send(302, '', extra={'Location': '/login'})
                    return self._send(503, f'<meta charset="utf-8"><body style="font-family:sans-serif;padding:40px">'
                                           f'<h3>화면을 열 수 없습니다</h3><p>{r.get("error", "")}</p><p><a href="/">다시 시도</a></p>')
                return self._send(200, rewrite(st, r['html'], name))
            self._send(404, 'not found')

        def do_POST(self):
            try:
                n = int(self.headers.get('Content-Length') or 0)
                raw = self.rfile.read(n)                      # 본문은 항상 먼저 다 읽는다 (안 읽고 응답하면 같은 연결의 다음 요청이 꼬임)
            except Exception:
                self.close_connection = True
                return self._send(400, 'bad request')
            if not self._guard():
                return
            try:
                body = json.loads(raw.decode('utf-8') or '{}')
            except Exception:
                return self._json({'ok': False, 'error': '요청 형식 오류'}, 400)
            path = self.path.split('?')[0]
            if path == '/app/login':
                try:
                    r = upstream(st, {'a': 'login', 'id': body.get('id', ''), 'password': body.get('password', ''), 'who': body.get('who', '')}, retries=0)
                except UpstreamError:
                    return self._json({'ok': False, 'error': '서버에 연결하지 못했습니다.'})
                if r.get('ok'):
                    st.set_session(r['token'], r.get('me') or {}, str(body.get('who', ''))[:30])
                    if body.get('remember'):
                        st.save_cred(str(body.get('id', '')), str(body.get('password', '')), str(body.get('who', ''))[:30])
                    else:
                        st.forget_cred()
                    prefetch(st, delay=0.3)
                    return self._json({'ok': True})
                return self._json({'ok': False, 'error': r.get('error', '로그인 실패')})
            if path == '/app/refresh':                            # '최신 데이터 받기' 버튼: 그 화면을 서버에서 새로 받아 저장
                name = str(body.get('name', ''))
                if not st.session:
                    return self._json({'ok': False, 'auth': True})
                if PAGE_RE.match(name):
                    r = fetch_page(st, name, fresh=True)
                    if r.get('ok'):
                        refresh_all_data(st)                          # 글 데이터도 함께 새로 받는다
                    return self._json({'ok': bool(r.get('ok')), 'auth': bool(r.get('auth'))})
                return self._json({'ok': False})
            if path != '/api':
                return self._json({'ok': False, 'error': 'not found'}, 404)
            a = body.get('a')
            if a == 'login':                                      # 화면이 직접 로그인하는 일은 없다
                return self._json({'ok': False, 'error': '앱에서 로그인하세요.'})
            if not st.session:
                return self._json({'ok': False, 'auth': True, 'error': '다시 로그인하세요.'})
            if a == 'page':
                name = str(body.get('name', ''))
                if not PAGE_RE.match(name):
                    return self._json({'ok': False, 'error': '페이지 이름이 올바르지 않습니다.'})
                r = fetch_page(st, name)
                if r.get('ok'):
                    r = dict(r, html=rewrite(st, r['html'], name))
                return self._json(r)
            if a == 'logout':
                try:
                    upstream(st, {'a': 'logout', 'token': st.session['token']}, retries=0, timeout=15)
                except UpstreamError:
                    pass
                st.clear_session()
                st.forget_cred()                                       # 로그아웃하면 자동 로그인 정보도 지운다
                return self._json({'ok': True})
            if a in ('pull', 'pullMany'):                          # 글 데이터: 저장본이 있으면 바로 답한다
                r = handle_pull(st, body)
                if r is not None:
                    return self._json(r)
            if a == 'archive':
                return self._json(handle_archive(st, body))
            body['token'] = st.session['token']                    # 그 밖의 요청(저장, 번역, 불러오기 …)은 진짜 열쇠를 붙여 기존 서버로 전달
            is_write = a in ('save', 'saveMany')
            try:
                r = upstream(st, body, retries=2 if a in ('pull', 'pullMany', 'archive', 'presence') else 0)
            except UpstreamError:
                if is_write:
                    log_write(st, body, {}, failed=True)
                return self._json({'ok': False, 'error': '서버에 연결하지 못했습니다.'})
            if r.get('auth'):
                st.clear_session()
            elif a in ('save', 'saveMany', 'close', 'translate') and isinstance(r, dict):
                if is_write:
                    log_write(st, body, r)
                try:
                    apply_writes(st, body, r)
                except Exception as ex:                                # 저장본 갱신이 실패해도 저장 결과는 그대로 돌려준다
                    log(st, f'[저장본] 갱신 실패: {ex!r}')
            return self._json(r)
    return H


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    st = None

    def handle_error(self, request, client_address):      # 창을 닫으며 끊긴 연결 등은 조용히 넘기고, 그 밖의 예외는 app.log 에 남긴다(원인을 알 수 있게)
        exc = sys.exc_info()[1]
        if self.st is not None and not isinstance(exc, (ConnectionError, TimeoutError, OSError)):
            log(self.st, f'[오류] 요청 처리 중 예외: {exc!r}')


def start_server(st, port=0):
    srv = Server(('127.0.0.1', port), make_handler(st))
    srv.st = st
    st.port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def load_api_url(cli):
    here = Path(sys.argv[0]).resolve().parent
    cands = [cli, os.environ.get('WJ_API_URL'),
             here / 'api_url.txt', data_dir() / 'api_url.txt',
             here.parent / 'apps_script' / 'weekly_journal' / 'api_url.txt']
    for c in cands:
        if not c:
            continue
        if isinstance(c, Path):
            if c.exists():
                return c.read_text(encoding='utf-8').strip()
        else:
            return str(c).strip()
    return ''


def check_min_version(url):
    """(선택) 너무 낡은 버전은 실행을 막는다. url 은 {"min_version": "0.1.0"} 같은 JSON 주소."""
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            need = json.loads(r.read().decode('utf-8')).get('min_version', '0')
        a = tuple(int(x) for x in APP_VERSION.split('.'))
        b = tuple(int(x) for x in str(need).split('.'))
        return a >= b, need
    except Exception:
        return True, ''                                        # 확인 실패 시에는 막지 않는다


def main(argv=None):
    safe_console()
    ap = argparse.ArgumentParser(description=APP_TITLE)
    ap.add_argument('--api-url', help='서버(Apps Script) 주소. 없으면 api_url.txt 또는 환경변수 WJ_API_URL')
    ap.add_argument('--browser', action='store_true', help='앱 창 대신 기본 브라우저로 열기 (시험용)')
    ap.add_argument('--reset', action='store_true', help='저장된 로그인과 화면 저장본을 지우고 시작')
    ap.add_argument('--version', action='store_true')
    a = ap.parse_args(argv)
    if a.version:
        print(APP_VERSION)
        return 0
    url = load_api_url(a.api_url)
    if not url:
        notify('서버 주소가 없습니다. api_url.txt 를 이 프로그램 옆에 두거나 --api-url 을 주세요.')
        return 2
    st = State(url)
    if a.reset:
        st.clear_session()
        st.forget_cred()
        st.cache_clear()
    mv = os.environ.get('WJ_MIN_VERSION_URL')
    if mv:
        ok, need = check_min_version(mv)
        if not ok:
            notify(f'이 앱({APP_VERSION})은 너무 오래되었습니다. {need} 이상으로 업데이트하세요.')
            return 3
    start_server(st)
    if st.session:                                             # 어제 로그인이 아직 유효하면 열기 전에 미리 받아 둔다
        prefetch(st, delay=1.0)
    start_url = f'http://127.0.0.1:{st.port}/?k={st.key}'
    if a.browser:
        print('열기:', start_url, '(Ctrl+C 로 종료)')
        webbrowser.open(start_url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return 0
    try:
        import webview
    except ImportError:
        print('pywebview 가 없어 브라우저로 엽니다. (pip install pywebview)')
        webbrowser.open(start_url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return 0
    webview.create_window(APP_TITLE, start_url, width=1500, height=950, min_size=(1000, 600))
    webview.start()
    return 0


if __name__ == '__main__':
    sys.exit(main())
