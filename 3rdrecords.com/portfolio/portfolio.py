#!/usr/bin/env python3
"""Build the Lead Major portfolio into <dist>/portfolio/leadmajor/ from portfolio/leadmajor.json.

Called from build.py (portfolio.build(DIST)). Static page, one inline stylesheet, one inline script.
At build time (GitHub Actions has internet) remote images are downloaded, resized and saved as WebP next
to the page, and the three web fonts are downloaded from jsDelivr. If a download fails, the page falls
back to the remote image URL / system fonts, so the build never breaks.
To replace an image by your own file, drop it in portfolio/img/<key>.webp (or .jpg/.png).
"""
import base64, datetime as dt, hashlib, html, io, json, pathlib, re, shutil, urllib.request, urllib.parse

HERE = pathlib.Path(__file__).parent
e = lambda s: html.escape(str(s), quote=True)
UA = {"User-Agent": "Mozilla/5.0 (3rdrecords.com build)"}


def fetch(url, timeout=25):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def origin(u):
    m = re.match(r"https://[^/]+", u)
    return m.group(0) if m else None


def prepare_images(P, out, domain):
    """Return {key: {"src", "srcset", "w", "h", "alt"}} with local files when possible."""
    from PIL import Image
    imgdir = out / "img"
    imgdir.mkdir(parents=True, exist_ok=True)
    res = {}
    for key, spec in P["images"].items():
        alt = spec.get("alt", "")
        if spec.get("local"):
            res[key] = {"src": spec["local"], "srcset": "", "w": None, "h": None, "alt": alt}
            continue
        raw = None
        for ext in ("webp", "jpg", "png"):
            f = HERE / "img" / f"{key}.{ext}"
            if f.exists():
                raw = f.read_bytes()
                break
        if raw is None:
            try:
                raw = fetch(spec["src"])
            except Exception as err:  # offline or source gone: keep the remote file
                print(f"  ! image {key}: {err} -> remote")
        if raw is None:
            res[key] = {"src": spec["src"], "srcset": "", "w": None, "h": None, "alt": alt, "remote": True}
            continue
        im = Image.open(io.BytesIO(raw))
        im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
        W = min(spec.get("w", 1200), im.width)
        widths = sorted({w for w in (480, 800, W) if w <= W})
        srcset = []
        for w in widths:
            h = round(im.height * w / im.width)
            name = f"{key}-{w}.webp"
            im.resize((w, h), Image.LANCZOS).save(imgdir / name, "WEBP", quality=82, method=6)
            srcset.append(f"img/{name} {w}w")
        res[key] = {"src": f"img/{key}-{W}.webp", "srcset": ", ".join(srcset), "w": W,
                    "h": round(im.height * W / im.width), "alt": alt}
    return res


def prepare_fonts(P, out):
    fdir = out / "fonts"
    fdir.mkdir(parents=True, exist_ok=True)
    ok = {}
    for key, url in P["fonts"].items():
        name = f"{key}.woff2"
        local = HERE / "fonts" / name
        try:
            data = local.read_bytes() if local.exists() else fetch(url)
            (fdir / name).write_bytes(data)
            ok[key] = f"fonts/{name}"
        except Exception as err:
            print(f"  ! font {key}: {err} -> system font")
    return ok


def img_tag(I, key, sizes, cls="", eager=False):
    i = I[key]
    attrs = [f'src="{e(i["src"])}"', f'alt="{e(i["alt"])}"', 'decoding="async"']
    if i.get("srcset"):
        attrs.append(f'srcset="{e(i["srcset"])}" sizes="{sizes}"')
    if i.get("w"):
        attrs.append(f'width="{i["w"]}" height="{i["h"]}"')
    attrs.append('fetchpriority="high"' if eager else 'loading="lazy"')
    if cls:
        attrs.append(f'class="{cls}"')
    return f"<img {' '.join(attrs)}>"


