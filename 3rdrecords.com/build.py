#!/usr/bin/env python3
"""Build 3rdrecords.com into ./dist from site.json.

Pages: home, /catalog/, /releases/<slug>/, /artists/, /artists/<slug>/, /news/, /contact/.
New release: add it at the top of "releases" in site.json (links, date, cover URLs).
Logos live in assets/*.svg (vector traces of the official 3rd Records marks).
js/site.js adds the interactions (menu, reveal, slider, filters, Spotify players); every page works without it.
Push to main and GitHub Actions rebuilds and redeploys.
Requires Python 3.9+, Pillow and CairoSVG (pip install pillow cairosvg).
"""
import base64, datetime as dt, hashlib, html, io, json, pathlib, re, shutil

ROOT = pathlib.Path(__file__).parent
DIST = ROOT / "dist"
S = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
L, RELEASES, ARTISTS, D = S["label"], S["releases"], S["artists"], S["domain"].rstrip("/")
NEWS = sorted(S.get("news", []), key=lambda n: n["date"], reverse=True)
R = RELEASES[0]
e = lambda s: html.escape(s, quote=True)
TODAY = dt.date.today().isoformat()
IMG_URLS = [u for rel in RELEASES for kind in ("jpg", "webp") for u in rel["image"].get(kind, {}).values()]
ORIGINS = sorted({re.match(r"https://[^/]+", u).group(0) for u in IMG_URLS + [a["image"] for a in ARTISTS] if u.startswith("https://")})




def artist_of(rel):
    return next((a for a in ARTISTS if a["name"] == rel["artist"]), None)


