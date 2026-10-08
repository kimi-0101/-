/**
 * 주간영업일지 API (Google Sheet + Apps Script)
 *
 * 구글 시트에 붙은(컨테이너 바운드) 스크립트입니다.
 * 탭: ROSTER(공용 계정), JOURNAL(일지 칸), WEEKS(주차 마감), LOG(변경 이력), SESSIONS(로그인 세션)
 * 로그인: 나라별 공용 아이디 + 비밀번호 (+ 화면에 표시할 작성자 이름)
 * 처음 한 번 setup() 을 실행하면 탭과 머리글, 비밀키가 만들어집니다.
 *
 * 요청 형식: POST, Content-Type text/plain, 본문 JSON {a:'동작', ...}
 * 응답 형식: JSON {ok:true|false, ...}
 */

var TAB = { ROSTER: 'ROSTER', JOURNAL: 'JOURNAL', WEEKS: 'WEEKS', LOG: 'LOG', SESSIONS: 'SESSIONS', PAGES: 'PAGES' };
var HEAD = {
  ROSTER: ['id', 'label', 'entity', 'dept', 'role', 'active', 'pwHash'],
  JOURNAL: ['cellId', 'html', 'version', 'updatedBy', 'updatedAt', 'auto'],
  WEEKS: ['entity', 'week', 'status', 'changedBy', 'changedAt'],
  LOG: ['time', 'who', 'action', 'cellId', 'baseVersion', 'newVersion', 'oldHtml'],
  SESSIONS: ['tokenHash', 'id', 'expires', 'createdAt', 'who'],
  PAGES: ['name', 'seq', 'chunk', 'status', 'asOf', 'updatedAt', 'total', 'pushId']
};
var MAX_FAIL = 5;             // 비밀번호 5회 틀리면
var LOCK_SEC = 900;           // 15분 잠금
var SESSION_DAYS = 1;         // 로그인 유지 1일 (2026-10-08, 14일에서 줄임)
var PRES_TTL = 30;            // "편집 중" 표시 유지 30초
var MAX_HTML = 20000;         // 칸당 최대 글자 수
var MAX_PHOTO_HTML = 46000;   // 사진 칸(VMD 경쟁사·금주 사진) 최대 글자 수 — 시트 한 칸 한도(5만 자) 안쪽
var AUTO_TRANSLATE = true;    // 저장하면 나머지 두 언어 칸을 구글 번역으로 채운다 (사람이 쓴 칸은 덮어쓰지 않음)
var LANG_CODE = { ko: 'ko', en: 'en', zh: 'zh-TW' };
var DRIVE_MARK = 'drive:';     // PAGES 의 chunk 칸이 이 글자로 시작하면 화면은 드라이브 파일에 있다 (뒤는 파일 ID). 시트에는 한 줄만 남아 가볍다.
var CHUNK_MARK = '~wj~';      // 조각 맨 앞에 붙이는 표지 (조각이 = + - ' 로 시작하면 시트가 수식·숫자로 바꿔 버리므로). 읽을 때 떼어 낸다. 표지 없는 옛 조각도 그대로 읽힌다.
var CHUNK = 40000;            // 화면(HTML)을 시트 칸에 나눠 담는 크기 (칸 한도 50,000자)
// 부서 코드 → 명단(ROSTER)에 적는 부서 이름. 명단에는 코드(MD)나 이름(상품기획) 어느 쪽을 써도 됩니다.
var DEPT_KO = { GM: 'GM', MD: '상품기획', SALES: '영업', EC: 'EC', VMD: 'VMD', MKT: '마케팅', TRADE: '물류', HR: 'HR', FIN: '회계/재무', BEP: 'BEP' };

