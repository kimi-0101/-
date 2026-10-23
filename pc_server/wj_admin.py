# -*- coding: utf-8 -*-
"""영업일지 PC 서버 관리 도구 — 계정·비밀번호·반영 키, 기존 백업 가져오기, DB 백업.

  python pc_server/wj_admin.py init                                  기본 계정(hk, tw, hq) 만들기
  python pc_server/wj_admin.py add-user kim --label "김 부장" --ent TW --dept MD --role writer
  python pc_server/wj_admin.py set-password tw                        (비밀번호는 입력창에서 받음. 8자 이상)
  python pc_server/wj_admin.py list-users
  python pc_server/wj_admin.py push-key                               ERP 숫자 반영 키를 새로 만든다 (이전 키는 무효)
  python pc_server/wj_admin.py import-backup wj_backup                backup_journal.py 가 받아 둔 날짜 폴더들을 DB 로 가져오기
  python pc_server/wj_admin.py translate-test "안녕하세요 <b>3분기</b> 매출" --to en     Gemini 키·번역 동작 확인
  python pc_server/wj_admin.py backup --keep 30                       DB 를 <프로젝트>/wj_data/backup/YYYY-MM-DD.sqlite3 로 복사
"""
import argparse
import datetime
import getpass
import glob
import gzip
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wj_server as S                                           # noqa: E402