def fmt_date(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


def picture(rel, cls, sizes, w=640):
    im = rel["image"]
    src = "".join([f'<source type="image/webp" srcset="{im["webp"]["640"]} 640w, {im["webp"]["1200"]} 1200w" sizes="{sizes}">'] if im.get("webp") else [])
    return (f'<picture>{src}<img class="{cls}" src="{im["jpg"]["640"]}" srcset="{im["jpg"]["640"]} 640w, {im["jpg"]["1200"]} 1200w" '
            f'sizes="{sizes}" width="{w}" height="{w}" alt="{e(im["alt"])}" loading="lazy" decoding="async"></picture>')

C = {"choco": "#512321", "orange": "#F6A10E", "ink": "#1D1D1B", "white": "#FEFEFE", "grey": "#9E9E9E"}

CB = L.get("createdBy")
GENRES = L.get("genres", [])
GENRE_TXT = (", ".join(g.lower() for g in GENRES[:-1]) + " and " + GENRES[-1].lower()) if len(GENRES) > 1 else "".join(GENRES).lower()
NAMES = ", ".join(a["name"] for a in ARTISTS[:-1]) + " and " + ARTISTS[-1]["name"]
TITLE = f"{L['name']} | Independent Record Label"
DESC = (f"{L['name']} is an independent {GENRE_TXT} record label created by {CB['name']}. Artists featured on its releases: {NAMES}. "
        f"Latest release: “{R['title']}” by {R['artist']}".rstrip(".") + ".")
ROSTER_TXT = f"Artists who have taken part in its releases include {NAMES}, and the catalog counts {len(RELEASES)} releases so far."
POOL_TXT = f"Not an exclusive roster: these are the artists who have taken part in {L['name']} projects."


def rel_url(rel):
    return f"/releases/{rel['slug']}/"


def rel_artists(rel):
    """Artists of a release that are on the roster (matched by name inside the credit)."""
    credit = rel["artist"].lower()
    return [a for a in ARTISTS if re.search(r"(^|[ ,&])" + re.escape(a["name"].lower()) + r"($|[ ,&])", credit)]


def svg_path(name):
    s = (ROOT / "assets" / f"{name}.svg").read_text()
    vb = re.search(r'viewBox="([^"]+)"', s).group(1)
    tr = re.search(r'transform="([^"]+)"', s).group(1)
    d = re.search(r' d="([^"]+)"', s).group(1)
    d = re.sub(r"\s+", " ", d)
    return vb, tr, d


MARK, RECORDS, CMARK = svg_path("mark"), svg_path("records"), svg_path("circle-mark")


def lockup(cls, mark_fill, word_fill, label=None, link=None):
    """3RD mark + 'records' wordmark side by side (viewBox 3344x1028). link: hidden easter-egg href on the duck."""
    a = f' role="img" aria-label="{e(label)}"' if label else ' aria-hidden="true"'
    return (f'<svg class="{cls}" viewBox="0 0 3344 1028" xmlns="http://www.w3.org/2000/svg"{a} focusable="false">'
            + (f'<a href="{link}" tabindex="-1" class="egg">' if link else '')
            + f'<g class="duck"><path fill="{mark_fill}" transform="{MARK[1]}" d="{MARK[2]}"/></g>'
            + ('</a>' if link else '')
            + f'<g transform="translate(1660 0)"><path fill="{word_fill}" transform="{RECORDS[1]}" d="{RECORDS[2]}"/></g></svg>')


def circle(fill, mark="#FEFEFE", size=None, ref=False):
    """Round 3RD logo. ref=True reuses the <symbol id="cm"> defined once in the page."""
    wh = f' width="{size}" height="{size}"' if size else ""
    inner = (f'<use href="#cm" fill="{mark}"/>' if ref else
             f'<path fill="{mark}" transform="{CMARK[1]}" d="{CMARK[2]}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2800 2800"{wh}>'
            f'<circle cx="1400" cy="1400" r="1400" fill="{fill}"/>{inner}</svg>')


CENTER = ' class="c"'
LONG = ' class="long"'
JS_VER = hashlib.sha256((ROOT / "js" / "site.js").read_bytes()).hexdigest()[:8]
WORKLET_VER = hashlib.sha256((ROOT / "js" / "scratch.js").read_bytes()).hexdigest()[:8]
CB_ARTIST = next((a for a in ARTISTS if CB and a["name"] == CB["name"]), ARTISTS[-1])


ICONS = {
    "right": '<path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M5 12h14m-6-6 6 6-6 6"/>',
    "left": '<path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M19 12H5m6-6-6 6 6 6"/>',
    "out": '<path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M8 16 16 8m-7 0h7v7"/>',
    "up": '<path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M12 19V5m-6 6 6-6 6 6"/>',
    "play": '<path fill="currentColor" d="M8 5.5v13a1 1 0 0 0 1.5.86l10.5-6.5a1 1 0 0 0 0-1.72L9.5 4.64A1 1 0 0 0 8 5.5z"/>',
    "x": '<path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" d="m6 6 12 12M18 6 6 18"/>',
}
SYMBOLS = ('<svg class="sr" aria-hidden="true" focusable="false"><symbol id="cm" viewBox="0 0 2800 2800">'
           f'<path transform="{CMARK[1]}" d="{CMARK[2]}"/></symbol>'
           + "".join(f'<symbol id="i-{k}" viewBox="0 0 24 24">{v}</symbol>' for k, v in ICONS.items())
           + '</svg>')


def icon(name):
    return f'<svg class="ico" aria-hidden="true" focusable="false"><use href="#i-{name}"/></svg>'


def fit_cls(text):
    """Keep short titles on one line: size class picked from the title length."""
    n = len(text)
    return " t8" if n <= 8 else " t10" if n <= 10 else " t12" if n <= 12 else ""


def words(text):
    """Split a heading into word masks for the rise-in animation (text stays plain for crawlers and screen readers)."""
    parts = text.split(" ")
    return " ".join(f'<span class="w"><span>{e(p)}</span></span>' for p in parts)


CSS = """
@font-face{font-family:Avigea;src:url(/fonts/avigea.woff2) format("woff2");font-display:swap}
@font-face{font-family:Roboto;src:url(/fonts/roboto-regular.woff2) format("woff2");font-weight:400;font-display:swap}
@font-face{font-family:Roboto;src:url(/fonts/roboto-medium.woff2) format("woff2");font-weight:500;font-display:swap}
@view-transition{navigation:auto}
:root{--choco:#512321;--orange:#F6A10E;--ink:#1D1D1B;--deep:#151514;--white:#FEFEFE;--soft:#e9e6e1;--grey:#9E9E9E;--line:rgba(254,254,254,.14);--d:Avigea,"Cooper Black",Georgia,serif;--pad:clamp(1rem,4vw,2.5rem);--ease:cubic-bezier(.2,.7,.2,1);color-scheme:dark}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%;scroll-behavior:smooth;scroll-padding-top:5rem}
body{margin:0;background:var(--ink);color:var(--white);font:400 1rem/1.6 Roboto,"Helvetica Neue",Arial,system-ui,sans-serif;-webkit-font-smoothing:antialiased;padding-bottom:3.5rem;overflow-x:clip}
::selection{background:var(--orange);color:var(--ink)}
a{color:inherit}
:focus-visible{outline:2px solid var(--orange);outline-offset:4px}
img,svg,video,canvas{display:block;max-width:100%}
img,svg{height:auto}
button{font:inherit;color:inherit;background:none;border:0;padding:0;cursor:pointer}
h1,h2,h3{margin:0;font-family:var(--d);font-weight:400;line-height:.95;letter-spacing:-.01em}
ul,ol{list-style:none;margin:0;padding:0}
[hidden]{display:none!important}
.up{font-size:.6875rem;font-weight:500;letter-spacing:.24em;text-transform:uppercase}
.or{color:var(--orange)}
.mute{color:var(--grey)}
.sr{position:absolute;width:1px;height:1px;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.ico{display:inline-block;width:1.15em;height:1.15em;flex:none;vertical-align:-.2em}
.skip{position:absolute;left:var(--pad);top:-4rem;z-index:30;background:var(--orange);color:var(--ink);padding:.6rem 1rem}
.skip:focus{top:1rem}
.progress{position:fixed;inset:0 0 auto;z-index:25;height:2px;background:var(--orange);transform-origin:0 50%;transform:scaleX(var(--sp,0));pointer-events:none}
.glow{position:fixed;left:0;top:0;z-index:0;width:46rem;height:46rem;margin:-23rem 0 0 -23rem;border-radius:50%;background:radial-gradient(circle,rgba(246,161,14,.09),rgba(246,161,14,0) 62%);pointer-events:none;opacity:0;transform:translate(var(--cx,-60rem),var(--cy,-60rem));transition:opacity .5s}
.moved .glow{opacity:1}
main,.foot{position:relative;z-index:1}
.top{position:fixed;inset:0 0 auto;z-index:20;display:flex;align-items:center;justify-content:space-between;gap:1rem;height:4.5rem;padding:0 var(--pad);border-bottom:1px solid transparent;transition:height .35s var(--ease),background-color .35s,border-color .35s}
.top.solid{height:3.75rem;background:rgba(21,21,20,.84);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);border-color:var(--line)}
.brand{display:flex;align-items:center;gap:.75rem;text-decoration:none;flex:none}
.brand svg{width:2.5rem;transition:transform .8s var(--ease)}
.brand:hover svg{transform:rotate(-360deg)}
.nav{display:flex;align-items:center;gap:.15rem}
.nav a{padding:.55rem .85rem;border-radius:999px;text-decoration:none;white-space:nowrap;transition:color .2s,background-color .2s}
.nav a:hover{color:var(--orange)}
.nav a[aria-current]{background:var(--white);color:var(--ink)}
.nav i{font-style:normal;color:var(--orange);margin-right:.45em}
.nav a[aria-current] i{color:var(--choco)}
.menu{display:none}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:.7em;min-height:2.875rem;padding:0 1.4rem;border:1px solid currentColor;border-radius:999px;text-decoration:none;white-space:nowrap;transition:background-color .25s,color .25s,border-color .25s}
.btn:hover{background:var(--orange);border-color:var(--orange);color:var(--ink)}
.btn.fill{background:var(--orange);border-color:var(--orange);color:var(--ink)}
.btn.fill:hover{background:var(--white);border-color:var(--white)}
.btn .ico{transition:transform .3s var(--ease)}
.btn:hover .ico{transform:translateX(.2em)}
.magnet{transform:translate(var(--mx,0),var(--my,0));transition:transform .35s var(--ease),background-color .25s,color .25s,border-color .25s}
.round{display:inline-grid;place-items:center;width:3rem;height:3rem;border-radius:50%;border:1px solid var(--line)}
.round:hover{background:var(--orange);border-color:var(--orange);color:var(--ink)}
.hero{position:relative;min-height:calc(100vh - 3.5rem);min-height:calc(100svh - 3.5rem);display:flex;flex-direction:column;overflow:hidden;isolation:isolate}
.hero::before{content:"";position:absolute;z-index:-1;width:70vmax;aspect-ratio:1;left:50%;top:42%;border-radius:50%;background:radial-gradient(circle,rgba(246,161,14,.22),rgba(246,161,14,0) 62%);transform:translate(-50%,-50%);animation:glow 7s ease-in-out infinite alternate}
.hero-in{flex:1;align-content:center;padding:6rem var(--pad) 1.5rem;display:grid;gap:clamp(1.5rem,4vh,2.5rem);justify-items:center;text-align:center;width:100%;max-width:84rem;margin:0 auto}
.stage{position:relative;width:min(72vw,26rem);aspect-ratio:1}
.disc{position:absolute;inset:0;border-radius:50%;background:radial-gradient(circle,#0c0c0b 0 31%,transparent 31.2%),repeating-radial-gradient(circle,#131312 0 1.5px,#262624 1.6px 3.2px);box-shadow:0 1.5rem 4rem rgba(0,0,0,.55),inset 0 0 0 .35rem #0c0c0b;animation:spin 5s linear infinite;touch-action:pan-y;cursor:grab}
.disc.grab{cursor:grabbing}
.js .disc.driven{animation:none}
.disc svg{position:absolute;inset:32%;width:36%}
.disc::after{content:"";position:absolute;left:50%;top:50%;width:2.2%;aspect-ratio:1;border-radius:50%;background:var(--ink);transform:translate(-50%,-50%)}
.sheen{position:absolute;inset:0;border-radius:50%;background:conic-gradient(from 30deg,transparent 0 8%,rgba(255,255,255,.09) 12%,transparent 18% 58%,rgba(255,255,255,.07) 62%,transparent 68%);pointer-events:none}
.arm{position:absolute;right:-6%;top:-4%;width:34%;height:62%;transform-origin:85% 8%;transform:rotate(22deg);animation:arm 5s ease-in-out infinite alternate;pointer-events:none}
.arm::before{content:"";position:absolute;right:10%;top:0;width:1.1rem;aspect-ratio:1;border-radius:50%;background:var(--grey);box-shadow:0 0 0 .35rem #3a3a38}
.arm::after{content:"";position:absolute;right:calc(10% + .45rem);top:.55rem;width:.22rem;height:92%;background:linear-gradient(var(--grey),#cfcfcf);border-radius:.2rem;box-shadow:-.15rem 0 0 rgba(0,0,0,.25)}
.hint{position:absolute;left:50%;bottom:-1.75rem;transform:translateX(-50%);color:var(--grey);white-space:nowrap;opacity:0;transition:opacity .4s}
.js .stage:hover .hint{opacity:1}
.hero h1{width:min(100%,46rem)}
.lockup{width:100%;overflow:visible}
.duck{transform-box:fill-box;transform-origin:50% 90%;animation:bob 2.4s ease-in-out infinite}
.egg{cursor:pointer}.egg:hover .duck{animation-duration:.5s}
.rise{animation:rise .9s var(--ease) both}
.rise.d2{animation-delay:.12s}.rise.d3{animation-delay:.24s}.rise.d4{animation-delay:.36s}
.tag{margin:0;display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:.5rem;color:var(--grey)}
.lm{width:1.5rem;height:1.5rem;animation:spin 12s linear infinite}
.cta{margin:0;display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:.75rem 1.25rem}
.eq{width:100%;height:4.5rem;opacity:.6}
.ticker{overflow:hidden;border-block:1px solid rgba(254,254,254,.07);padding:.55rem 0;white-space:nowrap;background:var(--ink);opacity:.55;transition:opacity .4s}
.ticker:hover{opacity:.9}
.ticker div{display:inline-flex;animation:tick 60s linear infinite}
.ticker:hover div{animation-play-state:paused}
.ticker span{font:500 .6875rem/1 Roboto,sans-serif;letter-spacing:.28em;text-transform:uppercase;color:var(--grey);padding-right:2rem;display:inline-flex;align-items:center;gap:2rem}
.ticker span::after{content:"";width:.35rem;aspect-ratio:1;border-radius:50%;background:var(--orange);opacity:.7}
.ticker b{font-weight:500;color:var(--soft)}
.sec{max-width:84rem;margin:0 auto;padding:clamp(5rem,12vw,9rem) var(--pad) 0}
.page{padding-top:clamp(7rem,14vw,10rem)}
.head{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:1.5rem 3rem;margin-bottom:clamp(2rem,5vw,3.5rem)}
.head h1,.head h2{font-size:clamp(3.25rem,10vw,7.5rem)}
.head p:not(.kick){margin:0;max-width:30em;color:var(--soft)}
.kick{display:flex;align-items:center;gap:.7rem;margin:0 0 1.1rem;color:var(--orange)}
.kick::before{content:"";width:1.75rem;height:1px;background:currentColor}
.lead{margin:1.5rem 0 0;max-width:36em;font-size:clamp(1.125rem,2.1vw,1.375rem);color:var(--soft)}
.w{display:inline-block;overflow:hidden;vertical-align:top;padding:0 .04em .12em;margin:0 -.04em -.12em}
.w>span{display:inline-block}
.load .w>span{animation:wup 1s var(--ease) both}
.load .w:nth-child(2)>span{animation-delay:.07s}.load .w:nth-child(3)>span{animation-delay:.14s}.load .w:nth-child(4)>span{animation-delay:.21s}.load .w:nth-child(5)>span{animation-delay:.28s}
.crumbs{display:flex;flex-wrap:wrap;gap:.5rem;margin:0 0 1.5rem;color:var(--grey)}
.crumbs a{text-decoration:none}.crumbs a:hover{color:var(--orange)}
.crumbs li+li::before{content:"/";margin-right:.5rem}
.release{display:grid;gap:clamp(2rem,5vw,4.5rem)}
.relinfo{container-type:inline-size;min-width:0}
.title.t8,.title.t10,.title.t12{white-space:nowrap}
.title.t8{font-size:min(clamp(3.5rem,11vw,8rem),23cqi)}
.title.t10{font-size:min(clamp(3.5rem,11vw,8rem),19cqi)}
.title.t12{font-size:min(clamp(3.5rem,11vw,8rem),18.5cqi)}
.sleeve{position:relative;margin-right:30%}
.sleeve picture{position:relative;z-index:1;display:block;box-shadow:0 1.5rem 3rem rgba(0,0,0,.5)}
.cover{width:100%;aspect-ratio:1;background:var(--choco)}
.rec{position:absolute;inset:3%;border-radius:50%;background:radial-gradient(circle,#0c0c0b 0 31%,transparent 31.2%),repeating-radial-gradient(circle,#131312 0 1.5px,#262624 1.6px 3.2px);box-shadow:inset 0 0 0 1px #3a3a38,0 1rem 2rem rgba(0,0,0,.5);animation:slide 1.2s .3s var(--ease) both;transition:transform .8s var(--ease)}
.rec svg{position:absolute;inset:32%;width:36%}
.release:hover .rec{transform:translateX(46%) rotate(200deg)}
.title{font-size:clamp(3.5rem,11vw,8rem)}
.title a{text-decoration:none}
.by{margin:1rem 0 0;font:400 clamp(1.5rem,3.5vw,2.25rem)/1.1 var(--d)}
.by a{text-decoration-thickness:1px;text-underline-offset:.2em}
.by a:hover,.title a:hover{color:var(--orange)}
.meta{margin:1rem 0 2.25rem;color:var(--grey)}
.credit{margin:2.5rem 0 0;max-width:34em;color:var(--soft)}
.listen{border-top:1px solid var(--line)}
.listen a{position:relative;isolation:isolate;display:flex;justify-content:space-between;align-items:center;gap:1rem;min-height:4rem;padding:0 .25rem;border-bottom:1px solid var(--line);text-decoration:none;overflow:hidden;transition:padding .4s var(--ease),color .3s}
.listen a::before{content:"";position:absolute;inset:0;z-index:-1;background:var(--orange);transform:scaleY(0);transform-origin:50% 100%;transition:transform .4s var(--ease)}
.listen a:hover{color:var(--ink);padding:0 1rem}
.listen a:hover::before{transform:none}
.pf{font:400 clamp(1.5rem,3.4vw,2.125rem)/1 var(--d)}
.act{display:inline-flex;align-items:center;gap:.5em;color:var(--grey);white-space:nowrap;transition:color .3s}
.listen a:hover .act{color:var(--ink)}
.player{margin-top:1.75rem;border:1px solid var(--line);border-radius:12px;background:var(--deep);overflow:hidden}
.player button{display:flex;align-items:center;gap:1rem;width:100%;min-height:5rem;padding:.9rem 1.1rem;text-align:left}
.player iframe{display:block;width:100%;height:152px;border:0}
.pp{display:inline-grid;place-items:center;flex:none;width:3.25rem;height:3.25rem;border-radius:50%;background:var(--orange);color:var(--ink);transition:transform .3s var(--ease)}
.pp .ico{width:1.3rem;height:1.3rem;margin-left:.15rem}
.player button:hover .pp{transform:scale(1.08)}
.player b{display:block;font:400 1.35rem/1.1 var(--d)}
.player small{display:block;margin-top:.25rem;color:var(--grey)}
.art{position:relative;display:block;overflow:hidden;background:var(--choco);border-radius:6px;transform:perspective(900px) rotateX(var(--ry,0deg)) rotateY(var(--rx,0deg));transition:transform .6s var(--ease),box-shadow .6s var(--ease)}
.art::after{content:"";position:absolute;inset:0;z-index:2;background:radial-gradient(circle at var(--x,50%) var(--y,50%),rgba(255,255,255,.2),rgba(255,255,255,0) 45%);opacity:0;transition:opacity .4s;pointer-events:none}
.art img{width:100%;aspect-ratio:1;object-fit:cover;transition:transform 1s var(--ease)}
.card,.artist{display:block;text-decoration:none}
.card:hover .art,.artist:hover .art,.slide .art:hover{box-shadow:0 1.75rem 3.5rem rgba(0,0,0,.55)}
.card:hover .art::after,.artist:hover .art::after,.art:hover::after{opacity:1}
.card:hover img,.artist:hover img,.art:hover img{transform:scale(1.05)}
.go{position:absolute;right:.9rem;bottom:.9rem;z-index:3;display:grid;place-items:center;width:2.75rem;height:2.75rem;border-radius:50%;background:var(--orange);color:var(--ink);transform:scale(0) rotate(-45deg);transition:transform .45s var(--ease)}
.card:hover .go,.artist:hover .go,.card:focus-visible .go,.artist:focus-visible .go{transform:none}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,15rem),1fr));gap:2.75rem 1.5rem}
.card h2,.card h3{font-size:clamp(1.6rem,3vw,2.25rem);margin-top:1.1rem;transition:color .25s}
.card:hover h2,.card:hover h3{color:var(--orange)}
.card p{margin:.45rem 0 0;color:var(--grey)}
.chips{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem;margin:0 0 2.5rem}
.chip{height:2.5rem;padding:0 1.1rem;border:1px solid var(--line);border-radius:999px;transition:background-color .25s,color .25s,border-color .25s}
.chip:hover{border-color:var(--orange)}
.chip[aria-pressed=true]{background:var(--orange);border-color:var(--orange);color:var(--ink)}
.chips output{margin-left:auto;color:var(--grey)}
.roster{display:grid;gap:1.5rem;grid-template-columns:repeat(auto-fill,minmax(min(100%,18rem),1fr))}
.artist .art{border-radius:6px}
.artist img,.artist video{width:100%;aspect-ratio:4/5;object-fit:cover;object-position:50% 58%}
.artist img.c{object-position:50% 50%}
.artist video{position:absolute;inset:0;height:100%;transition:transform 1s var(--ease)}
.artist:hover video{transform:scale(1.05)}
.artist .info{position:absolute;z-index:3;inset:auto 0 0;padding:1.25rem 1.25rem 1.1rem;background:linear-gradient(to top,rgba(21,21,20,.94),rgba(21,21,20,0))}
.artist h2,.artist h3{font-size:clamp(2.5rem,6vw,3.75rem)}
.artist .art{container-type:inline-size}
.artist .long,.profile .long{white-space:nowrap}
.artist .long{font-size:min(clamp(2.5rem,6vw,3.75rem),15cqi)}
.profile>div:last-child{container-type:inline-size;min-width:0}
.profile h1.long{font-size:min(clamp(4rem,15vw,10.5rem),17cqi)}
.artist p{margin:.45rem 0 0;color:var(--orange)}
.artist .go{top:.9rem;bottom:auto}
.slider{position:relative}
.track{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;overscroll-behavior-x:contain}
.track::-webkit-scrollbar{display:none}
.slide{flex:0 0 100%;scroll-snap-align:start;display:grid;gap:clamp(1.5rem,4vw,4.5rem);align-items:center;padding:.5rem .25rem 1rem}
.slide .art{max-width:34rem;width:100%}
.slide h3{font-size:clamp(2.75rem,8vw,6rem)}
.slide h3 a{text-decoration:none}.slide h3 a:hover{color:var(--orange)}
.pills{display:flex;flex-wrap:wrap;gap:.5rem;margin:1.5rem 0 2rem}
.pills a{display:inline-flex;align-items:center;gap:.4em;height:2.25rem;padding:0 .95rem;border:1px solid var(--line);border-radius:999px;text-decoration:none;font-size:.875rem;transition:border-color .2s,color .2s}
.pills a:hover{border-color:var(--orange);color:var(--orange)}
.ctrl{display:flex;align-items:center;gap:.75rem}
.count{min-width:4.5rem;text-align:center;color:var(--grey)}
.count b{color:var(--white);font-weight:500}
.bars{display:flex;gap:.4rem;margin:1.5rem 0 2.5rem}
.bars button{flex:1;height:1.25rem;position:relative}
.bars button::before{content:"";position:absolute;left:0;right:0;top:50%;height:2px;background:var(--line);transition:background-color .3s}
.bars button.done::before{background:rgba(246,161,14,.4)}
.bars button[aria-current=true]::before{background:var(--orange)}
.backdrop{position:absolute;inset:clamp(2rem,6vw,4rem) 0 -2rem;z-index:-1;pointer-events:none;-webkit-mask-image:radial-gradient(closest-side,#000 25%,transparent);mask-image:radial-gradient(closest-side,#000 25%,transparent)}
.backdrop img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:blur(90px) saturate(1.2);opacity:0;transition:opacity 1s}
.backdrop img.on{opacity:.18}
.feat{position:relative;isolation:isolate}
.news{border-top:1px solid var(--line)}
.news li{border-bottom:1px solid var(--line)}
.news a{display:grid;gap:.55rem;padding:1.75rem 0;text-decoration:none;transition:padding .4s var(--ease)}
.news a:hover{padding-left:1rem}
.news h2,.news h3{font-size:clamp(1.5rem,3.2vw,2.5rem);line-height:1.05;transition:color .2s}
.news a:hover h2,.news a:hover h3{color:var(--orange)}
.news p{margin:0;max-width:44em;color:var(--soft)}
.news .up{color:var(--grey)}
.news .up.or{color:var(--orange);display:flex;align-items:center;gap:.5em}
.more{margin:2.5rem 0 0;display:flex;flex-wrap:wrap;gap:1rem}
.about{display:grid;gap:2rem;align-items:center}
.about p:not(.kick){margin:0;max-width:30em;font-size:clamp(1.25rem,2.4vw,1.75rem);line-height:1.45;color:var(--soft)}
.seal{width:min(15rem,42vw)}
.seal svg{transform:rotate(calc(var(--sp,0) * 540deg))}
.profile{display:grid;gap:clamp(2rem,5vw,5rem);align-items:end}
.portrait img,.portrait video{width:100%;aspect-ratio:4/5;object-fit:cover}
.portrait video{position:absolute;inset:0;height:100%}
.profile h1{font-size:clamp(4rem,15vw,10.5rem)}
.role{margin:1.25rem 0 .5rem;font:400 clamp(1.35rem,2.8vw,2rem)/1.25 var(--d);color:var(--soft)}
.profile .meta{margin-bottom:2rem}
.pager{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.pager a{display:grid;gap:.5rem;padding:2rem 0;text-decoration:none}
.pager a+a{text-align:right;justify-items:end;border-left:1px solid var(--line);padding-left:1rem}
.pager a:first-child{padding-right:1rem}
.pager b{font:400 clamp(1.5rem,4.5vw,3.25rem)/1 var(--d);transition:color .2s}
.pager span{display:inline-flex;align-items:center;gap:.5em;color:var(--grey)}
.pager a:hover b{color:var(--orange)}
.mailbox{display:flex;flex-wrap:wrap;align-items:center;gap:1rem 2rem;margin-top:clamp(2.5rem,6vw,4rem)}
.big-mail{font:400 clamp(2rem,7.5vw,6rem)/1.05 var(--d);text-decoration:none;overflow-wrap:anywhere;background:linear-gradient(var(--orange),var(--orange)) 0 100%/0 3px no-repeat;padding-bottom:.08em;transition:background-size .6s var(--ease),color .25s}
.big-mail:hover{background-size:100% 3px;color:var(--orange)}
.links-big{display:flex;flex-wrap:wrap;gap:.25rem 2rem}
.links-big a{display:inline-flex;align-items:center;gap:.3em;font:400 clamp(1.75rem,4.5vw,3rem)/1.3 var(--d);text-decoration:none;transition:color .2s}
.links-big a:hover{color:var(--orange)}
.links-big .ico{width:.6em;height:.6em}
.foot{max-width:84rem;margin:clamp(6rem,14vw,10rem) auto 0;padding:0 var(--pad) 2rem}
.foot-cta{display:grid;gap:1.25rem;padding:clamp(2.5rem,6vw,4rem) 0;border-top:1px solid var(--line)}
.foot-cta h2{font-size:clamp(3.25rem,11vw,8rem)}
.foot-cta .mailbox{margin-top:.5rem}
.foot-cta .big-mail{font-size:clamp(1.6rem,4.5vw,3.25rem)}
.foot-grid{display:grid;gap:2rem 1.5rem;grid-template-columns:repeat(auto-fit,minmax(10rem,1fr));padding:2.5rem 0;border-top:1px solid var(--line)}
.fh{margin:0 0 1rem;color:var(--grey)}
.foot-grid li a{display:inline-block;padding:.2rem 0;text-decoration:none;transition:color .2s}
.foot-grid li a:hover{color:var(--orange)}
.legal{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:1rem;padding-top:1.5rem;border-top:1px solid var(--line);color:var(--grey)}
.legal button{display:inline-flex;align-items:center;gap:.5em;color:var(--white)}
.legal button:hover{color:var(--orange)}
.bar{position:fixed;inset:auto 0 0;z-index:15;display:flex;align-items:center;gap:.9rem;min-height:3.5rem;padding:0 var(--pad);background:rgba(21,21,20,.92);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);border-top:1px solid var(--line)}
.bar .pp{width:2.25rem;height:2.25rem}
.bar .pp .ico{width:.95rem;height:.95rem}
.bar .pp:hover{transform:scale(1.1)}
.bar b{font-weight:500;display:flex;align-items:center;gap:.6rem;white-space:nowrap}
.bar b::before{content:"";width:.5rem;height:.5rem;border-radius:50%;background:var(--orange);animation:pulse 2s ease-in-out infinite}
.bar i{font-style:normal;color:var(--grey);display:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar i a{text-decoration:none}.bar i a:hover{color:var(--white)}
.bar span{margin-left:auto;display:flex;gap:1.25rem}
.bar span a{text-decoration:none;padding:.5rem 0}
.bar span a:hover{color:var(--orange)}
.dock{position:fixed;right:var(--pad);bottom:4.25rem;z-index:16;width:min(26rem,calc(100vw - 2 * var(--pad)));border:1px solid var(--line);border-radius:14px;background:var(--deep);box-shadow:0 1.5rem 3rem rgba(0,0,0,.5);overflow:hidden;animation:rise .5s var(--ease) both}
.dock iframe{display:block;width:100%;height:152px;border:0}
.dock button{position:absolute;right:.4rem;top:.4rem;z-index:1;display:grid;place-items:center;width:2rem;height:2rem;border-radius:50%;background:rgba(0,0,0,.6)}
.nf{min-height:100svh;display:grid;place-content:center;gap:1.5rem;text-align:center;padding:6rem var(--pad) 3rem}
.nf h1{font-size:clamp(3.5rem,12vw,8rem)}
.nf .seal{margin:0 auto;width:7rem}
.nf .seal svg{animation:spin 5s linear infinite}
.cta-band{display:grid;gap:1.5rem 3rem;align-items:end}
.cta-band h2{font-size:clamp(3rem,8vw,6rem)}
.cta-side{display:grid;gap:1.5rem;justify-items:start}
.cta-side p{margin:0;max-width:30em;color:var(--soft)}
.subgrid{display:grid;gap:clamp(2.5rem,6vw,6rem);align-items:start}
.steps ol{display:grid;gap:0;margin:0 0 2rem}
.steps li{display:grid;grid-template-columns:3.25rem 1fr;gap:.35rem 1rem;padding:1.35rem 0;border-bottom:1px solid var(--line)}
.steps li:first-child{border-top:1px solid var(--line)}
.steps b{grid-row:span 2;font:400 2.25rem/1 var(--d);color:var(--orange)}
.steps strong{font:400 1.5rem/1.1 var(--d)}
.steps span{color:var(--soft);font-size:.9375rem}
.steps .mute a{color:var(--white)}
.subform fieldset{border:0;margin:0 0 3rem;padding:0;min-width:0;display:grid;gap:1.9rem}
.subform legend{display:flex;align-items:baseline;gap:.8rem;padding:0;margin-bottom:1.75rem;font:400 clamp(1.9rem,3.6vw,2.6rem)/1 var(--d)}
.subform legend i{font:500 .6875rem/1 Roboto,sans-serif;letter-spacing:.2em;color:var(--orange);font-style:normal}
.two{display:grid;gap:1.9rem}
.field{display:grid;gap:.45rem;min-width:0}
.lab{display:flex;justify-content:space-between;align-items:center;gap:1rem;min-height:1.5rem}
.lab label{font-size:.6875rem;font-weight:500;letter-spacing:.24em;text-transform:uppercase;color:var(--grey);transition:color .2s}
.field:focus-within label{color:var(--orange)}
.field input,.field textarea{width:100%;margin:0;padding:.65rem 0;border:0;border-bottom:1px solid rgba(254,254,254,.25);border-radius:0;background:transparent;color:var(--white);font:400 clamp(1.125rem,2vw,1.375rem)/1.4 Roboto,system-ui,sans-serif;outline:none;box-shadow:0 1px 0 transparent;transition:border-color .25s,box-shadow .25s}
.field textarea{min-height:10rem;resize:vertical;line-height:1.55}
.field input::placeholder,.field textarea::placeholder{color:#6d6a66}
.field input:focus,.field textarea:focus{border-color:var(--orange);box-shadow:0 1px 0 var(--orange)}
.field input:-webkit-autofill{-webkit-text-fill-color:var(--white);-webkit-box-shadow:0 0 0 40rem var(--ink) inset;caret-color:var(--white)}
.field small{display:flex;justify-content:space-between;gap:1rem;color:var(--grey);font-size:.8125rem}
.count-c{margin-left:auto;font-variant-numeric:tabular-nums}
.err{color:#ff8a6b;font-size:.8125rem;min-height:0}
.err:empty{display:none}
.bad input,.bad textarea{border-color:#ff8a6b}
.plat{padding:.25rem .65rem;border-radius:999px;background:rgba(246,161,14,.14);color:var(--orange);font-size:.625rem;font-weight:500;letter-spacing:.16em;text-transform:uppercase;opacity:0;transform:translateY(4px);transition:opacity .25s,transform .25s}
.plat.on{opacity:1;transform:none}
.lab .lbl{font-size:.6875rem;font-weight:500;letter-spacing:.24em;text-transform:uppercase;color:var(--grey)}
.genres{display:flex;flex-wrap:wrap;gap:.5rem;padding-top:.35rem}
.pill{position:relative;cursor:pointer}
.pill input{position:absolute;inset:0;opacity:0;margin:0;cursor:pointer}
.pill span{display:inline-flex;align-items:center;height:2.6rem;padding:0 1.15rem;border:1px solid rgba(254,254,254,.25);border-radius:999px;font-size:.9375rem;transition:background-color .2s,border-color .2s,color .2s}
.pill:hover span{border-color:var(--orange)}
.pill input:checked+span{background:var(--orange);border-color:var(--orange);color:var(--ink)}
.pill input:focus-visible+span{outline:2px solid var(--orange);outline-offset:3px}
.bad .pill span{border-color:#ff8a6b}
.check-wrap{display:grid;gap:.45rem}
.check{display:flex;gap:.9rem;align-items:flex-start;cursor:pointer;color:var(--soft)}
.check input{appearance:none;-webkit-appearance:none;flex:none;display:grid;place-items:center;width:1.45rem;height:1.45rem;margin:.05rem 0 0;border:1px solid var(--grey);border-radius:.35rem;background:transparent;cursor:pointer;transition:background-color .2s,border-color .2s}
.check input::after{content:"";width:.7rem;height:.38rem;margin-top:-.2rem;border:2px solid var(--ink);border-top:0;border-right:0;transform:rotate(-45deg) scale(0);transition:transform .2s var(--ease)}
.check input:checked{background:var(--orange);border-color:var(--orange)}
.check input:checked::after{transform:rotate(-45deg) scale(1)}
.check input:focus-visible{outline:2px solid var(--orange);outline-offset:3px}
.bad .check input{border-color:#ff8a6b}
.hp{position:absolute;left:-10000px;width:1px;height:1px;overflow:hidden}
.prose{max-width:46rem}
.prose h2{font-size:clamp(2.25rem,6vw,3.5rem);margin-bottom:1.25rem}
.prose p{margin:0 0 1.1rem;color:var(--soft);max-width:40em}
.prose p.mute{color:var(--grey)}
.prose a{text-underline-offset:.2em}
.prose a:hover{color:var(--orange)}
.bullets{display:grid;gap:.9rem;margin:0;max-width:40em}
.bullets li{position:relative;padding-left:1.5rem;color:var(--soft)}
.bullets li::before{content:"";position:absolute;left:0;top:.65em;width:.5rem;height:1px;background:var(--orange)}
.bullets strong{font-weight:500;color:var(--white)}
.facts{display:grid;gap:1px;margin:0;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.facts>div{display:grid;gap:.35rem;padding:1.1rem 1.25rem;background:var(--deep)}
.facts dt{color:var(--grey)}
.facts dd{margin:0}
.legal a{text-underline-offset:.2em}
.legal a:hover{color:var(--orange)}
.privacy{margin:0 0 1.5rem;color:var(--grey);font-size:.875rem;max-width:36em}
.send{min-height:3.5rem;padding:0 2.1rem}
.send:disabled{opacity:.6;cursor:wait}
.form-msg{margin:1rem 0 0;color:#ff8a6b}
.form-msg:empty{display:none}
.done{display:grid;gap:1.25rem;justify-items:start;padding:clamp(2rem,5vw,3.5rem);border:1px solid var(--line);border-radius:14px;background:var(--deep);outline:none;animation:rise .6s var(--ease) both}
.done h2{font-size:clamp(2.5rem,6vw,4.5rem)}
.done p{margin:0;max-width:34em;color:var(--soft)}
.done .more{margin:.5rem 0 0}
.tick{display:grid;place-items:center;width:3.5rem;height:3.5rem;border-radius:50%;background:var(--orange);color:var(--ink)}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes bob{0%,100%{transform:rotate(0) translateY(0)}30%{transform:rotate(-4deg) translateY(-2%)}60%{transform:rotate(2deg) translateY(0)}}
@keyframes glow{from{opacity:.55;transform:translate(-50%,-50%) scale(.9)}to{opacity:1;transform:translate(-50%,-50%) scale(1.08)}}
@keyframes arm{from{transform:rotate(20deg)}to{transform:rotate(24deg)}}
@keyframes rise{from{opacity:0;transform:translateY(1.25rem)}to{opacity:1;transform:none}}
@keyframes wup{from{transform:translateY(110%)}to{transform:none}}
@keyframes tick{to{transform:translateX(-50%)}}
@keyframes slide{from{transform:translateX(0) rotate(0)}to{transform:translateX(40%) rotate(90deg)}}
@keyframes pulse{50%{opacity:.35}}
@keyframes failsafe{to{opacity:1;transform:none}}
@media (scripting:enabled) and (prefers-reduced-motion:no-preference){
.reveal{opacity:0;transform:translateY(2rem);transition:opacity 1s var(--ease),transform 1s var(--ease)}
.reveal.in{opacity:1;transform:none}
.stagger>*{opacity:0;transform:translateY(1.75rem);transition:opacity .9s var(--ease),transform .9s var(--ease)}
.stagger.in>*{opacity:1;transform:none}
.stagger>:nth-child(2){transition-delay:.08s}.stagger>:nth-child(3){transition-delay:.16s}.stagger>:nth-child(4){transition-delay:.24s}.stagger>:nth-child(5){transition-delay:.32s}.stagger>:nth-child(n+6){transition-delay:.4s}
.words:not(.load) .w>span{transform:translateY(110%);transition:transform 1s var(--ease)}
.in .words .w>span,.words.in .w>span{transform:none}
.words:not(.load) .w:nth-child(2)>span{transition-delay:.07s}.words:not(.load) .w:nth-child(3)>span{transition-delay:.14s}.words:not(.load) .w:nth-child(4)>span{transition-delay:.21s}
html:not(.js) .reveal,html:not(.js) .stagger>*,html:not(.js) .words:not(.load) .w>span{animation:failsafe .01s 3s forwards}
}
@media (scripting:none){.menu,.ctrl,.bars,.bar .pp,.hint{display:none!important}}
@media (max-width:52rem){
.top .brand span{display:none}
.nav{overflow-x:auto;scrollbar-width:none}
.nav i{display:none}
.nav a{padding:.55rem .6rem}
}
@media (max-width:52rem) and (scripting:enabled){
.menu{display:inline-flex;align-items:center;gap:.7rem;height:2.5rem;padding:0 1.1rem;border:1px solid var(--line);border-radius:999px;background:rgba(21,21,20,.6)}
.menu i{position:relative;width:1rem;height:.5rem}
.menu i::before,.menu i::after{content:"";position:absolute;left:0;right:0;height:1.5px;background:currentColor;transition:transform .35s var(--ease),top .35s var(--ease)}
.menu i::before{top:0}.menu i::after{top:calc(100% - 1.5px)}
.open .menu i::before{top:calc(50% - .75px);transform:rotate(45deg)}
.open .menu i::after{top:calc(50% - .75px);transform:rotate(-45deg)}
.nav{position:fixed;inset:0;z-index:-1;flex-direction:column;align-items:flex-start;justify-content:center;gap:0;padding:6rem var(--pad) 5rem;background:var(--ink);overflow:auto;opacity:0;visibility:hidden;transition:opacity .35s,visibility .35s}
.nav a{display:flex;align-items:baseline;gap:.6rem;padding:.15rem 0;border-radius:0;font:400 clamp(2.75rem,13vw,4.75rem)/1.05 var(--d);letter-spacing:0;text-transform:none;opacity:0;transform:translateY(1.25rem);transition:opacity .5s,transform .6s var(--ease),color .2s}
.nav a[aria-current]{background:none;color:var(--orange)}
.nav i{display:inline;font:500 .75rem/1 Roboto,sans-serif;letter-spacing:.2em}
.nav a[aria-current] i{color:var(--orange)}
.open{overflow:hidden}
.open .top{-webkit-backdrop-filter:none;backdrop-filter:none;background:var(--ink);border-color:transparent}
.open .nav{opacity:1;visibility:visible}
.open .nav a{opacity:1;transform:none}
.open .nav a:nth-child(2){transition-delay:.05s}.open .nav a:nth-child(3){transition-delay:.1s}.open .nav a:nth-child(4){transition-delay:.15s}.open .nav a:nth-child(5){transition-delay:.2s}
}
@media (min-width:40rem){.bar i{display:block}.two{grid-template-columns:1fr 1fr}.facts{grid-template-columns:1fr 1fr}.facts>div:last-child:nth-child(odd){grid-column:1/-1}}
@media (max-width:64rem){.top .brand span{display:none}}
@media (min-width:48rem){.slide{grid-template-columns:minmax(0,5fr) minmax(0,6fr)}}
@media (min-width:60rem){
.hero-in{grid-template-columns:minmax(0,5fr) minmax(0,7fr);text-align:left;justify-items:start;align-items:center;column-gap:clamp(2rem,6vw,6rem)}
.hero-in .stage{grid-row:1/5;width:min(100%,30rem);justify-self:center}
.cta,.tag{justify-content:flex-start}
.release{grid-template-columns:minmax(0,1fr) minmax(0,1fr);align-items:start}
.subgrid{grid-template-columns:minmax(0,4fr) minmax(0,7fr)}
.steps{position:sticky;top:6rem}
.cta-band{grid-template-columns:minmax(0,1fr) minmax(0,26rem)}
.release .sleeve{position:sticky;top:6rem}
.about{grid-template-columns:minmax(0,1fr) auto}
.profile{grid-template-columns:minmax(0,5fr) minmax(0,7fr)}
.roster{grid-template-columns:repeat(3,minmax(0,1fr))}
.foot-cta{grid-template-columns:minmax(0,1fr) auto;align-items:end}
}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{transition:none!important;animation:none!important}.rec{transform:translateX(40%)}.artist video,.portrait video{display:none}.seal svg{transform:none}}
""".strip()
CSS = "".join(line.strip() for line in CSS.splitlines())
CSS_HASH = base64.b64encode(hashlib.sha256(CSS.encode()).digest()).decode()
CSP = (f"default-src 'none'; script-src 'self'; connect-src 'self' https://script.google.com https://script.googleusercontent.com; img-src 'self' {' '.join(ORIGINS)}; font-src 'self'; media-src 'self'; "
       f"frame-src https://open.spotify.com; style-src 'sha256-{CSS_HASH}'; base-uri 'none'; form-action 'none'")



def album_node(rel):
    lid = f"{D}/#label"
    arts = rel_artists(rel)
    by = [{"@id": a["id"]} for a in arts] if arts else [{"@type": "MusicGroup", "name": rel["artist"]}]
    url = f"{D}{rel_url(rel)}"
    return {"@type": "MusicAlbum", "@id": f"{url}#album", "name": rel["title"], "url": url,
            "albumReleaseType": f"https://schema.org/{rel['type']}Release",
            "byArtist": by[0] if len(by) == 1 else by, "creditText": rel["artist"],
            "datePublished": rel["date"], "image": rel["image"]["jpg"]["1200"],
            "sameAs": [l["url"] for l in rel["links"] if "watch?v=" not in l["url"]] + rel.get("sameAs", []),
            "numTracks": 1 if rel["type"] == "Single" else None, "genre": rel.get("genre"),
            "albumRelease": {"@type": "MusicRelease", "name": rel["title"], "recordLabel": {"@id": lid},
                             "gtin13": rel.get("upc"), "datePublished": rel["date"],
                             "musicReleaseFormat": "https://schema.org/DigitalFormat"},
            "track": {"@type": "MusicRecording", "name": rel["title"], "duration": rel.get("duration"),
                      "byArtist": by[0] if len(by) == 1 else by}}


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items() if v is not None}
    if isinstance(o, list):
        return [clean(v) for v in o]
    return o


