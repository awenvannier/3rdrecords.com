/**
 * 3rd Records · site backend (Google Apps Script web app, free).
 *  - duck game scoreboard: Sheet "3rd Records Duck Scoreboard", tab "scores"
 *  - music submissions (/submit/): Sheet "3rd Records Submissions", tab "submissions" + e-mail to NOTIFY
 * Standalone script (awen.vannier@gmail.com).
 * Deploy → New deployment → Web app · Execute as: Me · Who has access: Anyone
 * → copy the /exec URL into site.json "duck_api" and "submit_api".
 * After editing: Deploy > Manage deployments > edit > Version: New version (the URL stays the same).
 */
const SHEET_ID = '1W7vrxGeZCpaFcnand1v9-TfHapY1rlpF-Xjh5ZlTVRI';
const SUBMIT_SHEET_ID = '1pvF8Up-204bJhaS9UiKUPQBDc9QJMM_2NTMPupXq9hw';
const NOTIFY = 'contact@3rdrecords.com';
const ROUND = 30, MAX_SCORE = 400, KEEP = 500;

function sheet_() {
  const ss = SpreadsheetApp.openById(SHEET_ID);
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
  if (b && b.kind === 'submission') return submit_(b);
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

/* ---------------------------------------------------------------- submissions */

const GENRES = ['Pop', 'Bedroom pop', 'Lofi', 'Hip-hop', 'Other'];
const SUB_HEAD = ['Received', 'Artist', 'E-mail', 'Track title', 'Genre', 'Track link', 'Instagram', 'Streaming profile', 'Description', 'Status'];

function subSheet_() {
  const ss = SpreadsheetApp.openById(SUBMIT_SHEET_ID);
  let sh = ss.getSheetByName('submissions');
  if (!sh) {
    sh = ss.insertSheet('submissions', 0);
    sh.appendRow(SUB_HEAD);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, SUB_HEAD.length).setFontWeight('bold');
    const first = ss.getSheets().filter(x => x.getName() !== 'submissions')[0];
    if (first && first.getLastRow() === 0) ss.deleteSheet(first);
  }
  return sh;
}
function str_(v, max) {
  return String(v == null ? '' : v).replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, '').trim().slice(0, max);
}
function cell_(v) { // never let a submission become a spreadsheet formula
  return typeof v === 'string' && /^[=+\-@]/.test(v) ? "'" + v : v;
}
function url_(v) {
  const u = str_(v, 500);
  return /^https?:\/\/[^\s/$.?#][^\s]*\.[^\s]{2,}/i.test(u) ? u : '';
}
function insta_(v) {
  const h = str_(v, 200).replace(/^https?:\/\/(www\.)?instagram\.com\//i, '').replace(/^@/, '').split(/[/?#]/)[0];
  return /^[A-Za-z0-9._]{1,30}$/.test(h) ? 'https://www.instagram.com/' + h + '/' : '';
}

function submit_(b) {
  if (str_(b.website, 10)) return out_({ ok: true });            // honeypot: pretend it worked
  if (Number(b.elapsed) < 4000) return out_({ ok: false, err: 'fast' });
  const f = {
    artist: str_(b.artist, 80),
    email: str_(b.email, 120).toLowerCase(),
    title: str_(b.title, 120),
    genre: GENRES.indexOf(String(b.genre)) >= 0 ? String(b.genre) : '',
    track: url_(b.track),
    instagram: insta_(b.instagram),
    profile: url_(b.profile),
    about: str_(b.about, 1500),
  };
  const bad = [];
  if (!f.artist) bad.push('artist');
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(f.email)) bad.push('email');
  if (!f.title) bad.push('title');
  if (!f.genre) bad.push('genre');
  if (!f.track) bad.push('track');
  if (!f.instagram) bad.push('instagram');
  if (!f.profile) bad.push('profile');
  if (f.about.length < 20) bad.push('about');
  if (b.rights !== true) bad.push('rights');
  if (bad.length) return out_({ ok: false, err: 'invalid', fields: bad });

  const cache = CacheService.getScriptCache();
  const kMail = 'sub:' + f.email, kAll = 'sub:all';
  const nMail = Number(cache.get(kMail) || 0), nAll = Number(cache.get(kAll) || 0);
  if (nMail >= 3) return out_({ ok: false, err: 'limit' });
  if (nAll >= 60) return out_({ ok: false, err: 'busy' });

  const lock = LockService.getScriptLock();
  lock.waitLock(5000);
  try {
    subSheet_().appendRow([new Date(), f.artist, f.email, f.title, f.genre, f.track, f.instagram, f.profile, f.about, 'New'].map(cell_));
    SpreadsheetApp.flush();
  } finally {
    lock.releaseLock();
  }
  cache.put(kMail, String(nMail + 1), 6 * 3600);
  cache.put(kAll, String(nAll + 1), 3600);

  try {
    MailApp.sendEmail({
      to: NOTIFY,
      replyTo: f.email,
      name: '3rd Records website',
      subject: 'New submission (' + f.genre + '): ' + f.artist + ' - ' + f.title,
      body: [
        'New music submission from 3rdrecords.com/submit/',
        '',
        'Artist: ' + f.artist,
        'E-mail: ' + f.email,
        'Track: ' + f.title,
        'Genre: ' + f.genre,
        'Listen: ' + f.track,
        'Instagram: ' + f.instagram,
        'Streaming profile: ' + f.profile,
        '',
        f.about,
        '',
        'All submissions: https://docs.google.com/spreadsheets/d/' + SUBMIT_SHEET_ID + '/edit',
        'Reply to this e-mail to answer the artist directly.',
      ].join('\n'),
    });
  } catch (_) { /* the row is saved even if the e-mail fails */ }
  return out_({ ok: true });
}

/* Run once from the editor (select "authorize" > Run) to grant the e-mail permission. Sends nothing. */
function authorize() {
  Logger.log('Mail quota left today: ' + MailApp.getRemainingDailyQuota());
  Logger.log('Submissions sheet: ' + subSheet_().getParent().getName());
}
