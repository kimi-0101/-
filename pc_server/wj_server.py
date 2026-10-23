# -*- coding: utf-8 -*-
"""주간영업일지 PC 서버 (PC 서버 2단계) — 구글 Apps Script(Code.gs)를 대신하는 자체 서버.

Code.gs 와 같은 요청·응답 형식을 쓰므로, 앱·반영 프로그램은 api_url.txt 의 주소만 이 서버로 바꾸면 된다.
  요청: POST, 본문 JSON {a:'동작', ...}   응답: JSON {ok:true|false, ...}
저장소는 SQLite 파일 하나(기본 <프로젝트>/wj_data/wj.sqlite3). 파이썬 표준 라이브러리만 쓴다.

실행:  python pc_server/wj_server.py                     (127.0.0.1:8787, 이 PC 안에서만)
       python pc_server/wj_server.py --host 0.0.0.0      (같은 사무실 네트워크의 다른 PC 도 접속)
계정·비밀번호·반영 키·백업: python pc_server/wj_admin.py --help

Code.gs 와 다른 점
- 자동 번역(LanguageApp)은 구글 기능이라 없다. 저장 결과의 translated 는 항상 빈 목록이고 translate 요청은 아무것도 채우지 않는다.
- 비밀번호는 PBKDF2(사용자별 소금)로 저장한다. 시트의 해시는 옮길 수 없으니 계정마다 비밀번호를 새로 정한다.
"""
import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
import traceback
import urllib.parse
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(os.path.dirname(HERE), 'wj_data', 'wj.sqlite3')

MAX_FAIL = 5                    # 비밀번호 5회 틀리면
LOCK_SEC = 900                  # 15분 잠금
SESSION_DAYS = 1                # 로그인 유지 1일
PRES_TTL = 30                   # "편집 중" 표시 유지 30초
MAX_HTML = 20000                # 칸당 최대 글자 수
MAX_PHOTO_HTML = 46000          # 사진 칸 최대 글자 수
MAX_BODY = 64 * 1024 * 1024     # 요청 한 번 최대 64MB (화면 HTML 반영이 크다)
PUSH_FAIL_MAX = 10
PBKDF2_ROUNDS = 200_000
DEPT_KO = {'GM': 'GM', 'MD': '상품기획', 'SALES': '영업', 'EC': 'EC', 'VMD': 'VMD', 'MKT': '마케팅',
           'TRADE': '물류', 'HR': 'HR', 'FIN': '회계/재무', 'BEP': 'BEP'}
PAGE_RE = re.compile(r'^(journal|summary|monthly|yearly|msummary|ysummary|bep|store)_(HK|TW)(@(W|M)\d{1,2})?$')
PHOTO_CELL = re.compile(r'\|(vcomp|vthis)_p[1-4]\|ko$')
PHOTO_HTML = re.compile(r'^(<img src="data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+"( alt="[^"]*")?>)?$')

SCHEMA = """
CREATE TABLE IF NOT EXISTS config(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS roster(id TEXT PRIMARY KEY, label TEXT, ent TEXT, dept TEXT, role TEXT,
  active INTEGER NOT NULL DEFAULT 1, pw_salt TEXT NOT NULL DEFAULT '', pw_hash TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, id TEXT, who TEXT, created REAL, expires REAL);
CREATE TABLE IF NOT EXISTS journal(cell_id TEXT PRIMARY KEY, html TEXT NOT NULL, version INTEGER NOT NULL,
  updated_by TEXT, updated_at TEXT, auto TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS weeks(ent TEXT, week TEXT, status TEXT, changed_by TEXT, changed_at TEXT, PRIMARY KEY(ent, week));
CREATE TABLE IF NOT EXISTS log(id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, who TEXT, action TEXT, cell_id TEXT,
  base_version TEXT, new_version TEXT, old_html TEXT);
CREATE TABLE IF NOT EXISTS pages(name TEXT PRIMARY KEY, html TEXT NOT NULL, status TEXT, asof TEXT, updated_at TEXT,
  total INTEGER, push_id TEXT);
"""


