# -*- coding: utf-8 -*-
"""영업일지 백업 복원·검증 — backup_journal.py 가 받아 둔 날짜 폴더(<백업>/YYYY-MM-DD/{HK|TW}_{코드}.json.gz)를 서버에 되돌리거나, 서버와 같은지 대조한다.
Code.gs(구글)든 PC 서버(wj_server.py)든 같은 요청 형식이라 둘 다 된다.

  python pc_server/restore_journal.py --api-url <서버 주소> --id hq --verify                  백업과 서버를 대조만 한다(아무것도 바꾸지 않음)
  python pc_server/restore_journal.py --api-url <서버 주소> --id hq --dry-run                 무엇을 되돌릴지 보기만 한다
  python pc_server/restore_journal.py --api-url <서버 주소> --id hq                           서버에 없거나 비어 있는 칸만 채운다(안전, 기본)
  python pc_server/restore_journal.py --api-url <서버 주소> --id hq --mode overwrite          내용이 다른 칸도 백업 내용으로 되돌린다
  옵션: --backup <폴더>(기본 <프로젝트>/wj_backup)  --day YYYY-MM-DD(기본 가장 최근)  --ent TW  --codes W41 M09  --include-auto

- 로그인 계정은 본사(hq) 계정을 써야 모든 칸·마감된 주도 되돌릴 수 있다. 되돌린 칸의 작성자는 그 계정으로 기록된다.
- 자동 번역으로 채워진 칸(auto)은 기본으로 건너뛴다(사람이 쓴 것으로 바뀌지 않게). 필요하면 --include-auto.
- 서버에서 그 사이에 칸이 바뀌어 충돌이 나면 그 칸은 건너뛰고 '충돌'로 세어 알려 준다(덮어쓰지 않음).
- 사진 없이 받은 백업(--no-photos)의 사진 칸은 건너뛴다.
종료코드: 0 문제없음 / 1 되돌릴 것이 남음(verify) 또는 일부 실패 / 2 로그인·설정 오류
"""
import argparse
import getpass
import gzip
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BATCH = 40                                                      # 서버의 saveMany 한도(60) 아래로