/* ---------- 진입점 ---------- */
/** 주소로 들어오면 로그인 화면만 내려보내고, 로그인 후 화면(HTML)은 API 로 받는다. (화면 안의 숫자는 로그인 전에 노출되지 않음) */
function doGet(e) {
  var page = (e && e.parameter && e.parameter.p) || 'journal_TW';
  if (!/^(journal|summary|monthly|yearly|msummary|ysummary|bep)_(HK|TW)(@(W|M)\d{1,2})?$/.test(page)) page = 'journal_TW';
  var html = SHELL_HTML.replace('__API__', ScriptApp.getService().getUrl()).replace('__PAGE__', page);
  return HtmlService.createHtmlOutput(html).setTitle('Weekly Sales Journal')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

var SHELL_HTML = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Weekly Sales Journal</title>'
  + '<style>body{margin:0;font-family:system-ui,-apple-system,"Segoe UI","Malgun Gothic",sans-serif;background:#f4f5f7;display:flex;min-height:100vh;align-items:center;justify-content:center;padding:16px;box-sizing:border-box}'
  + 'form{background:#fff;border-radius:12px;padding:22px 24px;width:min(360px,100%);display:flex;flex-direction:column;gap:10px;box-shadow:0 10px 40px rgba(0,0,0,.12)}'
  + 'h3{margin:0;font-size:17px}p{margin:0;font-size:13px;color:#4b5563}input{font:inherit;font-size:14px;padding:8px 10px;border:1px solid #d1d5db;border-radius:8px}'
  + 'button{font:inherit;font-size:13px;padding:8px 12px;border:0;border-radius:8px;background:#111;color:#fff;cursor:pointer}#m{font-size:12px;color:#b45309;min-height:16px}</style></head><body>'
  + '<form id="f" hidden><h3>Weekly Sales Journal</h3><p>Sign in with the shared ID and password, then enter the author name to show on the page.</p>'
  + '<input id="i" autocomplete="username" autocapitalize="off" placeholder="ID"><input id="w" type="password" autocomplete="current-password" placeholder="Password">'
  + '<input id="n" autocomplete="name" maxlength="30" placeholder="Your name (e.g. Alex Chen)"><button type="submit">Sign in</button><div id="m"></div></form>'
  + '<div id="l" style="color:#6b7280;font-size:13px">Loading…</div>'
  + '<script>var API="__API__",PAGE="__PAGE__";'
  + 'function post(b){return fetch(API,{method:"POST",headers:{"Content-Type":"text/plain;charset=utf-8"},body:JSON.stringify(b)}).then(function(r){return r.json();});}'
  + 'function tok(){try{return localStorage.getItem("wj_tok_HK")||""}catch(e){return ""}}'
  + 'function form(msg){document.getElementById("l").hidden=true;document.getElementById("f").hidden=false;document.getElementById("m").textContent=msg||"";try{document.getElementById("n").value=localStorage.getItem("wj_who")||""}catch(e){}}'
  + 'function go(){post({a:"page",name:PAGE,token:tok()}).then(function(r){if(r.ok){document.open();document.write(r.html);document.close();}else{form(r.auth?"":(r.error||""));}}).catch(function(){form("Could not reach the server.");});}'
  + 'document.getElementById("f").addEventListener("submit",function(ev){ev.preventDefault();var id=document.getElementById("i").value.trim(),pw=document.getElementById("w").value,who=document.getElementById("n").value.trim();'
  + 'if(!id||!pw||!who){document.getElementById("m").textContent="Enter your ID, password and name.";return;}'
  + 'post({a:"login",id:id,password:pw,who:who}).then(function(r){if(!r.ok){document.getElementById("m").textContent=r.error||"";return;}'
  + 'try{localStorage.setItem("wj_tok_HK",r.token);localStorage.setItem("wj_tok_TW",r.token);localStorage.setItem("wj_who",who);localStorage.setItem("wj_role",(r.me&&r.me.role)||"");}catch(e){}go();}).catch(function(){document.getElementById("m").textContent="Could not reach the server.";});});'
  + 'if(tok())go();else form("");</script></body></html>';

function doPost(e) {
  var out;
  try {
    var req = JSON.parse(e.postData.contents);
    out = route_(req);
  } catch (err) {
    out = { ok: false, auth: !!(err && err.auth), error: String(err && err.message || err) };
  }
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}

function route_(req) {
  switch (req.a) {
    case 'login': return login_(req.id, req.password, req.who, req.site);
    case 'pushPage': return pushPage_(req);
    case 'pageInfo': return pageInfo_(req);
    case 'page': return getPage_(auth_(req.token), req.name);
    case 'archive': return listArchive_(auth_(req.token));
    case 'pull': return pull_(auth_(req.token), req.ent, req.week, !!req.photos);
    case 'pullMany': return pullMany_(auth_(req.token), req.ent, req.weeks, !!req.photos);
    case 'save': return save_(auth_(req.token), req.cellId, req.html, req.base, req.tr === false);
    case 'saveMany': return saveMany_(auth_(req.token), req.items);
    case 'translate': return translateMany_(auth_(req.token), req.cellIds);
    case 'presence': return presence_(auth_(req.token), req.ent, req.week, req.cell);
    case 'close': return closeWeek_(auth_(req.token), req.ent, req.week, req.closed);
    case 'logout': return logout_(req.token);
    default: throw new Error('알 수 없는 요청');
  }
}

/* ---------- 초기 설정 (한 번만 실행) ---------- */
function setup() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  Object.keys(TAB).forEach(function (k) {
    var sh = ss.getSheetByName(TAB[k]) || ss.insertSheet(TAB[k]);
    if (sh.getLastRow() === 0) {
      sh.getRange(1, 1, 1, HEAD[k].length).setValues([HEAD[k]]).setFontWeight('bold').setBackground('#111111').setFontColor('#ffffff');
      sh.setFrozenRows(1);
    }
  });
  var props = PropertiesService.getScriptProperties();
  if (!props.getProperty('SECRET')) props.setProperty('SECRET', Utilities.getUuid() + Utilities.getUuid());
  var ro = ss.getSheetByName(TAB.ROSTER);
  if (ro.getLastRow() < 2) {
    ro.getRange(2, 1, 3, 6).setValues([
      ['hk', '홍콩 공용', 'HK', 'ALL', 'writer', ''],
      ['tw', '대만 공용', 'TW', 'ALL', 'writer', ''],
      ['hq', '본사', 'ALL', 'ALL', 'hq', '']
    ]);
  }
  return '설정 완료. 메뉴 "주간영업일지 > 비밀번호 설정"으로 각 계정의 비밀번호를 정하세요.';
}

/** 시트를 열 때 메뉴를 추가합니다. */
function onOpen() {
  SpreadsheetApp.getUi().createMenu('주간영업일지').addItem('비밀번호 설정', 'menuSetPassword')
    .addItem('숫자 반영 키 만들기', 'menuCreatePushKey').addToUi();
}

/** 메뉴: 계정 아이디와 새 비밀번호를 묻고, 해시로만 저장합니다. (비밀번호 원문은 시트에 남지 않습니다) */
function menuSetPassword() {
  var ui = SpreadsheetApp.getUi();
  var a = ui.prompt('비밀번호 설정', 'ROSTER 탭의 아이디를 입력하세요 (예: tw)', ui.ButtonSet.OK_CANCEL);
  if (a.getSelectedButton() !== ui.Button.OK) return;
  var b = ui.prompt('비밀번호 설정', '새 비밀번호 (8자 이상)', ui.ButtonSet.OK_CANCEL);
  if (b.getSelectedButton() !== ui.Button.OK) return;
  try {
    setPassword_(a.getResponseText(), b.getResponseText());
    ui.alert('저장했습니다. 화면에서 이 아이디와 비밀번호로 로그인할 수 있습니다.');
  } catch (e) {
    ui.alert(String(e.message || e));
  }
}

/** 메뉴: ERP 숫자를 시트로 보내는 PC 전용 열쇠를 새로 만듭니다. 화면에 한 번만 보여 주니 바로 복사하세요. (다시 만들면 이전 열쇠는 무효) */
function menuCreatePushKey() {
  var key = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
  PropertiesService.getScriptProperties().setProperty('PUSH_KEY', key);
  SpreadsheetApp.getUi().alert('숫자 반영 키입니다. 지금 복사해서 이 PC의 apps_script/weekly_journal/push_key.txt 에 붙여넣으세요.\n\n' + key);
}

function pwHash_(id, pw) {
  return hash_('pw|' + norm_(id) + '|' + pw);
}