CSS = r"""
@font-face{font-family:"Bricolage";src:url(fonts/display.woff2) format("woff2");font-weight:200 800;font-display:swap}
@font-face{font-family:"InterV";src:url(fonts/body.woff2) format("woff2");font-weight:100 900;font-display:swap}
@font-face{font-family:"JBMono";src:url(fonts/mono.woff2) format("woff2");font-weight:400;font-display:swap}
:root{
  --bg:#07070a;--bg2:#0e0e13;--surface:#121218;--text:#eef0f5;--dim:#9aa0ad;--faint:#5f6470;
  --line:#1d1e26;--line2:#2c2e39;--blue:#5b74ff;--red:#ff4262;--green:#39e0a4;--accent:var(--blue);
  --display:"Bricolage","InterV",system-ui,sans-serif;--body:"InterV",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"JBMono",ui-monospace,"SF Mono",Menlo,monospace;
  --wrap:1240px;--gut:clamp(16px,4vw,44px);--head:64px;--bar:68px;--ease:cubic-bezier(.2,.7,.2,1);color-scheme:dark
}
*,*::before,*::after{box-sizing:border-box}
*{margin:0;padding:0}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%;scroll-behavior:smooth;scroll-padding-top:calc(var(--head) + 12px)}
body{background:var(--bg);color:var(--text);font:400 16px/1.55 var(--body);-webkit-font-smoothing:antialiased;overflow-x:hidden}
body.has-bar{padding-bottom:var(--bar)}
body.locked{overflow:hidden}
a{color:inherit;text-decoration:none}
button{font:inherit;color:inherit;background:none;border:0;cursor:pointer}
ul,ol{list-style:none}
img,svg,video{display:block;max-width:100%}
:focus-visible{outline:2px solid var(--blue);outline-offset:3px;border-radius:6px}
.mono{font-family:var(--mono);font-size:12px;letter-spacing:.04em}
.up{text-transform:uppercase;letter-spacing:.14em}
.sr{position:absolute!important;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.wrap{width:100%;max-width:var(--wrap);margin-inline:auto;padding-inline:var(--gut)}
.skip{position:absolute;left:12px;top:-60px;z-index:200;background:var(--text);color:var(--bg);padding:8px 14px;border-radius:8px}
.skip:focus{top:12px}
.dim{color:var(--dim)}
.grain{position:fixed;inset:-50%;z-index:90;pointer-events:none;opacity:.05;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");animation:grain 1.2s steps(6) infinite}
@keyframes grain{0%{transform:translate(0,0)}20%{transform:translate(-4%,3%)}40%{transform:translate(3%,-5%)}60%{transform:translate(-2%,4%)}80%{transform:translate(5%,1%)}100%{transform:translate(0,0)}}

/* buttons */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;height:44px;padding:0 20px;border-radius:999px;border:1px solid var(--line2);font-size:14px;font-weight:500;white-space:nowrap;transition:background-color .15s,color .15s,border-color .15s,transform .15s}
.btn:hover{background:var(--text);color:var(--bg);border-color:var(--text)}
.btn:active{transform:scale(.97)}
.btn-p{background:var(--blue);border-color:var(--blue);color:#fff}
.btn-p:hover{background:var(--text);border-color:var(--text);color:var(--bg)}
.btn-s{height:36px;padding:0 14px;font-size:13px}
.ico{width:18px;height:18px}
.round{width:52px;height:52px;border-radius:50%;display:inline-grid;place-items:center;border:1px solid var(--line2);transition:background-color .15s,color .15s,border-color .15s,transform .15s}
.round:hover{background:var(--text);color:var(--bg);border-color:var(--text)}
.round:active{transform:scale(.94)}
.round[disabled]{opacity:.3;pointer-events:none}
.chip{display:inline-flex;align-items:center;height:26px;padding:0 10px;border-radius:999px;border:1px solid var(--line2);font-family:var(--mono);font-size:11px;letter-spacing:.04em;color:var(--dim)}

/* gate */
.gate{position:fixed;inset:0;z-index:150;display:grid;place-items:center;overflow:hidden;background:#050507;transition:transform 1s cubic-bezier(.76,0,.24,1),opacity .6s}
.gate[hidden]{display:none}
.gate.out{transform:translateY(-100%);pointer-events:none}
.gate-bg{position:absolute;inset:-15%;background-size:cover;background-position:center;filter:blur(50px) saturate(1.3);opacity:.45;transform:scale(1.1);animation:drift 18s ease-in-out infinite alternate}
.gate-bg img{width:100%;height:100%;object-fit:cover}
@keyframes drift{to{transform:scale(1.28) translate(2%,-2%)}}
.gate-vig{position:absolute;inset:0;background:radial-gradient(70% 60% at 50% 50%,transparent,rgba(5,5,7,.85));pointer-events:none}
.gate-glow{position:absolute;left:50%;top:42%;width:min(110vw,1300px);aspect-ratio:2/1;translate:-50% -50%;pointer-events:none;
  background:radial-gradient(closest-side at 38% 50%,rgba(91,116,255,.34),transparent 70%),radial-gradient(closest-side at 62% 45%,rgba(255,66,98,.26),transparent 70%),radial-gradient(closest-side at 50% 70%,rgba(57,224,164,.2),transparent 70%);
  animation:breathe 4.4s ease-in-out infinite alternate}
@keyframes breathe{from{opacity:.55;scale:.94}to{opacity:1;scale:1.05}}
.gate-in{position:relative;display:grid;justify-items:center;gap:clamp(8px,2vh,20px);padding:16px;text-align:center}
.emblem{position:relative;width:min(46vw,300px,34svh);aspect-ratio:1}
.emblem video,.emblem svg{position:absolute;inset:0;width:100%;height:100%}
.emblem video{mix-blend-mode:screen;-webkit-mask-image:radial-gradient(closest-side,#000 80%,transparent);mask-image:radial-gradient(closest-side,#000 80%,transparent)}
.emblem.novid svg{animation:emb-in .6s ease forwards,spin 30s linear .6s infinite}
.emblem.novid video{display:none}
.emblem svg{opacity:0;animation:emb-in 1s ease 6.6s forwards,spin 30s linear 7.6s infinite;filter:drop-shadow(-3px 0 0 rgba(255,66,98,.8)) drop-shadow(3px 0 0 rgba(91,116,255,.8)) drop-shadow(0 0 18px rgba(57,224,164,.45))}
@keyframes emb-in{to{opacity:1}}
.gate-word{font:800 clamp(44px,10vw,120px)/.9 var(--display);letter-spacing:-.04em;text-transform:uppercase}
.gate-hint{color:rgba(238,240,245,.55);font-size:11px}
.enter{height:48px;min-width:230px;padding:0 30px;border-radius:999px;border:1px solid rgba(238,240,245,.6);background:rgba(5,5,7,.3);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);font-family:var(--mono);font-size:13px;letter-spacing:.28em;text-transform:uppercase;transition:background-color .2s,color .2s,transform .2s}
.enter:hover,.enter:focus-visible{background:var(--text);color:var(--bg)}
.enter:active{transform:scale(.97)}
.quiet{font-size:12px;color:var(--dim);text-decoration:underline;text-underline-offset:3px}
.quiet:hover{color:var(--text)}
.chroma{text-shadow:-.03em 0 0 rgba(255,66,98,.85),.03em 0 0 rgba(91,116,255,.85),0 0 .4em rgba(57,224,164,.25)}

/* header */
.head{position:sticky;top:0;z-index:60;background:color-mix(in srgb,var(--bg) 82%,transparent);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
.head-row{display:flex;align-items:center;gap:26px;min-height:var(--head)}
.brand{display:flex;align-items:center;gap:10px;font:700 18px/1 var(--display);letter-spacing:-.01em;white-space:nowrap}
.brand svg{width:30px;height:30px;animation:spin 24s linear infinite}
.brand b{color:var(--blue);font-weight:700}
.nav{flex:1;min-width:0}
.nav ul{display:flex;gap:22px;overflow-x:auto;scrollbar-width:none}
.nav ul::-webkit-scrollbar{display:none}
.nav a{display:inline-block;padding:6px 0;font-size:14px;color:var(--dim);white-space:nowrap;transition:color .15s}
.nav a:hover,.nav a.on{color:var(--text)}
.head-act{display:flex;align-items:center;gap:8px;margin-left:auto}
.eq{width:40px;height:40px;border-radius:50%;display:inline-grid;place-items:center;color:var(--dim)}
.eq:hover{color:var(--text);background:var(--bg2)}
.bars{display:flex;align-items:flex-end;gap:2px;height:14px}
.bars i{width:2px;height:3px;border-radius:1px;background:currentColor;transition:height .3s}
.playing .bars i,.bars.on i{animation:amb 1.1s ease-in-out infinite}
.playing .bars i:nth-child(2),.bars.on i:nth-child(2){animation-delay:-.4s}
.playing .bars i:nth-child(3),.bars.on i:nth-child(3){animation-delay:-.8s}
.playing .bars i:nth-child(4),.bars.on i:nth-child(4){animation-delay:-.2s}
.playing .eq{color:var(--blue)}
@keyframes amb{0%,100%{height:3px}50%{height:14px}}
@media (max-width:860px){
  .head-row{flex-wrap:wrap;gap:0 12px}
  .nav{order:3;flex-basis:100%;margin-inline:calc(var(--gut)*-1);position:relative}
  .nav ul{padding:0 var(--gut) 10px;gap:20px}
  .nav::after{content:"";position:absolute;right:0;top:0;bottom:0;width:32px;background:linear-gradient(90deg,transparent,var(--bg));pointer-events:none}
  .head-act .btn{display:none}
}

/* stage */
.stage{position:relative;overflow:hidden;isolation:isolate}
.stage::before{content:"";position:absolute;inset:0;z-index:-1;pointer-events:none;
  background:radial-gradient(38% 55% at 76% 42%,rgba(91,116,255,.16),transparent 70%),radial-gradient(26% 38% at 66% 72%,rgba(255,66,98,.12),transparent 70%),radial-gradient(24% 34% at 88% 70%,rgba(57,224,164,.1),transparent 70%)}
.stage-grid{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr);align-items:center;gap:clamp(24px,5vw,72px);padding-block:clamp(36px,7vw,96px) clamp(32px,5vw,64px)}
.kick{color:var(--dim)}
.h1{margin-top:14px;font:800 clamp(64px,11vw,156px)/.86 var(--display);letter-spacing:-.05em;text-transform:uppercase}
.h1 span{display:block}
.h1 span:nth-child(2){padding-left:.5em}
.lede{margin-top:22px;font:600 clamp(22px,2.6vw,32px)/1.15 var(--display);letter-spacing:-.015em}
.sub{margin-top:10px;max-width:40ch;color:var(--dim);font-size:clamp(15px,1.3vw,17px)}
.tags{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}
.cta{display:flex;flex-wrap:wrap;gap:10px;margin-top:28px}
.orb{position:relative;width:min(100%,460px);aspect-ratio:1;justify-self:center;border-radius:50%;animation:float 7s ease-in-out infinite}
.orb::before{content:"";position:absolute;inset:0;border-radius:50%;background:radial-gradient(circle at 50% 40%,#1b2150,#0a0b12 70%);box-shadow:0 0 0 1px rgba(255,255,255,.07),0 30px 120px rgba(91,116,255,.25),inset -30px -20px 80px rgba(255,66,98,.18),inset 30px 20px 80px rgba(57,224,164,.12)}
.orb::after{content:"";position:absolute;inset:0;border-radius:50%;pointer-events:none;background:radial-gradient(circle at 30% 22%,rgba(255,255,255,.3),transparent 30%);box-shadow:inset 0 0 40px rgba(255,255,255,.14)}
.orb-clip{position:absolute;inset:0;border-radius:50%;overflow:hidden}
.orb-clip img{position:absolute;left:50%;bottom:-8%;width:74%;height:auto;translate:-50% 0;filter:drop-shadow(0 20px 30px rgba(0,0,0,.5))}
.orb .ring{position:absolute;inset:-7%;border-radius:50%;border:1px dashed rgba(238,240,245,.16);animation:spin 40s linear infinite}
.orb .ring svg{position:absolute;width:44px;height:44px;left:50%;top:-22px;translate:-50% 0;filter:drop-shadow(0 0 10px rgba(91,116,255,.8))}
@keyframes float{50%{transform:translateY(-12px)}}
@keyframes spin{to{transform:rotate(360deg)}}
@media (max-width:780px){.stage-grid{grid-template-columns:1fr}.orb{order:-1;width:min(64vw,280px)}}
.ticker{border-block:1px solid var(--line);overflow:hidden;white-space:nowrap}
.ticker-track{display:inline-flex;gap:38px;padding:13px 0;animation:tick 42s linear infinite;color:var(--dim)}
.ticker:hover .ticker-track{animation-play-state:paused}
.ticker-track span{display:inline-flex;align-items:center;gap:38px}
.ticker-track span::after{content:"";width:6px;height:6px;border-radius:50%;background:var(--blue);box-shadow:-9px 0 0 var(--red),9px 0 0 var(--green)}
@keyframes tick{to{transform:translateX(-50%)}}

/* sections */
.sec{padding-block:clamp(64px,10vw,128px) 0}
.sec-head{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:16px 24px;margin-bottom:clamp(24px,4vw,40px)}
.h2{font:800 clamp(40px,6.5vw,88px)/.92 var(--display);letter-spacing:-.04em}
.label{color:var(--blue);margin-bottom:10px}
.reveal{opacity:0;transform:translateY(22px);transition:opacity .8s var(--ease),transform .8s var(--ease)}
.reveal.in{opacity:1;transform:none}

/* work slider */
.work{position:relative;isolation:isolate}
.work-bg{position:absolute;inset:0;z-index:-1;overflow:hidden;pointer-events:none}
.work-bg img{position:absolute;left:-25%;top:-25%;width:150%;height:150%;object-fit:cover;filter:blur(70px) saturate(1.4);opacity:0;transition:opacity 1s ease}
.work-bg img.on{opacity:.28}
.work-bg::after{content:"";position:absolute;inset:0;background:linear-gradient(var(--bg),transparent 25%,transparent 75%,var(--bg))}
.ctrl{display:flex;align-items:center;gap:14px}
.count{font-family:var(--mono);font-size:13px;color:var(--dim);min-width:64px;text-align:center}
.count b{color:var(--text);font-weight:400}
.slider{position:relative;overflow:hidden;touch-action:pan-y}
.track{display:flex;transition:transform .8s cubic-bezier(.7,0,.2,1)}
.slide{flex:0 0 100%;min-width:0;display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,.85fr);gap:clamp(20px,4vw,56px);align-items:center;padding-bottom:6px}
.slide:not(.cur) .info>*{opacity:0;transform:translateY(16px)}
.slide .info>*{transition:opacity .6s var(--ease),transform .6s var(--ease)}
.slide.cur .info>*:nth-child(2){transition-delay:.08s}.slide.cur .info>*:nth-child(3){transition-delay:.14s}.slide.cur .info>*:nth-child(4){transition-delay:.2s}.slide.cur .info>*:nth-child(5){transition-delay:.26s}.slide.cur .info>*:nth-child(6){transition-delay:.32s}
.media{position:relative;border-radius:14px;overflow:hidden;background:var(--surface);box-shadow:0 30px 80px rgba(0,0,0,.55),0 0 0 1px rgba(255,255,255,.06);aspect-ratio:16/9}
.media.sq{aspect-ratio:1;width:min(100%,560px);justify-self:center}
.media img,.media iframe{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border:0;transition:transform 1.2s var(--ease)}
.slide:not(.cur) .media img{transform:scale(1.08)}
.media .img-contain{object-fit:contain;background:#0b0b10}
.playbtn{position:absolute;inset:0;display:grid;place-items:center;background:linear-gradient(transparent 40%,rgba(0,0,0,.45))}
.playbtn span{width:78px;height:78px;border-radius:50%;display:grid;place-items:center;background:rgba(238,240,245,.92);color:#07070a;box-shadow:0 0 0 10px rgba(238,240,245,.14);transition:transform .2s,box-shadow .2s}
.playbtn:hover span{transform:scale(1.07);box-shadow:0 0 0 16px rgba(238,240,245,.12)}
.playbtn .ico{width:26px;height:26px;margin-left:3px}
.idx{color:var(--dim)}
.idx b{color:var(--blue);font-weight:400}
.wt{margin-top:10px;font:800 clamp(38px,5.2vw,72px)/.92 var(--display);letter-spacing:-.035em}
.wby{margin-top:8px;font:600 clamp(17px,1.6vw,21px)/1.25 var(--display);color:var(--dim)}
.roles{display:flex;flex-wrap:wrap;gap:6px;margin-top:18px}
.wtext{margin-top:16px;max-width:46ch;color:#c9ccd6}
.wlinks{display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}
.progress{display:flex;gap:6px;margin-top:clamp(24px,4vw,40px)}
.progress button{flex:1;height:30px;position:relative}
.progress button::before{content:"";position:absolute;left:0;right:0;top:50%;height:2px;background:var(--line2);border-radius:2px}
.progress button::after{content:"";position:absolute;left:0;top:50%;height:2px;width:0;background:var(--text);border-radius:2px;transition:width .5s var(--ease)}
.progress button.done::after{width:100%;background:var(--dim)}
.progress button.cur::after{width:100%;background:linear-gradient(90deg,var(--red),var(--blue),var(--green))}
.progress button:hover::before{background:var(--dim)}
.hint-keys{display:flex;align-items:center;gap:6px;color:var(--faint);margin-top:12px}
.hint-keys kbd{font:inherit;border:1px solid var(--line2);border-radius:5px;padding:1px 6px;color:var(--dim)}
@media (max-width:860px){.slide{grid-template-columns:1fr;align-items:start;align-content:start}.hint-keys{display:none}}
@media (max-width:600px){.reel-cap{display:none}.playbtn span{width:62px;height:62px}}

/* showreel */
.reel{position:relative;border-radius:18px;overflow:hidden;aspect-ratio:16/9;background:var(--surface);box-shadow:0 0 0 1px rgba(255,255,255,.06),0 40px 120px rgba(91,116,255,.14)}
.reel img,.reel iframe{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border:0}
.reel .playbtn{background:radial-gradient(circle,rgba(0,0,0,.1),rgba(0,0,0,.5))}
.reel-cap{position:absolute;left:clamp(16px,3vw,32px);bottom:clamp(14px,3vw,28px);right:120px;pointer-events:none}
.reel-cap strong{display:block;font:800 clamp(24px,4vw,48px)/1 var(--display);letter-spacing:-.03em}

/* sync */
.sync{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:clamp(24px,5vw,72px);align-items:start}
.deck{position:sticky;top:calc(var(--head) + 20px);border:1px solid var(--line);border-radius:18px;padding:clamp(20px,3vw,32px);background:linear-gradient(160deg,rgba(91,116,255,.1),rgba(255,66,98,.05) 50%,rgba(57,224,164,.06))}
.disc{position:relative;width:min(100%,260px);aspect-ratio:1;margin:0 auto 22px;border-radius:50%;background:radial-gradient(circle,#0a0a0f 0 30%,transparent 30.5%),repeating-radial-gradient(circle,#121219 0 1.5px,#22232d 1.6px 3.2px);box-shadow:0 20px 60px rgba(0,0,0,.6),inset 0 0 0 5px #0a0a0f;animation:spin 4s linear infinite;animation-play-state:paused}
.playing .disc{animation-play-state:running}
.disc svg{position:absolute;inset:34%;width:32%;height:32%;filter:drop-shadow(-2px 0 0 rgba(255,66,98,.9)) drop-shadow(2px 0 0 rgba(91,116,255,.9))}
.now{min-height:52px;text-align:center}
.now strong{display:block;font:700 22px/1.2 var(--display);letter-spacing:-.01em}
.transport{display:flex;align-items:center;justify-content:center;gap:12px;margin-top:16px}
.transport .big{width:64px;height:64px;background:var(--text);color:var(--bg);border-color:var(--text)}
.transport .big:hover{background:var(--blue);border-color:var(--blue);color:#fff}
.seek{position:relative;height:18px;margin-top:18px;cursor:pointer}
.seek::before{content:"";position:absolute;left:0;right:0;top:8px;height:2px;background:var(--line2);border-radius:2px}
.seek i{position:absolute;left:0;top:8px;height:2px;width:0;border-radius:2px;background:linear-gradient(90deg,var(--red),var(--blue),var(--green))}
.times{display:flex;justify-content:space-between;color:var(--faint)}
.sc-credit{display:block;margin-top:16px;text-align:center;color:var(--faint)}
.sc-credit:hover{color:var(--text)}
.tl{border-top:1px solid var(--line)}
.tl li{border-bottom:1px solid var(--line)}
.tl button{display:grid;grid-template-columns:44px minmax(0,1fr) 40px;align-items:center;gap:12px;width:100%;min-height:58px;padding:6px 8px;text-align:left;border-radius:10px;transition:background-color .15s}
.tl button:hover{background:var(--bg2)}
.tl .n{font-family:var(--mono);font-size:12px;color:var(--faint)}
.tl .t{font:600 17px/1.2 var(--display);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tl .bars{justify-self:end;opacity:0;color:var(--blue)}
.tl .cur .t{color:var(--blue)}
.tl .cur .bars{opacity:1}
@media (max-width:860px){.sync{grid-template-columns:1fr}.deck{position:relative;top:0}}

/* discography */
.disco{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:clamp(20px,3vw,40px)}
.disco h3{font:700 22px/1.2 var(--display);padding-bottom:12px;border-bottom:1px solid var(--line2);display:flex;justify-content:space-between;align-items:baseline}
.disco h3 small{font-family:var(--mono);font-size:12px;color:var(--faint);font-weight:400}
.disco a{display:grid;grid-template-columns:44px minmax(0,1fr) 16px;gap:10px;align-items:baseline;padding:10px 0;border-bottom:1px solid var(--line)}
.disco a:hover .dt{color:var(--blue)}
.disco .y{font-family:var(--mono);font-size:12px;color:var(--faint)}
.dt{font-weight:500;transition:color .15s}
.da{display:block;font-size:13px;color:var(--dim)}
.disco .ar{color:var(--faint);font-size:13px}
@media (max-width:980px){.disco{grid-template-columns:1fr 1fr}}
@media (max-width:640px){.disco{grid-template-columns:1fr}}

/* about */
.about{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr);gap:clamp(24px,5vw,72px);align-items:start}
.about p.big{font:500 clamp(22px,2.6vw,34px)/1.3 var(--display);letter-spacing:-.015em}
.facts{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);border:1px solid var(--line);border-radius:16px;overflow:hidden}
.facts div{background:var(--bg);padding:22px 20px}
.facts strong{display:block;font:800 clamp(26px,3vw,38px)/1 var(--display);letter-spacing:-.03em}
.facts span{display:block;margin-top:8px;color:var(--dim);font-size:13px}
.credits{display:flex;flex-wrap:wrap;gap:8px;margin-top:28px}
@media (max-width:860px){.about{grid-template-columns:1fr}}

/* contact */
.contact{position:relative;border-radius:24px;overflow:hidden;padding:clamp(28px,6vw,80px);border:1px solid var(--line);isolation:isolate}
.contact::before{content:"";position:absolute;inset:-40%;z-index:-1;background:conic-gradient(from 0deg,rgba(91,116,255,.28),rgba(255,66,98,.22),rgba(57,224,164,.2),rgba(91,116,255,.28));filter:blur(60px);animation:spin 26s linear infinite}
.contact::after{content:"";position:absolute;inset:0;z-index:-1;background:rgba(7,7,10,.72)}
.contact .h2{font-size:clamp(46px,9vw,128px)}
.mail{display:inline-flex;flex-wrap:wrap;align-items:center;gap:12px;margin-top:28px}
.mail a{font:600 clamp(20px,3.4vw,40px)/1.1 var(--display);letter-spacing:-.02em;text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:.18em;overflow-wrap:anywhere}
.mail a:hover{color:var(--blue)}
.cinfo{display:flex;flex-wrap:wrap;gap:8px 28px;margin-top:20px;color:var(--dim)}
.cinfo a:hover{color:var(--text)}
.socials{display:flex;flex-wrap:wrap;gap:8px;margin-top:28px}

.foot{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;padding-block:40px;margin-top:clamp(56px,8vw,96px);border-top:1px solid var(--line);color:var(--faint);font-size:13px}
.foot a:hover{color:var(--text)}

/* player bar */
.pbar{visibility:hidden;position:fixed;left:0;right:0;bottom:0;z-index:70;height:var(--bar);background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border-top:1px solid var(--line);transform:translateY(110%);transition:transform .5s var(--ease)}
.has-bar .pbar{transform:none;visibility:visible}
.pbar-row{display:flex;align-items:center;gap:14px;height:100%}
.pbar-em{width:34px;height:34px;flex:none;animation:spin 6s linear infinite;animation-play-state:paused}
.playing .pbar-em{animation-play-state:running}
.pbar-t{min-width:0;flex:1}
.pbar-t strong{display:block;font:600 15px/1.2 var(--display);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pbar .round{width:40px;height:40px}
.pbar .main{background:var(--text);color:var(--bg);border-color:var(--text)}
.pbar-p{position:absolute;left:0;top:-1px;height:2px;width:0;background:linear-gradient(90deg,var(--red),var(--blue),var(--green))}
@media (max-width:560px){.pbar .hide-s{display:none}}

@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  *,*::before,*::after{animation-duration:.001ms!important;animation-iteration-count:1!important;transition-duration:.001ms!important}
  .reveal{opacity:1;transform:none}
  .gate-word{animation:none}
  .emblem svg{opacity:1}
  .emblem video{display:none}
}
""".strip()