def post(url, body, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers={'Content-Type': 'text/plain;charset=utf-8'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def plain(html):
    return re.sub(r'<[^>]*>|&nbsp;', '', str(html or '')).strip()


def list_days(root):
    return sorted(d for d in os.listdir(root) if re.fullmatch(r'\d{4}-\d\d-\d\d', d) and os.path.isdir(os.path.join(root, d))) if os.path.isdir(root) else []


def load_backup(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        return json.load(f)


def compare(backup_cells, live_cells, include_auto=False):
    """칸별 상태: same / missing(서버에 없거나 비어 있음) / differs / skipped_photo / skipped_auto / empty(백업 쪽이 비어 있음)"""
    out = {}
    for cid, c in backup_cells.items():
        html = c.get('html')
        if html is None:
            out[cid] = 'skipped_photo'
        elif c.get('auto') and not include_auto:
            out[cid] = 'skipped_auto'
        elif not plain(html) and '<img' not in html:
            out[cid] = 'empty'
        else:
            live = live_cells.get(cid)
            if not live or (not plain(live.get('html')) and '<img' not in str(live.get('html') or '')):
                out[cid] = 'missing'
            elif live.get('html') == html:
                out[cid] = 'same'
            else:
                out[cid] = 'differs'
    return out


def pick_files(root, day, ent, codes):
    days = list_days(root)
    if not days:
        raise RuntimeError('백업 폴더에 날짜 폴더가 없습니다: ' + root)
    day = day or days[-1]
    if day not in days:
        raise RuntimeError('그 날짜의 백업이 없습니다: %s (있는 날짜: %s)' % (day, ', '.join(days[-5:])))
    files = []
    for n in sorted(os.listdir(os.path.join(root, day))):
        m = re.fullmatch(r'(HK|TW)_([WM]\d{1,2})\.json\.gz', n)
        if m and (not ent or m.group(1) == ent) and (not codes or m.group(2) in codes):
            files.append((m.group(1), m.group(2), os.path.join(root, day, n)))
    return day, files


def run(url, uid, pw, backup=None, day=None, ent=None, codes=None, mode='missing', dry_run=False, verify=False,
        include_auto=False, say=print):
    root = backup or os.path.join(os.path.dirname(HERE), 'wj_backup')
    day, files = pick_files(root, day, ent, set(codes or []))
    r = post(url, {'a': 'login', 'id': uid, 'password': pw, 'who': 'restore'})
    if not r.get('ok'):
        raise PermissionError('로그인 실패: ' + str(r.get('error')))
    tok = r['token']
    if (r.get('me') or {}).get('role') != 'hq' and not (dry_run or verify):
        say('[주의] 본사(hq) 계정이 아니라서 일부 칸·마감된 주는 되돌리지 못할 수 있습니다.')
    say('백업 날짜 %s · 파일 %d개 · 방식 %s%s' % (day, len(files), 'verify(대조만)' if verify else mode, ' · dry-run' if dry_run else ''))
    tot = dict(same=0, missing=0, differs=0, skipped_photo=0, skipped_auto=0, empty=0, restored=0, conflict=0, failed=0)
    for e, code, path in files:
        data = load_backup(path)
        cells = data.get('cells') or {}
        live = post(url, {'a': 'pull', 'ent': e, 'week': code, 'photos': True, 'token': tok})
        if not live.get('ok'):
            say('[실패] %s %s 서버 읽기: %s' % (e, code, live.get('error')))
            tot['failed'] += len(cells)
            continue
        st = compare(cells, live.get('cells') or {}, include_auto)
        for k in set(st.values()):
            tot[k] += list(st.values()).count(k)
        todo = [cid for cid, v in st.items() if v == 'missing' or (mode == 'overwrite' and v == 'differs')]
        line = '%s %s: 같음 %d / 없음 %d / 다름 %d' % (e, code, *(list(st.values()).count(k) for k in ('same', 'missing', 'differs')))
        if verify or dry_run:
            say(line + (' → 되돌릴 칸 %d' % len(todo) if dry_run else ''))
            continue
        done = 0
        for i in range(0, len(todo), BATCH):
            part = todo[i:i + BATCH]
            items = [{'cellId': cid, 'html': cells[cid]['html'], 'base': (live['cells'].get(cid) or {}).get('version', 0)} for cid in part]
            res = post(url, {'a': 'saveMany', 'items': items, 'token': tok})
            if not res.get('ok'):
                tot['failed'] += len(part)
                say('[실패] %s %s: %s' % (e, code, res.get('error')))
                continue
            for cid, x in zip(part, res['results']):
                if x.get('ok'):
                    done += 1
                elif x.get('conflict'):
                    tot['conflict'] += 1
                else:
                    tot['failed'] += 1
                    say('  [실패] %s: %s' % (cid, x.get('error')))
        tot['restored'] += done
        say(line + ' → 되돌림 %d' % done)
    say('합계: 같음 %(same)d / 서버에 없음 %(missing)d / 내용 다름 %(differs)d / 되돌림 %(restored)d / 충돌 %(conflict)d / 실패 %(failed)d '
        '(건너뜀: 사진 %(skipped_photo)d, 자동번역 %(skipped_auto)d, 빈 칸 %(empty)d)' % tot)
    return tot


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(errors='replace')
        except Exception:
            pass
    ap = argparse.ArgumentParser(description='영업일지 백업 복원·검증')
    ap.add_argument('--api-url', help='서버 주소 (없으면 api_url.txt)')
    ap.add_argument('--id', required=True)
    ap.add_argument('--password')
    ap.add_argument('--backup')
    ap.add_argument('--day')
    ap.add_argument('--ent', choices=['HK', 'TW'])
    ap.add_argument('--codes', nargs='*')
    ap.add_argument('--mode', choices=['missing', 'overwrite'], default='missing')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--include-auto', action='store_true')
    a = ap.parse_args(argv)
    url = a.api_url
    if not url:
        for p in (os.path.join(HERE, 'api_url.txt'), os.path.join(os.path.dirname(HERE), 'apps_script', 'weekly_journal', 'api_url.txt')):
            if os.path.exists(p):
                url = open(p, encoding='utf-8').read().strip()
                break
    if not url:
        print('서버 주소가 없습니다. --api-url 을 주세요.')
        return 2
    pw = a.password or getpass.getpass('비밀번호: ')
    try:
        t = run(url, a.id, pw, a.backup, a.day, a.ent, a.codes, a.mode, a.dry_run, a.verify, a.include_auto)
    except (RuntimeError, PermissionError, urllib.error.URLError, OSError) as ex:
        print('[중단]', ex)
        return 2
    if a.verify or a.dry_run:
        return 1 if (t['missing'] or t['differs'] or t['failed']) else 0
    return 1 if (t['failed'] or t['conflict']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
