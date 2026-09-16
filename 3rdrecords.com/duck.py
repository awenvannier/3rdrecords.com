"""Hidden easter egg: 3rdrecords.com/duck/ — click the ducks. Not linked from the site, noindex, not in the sitemap."""
import base64, hashlib, html

DUCK = ('<svg viewBox="0 0 120 100" aria-hidden="true" focusable="false">'
        '<ellipse cx="60" cy="92" rx="38" ry="5" fill="rgba(0,0,0,.28)"/>'
        '<path d="M18 58c0-17 16-26 38-26h14c7 0 12-4 16-9 4 10 10 16 16 20 5 4 6 12 1 19-8 13-25 22-52 22C28 84 18 74 18 58z" fill="#F6A10E"/>'
        '<path d="M30 60c8 9 24 11 36 5-4 10-20 14-32 8-4-3-5-8-4-13z" fill="#D98A04"/>'
        '<circle cx="44" cy="30" r="20" fill="#F6A10E"/>'
        '<path d="M22 30c-8-1-15 1-19 5 5 3 12 5 20 3z" fill="#512321"/>'
        '<path d="M22 34c-6 1-12 2-16 1 4 3 10 4 17 2z" fill="#3a1817"/>'
        '<circle cx="38" cy="25" r="4.2" fill="#1D1D1B"/><circle cx="36.6" cy="23.6" r="1.4" fill="#FEFEFE"/>'
        '<path d="M52 16c4-6 10-7 13-4-5 0-8 2-10 6z" fill="#D98A04"/></svg>')

CSS = """
@font-face{font-family:Avigea;src:url(/fonts/avigea.woff2) format("woff2");font-display:swap}
@font-face{font-family:Roboto;src:url(/fonts/roboto-medium.woff2) format("woff2");font-weight:500;font-display:swap}
:root{--choco:#512321;--orange:#F6A10E;--ink:#1D1D1B;--white:#FEFEFE;--grey:#9E9E9E;color-scheme:dark}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{background:radial-gradient(60% 50% at 50% 45%,rgba(246,161,14,.16),transparent 70%),var(--ink);color:var(--white);font:500 14px/1.4 Roboto,system-ui,sans-serif;overflow:hidden;-webkit-font-smoothing:antialiased;user-select:none;-webkit-user-select:none;touch-action:manipulation}
a,button{color:inherit;font:inherit}
.up{text-transform:uppercase;letter-spacing:.2em;font-size:11px}
.hud{position:fixed;inset:0 0 auto;z-index:5;display:flex;justify-content:space-between;align-items:center;gap:12px;padding:16px clamp(16px,4vw,32px);pointer-events:none}
.hud>*{pointer-events:auto}
.hud a{color:var(--grey);text-decoration:none;white-space:nowrap}@media (max-width:480px){.hud .up{letter-spacing:.1em}.stats{gap:10px}}.hud a:hover{color:var(--orange)}
.stats{display:flex;gap:clamp(14px,3vw,28px);align-items:baseline}
.stats b{font:400 clamp(26px,4vw,40px)/1 Avigea,Georgia,serif;color:var(--orange);margin-left:6px}
.center{position:fixed;inset:0;display:grid;place-content:center;justify-items:center;gap:14px;text-align:center;padding:24px;z-index:3;transition:opacity .4s}
.center.hide{opacity:0;pointer-events:none}
h1{font:400 clamp(64px,14vw,170px)/.9 Avigea,Georgia,serif;color:var(--orange)}
.center p{color:#d7d2cc;max-width:32ch;font-size:15px}.center p.up{max-width:none;color:var(--grey)}
.btn{margin-top:8px;height:48px;padding:0 28px;border-radius:999px;border:1px solid var(--white);background:none;cursor:pointer;text-transform:uppercase;letter-spacing:.2em;font-size:12px;transition:background-color .2s,color .2s,transform .2s}
.btn:hover,.btn:focus-visible{background:var(--orange);border-color:var(--orange);color:var(--ink)}
.btn:active{transform:scale(.96)}
:focus-visible{outline:2px solid var(--orange);outline-offset:3px}
.layer{position:fixed;inset:0;z-index:4;pointer-events:none;overflow:hidden}
.duck{position:absolute;left:0;top:0;border:0;background:none;padding:0;cursor:pointer;pointer-events:auto;will-change:transform;filter:drop-shadow(0 8px 12px rgba(0,0,0,.35));-webkit-tap-highlight-color:transparent}
.duck svg{display:block;width:100%;height:auto;transform-origin:50% 80%}
.duck.q svg{animation:quack .35s cubic-bezier(.2,.7,.2,1)}
.duck.gold svg path:nth-of-type(1),.duck.gold svg circle:nth-of-type(1){fill:#FFE27A}
.duck.gold{filter:drop-shadow(0 0 14px rgba(246,161,14,.9))}
@keyframes quack{30%{transform:scale(1.18,.86)}60%{transform:scale(.92,1.1)}}
.pop{position:fixed;z-index:6;pointer-events:none;font:400 26px/1 Avigea,Georgia,serif;color:var(--orange);animation:pop .8s ease-out forwards}
@keyframes pop{to{transform:translateY(-50px);opacity:0}}
.feather{position:fixed;z-index:4;width:8px;height:8px;border-radius:50% 0;background:var(--orange);pointer-events:none;animation:fly .7s ease-out forwards}
@keyframes fly{to{transform:translate(var(--dx),var(--dy)) rotate(220deg);opacity:0}}
.time.low b{color:#ff5a3c}
@media (prefers-reduced-motion:reduce){.duck.q svg,.pop,.feather{animation:none}}
""".strip()
CSS = "".join(l.strip() for l in CSS.splitlines())