def jsonld():
    lid = f"{D}/#label"
    graph = [
        {"@type": "WebSite", "@id": f"{D}/#website", "url": f"{D}/", "name": L["name"],
         "inLanguage": "en", "publisher": {"@id": lid}},
        {"@type": "WebPage", "@id": f"{D}/#webpage", "url": f"{D}/", "name": TITLE, "description": DESC,
         "inLanguage": "en", "isPartOf": {"@id": f"{D}/#website"}, "about": {"@id": lid},
         "primaryImageOfPage": f"{D}/og.png", "dateModified": TODAY},
        {"@type": "Organization", "@id": lid, "name": L["name"], "url": f"{D}/", "description": L["description"], "knowsAbout": [g + (" music" if g.lower() in ("pop", "lofi") else "") for g in GENRES] or None,
         "alternateName": L.get("alternateName"), "disambiguatingDescription": L.get("disambiguatingDescription"),
         "logo": f"{D}/logo.png", "image": f"{D}/og.png", "email": L["contact"], "sameAs": L["sameAs"],
         "founder": {"@id": CB["id"]} if CB else None,
         "subjectOf": [{"@id": f"{D}{rel_url(r)}#album"} for r in RELEASES]},
    ]
    for a in ARTISTS:
        graph.append({"@type": "MusicGroup", "@id": a["id"], "name": a["name"], "url": a["url"],
                      "sameAs": list(dict.fromkeys([a["url"]] + a.get("sameAs", []))), "genre": a.get("genre")})
    graph += [album_node(rel) for rel in RELEASES]

    return json.dumps({"@context": "https://schema.org", "@graph": [clean(g) for g in graph]},
                      ensure_ascii=False, separators=(",", ":"))


