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
L, R, ARTISTS, D = S["label"], S["release"], S["artists"], S["domain"].rstrip("/")
e = lambda s: html.escape(s, quote=True)
date = dt.date.fromisoformat(R["date"])
TODAY = dt.date.today().isoformat()
COVER = R["image"]["base"]
ORIGINS = sorted({re.match(r"https://[^/]+", u).group(0) for u in [COVER] + [a["image"] for a in ARTISTS] if u.startswith("https://")})

C = {"choco": "#512321", "orange": "#F6A10E", "ink": "#1D1D1B", "white": "#FEFEFE", "grey": "#9E9E9E"}

TITLE = f"{L['name']} – Record label · {R['artist']}, {R['title']}"
DESC = (f"{L['name']} is a record label and home of {' and '.join(a['name'] for a in ARTISTS)}. "
        f"Listen to the latest {R['type'].lower()}, “{R['title']}” by {R['artist']}, on Spotify, Apple Music, YouTube and Deezer.")


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
            f'<path fill="{mark_fill}" transform="{MARK[1]}" d="{MARK[2]}"/>'
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


STRIPES = ("linear-gradient(90deg,"
           "#F6A10E 0 6.8%,#FEFEFE 0 7.9%,#F6A10E 0 10.2%,#FEFEFE 0 15.5%,#F6A10E 0 22.2%,#FEFEFE 0 23.4%,"
           "#F6A10E 0 25.6%,#FEFEFE 0 31.2%,#F6A10E 0 38.4%,#FEFEFE 0 39.1%,#F6A10E 0 41.2%,#FEFEFE 0 46.5%,"
           "#F6A10E 0 53.7%,#FEFEFE 0 55.2%,#F6A10E 0 56.6%,#FEFEFE 0 62%,#F6A10E 0 69.3%,#FEFEFE 0 70.2%,"
           "#F6A10E 0 72.2%,#FEFEFE 0 77.4%,#F6A10E 0 84.9%,#FEFEFE 0 85.8%,#F6A10E 0 87.8%,#FEFEFE 0 93.2%,#F6A10E 0 100%)")

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
.hero{position:relative;background:var(--choco);min-height:calc(100vh - 3.5rem);min-height:calc(100svh - 3.5rem);display:flex;flex-direction:column;justify-content:flex-end;overflow:hidden}
.hero-in{padding:6.5rem var(--pad) clamp(2rem,6vh,3.5rem);display:grid;gap:clamp(1.25rem,3vh,2rem);justify-items:center;text-align:center}
.hero h1{width:min(100%,64rem)}
.lockup{width:100%}
.tag{margin:0;color:var(--white)}
.cta{margin:0;display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:.75rem 1.5rem}
.btn{display:inline-flex;align-items:center;gap:.75em;min-height:2.875rem;padding:0 1.4rem;border:1px solid currentColor;border-radius:999px;text-decoration:none;transition:background .2s,color .2s,border-color .2s}
.btn:hover{background:var(--orange);border-color:var(--orange);color:var(--ink)}
.stripes{height:clamp(1.5rem,5vw,3rem);background:STRIPES}
.sec{max-width:84rem;margin:0 auto;padding:clamp(4.5rem,12vw,8rem) var(--pad) 0}
.kick{margin:0 0 .9rem;color:var(--orange)}
.release{display:grid;gap:clamp(2rem,5vw,4.5rem)}
.cover{width:100%;aspect-ratio:1;background:var(--choco)}
.title{font-size:clamp(3.5rem,11vw,8rem)}
.by{margin:.5rem 0 0;font:400 clamp(1.5rem,3.5vw,2.25rem)/1.1 var(--d)}
.by a{text-decoration-thickness:1px;text-underline-offset:.2em}
.by a:hover{color:var(--orange)}
.meta{margin:1rem 0 2.25rem;color:var(--grey)}
.listen{border-top:1px solid var(--line)}
.listen a{display:flex;justify-content:space-between;align-items:center;gap:1rem;min-height:4rem;border-bottom:1px solid var(--line);text-decoration:none}
.pf{font:400 clamp(1.5rem,3.4vw,2.125rem)/1 var(--d);transition:color .2s}
.act{color:var(--grey);white-space:nowrap}
.listen a:hover .pf{color:var(--orange)}
.listen a:hover .act{color:var(--white)}
.sec>h2,.foot h2{font-size:clamp(3rem,8vw,5.5rem)}
.roster{display:grid;gap:1.5rem;margin-top:2.5rem}
.artist{position:relative;display:block;background:var(--choco);text-decoration:none;overflow:hidden}
.artist img{width:100%;aspect-ratio:4/5;object-fit:cover;object-position:50% 58%;transition:transform .5s}.artist img.c{object-position:50% 50%}
.artist div{position:absolute;inset:auto 0 0;padding:1.25rem 1.25rem 1.1rem;background:linear-gradient(to top,rgba(29,29,27,.92),rgba(29,29,27,0))}
.artist h3{font-size:clamp(2.5rem,6vw,3.75rem)}
.artist p{margin:.4rem 0 0;color:var(--orange)}
.artist:hover img{transform:scale(1.03)}
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
.nf{min-height:100svh;display:grid;place-content:center;gap:1.5rem;text-align:center;padding:var(--pad);background:var(--choco)}
.nf h1{font-size:clamp(3.5rem,12vw,8rem)}
.nf .seal{margin:0 auto;width:7rem}
.sr{position:absolute;width:1px;height:1px;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
@media (min-width:40rem){.bar i{display:inline}.roster{grid-template-columns:repeat(auto-fill,minmax(18rem,24rem))}}
@media (min-width:60rem){.release{grid-template-columns:minmax(0,1fr) minmax(0,1fr);align-items:end}.about,.foot{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.seal{justify-self:end}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
""".strip().replace("background:STRIPES", "background:" + STRIPES)
CSS = "".join(line.strip() for line in CSS.splitlines())
CSS_HASH = base64.b64encode(hashlib.sha256(CSS.encode()).digest()).decode()
CSP = (f"default-src 'none'; connect-src 'self'; img-src 'self' {' '.join(ORIGINS)}; font-src 'self'; "
       f"style-src 'sha256-{CSS_HASH}'; base-uri 'none'; form-action 'none'")


def jsonld():
    lid, rid = f"{D}/#label", f"{D}/#{R['slug']}"
    main_artist = next(a for a in ARTISTS if a["name"] == R["artist"])
    graph = [
        {"@type": "WebSite", "@id": f"{D}/#website", "url": f"{D}/", "name": L["name"],
         "inLanguage": "en", "publisher": {"@id": lid}},
        {"@type": "WebPage", "@id": f"{D}/#webpage", "url": f"{D}/", "name": TITLE, "description": DESC,
         "inLanguage": "en", "isPartOf": {"@id": f"{D}/#website"}, "about": {"@id": lid},
         "primaryImageOfPage": f"{D}/og.png", "dateModified": TODAY},
        {"@type": "Organization", "@id": lid, "name": L["name"], "url": f"{D}/", "description": L["description"],
         "logo": f"{D}/logo.png", "image": f"{D}/og.png", "email": L["contact"], "sameAs": L["sameAs"]},
    ]
    for a in ARTISTS:
        graph.append({"@type": "MusicGroup", "@id": a["id"], "name": a["name"], "url": a["url"],
                      "sameAs": [a["url"]], "genre": a.get("genre"), "recordLabel": {"@id": lid}})
    graph.append({"@type": "MusicAlbum", "@id": rid, "name": R["title"],
                  "albumReleaseType": f"https://schema.org/{R['type']}Release",
                  "byArtist": {"@id": main_artist["id"]}, "datePublished": R["date"],
                  "image": f"{COVER}-1200.jpg", "url": f"{D}/#{R['slug']}",
                  "sameAs": [l["url"] for l in R["links"] if "watch?v=" not in l["url"]],
                  "numTracks": 1 if R["type"] == "Single" else None,
                  "albumRelease": {"@type": "MusicRelease", "name": R["title"], "recordLabel": {"@id": lid},
                                   "gtin13": R.get("upc"), "datePublished": R["date"]},
                  "track": {"@type": "MusicRecording", "name": R["title"], "duration": R.get("duration"),
                            "byArtist": {"@id": main_artist["id"]}}})

    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items() if v is not None}
        return o
    return json.dumps({"@context": "https://schema.org", "@graph": [clean(g) for g in graph]},
                      ensure_ascii=False, separators=(",", ":"))


def head(title, desc, canonical=True, robots="index,follow,max-image-preview:large"):
    p = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         f"<title>{e(title)}</title>", f'<meta name="description" content="{e(desc)}">',
         f'<meta name="robots" content="{robots}">',
         f'<meta http-equiv="Content-Security-Policy" content="{CSP}">',
         '<meta name="referrer" content="strict-origin-when-cross-origin">']
    if canonical:
        p += [f'<link rel="canonical" href="{D}/">', '<meta property="og:type" content="website">',
              f'<meta property="og:site_name" content="{e(L["name"])}">',
              f'<meta property="og:title" content="{e(title)}">',
              f'<meta property="og:description" content="{e(desc)}">',
              f'<meta property="og:url" content="{D}/">', f'<meta property="og:image" content="{D}/og.png">',
              '<meta property="og:image:type" content="image/png">',
              '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
              f'<meta property="og:image:alt" content="{e(L["name"])} logo">',
              '<meta property="og:locale" content="en_US">', '<meta name="twitter:card" content="summary_large_image">']
    p += [f'<meta name="theme-color" content="{C["choco"]}">',
          '<link rel="icon" href="/favicon.ico" sizes="32x32">',
          '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
          '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
          '<link rel="preload" href="/fonts/avigea.woff2" as="font" type="font/woff2" crossorigin>',
          f"<style>{CSS}</style>"]
    return "".join(p)


CENTER = ' class="c"'


def index():
    t = e(R["title"])
    main_artist = next(a for a in ARTISTS if a["name"] == R["artist"])
    links = "".join(
        f'<li><a href="{e(l["url"])}"><span class="pf">{e(l["name"])}</span>'
        f'<span class="act up">{"Watch" if "watch?v=" in l["url"] else "Listen"}'
        f'<span class="sr">{"" if "watch?v=" in l["url"] else " to"} {t} on {e(l["name"])}</span> ↗</span></a></li>'
        for l in R["links"])
    roster = "".join(
        f'<li><a class="artist" href="{e(a["url"])}">'
        f'<img{CENTER if a.get("position") == "50% 50%" else ""} src="{e(a["image"])}" width="800" height="800" alt="{e(a["alt"])}" loading="lazy" decoding="async">'
        f'<div><h3>{e(a["name"])}</h3><p class="up">{e(a["role"])} · {e(a.get("linkLabel", "Official website"))} ↗</p></div></a></li>'
        for a in ARTISTS)
    first = R["links"][0]
    apple = next((l for l in R["links"] if l["name"] == "Apple Music"), None)
    bar = f'<a href="{e(first["url"])}">{e(first["name"])}</a>' + (f'<a href="{e(apple["url"])}">Apple Music</a>' if apple else "")
    year = max(date.year, dt.date.today().year)
    return (
        head(TITLE, DESC)
        + f'<script type="application/ld+json">{jsonld()}</script></head><body>'
        + SYMBOLS + '<a class="skip up" href="#release">Skip to the latest release</a>'
        + f'<header class="top"><a class="brand" href="/" aria-label="{e(L["name"])} home">{circle(C["orange"], ref=True)}</a>'
        + '<nav class="up" aria-label="Sections"><a href="#release">Release</a><a href="#artists">Artists</a><a href="#contact">Contact</a></nav></header>'
        + '<main>'
        + '<section class="hero" aria-labelledby="name"><div class="hero-in">'
        + f'<h1 id="name">{lockup("lockup", C["orange"], C["white"])}<span class="sr">{e(L["name"])}</span></h1>'
        + '<p class="tag up">Record label</p>'
        + f'<p class="cta"><span class="up or">New {e(R["type"].lower())} · {e(R["artist"])}</span><a class="btn up" href="#release">Listen to {t}</a></p>'
        + '</div><div class="stripes" aria-hidden="true"></div></section>'
        + f'<section class="sec release" id="release" aria-labelledby="release-title">'
        + '<picture>'
        + f'<source type="image/webp" srcset="{COVER}-640.webp 640w, {COVER}-1200.webp 1200w" sizes="(min-width:60rem) 42rem, calc(100vw - 2rem)">'
        + f'<img class="cover" src="{COVER}-640.jpg" width="640" height="640" alt="{e(R["image"]["alt"])}" loading="lazy" decoding="async">'
        + '</picture><div>'
        + '<p class="kick up">Latest release</p>'
        + f'<h2 class="title" id="release-title">{t}</h2>'
        + f'<p class="by"><a href="{e(main_artist["url"])}">{e(R["artist"])}</a></p>'
        + f'<p class="meta up">{e(R["type"])} · <time datetime="{R["date"]}">{date.day} {date.strftime("%B %Y")}</time> · {e(L["name"])}</p>'
        + f'<ul class="listen" aria-label="Listen to {t}">{links}</ul>'
        + '</div></section>'
        + f'<section class="sec" id="artists" aria-labelledby="artists-h"><p class="kick up">Roster</p><h2 id="artists-h">Artists</h2><ul class="roster">{roster}</ul></section>'
        + f'<section class="sec about" aria-labelledby="about-h"><div><p class="kick up">The label</p><h2 id="about-h" class="sr">About {e(L["name"])}</h2><p>{e(L["intro"])}</p></div>'
        + f'<div class="seal" aria-hidden="true">{circle(C["choco"], ref=True)}</div></section>'
        + '</main>'
        + '<footer class="sec foot" id="contact">'
        + f'<div><p class="kick up">Get in touch</p><h2>Contact</h2><a class="mail" href="mailto:{L["contact"]}">{L["contact"]}</a></div>'
        + '<div><p class="kick up">Elsewhere</p><h2 class="sr">Links</h2><ul class="follow">'
        + "".join(f'<li><a href="{e(u)}">MusicBrainz</a></li>' for u in L["sameAs"] if "musicbrainz" in u)
        + "".join(f'<li><a href="{e(a["url"])}">{e(a["name"])}</a></li>' for a in ARTISTS)
        + '</ul></div>'
        + f'<p class="legal up">© {year} {e(L["name"])}</p>'
        + '</footer>'
        + f'<aside class="bar up" aria-label="Listen now"><b>Out now</b><i>{e(R["artist"])} — {t}</i><span>{bar}</span></aside>'
        + '</body></html>\n')


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
    at = Image.new("RGB", (180, 180), C["choco"]); at.paste(png(circle(C["orange"]), 150), (15, 15), png(circle(C["orange"]), 150)); at.save(DIST / "apple-touch-icon.png", optimize=True)
    png(circle(C["choco"]), 512).save(DIST / "logo.png", optimize=True)
    og = Image.new("RGB", (1200, 630), C["choco"])
    lk = png(lockup("", C["orange"], C["white"]).replace('<svg class=""', '<svg'), 960, round(960 * 1028 / 3344))
    og.paste(lk, (120, (630 - lk.height) // 2 - 20), lk)
    band = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="40">'
        + "".join(f'<rect x="{a*12}" width="{(b-a)*12}" height="40" fill="{col}"/>' for a, b, col in _stripes())
        + '</svg>').encode()))).convert("RGB")
    og.paste(band, (0, 590))
    og.save(DIST / "og.png", optimize=True)


def _stripes():
    stops = re.findall(r"(#[0-9A-F]{6}) 0 ([\d.]+)%", STRIPES)
    out, prev = [], 0.0
    for col, end in stops:
        out.append((prev, float(end), col)); prev = float(end)
    return out


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    (DIST / "index.html").write_text(index(), encoding="utf-8")
    (DIST / "404.html").write_text(notfound(), encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {D}/sitemap.xml\n")
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{D}/</loc><lastmod>{TODAY}</lastmod></url>\n</urlset>\n")
    (DIST / "CNAME").write_text(D.split("://")[1] + "\n")
    (DIST / ".nojekyll").write_text("")
    shutil.copytree(ROOT / "fonts", DIST / "fonts")
    if (ROOT / "img").exists():
        shutil.copytree(ROOT / "img", DIST / "img")
    images()
    for f in sorted(DIST.rglob("*")):
        if f.is_file():
            print(f"{f.stat().st_size:>8}  {f.relative_to(DIST)}")


if __name__ == "__main__":
    main()
