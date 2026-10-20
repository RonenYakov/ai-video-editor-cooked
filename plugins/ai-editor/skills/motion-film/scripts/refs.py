#!/usr/bin/env python3
"""Film references: measure the look of a video, a folder of images or a website, per film.

  add <film> <source> [--take "..."] [--id refN]
        Appends the reference to the film's refs.json (new id when not given), copies a local file
        into <film>/refs/ when it sits outside it, then measures it.
  measure <film>
        Measures every entry of refs.json that has no <film>/refs/<id>.json yet.
  demo  Self-check offline on a synthetic video and a folder of two images.

<film> is a film folder, or a film name inside <library>/films/. refs.json is read from
<film>/refs.json (what the home page writes), else <film>/refs/refs.json.

Source kinds
  video file or video link   Runs visual.py, look.py and graphics.py (creator-teardown) on it in a scratch
                             teardown folder, then grade.py. Whole look only, no spans yet. Writes
                             refs/<id>.json (the style.json shape: pace, zoom, camera, graphics, grade, ...),
                             refs/<id>/still-1..4.png (evenly spaced) and refs/<id>.png (the middle frame).
  image folder or one image  grade.py on the images: grade and graphics.palette. The images (up to 4) are
                             copied as the stills. No pace, zoom or other motion field.
  website link               brand.from_url (colours, font, logo), kept as "brand_ref" in refs/<id>.json.
                             Nothing is saved to the profile. No screenshot: the repo has no page
                             screenshot helper to reuse.

"_measured" in refs/<id>.json says which scripts ran ("ok") and which did not ("failed: why").
A field a script could not measure stays missing. Every number comes from those scripts.

Usage (the tool venv python: numpy, pillow, opencv, ffmpeg on PATH):
  ~/.ai-video-editor/venv/bin/python refs.py add <film> <video|folder|image|url> [--take "the whole look"] [--id ref3]
  ~/.ai-video-editor/venv/bin/python refs.py measure <film>
  ~/.ai-video-editor/venv/bin/python refs.py demo

Exit codes: 0 ok - 1 error - 2 usage
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
PLUGINS = HERE.parents[4]
LIB = HERE.parents[3] / "lib" / "ai_editor"
TEAR = PLUGINS / "creator-teardown" / "skills" / "creator-teardown" / "scripts"
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".mts", ".3gp"}
# style.json blocks a whole-look reference keeps (the contract's names)
KEEP = ("aspect", "pace", "zoom", "camera", "transitions", "graphics", "grade", "captions", "face", "layout")
STEP_TIMEOUT = 1800


def say(msg):
    print(msg, file=sys.stderr)


def _lib():
    if str(LIB) not in sys.path:
        sys.path.insert(0, str(LIB))


def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(p, d):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(d, indent=2, default=float), encoding="utf-8")


# ---------- the film folder ----------

def film_dir(arg):
    p = Path(arg).expanduser()
    if p.is_dir():
        return p.resolve()
    _lib()
    import library
    q = library.path() / "films" / arg
    if q.is_dir():
        return q
    sys.exit(f"no film folder at {p} or {q}")


def refs_file(film):
    for p in (film / "refs.json", film / "refs" / "refs.json"):
        if p.exists():
            return p
    return film / "refs.json"


def load_refs(film):
    d = read_json(refs_file(film), [])
    return d if isinstance(d, list) else []


def save_refs(film, refs):
    write_json(refs_file(film), refs)


def next_id(refs):
    used = {r.get("id") for r in refs}
    n = 1
    while f"ref{n}" in used:
        n += 1
    return f"ref{n}"


# ---------- source kind ----------

def kind_of(source):
    s = str(source).strip()
    if re.match(r"https?://", s, re.I):
        _lib()
        import links
        k = links.classify(s, own=True)["kind"]
        if k in ("video", "own"):
            return "video-link"
        if k == "product":
            return "website"
        return "unsupported"
    p = Path(s).expanduser()
    if p.is_dir():
        return "images"
    if p.suffix.lower() in IMG_EXT:
        return "images"
    if p.suffix.lower() in VIDEO_EXT:
        return "video"
    return "unsupported"


def inside(p, folder):
    try:
        Path(p).resolve().relative_to(folder.resolve())
        return True
    except ValueError:
        return False


def localise(film, source, rid):
    """Source -> (kind, source as stored). Downloads a video link, copies a local file into refs/."""
    refs = film / "refs"
    refs.mkdir(exist_ok=True)
    kind = kind_of(source)
    if kind == "video-link":
        _lib()
        import links
        code, msg = links.fetch(source, refs)
        if code != 0:
            raise RuntimeError(f"download failed: {msg}")
        return "video", msg
    if kind in ("video", "images"):
        p = Path(source).expanduser().resolve()
        if not p.exists():
            raise RuntimeError(f"no such file: {p}")
        if inside(p, refs):
            return kind, str(p)
        dest = refs / (f"{rid}-{p.name}")
        if p.is_dir():
            shutil.copytree(p, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(p, dest)
        return kind, str(dest)
    return kind, source


# ---------- stills ----------

def ffmpeg_still(video, t, out):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", str(out)],
                       capture_output=True, text=True)
    return r.returncode == 0 and Path(out).exists()


def duration(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def video_stills(film, rid, video):
    dur = duration(video)
    if dur <= 0:
        return []
    sdir = film / "refs" / rid
    sdir.mkdir(parents=True, exist_ok=True)
    out = []
    for i in range(4):
        p = sdir / f"still-{i + 1}.png"
        if ffmpeg_still(video, dur * (2 * i + 1) / 8, p):
            out.append(p)
    ffmpeg_still(video, dur / 2, film / "refs" / f"{rid}.png")
    return out


def image_files(src):
    src = Path(src)
    if src.is_file():
        return [src]
    return sorted(p for p in src.iterdir() if p.suffix.lower() in IMG_EXT)


def image_stills(film, rid, src):
    from PIL import Image
    files = image_files(src)
    if len(files) > 4:   # evenly spread over the folder, not the first four
        files = [files[round(i * (len(files) - 1) / 3)] for i in range(4)]
    sdir = film / "refs" / rid
    sdir.mkdir(parents=True, exist_ok=True)
    out = []
    for i, f in enumerate(files):
        p = sdir / f"still-{i + 1}.png"
        try:
            with Image.open(f) as im:
                im.convert("RGB").save(p)
        except OSError as e:
            say(f"{f.name}: not an image Pillow can read ({e})")
            continue
        out.append(p)
    if out:
        shutil.copyfile(out[len(out) // 2], film / "refs" / f"{rid}.png")
    return out


# ---------- running the measuring scripts ----------

def run_script(name, args, cwd):
    """One creator-teardown script through its own CLI. ('ok', None) or ('failed', why)."""
    script = TEAR / name
    if not script.exists():
        return "failed", f"{name} not found"
    try:
        r = subprocess.run([sys.executable, str(script), *args], cwd=str(cwd), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=STEP_TIMEOUT)
    except subprocess.TimeoutExpired:
        return "failed", f"{name} timed out"
    if r.returncode != 0:
        tail = (r.stderr.strip() or r.stdout.strip()).splitlines()[-1:] or [f"exit {r.returncode}"]
        return "failed", tail[0][:200]
    return "ok", None


def as_mp4(src, dest):
    """The scripts glob *.mp4: link or re-encode the reference to dest. True when it worked."""
    if Path(src).suffix.lower() == ".mp4":
        shutil.copyfile(src, dest)
        return True
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-an", "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "23", "-pix_fmt", "yuv420p", str(dest)], capture_output=True, text=True)
    return r.returncode == 0


def measure_video(film, rid, video):
    """Whole-look measure of one video -> the refs/<id>.json dict."""
    ran = {}
    with tempfile.TemporaryDirectory(prefix="refs-") as tmp:
        work = Path(tmp)
        # the scripts keep a teardown folder at <cwd>/creator-teardowns/<handle>/video/<id>.mp4
        handle = re.sub(r"[^a-z0-9._-]", "", rid.lower()) or "ref"
        vdir = work / "creator-teardowns" / handle / "video"
        vdir.mkdir(parents=True)
        if not as_mp4(video, vdir / f"{handle}.mp4"):
            return {"_measured": {"decode": "failed: ffmpeg could not read the video"}}
        for script, args in (("visual.py", ["measure", handle]),
                             ("look.py", ["measure", handle]),
                             ("graphics.py", ["measure", handle])):
            state, why = run_script(script, args, work)
            ran[script[:-3]] = state if why is None else f"{state}: {why}"
        style_p = work / "creator-teardowns" / handle / "style.json"
        if not style_p.exists():
            write_json(style_p, {})
        state, why = run_script("grade.py", ["measure", str(video), "--style", str(style_p)], work)
        ran["grade"] = state if why is None else f"{state}: {why}"
        style = read_json(style_p, {})
    out = {k: style[k] for k in KEEP if k in style}
    out["_measured"] = ran
    return out


def measure_images(film, rid, src):
    ran = {}
    with tempfile.TemporaryDirectory(prefix="refs-") as tmp:
        style_p = Path(tmp) / "style.json"
        folder = Path(src)
        if folder.is_file():   # grade.py reads a video file or a folder: give it a folder of one
            folder = Path(tmp) / "one"
            folder.mkdir()
            shutil.copy2(src, folder / Path(src).name)
        state, why = run_script("grade.py", ["measure", str(folder), "--style", str(style_p)], Path(tmp))
        ran["grade"] = state if why is None else f"{state}: {why}"
        style = read_json(style_p, {})
    out = {}
    if "grade" in style:
        out["grade"] = style["grade"]
    if (style.get("graphics") or {}).get("palette"):
        out["graphics"] = {"palette": style["graphics"]["palette"]}
    out["_measured"] = ran
    return out


def measure_website(film, rid, url):
    _lib()
    import brand
    import profile
    keep_home = profile.HOME
    profile.HOME = film / "refs" / rid   # brand.from_url downloads the logo to <HOME>/brand/: not the user's profile
    try:
        kit = brand.from_url(url)
    except Exception as e:  # noqa: BLE001 - a dead site is a result, not a crash
        return {"_measured": {"brand": f"failed: {str(e)[:200]}"}}
    finally:
        profile.HOME = keep_home
    return {"brand_ref": kit, "_measured": {"brand": "ok", "screenshot": "skipped: no page screenshot helper in the repo"}}


# ---------- commands ----------

def measure_entry(film, entry):
    rid, source = entry["id"], entry["source"]
    kind, stored = localise(film, source, rid)
    if stored != source:
        entry["source"] = stored
    if kind == "video":
        res = measure_video(film, rid, stored)
        stills = video_stills(film, rid, stored)
    elif kind == "images":
        res = measure_images(film, rid, stored)
        stills = image_stills(film, rid, stored)
    elif kind == "website":
        res, stills = measure_website(film, rid, source), []
    else:
        raise RuntimeError(f"{source}: not a video, an image folder, an image or a website link")
    doc = {"id": rid, "source": entry["source"], "take": entry.get("take") or "the whole look", "kind": kind, **res}
    if stills:
        doc["stills"] = [str(p.relative_to(film)).replace("\\", "/") for p in stills]
    write_json(film / "refs" / f"{rid}.json", doc)
    return doc


def summary(doc):
    bits = [k for k in ("pace", "zoom", "graphics", "grade", "brand_ref") if k in doc]
    bad = [f"{k} {v}" for k, v in doc["_measured"].items() if v != "ok" and not v.startswith("skipped")]
    return f"{doc['id']} ({doc['kind']}): {', '.join(bits) or 'nothing measured'}" + (f"; not measured: {'; '.join(bad)}" if bad else "")


def cmd_measure(a):
    film = film_dir(a.film)
    refs = load_refs(film)
    todo = [r for r in refs if r.get("id") and r.get("source") and not (film / "refs" / f"{r['id']}.json").exists()]
    if not todo:
        print("every reference is measured")
        return 0
    rc = 0
    for r in todo:
        try:
            print(summary(measure_entry(film, r)))
        except (RuntimeError, OSError) as e:
            say(f"{r['id']}: {e}")
            rc = 1
    save_refs(film, refs)   # a copied file changes the stored source
    return rc


def cmd_add(a):
    film = film_dir(a.film)
    refs = load_refs(film)
    rid = a.id or next_id(refs)
    if any(r.get("id") == rid for r in refs):
        sys.exit(f"{rid} is already in refs.json. Pick another --id.")
    entry = {"id": rid, "source": a.source, "take": a.take or "the whole look"}
    refs.append(entry)
    save_refs(film, refs)
    try:
        print(summary(measure_entry(film, entry)))
    except (RuntimeError, OSError) as e:
        say(f"{rid}: {e} (kept in refs.json; `measure` retries it)")
        return 1
    finally:
        save_refs(film, refs)
    return 0


# ---------- self-check ----------

def demo_media(tmp):
    """A 3 s warm-tinted clip with a moving box and a hard cut at 1.5 s, and a folder of two images."""
    vid = tmp / "src" / "demo.mp4"
    vid.parent.mkdir(parents=True)
    flt = ("color=c=0x303a50:s=360x640:r=30:d=1.5[a];color=c=0x703020:s=360x640:r=30:d=1.5[b];"
           "[a][b]concat=n=2:v=1:a=0,"
           "drawbox=x='20+t*100':y=260:w=90:h=90:color=white@1:t=fill,"
           "colorchannelmixer=rr=1.15:bb=0.8,format=yuv420p")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-filter_complex", flt, "-t", "3", "-c:v", "libx264", str(vid)],
                       capture_output=True, text=True)
    assert r.returncode == 0 and vid.exists(), r.stderr
    from PIL import Image
    imgs = tmp / "src" / "photos"
    imgs.mkdir()
    Image.new("RGB", (240, 320), (200, 120, 60)).save(imgs / "a.png")
    Image.new("RGB", (240, 320), (40, 60, 150)).save(imgs / "b.png")
    return vid, imgs


def demo():
    with tempfile.TemporaryDirectory(prefix="refs-demo-") as t:
        tmp = Path(t)
        film = tmp / "films" / "demo"
        (film / "refs").mkdir(parents=True)
        vid, imgs = demo_media(tmp)
        ns = argparse.Namespace
        assert cmd_add(ns(film=str(film), source=str(vid), take="the whole look", id=None)) == 0
        assert cmd_add(ns(film=str(film), source=str(imgs), take="the colours", id=None)) == 0
        refs = read_json(film / "refs.json")
        assert [r["id"] for r in refs] == ["ref1", "ref2"], refs
        r1, r2 = read_json(film / "refs" / "ref1.json"), read_json(film / "refs" / "ref2.json")
        assert r1["grade"]["luma_mean"] is not None and "pace" in r1, r1
        assert r1["_measured"]["visual"] == "ok" and r1["_measured"]["grade"] == "ok", r1["_measured"]
        assert r1["pace"]["cuts_per_10s"] > 0, r1["pace"]   # the hard cut at 1.5 s
        assert r1["grade"]["source"] == "video", r1["grade"]
        assert "grade" in r2 and r2["graphics"]["palette"] and "pace" not in r2 and "zoom" not in r2, r2
        assert r2["grade"]["source"] == "images", r2["grade"]
        for rid, n in (("ref1", 4), ("ref2", 2)):
            for i in range(1, n + 1):
                assert (film / "refs" / rid / f"still-{i}.png").stat().st_size > 0, (rid, i)
            assert (film / "refs" / f"{rid}.png").stat().st_size > 0, rid
        assert Path(refs[0]["source"]).exists() and inside(refs[0]["source"], film / "refs"), refs[0]
        # measure again measures nothing new
        assert cmd_measure(ns(film=str(film))) == 0
        assert kind_of("https://example.com") == "website" and kind_of("https://www.youtube.com/watch?v=abc") == "video-link"
        assert kind_of(str(imgs)) == "images" and kind_of(str(vid)) == "video" and kind_of(str(tmp / "x.txt")) == "unsupported"
        print(f"measured ok: ref1 {r1['_measured']}, ref2 {r2['_measured']}")
    print("refs demo ok")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add")
    p.add_argument("film")
    p.add_argument("source", help="a video file or link, an image or folder of images, or a website link")
    p.add_argument("--take", help="what to take from it (default: the whole look)")
    p.add_argument("--id", help="reference id (default: the next refN)")
    p.set_defaults(fn=cmd_add)
    p = sub.add_parser("measure")
    p.add_argument("film")
    p.set_defaults(fn=cmd_measure)
    sub.add_parser("demo").set_defaults(fn=lambda a: demo())
    a = ap.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