def slug_of(a):
    return a.get("slug") or re.sub(r"[^a-z0-9]+", "-", a["name"].lower()).strip("-")


def artist_url(a):
    return f"/artists/{slug_of(a)}/"


NAV = [("Release", rel_url(R), "release"), ("Catalog", "/catalog/", "catalog"), ("Artists", "/artists/", "artists"),
       ("News", "/news/", "news"), ("Submit", "/submit/", "submit"), ("Contact", "/contact/", "contact")]
LINK_NAMES = {"instagram": "Instagram", "musicbrainz": "MusicBrainz", "discogs": "Discogs", "wikidata": "Wikidata",
              "spotify": "Spotify", "apple.com": "Apple Music", "deezer": "Deezer", "tidal": "Tidal", "youtube": "YouTube",
              "soundcloud": "SoundCloud", "bandcamp": "Bandcamp", "tiktok": "TikTok"}
LISTEN_SITES = ("spotify", "apple.com", "deezer", "tidal", "youtube", "soundcloud", "bandcamp", "amazon")


def link_name(u):
    return next((n for k, n in LINK_NAMES.items() if k in u), re.sub(r"^https?://(www\.)?", "", u).split("/")[0])


def spotify_embed(rel):
    sp = next((l["url"] for l in rel["links"] if "open.spotify.com/" in l["url"]), None)
    m = sp and re.search(r"open\.spotify\.com/(album|track|playlist)/([A-Za-z0-9]+)", sp)
    return f"https://open.spotify.com/embed/{m.group(1)}/{m.group(2)}?utm_source=3rdrecords&theme=0" if m else None


