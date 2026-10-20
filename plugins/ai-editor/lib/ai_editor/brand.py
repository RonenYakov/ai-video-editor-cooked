#!/usr/bin/env python3
"""A brand kit read from a website or a folder of photos, saved to the user's profile.

    python3 brand.py from-url <url> [--save]       colours (the most used in the page's CSS, up to 5), the first
                                                   real font-family of body / h1, and the best logo (downloaded
                                                   into ~/.ai-video-editor/brand/)
    python3 brand.py from-images <folder> [--save] the 5 dominant colours of the photos (median cut) and a file
                                                   named *logo* if there is one. Fonts cannot be read from photos
    python3 brand.py demo                          self-check, no network, no keys

Prints the kit as JSON: {"colors": ["#RRGGBB", ...], "font": "Name" | null, "logo": "/path" | null}.
--save merges it into profile["brand"] through profile.save: a field the page or photos did not give keeps what
the user already set, and a found field replaces it (and "use_creator" goes, the kit is theirs now).
Needs Pillow only for from-images (it is in requirements.lock); the rest is stdlib.
"""
import colorsys
import json
import re
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import net  # noqa: E402
import profile  # noqa: E402

GENERIC = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-sans-serif", "ui-serif",
           "ui-monospace", "ui-rounded", "emoji", "math", "fangsong", "inherit", "initial", "unset", "revert",
           "-apple-system", "blinkmacsystemfont", "segoe ui", "helvetica neue", "arial", "helvetica"}
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".ico")
UA = {"User-Agent": "Mozilla/5.0 (cooked brand reader)"}
MAX_BYTES = 3_000_000


# ---------- colour ----------
def to_hex(r, g, b):
    return "#%02X%02X%02X" % (r, g, b)


def norm_hex(s):
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return "#" + s.upper()


def boring(h):
    """Near white, near black or grey: the page's neutrals, not its brand."""
    r, g, b = profile.rgb(h)
    _, l, s = colorsys.rgb_to_hls(r, g, b)
    return l > 0.93 or l < 0.08 or s < 0.15


def css_colors(css, n=5):
    """The most used colours in `css`, as #RRGGBB. Neutrals only when nothing else is there."""
    count = {}
    for m in re.finditer(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b|rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})", css):
        h = norm_hex(m.group(1)) if m.group(1) else to_hex(*(min(255, int(x)) for x in m.groups()[1:]))
        count[h] = count.get(h, 0) + 1
    ranked = [c for c, _ in sorted(count.items(), key=lambda kv: -kv[1])]
    keep = [c for c in ranked if not boring(c)] or ranked
    return keep[:n]


