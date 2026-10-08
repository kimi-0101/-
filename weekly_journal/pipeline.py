# -*- coding: utf-8 -*-
"""주간영업일지 숫자 반영 파이프라인.

ERP 로 만든 erp_w{N}_RAW.json (기존 주간 체인: fetch → sync_all_slides) 을 읽어
HK/TW 상세 일지 + SUMMARY 화면(HTML)을 만들고, 구글 시트(Apps Script)에 밀어 넣는다.
ERP 접속 정보는 구글로 나가지 않는다. 나가는 것은 완성된 화면(숫자 포함)뿐이다.

사용:
  python weekly_journal/pipeline.py --week 40 --status draft      # 임시 숫자 (예: 월 06:00)
  python weekly_journal/pipeline.py --week 40 --status final      # 최종 숫자 (예: TW 온라인 확인 후)
  python weekly_journal/pipeline.py --week 40 --dry-run --out C:/tmp/wj   # 밀어 넣지 않고 파일로만 확인

필요한 파일 (apps_script/weekly_journal/ 안, 저장소에 올리지 않음):
  api_url.txt   웹 앱 URL          push_key.txt   시트 메뉴 '숫자 반영 키 만들기'로 만든 열쇠
환경변수 WJ_API_URL, WJ_PUSH_KEY 로도 줄 수 있다.
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.environ.setdefault('USE_LEDGER', '1')      # 주간 RAW 도 원장 기준으로 (2026-10-01)
CFG_DIR = os.path.join(ROOT, 'apps_script', 'weekly_journal')
sys.path.insert(0, HERE)
LOG = os.path.join(HERE, 'pipeline.log')


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except OSError:
        pass


def read_cfg(fname, env):
    if os.environ.get(env):
        return os.environ[env].strip()
    p = os.path.join(CFG_DIR, fname)
    return open(p, encoding='utf-8').read().strip() if os.path.exists(p) else ''


def need_raw(week):
    missing = [w for w in range(week - 4, week + 1)
               if not os.path.exists(os.path.join(ROOT, f'erp_w{w}_RAW.json'))]
    return missing


def post(url, body, timeout=120):
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'text/plain;charset=utf-8'})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def push(url, key, name, html, status, asof, tries=3):
    last = None
    for i in range(tries):
        t1 = time.time()
        try:
            r = post(url, dict(a='pushPage', key=key, name=name, html=html, status=status, asof=asof))
            if r.get('ok'):
                return r
            last = r.get('error') or str(r)
        except urllib.error.HTTPError as ex:      # 서버가 돌려준 응답 내용까지 남긴다 (원인 파악용)
            try:
                body = ex.read().decode('utf-8', 'replace')[:300]
            except Exception:
                body = ''
            last = f'HTTP {ex.code} {body!r}'
        except Exception as ex:                  # 네트워크 오류는 잠깐 쉬고 재시도
            last = repr(ex)[:160]
        log(f'[재시도 {i + 1}/{tries}] {name} ({len(html):,}자, {time.time() - t1:.0f}초 걸림): {str(last)[:600]}')
        if '키' in str(last):                   # 키가 틀리면 재시도해도 소용없음
            break
        time.sleep(3 * (i + 1))
    raise RuntimeError(f'{name} 반영 실패: {last}')


def main(argv=None):
    ap = argparse.ArgumentParser(description='주간영업일지 숫자 반영')
    ap.add_argument('--week', type=int, required=True, help='최신 주차 번호 (예: 40)')
    ap.add_argument('--status', choices=['draft', 'final'], default='draft', help='임시(draft) / 최종(final)')
    ap.add_argument('--dry-run', action='store_true', help='구글로 보내지 않고 파일로만 만든다')
    ap.add_argument('--out', default=None, help='--dry-run 때 저장할 폴더')
    ap.add_argument('--only', nargs='*', choices=['HK', 'TW'], help='일부 법인만')
    ap.add_argument('--no-refresh', action='store_true', help='과거 주 ERP 재정렬(refresh_past_weeks.py)을 건너뛴다')
    ap.add_argument('--no-ledger', action='store_true', help='시작 전에 ERP 원장을 갱신하지 않는다')
    ap.add_argument('--no-verify', action='store_true', help='ERP 대조(주간·월간)를 건너뛴다')
    ap.add_argument('--no-monthly', action='store_true', help='월간 화면(monthly_HK/TW)을 만들지 않는다')
    ap.add_argument('--week-archives', action='store_true', help='지난 주 SUMMARY(W1~)와 주차별 보관본도 올린다 (기본은 올리지 않음: 화면이 가볍고 반영이 빠르다)')
    ap.add_argument('--archive', choices=['auto', 'yes', 'no'], default='auto', help='주차별 보관본도 올린다 (auto: 최종(final)일 때만)')
    a = ap.parse_args(argv)

    miss = need_raw(a.week)
    if miss:
        log(f'[중단] ERP 데이터가 없습니다: ' + ', '.join(f'erp_w{w}_RAW.json' for w in miss)
            + f'  → 먼저 주간 체인(fetch → python sync_all_slides.py {a.week})을 실행하세요.')
        return 2

    if not a.no_refresh:
        # 과거 주 저장본을 지금 ERP 값으로 다시 맞춘다 (6시간 안에 이미 했으면 건너뜀). 실패해도 화면 생성은 계속.
        try:
            sys.path.insert(0, ROOT)
            import refresh_past_weeks as rpw
            rc = rpw.main(['--week', str(a.week)])
            log(f'과거 주 재정렬 종료코드 {rc} (0=정상/건너뜀, 2=안전장치 중단, 3=실패)')
        except Exception as ex:
            log(f'[경고] 과거 주 재정렬 오류 — 기존 저장본으로 계속: {ex!r}')

    if os.environ.get('USE_LEDGER') == '1' and not a.no_ledger:
        # 화면을 만들기 전에 ERP 원장을 최신으로 (최근 45일 재조회). 실패해도 계속하되, 이후 ERP 대조 관문이 어긋남을 잡아낸다.
        import subprocess
        try:
            rl = subprocess.call([sys.executable, os.path.join(ROOT, 'erp_ledger.py')], cwd=ROOT,
                                 env=dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8'),
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log(f'원장 갱신 종료코드 {rl} (0=정상)')
        except Exception as ex:
            log(f'[경고] 원장 갱신 오류 — 기존 원장으로 계속: {ex!r}')
    url, key = read_cfg('api_url.txt', 'WJ_API_URL'), read_cfg('push_key.txt', 'WJ_PUSH_KEY')
    if not a.dry_run and not (url and key):
        log('[중단] api_url.txt 또는 push_key.txt 가 없습니다. (--dry-run 으로 화면만 확인할 수 있습니다)')
        return 3

    import gen_journal4 as g
    asof = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    t0 = time.time()
    pages = g.generate(a.week, api_url=url, served=True, status=a.status, blank=True, asof=asof,
                       out_dir=(a.out if a.dry_run else None), only=a.only)
    log(f'화면 생성 완료 W{a.week} {a.status} — ' + ', '.join(f'{k} {len(v):,}자' for k, v in pages.items())
        + f' ({time.time() - t0:.1f}초)')
    if not a.no_monthly:
        try:
            mpages = g.generate_monthly(a.week, api_url=url, served=True, status=a.status, asof=asof,
                                        out_dir=(a.out if a.dry_run else None), only=a.only)
            log('월간 화면 생성 완료 — ' + ', '.join(f'{k} {len(v):,}자' for k, v in mpages.items()))
            pages.update(mpages)
            ypages = g.generate_yearly(a.week, api_url=url, served=True, status=a.status, asof=asof,
                                       out_dir=(a.out if a.dry_run else None), only=a.only)
            log('연간 화면 생성 완료 — ' + ', '.join(f'{k} {len(v):,}자' for k, v in ypages.items()))
            pages.update(ypages)
            bpages = g.generate_bep(a.week, api_url=url, served=True, status=a.status, asof=asof,
                                    out_dir=(a.out if a.dry_run else None), only=a.only)
            log('BEP 화면 생성 완료 — ' + ', '.join(f'{k} {len(v):,}자' for k, v in bpages.items()))
            pages.update(bpages)
            smpages = g.generate_summary_months(a.week, api_url=url, served=True, status=a.status, asof=asof,
                                                out_dir=(a.out if a.dry_run else None), only=a.only)
            swpages = {} if not a.week_archives else g.generate_summary_weeks(a.week, api_url=url, served=True, status=a.status, asof=asof,
                                               out_dir=(a.out if a.dry_run else None), only=a.only)
            log(f'월별 SUMMARY {len(smpages)}장, 지난 주 SUMMARY {len(swpages)}장 생성 완료')
            pages.update(smpages)
            pages.update(swpages)
        except Exception as ex:                    # 월간 화면 실패가 주간 반영을 막지 않게 한다
            log(f'[경고] 월간 화면 생성 실패 — 주간 화면만 반영: {ex!r}')
    if not a.no_verify:
        # 반영 전 관문: 화면 숫자 ↔ ERP 저장본(1단계) ↔ ERP 지금 값(2단계), 월간 ↔ ERP. 어긋나면 구글에 올리지 않는다.
        import subprocess
        env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
        vlog = os.path.join(HERE, 'verify.log')
        checks = [('주간', [sys.executable, os.path.join(HERE, 'verify_numbers.py'), '--week', str(a.week), '--live'])]
        if not a.no_monthly:
            checks.append(('월간', [sys.executable, os.path.join(HERE, 'verify_monthly.py'), '--week', str(a.week)]))
        failed = []
        with open(vlog, 'w', encoding='utf-8') as lf:
            for label, cmd in checks:
                lf.write(f'===== {label} =====' + chr(10)); lf.flush()
                rc_ = subprocess.call(cmd, stdout=lf, stderr=subprocess.STDOUT, env=env, cwd=ROOT)
                log(f'ERP 대조 {label}: ' + ('통과' if rc_ == 0 else f'불일치 있음(종료코드 {rc_})'))
                if rc_ != 0:
                    failed.append(label)
        if failed:
            log(f'[중단] ERP 와 맞지 않는 숫자가 있어 반영하지 않습니다 ({", ".join(failed)}). 자세한 내용: {vlog}  (무시하고 올리려면 --no-verify)')
            return 5
    if a.dry_run:
        if a.out:
            log(f'파일 저장: {a.out}')
        return 0

    try:
        for name, html in pages.items():
            r = push(url, key, name, html, a.status, asof)
            log(f'반영 완료 {name} ({r.get("chunks")}조각, {a.status})')
    except RuntimeError as ex:
        log(f'[실패] {ex}')
        return 4
    if a.archive == 'yes' or (a.archive == 'auto' and a.status == 'final'):
        # 보관본: 이 주 마감 시점의 화면 (지난 주 보기용). 이름은 journal_TW@W40 처럼 주차를 붙인다.
        try:
            arch_pages = g.generate(a.week, api_url=url, served=True, status=a.status, blank=True, asof=asof,
                                    only=a.only, arch=f'W{a.week}', nweeks=1)      # 보관본은 그 주 한 주만 담는다(가볍고 빠름, 2026-10-08)
            for name, html in arch_pages.items():
                r = push(url, key, f'{name}@W{a.week}', html, a.status, asof)
                log(f'보관본 반영 완료 {name}@W{a.week} ({r.get("chunks")}조각)')
        except RuntimeError as ex:
            log(f'[실패] 보관본 반영 — 현재 화면은 정상 반영됨: {ex}')
            return 4
    json.dump(dict(week=a.week, status=a.status, asof=asof, pages=list(pages)),
              open(os.path.join(HERE, 'last_push.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    return 0


if __name__ == '__main__':
    sys.exit(main())