def year_of(rel):
    return dt.date.fromisoformat(rel["date"]).year


def ldjson(graph):
    return ('<script type="application/ld+json">'
            + json.dumps({"@context": "https://schema.org", "@graph": [clean(g) for g in graph]}, ensure_ascii=False, separators=(",", ":"))
            + "</script>")


LABEL_REF = {"@type": "Organization", "@id": f"{D}/#label", "name": L["name"], "url": f"{D}/", "sameAs": L["sameAs"]}


def crumbs_ld(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": k, "name": n, "item": f"{D}{u}"} for k, (n, u) in enumerate(items, 1)]}


def crumbs_html(items):
    lis = "".join(f'<li><a href="{u}">{e(n)}</a></li>' for n, u in items[:-1])
    return f'<nav aria-label="Breadcrumb"><ol class="crumbs up">{lis}<li aria-current="page">{e(items[-1][0])}</li></ol></nav>'


def page_ld(path, title, desc, typ="WebPage", **extra):
    return dict({"@type": typ, "@id": f"{D}{path}", "url": f"{D}{path}", "name": title, "description": desc,
                 "inLanguage": "en", "isPartOf": {"@id": f"{D}/#website"}}, **extra)


def head(title, desc, canonical=True, robots="index,follow,max-image-preview:large", path="/", image=None, og_type="website", image_alt=None):
    p = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         f"<title>{e(title)}</title>", f'<meta name="description" content="{e(desc)}">',
         f'<meta name="robots" content="{robots}">',
         f'<meta http-equiv="Content-Security-Policy" content="{CSP}">',
         '<meta name="referrer" content="strict-origin-when-cross-origin">']
    if canonical:
        img = image or f"{D}/og.png"
        p += [f'<link rel="canonical" href="{D}{path}">', f'<meta property="og:type" content="{og_type}">',
              f'<meta property="og:site_name" content="{e(L["name"])}">',
              f'<meta property="og:title" content="{e(title)}">',
              f'<meta property="og:description" content="{e(desc)}">',
              f'<meta property="og:url" content="{D}{path}">', f'<meta property="og:image" content="{e(img)}">',
              f'<meta property="og:image:alt" content="{e(image_alt or L["name"] + " logo")}">',
              '<meta property="og:locale" content="en_US">', '<meta name="twitter:card" content="summary_large_image">']
    p += [f'<meta name="theme-color" content="{C["ink"]}">',
          '<link rel="icon" href="/favicon.ico" sizes="32x32">',
          '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
          '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
          '<link rel="preload" href="/fonts/avigea.woff2" as="font" type="font/woff2" crossorigin>',
          f"<style>{CSS}</style>",
          f'<script src="/js/site.js?v={JS_VER}" defer></script>']
    return "".join(p)


def top(cur=None):
    cur_attr = ' aria-current="page"'
    links = "".join(
        f'<a href="{u}"{cur_attr if key == cur else ""}><i>{k:02d}</i>{n}</a>'
        for k, (n, u, key) in enumerate(NAV, 1))
    return (f'<header class="top"><a class="brand" href="/" aria-label="{e(L["name"])} home">{circle(C["orange"], ref=True)}'
            f'<span class="up">{e(L["name"])}</span></a>'
            f'<nav class="nav up" id="nav" aria-label="Main">{links}</nav>'
            '<button class="menu up" type="button" aria-expanded="false" aria-controls="nav"><span>Menu</span><i aria-hidden="true"></i></button>'
            '</header>')


def footer(cta=True):
    year = max(year_of(R), dt.date.today().year)
    pages = "".join(f'<li><a href="{u}">{n}</a></li>' for n, u, _ in NAV)
    arts = "".join(f'<li><a href="{artist_url(a)}">{e(a["name"])}</a></li>' for a in ARTISTS)
    else_ = "".join(f'<li><a href="{e(u)}">{link_name(u)}</a></li>' for u in L["sameAs"])
    more = (f'<li><a href="mailto:{L["contact"]}">{L["contact"]}</a></li>'
            f'<li><a href="/portfolio/leadmajor/">{e(CB["name"])} portfolio</a></li>')
    return (
        '<footer class="foot">'
        + ('<div class="foot-cta reveal"><div><p class="kick up">Get in touch</p><h2>Contact</h2></div>'
           f'<div class="mailbox"><a class="big-mail" href="mailto:{L["contact"]}">{L["contact"]}</a>'
           f'<button class="btn up magnet" type="button" data-copy="{L["contact"]}"><span>Copy</span></button></div></div>' if cta else "")
        + '<div class="foot-grid">'
        + f'<div><p class="fh up">Pages</p><ul>{pages}</ul></div>'
        + f'<div><p class="fh up">Artists</p><ul>{arts}</ul></div>'
        + f'<div><p class="fh up">Elsewhere</p><ul>{else_}</ul></div>'
        + f'<div><p class="fh up">Contact</p><ul>{more}</ul></div></div>'
        + f'<div class="legal up"><span>© {year} {e(L["name"])} · Independent record label created by {e(CB["name"])} · <a href="/legal/">Legal notice &amp; privacy</a></span>'
        + f'<button type="button" data-totop>Back to top {icon("up")}</button></div>'
        + '</footer>')


def bar():
    t = e(R["title"])
    first = R["links"][0]
    apple = next((l for l in R["links"] if l["name"] == "Apple Music"), None)
    links = f'<a href="{e(first["url"])}">{e(first["name"])}</a>' + (f'<a href="{e(apple["url"])}">Apple Music</a>' if apple else "")
    emb = spotify_embed(R)
    pp = (f'<button class="pp" type="button" data-dock="{e(emb)}" data-title="{t} by {e(R["artist"])} on Spotify" '
          f'aria-expanded="false" aria-controls="dock" aria-label="Play {t} by {e(R["artist"])}">{icon("play")}</button>') if emb else ""
    return (f'<aside class="bar up" aria-label="Latest release">{pp}<b>Out now</b>'
            f'<i><a href="{rel_url(R)}">{e(R["artist"])} — {t}</a></i><span>{links}</span></aside>'
            + ('<div class="dock" id="dock" hidden><button type="button" data-undock aria-label="Close player">'
               + icon("x") + '</button><div class="dock-f"></div></div>' if emb else ""))


def shell(title, desc, path, main, graph, cur=None, cta=True, **meta):
    return (head(title, desc, path=path, **meta) + ldjson(graph) + '</head><body>'
            + SYMBOLS + '<a class="skip up" href="#main">Skip to content</a>'
            + '<div class="progress" aria-hidden="true"></div><div class="glow" aria-hidden="true"></div>'
            + top(cur) + f'<main id="main">{main}</main>' + footer(cta) + bar() + '</body></html>\n')


def listen_list(rel):
    t = e(rel["title"])
    return (f'<ul class="listen" aria-label="Listen to {t}">' + "".join(
        f'<li><a href="{e(l["url"])}"><span class="pf">{e(l["name"])}</span>'
        f'<span class="act up">{"Watch" if "watch?v=" in l["url"] else "Listen"}'
        f'<span class="sr">{"" if "watch?v=" in l["url"] else " to"} {t} on {e(l["name"])}</span>{icon("out")}</span></a></li>'
        for l in rel["links"]) + '</ul>')


def player(rel):
    emb = spotify_embed(rel)
    if not emb:
        return ""
    t = e(rel["title"])
    return (f'<div class="player"><button type="button" data-embed="{e(emb)}" data-title="{t} by {e(rel["artist"])} on Spotify">'
            f'<span class="pp">{icon("play")}</span><span><b>Play {t} here</b>'
            '<small class="up">Loads the Spotify player</small></span></button></div>')


def by_links(rel):
    by_html = e(rel["artist"])
    for a in sorted(rel_artists(rel), key=lambda a: -len(a["name"])):
        by_html = re.sub(r"(?<![\w>])" + re.escape(e(a["name"])) + r"(?![\w<])", f'<a href="{artist_url(a)}">{e(a["name"])}</a>', by_html, count=1)
    return by_html


def release_card(rel, h="h3", sizes="(min-width:60rem) 20rem, (min-width:40rem) 45vw, 100vw"):
    arts = "|".join(a["name"] for a in rel_artists(rel))
    return (f'<li data-artists="{e(arts)}"><a class="card" href="{rel_url(rel)}"><span class="art tilt">'
            f'{picture(rel, "", sizes, 640)}<span class="go">{icon("right")}</span></span>'
            f'<{h}>{e(rel["title"])}</{h}><p class="up">{e(rel["artist"])} · {e(rel["type"])} · '
            f'<time datetime="{rel["date"]}">{year_of(rel)}</time></p></a></li>')


def artist_card(a, h="h3"):
    img = (f'<img{CENTER if a.get("position") == "50% 50%" else ""} src="{e(a["image"])}" width="800" height="1000" '
           f'alt="{e(a["alt"])}" loading="lazy" decoding="async">')
    vid = (f'<video src="{e(a["video"])}" poster="{e(a["image"])}" autoplay muted loop playsinline '
           'preload="metadata" aria-hidden="true"></video>') if a.get("video") else ""
    n = len([r for r in RELEASES if a in rel_artists(r)])
    extra = f' · {n} release{"s" if n != 1 else ""}' if n else ""
    return (f'<li><a class="artist" href="{artist_url(a)}"><div class="art tilt">{img}{vid}'
            f'<span class="go">{icon("right")}</span>'
            f'<div class="info"><{h}{LONG if len(a["name"]) > 6 else ""}>{e(a["name"])}</{h}><p class="up">{e(a["role"])}{extra}</p></div></div></a></li>')


