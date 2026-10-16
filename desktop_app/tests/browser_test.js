const { chromium } = require('playwright');
const [base, key, ctl] = process.argv.slice(2);
const ok = (c, m) => { console.log((c ? 'PASS: ' : 'FAIL: ') + m); if (!c) process.exitCode = 1; };
const ctlCall = async (q) => (await (await fetch(ctl + q)).json());
(async () => {
  const b = await chromium.launch(); const ctx = await b.newContext(); const p = await ctx.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  // 1) 열쇠 없이 접근하면 막힌다
  const r0 = await ctx.request.get(base + '/'); ok(r0.status() === 403, '열쇠(쿠키) 없이 접근 → 403 차단');
  const r00 = await ctx.request.post(base + '/api', { data: '{"a":"save"}' }); ok(r00.status() === 403, '열쇠 없이 /api 호출 → 403 차단');
  // 2) 앱 창이 열쇠로 열면 로그인 화면
  await p.goto(base + '/?k=' + key); ok(await p.locator('#f').count() === 1, '처음 열면 로그인 화면');
  // 3) 틀린 비밀번호
  await p.fill('#i', 'tw'); await p.fill('#w', 'wrong'); await p.fill('#n', 'owen'); await p.click('#b');
  await p.waitForFunction(() => document.getElementById('m').textContent.includes('incorrect')); ok(true, '틀린 비밀번호 → 오류 메시지 표시');
  // 4) 로그인 성공 → 첫 화면
  await p.fill('#w', 'pw12345678'); await p.click('#b'); await p.waitForSelector('h1'); 
  ok((await p.textContent('h1')) === 'JOURNAL_TW', '로그인 후 첫 화면(JOURNAL_TW) 표시');
  ok((await p.evaluate(() => localStorage.getItem('wj_tok_TW'))) === 'app', '화면 안 자바스크립트에는 자리표시자 열쇠("app")만 있음');
  const html = await p.content(); const mockUrl = (await ctlCall('?q=url')).url;
  ok(!html.includes(mockUrl), '화면 안의 서버 주소가 앱 주소(/api)로 바뀜');
  // 5) 화면 이동 + 한 번 받은 화면은 서버를 다시 부르지 않음
  ok(await p.locator('#wjapp').count() === 1, "오른쪽 아래 '↻ 최신 데이터 받기' 버튼이 붙음");
  await p.waitForTimeout(4500);                       // 미리 받기(3초 뒤 시작)가 끝나기를 기다림
  await p.click('#go'); await p.waitForFunction(() => document.querySelector('h1').textContent === 'SUMMARY_TW'); ok(true, '화면 이동(document.write 방식)이 앱을 거쳐 동작');
  const mid = (await ctlCall('?q=count&a=page')).n;
  await p.click('#go'); await p.waitForFunction(() => document.querySelector('h1').textContent === 'JOURNAL_TW');
  await p.click('#go'); await p.waitForFunction(() => document.querySelector('h1').textContent === 'SUMMARY_TW');
  const after = (await ctlCall('?q=count&a=page')).n; ok(after === mid, `한 번 받은 화면은 서버를 다시 부르지 않음 (page 호출 ${mid} → ${after})`);
  // 5-1) 저장본이 오래됐어도 먼저 바로 열고, 뒤에서 새로 받음
  await ctlCall('?q=agecache&name=journal_TW&sec=900'); const pc0 = (await ctlCall('?q=pagecount&name=journal_TW')).n;
  const t0 = Date.now(); await p.goto(base + '/'); const dt = Date.now() - t0;
  ok((await p.textContent('h1')) === 'JOURNAL_TW', '오래된 저장본도 먼저 바로 열림');
  await p.waitForTimeout(1200); ok((await ctlCall('?q=pagecount&name=journal_TW')).n === pc0 + 1, '열어 준 뒤 뒤에서 새로 받아 둠 (+1회)');
  // 5-2) 같은 화면을 동시에 두 번 요청해도 서버는 한 번만
  await ctlCall('?q=clearcache'); const pc1 = (await ctlCall('?q=pagecount&name=monthly_TW')).n;
  const rr = await Promise.all([ctx.request.post(base + '/api', { data: JSON.stringify({a:'page', name:'monthly_TW'}) }), ctx.request.post(base + '/api', { data: JSON.stringify({a:'page', name:'monthly_TW'}) })]);
  console.log('  (동시 요청 응답:', rr.map(r => r.status()).join(','), (await rr[0].text()).slice(0,120), ')'); ok(rr.every(r => r.status() === 200), '동시에 두 번 요청해도 둘 다 정상 응답');
  ok((await ctlCall('?q=pagecount&name=monthly_TW')).n === pc1 + 1, '동시 요청은 서버를 한 번만 부름 (중복 호출 방지)');
  // 5-3) '최신 데이터 받기' 버튼
  await p.goto(base + '/'); await p.waitForSelector('#wjrf'); const pc2 = (await ctlCall('?q=pagecount&name=journal_TW')).n;
  await p.click('#wjrf'); await p.waitForTimeout(1200); ok((await ctlCall('?q=pagecount&name=journal_TW')).n >= pc2 + 1, "'최신 데이터 받기'를 누르면 서버에서 새로 받음");
  ok((await p.textContent('h1')) === 'JOURNAL_TW', '새로 받은 뒤에도 같은 화면 유지');
  // 6) 저장은 진짜 열쇠를 붙여 서버로 전달
  const sv = await p.evaluate(() => window.__save()); ok(sv.ok === true, '글 저장 요청이 기존 서버까지 전달됨');
  const seen = (await ctlCall('?q=lasttoken&a=save')).token; ok(seen === 'REALTOKEN_0123456789', '서버에는 진짜 열쇠가 붙어서 도착 (화면은 몰랐음)');
  // 7) 인터넷(서버) 끊김 → 저장해 둔 화면으로 열림
  await ctlCall('?q=ttl0'); await ctlCall('?q=offline&v=1');
  await p.goto(base + '/'); ok((await p.textContent('h1')) === 'JOURNAL_TW', '서버가 응답하지 않아도 저장해 둔 화면이 열림');
  await ctlCall('?q=offline&v=0');
  // 8) 로그인 만료 → 로그인 화면으로
  await ctlCall('?q=expire&v=1'); 
  await p.click('#go'); await p.waitForSelector('#f'); ok(true, '로그인이 만료되면 로그인 화면으로 돌아감');
  console.log('JS errors:', errs.length ? errs : 0);
  await b.close();
})().catch(e => { console.log('FAIL: 예외', e.message); process.exit(1); });
