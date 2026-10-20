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
import uuid

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


def landed(url, key, name, pid, wait=150):
    """404 로 응답이 끊겼을 때: 서버가 이 반영(pid)을 끝까지 저장·검증했는지 조회한다. 확인되면 그 정보를, 아니면 None."""
    t_end = time.time() + wait
    while time.time() < t_end:
        time.sleep(10)
        try:
            r = post(url, dict(a='pageInfo', key=key, name=name), timeout=60)
        except Exception:
            continue
        if r.get('ok') and r.get('pushId') == pid and r.get('verified'):
            return r
    return None


def push(url, key, name, html, status, asof, tries=3):
    last = None
    pid = uuid.uuid4().hex
    for i in range(tries):
        t1 = time.time()
        try:
            r = post(url, dict(a='pushPage', key=key, name=name, html=html, status=status, asof=asof, pid=pid))
            if r.get('ok'):
                return r
            last = r.get('error') or str(r)
        except urllib.error.HTTPError as ex:      # 서버가 돌려준 응답 내용까지 남긴다 (원인 파악용)
            try:
                body = ex.read().decode('utf-8', 'replace')[:300]
            except Exception:
                body = ''
            last = f'HTTP {ex.code} {body[:120]!r}'
            if ex.code == 404:                   # 구글 앞단이 응답만 끊은 경우가 많다 → 서버에 실제로 저장됐는지 확인
                log(f'[확인 중] {name}: 응답이 끊김(404, {time.time() - t1:.0f}초). 서버 저장 여부를 조회합니다...')
                info = landed(url, key, name, pid)
                if info:
                    log(f'[확인됨] {name}: 서버에 저장·검증 완료')
                    return info
        except Exception as ex:                  # 네트워크 오류는 잠깐 쉬고 재시도
            last = repr(ex)[:160]
        log(f'[재시도 {i + 1}/{tries}] {name} ({len(html):,}자, {time.time() - t1:.0f}초 걸림): {str(last)[:600]}')
        if '키' in str(last):                   # 키가 틀리면 재시도해도 소용없음
            break
        time.sleep(3 * (i + 1))
    raise RuntimeError(f'{name} 반영 실패: {last}')