JS = r"""
(() => {
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const body = document.body, reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const store = { get(k){ try { return sessionStorage.getItem(k); } catch(_) { return null; } }, set(k, v){ try { sessionStorage.setItem(k, v); } catch(_) {} } };

/* ---------- SoundCloud (SYNC reel) ---------- */
const P = { w: null, ready: false, list: [], idx: 0, playing: false, want: false, dur: 0 };
const titles = $$('.tl .t').map(t => t.textContent);
const fmt = ms => { const s = Math.max(0, Math.round(ms / 1000)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
function setNow(i){
  P.idx = i;
  const t = (P.list[i] && P.list[i].title) || titles[i] || 'SYNC';
  $$('[data-now]').forEach(n => n.textContent = t);
  $$('.tl button').forEach((b, k) => b.classList.toggle('cur', k === i));
}
function setPlaying(on){
  P.playing = on;
  body.classList.toggle('playing', on);
  $$('[data-toggle]').forEach(b => { b.setAttribute('aria-label', on ? 'Pause' : 'Play'); b.querySelector('use').setAttribute('href', on ? '#i-pause' : '#i-play'); });
  if (on) body.classList.add('has-bar');
}
function scInit(){
  const f = $('#sc');
  if (!f || !window.SC || !SC.Widget) return;
  P.w = SC.Widget(f);
  const E = SC.Widget.Events;
  P.w.bind(E.READY, () => {
    P.ready = true;
    P.w.getSounds(s => { P.list = s || []; P.list.forEach((x, i) => { const el = $$('.tl .t')[i]; if (el && x && x.title) el.textContent = x.title; }); });
    if (P.want) { P.w.play(); }
  });
  P.w.bind(E.PLAY, () => { setPlaying(true); P.w.getCurrentSoundIndex(i => setNow(i)); P.w.getDuration(d => { P.dur = d; $$('[data-dur]').forEach(n => n.textContent = fmt(d)); }); });
  P.w.bind(E.PAUSE, () => setPlaying(false));
  P.w.bind(E.FINISH, () => { if (P.idx >= titles.length - 1) setPlaying(false); });
  P.w.bind(E.PLAY_PROGRESS, e => {
    const r = (e.relativePosition || 0) * 100 + '%';
    $$('[data-prog]').forEach(n => n.style.width = r);
    $$('[data-pos]').forEach(n => n.textContent = fmt(e.currentPosition));
  });
}
const sc = { play(){ P.want = true; body.classList.add('has-bar'); if (P.ready) P.w.play(); },
  toggle(){ if (!P.ready) return sc.play(); P.w.toggle(); },
  next(){ P.ready && P.w.next(); }, prev(){ P.ready && P.w.prev(); },
  at(i){ body.classList.add('has-bar'); setNow(i); if (P.ready) { P.w.skip(i); P.w.play(); } else { P.want = true; } },
  pause(){ P.ready && P.playing && P.w.pause(); } };
if (window.SC) scInit(); else { const s = $('#sc-api'); s && s.addEventListener('load', scInit); }
document.addEventListener('click', ev => {
  const b = ev.target.closest('[data-toggle],[data-next],[data-prev],[data-track],[data-close],[data-seek]');
  if (!b) return;
  if (b.hasAttribute('data-toggle')) sc.toggle();
  else if (b.hasAttribute('data-next')) sc.next();
  else if (b.hasAttribute('data-prev')) sc.prev();
  else if (b.hasAttribute('data-track')) sc.at(+b.dataset.track);
  else if (b.hasAttribute('data-close')) { sc.pause(); body.classList.remove('has-bar'); }
  else if (b.hasAttribute('data-seek') && P.ready && P.dur) { const r = b.getBoundingClientRect(); P.w.seekTo(P.dur * Math.min(1, Math.max(0, (ev.clientX - r.left) / r.width))); }
});

/* ---------- gate ---------- */
const gate = $('#gate');
function leave(withSound){
  if (!gate || gate.hidden) return;
  store.set('lm-in', '1');
  if (withSound) sc.play();
  gate.classList.add('out');
  body.classList.remove('locked');
  setTimeout(() => { gate.hidden = true; const v = $('video', gate); v && v.pause(); }, reduce ? 0 : 1000);
  $('#main').focus({ preventScroll: true });
}
if (gate) {
  if (store.get('lm-in') || (location.hash && location.hash.length > 1)) gate.hidden = true;
  else {
    body.classList.add('locked');
    $('#enter').focus({ preventScroll: true });
    const v = $('video', gate), em = $('.emblem', gate);
    const novid = () => em && em.classList.add('novid');
    if (v && !reduce) { v.addEventListener('error', novid); v.play().catch(novid); } else novid();
  }
  $('#enter').addEventListener('click', () => leave(true));
  $('#enter-quiet').addEventListener('click', ev => { ev.preventDefault(); leave(false); });
  gate.addEventListener('keydown', ev => { if (ev.key === 'Escape') leave(false); });
}

/* ---------- video facades ---------- */
document.addEventListener('click', ev => {
  const b = ev.target.closest('[data-yt]');
  if (!b) return;
  sc.pause();
  const f = document.createElement('iframe');
  f.src = 'https://www.youtube-nocookie.com/embed/' + b.dataset.yt + '?autoplay=1&rel=0&modestbranding=1';
  f.title = b.getAttribute('aria-label') || 'Video';
  f.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
  f.allowFullscreen = true;
  b.parentNode.replaceChild(f, b);
});

/* ---------- work slider ---------- */
const slider = $('#slider');
if (slider) {
  const track = $('.track', slider), slides = $$('.slide', slider), n = slides.length;
  const dots = $$('.progress button'), bgs = $$('.work-bg img');
  let i = 0;
  const go = k => {
    i = (k + n) % n;
    track.style.transform = `translateX(${-i * 100}%)`;
    slides.forEach((s, j) => { s.classList.toggle('cur', j === i); s.setAttribute('aria-hidden', j === i ? 'false' : 'true'); s.inert = j !== i; });
    dots.forEach((d, j) => { d.classList.toggle('cur', j === i); d.classList.toggle('done', j < i); d.setAttribute('aria-current', j === i ? 'true' : 'false'); });
    bgs.forEach((b, j) => b.classList.toggle('on', j === i));
    $('#count').innerHTML = `<b>${String(i + 1).padStart(2, '0')}</b> / ${String(n).padStart(2, '0')}`;
    $('#live').textContent = `${i + 1} of ${n}: ${slides[i].dataset.title}`;
    slides.forEach((s, j) => { if (j !== i) { const f = $('iframe', s); if (f) f.remove(); } });
  };
  // restore facades removed when leaving a slide
  const facades = slides.map(s => { const b = $('[data-yt]', s); return b ? b.cloneNode(true) : null; });
  const restore = () => slides.forEach((s, j) => { const m = $('.media', s); if (facades[j] && m && !$('[data-yt]', m)) m.appendChild(facades[j].cloneNode(true)); });
  const move = k => { go(k); restore(); };
  $('#prev').addEventListener('click', () => move(i - 1));
  $('#next').addEventListener('click', () => move(i + 1));
  dots.forEach((d, j) => d.addEventListener('click', () => move(j)));
  document.addEventListener('keydown', ev => {
    if (gate && !gate.hidden) return;
    if (ev.altKey || ev.ctrlKey || ev.metaKey || /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) return;
    const r = slider.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight) return;
    if (ev.key === 'ArrowRight') { ev.preventDefault(); move(i + 1); }
    if (ev.key === 'ArrowLeft') { ev.preventDefault(); move(i - 1); }
  });
  let x0 = null, y0 = 0;
  slider.addEventListener('pointerdown', ev => { if (ev.pointerType !== 'mouse') { x0 = ev.clientX; y0 = ev.clientY; } });
  slider.addEventListener('pointerup', ev => {
    if (x0 === null) return;
    const dx = ev.clientX - x0, dy = ev.clientY - y0; x0 = null;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) move(i + (dx < 0 ? 1 : -1));
  });
  slider.addEventListener('pointercancel', () => { x0 = null; });
  go(0);
}

/* ---------- reveal + nav state ---------- */
if ('IntersectionObserver' in window && !reduce) {
  const io = new IntersectionObserver(es => es.forEach(en => { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } }), { rootMargin: '0px 0px -10% 0px' });
  $$('.reveal').forEach(el => io.observe(el));
  const links = $$('.nav a');
  const so = new IntersectionObserver(es => es.forEach(en => { if (en.isIntersecting) links.forEach(a => a.classList.toggle('on', a.getAttribute('href') === '#' + en.target.id)); }), { rootMargin: '-45% 0px -50% 0px' });
  $$('main section[id]').forEach(s => so.observe(s));
} else $$('.reveal').forEach(el => el.classList.add('in'));

/* ---------- copy e-mail ---------- */
const cp = $('#copy');
cp && cp.addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(cp.dataset.copy); cp.textContent = 'Copied'; }
  catch (_) { cp.textContent = 'Select & copy'; }
  setTimeout(() => cp.textContent = 'Copy', 1800);
});
})();
""".strip()


