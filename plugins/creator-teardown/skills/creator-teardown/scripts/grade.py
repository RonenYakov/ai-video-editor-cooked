#!/usr/bin/env python3
"""Measure a colour grade from pixels: a video, or a folder of stills.

  measure <video-or-folder> [--style style.json] [--frames 24]
        Samples frames with ffmpeg (a video) or reads every image (a folder). Per frame:
        luma mean and spread, black and white point (1st and 99th luma percentile), mean
        saturation, and the mean hue of the shadows and of the highlights. Medians over the
        frames go to style.json["grade"]. For a folder the five dominant colours also go to
        style.json["graphics"]["palette"] when it has none (same shape as look.py).
  demo   self-check on synthetic frames. No network, no keys.

Every number here comes from code. Luma is Rec. 709 on 0-1 RGB.

Usage (the tool venv python: numpy, pillow, opencv):
  ~/.ai-video-editor/venv/bin/python scripts/grade.py measure clip.mp4 --style style.json
  ~/.ai-video-editor/venv/bin/python scripts/grade.py demo

Exit codes: 0 ok - 1 error - 2 usage
"""
import argparse
import json
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

WORK_W = 160          # analysis width, px
SAMPLE_N = 24         # frames sampled from a video
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
LUMA = np.float32([0.2126, 0.7152, 0.0722])


# ---------- decoding ----------

def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    s = d["streams"][0]
    return int(s["width"]), int(s["height"]), float(d["format"]["duration"])


def video_frames(path, n=SAMPLE_N):
    """n frames spread evenly over the video, as RGB uint8 arrays scaled to WORK_W wide."""
    w, h, dur = probe(path)
    h2 = max(2, round(WORK_W * h / w / 2) * 2)
    fps = n / max(dur, 0.1)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={fps:.5f},scale={WORK_W}:{h2}",
                          "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    size = WORK_W * h2 * 3
    out = []
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        out.append(np.frombuffer(buf, np.uint8).reshape(h2, WORK_W, 3))
    p.stdout.close()
    p.wait()
    return out


def image_frames(folder):
    from PIL import Image
    out = []
    for f in sorted(Path(folder).iterdir()):
        if f.suffix.lower() in IMG_EXT:
            im = Image.open(f).convert("RGB")
            im.thumbnail((WORK_W, WORK_W * 4))
            out.append(np.asarray(im))
    return out


# ---------- measuring ----------

def hue_of(rgb):
    """Mean hue in degrees (0-360) of RGB pixels (N x 3, 0-1), weighted by chroma.
    None when the pixels have no colour to speak of."""
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    keep = d > 0.02
    if not keep.any():
        return None
    r, g, b = (rgb[keep, i] for i in range(3))
    dk, mk = d[keep], mx[keep]
    h = np.where(mk == r, ((g - b) / dk) % 6, np.where(mk == g, (b - r) / dk + 2, (r - g) / dk + 4)) * 60
    rad = np.radians(h)
    x, y = (np.cos(rad) * dk).sum(), (np.sin(rad) * dk).sum()
    if abs(x) + abs(y) < 1e-6:
        return None
    return float(np.degrees(np.arctan2(y, x)) % 360)


def frame_grade(img):
    a = img.reshape(-1, 3).astype(np.float32) / 255
    luma = a @ LUMA
    mx, mn = a.max(-1), a.min(-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    lo, hi = np.percentile(luma, [1, 99])
    # Shadows and highlights: the darkest and brightest quarter of the frame's own luma.
    q1, q3 = np.percentile(luma, [25, 75])
    sh = a[luma <= q1]
    hl = a[luma >= q3]
    return {"luma_mean": float(luma.mean()), "luma_std": float(luma.std()), "black": float(lo), "white": float(hi),
            "saturation": float(sat.mean()), "shadow_hue": hue_of(sh), "highlight_hue": hue_of(hl)}


def circ_median(degs):
    """A circular median: the mean of the hues nearest the circular mean."""
    degs = [d for d in degs if d is not None]
    if not degs:
        return None
    rad = np.radians(degs)
    m = np.degrees(np.arctan2(np.sin(rad).sum(), np.cos(rad).sum())) % 360
    diff = [abs((d - m + 180) % 360 - 180) for d in degs]
    cut = statistics.median(diff)
    near = np.radians([d for d, x in zip(degs, diff) if x <= cut])
    return float(np.degrees(np.arctan2(np.sin(near).sum(), np.cos(near).sum())) % 360)


def grade_of(frames, source):
    rows = [frame_grade(f) for f in frames]
    g = {k: round(statistics.median(r[k] for r in rows), 3)
         for k in ("luma_mean", "luma_std", "black", "white", "saturation")}
    for k in ("shadow_hue", "highlight_hue"):
        h = circ_median([r[k] for r in rows])
        g[k] = None if h is None else round(h, 1)
    g["frames"] = len(rows)
    g["source"] = source
    return g


def hexc(c):
    c = [int(round(v)) for v in c]
    if min(c) >= 232:
        c = [255, 255, 255]
    elif max(c) <= 28:
        c = [0, 0, 0]
    return "#{:02X}{:02X}{:02X}".format(*c)


def palette_of(frames, k=5):
    """Dominant colours, same shape as look.py's graphics palette: [{hex, pct}], biggest first."""
    import cv2
    px = np.concatenate([f.reshape(-1, 3) for f in frames])
    px = px[np.random.default_rng(0).choice(len(px), min(20000, len(px)), replace=False)]
    cv2.setRNGSeed(0)
    k = max(1, min(k, len(px)))
    _, lab, cen = cv2.kmeans(np.float32(px), k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1.0),
                             3, cv2.KMEANS_PP_CENTERS)
    lab = lab.ravel()
    cnt = np.bincount(lab, minlength=len(cen))
    return [{"hex": hexc(cen[j]), "pct": round(100 * cnt[j] / len(lab))} for j in np.argsort(-cnt)]