def news_list(items, h="h3"):
    def one(n):
        rel = next((r for r in RELEASES if r["slug"] == n.get("release")), None)
        meta = " · ".join(x for x in [e(n["outlet"]), e(n["author"]) if n.get("author") else "",
                                        f'<time datetime="{n["date"]}">{fmt_date(n["date"])}</time>'] if x)
        return (f'<li><a href="{e(n["url"])}"><p class="up">{meta}</p><{h}>{e(n["title"])}</{h}>'
                f'<p>{e(n["summary"])}</p><p class="up or">{e(n["artist"])}'
                + (f' · {e(rel["title"])}' if rel else "") + f' · Read on {e(n["outlet"])} {icon("out")}</p></a></li>')
    return f'<ul class="news stagger">{"".join(one(n) for n in items)}</ul>'


def section_head(kick, title, text="", hid=None, level="h2", extra=""):
    cls = "words" if level == "h2" else "words load"
    idattr = f' id="{hid}"' if hid else ""
    return (f'<div class="head"><div><p class="kick up">{e(kick)}</p>'
            f'<{level} class="{cls}"{idattr}>{words(title)}</{level}></div>'
            + (f'<p>{text}</p>' if text else "") + extra + '</div>')


# ---------------------------------------------------------------- home

def index():
    t = e(R["title"])
    PAST = RELEASES[1:]  # the latest release already has its own section above
    n = len(PAST)
    items = [f"<b>{t}</b> {e(R['artist'])}", "Out now", e(L["name"]), " / ".join(e(g) for g in GENRES), f"Created by {e(CB['name'])}"]
    tick = "".join(f"<span>{i}</span>" for i in items * 2)
    slides = "".join(
        f'<li class="slide" aria-roledescription="slide" aria-label="{k} of {n}: {e(rel["title"])}">'
        f'<a class="art tilt" href="{rel_url(rel)}" tabindex="-1">{picture(rel, "", "(min-width:48rem) 34rem, 100vw", 640)}</a>'
        f'<div><p class="up mute">{k:02d} · {e(rel["type"])} · <time datetime="{rel["date"]}">{fmt_date(rel["date"])}</time></p>'
        f'<h3><a href="{rel_url(rel)}">{e(rel["title"])}</a></h3><p class="by">{by_links(rel)}</p>'
        '<p class="pills">' + "".join(f'<a href="{e(l["url"])}">{e(l["name"])} {icon("out")}</a>' for l in rel["links"][:4]) + '</p>'
        f'<a class="btn up magnet" href="{rel_url(rel)}">Release page {icon("right")}</a></div></li>'
        for k, rel in enumerate(PAST, 1))
    on = ' class="on"'
    backdrop = "".join(f'<img src="{e(rel["image"]["jpg"]["640"])}" alt="" loading="lazy" decoding="async"{on if k == 0 else ""}>'
                       for k, rel in enumerate(PAST))
    ctrl = (f'<div class="ctrl"><button class="round magnet" type="button" data-prev aria-label="Previous release">{icon("left")}</button>'
            f'<span class="count up" aria-hidden="true"><b>01</b> / {n:02d}</span>'
            f'<button class="round magnet" type="button" data-next aria-label="Next release">{icon("right")}</button></div>')
    bars = '<div class="bars">' + "".join(
        f'<button type="button" aria-label="Show {e(rel["title"])}" aria-current="{"true" if k == 0 else "false"}"></button>'
        for k, rel in enumerate(PAST)) + '</div>'
    main = (
        '<section class="hero" aria-labelledby="name"><div class="hero-in">'
        + f'<div class="stage rise" aria-hidden="true"><div class="disc" data-worklet="/js/scratch.js?v={WORKLET_VER}">{circle(C["orange"], ref=True)}</div><div class="sheen"></div><div class="arm"></div>'
        + '<span class="hint up">Drag to scratch · sound on</span></div>'
        + f'<h1 id="name" class="rise d2">{lockup("lockup", C["orange"], C["white"], link="/duck/")}<span class="sr">{e(L["name"])}</span></h1>'
        + f'<p class="tag up rise d3">{" · ".join(e(g) for g in GENRES)} label · Created by <img class="lm" src="{e(CB["logo"])}" width="24" height="24" alt=""> {e(CB["name"])}</p>'
        + f'<p class="cta rise d4"><a class="btn up fill magnet" href="#release">Listen to {t} {icon("right")}</a>'
        + f'<a class="btn up magnet" href="/catalog/">Catalog</a></p>'
        + '</div><canvas class="eq" aria-hidden="true"></canvas>'
        + '<div class="ticker" aria-hidden="true"><div>' + tick * 2 + '</div></div></section>'
        # latest release
        + '<section class="sec release" id="release" aria-labelledby="release-title">'
        + f'<div class="sleeve reveal"><div class="rec" aria-hidden="true">{circle(C["orange"], ref=True)}</div>'
        + picture(R, "cover", "(min-width:60rem) 42rem, calc(100vw - 2rem)") + '</div><div class="reveal relinfo">'
        + f'<p class="kick up">Latest release · New {e(R["type"].lower())}</p>'
        + f'<h2 class="title words{fit_cls(R["title"])}" id="release-title"><a href="{rel_url(R)}">{words(R["title"])}</a></h2>'
        + f'<p class="by">{by_links(R)}</p>'
        + f'<p class="meta up">{e(R["type"])} · <time datetime="{R["date"]}">{fmt_date(R["date"])}</time> · {e(L["name"])}</p>'
        + listen_list(R) + player(R)
        + f'<p class="more"><a class="btn up magnet" href="{rel_url(R)}">Release page {icon("right")}</a></p>'
        + '</div></section>'
        # catalog slider
        + ('<section class="sec feat" id="catalog" aria-labelledby="catalog-h">'
           + f'<div class="backdrop" aria-hidden="true">{backdrop}</div>'
           + section_head("Discography", "Catalog", f"Earlier releases from {e(L['name'])}." + (" Use the arrows or your keyboard to browse." if n > 1 else ""), "catalog-h", extra=ctrl if n > 1 else "")
           + f'<div class="slider reveal"><ul class="track" aria-label="Earlier {e(L["name"])} releases">{slides}</ul></div>{bars if n > 1 else ""}'
           + f'<p class="more"><a class="btn up magnet" href="/catalog/">Full catalog {icon("right")}</a></p></section>' if PAST else "")
        # artists
        + '<section class="sec" id="artists" aria-labelledby="artists-h">'
        + section_head("Artist pool", "Artists", e(POOL_TXT), "artists-h")
        + f'<ul class="roster stagger">{"".join(artist_card(a) for a in ARTISTS)}</ul>'
        + f'<p class="more"><a class="btn up magnet" href="/artists/">All artists {icon("right")}</a></p></section>'
        # news
        + ('<section class="sec" id="news" aria-labelledby="news-h">'
           + section_head("In the press", "News", "", "news-h")
           + news_list(NEWS[:3]) + f'<p class="more"><a class="btn up magnet" href="/news/">All news {icon("right")}</a></p></section>' if NEWS else "")
        + submit_cta()
        # about
        + f'<section class="sec about reveal" aria-labelledby="about-h"><div><p class="kick up">The label</p><h2 id="about-h" class="sr">About {e(L["name"])}</h2>'
        + f'<p>{e(L["intro"])} {e(ROSTER_TXT)}</p></div>'
        + f'<div class="seal" aria-hidden="true">{circle(C["choco"], ref=True)}</div></section>'
    )
    return shell(TITLE, DESC, "/", main, json.loads(jsonld())["@graph"])


# ---------------------------------------------------------------- catalog

def catalog_page():
    path = "/catalog/"
    title = f"Catalog | {L['name']}"
    listing = ", ".join("“" + r["title"] + "” by " + r["artist"] for r in RELEASES)
    desc = f"The complete {L['name']} discography: {listing}. Listen on Spotify, Apple Music, Deezer and more."
    names = []
    for r in RELEASES:
        for a in rel_artists(r):
            if a["name"] not in names:
                names.append(a["name"])
    chips = ('<div class="chips" hidden role="group" aria-label="Filter by artist">'
             '<button class="chip up" type="button" data-f="*" aria-pressed="true">All</button>'
             + "".join(f'<button class="chip up" type="button" data-f="{e(nm)}" aria-pressed="false">{e(nm)}</button>' for nm in names)
             + f'<output class="up" aria-live="polite">{len(RELEASES)} releases</output></div>')
    items = "".join(release_card(r, "h2") for r in RELEASES)
    crumbs = [(L["name"], "/"), ("Catalog", path)]
    main = (f'<section class="sec page" aria-labelledby="page-h">{crumbs_html(crumbs)}'
            + section_head("Discography", "Catalog",
                           f"{len(RELEASES)} releases from {e(L['name'])}, newest first. Pick a release to listen on your platform.", "page-h", level="h1")
            + chips + f'<ul class="grid stagger">{items}</ul></section>')
    graph = [page_ld(path, title, desc, "CollectionPage", about={"@id": f"{D}/#label"}, breadcrumb=crumbs_ld(crumbs),
                     mainEntity={"@type": "ItemList", "numberOfItems": len(RELEASES), "itemListElement": [
                         {"@type": "ListItem", "position": k, "url": f"{D}{rel_url(r)}", "item": {"@id": f"{D}{rel_url(r)}#album"}}
                         for k, r in enumerate(RELEASES, 1)]}),
             LABEL_REF] + [album_node(r) for r in RELEASES]
    return shell(title, desc, path, main, graph, cur="catalog")


# ---------------------------------------------------------------- release

def release_page(rel):
    t = e(rel["title"])
    path = rel_url(rel)
    arts = rel_artists(rel)
    by = rel["artist"]
    k = RELEASES.index(rel)
    prev_r, next_r = RELEASES[(k - 1) % len(RELEASES)], RELEASES[(k + 1) % len(RELEASES)]
    press = [n for n in NEWS if n.get("release") == rel["slug"]]
    others = [r for r in RELEASES if r is not rel]
    title = f"{rel['title']} – {by} | {L['name']}"
    desc = (f"“{rel['title']}”, the {rel['type'].lower()} by {by}, released on {fmt_date(rel['date'])} by {L['name']}, "
            f"the independent record label created by {CB['name']}. Listen on {', '.join(l['name'] for l in rel['links'][:4])}.")
    crumbs = [(L["name"], "/"), ("Catalog", "/catalog/"), (rel["title"], path)]
    groups = [{"@type": "MusicGroup", "@id": a["id"], "name": a["name"], "url": a["url"],
               "sameAs": list(dict.fromkeys([a["url"]] + a.get("sameAs", [])))} for a in arts]
    graph = [page_ld(path, title, desc, about={"@id": f"{D}{path}#album"}, primaryImageOfPage=rel["image"]["jpg"]["1200"],
                     breadcrumb=crumbs_ld(crumbs)), album_node(rel), LABEL_REF] + groups
    pager = ('<nav class="sec" aria-label="More releases"><div class="pager">'
             f'<a href="{rel_url(prev_r)}" rel="prev"><span class="up">{icon("left")} Previous</span><b>{e(prev_r["title"])}</b></a>'
             f'<a href="{rel_url(next_r)}" rel="next"><span class="up">Next {icon("right")}</span><b>{e(next_r["title"])}</b></a>'
             '</div></nav>') if len(RELEASES) > 1 else ""
    main = (
        '<section class="sec release page" aria-labelledby="release-title">'
        + f'<div class="sleeve"><div class="rec" aria-hidden="true">{circle(C["orange"], ref=True)}</div>'
        + picture(rel, "cover", "(min-width:60rem) 42rem, calc(100vw - 2rem)").replace(' loading="lazy"', ' fetchpriority="high"') + '</div><div class="relinfo">'
        + crumbs_html(crumbs)
        + f'<h1 class="title words load{fit_cls(rel["title"])}" id="release-title">{words(rel["title"])}</h1>'
        + f'<p class="by">{by_links(rel)}</p>'
        + f'<p class="meta up">{e(rel["type"])} · <time datetime="{rel["date"]}">{fmt_date(rel["date"])}</time> · {e(L["name"])}</p>'
        + listen_list(rel) + player(rel)
        + f'<p class="credit">“{t}” is a {e(rel["type"].lower())} by {by_links(rel)}, released on {fmt_date(rel["date"])} by '
        + f'<a href="/">{e(L["name"])}</a>, the independent record label created by <a href="{artist_url(CB_ARTIST)}">{e(CB["name"])}</a>.'
        + (f' UPC {e(rel["upc"])}.' if rel.get("upc") else "") + '</p>'
        + '</div></section>'
        + pager
        + (f'<section class="sec" aria-labelledby="press-h">{section_head("In the press", "Press", "", "press-h")}{news_list(press)}</section>' if press else "")
        + (f'<section class="sec" aria-labelledby="more-h">{section_head("Catalog", "More releases", "", "more-h")}'
           f'<ul class="grid stagger">{"".join(release_card(r) for r in others)}</ul></section>' if others else "")
    )
    return shell(title, desc, path, main, graph, cur="release" if rel is R else "catalog",
                 image=rel["image"]["jpg"]["1200"], og_type="music.album", image_alt=rel["image"]["alt"])