def emblem_svg(ROOT, cls="", label=None):
    s = (ROOT / "img" / "lead-major-logo.svg").read_text()
    s = s.replace('fill="#FEFEFE"', 'fill="currentColor"')
    a = f' role="img" aria-label="{e(label)}"' if label else ' aria-hidden="true" focusable="false"'
    return s.replace("<svg ", f'<svg class="{cls}"{a} ', 1)


def symbols(ROOT):
    s = (ROOT / "img" / "lead-major-logo.svg").read_text()
    vb = re.search(r'viewBox="([^"]+)"', s).group(1)
    inner = re.search(r"<svg[^>]*>(.*)</svg>", s, re.S).group(1).replace('fill="#FEFEFE"', 'fill="currentColor"')
    return ('<svg class="sr" width="0" height="0" aria-hidden="true" focusable="false">'
            f'<symbol id="lm" viewBox="{vb}">{inner}</symbol>'
            '<symbol id="i-play" viewBox="0 0 24 24"><path fill="currentColor" d="M8 5.5v13a1 1 0 0 0 1.5.86l10.5-6.5a1 1 0 0 0 0-1.72L9.5 4.64A1 1 0 0 0 8 5.5z"/></symbol>'
            '<symbol id="i-pause" viewBox="0 0 24 24"><path fill="currentColor" d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z"/></symbol>'
            '<symbol id="i-next" viewBox="0 0 24 24"><path fill="currentColor" d="M6 6.5v11a1 1 0 0 0 1.55.83L15 13.2V17h2V7h-2v3.8L7.55 5.67A1 1 0 0 0 6 6.5z"/></symbol>'
            '<symbol id="i-prev" viewBox="0 0 24 24"><path fill="currentColor" d="M18 6.5v11a1 1 0 0 1-1.55.83L9 13.2V17H7V7h2v3.8l7.45-5.13A1 1 0 0 1 18 6.5z"/></symbol>'
            '<symbol id="i-left" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M19 12H5m6-6-6 6 6 6"/></symbol>'
            '<symbol id="i-right" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M5 12h14m-6-6 6 6-6 6"/></symbol>'
            '<symbol id="i-out" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M8 16 16 8m-7 0h7v7"/></symbol>'
            '<symbol id="i-x" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" d="m6 6 12 12M18 6 6 18"/></symbol>'
            '</svg>')