def build_summaries(week, only, mode, dry_run, codes=None, force=False, workers=3):
    """SUMMARY 5·6·7 핵심 정리 만들기 (시트의 부서 글 → AI 정리 → 숫자·사실 검증 → summary_draft/*.json).
    화면을 만들기 전에 불러야 화면이 정리본을 카드로 보여 준다. 어떤 오류도 반영 전체를 막지 않는다 (기존 정리본·원문 표로 계속).
    mode: auto(기본: --dry-run 이 아닐 때만 새로 만듦) / yes(항상) / no(만들지 않음 — 이미 있는 정리본은 화면에 그대로 쓰임)"""
    if mode == 'no' or (mode == 'auto' and dry_run):
        log(f'[요약] 새로 만들지 않음 (--summary {mode}' + (', --dry-run' if dry_run else '') + ') — 있는 정리본만 화면에 씁니다')
        return {}
    t0 = time.time()
    try:
        import build_summary_draft as B
        use = codes or B.auto_codes(week)
        res = B.run_all(only or ['HK', 'TW'], use, say=log, force=force, workers=workers)
        log(f'[요약] 코드 {",".join(use)} — ' + ', '.join(f'{k}:{v}' for k, v in res.items()) + f' ({time.time() - t0:.0f}초)')
        return res
    except Exception as ex:
        log(f'[경고] 요약 단계 오류 — 기존 정리본으로 계속: {ex!r}')
        return {}


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):                    # 로그를 파일·파이프로 보내면 한글 윈도우(cp949)가 '—' 같은 글자를 못 써서 죽는다 → 못 쓰는 글자는 ?로 바꿔 계속 진행
        try:
            _s.reconfigure(errors='replace')
        except Exception:
            pass
    ap = argparse.ArgumentParser(description='주간영업일지 숫자 반영')
    ap.add_argument('--week', type=int, required=True, help='최신 주차 번호 (예: 40)')
    ap.add_argument('--status', choices=['draft', 'final'], default='draft', help='임시(draft) / 최종(final)')
    ap.add_argument('--dry-run', action='store_true', help='구글로 보내지 않고 파일로만 만든다')
    ap.add_argument('--out', default=None, help='--dry-run 때 저장할 폴더')
    ap.add_argument('--only', nargs='*', choices=['HK', 'TW'], help='일부 법인만')
    ap.add_argument('--summary', choices=['auto', 'yes', 'no'], default='auto', help='SUMMARY 5·6·7 정리본 새로 만들기 (auto: --dry-run 이 아닐 때만, no: 만들지 않음)')
    ap.add_argument('--summary-codes', nargs='*', help='정리할 코드 (예: M09 W41). 없으면 그 주·이번 달·지난 달 자동')
    ap.add_argument('--summary-force', action='store_true', help='원문이 같아도 정리본을 다시 만든다')
    ap.add_argument('--translator', choices=['claude', 'gemini', 'auto'], default='claude', help='번역기: claude(기본, 부서 묶음을 동시에) / gemini(무료 키, 한도에 자주 걸림) / auto(Gemini 키가 있으면 Gemini, 없으면 Claude)')
    ap.add_argument('--workers', type=int, default=3, help='요약을 동시에 돌릴 건수(법인×코드). 1 이면 차례로 (기본 3)')
    ap.add_argument('--summarizer', choices=['claude', 'gemini'], default='claude', help='정리 엔진: claude(기본) / gemini(무료, Claude 사용량 0 — 품질은 compare_engines.py 로 먼저 비교)')
    ap.add_argument('--verifier', choices=['claude', 'gemini', 'none'], default='claude', help='사실 검증 엔진: claude(기본) / gemini / none(검증 안 함)')
    ap.add_argument('--summary-only', action='store_true', help='정리본만 만들고 끝낸다 (화면 생성·반영은 하지 않음. 새벽 등 따로 돌릴 때)')
    ap.add_argument('--no-refresh', action='store_true', help='과거 주 ERP 재정렬(refresh_past_weeks.py)을 건너뛴다')
    ap.add_argument('--no-ledger', action='store_true', help='시작 전에 ERP 원장을 갱신하지 않는다')
    ap.add_argument('--no-verify', action='store_true', help='ERP 대조(주간·월간)를 건너뛴다')
    ap.add_argument('--with-store', action='store_true', help='매장 탭(store_HK/TW)도 올린다 (기본은 올리지 않음)')
    ap.add_argument('--no-monthly', action='store_true', help='월간 화면(monthly_HK/TW)을 만들지 않는다')
    ap.add_argument('--week-archives', action='store_true', help='지난 주 SUMMARY(W1~)와 주차별 보관본도 올린다 (기본은 올리지 않음: 화면이 가볍고 반영이 빠르다)')
    ap.add_argument('--archive', choices=['auto', 'yes', 'no'], default='auto', help='주차별 보관본도 올린다 (auto: 최종(final)일 때만)')
    a = ap.parse_args(argv)

    os.environ['WJ_TRANSLATOR'] = a.translator
    os.environ['WJ_SUMMARIZER'] = a.summarizer
    os.environ['WJ_VERIFIER'] = a.verifier
    if a.summary_only:
        res = build_summaries(a.week, a.only, 'yes' if a.summary == 'auto' else a.summary, False, a.summary_codes, a.summary_force, a.workers)
        return 0 if not any(v in ('failed', 'read-failed') for v in res.values()) else 6

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

    build_summaries(a.week, a.only, a.summary, a.dry_run, a.summary_codes, a.summary_force, a.workers)

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
            if a.with_store:                       # 매장 탭은 개발 중이라 기본은 올리지 않는다 (Code.gs 에 store_ 이름 등록 후 --with-store)
                stpages = g.generate_store(a.week, api_url=url, served=True, status=a.status, asof=asof,
                                           out_dir=(a.out if a.dry_run else None), only=a.only)
                log('매장 화면 생성 완료 — ' + ', '.join(f'{k} {len(v):,}자' for k, v in stpages.items()))
                pages.update(stpages)
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
