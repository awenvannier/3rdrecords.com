#!/usr/bin/env python3
"""Build 3rdrecords.com into ./dist from site.json.

New release: edit the "release" block in site.json (links, date, cover base URL).
Covers and artist photos are served from the artist's own website (djouher.com).
Logos live in assets/*.svg (vector traces of the official 3rd Records marks).
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
NAMES = ", ".join(a["name"] for a in ARTISTS[:-1]) + " and " + ARTISTS[-1]["name"]
TITLE = f"{L['name']} | Independent Record Label"
DESC = (f"{L['name']} is an independent record label created by {CB['name']}, with {NAMES}. "
        f"Latest release: “{R['title']}” by {R['artist']}".rstrip(".") + ".")
ROSTER_TXT = f"The roster includes {NAMES}, and the catalog counts {len(RELEASES)} releases so far."


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


def lockup(cls, mark_fill, word_fill, label=None):
    """3RD mark + 'records' wordmark side by side (viewBox 3344x1028)."""
    a = f' role="img" aria-label="{e(label)}"' if label else ' aria-hidden="true"'
    return (f'<svg class="{cls}" viewBox="0 0 3344 1028" xmlns="http://www.w3.org/2000/svg"{a} focusable="false">'
            f'<g class="duck"><path fill="{mark_fill}" transform="{MARK[1]}" d="{MARK[2]}"/></g>'
            f'<g transform="translate(1660 0)"><path fill="{word_fill}" transform="{RECORDS[1]}" d="{RECORDS[2]}"/></g></svg>')


def circle(fill, mark="#FEFEFE", size=None, ref=False):
    """Round 3RD logo. ref=True reuses the <symbol id="cm"> defined once in the page."""
    wh = f' width="{size}" height="{size}"' if size else ""
    inner = (f'<use href="#cm" fill="{mark}"/>' if ref else
             f'<path fill="{mark}" transform="{CMARK[1]}" d="{CMARK[2]}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2800 2800"{wh}>'
            f'<circle cx="1400" cy="1400" r="1400" fill="{fill}"/>{inner}</svg>')


SYMBOLS = ('<svg class="sr" aria-hidden="true" focusable="false"><symbol id="cm" viewBox="0 0 2800 2800">'
           f'<path transform="{CMARK[1]}" d="{CMARK[2]}"/></symbol></svg>')


CSS = """
@font-face{font-family:Avigea;src:url(/fonts/avigea.woff2) format("woff2");font-display:swap}
@font-face{font-family:Roboto;src:url(/fonts/roboto-regular.woff2) format("woff2");font-weight:400;font-display:swap}
@font-face{font-family:Roboto;src:url(/fonts/roboto-medium.woff2) format("woff2");font-weight:500;font-display:swap}
:root{--choco:#512321;--orange:#F6A10E;--ink:#1D1D1B;--white:#FEFEFE;--grey:#9E9E9E;--line:rgba(254,254,254,.16);--d:Avigea,"Cooper Black",Georgia,serif;--pad:clamp(1rem,4vw,2.5rem);color-scheme:dark}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--ink);color:var(--white);font:400 1rem/1.6 Roboto,"Helvetica Neue",Arial,system-ui,sans-serif;-webkit-font-smoothing:antialiased;padding-bottom:3.5rem}
a{color:inherit}
a:focus-visible{outline:2px solid var(--orange);outline-offset:4px}
img,svg{display:block;max-width:100%;height:auto}
h1,h2,h3{margin:0;font-family:var(--d);font-weight:400;line-height:.95;letter-spacing:-.01em}
ul{list-style:none;margin:0;padding:0}
.up{font-size:.6875rem;font-weight:500;letter-spacing:.24em;text-transform:uppercase}
.or{color:var(--orange)}
.skip{position:absolute;left:var(--pad);top:-4rem;z-index:9;background:var(--orange);color:var(--ink);padding:.6rem 1rem}
.skip:focus{top:1rem}
.top{position:absolute;inset:0 0 auto;z-index:2;display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:1.25rem var(--pad)}
.brand{display:block;width:2.75rem;flex:none}
.top nav{display:flex;gap:clamp(1rem,3vw,2.75rem)}
.top nav a,.bar a{text-decoration:none;padding:.5rem 0}
.top nav a:hover,.bar a:hover,.follow a:hover{color:var(--orange)}
.hero{position:relative;background:var(--ink);min-height:calc(100vh - 3.5rem);min-height:calc(100svh - 3.5rem);display:flex;flex-direction:column;justify-content:center;overflow:hidden;isolation:isolate}
.hero::before{content:"";position:absolute;z-index:-1;width:70vmax;aspect-ratio:1;left:50%;top:40%;border-radius:50%;background:radial-gradient(circle,rgba(246,161,14,.22),rgba(246,161,14,0) 62%);transform:translate(-50%,-50%);animation:glow 7s ease-in-out infinite alternate}
.hero-in{flex:1;align-content:center;padding:6rem var(--pad) 2.5rem;display:grid;gap:clamp(1.5rem,4vh,2.5rem);justify-items:center;text-align:center;width:100%;max-width:84rem;margin:0 auto}
.stage{position:relative;width:min(72vw,26rem);aspect-ratio:1}
.disc{position:absolute;inset:0;border-radius:50%;background:radial-gradient(circle,#0c0c0b 0 31%,transparent 31.2%),repeating-radial-gradient(circle,#131312 0 1.5px,#262624 1.6px 3.2px);box-shadow:0 1.5rem 4rem rgba(0,0,0,.55),inset 0 0 0 .35rem #0c0c0b;animation:spin 5s linear infinite}
.disc svg{position:absolute;inset:32%;width:36%}
.disc::after{content:"";position:absolute;left:50%;top:50%;width:2.2%;aspect-ratio:1;border-radius:50%;background:var(--ink);transform:translate(-50%,-50%)}
.sheen{position:absolute;inset:0;border-radius:50%;background:conic-gradient(from 30deg,transparent 0 8%,rgba(255,255,255,.09) 12%,transparent 18% 58%,rgba(255,255,255,.07) 62%,transparent 68%);pointer-events:none}
.arm{position:absolute;right:-6%;top:-4%;width:34%;height:62%;transform-origin:85% 8%;transform:rotate(22deg);animation:arm 5s ease-in-out infinite alternate}
.arm::before{content:"";position:absolute;right:10%;top:0;width:1.1rem;aspect-ratio:1;border-radius:50%;background:var(--grey);box-shadow:0 0 0 .35rem #3a3a38}
.arm::after{content:"";position:absolute;right:calc(10% + .45rem);top:.55rem;width:.22rem;height:92%;background:linear-gradient(var(--grey),#cfcfcf);border-radius:.2rem;box-shadow:-.15rem 0 0 rgba(0,0,0,.25)}
.hero h1{width:min(100%,46rem)}
.lockup{width:100%;overflow:visible}
.duck{transform-box:fill-box;transform-origin:50% 90%;animation:bob 2.4s ease-in-out infinite}
.rise{animation:rise .9s cubic-bezier(.2,.7,.2,1) both}
.rise.d2{animation-delay:.12s}.rise.d3{animation-delay:.24s}
.tag{margin:0;color:var(--grey)}
.cta{margin:0;display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:.75rem 1.5rem}
.btn{display:inline-flex;align-items:center;gap:.75em;min-height:2.875rem;padding:0 1.4rem;border:1px solid currentColor;border-radius:999px;text-decoration:none;transition:background .2s,color .2s,border-color .2s,transform .2s}
.btn:hover{background:var(--orange);border-color:var(--orange);color:var(--ink);transform:translateY(-2px)}
.ticker{overflow:hidden;border-block:1px solid var(--line);padding:.9rem 0;white-space:nowrap}
.ticker div{display:inline-flex;animation:tick 32s linear infinite}
.ticker span{font:400 clamp(1.75rem,4vw,2.75rem)/1 var(--d);padding-right:2.5rem;display:inline-flex;align-items:center;gap:2.5rem}
.ticker span::after{content:"";width:.6em;aspect-ratio:1;border-radius:50%;background:var(--orange)}
.ticker b{font-weight:400;color:var(--orange)}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes bob{0%,100%{transform:rotate(0) translateY(0)}30%{transform:rotate(-4deg) translateY(-2%)}60%{transform:rotate(2deg) translateY(0)}}
@keyframes glow{from{opacity:.55;transform:translate(-50%,-50%) scale(.9)}to{opacity:1;transform:translate(-50%,-50%) scale(1.08)}}
@keyframes arm{from{transform:rotate(20deg)}to{transform:rotate(24deg)}}
@keyframes rise{from{opacity:0;transform:translateY(1.25rem)}to{opacity:1;transform:none}}
@keyframes tick{to{transform:translateX(-50%)}}
@keyframes slide{from{transform:translateX(0) rotate(0)}to{transform:translateX(40%) rotate(90deg)}}
.sec{max-width:84rem;margin:0 auto;padding:clamp(4.5rem,12vw,8rem) var(--pad) 0}
.kick{margin:0 0 .9rem;color:var(--orange)}
.release{display:grid;gap:clamp(2rem,5vw,4.5rem)}
.sleeve{position:relative;margin-right:30%}.sleeve picture{position:relative;z-index:1;display:block;box-shadow:0 1.5rem 3rem rgba(0,0,0,.5)}.cover{width:100%;aspect-ratio:1;background:var(--choco)}.rec{position:absolute;inset:3%;border-radius:50%;background:radial-gradient(circle,#0c0c0b 0 31%,transparent 31.2%),repeating-radial-gradient(circle,#131312 0 1.5px,#262624 1.6px 3.2px);box-shadow:inset 0 0 0 1px #3a3a38,0 1rem 2rem rgba(0,0,0,.5);animation:slide 1.2s .3s cubic-bezier(.2,.7,.2,1) both;transition:transform .6s}.rec svg{position:absolute;inset:32%;width:36%}.release:hover .rec{transform:translateX(46%) rotate(160deg)}
.title{font-size:clamp(3.5rem,11vw,8rem)}
.by{margin:.5rem 0 0;font:400 clamp(1.5rem,3.5vw,2.25rem)/1.1 var(--d)}
.by a{text-decoration-thickness:1px;text-underline-offset:.2em}
.by a:hover,.title a:hover{color:var(--orange)}
.title a{text-decoration:none}
.crumbs{list-style:none;padding:0;display:flex;flex-wrap:wrap;gap:.5rem;margin:0 0 1rem;color:var(--grey)}.crumbs a{text-decoration:none}.crumbs a:hover{color:var(--orange)}.crumbs li+li::before{content:"/";margin-right:.5rem}
.page{padding-top:7rem}
.news{margin-top:2.5rem;border-top:1px solid var(--line)}.news li{border-bottom:1px solid var(--line)}.news a{display:grid;gap:.5rem;padding:1.5rem 0;text-decoration:none}.news h3{font-size:clamp(1.5rem,3.2vw,2.25rem);line-height:1.05;transition:color .2s}.news a:hover h3{color:var(--orange)}.news p{margin:0;max-width:44em;color:#e9e6e1}.news .up{color:var(--grey)}.more{margin:2rem 0 0}
.lead{margin:1.5rem 0 0;max-width:36em;font-size:clamp(1.125rem,2.1vw,1.375rem);color:#e9e6e1}
.credit{margin:2.5rem 0 0;max-width:34em;color:#e9e6e1}
.meta{margin:1rem 0 2.25rem;color:var(--grey)}
.listen{border-top:1px solid var(--line)}
.listen a{display:flex;justify-content:space-between;align-items:center;gap:1rem;min-height:4rem;border-bottom:1px solid var(--line);text-decoration:none}
.pf{font:400 clamp(1.5rem,3.4vw,2.125rem)/1 var(--d);transition:color .2s}
.act{color:var(--grey);white-space:nowrap}
.listen a:hover .pf{color:var(--orange)}
.listen a:hover .act{color:var(--white)}
.sec>h2,.foot h2{font-size:clamp(3rem,8vw,5.5rem)}
.roster{display:grid;gap:1.5rem;margin-top:2.5rem}.cat{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,13rem),1fr));gap:2rem 1.5rem;margin-top:2.5rem}.cat a{display:block;text-decoration:none}.cat img{width:100%;aspect-ratio:1;background:var(--choco);transition:transform .4s}.cat a:hover img{transform:rotate(-2deg) scale(1.02)}.cat h3{font-size:clamp(1.5rem,3vw,2rem);margin-top:.9rem}.cat p{margin:.35rem 0 0;color:var(--grey)}.cat a:hover h3{color:var(--orange)}
.artist{position:relative;display:block;background:var(--choco);text-decoration:none;overflow:hidden}
.artist img{width:100%;aspect-ratio:4/5;object-fit:cover;object-position:50% 58%;transition:transform .5s}.artist img.c{object-position:50% 50%}
.artist div{position:absolute;z-index:1;inset:auto 0 0;padding:1.25rem 1.25rem 1.1rem;background:linear-gradient(to top,rgba(29,29,27,.92),rgba(29,29,27,0))}
.artist h3{font-size:clamp(2.5rem,6vw,3.75rem)}
.artist p{margin:.4rem 0 0;color:var(--orange)}
.artist:hover img,.artist:hover video{transform:scale(1.03)}.artist video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transition:transform .5s}.tag{display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:.5rem}.lm{width:1.5rem;height:1.5rem;animation:spin 12s linear infinite}
.about{display:grid;gap:1.5rem;align-items:center}
.about p:not(.kick){margin:0;max-width:30em;font-size:clamp(1.125rem,2.1vw,1.5rem);line-height:1.5;color:#e9e6e1}
.seal{width:min(14rem,40vw)}
.foot{padding-bottom:3rem;display:grid;gap:3rem}
.mail{display:inline-block;margin-top:1.25rem;font:400 clamp(1.5rem,4vw,2.5rem)/1.2 var(--d);text-underline-offset:.2em;text-decoration-thickness:1px;overflow-wrap:anywhere}
.mail:hover{color:var(--orange)}
.follow{display:flex;flex-wrap:wrap;gap:.25rem 1.75rem;margin-top:1.25rem}
.follow a{font:400 clamp(1.5rem,4vw,2.25rem)/1.3 var(--d);text-decoration:none}
.legal{grid-column:1/-1;margin:0;padding-top:2rem;border-top:1px solid var(--line);color:var(--grey)}
.bar{position:fixed;inset:auto 0 0;z-index:5;display:flex;align-items:center;gap:1rem;min-height:3.5rem;padding:0 var(--pad);background:var(--ink);border-top:1px solid var(--line)}
.bar b{font-weight:500;display:flex;align-items:center;gap:.6rem}
.bar b::before{content:"";width:.5rem;height:.5rem;border-radius:50%;background:var(--orange)}
.bar i{font-style:normal;color:var(--grey);display:none}
.bar span{margin-left:auto;display:flex;gap:1.25rem}
.nf{min-height:100svh;display:grid;place-content:center;gap:1.5rem;text-align:center;padding:var(--pad)}.nf .seal{animation:spin 5s linear infinite}
.nf h1{font-size:clamp(3.5rem,12vw,8rem)}
.nf .seal{margin:0 auto;width:7rem}
.sr{position:absolute;width:1px;height:1px;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
@media (max-width:39.99rem){.top nav .x{display:none}}
@media (min-width:40rem){.bar i{display:inline}.roster{grid-template-columns:repeat(auto-fill,minmax(18rem,24rem))}}
@media (min-width:60rem){.hero-in{grid-template-columns:minmax(0,5fr) minmax(0,7fr);text-align:left;justify-items:start;align-items:center;column-gap:clamp(2rem,6vw,6rem)}.hero-in .stage{grid-row:1/5;width:min(100%,30rem);justify-self:center}.cta,.tag{justify-content:flex-start}.release{grid-template-columns:minmax(0,1fr) minmax(0,1fr);align-items:end}.about,.foot{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.seal{justify-self:end}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{transition:none!important;animation:none!important}.rec{transform:translateX(40%)}.artist video{display:none}}
""".strip()
CSS = "".join(line.strip() for line in CSS.splitlines())
CSS_HASH = base64.b64encode(hashlib.sha256(CSS.encode()).digest()).decode()
CSP = (f"default-src 'none'; connect-src 'self'; img-src 'self' {' '.join(ORIGINS)}; font-src 'self'; media-src 'self'; "
       f"style-src 'sha256-{CSS_HASH}'; base-uri 'none'; form-action 'none'")


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
        {"@type": "Organization", "@id": lid, "name": L["name"], "url": f"{D}/", "description": L["description"],
         "alternateName": L.get("alternateName"), "disambiguatingDescription": L.get("disambiguatingDescription"),
         "logo": f"{D}/logo.png", "image": f"{D}/og.png", "email": L["contact"], "sameAs": L["sameAs"],
         "founder": {"@id": CB["id"]} if CB else None,
         "subjectOf": [{"@id": f"{D}{rel_url(r)}#album"} for r in RELEASES]},
    ]
    for a in ARTISTS:
        graph.append({"@type": "MusicGroup", "@id": a["id"], "name": a["name"], "url": a["url"],
                      "sameAs": list(dict.fromkeys([a["url"]] + a.get("sameAs", []))), "genre": a.get("genre"), "recordLabel": {"@id": lid}})
    graph += [album_node(rel) for rel in RELEASES]

    return json.dumps({"@context": "https://schema.org", "@graph": [clean(g) for g in graph]},
                      ensure_ascii=False, separators=(",", ":"))


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
          f"<style>{CSS}</style>"]
    return "".join(p)


CENTER = ' class="c"'
SAME_NAMES = {"instagram": "Instagram", "musicbrainz": "MusicBrainz", "discogs": "Discogs", "wikidata": "Wikidata"}


def index():
    t = e(R["title"])
    main_artist = artist_of(R)
    links = "".join(
        f'<li><a href="{e(l["url"])}"><span class="pf">{e(l["name"])}</span>'
        f'<span class="act up">{"Watch" if "watch?v=" in l["url"] else "Listen"}'
        f'<span class="sr">{"" if "watch?v=" in l["url"] else " to"} {t} on {e(l["name"])}</span> ↗</span></a></li>'
        for l in R["links"])
    def card(a):
        img = (f'<img{CENTER if a.get("position") == "50% 50%" else ""} src="{e(a["image"])}" width="800" height="800" '
               f'alt="{e(a["alt"])}" loading="lazy" decoding="async">')
        vid = (f'<video src="{e(a["video"])}" poster="{e(a["image"])}" autoplay muted loop playsinline '
               'preload="metadata" aria-hidden="true"></video>') if a.get("video") else ""
        return (f'<li><a class="artist" href="{e(a["url"])}">{img}{vid}'
                f'<div><h3>{e(a["name"])}</h3><p class="up">{e(a["role"])} · '
                f'{e(a.get("linkLabel", "Official website"))} ↗</p></div></a></li>')
    roster = "".join(card(a) for a in ARTISTS)
    catalog = "".join(
        f'<li id="{rel["slug"]}"><a href="{rel_url(rel)}">{picture(rel, "", "(min-width:40rem) 16rem, 45vw", 640)}'
        f'<h3>{e(rel["title"])}</h3><p class="up">{e(rel["artist"])} · {e(rel["type"])} · <time datetime="{rel["date"]}">{dt.date.fromisoformat(rel["date"]).year}</time></p>'
        '</a></li>'
        for rel in RELEASES)
    first = R["links"][0]
    apple = next((l for l in R["links"] if l["name"] == "Apple Music"), None)
    bar = f'<a href="{e(first["url"])}">{e(first["name"])}</a>' + (f'<a href="{e(apple["url"])}">Apple Music</a>' if apple else "")
    year = max(dt.date.fromisoformat(R["date"]).year, dt.date.today().year)
    items = [f"<b>{t}</b> {e(R['artist'])}", "Out now", e(L["name"]), f"Created by {e(CB['name'])}"]
    TICK = "".join(f"<span>{i}</span>" for i in items * 2)
    return (
        head(TITLE, DESC)
        + f'<script type="application/ld+json">{jsonld()}</script></head><body>'
        + SYMBOLS + '<a class="skip up" href="#release">Skip to the latest release</a>'
        + top()
        + '<main>'
        + '<section class="hero" aria-labelledby="name"><div class="hero-in">'
        + f'<div class="stage rise" aria-hidden="true"><div class="disc">{circle(C["orange"], ref=True)}</div><div class="sheen"></div><div class="arm"></div></div>'
        + f'<h1 id="name" class="rise d2">{lockup("lockup", C["orange"], C["white"])}<span class="sr">{e(L["name"])}</span></h1>'
        + f'<p class="tag up rise d3">Record label · Created by <img class="lm" src="{e(CB["logo"])}" width="24" height="24" alt=""> {e(CB["name"])}</p>'
        + f'<p class="cta rise d3"><span class="up or">New {e(R["type"].lower())} · {e(R["artist"])}</span><a class="btn up" href="#release">Listen to {t}</a></p>'
        + '</div>'
        + '<div class="ticker" aria-hidden="true"><div>' + TICK * 2 + '</div></div></section>'
        + f'<section class="sec release" id="release" aria-labelledby="release-title">'
        + f'<div class="sleeve"><div class="rec" aria-hidden="true">{circle(C["orange"], ref=True)}</div>'
        + picture(R, "cover", "(min-width:60rem) 42rem, calc(100vw - 2rem)") + '</div><div>'
        + '<p class="kick up">Latest release</p>'
        + f'<h2 class="title" id="release-title"><a href="{rel_url(R)}">{t}</a></h2>'
        + f'<p class="by"><a href="{e(main_artist["url"])}">{e(R["artist"])}</a></p>'
        + f'<p class="meta up">{e(R["type"])} · <time datetime="{R["date"]}">{fmt_date(R["date"])}</time> · {e(L["name"])}</p>'
        + f'<ul class="listen" aria-label="Listen to {t}">{links}</ul>'
        + '</div></section>'
        + f'<section class="sec" id="catalog" aria-labelledby="catalog-h"><p class="kick up">Discography</p><h2 id="catalog-h">Catalog</h2><ul class="cat">{catalog}</ul></section>'
        + f'<section class="sec" id="artists" aria-labelledby="artists-h"><p class="kick up">Roster</p><h2 id="artists-h">Artists</h2><ul class="roster">{roster}</ul></section>'
        + (f'<section class="sec" id="news" aria-labelledby="news-h"><p class="kick up">In the press</p><h2 id="news-h">News</h2>'
           + news_list(NEWS[:3]) + '<p class="more"><a class="btn up" href="/news/">All news</a></p></section>' if NEWS else "")
        + f'<section class="sec about" aria-labelledby="about-h"><div><p class="kick up">The label</p><h2 id="about-h" class="sr">About {e(L["name"])}</h2><p>{e(L["intro"])} {e(ROSTER_TXT)}</p></div>'
        + f'<div class="seal" aria-hidden="true">{circle(C["choco"], ref=True)}</div></section>'
        + '</main>'
        + '<footer class="sec foot" id="contact">'
        + f'<div><p class="kick up">Get in touch</p><h2>Contact</h2><a class="mail" href="mailto:{L["contact"]}">{L["contact"]}</a></div>'
        + '<div><p class="kick up">Elsewhere</p><h2 class="sr">Links</h2><ul class="follow">'
        + "".join(f'<li><a href="{e(u)}">{n}</a></li>' for u in L["sameAs"] for k, n in SAME_NAMES.items() if k in u)
        + "".join(f'<li><a href="{e(a["url"])}">{e(a["name"])}</a></li>' for a in ARTISTS)
        + '</ul></div>'
        + f'<p class="legal up">© {year} {e(L["name"])}</p>'
        + '</footer>'
        + f'<aside class="bar up" aria-label="Listen now"><b>Out now</b><i>{e(R["artist"])} — {t}</i><span>{bar}</span></aside>'
        + '</body></html>\n')


def top():
    return (f'<header class="top"><a class="brand" href="/" aria-label="{e(L["name"])} home">{circle(C["orange"], ref=True)}</a>'
            '<nav class="up" aria-label="Sections"><a class="x" href="/#release">Release</a><a href="/#catalog">Catalog</a>'
            '<a href="/#artists">Artists</a><a href="/news/">News</a><a class="x" href="/#contact">Contact</a></nav></header>')


def release_page(rel):
    t = e(rel["title"])
    path = rel_url(rel)
    arts = rel_artists(rel)
    by = rel["artist"]
    by_html = e(by)
    for a in sorted(arts, key=lambda a: -len(a["name"])):
        by_html = re.sub(r"(?<![\w>])" + re.escape(e(a["name"])) + r"(?![\w<])", f'<a href="{e(a["url"])}">{e(a["name"])}</a>', by_html, count=1)
    links = "".join(
        f'<li><a href="{e(l["url"])}"><span class="pf">{e(l["name"])}</span>'
        f'<span class="act up">{"Watch" if "watch?v=" in l["url"] else "Listen"}'
        f'<span class="sr">{"" if "watch?v=" in l["url"] else " to"} {t} on {e(l["name"])}</span> ↗</span></a></li>'
        for l in rel["links"])
    others = [r for r in RELEASES if r is not rel]
    press = [n for n in NEWS if n.get("release") == rel["slug"]]
    more = "".join(
        f'<li><a href="{rel_url(r)}">{picture(r, "", "(min-width:40rem) 16rem, 45vw", 640)}'
        f'<h3>{e(r["title"])}</h3><p class="up">{e(r["artist"])} · {e(r["type"])} · <time datetime="{r["date"]}">{dt.date.fromisoformat(r["date"]).year}</time></p></a></li>'
        for r in others)
    title = f"{rel['title']} – {by} | {L['name']}"
    desc = (f"“{rel['title']}”, the {rel['type'].lower()} by {by}, released on {fmt_date(rel['date'])} by {L['name']}, "
            f"the independent record label created by {CB['name']}. Listen on {', '.join(l['name'] for l in rel['links'][:4])}.")
    crumbs = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": L["name"], "item": f"{D}/"},
        {"@type": "ListItem", "position": 2, "name": "Catalog", "item": f"{D}/#catalog"},
        {"@type": "ListItem", "position": 3, "name": rel["title"], "item": f"{D}{path}"}]}
    page = {"@type": "WebPage", "@id": f"{D}{path}", "url": f"{D}{path}", "name": title, "description": desc,
            "inLanguage": "en", "isPartOf": {"@id": f"{D}/#website"}, "about": {"@id": f"{D}{path}#album"},
            "primaryImageOfPage": rel["image"]["jpg"]["1200"], "breadcrumb": crumbs}
    label = {"@type": "Organization", "@id": f"{D}/#label", "name": L["name"], "url": f"{D}/", "sameAs": L["sameAs"]}
    groups = [clean({"@type": "MusicGroup", "@id": a["id"], "name": a["name"], "url": a["url"],
                     "sameAs": list(dict.fromkeys([a["url"]] + a.get("sameAs", [])))}) for a in arts]
    ld = json.dumps({"@context": "https://schema.org", "@graph": [clean(page), clean(album_node(rel)), label] + groups},
                    ensure_ascii=False, separators=(",", ":"))
    return (
        head(title, desc, path=path, image=rel["image"]["jpg"]["1200"], og_type="music.album", image_alt=rel["image"]["alt"])
        + f'<script type="application/ld+json">{ld}</script></head><body>'
        + SYMBOLS + '<a class="skip up" href="#main">Skip to content</a>' + top()
        + '<main id="main">'
        + '<section class="sec release page" aria-labelledby="release-title">'
        + f'<div class="sleeve"><div class="rec" aria-hidden="true">{circle(C["orange"], ref=True)}</div>'
        + picture(rel, "cover", "(min-width:60rem) 42rem, calc(100vw - 2rem)").replace(' loading="lazy"', ' fetchpriority="high"') + '</div><div>'
        + f'<nav aria-label="Breadcrumb"><ol class="crumbs up"><li><a href="/">{e(L["name"])}</a></li><li><a href="/#catalog">Catalog</a></li><li aria-current="page">{t}</li></ol></nav>'
        + f'<h1 class="title" id="release-title">{t}</h1>'
        + f'<p class="by">{by_html}</p>'
        + f'<p class="meta up">{e(rel["type"])} · <time datetime="{rel["date"]}">{fmt_date(rel["date"])}</time> · {e(L["name"])}</p>'
        + f'<ul class="listen" aria-label="Listen to {t}">{links}</ul>'
        + f'<p class="credit">“{t}” is a {e(rel["type"].lower())} by {by_html}, released on {fmt_date(rel["date"])} by '
        + f'<a href="/">{e(L["name"])}</a>, the independent record label created by {e(CB["name"])}.'
        + (f' UPC {e(rel["upc"])}.' if rel.get("upc") else "") + '</p>'
        + '</div></section>'
        + (f'<section class="sec" aria-labelledby="press-h"><p class="kick up">In the press</p><h2 id="press-h">Press</h2>{news_list(press)}</section>' if press else "")
        + (f'<section class="sec" aria-labelledby="more-h"><p class="kick up">Catalog</p><h2 id="more-h">More from {e(L["name"])}</h2><ul class="cat">{more}</ul></section>' if more else "")
        + '</main>'
        + '<footer class="sec foot">'
        + f'<div><p class="kick up">Get in touch</p><h2>Contact</h2><a class="mail" href="mailto:{L["contact"]}">{L["contact"]}</a></div>'
        + f'<p class="legal up">© {max(dt.date.fromisoformat(rel["date"]).year, dt.date.today().year)} <a href="/">{e(L["name"])}</a></p>'
        + '</footer></body></html>\n')


def news_list(items):
    def one(n):
        rel = next((r for r in RELEASES if r["slug"] == n.get("release")), None)
        meta = " · ".join(x for x in [e(n["outlet"]), e(n["author"]) if n.get("author") else "",
                                        f'<time datetime="{n["date"]}">{fmt_date(n["date"])}</time>'] if x)
        return (f'<li><a href="{e(n["url"])}"><p class="up">{meta}</p><h3>{e(n["title"])}</h3>'
                f'<p>{e(n["summary"])}</p><p class="up or">{e(n["artist"])}'
                + (f' · {e(rel["title"])}' if rel else "") + ' · Read on ' + e(n["outlet"]) + ' ↗</p></a></li>')
    return f'<ul class="news">{"".join(one(n) for n in items)}</ul>'


def news_page():
    path = "/news/"
    title = f"News & Press | {L['name']}"
    desc = (f"News and press coverage of {L['name']} and its artists {NAMES}: reviews, features and release announcements.")
    arts = {a["name"]: a for a in ARTISTS}
    items = []
    for i, n in enumerate(NEWS, 1):
        art = {"@type": "Article", "headline": n["title"], "url": n["url"], "datePublished": n["date"],
               "publisher": {"@type": "Organization", "name": n["outlet"]},
               "author": {"@type": "Person", "name": n["author"]} if n.get("author") else None,
               "about": {"@id": arts[n["artist"]]["id"]} if n["artist"] in arts else {"@type": "MusicGroup", "name": n["artist"]}}
        items.append({"@type": "ListItem", "position": i, "item": art})
    ld = json.dumps({"@context": "https://schema.org", "@graph": [clean({
        "@type": "CollectionPage", "@id": f"{D}{path}", "url": f"{D}{path}", "name": title, "description": desc,
        "inLanguage": "en", "isPartOf": {"@id": f"{D}/#website"}, "about": {"@id": f"{D}/#label"},
        "mainEntity": {"@type": "ItemList", "itemListElement": items},
        "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": L["name"], "item": f"{D}/"},
            {"@type": "ListItem", "position": 2, "name": "News", "item": f"{D}{path}"}]}}),
        {"@type": "Organization", "@id": f"{D}/#label", "name": L["name"], "url": f"{D}/", "sameAs": L["sameAs"]}]},
        ensure_ascii=False, separators=(",", ":"))
    return (
        head(title, desc, path=path)
        + f'<script type="application/ld+json">{ld}</script></head><body>'
        + SYMBOLS + '<a class="skip up" href="#main">Skip to content</a>' + top()
        + '<main id="main"><section class="sec page" aria-labelledby="news-h">'
        + f'<nav aria-label="Breadcrumb"><ol class="crumbs up"><li><a href="/">{e(L["name"])}</a></li><li aria-current="page">News</li></ol></nav>'
        + '<h1 class="title" id="news-h">News</h1>'
        + f'<p class="lead">Press coverage, reviews and features about {e(L["name"])} artists. Links open the original articles.</p>'
        + news_list(NEWS)
        + '</section></main>'
        + '<footer class="sec foot">'
        + f'<div><p class="kick up">Press enquiries</p><h2>Contact</h2><a class="mail" href="mailto:{L["contact"]}">{L["contact"]}</a></div>'
        + f'<p class="legal up">© {dt.date.today().year} <a href="/">{e(L["name"])}</a></p>'
        + '</footer></body></html>\n')


def notfound():
    return (head(f"Page not found – {L['name']}", "This page does not exist.", canonical=False, robots="noindex")
            + '</head><body><main class="nf">'
            + f'<div class="seal" aria-hidden="true">{circle(C["orange"])}</div>'
            + '<p class="up or">Error 404</p><h1>Page not found</h1>'
            + f'<p><a class="btn up" href="/">Back to {e(L["name"])}</a></p></main></body></html>\n')


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
    (DIST / "index.html").write_text(index(), encoding="utf-8")
    (DIST / "404.html").write_text(notfound(), encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {D}/sitemap.xml\n")
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{D}/</loc><lastmod>{TODAY}</lastmod></url>\n"
        + "".join(f"  <url><loc>{D}{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in ([rel_url(r) for r in RELEASES] + (["/news/"] if NEWS else [])))
        + "</urlset>\n")
    if NEWS:
        (DIST / "news").mkdir()
        (DIST / "news" / "index.html").write_text(news_page(), encoding="utf-8")
    for rel in RELEASES:
        out = DIST / rel_url(rel).strip("/")
        out.mkdir(parents=True)
        (out / "index.html").write_text(release_page(rel), encoding="utf-8")
    (DIST / "CNAME").write_text(D.split("://")[1] + "\n")
    (DIST / ".nojekyll").write_text("")
    shutil.copytree(ROOT / "fonts", DIST / "fonts")
    if (ROOT / "img").exists():
        shutil.copytree(ROOT / "img", DIST / "img")
    images()
    try:
        import portfolio.portfolio as pf
        extra = pf.build(DIST, D)
    except Exception as err:  # the label site must deploy even if the portfolio fails
        print("portfolio build failed:", err)
        extra = []
    if extra:
        sm = DIST / "sitemap.xml"
        sm.write_text(sm.read_text().replace("</urlset>", "".join(f"  <url><loc>{D}{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in extra) + "</urlset>"))
    for f in sorted(DIST.rglob("*")):
        if f.is_file():
            print(f"{f.stat().st_size:>8}  {f.relative_to(DIST)}")


if __name__ == "__main__":
    main()