def icon(name, cls="ico"):
    return f'<svg class="{cls}" aria-hidden="true" focusable="false"><use href="#{name}"/></svg>'


def bars(cls="bars"):
    return f'<span class="{cls}" aria-hidden="true"><i></i><i></i><i></i><i></i></span>'


def page(P, I, fonts, domain, ROOT):
    url = domain + P["path"]
    W = P["works"]
    today = dt.date.today()

    # ---------- works ----------
    slides, dots, bgs = [], [], []
    for k, w in enumerate(W):
        im = I[w["image"]]
        wide = w.get("wide")
        cls = "media" + ("" if wide else " sq")
        img = img_tag(I, w["image"], "(min-width:860px) 56vw, 100vw", "img-contain" if w["image"] == "label" else "")
        play = (f'<button class="playbtn" type="button" data-yt="{e(w["video"])}" aria-label="Play the video: {e(w["title"])}">'
                f'<span>{icon("i-play")}</span></button>') if w.get("video") else ""
        roles = "".join(f'<span class="chip">{e(r)}</span>' for r in w["roles"])
        links = "".join(
            f'<a class="btn btn-s" href="{e(l["url"])}" rel="noopener" target="_blank">{e(l["name"])}{icon("i-out", "ico")}'
            f'<span class="sr"> (opens in a new tab)</span></a>' for l in w["links"])
        slides.append(
            f'<article class="slide" id="w-{e(w["slug"])}" data-title="{e(w["title"])}" aria-roledescription="slide" aria-label="{k + 1} of {len(W)}">'
            f'<div class="{cls}">{img}{play}</div>'
            f'<div class="info"><p class="idx mono up"><b>{k + 1:02d}</b> · {e(w["kind"])} · {e(w["year"])}</p>'
            f'<h3 class="wt">{e(w["title"])}</h3><p class="wby">{e(w["by"])}</p>'
            f'<div class="roles">{roles}</div><p class="wtext">{e(w["text"])}</p><div class="wlinks">{links}</div></div></article>')
        dots.append(f'<button type="button" aria-label="Go to {e(w["title"])}"></button>')
        bgs.append(f'<img src="{e(im["src"])}" alt="" loading="lazy" decoding="async">')

    # ---------- sync ----------
    S = P["sync"]
    tracks = "".join(
        f'<li><button type="button" data-track="{k}"><span class="n">{k + 1:02d}</span><span class="t">{e(t)}</span>{bars()}</button></li>'
        for k, t in enumerate(S["tracks"]))
    sc_src = ("https://w.soundcloud.com/player/?url=" + urllib.parse.quote(S["url"], safe="")
              + "&auto_play=false&visual=false&hide_related=true&show_comments=false&show_user=true"
              + "&show_reposts=false&show_teaser=false&buying=false&sharing=false&download=false&color=%235b74ff")

    # ---------- discography ----------
    disco = []
    for g in P["discography"]:
        rows = "".join(
            f'<li><a href="https://music.apple.com/album/{it[3]}" rel="noopener" target="_blank">'
            f'<span class="y">{e(it[0])}</span><span><span class="dt">{e(it[1])}</span><span class="da">{e(it[2])}</span></span>'
            f'<span class="ar" aria-hidden="true">↗</span><span class="sr"> on Apple Music (opens in a new tab)</span></a></li>'
            for it in g["items"])
        disco.append(f'<div class="reveal"><h3>{e(g["group"])} <small>{len(g["items"])}</small></h3><ul>{rows}</ul></div>')
    total = sum(len(g["items"]) for g in P["discography"])

    facts = "".join(f'<div><strong>{e(a)}</strong><span>{e(b)}</span></div>' for a, b in P["facts"])
    credits = "".join(f'<span class="chip">{e(c)}</span>' for c in P["credits"])
    socials = "".join(f'<a class="btn btn-s" href="{e(s["url"])}" rel="noopener me" target="_blank">{e(s["name"])}</a>' for s in P["socials"])
    ticker_items = [f"{t}" for t in ["Composer", "Sound engineer", "Mix & master", "Sound design", "Audio post"] + P["credits"]]
    ticker = "".join(f'<span class="mono up">{e(t)}</span>' for t in ticker_items) * 2
    tags = "".join(f'<span class="chip">{e(t)}</span>' for t in P["tags"])
    tel = "tel:" + re.sub(r"[^+\d]", "", P["phone"])

    # ---------- structured data ----------
    same = [s["url"] for s in P["socials"]] + ["https://www.wikidata.org/wiki/Q141470222"]
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "ProfilePage", "@id": url, "url": url, "name": P["title"], "description": P["description"],
         "inLanguage": "en", "isPartOf": {"@id": f"{domain}/#website"}, "mainEntity": {"@id": f"{domain}/#lead-major"},
         "dateModified": today.isoformat(),
         "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
             {"@type": "ListItem", "position": 1, "name": "3rd Records", "item": f"{domain}/"},
             {"@type": "ListItem", "position": 2, "name": "Lead Major", "item": url}]}},
        {"@type": ["Person", "MusicGroup"], "@id": f"{domain}/#lead-major", "name": P["name"], "alternateName": P["person"],
         "url": url, "email": P["email"], "jobTitle": "Composer and sound engineer",
         "knowsAbout": ["Music composition", "Music production", "Mixing", "Mastering", "Sound design", "Audio post-production"],
         "image": domain + "/img/lead-major.webp", "sameAs": same,
         "memberOf": {"@id": f"{domain}/#label"}, "founder": None},
    ]}
    ld["@graph"][1].pop("founder")
    ld_json = json.dumps(ld, ensure_ascii=False, separators=(",", ":"))

    css = CSS
    if not fonts:
        css = re.sub(r"@font-face\{[^}]*\}", "", css)
    css = "".join(l.strip() for l in css.splitlines())
    js = JS
    sh = lambda s: base64.b64encode(hashlib.sha256(s.encode()).digest()).decode()
    img_origins = sorted({o for o in (origin(i["src"]) for i in I.values() if i["src"].startswith("https://")) if o})
    csp = (f"default-src 'none'; base-uri 'none'; form-action 'none'; connect-src 'self'; "
           f"img-src 'self' data: {' '.join(img_origins)}; font-src 'self'; media-src 'self'; "
           f"style-src 'sha256-{sh(css)}'; script-src 'sha256-{sh(js)}' https://w.soundcloud.com; "
           "frame-src https://w.soundcloud.com https://www.youtube-nocookie.com")
    og = I["ikh"]["src"]
    og = og if og.startswith("http") else url + og

    first_bg = I["portrait"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(P["title"])}</title>
