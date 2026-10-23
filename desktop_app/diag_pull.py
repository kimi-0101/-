# -*- coding: utf-8 -*-
"""일지 글 데이터(pullMany)가 왜 저장본으로 빨라지지 않는지 주 단위로 보여 주는 진단 도구. 읽기 요청만 보낸다.

  python desktop_app\\diag_pull.py --api-url <서버 주소> --id tw --password <비밀번호> [--weeks W40 W41 ...]
"""
import argparse
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wj_app  # noqa: E402
import bench  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--api-url')
    ap.add_argument('--id', required=True)
    ap.add_argument('--password', required=True)
    ap.add_argument('--weeks', nargs='*')
    a = ap.parse_args(argv)
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors='replace')
        except Exception:
            pass
    url = wj_app.load_api_url(a.api_url)
    st = wj_app.State(url, root=tempfile.mkdtemp(prefix='wjdiag_'))
    wj_app.log = lambda st_, msg: None
    r = wj_app.upstream(st, {'a': 'login', 'id': a.id, 'password': a.password, 'who': 'diag'}, retries=0)
    if not r.get('ok'):
        print('[중단] 로그인 실패:', r.get('error'))
        return 1
    st.set_session(r['token'], r.get('me') or {}, 'diag')
    me = r.get('me') or {}
    ent = me.get('ent') if me.get('ent') in ('HK', 'TW') else 'TW'
    weeks = a.weeks or bench.week_codes()
    print(f'로그인 me={ {k: me.get(k) for k in ("id", "ent", "role")} }  법인={ent}  주={weeks}')
    for photos in (True, False):
        print(f'\n--- photos={photos} ---')
        body = {'a': 'pullMany', 'ent': ent, 'weeks': weeks, 'photos': photos}
        for n in (1, 2):
            t = time.perf_counter()
            res = wj_app.handle_pull(st, dict(body))
            dt = time.perf_counter() - t
            rows = []
            for w, x in zip(weeks, (res or {}).get('results') or []):
                rows.append(f"{w}: {'ok' if x.get('ok') else 'X ' + str(x.get('error'))[:40]}{' (저장본)' if x.get('cached') else ''} 칸{len(x.get('cells') or {})}")
            print(f'{n}번째 {dt:.2f}초  ' + ' | '.join(rows) if rows else f'{n}번째 {dt:.2f}초  결과 없음: {str(res)[:120]}')
        cachedir = os.path.join(st.root, 'cache')
        files = [(f, os.path.getsize(os.path.join(cachedir, f))) for f in os.listdir(cachedir)] if os.path.isdir(cachedir) else []
        print('저장본 파일:', ', '.join(f'{f[:14]}.. {s // 1024}KB' for f, s in files) or '없음')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