def import_backup(store, root, say=print):
    """backup_journal.py 의 결과(<root>/YYYY-MM-DD/{HK|TW}_{코드}.json.gz)를 DB 로 가져온다.
    날짜가 오래된 것부터 읽고, 같은 칸은 버전이 더 높거나 같은(= 더 나중에 받은) 쪽이 남는다. 이미 DB 에 더 높은 버전이 있으면 건드리지 않는다.
    사진 없이 받은 파일(html 이 null)의 칸은 건너뛴다. 마감 상태(closed)는 마감된 것만 가져온다."""
    days = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))) if os.path.isdir(root) else []
    st = {'files': 0, 'cells': 0, 'skipped': 0, 'closed': 0, 'bad': 0}
    for d in days:
        for path in sorted(glob.glob(os.path.join(root, d, '*.json.gz'))):
            try:
                with gzip.open(path, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            except (OSError, ValueError):
                st['bad'] += 1
                say('[건너뜀] 깨진 파일: ' + path)
                continue
            st['files'] += 1
            with store.lock, store.tx():
                for cid, c in (data.get('cells') or {}).items():
                    try:
                        S.parse_cell(cid)
                    except S.ApiError:
                        st['skipped'] += 1
                        continue
                    if c.get('html') is None:
                        st['skipped'] += 1
                        continue
                    ver = int(c.get('version') or 0)
                    cur = store.db.execute('SELECT version FROM journal WHERE cell_id=?', (cid,)).fetchone()
                    if cur and cur['version'] > ver:
                        st['skipped'] += 1
                        continue
                    store.db.execute(
                        'INSERT INTO journal(cell_id,html,version,updated_by,updated_at,auto) VALUES(?,?,?,?,?,?) '
                        'ON CONFLICT(cell_id) DO UPDATE SET html=excluded.html, version=excluded.version, '
                        'updated_by=excluded.updated_by, updated_at=excluded.updated_at, auto=excluded.auto',
                        (cid, c['html'], ver, c.get('by') or '', c.get('at') or S.now_iso(), 'auto' if c.get('auto') else ''))
                    st['cells'] += 1
                if data.get('closed') and data.get('ent') in ('HK', 'TW') and data.get('code'):
                    store.db.execute("INSERT INTO weeks(ent,week,status,changed_by,changed_at) VALUES(?,?,'closed','import',?) "
                                     "ON CONFLICT(ent,week) DO NOTHING", (data['ent'], data['code'], S.now_iso()))
                    st['closed'] += 1
        say('%s 처리 (누계 칸 %d)' % (d, st['cells']))
    return st


def backup_db(store, out_dir, keep=30, today=None):
    """SQLite 백업 API 로 일관된 사본을 만든다(서버가 돌고 있어도 안전). 오래된 사본은 keep 일만 남긴다."""
    today = today or datetime.date.today()
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, today.isoformat() + '.sqlite3')
    tmp = dst + '.tmp'
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    try:
        with store.lock:
            store.db.backup(con)
    finally:
        con.close()
    os.replace(tmp, dst)
    removed = []
    for name in os.listdir(out_dir):
        if not name.endswith('.sqlite3'):
            continue
        try:
            d = datetime.date.fromisoformat(name[:-len('.sqlite3')])
        except ValueError:
            continue
        if (today - d).days >= keep:
            os.remove(os.path.join(out_dir, name))
            removed.append(name)
    return dst, removed


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(errors='replace')
        except Exception:
            pass
    ap = argparse.ArgumentParser(description='영업일지 PC 서버 관리')
    ap.add_argument('--db', default=S.DEFAULT_DB)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('init')
    u = sub.add_parser('add-user')
    u.add_argument('id')
    u.add_argument('--label', default='')
    u.add_argument('--ent', default='ALL', help='HK / TW / ALL')
    u.add_argument('--dept', default='ALL', help='ALL 또는 부서 코드(MD, SALES, EC, VMD, MKT, TRADE, HR, FIN, BEP, GM)')
    u.add_argument('--role', default='writer', help='writer / hq / viewer')
    u.add_argument('--inactive', action='store_true')
    p = sub.add_parser('set-password')
    p.add_argument('id')
    p.add_argument('--password', help='생략하면 입력창에서 받는다(화면·기록에 남지 않음)')
    sub.add_parser('list-users')
    sub.add_parser('push-key')
    i = sub.add_parser('import-backup')
    i.add_argument('folder', help='backup_journal.py 의 --out 폴더 (날짜 폴더들이 들어 있는 곳)')
    t = sub.add_parser('translate-test')
    t.add_argument('text')
    t.add_argument('--from', dest='src', default='ko', choices=['ko', 'en', 'zh'])
    t.add_argument('--to', default='en', choices=['ko', 'en', 'zh'])
    b = sub.add_parser('backup')
    b.add_argument('--out', default=None, help='기본 <DB 폴더>/backup')
    b.add_argument('--keep', type=int, default=30)
    a = ap.parse_args(argv)

    store = S.Store(a.db)
    try:
        if a.cmd == 'init':
            store.init_defaults()
            print('기본 계정(hk, tw, hq)을 만들었습니다. 이어서 set-password 로 비밀번호를 정하세요.')
        elif a.cmd == 'add-user':
            store.upsert_user(a.id, a.label, a.ent, a.dept, a.role, active=not a.inactive)
            print('저장했습니다: ' + a.id + ' (비밀번호는 set-password 로 정하세요)')
        elif a.cmd == 'set-password':
            pw = a.password
            if pw is None:
                pw = getpass.getpass('새 비밀번호(8자 이상): ')
                if pw != getpass.getpass('한 번 더: '):
                    print('두 번 입력이 다릅니다.')
                    return 1
            store.set_password(a.id, pw)
            print('저장했습니다. 이 계정의 기존 로그인은 모두 끊겼습니다.')
        elif a.cmd == 'list-users':
            for r in store.db.execute('SELECT id,label,ent,dept,role,active,pw_hash FROM roster ORDER BY id'):
                print('%-12s %-14s 법인=%-4s 부서=%-6s 역할=%-7s %s %s' % (
                    r['id'], r['label'], r['ent'], r['dept'], r['role'], '사용' if r['active'] else '중지',
                    '' if r['pw_hash'] else '(비밀번호 없음)'))
        elif a.cmd == 'push-key':
            key = store.create_push_key()
            print('숫자 반영 키입니다. 지금 복사해서 반영 프로그램의 push_key.txt 에 붙여넣으세요. (다시 만들면 이전 키는 무효)\n\n' + key)
        elif a.cmd == 'import-backup':
            st = import_backup(store, a.folder)
            print('가져오기 완료: 파일 %(files)d / 칸 %(cells)d / 건너뜀 %(skipped)d / 마감 %(closed)d / 깨진 파일 %(bad)d' % st)
            return 1 if st['bad'] else 0
        elif a.cmd == 'translate-test':
            import wj_translate
            tr = wj_translate.GeminiTranslator.from_env()
            if not tr:
                print('[오류] Gemini 키가 없습니다. wj_data/gemini_key.txt 에 키를 넣거나 환경변수 GEMINI_API_KEY 를 설정하세요.')
                return 2
            try:
                print(tr.translate(a.text, a.src, a.to))
            except wj_translate.TranslateError as ex:
                print('[실패] ' + str(ex))
                return 1
        elif a.cmd == 'backup':
            out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.db)), 'backup')
            dst, removed = backup_db(store, out, a.keep)
            print('백업 완료: %s (%.1fMB) / 지운 오래된 사본 %d개' % (dst, os.path.getsize(dst) / 1048576, len(removed)))
    except S.ApiError as ex:
        print('[오류] ' + str(ex))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