function setPassword_(id, pw) {
  id = norm_(id);
  if (String(pw || '').length < 8) throw new Error('비밀번호는 8자 이상이어야 합니다.');
  var sh = sh_(TAB.ROSTER), r = rows_(TAB.ROSTER);
  for (var i = 0; i < r.length; i++) {
    if (norm_(r[i][0]) === id) {
      sh.getRange(i + 2, 7).setValue(pwHash_(id, pw));
      // 이 계정의 기존 로그인을 모두 끊습니다
      var ss = rows_(TAB.SESSIONS), sn = sh_(TAB.SESSIONS);
      for (var k = ss.length - 1; k >= 0; k--) if (norm_(ss[k][1]) === id) sn.deleteRow(k + 2);
      audit_('admin', 'set_password', id, '', '', '');
      return true;
    }
  }
  throw new Error('ROSTER 탭에 없는 아이디입니다: ' + id);
}

/* ---------- 공통 도구 ---------- */
function sh_(name) {
  var s = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name);
  if (!s) throw new Error(name + ' 탭이 없습니다. setup() 을 먼저 실행하세요.');
  return s;
}

function secret_() {
  var s = PropertiesService.getScriptProperties().getProperty('SECRET');
  if (!s) throw new Error('setup() 을 먼저 실행하세요.');
  return s;
}

function hex_(bytes) {
  return bytes.map(function (b) { return ('0' + (b < 0 ? b + 256 : b).toString(16)).slice(-2); }).join('');
}

function hash_(s) {
  return hex_(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, secret_() + '|' + s));
}

function norm_(id) {
  return String(id || '').trim().toLowerCase();
}

function rows_(name) {
  var sh = sh_(name), n = sh.getLastRow();
  if (n < 2) return [];
  return sh.getRange(2, 1, n - 1, HEAD[name].length).getValues();
}

function findRoster_(id) {
  var e = norm_(id), r = rows_(TAB.ROSTER);
  for (var i = 0; i < r.length; i++) {
    if (norm_(r[i][0]) === e) {
      var act = String(r[i][5]).trim().toUpperCase();
      if (act === 'FALSE' || act === 'N' || act === '0' || act === 'X') return null;   // 비활성
      return {
        id: e, label: String(r[i][1] || e), ent: String(r[i][2] || '').toUpperCase(),
        dept: String(r[i][3] || ''), role: String(r[i][4] || 'viewer').toLowerCase(), pwHash: String(r[i][6] || '')
      };
    }
  }
  return null;
}

/* ---------- 로그인 (공용 아이디 + 비밀번호) ---------- */
function login_(id, password, who, site) {
  var e = norm_(id), cache = CacheService.getScriptCache();
  if (!e) throw new Error('Enter your ID.');
  if (cache.get('lock:' + e)) throw new Error('Too many failed attempts. The account is locked for now. Try again in 15 minutes.');
  var user = findRoster_(e);
  var ok = user && user.pwHash && user.pwHash === pwHash_(e, String(password || ''));
  if (!ok) {
    var f = Number(cache.get('fail:' + e) || 0) + 1;
    cache.put('fail:' + e, String(f), LOCK_SEC);
    if (f >= MAX_FAIL) cache.put('lock:' + e, '1', LOCK_SEC);
    audit_(e, 'login_fail', '', '', '', '');
    throw new Error('The ID or password is incorrect.');
  }
  /* 입구(주소)별 계정 제한: 홍콩 주소는 HK 계정만, 대만 주소는 TW 계정만, 본사 주소는 본사(ALL) 계정만. site 가 없으면(옛 입구) 제한하지 않는다. */
  var st = String(site || '').toUpperCase();
  if (st) {
    var mine = (user.role === 'hq' || user.ent === 'ALL') ? 'HQ' : user.ent;
    if (!/^(HK|TW|HQ)$/.test(st) || mine !== st) {
      audit_(e, 'login_wrong_site', st, '', '', '');
      throw new Error('The ID or password is incorrect.');
    }
  }
  var name = String(who || '').replace(/[<>|]/g, '').trim().slice(0, 30);
  if (!name) throw new Error('Enter your name.');
  cache.remove('fail:' + e);
  var token = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
  var exp = new Date(Date.now() + SESSION_DAYS * 86400000);
  sh_(TAB.SESSIONS).appendRow([hash_(token), e, exp, new Date(), name]);
  audit_(e + ' (' + name + ')', 'login', '', '', '', '');
  user.who = name;
  user.sid = hash_(token).slice(0, 12);
  return { ok: true, token: token, me: publicUser_(user) };
}

function publicUser_(u) {
  return { id: u.id, label: u.label, name: u.who, sid: u.sid, ent: u.ent, dept: u.dept, role: u.role };
}

function actor_(u) {
  return u.id + ' (' + u.who + ')';
}

function auth_(token) {
  if (!token) throw authError_();
  var h = hash_(token), cache = CacheService.getScriptCache();
  var hit = cache.get('sess:' + h);
  if (hit) {
    var c = JSON.parse(hit), u0 = findRoster_(c.id);
    if (u0 && u0.pwHash.slice(0, 12) === c.pf) { u0.who = c.who; u0.sid = h.slice(0, 12); return u0; }   // 비밀번호가 바뀌면 캐시도 무효
  }
  var r = rows_(TAB.SESSIONS), now = Date.now();
  for (var i = r.length - 1; i >= 0; i--) {
    if (r[i][0] === h) {
      if (new Date(r[i][2]).getTime() < now) throw authError_();
      if (new Date(r[i][3]).getTime() + SESSION_DAYS * 86400000 < now) throw authError_();   // 발급 시각 기준으로도 검사 (기간을 줄이기 전에 받은 열쇠도 새 기준 적용)
      var u = findRoster_(r[i][1]);
      if (!u) throw authError_();
      u.who = String(r[i][4] || u.label);
      u.sid = h.slice(0, 12);
      cache.put('sess:' + h, JSON.stringify({ id: u.id, who: u.who, pf: u.pwHash.slice(0, 12) }), 300);
      return u;
    }
  }
  throw authError_();
}

function authError_() {
  var e = new Error('다시 로그인하세요.');
  e.auth = true;
  return e;
}

function logout_(token) {
  if (!token) return { ok: true };
  var h = hash_(token), sh = sh_(TAB.SESSIONS), r = rows_(TAB.SESSIONS);
  for (var i = r.length - 1; i >= 0; i--) {
    if (r[i][0] === h) sh.deleteRow(i + 2);
  }
  CacheService.getScriptCache().remove('sess:' + h);
  return { ok: true };
}