<meta name="description" content="{e(P["description"])}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<link rel="canonical" href="{url}">
<meta property="og:type" content="profile"><meta property="og:site_name" content="3rd Records">
<meta property="og:title" content="{e(P["title"])}"><meta property="og:description" content="{e(P["description"])}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{e(og)}"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#07070a">
<link rel="icon" href="/img/lead-major-logo.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
{''.join(f'<link rel="preload" href="{f}" as="font" type="font/woff2" crossorigin>' for k, f in fonts.items() if k != "mono")}
<style>{css}</style>
<script type="application/ld+json">{ld_json}</script>
</head><body>
{symbols(ROOT)}
<div class="gate" id="gate" role="dialog" aria-modal="true" aria-label="Welcome to the Lead Major portfolio">
  <div class="gate-bg" aria-hidden="true"><img src="{e(I["ikh"]["src"])}" alt=""></div>
  <div class="gate-vig" aria-hidden="true"></div><div class="gate-glow" aria-hidden="true"></div>
  <div class="gate-in">
    <div class="emblem" aria-hidden="true"><video src="/img/lead-major.mp4" muted playsinline preload="auto" disablepictureinpicture></video><svg viewBox="0 0 2154 2106"><use href="#lm"/></svg></div>
    <p class="gate-word chroma">Lead Major</p>
    <button class="enter" type="button" id="enter">Enter</button>
    <a class="quiet" href="#main" id="enter-quiet">Enter without sound</a>
    <p class="gate-hint mono up">Composer · Sound engineer · {e(P["location"])}</p>
  </div>
