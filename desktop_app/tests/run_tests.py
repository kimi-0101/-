# -*- coding: utf-8 -*-
"""앱 + 가짜 서버를 띄우고 실제 브라우저(playwright)로 끝까지 시험한다.  사용: python run_tests.py"""
import http.server, json, os, shutil, socketserver, subprocess, sys, tempfile, threading, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mock_server, wj_app

mock = mock_server.Mock(); msrv = mock_server.start(mock)
tmp = tempfile.mkdtemp(); st = wj_app.State(mock.url, root=tmp); srv = wj_app.start_server(st)

class Ctl(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query); k = q.get('q', [''])[0]; out = {}
        if k == 'url': out = {'url': mock.url}
        elif k == 'count': out = {'n': mock.count(q['a'][0])}
        elif k == 'lasttoken': out = {'token': [t for a, t in mock.calls if a == q['a'][0]][-1]}
        elif k == 'ttl0': st.page_ttl = 0
        elif k == 'offline': mock.offline = q['v'][0] == '1'
        elif k == 'expire': mock.expire = q['v'][0] == '1'
        b = json.dumps(out).encode(); self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    def handle_error(self, *a): pass
csrv = S(('127.0.0.1', 0), Ctl); threading.Thread(target=csrv.serve_forever, daemon=True).start()
env = dict(os.environ, NODE_PATH=os.environ.get('NODE_PATH', '/opt/node22/lib/node_modules'))
rc = subprocess.call(['node', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'browser_test.js'), f'http://127.0.0.1:{st.port}', st.key, f'http://127.0.0.1:{csrv.server_address[1]}/'], env=env)
shutil.rmtree(tmp, ignore_errors=True); sys.exit(rc)
