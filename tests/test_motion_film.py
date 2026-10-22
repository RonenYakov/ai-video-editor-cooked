#!/usr/bin/env python3
"""End to end checks for "New motion video" (docs/EXEC-motion-film.md). Real renders, small and short.

    python tests/test_motion_film.py            every check; needs node, ffmpeg and the engine's playwright-core
                                                (plugins/ai-editor/motion-engine: npm install, or setup.py motion-engine)

Checks: a film renders; probe passes a smooth film, fails an undeclared jump, passes it once declared; a grade
moves saturation the way it says; still.mjs draws one frame per beat; ease() matches GSAP's formulas; a reference
measured by refs.py feeds a render's grade; the builder and reviser agents pin their model and effort.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = Path(os.environ.get("MOTION_ENGINE") or ROOT / "plugins/ai-editor/motion-engine")
REFS = ROOT / "plugins/ai-editor/skills/motion-film/scripts/refs.py"
AGENTS = ROOT / "plugins/ai-editor/agents"
NODE = shutil.which("node")

# A smooth, colourful film: three bands and a box sliding across. JUMP > 0 teleports the box at that time.
FILM = """<!doctype html><meta charset="utf-8"><canvas id="c"></canvas>
<script type="module">
import { clamp } from '/engine/lib/motion.js';
const q = new URLSearchParams(location.search), W = +q.get('w'), H = +q.get('h'), JUMP = %s;
const c = document.getElementById('c'); c.width = W; c.height = H; const x = c.getContext('2d');
window.ready = document.fonts.ready;
window.seek = (t) => {
  ['#d23a2a', '#2aa84a', '#2a5ad2'].forEach((col, i) => { x.fillStyle = col; x.fillRect(0, i * H / 3, W, H / 3); });
  const p = clamp(t / 1.0) * 0.6 + (JUMP && t >= JUMP ? 0.35 : 0);
  x.fillStyle = '#f2eee6'; x.fillRect(W * p, H * 0.4, W * 0.25, H * 0.2);
};
</script>"""

results = []


def check(name, fn):
    try:
        fn()
        results.append((name, "ok", ""))
    except Exception as e:  # noqa: BLE001 - report every check, not just the first failure
        results.append((name, "FAIL", f"{type(e).__name__}: {e}"))


def node(*args, ok=True):
    r = subprocess.run([NODE, *map(str, args)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if ok and r.returncode:
        raise AssertionError(f"node {' '.join(map(str, args))} exit {r.returncode}\n{(r.stdout + r.stderr)[-1500:]}")
    return r


def film(tmp, name, jump=0, **cfg):
    d = Path(tmp) / name
    node(ENGINE / "tools/new.mjs", d)
    (d / "film.html").write_text(FILM % jump, encoding="utf-8")
    c = json.loads((d / "film.config.json").read_text(encoding="utf-8"))
    c.update({"duration": 1, "fps": 30, "subframes": 1, "scale": 1, "loop": False,
              "formats": [{"name": "9:16", "w": 270, "h": 480}], **cfg})
    (d / "film.config.json").write_text(json.dumps(c), encoding="utf-8")
    return d


def stat(mp4, key):
    """Mean of one ffmpeg signalstats value over every frame."""
    r = subprocess.run(["ffmpeg", "-i", str(mp4), "-vf", f"signalstats,metadata=print:key=lavfi.signalstats.{key}", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    vals = [float(v) for v in re.findall(rf"{key}=([\d.]+)", r.stderr)]
    assert vals, f"no {key} from ffmpeg"
    return sum(vals) / len(vals)


def render(d, *flags):
    node(ENGINE / "render.mjs", d, "--draft", *flags)
    out = d / "out" / "silent-9x16-draft.mp4"
    assert out.exists() and out.stat().st_size > 1000, f"draft missing or empty: {out}"
    return out


def main():
    if not NODE or not shutil.which("ffmpeg"):
        sys.exit("needs node and ffmpeg on PATH")
    if not (ENGINE / "node_modules" / "playwright-core").is_dir():
        sys.exit(f"engine not installed: npm install in {ENGINE} (or set MOTION_ENGINE to an installed copy)")
    tmp = tempfile.mkdtemp(prefix="motion_film_test_")
    try:
        run_checks(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for name, status, why in results:
        print(f"{status:4}  {name}" + (f"\n      {why}" if why else ""))
    bad = [r for r in results if r[1] != "ok"]
    print(f"{len(results) - len(bad)}/{len(results)} ok")
    sys.exit(1 if bad else 0)


def run_checks(tmp):
    def renders():
        render(film(tmp, "renders"))
    check("a film renders a draft", renders)

    def gate():   # a cooked. film (.gate) renders nothing until review.py recorded Approve on this exact beat sheet
        d = film(tmp, "gated")
        (d / ".gate").write_text("beats\n", encoding="utf-8")
        r = node(ENGINE / "render.mjs", d, "--draft", ok=False)
        assert r.returncode == 3 and "not approved" in r.stderr, r.stderr[-400:]
        (d / "beats.sheet.json").write_text('{"beats": [{"id": 1, "t": 0, "dur": 1}]}', encoding="utf-8")
        sys.path.insert(0, str(ROOT / "plugins/ai-editor/lib/ai_editor"))
        import review
        review.approve_beats(d)
        render(d)
        (d / "beats.sheet.json").write_text('{"beats": [{"id": 1, "t": 0, "dur": 2}]}', encoding="utf-8")
        r = node(ENGINE / "render.mjs", d, "--draft", ok=False)
        assert r.returncode == 3, "a changed sheet rendered without a new Approve"
    check("gate: no render before the beat sheet is approved, none after it changes", gate)

    def probe():
        smooth = film(tmp, "smooth")
        r = node(ENGINE / "probe.mjs", smooth, ok=False)
        assert r.returncode == 0, "smooth film failed probe:\n" + r.stdout[-800:]
        jump = film(tmp, "jump", jump=0.5)
        r = node(ENGINE / "probe.mjs", jump, ok=False)
        found = json.loads((jump / "out" / "probe.json").read_text(encoding="utf-8"))["findings"]
        assert r.returncode == 1 and any(f["kind"] == "cut" and abs(f["t"] - 0.5) < 0.07 for f in found), found
        declared = film(tmp, "declared", jump=0.5, cuts=[0.5])
        r = node(ENGINE / "probe.mjs", declared, ok=False)
        assert r.returncode == 0, "a declared cut still failed:\n" + r.stdout[-800:]
    check("probe: smooth passes, undeclared jump fails, declared cut passes", probe)

    def grade():
        base = stat(render(film(tmp, "nograde")), "SATAVG")
        dull = stat(render(film(tmp, "dull", grade={"saturation": 0.1, "black": 0.0, "white": 1.0})), "SATAVG")
        vivid = stat(render(film(tmp, "vivid", grade={"saturation": 0.65, "black": 0.0, "white": 1.0})), "SATAVG")
        assert dull < base * 0.95 < base * 1.05 < vivid, f"saturation dull {dull:.1f} / none {base:.1f} / vivid {vivid:.1f}"
        d = film(tmp, "skip", grade={"saturation": 0.1})
        off = stat(render(d, "--nograde"), "SATAVG")
        assert abs(off - base) < base * 0.02, f"--nograde changed saturation: {off:.1f} vs {base:.1f}"
    check("grade: low saturation dulls, high saturation lifts, --nograde leaves it", grade)

    def stills():
        d = film(tmp, "stills")
        node(ENGINE / "tools/still.mjs", d, "0.1=stills/beat-01.png", "0.9=stills/beat-02.png")
        a, b = (d / "stills" / "beat-01.png").read_bytes(), (d / "stills" / "beat-02.png").read_bytes()
        assert a[:8] == b"\x89PNG\r\n\x1a\n" and b[:8] == a[:8] and a != b, "stills missing or identical"
        assert node(ENGINE / "tools/still.mjs", d, ok=False).returncode == 1, "no pairs should be a usage error"
    check("still.mjs: one PNG per beat, from seek(t)", stills)

    def eases():
        js = ("import { ease, tween } from " + json.dumps((ENGINE / "lib/motion.js").as_uri()) + ";"
              "console.log(JSON.stringify([ease('power2.out',.5), ease('power2.in',.5), ease('power1.out',.5), ease('none',.3),"
              "ease('power3.inOut',.25)+ease('power3.inOut',.75), Math.max(...Array.from({length:101},(_, i)=>ease('back.out(1.7)',i/100))),"
              "ease('expo.out',0), ease('expo.out',1), tween(5, 1, 2, 10, 20, 'power2.out'), tween(0, 1, 2, 10, 20, 'power2.out')]));")
        r = subprocess.run([NODE, "--input-type=module", "-e", js], capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, r.stderr
        v = json.loads(r.stdout)
        want = [0.875, 0.125, 0.75, 0.3, 1.0, None, 0.0, 1.0, 20.0, 10.0]
        for i, (got, w) in enumerate(zip(v, want)):
            assert w is None or abs(got - w) < 1e-6, f"value {i}: {got} != {w}"
        assert v[5] > 1.05, f"back.out(1.7) should overshoot, peak {v[5]}"
        bad = subprocess.run([NODE, "--input-type=module", "-e", "import { ease } from " + json.dumps((ENGINE / "lib/motion.js").as_uri()) + "; ease('wobble.out', .5)"],
                             capture_output=True, text=True, timeout=30)
        assert bad.returncode != 0 and "wobble" in bad.stderr, "an unknown ease must throw with its name"
    check("ease(): GSAP values, overshoot, endpoints, tween holds, unknown throws", eases)

    def refs_to_render():
        d = film(tmp, "withref")
        src = Path(tmp) / "warm.mp4"
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x568:rate=30:duration=3", "-vf", "eq=saturation=0.3",
                        "-pix_fmt", "yuv420p", str(src)], capture_output=True, check=True)
        py = sys.executable
        r = subprocess.run([py, str(REFS), "add", str(d), str(src), "--take", "the whole look"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600)
        assert r.returncode == 0, (r.stdout + r.stderr)[-1500:]
        refs = json.loads((d / "refs.json").read_text(encoding="utf-8")) if (d / "refs.json").exists() else \
            json.loads((d / "refs" / "refs.json").read_text(encoding="utf-8"))
        rid = refs[-1]["id"]
        m = json.loads((d / "refs" / f"{rid}.json").read_text(encoding="utf-8"))
        assert isinstance(m.get("grade", {}).get("saturation"), (int, float)), m.get("grade")
        assert (d / "refs" / f"{rid}.png").exists(), "reference still missing"
        c = json.loads((d / "film.config.json").read_text(encoding="utf-8"))
        c["grade"] = f"refs/{rid}.json"
        (d / "film.config.json").write_text(json.dumps(c), encoding="utf-8")
        graded = stat(render(d), "SATAVG")
        base = stat(render(d, "--nograde"), "SATAVG")
        assert graded < base, f"a desaturated reference should dull the film: {graded:.1f} vs {base:.1f}"
    check("refs.py measures a video and its grade drives the render", refs_to_render)

    def agents():
        def fm(name):
            t = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
            return dict(re.findall(r"^(\w+):\s*(.+)$", t.split("---")[1], re.M))
        b, r = fm("motion-builder"), fm("motion-reviser")
        assert (b.get("model"), b.get("effort")) == ("opus", "xhigh"), b
        assert (r.get("model"), r.get("effort")) == ("opus", "medium"), r
        skill = ROOT / "plugins/ai-editor/skills/motion-film/SKILL.md"
        assert skill.exists(), "motion-film skill missing"
        s = skill.read_text(encoding="utf-8")
        assert "motion-builder" in s and "xhigh" in s and "motion-reviser" in s, "the skill must launch both agents"
        assert len(s.splitlines()) < 200, "SKILL.md over 200 lines"
    check("agents: builder opus+xhigh, reviser opus+medium, launched by the skill", agents)


if __name__ == "__main__":
    main()
