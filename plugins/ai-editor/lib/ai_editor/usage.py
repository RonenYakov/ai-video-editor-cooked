#!/usr/bin/env python3
"""What each paid use cost: one line per use in $AI_EDITOR_HOME/usage.json, shown in Settings.

    python3 usage.py           the uses so far, newest first
    python3 usage.py demo      self-check

Only ElevenLabs Scribe (the talking-head transcription) is metered here. It bills per hour of audio, so the cost is
worked out from the audio's length at the list price (ElevenLabs API pricing, Scribe v2 batch: $0.22 an hour, keyterm
prompting $0.05 an hour more). Plans with included hours pay less: it is an upper estimate, never a bill.
"""
import json
import os
import sys
import time
from pathlib import Path

USD_PER_HOUR = {"scribe": float(os.environ.get("AI_EDITOR_SCRIBE_USD_HOUR") or 0.22), "keyterms": 0.05}
KEEP = 200   # the newest uses kept


def home():
    return Path(os.environ.get("AI_EDITOR_HOME", Path.home() / ".ai-video-editor"))


def path():
    return home() / "usage.json"


def scribe_cost(seconds, keyterms=False):
    """USD for one Scribe request of `seconds` of audio."""
    rate = USD_PER_HOUR["scribe"] + (USD_PER_HOUR["keyterms"] if keyterms else 0)
    return round(max(0.0, seconds) / 3600 * rate, 4)


def money(usd):
    return "under $0.01" if usd < 0.01 else f"${usd:.2f}"


def line(seconds, usd):
    """'3.2 min of audio, about $0.01' as the page and the job step say it."""
    return f"{seconds / 60:.1f} min of audio, about {money(usd)}"


def load():
    try:
        d = json.loads(path().read_text(encoding="utf-8"))
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def record(service, what, seconds, usd):
    """Add one use. Never raises: a failed note must not fail the transcription."""
    try:
        rows = [{"service": service, "what": what, "seconds": round(seconds, 1), "usd": usd, "at": time.time()}] + load()
        path().parent.mkdir(parents=True, exist_ok=True)
        tmp = path().with_suffix(".tmp")
        tmp.write_text(json.dumps(rows[:KEEP], indent=1), encoding="utf-8")
        os.replace(tmp, path())
    except OSError:
        pass


def summary(service):
    """{'uses', 'usd', 'last'} for one service (Settings)."""
    rows = [r for r in load() if r.get("service") == service]
    return {"uses": len(rows), "usd": round(sum(r.get("usd") or 0 for r in rows), 4), "last": rows[0] if rows else None}


def demo():
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        os.environ["AI_EDITOR_HOME"] = t
        assert summary("elevenlabs") == {"uses": 0, "usd": 0, "last": None}
        assert scribe_cost(3600) == 0.22 and scribe_cost(3600, keyterms=True) == 0.27
        c = scribe_cost(192)   # a 3.2 minute take
        assert c == 0.0117 and line(192, c) == "3.2 min of audio, about $0.01", line(192, c)
        assert money(0.004) == "under $0.01"
        record("elevenlabs", "take.mov", 192, c)
        record("elevenlabs", "two.mov", 600, scribe_cost(600))
        s = summary("elevenlabs")
        assert s["uses"] == 2 and s["last"]["what"] == "two.mov" and s["usd"] == round(c + scribe_cost(600), 4), s
        path().write_text("not json", encoding="utf-8")
        assert summary("elevenlabs")["uses"] == 0, "a broken file reads as none"
    print("usage demo ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["demo"]:
        demo()
    else:
        for r in load():
            print(f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(r['at']))}  {r['service']}  {r['what']}  "
                  f"{line(r['seconds'], r['usd'])}")
