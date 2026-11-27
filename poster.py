"""vGudia posters, made for free: an HTML design in the vGudia style + a real stock photo,
rendered to JPEG with a headless browser. The Bengali text is typed, so it is always exact.

Photos: Pexels (free API key, best quality) or, without a key, Openverse public-domain photos.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import pathlib
import re

import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "vgudia-bot/1.0"}

BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
BN_MONTHS = ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই",
             "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]
NOTICE = "শুধুমাত্র তথ্যের জন্য, বিনিয়োগ পরামর্শ নয়"
SWIPE = "সোয়াইপ করুন →"
COMMENT_CTA = "আপনার মত কমেন্টে জানান"


def bn_num(n: int) -> str:
    return str(n).translate(BN_DIGITS)


def bengali_date(day: dt.date) -> str:
    return f"{bn_num(day.day)} {BN_MONTHS[day.month - 1]} {bn_num(day.year)}"


# ---------------------------------------------------------------- photos

def _download(url: str, dest: str) -> bool:
    try:
        r = requests.get(url, headers=UA, timeout=60)
        if r.status_code == 200 and len(r.content) > 20_000:
            with open(dest, "wb") as f:
                f.write(r.content)
            return True
    except requests.RequestException:
        pass
    return False


def _pexels(query: str, used: set[str], dest: str) -> bool:
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        return False
    try:
        r = requests.get("https://api.pexels.com/v1/search", timeout=30,
                         params={"query": query, "per_page": 20, "orientation": "landscape"},
                         headers={"Authorization": key})
        photos = r.json().get("photos", []) if r.status_code == 200 else []
    except (requests.RequestException, ValueError):
        return False
    for p in photos:
        pid = f"pexels:{p['id']}"
        if pid in used:
            continue
        if _download(p["src"].get("large2x") or p["src"]["original"], dest):
            used.add(pid)
            return True
    return False


def _openverse(query: str, used: set[str], dest: str) -> bool:
    try:
        r = requests.get("https://api.openverse.org/v1/images/", headers=UA, timeout=30,
                         params={"q": query, "license": "cc0,pdm", "page_size": 20,
                                 "aspect_ratio": "wide", "size": "large"})
        results = r.json().get("results", []) if r.status_code == 200 else []
    except (requests.RequestException, ValueError):
        return False
    for p in results:
        pid = f"openverse:{p['id']}"
        if pid in used or (p.get("width") or 0) < 1200:
            continue
        if _download(p["url"], dest):
            used.add(pid)
            return True
    return False


def find_photo(query: str, used: set[str], dest: str) -> str | None:
    """Download a fresh photo for `query` to `dest`. Returns the path, or None (design falls back)."""
    for q in (query, " ".join(query.split()[:2]), "stock market"):
        if q and _pexels(q, used, dest):
            return dest
    # Openverse public-domain photos are often old archive pictures or charts with foreign
    # numbers on them, so they are only used when explicitly turned on.
    if os.getenv("USE_OPENVERSE") == "1" and _openverse(query, used, dest):
        return dest
    return None


# ---------------------------------------------------------------- logos

LOGO_DIR = os.path.join(ROOT, "logos")
_WIKI = "https://en.wikipedia.org/w/api.php"
_LOGO_FIELD = re.compile(r"\|\s*logo\s*=\s*(?:\[\[)?(?:File:|Image:)?\s*([^|\]\n{}]+?\.(?:svg|png|jpe?g|gif|webp))",
                         re.IGNORECASE)


def _wiki_ua() -> dict:
    repo = os.getenv("GITHUB_REPOSITORY", "vgudia-bot")
    return {"User-Agent": f"vgudia-bot/1.0 (https://github.com/{repo}; news poster maker)"}


def _slug(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (key or "").lower()).strip("-")[:60]


def _missing_cache() -> dict:
    path = os.path.join(LOGO_DIR, "_missing.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _mark_missing(key: str) -> None:
    data = _missing_cache()
    data[key] = dt.date.today().isoformat()
    os.makedirs(LOGO_DIR, exist_ok=True)
    with open(os.path.join(LOGO_DIR, "_missing.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True)


def get_logo(wiki_title: str, key: str) -> str | None:
    """Path to the organisation's logo, from logos/ or fetched once from its Wikipedia infobox.

    Put your own file at logos/<key>.png (or .svg/.jpg) to override or fix a logo.
    """
    key = _slug(key)
    if not key or not (wiki_title or "").strip():
        return None
    for ext in ("png", "svg", "jpg", "jpeg", "webp"):
        path = os.path.join(LOGO_DIR, f"{key}.{ext}")
        if os.path.exists(path):
            return path
    missed = _missing_cache().get(key)
    if missed and (dt.date.today() - dt.date.fromisoformat(missed)).days < 30:
        return None
    try:
        r = requests.get(_WIKI, headers=_wiki_ua(), timeout=20, params={
            "action": "parse", "format": "json", "prop": "wikitext", "section": 0,
            "redirects": 1, "page": wiki_title})
        if r.status_code == 429:
            return None  # rate limited: try again another time, don't remember as missing
        wikitext = r.json().get("parse", {}).get("wikitext", {}).get("*", "")
        m = _LOGO_FIELD.search(wikitext)
        if not m:
            _mark_missing(key)
            return None
        info = requests.get(_WIKI, headers=_wiki_ua(), timeout=20, params={
            "action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url",
            "iiurlwidth": 400, "titles": f"File:{m.group(1).strip()}"}).json()
        page = next(iter(info.get("query", {}).get("pages", {}).values()), {})
        url = (page.get("imageinfo") or [{}])[0].get("thumburl")
        if not url:
            _mark_missing(key)
            return None
        img = requests.get(url, headers=_wiki_ua(), timeout=30)
        if img.status_code != 200 or len(img.content) < 500:
            return None
        ext = "png" if ".png" in url.lower() else ("jpg" if re.search(r"\.jpe?g", url.lower()) else "png")
        os.makedirs(LOGO_DIR, exist_ok=True)
        path = os.path.join(LOGO_DIR, f"{key}.{ext}")
        with open(path, "wb") as f:
            f.write(img.content)
        return path
    except (requests.RequestException, ValueError):
        return None


# ---------------------------------------------------------------- icons

ICONS = {
    "chart-up": '<path d="M5 33h30"/><rect x="8" y="22" width="5" height="9" fill="#fff"/><rect x="17" y="16" width="5" height="15" fill="#fff"/><rect x="26" y="10" width="5" height="21" fill="#fff"/><path d="M7 15l9-7 6 4 11-8"/><path d="M28 4h5v5"/>',
    "chart-down": '<path d="M5 33h30"/><rect x="8" y="12" width="5" height="19" fill="#fff"/><rect x="17" y="18" width="5" height="13" fill="#fff"/><rect x="26" y="24" width="5" height="7" fill="#fff"/><path d="M7 6l9 7 6-4 11 8"/><path d="M28 17h5v-5"/>',
    "bank": '<path d="M20 4l15 8H5z" fill="#fff"/><path d="M8 16v14M16 16v14M24 16v14M32 16v14"/><path d="M4 34h32"/>',
    "globe": '<circle cx="20" cy="20" r="15"/><path d="M5 20h30M20 5c5 5 5 25 0 30M20 5c-5 5-5 25 0 30"/>',
    "handshake": '<path d="M4 14l8-6 8 5 8-5 8 6"/><path d="M12 8l-4 14 8 8 4-3 4 3 8-8-4-14"/><path d="M16 22l4 4M20 19l5 5"/>',
    "target": '<circle cx="20" cy="20" r="15"/><circle cx="20" cy="20" r="9"/><circle cx="20" cy="20" r="3" fill="#fff"/>',
    "coins": '<ellipse cx="20" cy="10" rx="12" ry="5"/><path d="M8 10v8c0 3 5 5 12 5s12-2 12-5v-8"/><path d="M8 18v8c0 3 5 5 12 5s12-2 12-5v-8"/>',
    "oil": '<rect x="10" y="6" width="20" height="28" rx="3"/><path d="M10 14h20M10 26h20"/><path d="M20 17c-3 4-3 6 0 7 3-1 3-3 0-7z" fill="#fff"/>',
    "factory": '<path d="M4 34V18l8 5v-5l8 5v-5l8 5V6h6v28z"/><path d="M10 28h4M18 28h4M26 28h4"/>',
    "ship": '<path d="M4 26h32l-5 8H9z"/><path d="M10 26V16h20v10"/><path d="M16 16V9h8v7"/>',
    "warning": '<path d="M20 5l16 28H4z"/><path d="M20 15v9"/><circle cx="20" cy="28" r="1.5" fill="#fff"/>',
    "document": '<path d="M10 4h14l6 6v26H10z"/><path d="M24 4v6h6M15 18h10M15 24h10M15 30h6"/>',
}


def _icon(name: str) -> str:
    return (f'<svg viewBox="0 0 40 40" fill="none" stroke="#fff" stroke-width="3" '
            f'stroke-linecap="round" stroke-linejoin="round">{ICONS.get(name, ICONS["chart-up"])}</svg>')


# ---------------------------------------------------------------- HTML

CSS = """
:root{--navy:#0b2a6b;--navy-deep:#071d4d;--saffron:#ff7a00;--saffron-2:#ff9a1f;--yellow:#ffc928;--ink:#0d1b3d;--bg:#eef4fd}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1080px;overflow:hidden;background:var(--bg)}
body{font-family:'Noto Sans Bengali','Hind Siliguri',sans-serif;color:var(--ink)}
.en{font-family:'Poppins',sans-serif}
.page{position:relative;width:1080px;height:1080px;display:flex;flex-direction:column}
.hero{position:relative;flex:1 1 auto;min-height:360px;padding:30px 40px 18px;overflow:hidden}
.photo{position:absolute;inset:0;background-size:cover;background-position:center}
.photo.none{background:radial-gradient(800px 420px at 85% 10%,#cfe0ff 0%,transparent 60%),linear-gradient(180deg,#e4eefc,#f3f7fe)}
.fade{position:absolute;inset:0;background:
  linear-gradient(90deg,rgba(238,244,253,.97) 0%,rgba(238,244,253,.93) 40%,rgba(238,244,253,.35) 66%,rgba(238,244,253,0) 82%),
  linear-gradient(180deg,rgba(238,244,253,0) 72%,var(--bg) 100%)}
.hero>*:not(.photo):not(.fade){position:relative}
.tag{display:inline-flex;align-items:center;gap:14px;background:var(--navy);color:#fff;padding:8px 24px 8px 20px;
  border-radius:6px 22px 22px 6px;border-left:10px solid var(--saffron);font-size:24px;box-shadow:0 6px 16px rgba(7,29,77,.3)}
.tag .en{font-style:italic;font-weight:800;letter-spacing:.4px}
.tag .sep{width:2px;height:24px;background:rgba(255,255,255,.55)}
.badge{position:absolute!important;top:30px;right:40px;background:var(--saffron);color:#fff;font-weight:800;font-size:26px;
  padding:6px 18px;border-radius:20px;box-shadow:0 6px 14px rgba(255,122,0,.4)}
h1{margin-top:16px;max-width:640px;font-weight:900;font-size:76px;line-height:1.14;color:var(--navy-deep);
  text-shadow:0 2px 0 rgba(255,255,255,.8)}
h1 .accent{color:var(--saffron)}
.brush{display:inline-block;margin-top:14px;padding:6px 36px 12px 26px;color:#fff;font-weight:900;font-size:42px;line-height:1.25;position:relative;isolation:isolate;max-width:700px}
.brush::before{content:"";position:absolute;inset:0;z-index:-1;background:linear-gradient(90deg,var(--saffron),var(--saffron-2));
  clip-path:polygon(1% 12%,8% 0,30% 6%,60% 0,92% 4%,100% 18%,98% 60%,100% 92%,70% 100%,40% 94%,10% 100%,0 86%,2% 50%);
  filter:drop-shadow(0 6px 10px rgba(255,122,0,.35))}
.brush span{position:relative}
.strip{margin:6px 40px 0;background:#fff;border-radius:18px;padding:34px 16px 16px;position:relative;
  box-shadow:0 10px 26px rgba(11,42,107,.14);display:flex}
.strip .title{position:absolute;top:-22px;left:50%;transform:translateX(-50%);background:var(--navy);color:#fff;
  font-weight:700;font-size:26px;padding:6px 28px;border-radius:24px;white-space:nowrap;box-shadow:0 6px 14px rgba(7,29,77,.3)}
.item{flex:1;text-align:center;padding:4px 8px;border-left:1px solid #e3e9f5}
.item:first-child{border-left:0}
.item .label{font-family:'Poppins','Noto Sans Bengali',sans-serif;font-weight:600;font-size:21px;line-height:1.2;color:var(--ink);min-height:50px;display:flex;align-items:center;justify-content:center}
.item .value{margin-top:6px;display:inline-block;background:#e9eef7;border-radius:12px;padding:6px 14px;
  font-family:'Poppins','Noto Sans Bengali',sans-serif;font-weight:800;font-size:26px;color:var(--navy-deep)}
.item.hi{background:#fff3e3;border-radius:12px}
.item.hi .label{color:var(--saffron);font-weight:800}
.item.hi .value{background:linear-gradient(90deg,var(--saffron),var(--saffron-2));color:#fff}
.cards{margin:20px 40px 0;display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.card{background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 10px 24px rgba(11,42,107,.16);border-bottom:6px solid var(--saffron);display:flex;flex-direction:column}
.card .hd{display:flex;align-items:center;gap:12px;padding:10px 16px;background:var(--navy);color:#fff;font-weight:700;font-size:26px;line-height:1.15;min-height:66px}
.card.red .hd{background:linear-gradient(135deg,#c8102e,#e2363f)}
.card .hd svg{flex:none;width:40px;height:40px}
.card .bd{padding:12px 16px 14px;font-size:24px;font-weight:700;line-height:1.36;text-align:center;flex:1;display:flex;align-items:center;justify-content:center}
.notice{margin:18px auto 14px;display:flex;align-items:center;gap:12px;background:var(--yellow);padding:8px 28px;border-radius:30px;
  font-size:24px;font-weight:700;box-shadow:0 6px 14px rgba(255,201,40,.4)}
.notice svg{width:30px;height:30px}
footer{flex:none;height:100px;position:relative;background:linear-gradient(180deg,var(--navy),var(--navy-deep));
  display:flex;align-items:center;justify-content:space-between;padding:0 50px;color:#fff}
footer::before{content:"";position:absolute;left:0;right:0;top:-7px;height:7px;background:linear-gradient(90deg,var(--saffron),var(--yellow),var(--saffron))}
.logo{font-family:'Poppins',sans-serif;font-weight:800;font-size:56px;letter-spacing:-1px}
.logo .v{color:var(--saffron)}
.logo img{height:64px;display:block}
.vsep{width:2px;height:50px;background:rgba(255,255,255,.4)}
.tagline{font-family:'Poppins',sans-serif;font-style:italic;font-weight:600;font-size:30px}
.bn-tag{color:var(--yellow);font-weight:800;font-size:36px}
/* carousel detail slide */
.slide-hero{min-height:330px;flex:0 0 330px}
.slide-title{margin-top:18px;max-width:720px;font-weight:900;font-size:62px;line-height:1.18;color:var(--navy-deep)}
.underline{margin-top:10px;width:220px;height:12px;border-radius:8px;background:linear-gradient(90deg,var(--saffron),var(--saffron-2))}
.points{flex:1;margin:0 40px;background:#fff;border-radius:22px;box-shadow:0 12px 30px rgba(11,42,107,.16);border-top:8px solid var(--navy);
  padding:26px 34px;display:flex;flex-direction:column;justify-content:space-evenly}
.pt{display:flex;gap:20px;align-items:flex-start;font-size:34px;font-weight:700;line-height:1.35}
.pt .n{flex:none;width:52px;height:52px;border-radius:50%;background:var(--saffron);color:#fff;display:grid;place-items:center;font-size:28px;font-weight:800;margin-top:2px}
.slide-bottom{display:flex;align-items:center;justify-content:center;gap:18px;margin:18px 40px 16px}
.pill{background:var(--saffron);color:#fff;font-weight:800;font-size:28px;padding:8px 26px;border-radius:26px;box-shadow:0 6px 14px rgba(255,122,0,.35)}
.pill.navy{background:var(--navy)}
.logo-card{position:absolute!important;right:40px;top:100px;width:250px;height:140px;background:#fff;border-radius:18px;
  box-shadow:0 10px 26px rgba(7,29,77,.28);display:flex;align-items:center;justify-content:center;padding:18px 22px}
.logo-card img{max-width:100%;max-height:100%;object-fit:contain}
.item .ilogo{height:46px;max-width:150px;object-fit:contain;display:block;margin:0 auto 6px}
.bottomrow{display:flex;justify-content:center;align-items:center;gap:16px;margin:18px 40px 14px}
.bottomrow .notice{margin:0}
.candles{position:absolute;right:30px;top:70px;width:470px;height:270px;opacity:.75}
"""

FIT_JS = """
function shrink(el, maxH, min){ if(!el) return; let s=parseFloat(getComputedStyle(el).fontSize);
  while(el.scrollHeight>maxH && s>min){ s-=2; el.style.fontSize=s+'px'; } }
function fitAll(){
  shrink(document.querySelector('h1'), 270, 44);
  shrink(document.querySelector('.slide-title'), 160, 40);
  shrink(document.querySelector('.brush'), 120, 28);
  document.querySelectorAll('.card .bd').forEach(e=>shrink(e, 150, 17));
  document.querySelectorAll('.item .label').forEach(e=>shrink(e, 52, 14));
  const pts=document.querySelector('.points');
  if(pts){ let s=34; while(pts.scrollHeight>pts.clientHeight+2 && s>20){ s-=2; pts.querySelectorAll('.pt').forEach(p=>p.style.fontSize=s+'px'); } }
  const page=document.querySelector('.page'); let guard=0;
  while(page.scrollHeight>1080 && guard++<30){ document.querySelectorAll('.card .bd,.item .label').forEach(e=>{e.style.fontSize=(parseFloat(getComputedStyle(e).fontSize)-1)+'px'});
    const h=document.querySelector('h1'); if(h) h.style.fontSize=(parseFloat(getComputedStyle(h).fontSize)-2)+'px'; }
}
window.__fit = fitAll;
"""

FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@600;700;800;900'
         '&family=Poppins:ital,wght@0,600;0,800;1,600;1,800&display=block" rel="stylesheet">')

WARN_SVG = ('<svg viewBox="0 0 40 40" fill="none" stroke="#0d1b3d" stroke-width="3" stroke-linejoin="round">'
            '<path d="M20 5l16 28H4z"/><path d="M20 15v9"/><circle cx="20" cy="28" r="1.5" fill="#0d1b3d"/></svg>')


def _e(text: str) -> str:
    return html.escape(text or "")


def _footer() -> str:
    logo_file = os.path.join(ROOT, "logo.png")
    logo = (f'<img src="{pathlib.Path(logo_file).as_uri()}" alt="vGudia">' if os.path.exists(logo_file)
            else '<span class="v">v</span>Gudia')
    return (f'<footer><div class="logo">{logo}</div><div class="vsep"></div>'
            f'<div class="tagline">Making Market Simple</div><div class="vsep"></div>'
            f'<div class="bn-tag">বাজারকে সহজ করা</div></footer>')


def _doc(body: str) -> str:
    return (f'<!doctype html><html lang="bn"><head><meta charset="utf-8">{FONTS}<style>{CSS}</style></head>'
            f'<body>{body}<script>{FIT_JS}</script></body></html>')


def _photo_div(photo: str | None) -> str:
    if photo:
        return f'<div class="photo" style="background-image:url(\'{pathlib.Path(photo).as_uri()}\')"></div>'
    return f'<div class="photo none">{CANDLES_SVG}</div>'


CANDLES_SVG = """<svg class="candles" viewBox="0 0 420 240" aria-hidden="true">
<defs><linearGradient id="g" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#ff7a00" stop-opacity="0"/><stop offset="1" stop-color="#ff7a00" stop-opacity=".9"/></linearGradient></defs>
<polyline points="10,210 60,190 100,200 150,160 200,170 250,120 300,130 350,70 410,30" fill="none" stroke="url(#g)" stroke-width="5" stroke-linecap="round"/>
<g fill="#22a35a"><rect x="40" y="170" width="14" height="40"/><rect x="46" y="160" width="2" height="60"/>
<rect x="140" y="140" width="14" height="45"/><rect x="146" y="128" width="2" height="66"/>
<rect x="240" y="100" width="14" height="45"/><rect x="246" y="88" width="2" height="68"/>
<rect x="340" y="55" width="14" height="45"/><rect x="346" y="42" width="2" height="68"/>
<rect x="390" y="25" width="14" height="40"/><rect x="396" y="12" width="2" height="62"/></g>
<g fill="#d9534f"><rect x="90" y="175" width="14" height="35"/><rect x="96" y="165" width="2" height="55"/>
<rect x="190" y="150" width="14" height="30"/><rect x="196" y="140" width="2" height="50"/>
<rect x="290" y="110" width="14" height="30"/><rect x="296" y="98" width="2" height="52"/></g></svg>"""


def _tag(plan: dict, day: dt.date) -> str:
    return (f'<div class="tag"><span class="en">{_e(plan["category_tag"])}</span><span class="sep"></span>'
            f'<span>{bengali_date(day)}</span></div>')


def _img(path: str | None, cls: str = "") -> str:
    return f'<img class="{cls}" src="{pathlib.Path(path).as_uri()}" alt="">' if path else ""


def cover_html(plan: dict, day: dt.date, photo: str | None, total: int = 1,
               main_logo: str | None = None, item_logos: list | None = None) -> str:
    item_logos = item_logos or []
    headline = _e(plan["headline"])
    accent = _e(plan.get("headline_accent", ""))
    if accent and accent in headline:
        headline = headline.replace(accent, f'<span class="accent">{accent}</span>', 1)

    strip = ""
    items = plan.get("data_items") or []
    if len(items) >= 2:
        cells = "".join(
            f'<div class="item{" hi" if d.get("highlight") else ""}">'
            f'{_img(item_logos[i] if i < len(item_logos) else None, "ilogo")}'
            f'<div class="label">{_e(d["label"])}</div>'
            f'<div class="value">{_e(d["value"])}</div></div>' for i, d in enumerate(items[:5]))
        strip = f'<div class="strip"><div class="title">{_e(plan.get("data_title", ""))}</div>{cells}</div>'

    cards = "".join(
        f'<div class="card{" red" if c.get("color") == "red" else ""}"><div class="hd">{_icon(c.get("icon", ""))}'
        f'<span>{_e(c["header"])}</span></div><div class="bd">{_e(c["body"])}</div></div>'
        for c in plan["cards"][:3])

    badge = f'<div class="badge">{bn_num(1)}/{bn_num(total)}</div>' if total > 1 else ""
    swipe = f'<div class="pill">{SWIPE}</div>' if total > 1 else ""

    body = (f'<div class="page"><div class="hero">{_photo_div(photo)}<div class="fade"></div>'
            f'{_tag(plan, day)}{badge}'
            f'{f"<div class=logo-card>{_img(main_logo)}</div>" if main_logo else ""}'
            f'<h1>{headline}</h1>'
            f'<div><div class="brush"><span>{_e(plan["banner"])}</span></div></div></div>'
            f'{strip}<div class="cards">{cards}</div>'
            f'<div class="bottomrow"><div class="notice">{WARN_SVG}<span>{NOTICE}</span></div>{swipe}</div>'
            f'{_footer()}</div>')
    return _doc(body)


def slide_html(plan: dict, slide: dict, number: int, total: int, day: dt.date, photo: str | None) -> str:
    pts = "".join(f'<div class="pt"><div class="n">{bn_num(i)}</div><div>{_e(p)}</div></div>'
                  for i, p in enumerate(slide["points"][:4], 1))
    last = number == total
    bottom = (f'<div class="slide-bottom"><div class="pill navy">{COMMENT_CTA}</div></div>'
              f'<div class="notice" style="margin-top:0">{WARN_SVG}<span>{NOTICE}</span></div>'
              if last else f'<div class="slide-bottom"><div class="pill">{SWIPE}</div></div>')
    body = (f'<div class="page"><div class="hero slide-hero">{_photo_div(photo)}<div class="fade"></div>'
            f'{_tag(plan, day)}<div class="badge">{bn_num(number)}/{bn_num(total)}</div>'
            f'<div class="slide-title">{_e(slide["title"])}</div><div class="underline"></div></div>'
            f'<div class="points">{pts}</div>{bottom}{_footer()}</div>')
    return _doc(body)


# ---------------------------------------------------------------- render

def render_post(plan: dict, day: dt.date, folder: str, used_photos: set[str]) -> list[str]:
    """Make the cover (+ carousel slides) as JPEGs in `folder`. Returns the image paths."""
    slides = plan.get("slides") or []
    total = 1 + len(slides)
    jobs = []
    photo = find_photo(plan.get("photo_query", "stock market"), used_photos, os.path.join(folder, "photo-1.jpg"))
    main_logo = get_logo(plan.get("main_wiki_title", ""), plan.get("main_logo_key", ""))
    item_logos = [get_logo(d.get("wiki_title", ""), d.get("logo_key", "")) for d in (plan.get("data_items") or [])[:5]]
    jobs.append(cover_html(plan, day, photo, total, main_logo, item_logos))
    for n, slide in enumerate(slides, 2):
        p = find_photo(slide.get("photo_query", "stock market"), used_photos, os.path.join(folder, f"photo-{n}.jpg"))
        jobs.append(slide_html(plan, slide, n, total, day, p))

    from playwright.sync_api import sync_playwright

    out = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=os.getenv("PLAYWRIGHT_CHANNEL") or None)
        page = browser.new_page(viewport={"width": 1080, "height": 1080}, device_scale_factor=1)
        for i, doc in enumerate(jobs, 1):
            html_path = os.path.join(folder, f"slide-{i}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(doc)
            page.goto(pathlib.Path(html_path).as_uri(), wait_until="networkidle")
            page.evaluate("document.fonts.ready.then(() => true)")
            page.evaluate("window.__fit()")
            img = os.path.join(folder, f"post-{i}.jpg")
            page.screenshot(path=img, type="jpeg", quality=90)
            out.append(img)
        browser.close()
    return out