/* ---------- 권한 ---------- */
function parseCell_(cellId) {
  var p = String(cellId || '').split('|');
  if (p.length !== 5) throw new Error('칸 주소가 올바르지 않습니다.');
  if (!/^(HK|TW)$/.test(p[0])) throw new Error('법인이 올바르지 않습니다.');
  if (!/^[WM]\d{1,2}$/.test(p[1])) throw new Error('주차(W) 또는 월(M)이 올바르지 않습니다.');
  if (!DEPT_KO.hasOwnProperty(p[2])) throw new Error('부서 코드가 올바르지 않습니다.');
  if (!/^[A-Za-z0-9_]{1,40}$/.test(p[3])) throw new Error('항목 코드가 올바르지 않습니다.');
  if (p[4] !== 'ko' && p[4] !== 'en' && p[4] !== 'zh') throw new Error('언어가 올바르지 않습니다.');
  return { ent: p[0], week: p[1], dept: p[2], item: p[3], lang: p[4] };
}

function canEdit_(user, c) {
  if (user.role === 'viewer') return false;
  if (c.item === 'hq') return user.role === 'hq';              // HQ 코멘트는 본사만
  if (user.role === 'hq') return true;
  if (user.role !== 'writer') return false;
  if (user.ent !== 'ALL' && user.ent !== c.ent) return false;
  if (c.dept === 'BEP' && c.item.indexOf('bep_') === 0) return true;      // BEP 코멘트: 그 법인 작성자 누구나
  var d = String(user.dept || '');
  if (c.dept === 'TRADE' && d === '무역') return true;                  // 부서 이름을 '무역'에서 '물류'로 바꾸기 전에 만든 계정 호환
  if (c.dept === 'FIN' && d === '회계') return true;                     // 명단에 '회계'로만 적은 계정도 허용
  return d === 'ALL' || d === c.dept || d === DEPT_KO[c.dept];
}

function weekClosed_(ent, week) {
  var r = rows_(TAB.WEEKS);
  for (var i = r.length - 1; i >= 0; i--) {
    if (r[i][0] === ent && r[i][1] === week) return r[i][2] === 'closed';
  }
  return false;
}

/* ---------- 읽기 ---------- */
function pull_(user, ent, week, photos) {
  return pullCore_(user, ent, week, photos, rows_(TAB.JOURNAL), rows_(TAB.WEEKS));
}

function closedFrom_(wkRows, ent, week) {
  for (var i = wkRows.length - 1; i >= 0; i--) {
    if (wkRows[i][0] === ent && wkRows[i][1] === week) return wkRows[i][2] === 'closed';
  }
  return false;
}

/* 시트 행(r, wkRows)을 받아서 한 주의 칸을 만든다 — pullMany_ 가 시트를 한 번만 읽어 여러 주에 공유한다 */
function pullCore_(user, ent, week, photos, r, wkRows) {
  if (!/^(HK|TW)$/.test(ent) || !/^[WM]\d{1,2}$/.test(week)) throw new Error('요청이 올바르지 않습니다.');
  if (user.role !== 'hq' && user.ent !== 'ALL' && user.ent !== ent && !readOthers_()) throw new Error('이 법인은 볼 수 없습니다.');
  var prefix = ent + '|' + week + '|', cells = {};
  for (var i = 0; i < r.length; i++) {
    if (String(r[i][0]).indexOf(prefix) === 0) {
      cells[r[i][0]] = { html: (!photos && PHOTO_CELL_.test(String(r[i][0]))) ? null : r[i][1], version: Number(r[i][2]), by: r[i][3], at: r[i][4] instanceof Date ? r[i][4].toISOString() : String(r[i][4]), auto: String(r[i][5]) === 'auto' };
    }
  }
  return { ok: true, me: publicUser_(user), closed: closedFrom_(wkRows, ent, week), cells: cells, presence: readPresence_(ent, week), now: Date.now() };
}

/* 여러 주(최대 6개)를 한 번에: 화면이 열릴 때 주마다 따로 부르던 것(4번)을 1번으로 */
function pullMany_(user, ent, weeks, photos) {
  if (!weeks || !weeks.length || weeks.length > 60) throw new Error('요청이 올바르지 않습니다.');
  var results = [], jr = rows_(TAB.JOURNAL), wr = rows_(TAB.WEEKS);      // 시트는 한 번만 읽는다 (주마다 읽으면 느리다)
  for (var i = 0; i < weeks.length; i++) {
    try { results.push(pullCore_(user, ent, String(weeks[i]), photos, jr, wr)); }
    catch (e) { results.push({ ok: false, error: String(e && e.message || e) }); }
  }
  return { ok: true, results: results };
}

