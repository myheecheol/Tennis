/**
 * 복식 무브 검증판 — 기록 받기 (Google Apps Script)
 *
 * 검증판 게임(web/play.html)을 claude.ai 밖(GitHub Pages, Netlify 등)에 올려 여러 사람에게 공개할 때,
 * 게임이 보내는 이벤트를 구글 시트에 한 줄씩 쌓는다. 설정 방법은 design/08-phase1.md 의 "공개 테스트" 참고.
 *
 *   1) 구글 시트를 새로 만든다 → 확장 프로그램 → Apps Script
 *   2) 이 파일 내용을 그대로 붙여 넣고 저장한다
 *   3) 배포 → 새 배포 → 유형: 웹 앱 → 실행: 나 → 액세스 권한: 모든 사용자 → 배포
 *   4) 나온 웹 앱 주소(https://script.google.com/macros/s/…/exec)를 web/play.config.json 의 endpoint 에 넣고
 *      python3 web/build.py 로 web/play.html 을 다시 만든다
 *
 * 게임이 보내는 몸통: {"u": "p_…(브라우저마다 무작위 익명 id)", "events": [{"t": ISO 시각, "e": 이벤트, …}]}
 * 이벤트 종류와 칸의 뜻도 design/08-phase1.md 에 있다. 이름이나 연락처는 오지 않는다.
 */
var HEAD = ['받은 시각', '참여자', '시각', '이벤트', '카드', '결과', '보기', '걸린 ms', '복습', '세션', '나머지'];
var KNOWN = ['t', 'e', 'c', 'v', 'o', 'ms', 'rev', 'sid'];

function doPost(e) {
  var body;
  try { body = JSON.parse(e.postData.contents); } catch (err) { return ContentService.createTextOutput('bad json'); }
  var events = (body && body.events) || [];
  if (!Array.isArray(events) || events.length > 200) return ContentService.createTextOutput('bad events');
  var who = String(body.u || '').slice(0, 40);
  var rows = events.map(function (ev) {
    var rest = {};
    Object.keys(ev || {}).forEach(function (k) { if (KNOWN.indexOf(k) < 0) rest[k] = ev[k]; });
    return [new Date(), who, cut(ev.t), cut(ev.e), cut(ev.c), cut(ev.v), ev.o == null ? '' : ev.o,
            ev.ms == null ? '' : ev.ms, ev.rev ? 1 : '', cut(ev.sid), cut(JSON.stringify(rest), 500)];
  });
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);   // 여러 사람이 동시에 보내도 줄이 겹치지 않게
  try {
    var book = SpreadsheetApp.getActiveSpreadsheet();
    var sh = book.getSheetByName('events') || book.insertSheet('events');
    if (sh.getLastRow() === 0) sh.appendRow(HEAD);
    if (rows.length) sh.getRange(sh.getLastRow() + 1, 1, rows.length, HEAD.length).setValues(rows);
  } finally {
    lock.releaseLock();
  }
  return ContentService.createTextOutput('ok');
}

function cut(v, n) {
  return v == null ? '' : String(v).slice(0, n || 80);
}
