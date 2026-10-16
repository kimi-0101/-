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
from pathlib import Path

APP_VERSION = '0.2.0'
APP_TITLE = '주간영업일지'
SESSION_HOURS = 24            # 서버의 로그인 유지(1일)와 맞춤
PAGE_TTL = 3 * 24 * 3600      # 저장해 둔 화면을 이 기간까지는 '먼저 바로' 열어 준다 (숫자는 화면 위의 '데이터 기준'에 표시됨)
REFRESH_AFTER = 5 * 60        # 저장된 지 이보다 오래된 화면은 열어 주면서 뒤에서 새로 받아 둔다
PAGE_RE = re.compile(r'^(journal|summary|monthly|yearly|msummary|ysummary|bep)_(HK|TW)(@(W|M)\d{1,2})?$')
PREFETCH = ('journal', 'summary', 'monthly', 'msummary', 'yearly', 'ysummary', 'bep')


def data_dir():
    base = os.environ.get('LOCALAPPDATA') or os.path.join(str(Path.home()), '.local', 'share')
    d = Path(base) / 'WJApp'
    d.mkdir(parents=True, exist_ok=True)
    return d


class UpstreamError(Exception):
    pass


def log(st, msg):
    """걸린 시간 등을 화면에 찍고 app.log 에도 남긴다 (느릴 때 어디서 걸리는지 보려는 용도)."""
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
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
        try:
            return json.loads(self._cpath(name).read_text(encoding='utf-8'))
        except Exception:
            return None

    def cache_put(self, name, r):
        c = dict(name=name, html=r['html'], status=r.get('status', ''), asOf=r.get('asOf', ''), at=time.time())
        tmp = self._cpath(name).with_suffix('.tmp')
        tmp.write_text(json.dumps(c, ensure_ascii=False), encoding='utf-8')
        tmp.replace(self._cpath(name))             # 쓰는 도중 꺼져도 반쪽 파일이 남지 않게 교체 방식으로 저장

    def cache_clear(self):
        for f in (self.root / 'cache').glob('*.json'):
            f.unlink()


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


def prefetch(st, delay=3.0):
    """뒤에서 자주 여는 화면을 미리 받아 둔다 (첫 화면을 여는 동안은 방해하지 않도록 잠깐 뒤에 시작)."""
    me = (st.session or {}).get('me') or {}
    ents = ['HK', 'TW'] if me.get('ent') in ('ALL', '', None) else [me['ent']]
    first = default_page(st)

    def run():
        time.sleep(delay)
        names = [f'{k}_{e}' for e in ents for k in PREFETCH]
        for n in names:
            if n == first or not st.session:
                continue
            c = st.cache_get(n)
            if c and time.time() - c['at'] < REFRESH_AFTER:
                continue
            try:
                load_now(st, n)
            except Exception:
                pass
            time.sleep(0.5)
    threading.Thread(target=run, daemon=True).start()


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
<input id="n" placeholder="이름 (화면에 표시)" maxlength="30"><button type="submit" id="b">로그인</button><div id="m"></div></form>
<script>var n=document.getElementById('n');try{n.value=localStorage.getItem('wj_name')||''}catch(e){}
document.getElementById('f').addEventListener('submit',function(ev){ev.preventDefault();
var id=i.value.trim(),pw=w.value,who=n.value.trim(),m=document.getElementById('m');
if(!id||!pw||!who){m.textContent='아이디, 비밀번호, 이름을 입력하세요.';return;}
b.disabled=true;m.textContent='로그인 중…';
fetch('/app/login',{method:'POST',body:JSON.stringify({id:id,password:pw,who:who})}).then(function(r){return r.json()}).then(function(r){
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
            if path == '/login' or not st.session:
                return self._send(200, LOGIN_HTML.replace('__VER__', APP_VERSION))
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
                    prefetch(st)
                    return self._json({'ok': True})
                return self._json({'ok': False, 'error': r.get('error', '로그인 실패')})
            if path == '/app/refresh':                            # '최신 데이터 받기' 버튼: 그 화면을 서버에서 새로 받아 저장
                name = str(body.get('name', ''))
                if not st.session:
                    return self._json({'ok': False, 'auth': True})
                if PAGE_RE.match(name):
                    r = fetch_page(st, name, fresh=True)
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
                return self._json({'ok': True})
            body['token'] = st.session['token']                    # 그 밖의 요청(저장, 번역, 불러오기 …)은 진짜 열쇠를 붙여 기존 서버로 전달
            try:
                r = upstream(st, body, retries=2 if a in ('pull', 'pullMany', 'archive', 'presence') else 0)
            except UpstreamError:
                return self._json({'ok': False, 'error': '서버에 연결하지 못했습니다.'})
            if r.get('auth'):
                st.clear_session()
            return self._json(r)
    return H


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):      # 창을 닫으며 끊긴 연결 등은 조용히 넘긴다
        pass


def start_server(st, port=0):
    srv = Server(('127.0.0.1', port), make_handler(st))
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
        print('서버 주소가 없습니다. --api-url 을 주거나 api_url.txt 를 이 프로그램 옆에 두세요.')
        return 2
    st = State(url)
    if a.reset:
        st.clear_session()
        st.cache_clear()
    mv = os.environ.get('WJ_MIN_VERSION_URL')
    if mv:
        ok, need = check_min_version(mv)
        if not ok:
            print(f'이 앱({APP_VERSION})은 너무 오래되었습니다. {need} 이상으로 업데이트하세요.')
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