var PHOTO_CELL_ = /\|(vcomp|vthis)_p[1-4]\|ko$/;
var PHOTO_HTML_ = /^(<img src="data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+\/=]+"( alt="[^"]*")?>)?$/;

function readOthers_() {
  return false;   // 다른 법인 탭 열람 허용 (기본). 막으려면 false
}

/* ---------- 쓰기 (칸 단위, 버전 검사) ---------- */
function clean_(html) {
  var s = String(html == null ? '' : html);
  s = s.replace(/<\s*(script|style|iframe|object|embed|link|meta|form)[\s\S]*?(<\/\s*\1\s*>|$)/gi, '');
  s = s.replace(/\son[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '');
  s = s.replace(/javascript:/gi, '');
  return s;
}

/* 저장 전 검증(권한·마감·형식·길이). 통과하면 {c, body, isPhoto} */
function prepSave_(user, cellId, html, weekRows) {
  var c = parseCell_(cellId);
  if (!canEdit_(user, c)) throw new Error('이 칸을 수정할 권한이 없습니다.');
  if (closedFrom_(weekRows, c.ent, c.week) && user.role !== 'hq' && c.week.charAt(0) !== 'M') throw new Error('마감된 주차입니다.');   // 월간(M..) 칸은 마감 후에도 작성자가 쓸 수 있다
  var body = clean_(html);
  var isPhoto = /_p\d+$/.test(c.item);
  if (isPhoto) {                                                   // 사진 칸: VMD 의 경쟁사·금주 항목만, 언어 무관(ko 칸), 사진 한 장(또는 비움)만
    if (!(c.dept === 'VMD' && c.lang === 'ko' && /^(vcomp|vthis)_p[1-4]$/.test(c.item))) throw new Error('사진을 올릴 수 없는 칸입니다.');
    if (!PHOTO_HTML_.test(body)) throw new Error('사진 형식이 올바르지 않습니다.');
    if (body.length > MAX_PHOTO_HTML) throw new Error('사진 용량이 너무 큽니다. 더 작은 사진을 올려 주세요.');
  } else if (body.length > MAX_HTML) throw new Error('내용이 너무 깁니다. (최대 ' + MAX_HTML + '자)');
  return { c: c, body: body, isPhoto: isPhoto };
}

/* 여러 칸을 한 번에 저장 (2026-10-08): 시트 열 한 번 읽고, 잠금 한 번, 이력 한 번에 기록. 번역은 하지 않는다(별도 translate 요청). */
function saveMany_(user, items) {
  if (!items || !items.length || items.length > 60) throw new Error('요청이 올바르지 않습니다.');
  var weekRows = rows_(TAB.WEEKS), results = [], audits = [];
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var sh = sh_(TAB.JOURNAL), n = sh.getLastRow(), map = {};
    if (n >= 2) {
      var ids = sh.getRange(2, 1, n - 1, 1).getValues();
      for (var i = 0; i < ids.length; i++) map[ids[i][0]] = i + 2;
    }
    for (var k = 0; k < items.length; k++) {
      var it = items[k];
      try {
        var p = prepSave_(user, it.cellId, it.html, weekRows);
        var row = map[it.cellId] || -1, cur = row > 0 ? sh.getRange(row, 1, 1, 5).getValues()[0] : null;
        var curVer = cur ? Number(cur[2]) : 0;
        if (curVer !== Number(it.base || 0)) {
          results.push({ ok: false, conflict: true, current: { html: cur ? cur[1] : '', version: curVer, by: cur ? cur[3] : '', at: cur ? String(cur[4]) : '' } });
          continue;
        }
        var ver = curVer + 1, now = new Date();
        if (row > 0) sh.getRange(row, 2, 1, 5).setValues([[p.body, ver, actor_(user), now, '']]);
        else { sh.appendRow([it.cellId, p.body, ver, actor_(user), now, '']); map[it.cellId] = sh.getLastRow(); }
        audits.push([new Date(), actor_(user), 'save', it.cellId, curVer, ver, cur ? String(cur[1]).slice(0, 2000) : '']);
        results.push({ ok: true, version: ver });
      } catch (e) {
        results.push({ ok: false, error: String(e && e.message || e) });
      }
    }
  } finally {
    lock.releaseLock();
  }
  try {
    if (audits.length) { var lg = sh_(TAB.LOG); lg.getRange(lg.getLastRow() + 1, 1, audits.length, audits[0].length).setValues(audits); }
  } catch (e) { /* 이력 실패는 무시 */ }
  return { ok: true, results: results };
}

/* 번역만 따로: 저장이 끝난 칸(ko/en/zh)의 나머지 두 언어를 채운다. 사용자는 이 요청을 기다리지 않는다. */
function translateMany_(user, cellIds) {
  if (!cellIds || !cellIds.length || cellIds.length > 12) throw new Error('요청이 올바르지 않습니다.');
  var sh = sh_(TAB.JOURNAL), n = sh.getLastRow(), map = {}, done = [];
  if (n >= 2) {
    var ids = sh.getRange(2, 1, n - 1, 1).getValues();
    for (var i = 0; i < ids.length; i++) map[ids[i][0]] = i + 2;
  }
  cellIds.forEach(function (id) {
    try {
      var c = parseCell_(id);
      if (!canEdit_(user, c) || !AUTO_TRANSLATE || /_p\d+$/.test(c.item) || !map[id]) return;
      var html = String(sh.getRange(map[id], 2).getValue());
      done.push({ cellId: id, translated: autoTranslate_(id, html) });
    } catch (e) { /* 한 칸 실패가 나머지를 막지 않게 */ }
  });
  return { ok: true, results: done };
}

function save_(user, cellId, html, base, noTranslate) {
  var pr = prepSave_(user, cellId, html, rows_(TAB.WEEKS));
  var c = pr.c, body = pr.body, isPhoto = pr.isPhoto;
  var lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    var sh = sh_(TAB.JOURNAL), n = sh.getLastRow(), row = -1, cur = null;
    if (n >= 2) {
      var ids = sh.getRange(2, 1, n - 1, 1).getValues();
      for (var i = 0; i < ids.length; i++) if (ids[i][0] === cellId) { row = i + 2; break; }
    }
    if (row > 0) cur = sh.getRange(row, 1, 1, 5).getValues()[0];
    var curVer = cur ? Number(cur[2]) : 0;
    if (curVer !== Number(base || 0)) {
      return { ok: false, conflict: true, current: { html: cur ? cur[1] : '', version: curVer, by: cur ? cur[3] : '', at: cur ? String(cur[4]) : '' } };
    }
    var ver = curVer + 1, now = new Date();
    if (row > 0) sh.getRange(row, 2, 1, 5).setValues([[body, ver, actor_(user), now, '']]);
    else sh.appendRow([cellId, body, ver, actor_(user), now, '']);
    audit_(actor_(user), 'save', cellId, curVer, ver, cur ? String(cur[1]).slice(0, 2000) : '');
  } finally {
    lock.releaseLock();
  }
  var tr = (AUTO_TRANSLATE && !isPhoto && !noTranslate) ? autoTranslate_(cellId, body) : [];      // 번역 실패는 저장 결과에 영향을 주지 않는다
  return { ok: true, version: ver, translated: tr };
}

/**
 * 방금 사람이 저장한 칸(cellId)의 내용을 나머지 두 언어 칸에 번역해 넣는다.
 * - 이미 사람이 쓴 칸(auto 표시가 없고 내용이 있는 칸)은 건너뛴다.
 * - 이전에 자동 번역으로 채운 칸은 새 번역으로 바꾼다. 그 칸을 사람이 직접 고쳐 저장하면 그 뒤로는 사람이 쓴 칸이 된다.
 */