JS = r"""
(() => {
const $ = s => document.querySelector(s);
const layer = $('#layer'), menu = $('#menu'), scoreEl = $('#score'), timeEl = $('#time'), bestEl = $('#best');
const SVG = $('#duck-tpl').innerHTML;
const ROUND = 30, MAX = 22;
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
let ducks = [], raf = 0, last = 0, score = 0, left = ROUND, playing = false, tick = 0, spawnT = 0, ac = null;
let best = 0; try { best = +localStorage.getItem('3rd-duck-best') || 0; } catch (_) {}
bestEl.textContent = best;

function quack(pitch){
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    ac = ac || new AC(); ac.resume();
    const t = ac.currentTime;
    [0, .16].forEach((d, k) => {
      const o = ac.createOscillator(), f = ac.createBiquadFilter(), g = ac.createGain();
      o.type = 'sawtooth';
      o.frequency.setValueAtTime((k ? 620 : 700) * pitch, t + d);
      o.frequency.exponentialRampToValueAtTime((k ? 300 : 360) * pitch, t + d + .13);
      f.type = 'bandpass'; f.frequency.value = 1100; f.Q.value = 3;
      g.gain.setValueAtTime(.0001, t + d);
      g.gain.exponentialRampToValueAtTime(.22, t + d + .015);
      g.gain.exponentialRampToValueAtTime(.0001, t + d + .14);
      o.connect(f); f.connect(g); g.connect(ac.destination);
      o.start(t + d); o.stop(t + d + .16);
    });
  } catch (_) {}
}
function burst(x, y, txt){
  const p = document.createElement('div'); p.className = 'pop'; p.textContent = txt;
  p.style.left = x + 'px'; p.style.top = y + 'px'; document.body.append(p);
  setTimeout(() => p.remove(), 800);
  if (reduce) return;
  for (let i = 0; i < 8; i++) {
    const f = document.createElement('i'); f.className = 'feather';
    const a = Math.random() * Math.PI * 2, r = 40 + Math.random() * 50;
    f.style.left = x + 'px'; f.style.top = y + 'px';
    f.style.setProperty('--dx', Math.cos(a) * r + 'px'); f.style.setProperty('--dy', Math.sin(a) * r + 'px');
    document.body.append(f); setTimeout(() => f.remove(), 700);
  }
}
function spawn(x, y){
  if (ducks.length >= MAX) return;
  const gold = playing && Math.random() < .08;
  const el = document.createElement('button');
  el.type = 'button'; el.className = 'duck' + (gold ? ' gold' : '');
  el.setAttribute('aria-label', gold ? 'Golden duck' : 'Duck');
  el.innerHTML = SVG;
  const size = gold ? 60 : 64 + Math.random() * 56;
  const speed = 1 + (ROUND - left) / ROUND * .9;
  if (x == null) { x = Math.random() * (innerWidth - size); y = innerHeight + 10; }
  const d = { el, size, x, y, t: Math.random() * 6, gold,
    vx: (Math.random() < .5 ? -1 : 1) * (110 + Math.random() * 150) * speed,
    vy: -(200 + Math.random() * 260) * speed };
  el.style.width = size + 'px';
  el.addEventListener('pointerdown', ev => {
    ev.preventDefault();
    quack(gold ? 1.5 : .85 + Math.random() * .4);
    const r = el.getBoundingClientRect();
    if (playing) {
      const pts = gold ? 5 : 1;
      score += pts; scoreEl.textContent = score;
      burst(r.left + r.width / 2, r.top + r.height / 3, '+' + pts);
      remove(d);
      spawn(); if (Math.random() < .6) spawn();
    } else {
      d.vy = -Math.abs(d.vy) - 260; d.vx *= 1.12;
      el.classList.remove('q'); void el.offsetWidth; el.classList.add('q');
      spawn(d.x, d.y);
    }
  });
  layer.append(el); ducks.push(d); place(d);
}
function remove(d){ d.el.remove(); ducks = ducks.filter(x => x !== d); }
function place(d){
  const flip = d.vx < 0 ? 1 : -1, wob = reduce ? 0 : Math.sin(d.t) * 9;
  d.el.style.transform = `translate(${d.x.toFixed(1)}px,${d.y.toFixed(1)}px) scaleX(${flip}) rotate(${wob.toFixed(1)}deg)`;
}
function frame(now){
  const dt = Math.min(.05, last ? (now - last) / 1000 : .016); last = now;
  const W = innerWidth, H = innerHeight;
  for (const d of ducks) {
    const h = d.size * .85;
    d.vy += 140 * dt;
    d.x += d.vx * dt; d.y += d.vy * dt; d.t += dt * (6 + Math.abs(d.vx) / 40);
    if (d.x < 0) { d.x = 0; d.vx = Math.abs(d.vx); }
    if (d.x > W - d.size) { d.x = W - d.size; d.vx = -Math.abs(d.vx); }
    if (d.y < 64 && d.vy < 0) { d.y = 64; d.vy = Math.abs(d.vy); }
    if (d.y > H - h) { d.y = H - h; d.vy = -Math.max(200, Math.abs(d.vy) * .92); }
    place(d);
  }
  if (playing) {
    spawnT -= dt;
    if (spawnT <= 0) { spawn(); spawnT = Math.max(.35, 1.1 - (ROUND - left) * .025); }
  }
  raf = requestAnimationFrame(frame);
}
function clear(){ ducks.forEach(d => d.el.remove()); ducks = []; }
function start(){
  clear(); score = 0; left = ROUND; playing = true; spawnT = 0;
  scoreEl.textContent = 0; timeEl.textContent = left; timeEl.parentNode.classList.remove('low');
  menu.classList.add('hide');
  for (let i = 0; i < 3; i++) spawn();
  clearInterval(tick);
  tick = setInterval(() => {
    left--; timeEl.textContent = left;
    timeEl.parentNode.classList.toggle('low', left <= 5);
    if (left <= 0) end();
  }, 1000);
}
function end(){
  clearInterval(tick); playing = false; clear();
  const rec = score > best;
  if (rec) { best = score; bestEl.textContent = best; try { localStorage.setItem('3rd-duck-best', best); } catch (_) {} }
  $('#title').textContent = rec ? 'New record!' : 'Quack.';
  $('#msg').textContent = `You caught ${score} duck${score === 1 ? '' : 's'} in ${ROUND} seconds.` + (rec ? '' : ` Best: ${best}.`);
  $('#go').textContent = 'Play again';
  menu.classList.remove('hide');
  $('#go').focus();
  spawn(innerWidth / 2 - 50, innerHeight / 2 - 160);
}
$('#go').addEventListener('click', start);
spawn(innerWidth / 2 - 50, innerHeight / 2 - 170);
if (!reduce) raf = requestAnimationFrame(frame);
else { playing = false; }
})();
""".strip()


