/**
 * 3rd Records · duck game scoreboard (Google Apps Script web app, free).
 * Setup: Google Sheet → Extensions → Apps Script → paste this → Deploy → New deployment
 * → Web app · Execute as: Me · Who has access: Anyone → copy the /exec URL into site.json "duck_api".
 */
const ROUND = 30, MAX_SCORE = 400, KEEP = 500;

function sheet_() {
  const ss = SpreadsheetApp.getActive();
  return ss.getSheetByName('scores') || ss.insertSheet('scores');
}
function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
function top_() {
  const sh = sheet_(), n = sh.getLastRow();
  if (!n) return [];
  return sh.getRange(1, 1, n, 4).getValues()
    .filter(r => r[0] && typeof r[2] === 'number')
    .sort((a, b) => b[2] - a[2] || new Date(a[3]) - new Date(b[3]))
    .slice(0, 10)
    .map(r => ({ id: String(r[0]), name: String(r[1]), score: r[2] }));
}
function clean_(n) {
  return String(n || '').normalize('NFKC').replace(/[^\p{L}\p{N} ._-]/gu, '')
    .replace(/\s+/g, ' ').trim().slice(0, 12);
}

function doGet(e) {
  const a = (e && e.parameter && e.parameter.a) || 'top';
  if (a === 'start') {
    const t = Utilities.getUuid();
    CacheService.getScriptCache().put(t, String(Date.now()), 900);
    return out_({ ok: true, t: t });
  }
  return out_({ ok: true, top: top_() });
}

function doPost(e) {
  let b;
  try { b = JSON.parse(e.postData.contents); } catch (_) { return out_({ ok: false, err: 'json' }); }
  const cache = CacheService.getScriptCache();
  const started = Number(cache.get(String(b.t || '')));
  if (!started) return out_({ ok: false, err: 'token' });
  cache.remove(String(b.t));
  if (Date.now() - started < (ROUND - 2) * 1000) return out_({ ok: false, err: 'early' });
  const name = clean_(b.name), score = Math.floor(Number(b.score));
  if (!name || !(score > 0) || score > MAX_SCORE) return out_({ ok: false, err: 'invalid' });

  const lock = LockService.getScriptLock();
  lock.waitLock(5000);
  try {
    const sh = sheet_(), id = Utilities.getUuid().slice(0, 8);
    sh.appendRow([id, name, score, new Date()]);
    if (sh.getLastRow() > KEEP + 50) {
      sh.getRange(1, 1, sh.getLastRow(), 4).sort({ column: 3, ascending: false });
      sh.deleteRows(KEEP + 1, sh.getLastRow() - KEEP);
    }
    SpreadsheetApp.flush();
    return out_({ ok: true, id: id, top: top_() });
  } finally {
    lock.releaseLock();
  }
}