class ApiError(Exception):
    def __init__(self, msg, auth=False):
        super().__init__(msg)
        self.auth = auth


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def norm(i):
    return str(i or '').strip().lower()


def pw_hash(salt, pw):
    return hashlib.pbkdf2_hmac('sha256', str(pw).encode('utf-8'), bytes.fromhex(salt), PBKDF2_ROUNDS).hex()


def tok_hash(token):
    return hashlib.sha256(str(token).encode('utf-8')).hexdigest()


def clean_html(html):
    s = '' if html is None else str(html)
    s = re.sub(r'<\s*(script|style|iframe|object|embed|link|meta|form)[\s\S]*?(<\s*/\s*\1\s*>|$)', '', s, flags=re.I)
    s = re.sub(r'\son[a-z]+\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)', '', s, flags=re.I)
    s = re.sub(r'javascript:', '', s, flags=re.I)
    return s


def parse_cell(cell_id):
    p = str(cell_id or '').split('|')
    if len(p) != 5:
        raise ApiError('칸 주소가 올바르지 않습니다.')
    if p[0] not in ('HK', 'TW'):
        raise ApiError('법인이 올바르지 않습니다.')
    if not re.fullmatch(r'[WM]\d{1,2}', p[1]):
        raise ApiError('주차(W) 또는 월(M)이 올바르지 않습니다.')
    if p[2] not in DEPT_KO:
        raise ApiError('부서 코드가 올바르지 않습니다.')
    if not re.fullmatch(r'[A-Za-z0-9_]{1,40}', p[3]):
        raise ApiError('항목 코드가 올바르지 않습니다.')
    if p[4] not in ('ko', 'en', 'zh'):
        raise ApiError('언어가 올바르지 않습니다.')
    return {'ent': p[0], 'week': p[1], 'dept': p[2], 'item': p[3], 'lang': p[4]}


def can_edit(user, c):
    role = user['role']
    if role == 'viewer':
        return False
    if c['item'] == 'hq':
        return role == 'hq'                                      # HQ 코멘트는 본사만
    if role == 'hq':
        return True
    if role != 'writer':
        return False
    if user['ent'] != 'ALL' and user['ent'] != c['ent']:
        return False
    if c['dept'] == 'BEP' and c['item'].startswith('bep_'):
        return True                                              # BEP 코멘트: 그 법인 작성자 누구나
    d = user['dept']
    if c['dept'] == 'TRADE' and d == '무역':
        return True
    if c['dept'] == 'FIN' and d == '회계':
        return True
    return d == 'ALL' or d == c['dept'] or d == DEPT_KO[c['dept']]