function autoTranslate_(cellId, html) {
  var done = [];
  var plain = String(html || '').replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim();
  if (!plain) return done;
  var c = parseCell_(cellId);
  ['ko', 'en', 'zh'].forEach(function (lang) {
    if (lang === c.lang) return;
    var tid = [c.ent, c.week, c.dept, c.item, lang].join('|');
    try {
      var sh = sh_(TAB.JOURNAL), n = sh.getLastRow(), row = -1, cur = null;
      if (n >= 2) {
        var ids = sh.getRange(2, 1, n - 1, 1).getValues();
        for (var i = 0; i < ids.length; i++) if (ids[i][0] === tid) { row = i + 2; break; }
      }
      if (row > 0) {
        cur = sh.getRange(row, 1, 1, 6).getValues()[0];
        if (String(cur[5]) !== 'auto' && String(cur[1]).replace(/<[^>]*>/g, '').trim() !== '') return;   // 사람이 쓴 칸
      }
      var out = clean_(LanguageApp.translate(html, LANG_CODE[c.lang], LANG_CODE[lang], { contentType: 'html' }));
      if (out.length > MAX_HTML) return;
      var lock = LockService.getScriptLock();
      lock.waitLock(15000);
      try {
        n = sh.getLastRow(); row = -1;
        if (n >= 2) {
          var ids2 = sh.getRange(2, 1, n - 1, 1).getValues();
          for (var k = 0; k < ids2.length; k++) if (ids2[k][0] === tid) { row = k + 2; break; }
        }
        var now = new Date();
        if (row > 0) {
          var ver = Number(sh.getRange(row, 3).getValue()) + 1;
          sh.getRange(row, 2, 1, 5).setValues([[out, ver, 'auto-translate', now, 'auto']]);
        } else {
          sh.appendRow([tid, out, 1, 'auto-translate', now, 'auto']);
        }
      } finally {
        lock.releaseLock();
      }
      done.push(lang);
    } catch (e) {
      audit_('auto-translate', 'translate_fail', tid, '', '', String(e && e.message || e).slice(0, 300));
    }
  });
  return done;
}

function audit_(who, action, cellId, base, ver, oldHtml) {
  try { sh_(TAB.LOG).appendRow([new Date(), who, action, cellId, base, ver, oldHtml]); } catch (e) { /* 이력 실패는 무시 */ }
}

/* ---------- 마감 ---------- */
function closeWeek_(user, ent, week, closed) {
  if (user.role !== 'hq') throw new Error('마감은 본사 담당만 할 수 있습니다.');
  if (!/^(HK|TW)$/.test(ent) || !/^[WM]\d{1,2}$/.test(week)) throw new Error('요청이 올바르지 않습니다.');
  var sh = sh_(TAB.WEEKS), r = rows_(TAB.WEEKS), st = closed ? 'closed' : 'open', now = new Date();
  for (var i = r.length - 1; i >= 0; i--) {
    if (r[i][0] === ent && r[i][1] === week) {
      sh.getRange(i + 2, 3, 1, 3).setValues([[st, actor_(user), now]]);
      audit_(actor_(user), closed ? 'close' : 'reopen', ent + '|' + week, '', '', '');
      return { ok: true, closed: !!closed };
    }
  }
  sh.appendRow([ent, week, st, actor_(user), now]);
  audit_(actor_(user), closed ? 'close' : 'reopen', ent + '|' + week, '', '', '');
  return { ok: true, closed: !!closed };
}

/* ---------- "OO 편집 중" ---------- */
function presKey_(ent, week) { return 'pres:' + ent + ':' + week; }

function readPresence_(ent, week) {
  var raw = CacheService.getScriptCache().get(presKey_(ent, week)), out = {}, now = Date.now();
  if (!raw) return out;
  var m = JSON.parse(raw);
  Object.keys(m).forEach(function (id) { if (now - m[id].t < PRES_TTL * 1000) out[id] = m[id]; });
  return out;
}

function presence_(user, ent, week, cell) {
  if (!/^(HK|TW)$/.test(ent) || !/^[WM]\d{1,2}$/.test(week)) throw new Error('요청이 올바르지 않습니다.');
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(3000)) return { ok: true };
  try {
    var m = readPresence_(ent, week);
    Object.keys(m).forEach(function (id) { if (m[id].e === user.sid) delete m[id]; });
    if (cell) {
      parseCell_(cell);
      m[cell] = { n: user.who, e: user.sid, t: Date.now() };
    }
    CacheService.getScriptCache().put(presKey_(ent, week), JSON.stringify(m), 120);
  } finally {
    lock.releaseLock();
  }
  return { ok: true };
}

/* ---------- 화면(HTML) 보관·제공 : ERP 숫자가 들어간 페이지를 이 PC가 만들어 밀어 넣는다 ---------- */
function samePushKey_(k) {
  var want = PropertiesService.getScriptProperties().getProperty('PUSH_KEY');
  k = String(k || '');
  if (!want || k.length !== want.length) return false;
  var d = 0;
  for (var i = 0; i < want.length; i++) d |= want.charCodeAt(i) ^ k.charCodeAt(i);
  return d === 0;
}

function validPage_(name) {
  if (!/^(journal|summary|monthly|yearly|msummary|ysummary|bep)_(HK|TW)(@(W|M)\d{1,2})?$/.test(String(name || ''))) throw new Error('페이지 이름이 올바르지 않습니다.');
  return name;
}

function checkPushKey_(k) {
  var cache = CacheService.getScriptCache(), failKey = 'pushfail';
  if (Number(cache.get(failKey) || 0) >= 10) throw new Error('반영 키를 여러 번 틀려 잠시 잠겼습니다. 15분 뒤 다시 시도하세요.');
  if (!samePushKey_(k)) {
    cache.put(failKey, String(Number(cache.get(failKey) || 0) + 1), LOCK_SEC);
    throw new Error('반영 키가 맞지 않습니다.');
  }
}

