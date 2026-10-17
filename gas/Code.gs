/**
 * かんじ練習帳の記録係。スプレッドシートの「拡張機能 → Apps Script」に貼り付けて使う。
 * iPhone・iPad のアプリが、ここを通して同じ記録を読み書きする。
 *
 * ① 下の KEY を、家族で決めた合言葉に書きかえる（アプリにも同じ合言葉を入れる）
 * ② 「デプロイ → 新しいデプロイ → ウェブアプリ」
 *    次のユーザーとして実行：自分 ／ アクセスできるユーザー：全員
 * ③ 写真の字の読みとりを使うときは、左の「サービス ＋」から「Drive API」を追加する
 *    （Googleドライブの文字読みとり＝OCR を使う。無料。写真は読みとったらすぐ消す）
 */
const KEY = 'ここに合言葉';

const SHEET_KANJI = '漢字の記録';
const SHEET_KANA = 'かなクイズの記録';
const SHEET_LISTS = '登録したリスト';

function doGet(e) {
  if (!e || !e.parameter || e.parameter.key !== KEY) return json_({ error: 'key' });
  return json_(load_());
}

function doPost(e) {
  let body;
  try { body = JSON.parse(e.postData.contents); } catch (err) { return json_({ error: 'bad' }); }
  if (body.key !== KEY) return json_({ error: 'key' });
  if (body.ocr) {
    try { return json_({ text: ocr_(body.ocr, body.type) }); } catch (err) { return json_({ error: 'ocr', msg: String(err) }); }
  }
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const merged = merge_(load_(), body.state || {});
    save_(merged);
    return json_(merged);
  } finally {
    lock.releaseLock();
  }
}

// 写真を いったん Googleドキュメントに 変えて 文字を 読みとり、すぐ 消す
function ocr_(b64, type) {
  const blob = Utilities.newBlob(Utilities.base64Decode(b64), type || 'image/jpeg', 'kanji.jpg');
  let id;
  if (Drive.Files.create) id = Drive.Files.create({ name: 'かんじ読みとり', mimeType: 'application/vnd.google-apps.document' }, blob, { ocrLanguage: 'ja' }).id;
  else id = Drive.Files.insert({ title: 'かんじ読みとり', mimeType: 'image/jpeg' }, blob, { ocr: true, ocrLanguage: 'ja' }).id;
  try { return DocumentApp.openById(id).getBody().getText(); }
  finally { try { Drive.Files.remove(id); } catch (err) { DriveApp.getFileById(id).setTrashed(true); } }
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

// 端末どうしの記録を合わせる。字ごとに「最後にやったほう」を残す
function merge_(a, b) {
  const pick = (x, y) => {
    const out = Object.assign({}, x);
    Object.keys(y || {}).forEach(k => { if (!out[k] || (y[k].last || 0) > (out[k].last || 0)) out[k] = y[k]; });
    return out;
  };
  const newer = (b.listsT || 0) > (a.listsT || 0);
  return {
    lists: newer ? (b.lists || []) : a.lists,
    listsT: newer ? b.listsT : a.listsT,
    stats: pick(a.stats, b.stats),
    kstats: pick(a.kstats, b.kstats),
  };
}

function sheet_(name, header) {
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.getRange(1, 1, 1, header.length).setValues([header]).setFontWeight('bold');
    sh.setFrozenRows(1);
  }
  return sh;
}

const H_KANJI = ['字', 'テストで○', 'テストで△', '連続○', 'れんしゅう回数', '最後にやった日', '状態', '(内部)最終時刻'];
const H_KANA = ['番号', '問題', '○', '×', '連続○', '最後にやった日', '(内部)最終時刻'];
const H_LISTS = ['名前', '中身', '(内部)id'];

function rows_(sh) {
  const n = sh.getLastRow() - 1;
  return n > 0 ? sh.getRange(2, 1, n, sh.getLastColumn()).getValues() : [];
}

function load_() {
  const stats = {}, kstats = {};
  rows_(sheet_(SHEET_KANJI, H_KANJI)).forEach(r => {
    if (r[0]) stats[r[0]] = { ok: +r[1] || 0, ng: +r[2] || 0, st: +r[3] || 0, p: +r[4] || 0, last: +r[7] || 0 };
  });
  rows_(sheet_(SHEET_KANA, H_KANA)).forEach(r => {
    if (r[0] !== '') kstats[r[0]] = { q: r[1], ok: +r[2] || 0, ng: +r[3] || 0, st: +r[4] || 0, last: +r[6] || 0 };
  });
  const lsh = sheet_(SHEET_LISTS, H_LISTS);
  // リストを全部消したときも時刻が残るよう、更新時刻は表とは別に持つ
  const listsT = +PropertiesService.getScriptProperties().getProperty('listsT') || 0;
  const lists = rows_(lsh).filter(r => r[2]).map(r => {
    let items = [];
    try { items = JSON.parse(r[1]); } catch (err) {}
    return { id: r[2], name: r[0], items: items };
  });
  return { lists: lists, listsT: listsT, stats: stats, kstats: kstats };
}

function day_(ms) {
  return ms ? Utilities.formatDate(new Date(ms), 'Asia/Tokyo', 'yyyy/MM/dd') : '';
}

function write_(sh, header, rows) {
  const n = sh.getLastRow();
  if (n > 1) sh.getRange(2, 1, n - 1, header.length).clearContent();
  if (rows.length) sh.getRange(2, 1, rows.length, header.length).setValues(rows);
}

function save_(s) {
  const status = v => v.st >= 3 ? 'おぼえた' : (v.st === 0 && v.ng > 0) ? 'にがて' : (v.ok || v.ng) ? 'かけた' : 'れんしゅうだけ';
  write_(sheet_(SHEET_KANJI, H_KANJI), H_KANJI, Object.keys(s.stats || {}).sort().map(k => {
    const v = s.stats[k];
    return [k, v.ok || 0, v.ng || 0, v.st || 0, v.p || 0, day_(v.last), status(v), v.last || 0];
  }));
  write_(sheet_(SHEET_KANA, H_KANA), H_KANA, Object.keys(s.kstats || {}).sort((a, b) => a - b).map(k => {
    const v = s.kstats[k];
    return [+k, v.q || '', v.ok || 0, v.ng || 0, v.st || 0, day_(v.last), v.last || 0];
  }));
  // リストの中身は、アプリの入力欄と同じ書き方で残す（JSONのまま。表で直さない）
  write_(sheet_(SHEET_LISTS, H_LISTS), H_LISTS, (s.lists || []).map(l => [l.name, JSON.stringify(l.items), l.id]));
  PropertiesService.getScriptProperties().setProperty('listsT', String(s.listsT || 0));
}