class Store:
    """SQLite 위의 모든 동작. 연결 하나를 잠금으로 보호한다(사용자 수십 명 규모에는 충분)."""

    def __init__(self, path=DEFAULT_DB):
        self.path = path
        if path != ':memory:':
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        if path != ':memory:':
            self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript(SCHEMA)
        self.lock = threading.RLock()
        self.fails = {}                      # 아이디 → [실패 횟수, 잠금 풀리는 시각]
        self.push_fails = [0, 0.0]
        self.presence = {}                   # (법인, 주) → {칸: {n, e, t}}

    # ---------- 공통 ----------
    def tx(self):
        return _Tx(self)

    def cfg(self, k, default=None):
        r = self.db.execute('SELECT v FROM config WHERE k=?', (k,)).fetchone()
        return r['v'] if r else default

    def set_cfg(self, k, v):
        self.db.execute('INSERT INTO config(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v', (k, v))

    def audit(self, who, action, cell_id='', base='', ver='', old_html=''):
        try:
            self.db.execute('INSERT INTO log(time,who,action,cell_id,base_version,new_version,old_html) VALUES(?,?,?,?,?,?,?)',
                            (now_iso(), who, action, cell_id, str(base), str(ver), old_html))
        except sqlite3.Error:
            pass                                                 # 이력 실패는 무시

    # ---------- 계정 관리 (wj_admin 에서 사용) ----------
    def init_defaults(self):
        with self.lock:
            if self.db.execute('SELECT COUNT(*) c FROM roster').fetchone()['c'] == 0:
                for row in (('hk', '홍콩 공용', 'HK', 'ALL', 'writer'), ('tw', '대만 공용', 'TW', 'ALL', 'writer'),
                            ('hq', '본사', 'ALL', 'ALL', 'hq')):
                    self.db.execute('INSERT INTO roster(id,label,ent,dept,role) VALUES(?,?,?,?,?)', row)

    def upsert_user(self, uid, label, ent, dept, role, active=True):
        uid = norm(uid)
        if not uid:
            raise ApiError('아이디를 입력하세요.')
        role = norm(role) or 'viewer'
        if role not in ('writer', 'hq', 'viewer'):
            raise ApiError('역할은 writer / hq / viewer 중 하나여야 합니다.')
        with self.lock:
            self.db.execute(
                'INSERT INTO roster(id,label,ent,dept,role,active) VALUES(?,?,?,?,?,?) '
                'ON CONFLICT(id) DO UPDATE SET label=excluded.label, ent=excluded.ent, dept=excluded.dept, role=excluded.role, active=excluded.active',
                (uid, label or uid, str(ent or '').upper(), str(dept or ''), role, 1 if active else 0))

    def set_password(self, uid, pw):
        uid = norm(uid)
        if len(str(pw or '')) < 8:
            raise ApiError('비밀번호는 8자 이상이어야 합니다.')
        with self.lock:
            if not self.db.execute('SELECT 1 FROM roster WHERE id=?', (uid,)).fetchone():
                raise ApiError('명단에 없는 아이디입니다: ' + uid)
            salt = secrets.token_hex(16)
            self.db.execute('UPDATE roster SET pw_salt=?, pw_hash=? WHERE id=?', (salt, pw_hash(salt, pw), uid))
            self.db.execute('DELETE FROM sessions WHERE id=?', (uid,))      # 이 계정의 기존 로그인을 모두 끊는다
            self.audit('admin', 'set_password', uid)

    def create_push_key(self):
        key = secrets.token_hex(32)
        with self.lock:
            self.set_cfg('PUSH_KEY', key)
            self.audit('admin', 'create_push_key')
        return key

    def find_user(self, uid):
        r = self.db.execute('SELECT * FROM roster WHERE id=?', (norm(uid),)).fetchone()
        if not r or not r['active']:
            return None
        return {'id': r['id'], 'label': r['label'] or r['id'], 'ent': (r['ent'] or '').upper(), 'dept': r['dept'] or '',
                'role': (r['role'] or 'viewer').lower(), 'salt': r['pw_salt'], 'pw': r['pw_hash']}

    @staticmethod
    def public_user(u):
        return {'id': u['id'], 'label': u['label'], 'name': u.get('who'), 'sid': u.get('sid'),
                'ent': u['ent'], 'dept': u['dept'], 'role': u['role']}

    @staticmethod
    def actor(u):
        return '%s (%s)' % (u['id'], u.get('who'))

    # ---------- 로그인 ----------
    def login(self, uid, password, who, site):
        e = norm(uid)
        if not e:
            raise ApiError('Enter your ID.')
        with self.lock:
            f = self.fails.get(e)
            if f and f[1] > time.time():
                raise ApiError('Too many failed attempts. The account is locked for now. Try again in 15 minutes.')
            user = self.find_user(e)
            ok = bool(user and user['pw'] and hmac.compare_digest(user['pw'], pw_hash(user['salt'], password or '')))
            if not ok:
                cnt = (f[0] if f and f[1] > time.time() else 0) + 1
                self.fails[e] = [cnt, time.time() + LOCK_SEC]
                self.audit(e, 'login_fail')
                raise ApiError('The ID or password is incorrect.')
            st = str(site or '').upper()
            if st:                                               # 입구(주소)별 계정 제한. site 가 없으면 제한하지 않는다
                mine = 'HQ' if (user['role'] == 'hq' or user['ent'] == 'ALL') else user['ent']
                if st not in ('HK', 'TW', 'HQ') or mine != st:
                    self.audit(e, 'login_wrong_site', st)
                    raise ApiError('The ID or password is incorrect.')
            name = re.sub(r'[<>|]', '', str(who or '')).strip()[:30]
            if not name:
                raise ApiError('Enter your name.')
            self.fails.pop(e, None)
            token = secrets.token_hex(32)
            th = tok_hash(token)
            now = time.time()
            self.db.execute('DELETE FROM sessions WHERE expires < ?', (now,))
            self.db.execute('INSERT INTO sessions(token_hash,id,who,created,expires) VALUES(?,?,?,?,?)',
                            (th, e, name, now, now + SESSION_DAYS * 86400))
            self.audit('%s (%s)' % (e, name), 'login')
            user['who'], user['sid'] = name, th[:12]
            return {'ok': True, 'token': token, 'me': self.public_user(user)}

    def auth(self, token):
        if not token:
            raise ApiError('다시 로그인하세요.', auth=True)
        th = tok_hash(token)
        r = self.db.execute('SELECT * FROM sessions WHERE token_hash=?', (th,)).fetchone()
        if not r or r['expires'] < time.time() or r['created'] + SESSION_DAYS * 86400 < time.time():
            raise ApiError('다시 로그인하세요.', auth=True)
        u = self.find_user(r['id'])
        if not u:
            raise ApiError('다시 로그인하세요.', auth=True)
        u['who'], u['sid'] = r['who'] or u['label'], th[:12]
        return u

    def logout(self, token):
        if token:
            with self.lock:
                self.db.execute('DELETE FROM sessions WHERE token_hash=?', (tok_hash(token),))
        return {'ok': True}

    # ---------- 읽기 ----------
    def week_closed(self, ent, week):
        r = self.db.execute('SELECT status FROM weeks WHERE ent=? AND week=?', (ent, week)).fetchone()
        return bool(r and r['status'] == 'closed')

    def pull_core(self, user, ent, week, photos):
        if ent not in ('HK', 'TW') or not re.fullmatch(r'[WM]\d{1,2}', str(week)):
            raise ApiError('요청이 올바르지 않습니다.')
        prefix = ent + '|' + week + '|'
        cells = {}
        for r in self.db.execute('SELECT * FROM journal WHERE substr(cell_id,1,?)=?', (len(prefix), prefix)):
            hide = (not photos) and PHOTO_CELL.search(r['cell_id'])
            cells[r['cell_id']] = {'html': None if hide else r['html'], 'version': r['version'], 'by': r['updated_by'],
                                   'at': r['updated_at'], 'auto': r['auto'] == 'auto'}
        return {'ok': True, 'me': self.public_user(user), 'closed': self.week_closed(ent, week), 'cells': cells,
                'presence': self.read_presence(ent, week), 'now': int(time.time() * 1000)}

    def pull_many(self, user, ent, weeks, photos):
        if not weeks or len(weeks) > 60:
            raise ApiError('요청이 올바르지 않습니다.')
        out = []
        with self.lock:
            for w in weeks:
                try:
                    out.append(self.pull_core(user, ent, str(w), photos))
                except ApiError as ex:
                    out.append({'ok': False, 'error': str(ex)})
        return {'ok': True, 'results': out}

    # ---------- 쓰기 ----------
    def prep_save(self, user, cell_id, html):
        c = parse_cell(cell_id)
        if not can_edit(user, c):
            raise ApiError('이 칸을 수정할 권한이 없습니다.')
        if self.week_closed(c['ent'], c['week']) and user['role'] != 'hq' and c['week'][0] != 'M':
            raise ApiError('마감된 주차입니다.')                  # 월간(M..) 칸은 마감 후에도 작성자가 쓸 수 있다
        body = clean_html(html)
        if re.search(r'_p\d+$', c['item']):                      # 사진 칸: VMD 의 경쟁사·금주 항목만, ko 칸, 사진 한 장(또는 비움)
            if not (c['dept'] == 'VMD' and c['lang'] == 'ko' and re.fullmatch(r'(vcomp|vthis)_p[1-4]', c['item'])):
                raise ApiError('사진을 올릴 수 없는 칸입니다.')
            if not PHOTO_HTML.match(body):
                raise ApiError('사진 형식이 올바르지 않습니다.')
            if len(body) > MAX_PHOTO_HTML:
                raise ApiError('사진 용량이 너무 큽니다. 더 작은 사진을 올려 주세요.')
        elif len(body) > MAX_HTML:
            raise ApiError('내용이 너무 깁니다. (최대 %d자)' % MAX_HTML)
        return body

    def _save_one(self, user, cell_id, html, base):
        body = self.prep_save(user, cell_id, html)
        cur = self.db.execute('SELECT * FROM journal WHERE cell_id=?', (cell_id,)).fetchone()
        cur_ver = cur['version'] if cur else 0
        try:
            base_n = int(base or 0)
        except (TypeError, ValueError):
            base_n = -1
        if cur_ver != base_n:
            return {'ok': False, 'conflict': True, 'current': {'html': cur['html'] if cur else '', 'version': cur_ver,
                                                               'by': cur['updated_by'] if cur else '', 'at': cur['updated_at'] if cur else ''}}
        ver, now = cur_ver + 1, now_iso()
        if cur:
            self.db.execute('UPDATE journal SET html=?, version=?, updated_by=?, updated_at=?, auto=\'\' WHERE cell_id=?',
                            (body, ver, self.actor(user), now, cell_id))
        else:
            self.db.execute('INSERT INTO journal(cell_id,html,version,updated_by,updated_at,auto) VALUES(?,?,?,?,?,\'\')',
                            (cell_id, body, ver, self.actor(user), now))
        self.audit(self.actor(user), 'save', cell_id, cur_ver, ver, cur['html'][:2000] if cur else '')
        return {'ok': True, 'version': ver}

    def save(self, user, cell_id, html, base):
        with self.lock, self.tx():
            r = self._save_one(user, cell_id, html, base)
        r['translated'] = []
        return r

    def save_many(self, user, items):
        if not items or len(items) > 60:
            raise ApiError('요청이 올바르지 않습니다.')
        results = []
        with self.lock, self.tx():
            for it in items:
                try:
                    results.append(self._save_one(user, it.get('cellId'), it.get('html'), it.get('base')))
                except ApiError as ex:
                    results.append({'ok': False, 'error': str(ex)})
        return {'ok': True, 'results': results}

    def translate(self, user, cell_ids):
        if not cell_ids or len(cell_ids) > 12:
            raise ApiError('요청이 올바르지 않습니다.')
        return {'ok': True, 'results': []}                       # 자동 번역은 지원하지 않는다

    def close_week(self, user, ent, week, closed):
        if user['role'] != 'hq':
            raise ApiError('마감은 본사 담당만 할 수 있습니다.')
        if ent not in ('HK', 'TW') or not re.fullmatch(r'[WM]\d{1,2}', str(week)):
            raise ApiError('요청이 올바르지 않습니다.')
        st = 'closed' if closed else 'open'
        with self.lock:
            self.db.execute('INSERT INTO weeks(ent,week,status,changed_by,changed_at) VALUES(?,?,?,?,?) '
                            'ON CONFLICT(ent,week) DO UPDATE SET status=excluded.status, changed_by=excluded.changed_by, changed_at=excluded.changed_at',
                            (ent, week, st, self.actor(user), now_iso()))
            self.audit(self.actor(user), 'close' if closed else 'reopen', ent + '|' + week)
        return {'ok': True, 'closed': bool(closed)}

    # ---------- "OO 편집 중" ----------
    def read_presence(self, ent, week):
        now = time.time() * 1000
        m = self.presence.get((ent, week), {})
        return {k: v for k, v in m.items() if now - v['t'] < PRES_TTL * 1000}

    def set_presence(self, user, ent, week, cell):
        if ent not in ('HK', 'TW') or not re.fullmatch(r'[WM]\d{1,2}', str(week)):
            raise ApiError('요청이 올바르지 않습니다.')
        with self.lock:
            m = self.read_presence(ent, week)
            for k in [k for k, v in m.items() if v['e'] == user['sid']]:
                del m[k]
            if cell:
                parse_cell(cell)
                m[cell] = {'n': user['who'], 'e': user['sid'], 't': int(time.time() * 1000)}
            self.presence[(ent, week)] = m
        return {'ok': True}

    # ---------- 화면(HTML) 보관·제공 ----------
    def check_push_key(self, key):
        with self.lock:
            if self.push_fails[0] >= PUSH_FAIL_MAX and self.push_fails[1] > time.time():
                raise ApiError('반영 키를 여러 번 틀려 잠시 잠겼습니다. 15분 뒤 다시 시도하세요.')
            want = self.cfg('PUSH_KEY')
            if not want or not hmac.compare_digest(want.encode(), str(key or '').encode()):
                cnt = (self.push_fails[0] if self.push_fails[1] > time.time() else 0) + 1
                self.push_fails = [cnt, time.time() + LOCK_SEC]
                raise ApiError('반영 키가 맞지 않습니다.')
            self.push_fails = [0, 0.0]

    @staticmethod
    def valid_page(name):
        if not PAGE_RE.match(str(name or '')):
            raise ApiError('페이지 이름이 올바르지 않습니다.')
        return name

    def page_info(self, req):
        self.check_push_key(req.get('key'))
        name = self.valid_page(req.get('name'))
        r = self.db.execute('SELECT html,total,push_id FROM pages WHERE name=?', (name,)).fetchone()
        if not r:
            return {'ok': True, 'found': False}
        return {'ok': True, 'found': True, 'pushId': r['push_id'] or '', 'verified': len(r['html']) == r['total'], 'chunks': 1}

    def push_page(self, req):
        self.check_push_key(req.get('key'))
        name = self.valid_page(req.get('name'))
        html = str(req.get('html') or '').replace('\r\n', '\n').replace('\r', '\n')
        if len(html) < 1000:
            raise ApiError('화면 내용이 비어 있습니다.')
        status = 'draft' if req.get('status') == 'draft' else 'final'
        asof, pid = str(req.get('asof') or '')[:40], str(req.get('pid') or '')[:40]
        with self.lock, self.tx():
            self.db.execute('INSERT INTO pages(name,html,status,asof,updated_at,total,push_id) VALUES(?,?,?,?,?,?,?) '
                            'ON CONFLICT(name) DO UPDATE SET html=excluded.html, status=excluded.status, asof=excluded.asof, '
                            'updated_at=excluded.updated_at, total=excluded.total, push_id=excluded.push_id',
                            (name, html, status, asof, now_iso(), len(html), pid))
            self.audit('pipeline', 'push_page', name, '', 1, status + ' ' + asof)
        return {'ok': True, 'chunks': 1, 'status': status}

    def get_page(self, user, name):
        self.valid_page(name)
        r = self.db.execute('SELECT html,status,asof FROM pages WHERE name=?', (name,)).fetchone()
        if not r:
            raise ApiError('아직 이 화면이 준비되지 않았습니다. 숫자 반영이 끝난 뒤 다시 열어 주세요.')
        return {'ok': True, 'html': r['html'], 'status': r['status'], 'asOf': r['asof']}

    def list_archive(self, user):
        by_week = {}
        for r in self.db.execute("SELECT name,status,asof,updated_at FROM pages WHERE name LIKE '%@W%'"):
            m = re.match(r'^(journal|summary)_(HK|TW)@(W\d+)$', r['name'])
            if not m:
                continue
            w = by_week.setdefault(m.group(3), {'week': m.group(3), 'pages': [], 'status': r['status'],
                                                'asOf': r['asof'], 'pushedAt': r['updated_at']})
            w['pages'].append(r['name'])
        closed = {(r['ent'], r['week']) for r in self.db.execute("SELECT ent,week FROM weeks WHERE status='closed'")}
        weeks = []
        for k, w in by_week.items():
            w['closed'] = {'HK': ('HK', k) in closed, 'TW': ('TW', k) in closed}
            weeks.append(w)
        weeks.sort(key=lambda w: -int(w['week'][1:]))
        return {'ok': True, 'weeks': weeks}

    # ---------- 요청 분기 ----------
    def route(self, req):
        a = req.get('a')
        t = req.get('token')
        if a == 'login':
            return self.login(req.get('id'), req.get('password'), req.get('who'), req.get('site'))
        if a == 'pushPage':
            return self.push_page(req)
        if a == 'pageInfo':
            return self.page_info(req)
        if a == 'logout':
            return self.logout(t)
        handlers = {
            'page': lambda u: self.get_page(u, req.get('name')),
            'archive': lambda u: self.list_archive(u),
            'pull': lambda u: self.pull_many(u, req.get('ent'), [req.get('week')], bool(req.get('photos')))['results'][0],
            'pullMany': lambda u: self.pull_many(u, req.get('ent'), req.get('weeks'), bool(req.get('photos'))),
            'save': lambda u: self.save(u, req.get('cellId'), req.get('html'), req.get('base')),
            'saveMany': lambda u: self.save_many(u, req.get('items')),
            'translate': lambda u: self.translate(u, req.get('cellIds')),
            'presence': lambda u: self.set_presence(u, req.get('ent'), req.get('week'), req.get('cell')),
            'close': lambda u: self.close_week(u, req.get('ent'), req.get('week'), req.get('closed')),
        }
        if a not in handlers:
            raise ApiError('알 수 없는 요청')
        return handlers[a](self.auth(t))

    def handle(self, req):
        try:
            if not isinstance(req, dict):
                raise ApiError('요청이 올바르지 않습니다.')
            with self.lock:                                      # 연결 하나를 스레드끼리 섞어 쓰지 않도록 요청 단위로 직렬화
                return self.route(req)
        except ApiError as ex:
            return {'ok': False, 'auth': ex.auth, 'error': str(ex)}