def css_font(css):
    """The first non-generic family of a body, html or h1 rule."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for want in ("body", "html", "h1"):
        for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            if want not in [s.strip().lower() for s in sel.split(",")]:
                continue
            m = re.search(r"font-family\s*:\s*([^;}]+)", body, re.I)
            for fam in (m.group(1).split(",") if m else []):
                fam = fam.strip().strip("'\"").strip()
                if fam and fam.lower() not in GENERIC and not fam.startswith(("var(", "-")):
                    return fam
    return None


# ---------- html ----------
class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sheets, self.inline, self.logos, self._style = [], [], [], False

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        rel, href = a.get("rel", "").lower(), a.get("href", "")
        if tag == "style":
            self._style = True
        elif tag == "link" and "stylesheet" in rel and href:
            self.sheets.append(href)
        elif tag == "link" and "apple-touch-icon" in rel and href:
            self.logos.append((60, href))
        elif tag == "link" and "icon" in rel and href:
            self.logos.append((10, href))
        elif tag == "meta" and a.get("property") == "og:image" and a.get("content"):
            self.logos.append((30, a["content"]))
        elif tag == "img" and a.get("src"):
            blob = " ".join(a.get(k, "") for k in ("class", "id", "alt", "src")).lower()
            if "logo" in blob:
                self.logos.append((100 if "logo" in a.get("src", "").lower() or "logo" in a.get("alt", "").lower() else 90, a["src"]))
        if "style" in a:
            self.inline.append(a["style"])

    def handle_endtag(self, tag):
        if tag == "style":
            self._style = False

    def handle_data(self, data):
        if self._style:
            self.inline.append(data)


def parse_page(html, base=""):
    """(inline css, stylesheet urls, logo urls best first) of one page."""
    p = Page()
    p.feed(html)
    web = lambda us: [u for u in (urljoin(base, x) for x in us) if urlparse(u).scheme in ("http", "https")]  # a page never points us at file://
    logos = web(u for _, u in sorted(p.logos, key=lambda x: -x[0]))
    return "\n".join(p.inline), web(p.sheets), list(dict.fromkeys(logos))


def get(url, limit=MAX_BYTES):
    from urllib.request import Request
    with net.urlopen(Request(url, headers=UA), 20) as r:
        return r.read(limit)


def download_logo(urls, home=None):
    """The first of `urls` that downloads as something non-empty, into <home>/brand/. Its path or None."""
    out = Path(home or profile.HOME) / "brand"
    for u in urls:
        try:
            data = get(u)
        except Exception as e:  # noqa: BLE001 - a dead logo link is not fatal, try the next
            print(f"logo skipped {u}: {net.friendly(e)}", file=sys.stderr)
            continue
        if not data:
            continue
        ext = Path(urlparse(u).path).suffix.lower()
        out.mkdir(parents=True, exist_ok=True)
        dest = out / ("logo" + (ext if ext in IMG_EXT else ".png"))
        dest.write_bytes(data)
        return str(dest)
    return None


def from_url(url):
    if "://" not in url:
        url = "https://" + url
    html = get(url).decode("utf-8", "replace")
    css, sheets, logos = parse_page(html, url)
    for s in sheets[:8]:
        try:
            css += "\n" + get(s).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            print(f"stylesheet skipped {s}: {net.friendly(e)}", file=sys.stderr)
    logos = logos + [urljoin(url, "/favicon.ico")]
    return {"colors": css_colors(css), "font": css_font(css), "logo": download_logo(logos)}


# ---------- images ----------
def from_images(folder, n=5):
    from PIL import Image
    files = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in IMG_EXT)
    logo = next((p for p in files if "logo" in p.stem.lower()), None)
    tiles = []
    for p in files:
        if p == logo or p.suffix.lower() == ".svg":
            continue
        try:
            with Image.open(p) as im:
                tiles.append(im.convert("RGB").resize((48, 48)))
        except OSError:
            continue
    colors = []
    if tiles:
        sheet = Image.new("RGB", (48, 48 * len(tiles)))
        for i, t in enumerate(tiles):
            sheet.paste(t, (0, 48 * i))
        q = sheet.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
        pal = q.getpalette()
        used = sorted(q.getcolors(), reverse=True)   # (count, index)
        colors = [to_hex(*pal[i * 3:i * 3 + 3]) for _, i in used][:n]
    return {"colors": colors, "font": None, "logo": str(logo.resolve()) if logo else None}


# ---------- save ----------
def merge(brand, kit):
    """kit over brand: a found field replaces, an empty one keeps what the user set."""
    out = dict(brand or {})
    found = {k: v for k, v in kit.items() if v}
    out.update(found)
    if found:
        out.pop("use_creator", None)
    return out


def save(kit):
    prof = profile.load()
    prof["brand"] = merge(prof.get("brand"), kit)
    return profile.save(prof)


# ---------- demo ----------
def demo():
    html = ('<html><head><link rel="stylesheet" href="/s.css"><link rel="apple-touch-icon" href="/touch.png">'
            '<meta property="og:image" content="/og.png"><style>body{font-family:"Fraunces",Georgia,serif;color:#111}'
            '.a{color:#E5482C}.b{background:rgb(229,72,44)}.c{color:#e5482c}.d{color:#1D6FA5}.w{background:#fff}'
            '.g{color:#888}</style></head><body><img class="nav-logo" src="/img/brand.svg" alt="x"></body></html>')
    css, sheets, logos = parse_page(html, "https://x.io/p/")
    assert sheets == ["https://x.io/s.css"], sheets
    assert logos == ["https://x.io/img/brand.svg", "https://x.io/touch.png", "https://x.io/og.png"], logos
    assert css_colors(css) == ["#E5482C", "#1D6FA5"], css_colors(css)
    assert css_colors("a{color:#fff}b{color:#000}b2{color:#888}") == ["#FFFFFF", "#000000", "#888888"]
    assert parse_page('<img class="logo" src="file:///etc/passwd"><link rel="stylesheet" href="file:///x.css">', "https://x.io/")[1:] == ([], [])
    assert css_font(css) == "Fraunces" and css_font("h1{font-family:Inter,sans-serif}") == "Inter"
    assert css_font("body{font-family:system-ui,sans-serif}") is None

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        profile.HOME = d / "home"
        # download from a file: URL, no network
        src = d / "src.svg"
        src.write_text("<svg/>", encoding="utf-8")
        got = download_logo(["file:///nonexistent/none.png", src.as_uri()])
        assert got and Path(got).parent == profile.HOME / "brand" and Path(got).read_text(encoding="utf-8") == "<svg/>", got
        # photos: half red, half blue, plus a logo file
        from PIL import Image
        pics = d / "pics"
        pics.mkdir()
        Image.new("RGB", (60, 60), (220, 40, 40)).save(pics / "a.png")
        Image.new("RGB", (60, 60), (30, 60, 200)).save(pics / "b.jpg")
        Image.new("RGB", (20, 20), (0, 0, 0)).save(pics / "My-Logo.png")
        kit = from_images(pics)
        assert kit["font"] is None and kit["logo"].endswith("My-Logo.png"), kit
        assert len(kit["colors"]) == 2 and all(any(profile.near(c, w, 0.05) for c in kit["colors"]) for w in ("#DC2828", "#1E3CC8")), kit
        # merge: nothing set -> stays; found replaces; empty keeps; use_creator goes
        profile.save({"platform": "tiktok", "brand": {"use_creator": True}})
        save({"colors": [], "font": None, "logo": None})
        assert profile.load()["brand"] == {"use_creator": True}
        save({"colors": ["#E5482C"], "font": "Fraunces", "logo": None})
        assert profile.load()["brand"] == {"colors": ["#E5482C"], "font": "Fraunces"}
        save({"colors": ["#111111"], "font": None, "logo": "/a/logo.png"})
        assert profile.load()["brand"] == {"colors": ["#111111"], "font": "Fraunces", "logo": "/a/logo.png"}
        assert profile.load()["platform"] == "tiktok"
    print("brand ok")


def main():
    a = sys.argv[1:]
    if a == ["demo"]:
        return demo()
    if len(a) >= 2 and a[0] in ("from-url", "from-images"):
        kit = from_url(a[1]) if a[0] == "from-url" else from_images(a[1])
        print(json.dumps(kit, indent=1))
        if a[0] == "from-images":
            print("fonts cannot be read from photos: ask for the font name if the brand has one", file=sys.stderr)
        if "--save" in a:
            print(f"saved brand -> {save(kit)}")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