def merge_style(style, grade, palette=None):
    # look.py keeps its own luma / sat keys in this block (plan.py reads them): update, do not replace.
    style["grade"] = {**(style.get("grade") or {}), **grade}
    if palette:
        gfx = style.setdefault("graphics", {})
        if not gfx.get("palette"):
            gfx["palette"] = palette
    return style


def cmd_measure(a):
    src = Path(a.source)
    if src.is_dir():
        frames, kind = image_frames(src), "images"
    elif src.is_file():
        frames, kind = video_frames(src, a.frames), "video"
    else:
        sys.exit(f"{src}: not a video file or a folder of images")
    if not frames:
        sys.exit(f"{src}: no frames could be read")
    g = grade_of(frames, kind)
    pal = palette_of(frames) if kind == "images" else None
    print(json.dumps(g, indent=2))
    if a.style:
        sp = Path(a.style)
        style = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
        sp.write_text(json.dumps(merge_style(style, g, pal), indent=2), encoding="utf-8")
        print(f"-> {sp}")


# ---------- self-check ----------

def solid(rgb, n=64):
    """A synthetic frame: one colour with a vertical gradient, so the percentiles differ."""
    base = np.array(rgb, np.float32)[None, None, :] * np.linspace(0.6, 1.0, n)[:, None, None]
    return np.clip(np.broadcast_to(base, (n, n, 3)), 0, 255).astype(np.uint8)


def split(shadow, light, n=64):
    """Dark half in `shadow`, bright half in `light`."""
    f = np.zeros((n, n, 3), np.uint8)
    f[: n // 2] = shadow
    f[n // 2:] = light
    return f


def near(h, target, tol):
    return h is not None and abs((h - target + 180) % 360 - 180) <= tol


def demo():
    dark = grade_of([solid((60, 60, 60))] * 3, "images")
    bright = grade_of([solid((220, 220, 220))] * 3, "images")
    assert dark["luma_mean"] < bright["luma_mean"] - 0.3, (dark, bright)
    assert 0 <= dark["black"] <= dark["white"] <= 1, dark

    grey = grade_of([solid((128, 128, 128))], "images")
    vivid = grade_of([solid((230, 40, 40))], "images")
    assert grey["saturation"] < 0.02 and vivid["saturation"] > 0.5, (grey, vivid)

    flat = grade_of([solid((120, 120, 120))], "images")
    contrasty = grade_of([split((10, 10, 10), (245, 245, 245))], "images")
    assert contrasty["luma_std"] > flat["luma_std"] + 0.3, (flat, contrasty)
    assert contrasty["black"] < 0.1 and contrasty["white"] > 0.9, contrasty

    teal_orange = grade_of([split((10, 50, 60), (255, 190, 110))], "images")
    assert near(teal_orange["highlight_hue"], 30, 15), teal_orange     # orange
    assert near(teal_orange["shadow_hue"], 190, 20), teal_orange       # teal
    assert grey["highlight_hue"] is None, grey                          # no colour, no hue

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        mp4s = {}
        for name, rgb in (("dark", (50, 50, 60)), ("warm", (240, 170, 90))):
            mp4 = td / f"{name}.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "64x64", "-r", "10",
                            "-i", "-", "-pix_fmt", "yuv420p", str(mp4)],
                           input=np.stack([solid(rgb)] * 20).tobytes(), check=True)
            mp4s[name] = mp4
        gd = grade_of(video_frames(mp4s["dark"], 6), "video")
        gw = grade_of(video_frames(mp4s["warm"], 6), "video")
        assert gd["source"] == "video" and gd["frames"] >= 3, gd
        assert gd["luma_mean"] < gw["luma_mean"] - 0.3, (gd, gw)
        assert near(gw["highlight_hue"], 30, 15), gw

        # An image folder: the grade, plus a palette that is written once and never overwritten.
        from PIL import Image
        imgs = td / "imgs"
        imgs.mkdir()
        for i, rgb in enumerate(((20, 40, 200), (25, 45, 210), (240, 240, 240))):
            Image.fromarray(solid(rgb, 48)).save(imgs / f"{i}.png")
        fr = image_frames(imgs)
        gi = grade_of(fr, "images")
        assert gi["source"] == "images" and gi["frames"] == 3, gi
        pal = palette_of(fr)
        assert any(p["hex"][5:7] > "90" and p["hex"][1:3] < "60" for p in pal), pal   # a blue
        st = merge_style({"grade": {"luma": 99.0, "sat": 0.1}}, gi, pal)
        assert st["grade"]["luma"] == 99.0 and st["grade"]["luma_mean"] == gi["luma_mean"], st
        assert st["graphics"]["palette"] == pal
        st2 = merge_style({"graphics": {"palette": [{"hex": "#000000", "pct": 100}]}}, gi, pal)
        assert st2["graphics"]["palette"][0]["hex"] == "#000000", st2
    print("grade.py demo ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("measure")
    p.add_argument("source", help="a video file or a folder of images")
    p.add_argument("--style", help="style.json to write the grade block into")
    p.add_argument("--frames", type=int, default=SAMPLE_N)
    p.set_defaults(fn=cmd_measure)
    sub.add_parser("demo").set_defaults(fn=lambda a: demo())
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