/* 반영 결과 조회: 구글 앞단이 응답을 404 로 끊어도 서버는 저장을 끝냈을 수 있다. 반영 프로그램이 pushId 로 실제 저장·검증 여부를 확인한다. */
function pageInfo_(req) {
  checkPushKey_(req.key);
  var name = validPage_(req.name), idx = pageRows_(name);
  if (!idx.length) return { ok: true, found: false };
  var pid = String(sh_(TAB.PAGES).getRange(idx[0], 8).getValue() || '');
  var chk = readPageOnce_(name);
  return { ok: true, found: true, pushId: pid, verified: !!chk.ok, chunks: idx.length };
}

function pushPage_(req) {
  checkPushKey_(req.key);
  var name = validPage_(req.name), html = String(req.html || '').replace(/\r\n?/g, '\n');   // 줄바꿈 통일 (HTML 모양에는 영향 없음)
  if (html.length < 1000) throw new Error('화면 내용이 비어 있습니다.');
  var status = req.status === 'draft' ? 'draft' : 'final', asof = String(req.asof || '').slice(0, 40), pid = String(req.pid || '').slice(0, 40);
  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    storePage_(name, html, status, asof, pid);
    audit_('pipeline', 'push_page', name, '', 1, status + ' ' + asof);
  } finally {
    lock.releaseLock();
  }
  return { ok: true, chunks: 1, status: status };
}

/* ---------- 화면 저장소: 드라이브 파일 (2026-10-08) ----------
   시트 칸(4만 자 조각)에 화면을 담으니 파일이 1,000만 자 넘게 무거워져 로그인까지 느려지고(11초), 조각이 = 로 시작하면 #ERROR! 로 깨졌다.
   이제 화면은 드라이브 폴더(WJ_PAGES)에 파일 하나로 두고, PAGES 탭에는 이름·상태·파일 ID 한 줄만 둔다. */
function pageFolder_() {
  var props = PropertiesService.getScriptProperties(), id = props.getProperty('PAGES_FOLDER');
  if (id) { try { return DriveApp.getFolderById(id); } catch (e) { /* 지워졌으면 새로 만든다 */ } }
  var f = DriveApp.createFolder('WJ_PAGES');
  props.setProperty('PAGES_FOLDER', f.getId());
  return f;
}

function readPageFile_(fid) {
  return DriveApp.getFileById(fid).getBlob().getDataAsString('UTF-8');
}

/** 화면을 드라이브 파일에 쓰고, 읽어서 원본과 같은지 확인한 뒤, PAGES 의 그 이름 줄을 한 줄(파일 ID)로 바꾼다. 잠금 안에서 부른다. */
function storePage_(name, html, status, asof, pid) {
  var folder = pageFolder_(), it = folder.getFilesByName(name), file = it.hasNext() ? it.next() : null;
  if (file) file.setContent(html); else file = folder.createFile(name, html, MimeType.PLAIN_TEXT);
  var fid = file.getId(), back = '';
  for (var t = 0; t < 3; t++) {                                        // 쓴 직후 읽어서 대조 (드라이브 반영이 아주 잠깐 늦을 수 있어 몇 번 확인)
    back = readPageFile_(fid);
    if (back === html) break;
    Utilities.sleep(1000);
  }
  if (back !== html) throw new Error(diffInfo_(name, 0, html, back));
  var sh = sh_(TAB.PAGES);
  deletePageRows_(sh, name);
  sh.appendRow([name, 0, DRIVE_MARK + fid, status, asof, new Date(), html.length, pid]);
}

/** PAGES 탭에서 그 이름의 줄을 모두 지운다 (이어진 줄은 한 번에) */
function deletePageRows_(sh, name) {
  var n = sh.getLastRow();
  if (n < 2) return;
  var names = sh.getRange(2, 1, n - 1, 1).getValues(), hit = [];
  for (var i = 0; i < names.length; i++) if (names[i][0] === name) hit.push(i + 2);
  for (var h = hit.length - 1; h >= 0;) {
    var e = h;
    while (e > 0 && hit[e - 1] === hit[e] - 1) e--;
    sh.deleteRows(hit[e], h - e + 1);
    h = e - 1;
  }
}

/** [편집기에서 한 번 실행] 시트 조각으로 남아 있는 옛 화면(지난 주 보관본 등)을 드라이브로 옮겨 시트를 가볍게 한다.
    처음 실행할 때 드라이브 권한을 묻는다. 시간이 모자라면 멈추니, '남음'이 0 이 될 때까지 다시 실행하면 된다. */
function migratePagesToDrive() {
  var sh = sh_(TAB.PAGES), n = sh.getLastRow(), order = [], seen = {}, bad = [], done = 0, t0 = Date.now();
  if (n >= 2) {
    sh.getRange(2, 1, n - 1, 3).getValues().forEach(function (r) {
      var nm = String(r[0]);
      if (nm && !seen[nm] && String(r[2]).indexOf(DRIVE_MARK) !== 0) { seen[nm] = true; order.push(nm); }
    });
  }
  for (var i = 0; i < order.length && Date.now() - t0 < 270000; i++) {
    var lock = LockService.getScriptLock();
    lock.waitLock(30000);
    try {
      var idx = pageRows_(order[i]);
      if (!idx.length) continue;
      var meta = sh.getRange(idx[0], 1, 1, 8).getValues()[0], pg = readPageOnce_(order[i]);
      if (!pg.ok) { bad.push(order[i]); continue; }
      storePage_(order[i], pg.html, meta[3], meta[4], String(meta[7] || ''));
      done++;
    } finally {
      lock.releaseLock();
    }
  }
  var left = order.length - done - bad.length;
  var msg = '드라이브로 옮김 ' + done + '개 / 남음 ' + left + '개' + (left ? ' (다시 실행하세요)' : '')
    + (bad.length ? ' / 손상되어 못 옮김(숫자 반영을 다시 하면 해결): ' + bad.join(', ') : '');
  Logger.log(msg);
  return msg;
}

