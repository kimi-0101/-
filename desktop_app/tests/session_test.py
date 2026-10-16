# -*- coding: utf-8 -*-
"""로그인 정보 저장(암호화) 시험.  사용: python tests/session_test.py   (윈도우에서는 실제 DPAPI, 그 밖에는 가짜 암호화로 흐름을 점검)"""
import json, os, sys, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import wj_app

fails = 0
def check(ok, msg):
    global fails
    print(('PASS: ' if ok else 'FAIL: ') + msg)
    fails += 0 if ok else 1

if sys.platform != 'win32':                                   # 윈도우 아닌 환경: 뒤집기만 하는 가짜 암호화로 파일 흐름을 점검
    wj_app._dpapi = lambda data, protect: data[::-1]

tmp = tempfile.mkdtemp()
try:
    st = wj_app.State('http://x', root=tmp)
    st.set_session('SECRET-TOKEN', {'ent': 'TW', 'role': 'admin'}, '홍길동')
    raw = (st.root / 'session.json').read_bytes()
    check(b'SECRET-TOKEN' not in raw, '파일에 열쇠(토큰)가 그대로 보이지 않음' + ('' if sys.platform == 'win32' else ' (가짜 암호화)'))
    check(raw.startswith(b'DPAPI1'), '암호화 표시가 붙음')
    s2 = wj_app.State('http://x', root=tmp).session
    check(bool(s2) and s2['token'] == 'SECRET-TOKEN' and s2['who'] == '홍길동', '다시 시작해도 로그인이 복원됨')
    (st.root / 'session.json').write_text(json.dumps(dict(token='OLD', me={}, who='a', at=__import__('time').time())), encoding='utf-8')
    check((wj_app.State('http://x', root=tmp).session or {}).get('token') == 'OLD', 'v0.2 이전 평문 파일도 읽힘')
    (st.root / 'session.json').write_bytes(b'DPAPI1' + b'!!notbase64!!')
    check(wj_app.State('http://x', root=tmp).session is None, '깨진 파일이면 로그인 화면으로 (오류 없이)')
finally:
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(1 if fails else 0)
