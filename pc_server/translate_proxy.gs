/**
 * 영업일지 PC 서버용 번역 전용 웹앱 (구글 번역 = LanguageApp)
 *
 * 일지 데이터는 저장하지 않습니다. PC 서버가 보낸 글을 번역해서 돌려주기만 합니다.
 * 요청: POST, 본문 JSON {key, text, src, dst}  (src/dst: ko, en, zh-TW)   응답: {ok:true, text} 또는 {ok:false, error}
 *
 * 설치 (한 번만, 5분):
 *  1) script.google.com → 새 프로젝트 → 이 파일 내용을 붙여넣기 (기존 영업일지 시트와 별개의 새 프로젝트)
 *  2) 함수 목록에서 setup 선택 → 실행 → 권한 허용. 실행 로그에 나온 열쇠(KEY)를 복사
 *  3) 배포 → 새 배포 → 유형 "웹 앱" → 실행 사용자: 나 / 액세스: 모든 사용자 → 배포 → 웹 앱 URL 복사
 *  4) PC 의 wj_data\translate_url.txt 에 두 줄로 저장:  첫 줄 = 웹 앱 URL, 둘째 줄 = 열쇠
 *  5) python pc_server\wj_admin.py translate-test "안녕하세요" --to en  으로 확인
 * 열쇠를 아는 서버만 쓸 수 있습니다. 열쇠가 새면 setup 을 다시 실행해 새 열쇠를 만들고 translate_url.txt 도 바꾸세요.
 */
var MAX_CHARS = 30000;

function setup() {
  var key = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
  PropertiesService.getScriptProperties().setProperty('TRANSLATE_KEY', key);
  Logger.log('KEY = ' + key);
  return key;
}

function doPost(e) {
  var out;
  try {
    var req = JSON.parse(e.postData.contents);
    var want = PropertiesService.getScriptProperties().getProperty('TRANSLATE_KEY');
    if (!want || String(req.key || '') !== want) throw new Error('열쇠가 맞지 않습니다.');
    var text = String(req.text || '');
    if (!text || text.length > MAX_CHARS) throw new Error('글이 비었거나 너무 깁니다.');
    var ok = { 'ko': 1, 'en': 1, 'zh-TW': 1 };
    if (!ok[req.src] || !ok[req.dst] || req.src === req.dst) throw new Error('언어 코드가 올바르지 않습니다.');
    out = { ok: true, text: LanguageApp.translate(text, req.src, req.dst, { contentType: 'html' }) };
  } catch (err) {
    out = { ok: false, error: String(err && err.message || err) };
  }
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}