class _Tx:
    def __init__(self, store):
        self.s = store

    def __enter__(self):
        self.s.db.execute('BEGIN IMMEDIATE')

    def __exit__(self, et, ev, tb):
        self.s.db.execute('COMMIT' if et is None else 'ROLLBACK')
        return False


SHELL_HTML = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Weekly Sales Journal</title>'
  '<style>body{margin:0;font-family:system-ui,-apple-system,"Segoe UI","Malgun Gothic",sans-serif;background:#f4f5f7;display:flex;min-height:100vh;align-items:center;justify-content:center;padding:16px;box-sizing:border-box}'
  'form{background:#fff;border-radius:12px;padding:22px 24px;width:min(360px,100%);display:flex;flex-direction:column;gap:10px;box-shadow:0 10px 40px rgba(0,0,0,.12)}'
  'h3{margin:0;font-size:17px}p{margin:0;font-size:13px;color:#4b5563}input{font:inherit;font-size:14px;padding:8px 10px;border:1px solid #d1d5db;border-radius:8px}'
  'button{font:inherit;font-size:13px;padding:8px 12px;border:0;border-radius:8px;background:#111;color:#fff;cursor:pointer}#m{font-size:12px;color:#b45309;min-height:16px}</style></head><body>'
  '<form id="f" hidden><h3>Weekly Sales Journal</h3><p>Sign in with the shared ID and password, then enter the author name to show on the page.</p>'
  '<input id="i" autocomplete="username" autocapitalize="off" placeholder="ID"><input id="w" type="password" autocomplete="current-password" placeholder="Password">'
  '<input id="n" autocomplete="name" maxlength="30" placeholder="Your name (e.g. Alex Chen)"><button type="submit">Sign in</button><div id="m"></div></form>'
  '<div id="l" style="color:#6b7280;font-size:13px">Loading…</div>'
  '<script>var API="__API__",PAGE="__PAGE__";'
  'function post(b){return fetch(API,{method:"POST",headers:{"Content-Type":"text/plain;charset=utf-8"},body:JSON.stringify(b)}).then(function(r){return r.json();});}'
  'function tok(){try{return localStorage.getItem("wj_tok_HK")||""}catch(e){return ""}}'
  'function form(msg){document.getElementById("l").hidden=true;document.getElementById("f").hidden=false;document.getElementById("m").textContent=msg||"";try{document.getElementById("n").value=localStorage.getItem("wj_who")||""}catch(e){}}'
  'function go(){post({a:"page",name:PAGE,token:tok()}).then(function(r){if(r.ok){document.open();document.write(r.html);document.close();}else{form(r.auth?"":(r.error||""));}}).catch(function(){form("Could not reach the server.");});}'
  'document.getElementById("f").addEventListener("submit",function(ev){ev.preventDefault();var id=document.getElementById("i").value.trim(),pw=document.getElementById("w").value,who=document.getElementById("n").value.trim();'
  'if(!id||!pw||!who){document.getElementById("m").textContent="Enter your ID, password and name.";return;}'
  'post({a:"login",id:id,password:pw,who:who}).then(function(r){if(!r.ok){document.getElementById("m").textContent=r.error||"";return;}'
  'try{localStorage.setItem("wj_tok_HK",r.token);localStorage.setItem("wj_tok_TW",r.token);localStorage.setItem("wj_who",who);localStorage.setItem("wj_role",(r.me&&r.me.role)||"");}catch(e){}go();}).catch(function(){document.getElementById("m").textContent="Could not reach the server.";});});'
  'if(tok())go();else form("");</script></body></html>')


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'
        server_version = 'WJServer'

        def log_message(self, fmt, *args):
            sys.stderr.write('%s [%s] %s\n' % (datetime.now().strftime('%H:%M:%S'), self.address_string(), fmt % args))

        def _send(self, code, body, ctype):
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path == '/healthz':
                return self._send(200, b'ok', 'text/plain')
            page = (urllib.parse.parse_qs(u.query).get('p') or ['journal_TW'])[0]
            if not PAGE_RE.match(page):
                page = 'journal_TW'
            html = SHELL_HTML.replace('__API__', 'api').replace('__PAGE__', page)
            self._send(200, html.encode('utf-8'), 'text/html; charset=utf-8')

        def do_POST(self):
            try:
                n = int(self.headers.get('Content-Length') or 0)
            except ValueError:
                n = -1
            if n < 0 or n > MAX_BODY:
                self.close_connection = True
                return self._send(413, json.dumps({'ok': False, 'error': '요청이 너무 큽니다.'}).encode(), 'application/json; charset=utf-8')
            raw = self.rfile.read(n)
            try:
                req = json.loads(raw.decode('utf-8'))
                out = store.handle(req)
            except (ValueError, UnicodeDecodeError):
                out = {'ok': False, 'error': '요청 형식이 올바르지 않습니다.'}
            except Exception:
                traceback.print_exc()
                out = {'ok': False, 'error': '서버 오류가 났습니다. 잠시 뒤 다시 시도하세요.'}
            self._send(200, json.dumps(out, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')
    return Handler


def make_server(store, host='127.0.0.1', port=8787):
    srv = ThreadingHTTPServer((host, port), make_handler(store))
    srv.daemon_threads = True
    return srv


def main(argv=None):
    ap = argparse.ArgumentParser(description='주간영업일지 PC 서버')
    ap.add_argument('--db', default=DEFAULT_DB, help='SQLite 파일 (기본 <프로젝트>/wj_data/wj.sqlite3)')
    ap.add_argument('--host', default='127.0.0.1', help='0.0.0.0 으로 하면 같은 네트워크의 다른 PC 도 접속')
    ap.add_argument('--port', type=int, default=8787)
    a = ap.parse_args(argv)
    store = Store(a.db)
    store.init_defaults()
    srv = make_server(store, a.host, a.port)
    print('영업일지 PC 서버: http://%s:%d/  (DB: %s)  끝내려면 Ctrl+C' % (a.host, a.port, a.db))
    if not store.cfg('PUSH_KEY'):
        print('[안내] 반영 키가 아직 없습니다: python pc_server/wj_admin.py push-key')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
