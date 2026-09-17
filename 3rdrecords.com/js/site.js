/* 3rdrecords.com — progressive enhancement only: every page works without this file. */
(() => {
  const d = document, root = d.documentElement, body = d.body;
  root.classList.add('js');
  const $ = (s, r = d) => r.querySelector(s);
  const $$ = (s, r = d) => [...r.querySelectorAll(s)];
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const fine = matchMedia('(pointer: fine)').matches;
  const typing = () => /INPUT|TEXTAREA|SELECT/.test((d.activeElement || {}).tagName || '');

  /* ---------- header state + scroll progress ---------- */
  const top = $('.top');
  let ticking = false;
  const onScroll = () => {
    ticking = false;
    if (top) top.classList.toggle('solid', scrollY > 24);
    const h = root.scrollHeight - innerHeight;
    root.style.setProperty('--sp', h > 0 ? Math.min(1, scrollY / h).toFixed(4) : '0');
  };
  addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  onScroll();

  /* ---------- mobile menu ---------- */
  const menu = $('.menu');
  if (menu) {
    const label = $('span', menu);
    const set = on => {
      body.classList.toggle('open', on);
      menu.setAttribute('aria-expanded', String(on));
      label.textContent = on ? 'Close' : 'Menu';
    };
    menu.addEventListener('click', () => set(!body.classList.contains('open')));
    $$('.nav a').forEach(a => a.addEventListener('click', () => set(false)));
    d.addEventListener('keydown', ev => {
      if (ev.key === 'Escape' && body.classList.contains('open')) { set(false); menu.focus(); }
    });
    matchMedia('(min-width: 52.01rem)').addEventListener('change', m => { if (m.matches) set(false); });
  }

  /* ---------- reveal on scroll ---------- */
  const revealables = $$('.reveal, .stagger, .words:not(.load)');
  if ('IntersectionObserver' in window && !reduce) {
    const io = new IntersectionObserver(entries => entries.forEach(en => {
      if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
    }), { rootMargin: '0px 0px -8% 0px' });
    revealables.forEach(el => io.observe(el));
  } else revealables.forEach(el => el.classList.add('in'));

  /* ---------- pointer effects: glow, tilt, magnetic buttons ---------- */
  if (fine && !reduce) {
    const glow = $('.glow');
    let mx = 0, my = 0, raf = 0;
    addEventListener('pointermove', ev => {
      mx = ev.clientX; my = ev.clientY;
      body.classList.add('moved');
      if (!raf) raf = requestAnimationFrame(() => {
        raf = 0;
        if (glow) { glow.style.setProperty('--cx', mx + 'px'); glow.style.setProperty('--cy', my + 'px'); }
      });
    }, { passive: true });
    root.addEventListener('mouseleave', () => body.classList.remove('moved'));

    $$('.tilt').forEach(el => {
      el.addEventListener('pointermove', ev => {
        const r = el.getBoundingClientRect();
        const x = (ev.clientX - r.left) / r.width, y = (ev.clientY - r.top) / r.height;
        el.style.setProperty('--x', (x * 100).toFixed(1) + '%');
        el.style.setProperty('--y', (y * 100).toFixed(1) + '%');
        el.style.setProperty('--rx', ((x - .5) * 9).toFixed(2) + 'deg');
        el.style.setProperty('--ry', ((.5 - y) * 9).toFixed(2) + 'deg');
      });
      el.addEventListener('pointerleave', () => {
        el.style.setProperty('--rx', '0deg');
        el.style.setProperty('--ry', '0deg');
      });
    });

    $$('.magnet').forEach(el => {
      el.addEventListener('pointermove', ev => {
        const r = el.getBoundingClientRect();
        el.style.setProperty('--mx', ((ev.clientX - r.left - r.width / 2) * .25).toFixed(1) + 'px');
        el.style.setProperty('--my', ((ev.clientY - r.top - r.height / 2) * .35).toFixed(1) + 'px');
      });
      el.addEventListener('pointerleave', () => { el.style.setProperty('--mx', '0px'); el.style.setProperty('--my', '0px'); });
    });
  }

  /* ---------- hero: scratchable vinyl + equalizer ---------- */
  const disc = $('.disc'), eq = $('.eq');
  let speed = 1;
  const watch = (el, cb) => {
    if (!('IntersectionObserver' in window)) return cb(true);
    new IntersectionObserver(es => cb(es[0].isIntersecting)).observe(el);
  };
  if (disc && !reduce) {
    const BASE = 72; // degrees per second, same as the CSS spin
    let angle = 0, vel = BASE, last = 0, drag = null, on = true, running = false;
    disc.classList.add('driven');
    const frame = now => {
      if (!on) { running = false; last = 0; return; }
      const dt = Math.min(.05, last ? (now - last) / 1000 : 0);
      last = now;
      if (drag) { if (now - drag.t > 90) vel *= .85; }
      else { vel += (BASE - vel) * Math.min(1, dt * 1.6); angle += vel * dt; }
      disc.style.transform = `rotate(${(angle % 360).toFixed(2)}deg)`;
      speed = vel / BASE;
      requestAnimationFrame(frame);
    };
    const start = () => { if (!running) { running = true; requestAnimationFrame(frame); } };
    watch(disc, v => { on = v; if (v) start(); });
    start();
    const angleOf = ev => {
      const r = disc.getBoundingClientRect();
      return Math.atan2(ev.clientY - (r.top + r.height / 2), ev.clientX - (r.left + r.width / 2)) * 180 / Math.PI;
    };
    disc.addEventListener('pointerdown', ev => {
      drag = { a: angleOf(ev), t: performance.now() };
      disc.setPointerCapture(ev.pointerId);
      disc.classList.add('grab');
    });
    disc.addEventListener('pointermove', ev => {
      if (!drag) return;
      const a = angleOf(ev), now = performance.now();
      let da = a - drag.a;
      if (da > 180) da -= 360;
      if (da < -180) da += 360;
      angle += da;
      vel = vel * .4 + (da / (Math.max(8, now - drag.t) / 1000)) * .6;
      drag.a = a; drag.t = now;
    });
    const release = () => { drag = null; disc.classList.remove('grab'); };
    disc.addEventListener('pointerup', release);
    disc.addEventListener('pointercancel', release);
    disc.addEventListener('lostpointercapture', release);
  }
  if (eq && eq.getContext && !reduce) {
    const ctx = eq.getContext('2d');
    const N = 72;
    let on = true, running = false, t = 0, amp = .35;
    const size = () => { eq.width = Math.round(eq.clientWidth * devicePixelRatio); eq.height = Math.round(eq.clientHeight * devicePixelRatio); };
    size();
    addEventListener('resize', size);
    const loop = () => {
      if (!on) { running = false; return; }
      const s = Math.abs(speed);
      t += .016 * Math.max(.25, Math.min(4, s));
      amp += (Math.min(1.25, .35 + Math.abs(speed - 1) * .45) - amp) * .08;
      const W = eq.width, H = eq.height, bw = W / N;
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = speed < 0 ? 'rgba(254,254,254,.55)' : 'rgba(246,161,14,.7)';
      for (let i = 0; i < N; i++) {
        const x = i / N;
        const v = Math.abs(Math.sin(x * 9 + t * 2.1) * .5 + Math.sin(x * 23 - t * 3.3) * .3 + Math.sin(x * 51 + t * 5.2) * .2);
        const h = Math.max(2 * devicePixelRatio, v * amp * H * (1 - Math.abs(x - .5) * .8));
        ctx.fillRect(i * bw + bw * .25, H - h, bw * .5, h);
      }
      requestAnimationFrame(loop);
    };
    const start = () => { if (!running) { running = true; requestAnimationFrame(loop); } };
    watch(eq, v => { on = v; if (v) start(); });
    start();
  }

  /* ---------- featured slider ---------- */
  $$('.slider').forEach(sl => {
    const track = $('.track', sl), slides = $$('.slide', sl), n = slides.length;
    const scope = sl.closest('section') || sl;
    const bars = $$('.bars button', scope), shots = $$('.backdrop img', scope), count = $('.count', scope);
    const pad = k => String(k).padStart(2, '0');
    let i = 0, timer = 0;
    const show = k => {
      i = k;
      bars.forEach((b, j) => { b.setAttribute('aria-current', String(j === i)); b.classList.toggle('done', j < i); });
      shots.forEach((s, j) => s.classList.toggle('on', j === i));
      slides.forEach((s, j) => s.classList.toggle('cur', j === i));
      if (count) count.innerHTML = `<b>${pad(i + 1)}</b> / ${pad(n)}`;
    };
    const go = k => {
      k = (k + n) % n;
      track.scrollTo({ left: k * track.clientWidth, behavior: reduce ? 'auto' : 'smooth' });
      show(k);
    };
    track.addEventListener('scroll', () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const k = Math.round(track.scrollLeft / Math.max(1, track.clientWidth));
        if (k !== i && k >= 0 && k < n) show(k);
      }, 90);
    }, { passive: true });
    $$('[data-prev]', scope).forEach(b => b.addEventListener('click', () => go(i - 1)));
    $$('[data-next]', scope).forEach(b => b.addEventListener('click', () => go(i + 1)));
    bars.forEach((b, j) => b.addEventListener('click', () => go(j)));
    d.addEventListener('keydown', ev => {
      if (ev.altKey || ev.ctrlKey || ev.metaKey || typing() || body.classList.contains('open')) return;
      if (ev.key !== 'ArrowLeft' && ev.key !== 'ArrowRight') return;
      const r = sl.getBoundingClientRect();
      if (r.bottom < innerHeight * .15 || r.top > innerHeight * .85) return;
      ev.preventDefault();
      go(i + (ev.key === 'ArrowRight' ? 1 : -1));
    });
    addEventListener('resize', () => track.scrollTo({ left: i * track.clientWidth }));
    show(0);
  });

  /* ---------- catalog filter ---------- */
  const chips = $('.chips');
  if (chips) {
    chips.hidden = false;
    const items = $$('[data-artists]'), out = $('output', chips);
    const apply = v => {
      $$('.chip', chips).forEach(c => c.setAttribute('aria-pressed', String(c.dataset.f === v)));
      let k = 0;
      items.forEach(li => {
        const on = v === '*' || li.dataset.artists.split('|').includes(v);
        const was = !li.hidden;
        li.hidden = !on;
        if (on) {
          if (!was && !reduce && li.animate) li.animate([{ opacity: 0, transform: 'translateY(14px)' }, { opacity: 1, transform: 'none' }], { duration: 500, delay: k * 60, easing: 'cubic-bezier(.2,.7,.2,1)', fill: 'backwards' });
          k++;
        }
      });
      if (out) out.textContent = `${k} release${k === 1 ? '' : 's'}`;
    };
    chips.addEventListener('click', ev => { const c = ev.target.closest('.chip'); if (c) apply(c.dataset.f); });
  }

  /* ---------- Spotify players (loaded only on click) ---------- */
  const frame = (src, title) => {
    const f = d.createElement('iframe');
    f.src = src;
    f.title = title;
    f.allow = 'autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture';
    f.loading = 'lazy';
    return f;
  };
  const dock = $('#dock');
  d.addEventListener('click', ev => {
    const emb = ev.target.closest('[data-embed]');
    if (emb) { emb.replaceWith(frame(emb.dataset.embed, emb.dataset.title)); return; }
    const pd = ev.target.closest('[data-dock]');
    if (pd && dock) {
      if (dock.hidden) {
        $('.dock-f', dock).replaceChildren(frame(pd.dataset.dock, pd.dataset.title));
        dock.hidden = false;
        pd.setAttribute('aria-expanded', 'true');
      } else {
        dock.hidden = true;
        $('.dock-f', dock).replaceChildren();
        pd.setAttribute('aria-expanded', 'false');
      }
      return;
    }
    if (ev.target.closest('[data-undock]') && dock) {
      dock.hidden = true;
      $('.dock-f', dock).replaceChildren();
      const b = $('[data-dock]');
      if (b) { b.setAttribute('aria-expanded', 'false'); b.focus(); }
      return;
    }
    const cp = ev.target.closest('[data-copy]');
    if (cp) {
      const txt = cp.dataset.copy, lab = $('span', cp) || cp, old = lab.textContent;
      const done = msg => { lab.textContent = msg; setTimeout(() => { lab.textContent = old; }, 1800); };
      if (navigator.clipboard) navigator.clipboard.writeText(txt).then(() => done('Copied'), () => done('Select to copy'));
      else done('Select to copy');
      return;
    }
    if (ev.target.closest('[data-totop]')) {
      scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
      const skip = $('.skip'); if (skip) skip.focus({ preventScroll: true });
    }
  });

  /* ---------- release pages: arrow keys move between releases ---------- */
  const pager = $('.pager');
  if (pager && !$('.slider')) {
    d.addEventListener('keydown', ev => {
      if (ev.altKey || ev.ctrlKey || ev.metaKey || ev.shiftKey || typing() || body.classList.contains('open')) return;
      const a = ev.key === 'ArrowLeft' ? $('a[rel=prev]', pager) : ev.key === 'ArrowRight' ? $('a[rel=next]', pager) : null;
      if (a) location.href = a.href;
    });
  }
})();