</div>
<a class="skip" href="#main">Skip to content</a>
<div class="grain" aria-hidden="true"></div>
<header class="head"><div class="wrap head-row">
  <a class="brand" href="#top" aria-label="Lead Major, back to top"><svg viewBox="0 0 2154 2106" aria-hidden="true"><use href="#lm"/></svg><span>lead<b>.</b>major</span></a>
  <nav class="nav" aria-label="Sections"><ul>
    <li><a href="#work">Work</a></li><li><a href="#showreel">Showreel</a></li><li><a href="#sync">Sync</a></li>
    <li><a href="#discography">Discography</a></li><li><a href="#about">About</a></li><li><a href="#contact">Contact</a></li></ul></nav>
  <div class="head-act">
    <button class="eq" type="button" data-toggle aria-label="Play">{bars()}<svg class="sr"><use href="#i-play"/></svg></button>
    <a class="btn btn-s" href="#contact">Let’s talk</a>
  </div>
</div></header>

<main id="main" tabindex="-1">
<section class="stage" id="top" aria-labelledby="h1">
  <div class="wrap stage-grid">
    <div>
      <p class="kick mono up">{e(P["person"])} · Portfolio</p>
      <h1 class="h1 chroma" id="h1"><span>Lead</span><span>Major</span></h1>
      <p class="lede">{e(P["lede"])}</p>
      <p class="sub">{e(P["sub"])}</p>
      <div class="tags">{tags}</div>
      <div class="cta"><a class="btn btn-p" href="#work">See the work {icon("i-right")}</a>
        <button class="btn" type="button" data-toggle aria-label="Play">{icon("i-play")}<span>Play the sync reel</span></button></div>
    </div>
    <div class="orb">
      <div class="orb-clip">{img_tag(I, "portrait", "(min-width:780px) 34vw, 64vw", eager=True)}</div>
      <div class="ring" aria-hidden="true"><svg viewBox="0 0 2154 2106"><use href="#lm"/></svg></div>
    </div>
  </div>
  <div class="ticker" aria-hidden="true"><div class="ticker-track">{ticker}</div></div>