def page(font_ok=True):
    sh = lambda s: base64.b64encode(hashlib.sha256(s.encode()).digest()).decode()
    csp = (f"default-src 'none'; base-uri 'none'; form-action 'none'; img-src 'self'; font-src 'self'; "
           f"style-src 'sha256-{sh(CSS)}'; script-src 'sha256-{sh(JS)}'")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Quack · 3rd Records</title>
<meta name="robots" content="noindex,nofollow">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<meta name="theme-color" content="#1D1D1B">
<link rel="icon" href="/favicon.ico" sizes="32x32"><link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>{CSS}</style></head><body>
<template id="duck-tpl">{DUCK}</template>
<header class="hud"><a class="up" href="/">← 3rd Records</a>
<div class="stats up"><span>Score<b id="score">0</b></span><span class="time">Time<b id="time">30</b></span><span>Best<b id="best">0</b></span></div></header>
<div class="layer" id="layer"></div>
<main class="center" id="menu"><p class="up">3rd Records · secret level</p><h1 id="title">Quack.</h1>
<p id="msg">You found the duck. Catch as many as you can in 30 seconds. Golden ones are worth 5.</p>
<button class="btn" id="go" type="button">Play</button></main>
<script>{JS}</script>
</body></html>
"""


def build(DIST):
    out = DIST / "duck"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page(), encoding="utf-8")
