#!/usr/bin/env python3
"""One reference video's breakdown, joined from a creator teardown's files. Stdlib only.

    python3 reference.py HANDLE          the teardown's videos: id, title, thumb, has_beats
    python3 reference.py HANDLE ID       that video's breakdown as JSON

Reads <library>/creator-teardowns/<handle>/: videos.json, beats/<id>.json (video-analyst's beat map,
saved by the teardown's step 3), metrics.json, video/<id>.visual.json, format.json. A value the
files do not hold is null or absent, never guessed. Teardowns made before beats/ get
"needs_reanalyse": true.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import library  # noqa: E402


def _dir(handle):
    return library.path(make=False) / "creator-teardowns" / handle


def _load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _rows(d):
    j = _load(d / "videos.json")
    return j.get("videos") or [] if isinstance(j, dict) else []


def _thumb(d, v):
    t = d / "thumbs" / f"{v['id']}.jpg"
    return str(t) if t.exists() else v.get("thumbnail")


def list_refs(handle):
    d = _dir(handle)
    return [{"id": v["id"], "title": v.get("title"), "thumb": _thumb(d, v),
             "has_beats": (d / "beats" / f"{v['id']}.json").exists()} for v in _rows(d)]


def breakdown(handle, vid_id):
    d = _dir(handle)
    v = next((r for r in _rows(d) if r.get("id") == vid_id), None)
    if v is None:
        return None
    beats = _load(d / "beats" / f"{vid_id}.json")
    m = next((r for r in _load(d / "metrics.json") or [] if r.get("id") == vid_id), None) or {}
    vis = _load(d / "video" / f"{vid_id}.visual.json") or {}
    fmt = _load(d / "format.json") or {}
    mp4 = d / "video" / f"{vid_id}.mp4"
    out = {
        "id": vid_id, "handle": handle, "title": v.get("title"), "url": v.get("webpage_url"),
        "views": v.get("view_count"), "thumb": _thumb(d, v),
        "platform": (_load(d / "videos.json") or {}).get("platform"),
        "duration": v.get("duration"),
        "video_path": str(mp4) if mp4.exists() else None,
        "beats": beats,
        "pace": {k: m.get(k) for k in ("wpm", "wpm_thirds", "pause_median_ms", "pauses_per_min",
                                       "longest_pause_s", "first_word_at", "filler_rate_per_100w")},
        "visual": {k: vis.get(k) for k in ("cuts_per_10s", "median_shot_s", "zooms_per_min")},
        "format": "kept" if vid_id in fmt.get("kept", []) else
                  "left_out" if any(x.get("id") == vid_id for x in fmt.get("left_out", [])) else None,
    }
    if beats is None:
        out["needs_reanalyse"] = True
    return out


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    r = breakdown(a[0], a[1]) if len(a) > 1 else list_refs(a[0])
    print(json.dumps(r, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