# ---------------------------------------------------------------- artists

def artists_page():
    path = "/artists/"
    title = f"Artists | {L['name']}"
    desc = f"Artists who have taken part in {L['name']} projects: {NAMES}. Profiles, releases and official links."
    crumbs = [(L["name"], "/"), ("Artists", path)]
    main = (f'<section class="sec page" aria-labelledby="page-h">{crumbs_html(crumbs)}'
            + section_head("Artist pool", "Artists", f"{len(ARTISTS)} artists have taken part in {e(L['name'])} projects. They are not exclusively signed to the label. Open a profile for releases, press and official links.", "page-h", level="h1")
            + f'<ul class="roster stagger">{"".join(artist_card(a, "h2") for a in ARTISTS)}</ul></section>')
    graph = [page_ld(path, title, desc, "CollectionPage", about={"@id": f"{D}/#label"}, breadcrumb=crumbs_ld(crumbs),
                     mainEntity={"@type": "ItemList", "numberOfItems": len(ARTISTS), "itemListElement": [
                         {"@type": "ListItem", "position": k, "url": f"{D}{artist_url(a)}", "item": {"@id": a["id"]}}
                         for k, a in enumerate(ARTISTS, 1)]}), LABEL_REF] + [
        {"@type": "MusicGroup", "@id": a["id"], "name": a["name"], "url": a["url"], "genre": a.get("genre"),
         "sameAs": list(dict.fromkeys([a["url"]] + a.get("sameAs", [])))} for a in ARTISTS]
    return shell(title, desc, path, main, graph, cur="artists")


def artist_page(a):
    path = artist_url(a)
    rels = [r for r in RELEASES if a in rel_artists(r)]
    press = [n for n in NEWS if n.get("artist") == a["name"]]
    founder = CB and a["name"] == CB["name"]
    title = f"{a['name']} | {L['name']}"
    first = a["role"].split(" ")[0]
    role = (first.lower() + a["role"][len(first):]) if first.lower() in ("producer", "lo-fi", "lofi", "singer", "composer", "beatmaker", "rapper", "dj") else a["role"]
    desc = (f"{a['name']}, {role}, "
            + (f"creator of {L['name']}" if founder else f"featured on {L['name']} releases")
            + (f". Releases: {', '.join('“' + r['title'] + '”' for r in rels)}." if rels else ".")
            + " Official links and press.")
    links = [(a.get("linkLabel", "Official website"), a["url"])]
    if founder:
        links.append(("Portfolio", "/portfolio/leadmajor/"))
    links += [(link_name(u), u) for u in a.get("sameAs", []) if u != a["url"]]
    lis = "".join(
        f'<li><a href="{e(u)}"><span class="pf">{e(n)}</span><span class="act up">'
        f'{"Listen" if any(s in u for s in LISTEN_SITES) else "Visit"}<span class="sr"> {e(a["name"])} on {e(n)}</span>'
        f'{icon("right" if u.startswith("/") else "out")}</span></a></li>' for n, u in links)
    img = (f'<img{CENTER if a.get("position") == "50% 50%" else ""} src="{e(a["image"])}" width="800" height="1000" '
           f'alt="{e(a["alt"])}" fetchpriority="high" decoding="async">')
    vid = (f'<video src="{e(a["video"])}" poster="{e(a["image"])}" autoplay muted loop playsinline '
           'preload="metadata" aria-hidden="true"></video>') if a.get("video") else ""
    crumbs = [(L["name"], "/"), ("Artists", "/artists/"), (a["name"], path)]
    others = [x for x in ARTISTS if x is not a]
    meta = [e(a["role"])]
    on_label = "On " + e(L["name"]) + "." 
    main = (
        '<section class="sec page profile" aria-labelledby="page-h">'
        + f'<div class="art tilt portrait">{img}{vid}</div><div>'
        + crumbs_html(crumbs)
        + f'<p class="kick up">{"Founder of " + e(L["name"]) if founder else "Featured on " + e(L["name"]) + " releases"}</p>'
        + f'<h1 class="words load{" long" if len(a["name"]) > 6 else ""}" id="page-h">{words(a["name"])}</h1>'
        + f'<p class="role">{" · ".join(meta)}</p>'
        + (f'<p class="meta up">{len(rels)} release{"s" if len(rels) != 1 else ""} on {e(L["name"])}'
           + (f' · {len(press)} press article{"s" if len(press) != 1 else ""}' if press else "") + '</p>' if rels else '<div class="meta"></div>')
        + f'<ul class="listen" aria-label="{e(a["name"])} links">{lis}</ul></div></section>'
        + (f'<section class="sec" aria-labelledby="rel-h">{section_head("Discography", "Releases", on_label, "rel-h")}'
           f'<ul class="grid stagger">{"".join(release_card(r) for r in rels)}</ul></section>' if rels else "")
        + (f'<section class="sec" aria-labelledby="press-h">{section_head("In the press", "Press", "", "press-h")}{news_list(press)}</section>' if press else "")
        + (f'<section class="sec" aria-labelledby="oth-h">{section_head("Artist pool", "More artists", e(POOL_TXT), "oth-h")}'
           f'<ul class="roster stagger">{"".join(artist_card(x) for x in others)}</ul></section>' if others else "")
    )
    person = clean({"@type": "MusicGroup", "@id": a["id"], "name": a["name"], "url": a["url"], "description": a["role"],
                    "image": a["image"] if a["image"].startswith("http") else f"{D}{a['image']}", "genre": a.get("genre"),
                    "sameAs": list(dict.fromkeys([a["url"]] + a.get("sameAs", []) + ([f"{D}/portfolio/leadmajor/"] if founder else []))),
                    "album": [{"@id": f"{D}{rel_url(r)}#album"} for r in rels] or None})
    graph = [page_ld(path, title, desc, "ProfilePage", mainEntity={"@id": a["id"]}, breadcrumb=crumbs_ld(crumbs)),
             person, LABEL_REF] + [album_node(r) for r in rels]
    return shell(title, desc, path, main, graph, cur="artists",
                 image=a["image"] if a["image"].startswith("http") else f"{D}{a['image']}", og_type="profile", image_alt=a["alt"])


# ---------------------------------------------------------------- news / contact / 404

def news_page():
    path = "/news/"
    title = f"News & Press | {L['name']}"
    desc = f"News and press coverage of {L['name']} and its artists {NAMES}: reviews, features and release announcements."
    arts = {a["name"]: a for a in ARTISTS}
    items = []
    for i, n in enumerate(NEWS, 1):
        art = {"@type": "Article", "headline": n["title"], "url": n["url"], "datePublished": n["date"],
               "publisher": {"@type": "Organization", "name": n["outlet"]},
               "author": {"@type": "Person", "name": n["author"]} if n.get("author") else None,
               "about": {"@id": arts[n["artist"]]["id"]} if n["artist"] in arts else {"@type": "MusicGroup", "name": n["artist"]}}
        items.append({"@type": "ListItem", "position": i, "item": art})
    crumbs = [(L["name"], "/"), ("News", path)]
    main = (f'<section class="sec page" aria-labelledby="page-h">{crumbs_html(crumbs)}'
            + section_head("In the press", "News", f"Press coverage, reviews and features about {e(L['name'])} artists. Links open the original articles.", "page-h", level="h1")
            + news_list(NEWS, "h2") + '</section>')
    graph = [page_ld(path, title, desc, "CollectionPage", about={"@id": f"{D}/#label"}, breadcrumb=crumbs_ld(crumbs),
                     mainEntity={"@type": "ItemList", "itemListElement": items}), LABEL_REF]
    return shell(title, desc, path, main, graph, cur="news")


def contact_page():
    path = "/contact/"
    title = f"Contact | {L['name']}"
    desc = f"Contact {L['name']}, the independent record label created by {CB['name']}: {L['contact']}."
    crumbs = [(L["name"], "/"), ("Contact", path)]
    links = "".join(f'<li><a href="{e(u)}">{link_name(u)} {icon("out")}</a></li>' for u in L["sameAs"])
    main = (f'<section class="sec page" aria-labelledby="page-h">{crumbs_html(crumbs)}'
            + section_head("Get in touch", "Contact", f"Press, partnerships or questions about {e(L['name'])} and its artists: write to us.", "page-h", level="h1")
            + f'<div class="mailbox reveal"><a class="big-mail" href="mailto:{L["contact"]}">{L["contact"]}</a>'
            + f'<button class="btn up magnet" type="button" data-copy="{L["contact"]}"><span>Copy address</span></button></div></section>'
            + f'<section class="sec about reveal" aria-labelledby="about-h"><div><p class="kick up">The label</p><h2 id="about-h" class="sr">About {e(L["name"])}</h2>'
            + f'<p>{e(L["intro"])} {e(ROSTER_TXT)}</p></div><div class="seal" aria-hidden="true">{circle(C["choco"], ref=True)}</div></section>'
            + submit_cta("Artists")
            + f'<section class="sec" aria-labelledby="else-h">{section_head("Elsewhere", "Follow", "", "else-h")}<ul class="links-big stagger">{links}</ul></section>')
    graph = [page_ld(path, title, desc, "ContactPage", about={"@id": f"{D}/#label"}, breadcrumb=crumbs_ld(crumbs)),
             dict(LABEL_REF, email=L["contact"], contactPoint={"@type": "ContactPoint", "email": L["contact"], "contactType": "customer support"})]
    return shell(title, desc, path, main, graph, cur="contact", cta=False)


def submit_cta(kick="Demo submissions"):
    return ('<section class="sec cta-band reveal" aria-labelledby="cta-h">'
            f'<div><p class="kick up">{e(kick)}</p><h2 class="words" id="cta-h">{words("Send us your music")}</h2></div>'
            f'<div class="cta-side"><p>Made something you think fits {e(L["name"])}? Share a link, your profiles and a few words about the track.</p>'
            f'<a class="btn up fill magnet" href="/submit/">Submit a track {icon("right")}</a></div></section>')


def field(name, label, kind="text", hint="", placeholder="", extra="", plat=False):
    ph = f' placeholder="{e(placeholder)}"' if placeholder else ""
    tag = f'<span class="plat" data-plat="{name}" aria-hidden="true"></span>' if plat else ""
    hid = f"f-{name}"
    desc = f' aria-describedby="{hid}-h {hid}-e"' if hint else f' aria-describedby="{hid}-e"'
    if kind == "textarea":
        ctl = f'<textarea id="{hid}" name="{name}"{ph}{desc}{extra}></textarea>'
    else:
        ctl = f'<input id="{hid}" name="{name}" type="{kind}"{ph}{desc}{extra}>'
    return (f'<div class="field"><div class="lab"><label for="{hid}">{e(label)}</label>{tag}</div>{ctl}'
            + (f'<small id="{hid}-h">{hint}</small>' if hint else "")
            + f'<span class="err" id="{hid}-e"></span></div>')