/** 원본 조각과 시트에서 읽은 조각이 처음 달라지는 위치와 그 주변 글자 (손상 원인 진단용) */
function diffInfo_(name, seq, want, got) {
  var i = 0, n = Math.min(want.length, got.length);
  while (i < n && want.charCodeAt(i) === got.charCodeAt(i)) i++;
  function cp(str) { var c = str.charCodeAt(i); return isNaN(c) ? '(끝)' : 'U+' + ('0000' + c.toString(16)).slice(-4).toUpperCase(); }
  function near(str) { return JSON.stringify(str.substring(Math.max(0, i - 20), i + 30)); }
  return '손상 진단 ' + name + ' 조각#' + seq + ': 원본 ' + want.length + '자 → 시트 ' + got.length + '자, 첫 차이 위치 ' + i
    + ', 원본 ' + cp(want) + ' ' + near(want) + ' / 시트 ' + cp(got) + ' ' + near(got);
}

/** PAGES 탭에서 이름이 같은 조각들의 행 번호 (이름 열만 읽는다) */
function pageRows_(name) {
  var sh = sh_(TAB.PAGES), n = sh.getLastRow(), idx = [];
  if (n < 2) return idx;
  var names = sh.getRange(2, 1, n - 1, 1).getValues();
  for (var i = 0; i < names.length; i++) if (names[i][0] === name) idx.push(i + 2);
  return idx;
}

/* 화면 읽기: 반영(push)과 겹치지 않게 잠금 안에서 읽고, 조각 합계가 기록된 전체 길이와 다르면(조각이 빠짐) 다시 읽는다.
   (2026-10-08 홍콩 SUMMARY 가운데 4만 자가 통째로 빠져 보인 사고: 반영 중 읽기로 조각이 섞인 것으로 추정) */
function getPage_(user, name) {
  validPage_(name);
  var last = readPageOnce_(name);                                  // 드라이브 화면은 잠금 없이 바로 읽는다 (사용자끼리 줄 서지 않게)
  if (last.ok) return last;
  var lock = LockService.getScriptLock(), locked = true;
  try { lock.waitLock(15000); } catch (e) { locked = false; }
  try {
    for (var tryN = 0; tryN < 3; tryN++) {
      last = readPageOnce_(name);
      if (last.ok) return last;
      Utilities.sleep(1200);
    }
  } finally {
    if (locked) lock.releaseLock();
  }
  throw new Error('화면 데이터가 갱신 중입니다. 잠시 뒤 다시 열어 주세요.');
}

function readPageOnce_(name) {
  var idx = pageRows_(name), sh = sh_(TAB.PAGES), parts = [], status = '', asof = '', total = 0;
  if (!idx.length) throw new Error('아직 이 화면이 준비되지 않았습니다. 숫자 반영이 끝난 뒤 다시 열어 주세요.');
  if (idx.length === 1) {
    var one = sh.getRange(idx[0], 1, 1, 7).getValues()[0], ref = String(one[2]);
    if (ref.indexOf(DRIVE_MARK) === 0) {
      var h1 = readPageFile_(ref.substring(DRIVE_MARK.length));
      if (Number(one[6]) && h1.length !== Number(one[6])) return { ok: false };
      return { ok: true, html: h1, status: one[3], asOf: one[4] };
    }
  }
  for (var s = 0; s < idx.length;) {                       // 이어진 행끼리 한 번에 읽는다
    var e = s;
    while (e + 1 < idx.length && idx[e + 1] === idx[e] + 1) e++;
    var vals = sh.getRange(idx[s], 1, e - s + 1, 7).getValues();
    for (var k = 0; k < vals.length; k++) {
      var pc = String(vals[k][2]);
      parts[Number(vals[k][1])] = pc.indexOf(CHUNK_MARK) === 0 ? pc.substring(CHUNK_MARK.length) : pc;
      status = vals[k][3];
      asof = vals[k][4];
      total = Number(vals[k][6]) || total;
    }
    s = e + 1;
  }
  for (var q = 0; q < parts.length; q++) if (parts[q] === undefined || (q < parts.length - 1 && !parts[q].length)) return { ok: false };
  var html = parts.join('');
  if (total && html.length !== total) return { ok: false };      // 옛 형식(전체 길이 기록 없음)은 검사하지 않는다
  return { ok: true, html: html, status: status, asOf: asof };
}

/** 보관된 주차 목록 (지난 주 보기용). 본문(조각)은 읽지 않는다. */
/* ISO 주차(W1~W53) → '9/21–9/27' (월~일). 화면 위쪽 4주 목록과 같은 모양으로 보관본 목록을 보여주기 위해 */
function weekRange_(wk, year) {
  var n = Number(String(wk).slice(1)), j4 = new Date(Date.UTC(year, 0, 4)), dow = (j4.getUTCDay() + 6) % 7;
  var mon = new Date(j4.getTime() + ((n - 1) * 7 - dow) * 86400000), sun = new Date(mon.getTime() + 6 * 86400000);
  return (mon.getUTCMonth() + 1) + '/' + mon.getUTCDate() + '–' + (sun.getUTCMonth() + 1) + '/' + sun.getUTCDate();
}

function listArchive_(user) {
  var sh = sh_(TAB.PAGES), n = sh.getLastRow(), byWeek = {};
  if (n >= 2) {
    var ab = sh.getRange(2, 1, n - 1, 2).getValues(), de = sh.getRange(2, 4, n - 1, 2).getValues();
    for (var i = 0; i < ab.length; i++) {
      if (Number(ab[i][1]) !== 0) continue;                // 첫 조각 행만
      var m = /^(journal|summary)_(HK|TW)@(W\d+)$/.exec(String(ab[i][0]));
      if (!m) continue;
      var yr = new Date(de[i][1]).getFullYear(); if (!(yr > 2000)) yr = new Date().getFullYear();
      var w = byWeek[m[3]] = byWeek[m[3]] || { week: m[3], pages: [], status: de[i][0], asOf: weekRange_(m[3], yr), pushedAt: String(de[i][1]) };
      w.pages.push(ab[i][0]);
    }
  }
  var closed = {};
  rows_(TAB.WEEKS).forEach(function (r) { if (r[2] === 'closed') closed[r[0] + '|' + r[1]] = true; });
  var weeks = Object.keys(byWeek).map(function (k) {
    var w = byWeek[k];
    w.closed = { HK: !!closed['HK|' + k], TW: !!closed['TW|' + k] };
    return w;
  }).sort(function (a, b) { return Number(b.week.slice(1)) - Number(a.week.slice(1)); });
  return { ok: true, weeks: weeks };
}
