# -*- coding: utf-8 -*-
"""영업일지 전체(글·사진) 일일 백업 — 시트(Apps Script)에 있는 JOURNAL 을 PC 에 날짜별로 저장한다. (PC 서버 1단계)

저장 위치: <out>/YYYY-MM-DD/{HK|TW}_{코드}.json.gz  (코드 = W1~W53 주간, M01~M12 월간. 글이 하나도 없는 코드는 저장하지 않음)
각 파일 = Apps Script pull 결과 그대로({cells: {칸ID: {html, version, by, at, auto}}, closed, ...}) + 받은 시각.
그날 폴더에 있는 코드는 다시 받지 않는다(중간에 끊겨도 이어서). 오래된 날짜 폴더는 --keep 일만 남기고 지운다.

사용:  python pc_server/backup_journal.py                      (기본 폴더 <프로젝트>\\wj_backup, 30일 보관)
       python pc_server/backup_journal.py --out D:\\wj_backup --keep 60
       python pc_server/backup_journal.py --no-photos             (사진 칸 제외 — 빠르고 가벼움)
로그인: 반영 프로그램의 요약기 계정(summarizer_login.txt, api_url.txt)을 그대로 쓴다. 이 계정은 읽기 전용으로만 쓴다(이 도구는 시트에 쓰지 않음).
종료코드: 0 모두 성공 / 1 일부 실패 / 2 로그인·설정 오류
"""
import argparse
import datetime
import gzip
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'weekly_journal'))
import sheet_reader as R                                        # noqa: E402  (로그인·post 재사용)

ENTS = ('HK', 'TW')
CHUNK = 8                                                       # 사진까지 받으면 응답이 크다 — 한 번에 8개 코드씩


def all_codes():
    return [f'W{i}' for i in range(1, 54)] + [f'M{i:02d}' for i in range(1, 13)]


def has_cells(one):
    return bool(one and one.get('ok') and one.get('cells'))


def save_one(day_dir, ent, code, one, taken_at, photos=True):
    os.makedirs(day_dir, exist_ok=True)
    path = os.path.join(day_dir, f'{ent}_{code}.json.gz')
    tmp = path + '.tmp'
    data = dict(one, ent=ent, code=code, taken_at=taken_at, photos=photos)
    with gzip.open(tmp, 'wt', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)                                       # 쓰는 도중 꺼져도 반쪽 파일이 남지 않게
    return path


def is_done(path, photos):
    """오늘 이미 받은 파일이면 True. 사진 없이 받은 파일은 '사진 포함' 요청에는 다시 받는다."""
    if not os.path.exists(path):
        return False
    if not photos:
        return True
    try:
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            return bool(json.load(f).get('photos'))
    except (OSError, ValueError):
        return False                                            # 깨진 파일은 다시 받는다


def prune(out, keep, today):
    removed = []
    for name in sorted(os.listdir(out)) if os.path.isdir(out) else []:
        try:
            d = datetime.date.fromisoformat(name)
        except ValueError:
            continue                                            # 날짜 폴더가 아니면 건드리지 않는다
        if (today - d).days >= keep:
            shutil.rmtree(os.path.join(out, name), ignore_errors=True)
            removed.append(name)
    return removed


def run(out, keep=30, photos=True, say=print, now=None, codes=None, ents=ENTS):
    now = now or datetime.datetime.now()
    day = now.date().isoformat()
    day_dir = os.path.join(out, day)
    url, tok, _me = R.login()
    stat = {'saved': 0, 'skipped_done': 0, 'empty': 0, 'failed': 0, 'bytes': 0}
    for ent in ents:
        todo = [c for c in (codes or all_codes()) if not is_done(os.path.join(day_dir, f'{ent}_{c}.json.gz'), photos)]
        stat['skipped_done'] += len(codes or all_codes()) - len(todo)
        for i in range(0, len(todo), CHUNK):
            part = todo[i:i + CHUNK]
            try:
                r = R.post(url, {'a': 'pullMany', 'ent': ent, 'weeks': part, 'photos': photos, 'token': tok}, timeout=300)
                if not r.get('ok'):
                    raise RuntimeError(str(r.get('error')))
                res = r.get('results') or []
                if len(res) != len(part):
                    raise RuntimeError(f'응답 개수 불일치({len(res)}/{len(part)})')
            except Exception as ex:
                stat['failed'] += len(part)
                say(f'[실패] {ent} {part[0]}~{part[-1]}: {ex!r}')
                continue
            for code, one in zip(part, res):
                if has_cells(one):
                    p = save_one(day_dir, ent, code, one, now.strftime('%Y-%m-%d %H:%M:%S'), photos)
                    stat['saved'] += 1
                    stat['bytes'] += os.path.getsize(p)
                elif one and one.get('ok'):
                    stat['empty'] += 1
                else:
                    stat['failed'] += 1
                    say(f'[실패] {ent} {code}: {(one or {}).get("error")}')
            say(f'{ent} {part[0]}~{part[-1]} 처리 (저장 누계 {stat["saved"]})')
    stat['pruned'] = prune(out, keep, now.date())
    return stat


def main(argv=None):
    for _s in (sys.stdout, sys.stderr):                    # 로그를 파일·파이프로 보내면 한글 윈도우(cp949)가 '—' 같은 글자를 못 써서 죽는다 → 못 쓰는 글자는 ?로 바꿔 계속 진행
        try:
            _s.reconfigure(errors='replace')
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(os.path.dirname(HERE), 'wj_backup'))
    ap.add_argument('--keep', type=int, default=30, help='날짜 폴더 보관 일수')
    ap.add_argument('--no-photos', action='store_true')
    a = ap.parse_args(argv)
    try:
        st = run(a.out, a.keep, photos=not a.no_photos)
    except RuntimeError as ex:                                  # 로그인·설정 문제
        print(f'[중단] {ex}')
        return 2
    mb = st['bytes'] / 1048576
    print(f"백업 완료: 저장 {st['saved']} / 이미 받음 {st['skipped_done']} / 글 없음 {st['empty']} / 실패 {st['failed']} / {mb:.1f}MB / 지운 오래된 폴더 {len(st['pruned'])}")
    return 1 if st['failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