def submit_page():
    path = "/submit/"
    api = S.get("submit_api", "")
    title = f"Submit your music | {L['name']}"
    desc = (f"Send your music to {L['name']}, the independent record label created by {CB['name']}: "
            "share a listening link, your Instagram, a streaming profile and a few words about the track.")
    crumbs = [(L["name"], "/"), ("Submit", path)]
    req = ' required'
    steps = (
        '<ol class="stagger">'
        '<li><b>01</b><strong>Your music</strong><span>A link we can listen to and its genre. Private SoundCloud, Dropbox or Google Drive links work.</span></li>'
        '<li><b>02</b><strong>About you</strong><span>Your artist name, an e-mail to reply to, your Instagram and one streaming profile.</span></li>'
        '<li><b>03</b><strong>The story</strong><span>A few lines about the track: the vibe, who made it, where it is headed.</span></li>'
        '</ol>')
    form = (
        f'<form class="subform reveal" id="subform" data-api="{e(api)}" novalidate aria-labelledby="page-h">'
        '<fieldset><legend><i>01</i> Your music</legend>'
        + field("title", "Track title", extra=req + ' maxlength="120" autocomplete="off"')
        + ('<div class="field genre-wrap"><div class="lab"><span class="lbl" id="f-genre-l">Genre</span></div>'
           '<div class="genres" role="radiogroup" aria-labelledby="f-genre-l" aria-describedby="f-genre-e">'
           + "".join(f'<label class="pill"><input type="radio" name="genre" value="{e(g)}" required><span>{e(g)}</span></label>' for g in GENRES + ["Other"])
           + '</div><span class="err" id="f-genre-e"></span></div>')
        + field("track", "Listening link", "url", "Make sure the link opens without an account or password.",
                "https://soundcloud.com/…", req + ' maxlength="500" inputmode="url" autocomplete="off"', plat=True)
        + '</fieldset>'
        '<fieldset><legend><i>02</i> About you</legend><div class="two">'
        + field("artist", "Artist name", extra=req + ' maxlength="80" autocomplete="nickname"')
        + field("email", "E-mail", "email", "", "you@example.com", req + ' maxlength="120" autocomplete="email" inputmode="email"')
        + '</div><div class="two">'
        + field("instagram", "Instagram", "text", "", "@yourname", req + ' maxlength="120" autocomplete="off" autocapitalize="off" spellcheck="false"')
        + field("profile", "Streaming profile", "url", "Spotify, Apple Music, SoundCloud, Deezer…",
                "https://open.spotify.com/artist/…", req + ' maxlength="500" inputmode="url" autocomplete="off"', plat=True)
        + '</div></fieldset>'
        '<fieldset><legend><i>03</i> The story</legend>'
        + field("about", "Description", "textarea", '<span class="count-c" aria-live="off">0 / 1500</span>',
                "Tell us about the track and about you.", req + ' minlength="20" maxlength="1500" rows="6"')
        + '<div class="check-wrap"><label class="check"><input type="checkbox" name="rights" required aria-describedby="f-rights-e">'
        '<span>I own or control the rights to this music.</span></label><span class="err" id="f-rights-e"></span></div>'
        '</fieldset>'
        '<div class="hp" aria-hidden="true"><label>Leave this empty <input name="website" tabindex="-1" autocomplete="off"></label></div>'
        f'<p class="privacy">Your details are only used by {e(L["name"])} to listen to your submission and reply to you. '
        f'Your track stays yours: nothing is used without your written agreement. <a href="/legal/">Submissions &amp; privacy</a>.</p>'
        f'<button class="btn up fill magnet send" type="submit"><span>Send submission</span> {icon("right")}</button>'
        '<p class="form-msg" role="alert"></p></form>'
        '<div class="done" id="sub-done" hidden tabindex="-1">'
        '<span class="tick" aria-hidden="true"><svg viewBox="0 0 24 24" width="24" height="24"><path fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" d="m5 12.5 4.5 4.5L19 7.5"/></svg></span>'
        '<h2>Thanks, <span data-name></span>.</h2>'
        f'<p>Your track is in. If it is a fit for {e(L["name"])}, we will reply by e-mail.</p>'
        f'<p class="more"><button class="btn up" type="button" data-again>Send another track</button><a class="btn up" href="/catalog/">Explore the catalog</a></p></div>'
        f'<noscript><p class="lead">This form needs JavaScript. You can also e-mail your link to <a href="mailto:{L["contact"]}">{L["contact"]}</a>.</p></noscript>')
    main = (f'<section class="sec page" aria-labelledby="page-h">{crumbs_html(crumbs)}'
            + section_head("Demo submissions", "Submit",
                           f"Send your music to {e(L['name'])}. We release {e(GENRE_TXT)}. Fill in the form below: it takes about two minutes.", "page-h", level="h1")
            + f'<div class="subgrid"><aside class="steps" aria-label="What we need">{steps}'
            f'<p class="mute">Prefer e-mail? Write to <a href="mailto:{L["contact"]}">{L["contact"]}</a>.</p></aside>'
            + f'<div>{form}</div></div></section>')
    graph = [page_ld(path, title, desc, about={"@id": f"{D}/#label"}, breadcrumb=crumbs_ld(crumbs)), LABEL_REF]
    return shell(title, desc, path, main, graph, cur="submit", cta=False)


def legal_page():
    path = "/legal/"
    G = S.get("legal", {})
    months = G.get("retention_months", 12)
    title = f"Legal notice & privacy | {L['name']}"
    desc = (f"Legal notice for {L['name']}, how the label handles the details sent through the site, "
            "and what happens to the music you send through the submission form.")
    crumbs = [(L["name"], "/"), ("Legal", path)]
    rows = [("Publisher", e(G.get("entity", L["name"]))),
            ("Legal form", e(G.get("form", ""))),
            ("SIREN", e(G.get("siren", ""))),
            ("Trade register", e(G.get("rcs", ""))),
            ("Business code", e(G.get("ape", ""))),
            ("Contact", f'<a href="mailto:{L["contact"]}">{L["contact"]}</a>'),
            ("Hosting", e(G.get("host", "")))]
    table = "".join(f'<div><dt class="up">{k}</dt><dd>{v}</dd></div>' for k, v in rows if v)
    main = (
        f'<section class="sec page" aria-labelledby="page-h">{crumbs_html(crumbs)}'
        + section_head("Legal", "Legal notice",
                       "Who runs this site, what we do with the details you send us, and what happens to the music you submit.",
                       "page-h", level="h1")
        + f'<dl class="facts reveal">{table}</dl></section>'
        # ---- submissions
        + '<section class="sec prose reveal" aria-labelledby="sub-h">'
        + f'<p class="kick up">Music submissions</p><h2 id="sub-h">Your music stays yours</h2>'
        + f'<p>Tracks sent through <a href="/submit/">the submission form</a> are kept for one reason only: so that {e(L["name"])} '
        'can listen to them and talk about them internally.</p>'
        + '<ul class="bullets">'
        '<li>Nothing is published, released, remixed, sampled, used in a playlist or shared outside the label until we have '
        'talked with you and you have given your written agreement.</li>'
        '<li>You keep every right on your music. Sending a track gives us no licence and no exclusivity.</li>'
        f'<li>Submissions we do not follow up on are deleted after {months} months, and sooner if you ask.</li>'
        f'<li>You can ask us to delete your submission at any time by writing to <a href="mailto:{L["contact"]}">{L["contact"]}</a>.</li>'
        '</ul></section>'
        # ---- privacy
        + '<section class="sec prose reveal" aria-labelledby="priv-h">'
        + '<p class="kick up">Privacy</p><h2 id="priv-h">Your details</h2>'
        + '<p>The submission form asks for your artist name, e-mail address, Instagram handle, a streaming profile, '
        'a listening link and a short description. We use them to listen to your track and to reply to you. '
        'Nothing is sold, shared with third parties or used for advertising.</p>'
        + '<ul class="bullets">'
        '<li><strong>Where it is stored:</strong> a private Google Sheet and the label mailbox, both on Google Workspace. '
        'Only the label has access.</li>'
        f'<li><strong>How long:</strong> {months} months for submissions we do not follow up on. If we work together, '
        'the messages are kept as part of that relationship.</li>'
        f'<li><strong>Your rights:</strong> you can ask for a copy, a correction or the deletion of your details at '
        f'<a href="mailto:{L["contact"]}">{L["contact"]}</a>. You can also complain to the CNIL (cnil.fr).</li>'
        '<li><strong>No tracking:</strong> this site has no analytics, no advertising and no tracking cookies. '
        'Fonts and images are served from the site itself.</li>'
        '<li><strong>Embedded players:</strong> Spotify players only load when you click Play. From that moment Spotify '
        'receives your IP address and may set its own cookies, under its own policy.</li>'
        '<li><strong>Hidden game:</strong> if you send a score to the duck game scoreboard, the name you type and your '
        'score are shown publicly on that page. Pick a nickname if you prefer.</li>'
        '<li><strong>Server logs:</strong> the host keeps standard technical logs of page requests, as any web server does.</li>'
        '</ul></section>'
        # ---- content
        + '<section class="sec prose reveal" aria-labelledby="ip-h">'
        + '<p class="kick up">Content</p><h2 id="ip-h">Music, artwork and names</h2>'
        + f'<p>Recordings, artwork, photos, logos and texts on this site belong to {e(L["name"])}, to its artists or to '
        'their respective owners, and cannot be reused without permission. If you think something here should not be '
        f'online, write to <a href="mailto:{L["contact"]}">{L["contact"]}</a> and we will take a look.</p>'
        + f'<p class="mute up">Last updated {fmt_date(G.get("updated", TODAY))}</p></section>')
    graph = [page_ld(path, title, desc, about={"@id": f"{D}/#label"}, breadcrumb=crumbs_ld(crumbs)), LABEL_REF]
    return shell(title, desc, path, main, graph, cur="legal", cta=False, robots="index,follow")


def notfound():
    return (head(f"Page not found – {L['name']}", "This page does not exist.", canonical=False, robots="noindex")
            + '</head><body>' + SYMBOLS + top()
            + '<main class="nf" id="main">'
            + f'<div class="seal" aria-hidden="true">{circle(C["orange"])}</div>'
            + '<p class="up or">Error 404</p><h1>Page not found</h1>'
            + f'<p class="cta"><a class="btn up fill" href="/">Back to {e(L["name"])}</a><a class="btn up" href="/catalog/">Catalog</a></p></main></body></html>\n')


def images():
    import cairosvg
    from PIL import Image
    fav = circle(C["orange"])
    (DIST / "favicon.svg").write_text(fav + "\n")
    def png(svg, w, h=None):
        return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=w, output_height=h or w))).convert("RGBA")
    png(fav, 32).save(DIST / "favicon.ico", sizes=[(32, 32)])
    at = Image.new("RGB", (180, 180), C["ink"]); at.paste(png(circle(C["orange"]), 150), (15, 15), png(circle(C["orange"]), 150)); at.save(DIST / "apple-touch-icon.png", optimize=True)
    png(circle(C["choco"]), 512).save(DIST / "logo.png", optimize=True)
    og = Image.new("RGB", (1200, 630), C["ink"])
    lk = png(lockup("", C["orange"], C["white"]).replace('<svg class=""', '<svg'), 960, round(960 * 1028 / 3344))
    og.paste(lk, (120, (630 - lk.height) // 2), lk)
    og.save(DIST / "og.png", optimize=True)


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    pages = {"/": index(), "/catalog/": catalog_page(), "/artists/": artists_page(), "/contact/": contact_page(), "/submit/": submit_page(), "/legal/": legal_page()}
    if NEWS:
        pages["/news/"] = news_page()
    for rel in RELEASES:
        pages[rel_url(rel)] = release_page(rel)
    for a in ARTISTS:
        pages[artist_url(a)] = artist_page(a)
    for path, doc in pages.items():
        out = DIST / path.strip("/")
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(doc, encoding="utf-8")
    (DIST / "404.html").write_text(notfound(), encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {D}/sitemap.xml\n")
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{D}{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in pages)
        + "</urlset>\n")
    (DIST / "CNAME").write_text(D.split("://")[1] + "\n")
    (DIST / ".nojekyll").write_text("")
    shutil.copytree(ROOT / "fonts", DIST / "fonts")
    shutil.copytree(ROOT / "js", DIST / "js")
    if (ROOT / "img").exists():
        shutil.copytree(ROOT / "img", DIST / "img")
    images()
    try:
        import portfolio.portfolio as pf
        extra = pf.build(DIST, D)
    except Exception as err:  # the label site must deploy even if the portfolio fails
        import traceback
        traceback.print_exc()
        print("::warning::portfolio build failed:", err)
        extra = []
    try:
        import duck
        duck.build(DIST, S.get("duck_api", ""))
    except Exception as err:
        print("::warning::duck page failed:", err)
    if extra:
        sm = DIST / "sitemap.xml"
        sm.write_text(sm.read_text().replace("</urlset>", "".join(f"  <url><loc>{D}{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in extra) + "</urlset>"))
    for f in sorted(DIST.rglob("*")):
        if f.is_file():
            print(f"{f.stat().st_size:>8}  {f.relative_to(DIST)}")


if __name__ == "__main__":
    main()
