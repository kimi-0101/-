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
  // 5) 화면 이동 (캐시 저장 → 서버를 다시 부르지 않음)
  await p.waitForTimeout(1500);                       // 미리 받기 끝나기를 잠깐 기다림
  const before = (await ctlCall('?q=count&a=page')).n;
  await p.click('#go'); await p.waitForFunction(() => document.querySelector('h1').textContent === 'SUMMARY_TW'); ok(true, '화면 이동(document.write 방식)이 앱을 거쳐 동작');
  await p.click('#go'); await p.waitForFunction(() => document.querySelector('h1').textContent === 'JOURNAL_TW');
  const after = (await ctlCall('?q=count&a=page')).n; ok(after === before, `저장해 둔 화면은 서버를 다시 부르지 않음 (page 호출 ${before} → ${after})`);
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
