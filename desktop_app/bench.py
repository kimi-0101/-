# -*- coding: utf-8 -*-
"""앱 속도 실측 도구 — 실제 서버(구글 또는 PC 서버)에 대해 '저장본이 없을 때(처음)'와 '있을 때(앱이 쓰는 방식)'를 재서 비교한다.

  python bench.py run --api-url <서버 주소> --id tw --who 홍길동        (비밀번호는 입력창에서 받음. --password 로도 가능)
  python bench.py log [--file %LOCALAPPDATA%\\WJApp\\app.log]              앱을 쓰며 쌓인 app.log 를 동작별 평균·중앙값·최대로 요약

run 이 재는 것 (모두 이 PC 에서, 임시 폴더를 쓰므로 평소 앱의 저장본·로그인은 건드리지 않음):
  로그인 / 첫 화면 / 화면 7개 이동 / 글 데이터(pullMany) / 지난 주 목록(archive)
  각각 '처음(저장본 없음 = 서버 속도)' 과 '두 번째(앱의 저장본)' 시간, 그리고 몇 배 빨라졌는지.
읽기 요청만 보내며 서버의 데이터를 바꾸지 않는다.
"""
import argparse
import getpass
import os
import re
import statistics
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wj_app  # noqa: E402


def timed(fn):
    t0 = time.perf_counter()
    r = fn()
    return time.perf_counter() - t0, r


def week_codes(n=4, today=None):
    import datetime
    d = today or datetime.date.today()
    wk = d.isocalendar()[1]
    return [f'W{w}' for w in range(max(1, wk - n + 1), wk + 1)]


def run(api_url, uid, pw, who, say=print, weeks=None, silent_log=True):
    root = tempfile.mkdtemp(prefix='wjbench_')
    st = wj_app.State(api_url, root=root)
    if silent_log:
        wj_app.log = lambda st_, msg: None                      # 측정 중에는 앱 로그를 남기지 않는다
    rows = []

    def add(name, cold, warm, note=''):
        rows.append((name, cold, warm, note))

    t, r = timed(lambda: wj_app.upstream(st, {'a': 'login', 'id': uid, 'password': pw, 'who': who}, retries=0))
    if not r.get('ok'):
        raise RuntimeError('로그인 실패: ' + str(r.get('error')))
    st.set_session(r['token'], r.get('me') or {}, who)
    add('로그인 (매일 처음 한 번)', t, None, '저장본 없음 — 서버 속도')
    me = r.get('me') or {}
    ents = ['HK', 'TW'] if me.get('ent') in ('ALL', '', None) else [me['ent']]
    ent = ents[0]
    first = wj_app.default_page(st)

    c, rr = timed(lambda: wj_app.fetch_page(st, first))
    w, _ = timed(lambda: wj_app.fetch_page(st, first))
    add(f'첫 화면 열기 ({first})', c, w, '' if rr.get('ok') else '화면을 받지 못함: ' + str(rr.get('error')))

    names = [f'{k}_{ent}' for k in wj_app.PREFETCH if f'{k}_{ent}' != first]
    c = sum(timed(lambda n=n: wj_app.fetch_page(st, n))[0] for n in names)
    w = sum(timed(lambda n=n: wj_app.fetch_page(st, n))[0] for n in names)
    add(f'화면 {len(names)}개를 차례로 이동', c, w, '합계')

    wk = weeks or week_codes()
    body = {'a': 'pullMany', 'ent': ent, 'weeks': wk, 'photos': True}
    c, r1 = timed(lambda: wj_app.handle_pull(st, dict(body)))
    w, r2 = timed(lambda: wj_app.handle_pull(st, dict(body)))
    ok = isinstance(r1, dict) and r1.get('ok')
    add(f'일지 글·사진 {len(wk)}주 ({ent})', c, w, '' if ok else '받지 못함: ' + str((r1 or {}).get('error')))

    c, _ = timed(lambda: wj_app.handle_archive(st, {}))
    w, _ = timed(lambda: wj_app.handle_archive(st, {}))
    add('지난 주 목록(archive)', c, w)

    say('')
    say(f'서버: {api_url}   계정: {uid}   법인: {ent}')
    say(f'{"동작":<30}{"처음(서버)":>12}{"저장본":>10}{"배수":>8}  비고')
    for name, cold, warm, note in rows:
        if warm is None:
            say(f'{name:<30}{cold:>11.2f}s{"":>10}{"":>8}  {note}')
        else:
            ratio = f'{cold / warm:.0f}배' if warm > 0.0005 else '>1000배'
            say(f'{name:<30}{cold:>11.2f}s{warm:>9.3f}s{ratio:>8}  {note}')
    say('')
    say('읽는 법: "처음(서버)"은 설치 직후·매일 첫 로그인처럼 저장본이 없을 때의 대기 시간이고, "저장본"은 그 뒤 화면을 옮길 때의 대기 시간입니다.')
    return rows


LINE = re.compile(r'^\d\d:\d\d:\d\d \[(서버|화면|글)\] (\S+)\s.*?([\d.]+)초')       # 이름이 비어 공백이 둘이어도, 중간에 '실패'가 끼어도 읽는다


def summarize_log(path, say=print):
    """app.log 를 '[서버] 동작 이름 N초' / '[화면] …' / '[글] …' 단위로 묶어 요약한다."""
    groups = {}
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            m = LINE.match(line.strip())
            if not m:
                continue
            kind, act, sec = m.group(1), m.group(2), float(m.group(3))
            if kind == '화면':
                act = '화면:' + ('저장본' if '저장본' in line else '서버')
            elif kind == '글':
                act = '글:저장본포함'
            else:
                act = '서버:' + act + ('(실패)' if '실패' in line else '')
            groups.setdefault(act, []).append(sec)
    say(f'{"동작":<24}{"횟수":>6}{"중앙값":>9}{"평균":>8}{"최대":>8}')
    for k in sorted(groups):
        v = groups[k]
        say(f'{k:<24}{len(v):>6}{statistics.median(v):>8.2f}s{statistics.mean(v):>7.2f}s{max(v):>7.2f}s')
    return groups


def main(argv=None):
    ap = argparse.ArgumentParser(description='앱 속도 실측')
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--api-url')
    r.add_argument('--id', required=True)
    r.add_argument('--password')
    r.add_argument('--who', default='bench')
    r.add_argument('--weeks', nargs='*', help='재볼 주차 (기본: 최근 4주)')
    lg = sub.add_parser('log')
    lg.add_argument('--file', default=os.path.join(str(wj_app.data_dir()), 'app.log'))
    a = ap.parse_args(argv)
    for s_ in (sys.stdout, sys.stderr):
        try:
            s_.reconfigure(errors='replace')
        except Exception:
            pass
    if a.cmd == 'log':
        if not os.path.exists(a.file):
            print('로그 파일이 없습니다:', a.file)
            return 2
        summarize_log(a.file)
        return 0
    url = wj_app.load_api_url(a.api_url)
    if not url:
        print('서버 주소가 없습니다. --api-url 또는 api_url.txt 를 확인하세요.')
        return 2
    pw = a.password or getpass.getpass('비밀번호: ')
    try:
        run(url, a.id, pw, a.who, weeks=a.weeks)
    except (RuntimeError, wj_app.UpstreamError) as ex:
        print('[중단]', ex)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
