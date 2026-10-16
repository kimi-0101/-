# -*- coding: utf-8 -*-
"""Apps Script 흉내 서버 (시험용): 로그인·화면·저장 요청에 답하고, 받은 요청을 기록한다."""
import http.server, json, socketserver, threading

REAL_TOKEN = 'REALTOKEN_0123456789'

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>__NAME__</title></head><body>
<h1>__NAME__</h1><a href="#" data-go="__OTHER__" id="go">GO</a>
<script>var API='__API__';
function tok(){try{return localStorage.getItem('wj_tok_TW')||''}catch(e){return ''}}
window.wjGo=function(name){return fetch(API,{method:'POST',headers:{'Content-Type':'text/plain;charset=utf-8'},body:JSON.stringify({a:'page',name:name,token:tok()})}).then(function(r){return r.json()}).then(function(r){if(!r.ok){if(r.auth){location.reload();}return;}document.open();document.write(r.html);document.close();});};
document.addEventListener('click',function(ev){var a=ev.target.closest('a[data-go]');if(!a)return;ev.preventDefault();window.wjGo(a.getAttribute('data-go'));});
window.__save=function(){return fetch(API,{method:'POST',headers:{'Content-Type':'text/plain;charset=utf-8'},body:JSON.stringify({a:'save',cellId:'TW|W40|MD|x|ko',html:'hi',base:0,token:tok()})}).then(function(r){return r.json()});};
</script></body></html>"""


class Mock:
    def __init__(self):
        self.calls = []          # (action, token)
        self.offline = False
        self.expire = False
        self.url = ''
        self.pages = {}

    def page_html(self, name):
        if name in self.pages:
            return self.pages[name].replace('__API__', self.url)
        other = 'summary_TW' if name.startswith('journal') else 'journal_TW'
        return PAGE.replace('__NAME__', name.upper()).replace('__OTHER__', other).replace('__API__', self.url)

    def count(self, a):
        return sum(1 for x, _ in self.calls if x == a)


def start(mock):
    class H(http.server.BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'
        def log_message(self, *a): pass
        def _out(self, code, body, ctype='application/json'):
            b = body.encode('utf-8') if isinstance(body, str) else body
            self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
        def do_POST(self):
            n = int(self.headers.get('Content-Length') or 0)
            req = json.loads(self.rfile.read(n).decode('utf-8'))
            a, tok = req.get('a'), req.get('token', '')
            mock.calls.append((a, tok))
            if mock.offline:
                return self._out(404, '<!DOCTYPE html><html>Not Found</html>', 'text/html')
            if a == 'login':
                if req.get('id') == 'tw' and req.get('password') == 'pw12345678':
                    return self._out(200, json.dumps({'ok': True, 'token': REAL_TOKEN, 'me': {'id': 'tw', 'ent': 'TW', 'role': 'writer', 'name': req.get('who')}}))
                return self._out(200, json.dumps({'ok': False, 'error': 'The ID or password is incorrect.'}))
            if tok != REAL_TOKEN or mock.expire:
                return self._out(200, json.dumps({'ok': False, 'auth': True, 'error': '다시 로그인하세요.'}))
            if a == 'page':
                return self._out(200, json.dumps({'ok': True, 'html': mock.page_html(req['name']), 'status': 'final', 'asOf': '2026-10-16 10:00'}))
            if a == 'save':
                return self._out(200, json.dumps({'ok': True, 'version': 1}))
            if a == 'logout':
                return self._out(200, json.dumps({'ok': True}))
            return self._out(200, json.dumps({'ok': True}))
    class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        def handle_error(self, *a): pass
    srv = S(('127.0.0.1', 0), H)
    mock.url = f'http://127.0.0.1:{srv.server_address[1]}/exec'
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