</section>

<section class="sec work" id="work" aria-labelledby="work-h">
  <div class="work-bg" aria-hidden="true">{''.join(bgs)}</div>
  <div class="wrap">
    <div class="sec-head">
      <div><p class="label mono up">Selected work</p><h2 class="h2" id="work-h">Projects</h2></div>
      <div class="ctrl"><button class="round" type="button" id="prev" aria-label="Previous project">{icon("i-left")}</button>
        <p class="count" id="count" aria-hidden="true"><b>01</b> / {len(W):02d}</p>
        <button class="round" type="button" id="next" aria-label="Next project">{icon("i-right")}</button></div>
    </div>
    <div class="slider" id="slider" aria-roledescription="carousel" aria-label="Selected projects">
      <p class="sr" aria-live="polite" id="live"></p>
      <div class="track">{''.join(slides)}</div>
    </div>
    <div class="progress" role="group" aria-label="Choose a project">{''.join(dots)}</div>
    <p class="hint-keys mono">Use <kbd>←</kbd> <kbd>→</kbd> to browse</p>
  </div>
</section>

<section class="sec" id="showreel" aria-labelledby="reel-h">
  <div class="wrap">
    <div class="sec-head reveal"><div><p class="label mono up">Know-how</p><h2 class="h2" id="reel-h">Showreel</h2></div>
      <p class="dim">Music and sound design, in two minutes.</p></div>
    <div class="reel reveal">{img_tag(I, P["showreel"]["image"], "(min-width:1240px) 1160px, 100vw")}
      <button class="playbtn" type="button" data-yt="{e(P["showreel"]["video"])}" aria-label="Play the showreel"><span>{icon("i-play")}</span></button>
      <p class="reel-cap"><span class="mono up dim">Music + sound design</span><strong>{e(P["showreel"]["title"])}</strong></p>
    </div>
  </div>
</section>

<section class="sec" id="sync" aria-labelledby="sync-h">
  <div class="wrap">
    <div class="sec-head reveal"><div><p class="label mono up">Music for picture</p><h2 class="h2" id="sync-h">Sync reel</h2></div>
      <p class="dim">{len(S["tracks"])} cues, from jazz noir to orchestral and hyperpop.</p></div>
    <div class="sync">
      <div class="deck reveal">
        <div class="disc" aria-hidden="true"><svg viewBox="0 0 2154 2106"><use href="#lm"/></svg></div>
        <div class="now" aria-live="polite"><span class="mono up dim">Now playing</span><strong data-now>{e(S["tracks"][0])}</strong></div>
        <div class="seek" data-seek role="presentation"><i data-prog></i></div>
        <div class="times mono"><span data-pos>0:00</span><span data-dur>–:––</span></div>
        <div class="transport">
          <button class="round" type="button" data-prev aria-label="Previous cue">{icon("i-prev")}</button>
          <button class="round big" type="button" data-toggle aria-label="Play"><svg class="ico" aria-hidden="true"><use href="#i-play"/></svg></button>
          <button class="round" type="button" data-next aria-label="Next cue">{icon("i-next")}</button>
        </div>
        <a class="sc-credit mono" href="{e(S["url"])}" rel="noopener" target="_blank">Listen on SoundCloud ↗</a>
      </div>
      <ol class="tl reveal">{tracks}</ol>
    </div>
    <iframe id="sc" class="sr" title="SoundCloud player: SYNC by Lead Major" src="{e(sc_src)}" allow="autoplay" loading="eager" tabindex="-1"></iframe>
  </div>
</section>

<section class="sec" id="discography" aria-labelledby="disco-h">
  <div class="wrap">
    <div class="sec-head reveal"><div><p class="label mono up">Everything released</p><h2 class="h2" id="disco-h">Discography</h2></div>
      <p class="dim">{total} releases since 2018 · links open Apple Music</p></div>
    <div class="disco">{''.join(disco)}</div>
  </div>
</section>

<section class="sec" id="about" aria-labelledby="about-h">
  <div class="wrap about">
    <div class="reveal"><p class="label mono up">About</p><h2 class="sr" id="about-h">About Lead Major</h2>
      <p class="big">{e(P["about"])}</p>
      <div class="credits" aria-label="Worked with">{credits}</div></div>
    <div class="facts reveal">{facts}</div>
  </div>
</section>

<section class="sec" id="contact" aria-labelledby="contact-h">
  <div class="wrap"><div class="contact reveal">
    <p class="label mono up">Let’s collaborate</p>
    <h2 class="h2" id="contact-h">Tell me about<br>your project.</h2>
    <p class="mail"><a href="mailto:{e(P["email"])}">{e(P["email"])}</a><button class="btn btn-s" type="button" id="copy" data-copy="{e(P["email"])}">Copy</button></p>
    <p class="cinfo mono"><a href="{tel}">{e(P["phone"])}</a><span>{e(P["location"])}</span></p>
    <div class="socials">{socials}</div>
  </div></div>
</section>
</main>

<footer class="wrap foot"><span>© {today.year} {e(P["person"])} · Lead Major</span><span>Part of <a href="/">3rd Records</a> · <a href="/news/">News</a></span></footer>

<aside class="pbar" aria-label="Sync reel player"><div class="pbar-p" data-prog></div><div class="wrap pbar-row">
  <svg class="pbar-em" viewBox="0 0 2154 2106" aria-hidden="true"><use href="#lm"/></svg>
  <p class="pbar-t"><span class="mono up dim">Sync reel</span><strong data-now>{e(S["tracks"][0])}</strong></p>
  <span class="mono dim hide-s" data-pos>0:00</span>
  <button class="round hide-s" type="button" data-prev aria-label="Previous cue">{icon("i-prev")}</button>
  <button class="round main" type="button" data-toggle aria-label="Play"><svg class="ico" aria-hidden="true"><use href="#i-play"/></svg></button>
  <button class="round" type="button" data-next aria-label="Next cue">{icon("i-next")}</button>
  <button class="round" type="button" data-close aria-label="Stop and close the player">{icon("i-x")}</button>
</div></aside>
<script id="sc-api" src="https://w.soundcloud.com/player/api.js" defer></script>
<script>{js}</script>
</body></html>
"""


def build(DIST, domain="https://3rdrecords.com"):
    ROOT = HERE.parent
    P = json.loads((HERE / "leadmajor.json").read_text(encoding="utf-8"))
    out = DIST / P["path"].strip("/")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    I = prepare_images(P, out, domain)
    fonts = prepare_fonts(P, out)
    (out / "index.html").write_text(page(P, I, fonts, domain, ROOT), encoding="utf-8")
    return [P["path"]]


if __name__ == "__main__":
    import sys
    d = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else HERE.parent / "dist")
    print(build(d))
