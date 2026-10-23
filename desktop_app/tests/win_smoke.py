# -*- coding: utf-8 -*-
"""윈도우 실제 환경 점검 (CI 의 windows 러너에서 실행): 윈도우 암호화(DPAPI) 왕복, 앱 서버 기동, 로그인 화면, 자동 로그인 저장/복구.
실행:  python desktop_app/tests/win_smoke.py
"""
import http.client
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import mock_server   # noqa: E402
import wj_app        # noqa: E402


wj_app.safe_console()                                   # 윈도우 콘솔(cp1252)이 한글 때문에 죽지 않게


def check(cond, msg):
    print(('PASS: ' if cond else 'FAIL: ') + msg, flush=True)
    if not cond:
        raise SystemExit(1)


def main():
    check(sys.platform == 'win32', '윈도우에서 실행 중 (%s)' % sys.platform)
    blob = wj_app.protect_bytes('비밀번호-secret'.encode('utf-8'))
    check(bool(blob) and b'secret' not in blob, 'DPAPI 암호화: 결과에 원문이 들어 있지 않음')
    check(wj_app.unprotect_bytes(blob) == '비밀번호-secret'.encode('utf-8'), 'DPAPI 복호화: 원문으로 돌아옴')
    check(wj_app.unprotect_bytes(b'garbage-not-dpapi') is None, 'DPAPI: 엉뚱한 데이터는 풀리지 않고 None')

    mock = mock_server.Mock()
    mock_server.start(mock)
    tmp = tempfile.mkdtemp()
    st = wj_app.State(mock.url, root=tmp)
    wj_app.start_server(st)
    check(st.can_remember(), '이 PC 에서 자동 로그인 사용 가능')

    def req(method, path, body=None):
        c = http.client.HTTPConnection('127.0.0.1', st.port, timeout=20)
        c.request(method, path, json.dumps(body) if body is not None else None, {'Cookie': 'wjk=' + st.key})
        r = c.getresponse()
        data = r.read().decode('utf-8')
        c.close()
        return r.status, data

    s, body = req('GET', '/')
    check(s == 200 and '<form id="f">' in body and 'id="rm"' in body, '앱 서버가 뜨고 로그인 화면에 자동 로그인 선택 칸이 보임')
    s, body = req('POST', '/app/login', {'id': 'tw', 'password': 'pw12345678', 'who': 't', 'remember': True})
    check(json.loads(body).get('ok') is True, '로그인 성공')
    check(os.path.exists(os.path.join(tmp, 'cred.bin')) and b'pw12345678' not in open(os.path.join(tmp, 'cred.bin'), 'rb').read(),
          '자동 로그인 정보가 암호화되어 저장됨 (파일에 비밀번호 없음)')
    st.clear_session()
    s, body = req('GET', '/')
    check(s == 200 and '<form id="f">' not in body and st.session is not None, '다음에 열면 입력 없이 자동 로그인되어 일지 화면이 열림')
    s, body = req('POST', '/api', {'a': 'pull', 'ent': 'TW', 'week': 'W40', 'photos': True})
    check(json.loads(body).get('ok') is True, '글 데이터 요청이 앱을 거쳐 응답')
    s, body = req('POST', '/api', {'a': 'pull', 'ent': 'TW', 'week': 'W40', 'photos': True})
    check(json.loads(body).get('cached') is True, '두 번째 요청은 PC 저장본으로 응답')
    req('POST', '/api', {'a': 'logout'})
    check(not os.path.exists(os.path.join(tmp, 'cred.bin')), '로그아웃하면 자동 로그인 정보가 지워짐')
    print('ALL OK')


if __name__ == '__main__':
    main()
