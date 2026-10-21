#!/usr/bin/env python3
"""Native chat: one `claude -p` per message, streamed as normalized events. Stdlib only.

    start(text, session_id=None, context=None) -> turn_id
    events(turn_id, since=0) -> (events, next_index, finished)
    stop(turn_id) -> bool
    session_of(turn_id) -> session id or None
    python3 chat.py "hello" [--resume SID]     print the events as they arrive
    python3 chat.py demo                       self-check (no claude, no network)

Events: {"type":"session","id"} {"type":"text","text"} {"type":"tool","name","summary"}
{"type":"done","session","cost"} {"type":"error","text"}. The prompt goes in on stdin (a Windows claude.cmd would
mangle newlines and quotes in an argument); the plugin dir and permissions come from launcher.plan().
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import library  # noqa: E402

KEEP_S = 3600
_turns = {}
_lock = threading.Lock()


def argv(session_id=None):
    """claude -p (prompt on stdin) with launcher.plan()'s plugin dirs and permission settings."""
    import launcher   # late: launcher imports home, which imports this module
    base = launcher.plan(claude=shutil.which("claude"), prompt="")[:-1]   # drop the (empty) positional prompt
    cmd = base[:1] + ["-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages"] + base[1:]
    return cmd + (["--resume", session_id] if session_id else [])


def summary(name, inp):
    inp = inp if isinstance(inp, dict) else {}
    if name == "Skill":
        return str(inp.get("skill") or "")
    for k in ("command", "file_path", "path", "pattern", "url", "description"):
        if inp.get(k):
            return " ".join(str(inp[k]).split())[:120]
    return ""


def normalize(ev, turn):
    """Events for one stream-json line. turn["streamed"]: text already sent as deltas for this message."""
    t = ev.get("type")
    if t == "system" and ev.get("subtype") == "init":
        return [{"type": "session", "id": ev.get("session_id")}]
    if t == "stream_event":
        e = ev.get("event") or {}
        d = e.get("delta") or {}
        if e.get("type") == "content_block_delta" and d.get("type") == "text_delta" and d.get("text"):
            turn["streamed"] = True
            return [{"type": "text", "text": d["text"]}]
        return []
    if t == "assistant":
        out = []
        for b in (ev.get("message") or {}).get("content") or []:
            if b.get("type") == "text" and b.get("text") and not turn["streamed"]:
                out.append({"type": "text", "text": b["text"]})
            elif b.get("type") == "tool_use":
                out.append({"type": "tool", "name": b.get("name", ""), "summary": summary(b.get("name"), b.get("input"))})
        turn["streamed"] = False
        return out
    if t == "result":
        if ev.get("is_error"):
            return [{"type": "error", "text": str(ev.get("result") or "Claude stopped with an error")},
                    {"type": "done", "session": ev.get("session_id"), "cost": ev.get("total_cost_usd")}]
        return [{"type": "done", "session": ev.get("session_id"), "cost": ev.get("total_cost_usd")}]
    return []


def _add(turn, evs):
    with _lock:
        for e in evs:
            turn["events"].append(e)
            if e["type"] == "session" and e.get("id"):
                turn["session"] = e["id"]
            if e["type"] == "done" and e.get("session"):
                turn["session"] = e["session"]


def _attempt(turn, text):
    """One `claude -p` run, its events added to turn. -> (exit code, stderr), code None when it never started."""
    err = []
    try:
        p = subprocess.Popen(argv(turn["resume"]), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             cwd=str(library.path()), text=True, encoding="utf-8", errors="replace",
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        turn["proc"] = p
        threading.Thread(target=lambda: err.append(p.stderr.read()), daemon=True).start()
        p.stdin.write(text)
        p.stdin.close()
        for line in p.stdout:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            _add(turn, normalize(ev, turn))
        code = p.wait()
        time.sleep(0.05)
        return code, "".join(err).strip()
    except OSError as e:
        return None, f"Could not start claude: {e}"


def _nothing_yet(turn):
    """True when the run produced no reply at all: how a --resume id Claude Code no longer has fails."""
    return not any(e["type"] in ("session", "text", "tool", "done") for e in turn["events"])


def _run(turn, text):
    try:
        code, err = _attempt(turn, text)
        # A stale --resume id (the session was pruned, or came from another config dir) fails before any event
        # arrives. Drop it and run once more fresh: otherwise every later message in the project fails the same
        # way and its chat is lost for good. turn["reset"] tells the caller to forget the id it passed in.
        if turn["resume"] and code not in (0, None) and not turn["stopped"] and _nothing_yet(turn):
            turn["resume"] = turn["session"] = None
            turn["reset"] = True
            code, err = _attempt(turn, text)
        done = any(e["type"] == "done" for e in turn["events"])
        if turn["stopped"]:
            _add(turn, [{"type": "done", "session": turn["session"], "cost": None}] if not done else [])
        elif code is None:
            _add(turn, [{"type": "error", "text": err}])
        elif code != 0 and not done:
            _add(turn, [{"type": "error", "text": (err or f"claude exited with code {code}")[-600:]}])
    finally:   # the page polls until finished: it must be set whatever happened
        with _lock:
            turn["finished"] = True
            turn["ended"] = time.time()


def start(text, session_id=None, context=None):
    if context and not session_id:
        text = f"{context.rstrip()}\n\n{text}"
    tid = uuid.uuid4().hex
    turn = {"events": [], "finished": False, "session": session_id, "resume": session_id, "proc": None,
            "stopped": False, "streamed": False, "ended": 0, "reset": False}
    with _lock:
        for k in [k for k, v in _turns.items() if v["finished"] and time.time() - v["ended"] > KEEP_S]:
            del _turns[k]
        _turns[tid] = turn
    threading.Thread(target=_run, args=(turn, text), daemon=True).start()
    return tid


def events(turn_id, since=0):
    with _lock:
        t = _turns.get(turn_id)
        if not t:
            return [], since, True
        return t["events"][since:], len(t["events"]), t["finished"]


def session_of(turn_id):
    with _lock:
        t = _turns.get(turn_id)
        return t["session"] if t else None


def session_reset(turn_id):
    """True when the session id passed to start() was stale and abandoned: stop storing it."""
    with _lock:
        t = _turns.get(turn_id)
        return bool(t and t["reset"])


def stop(turn_id):
    with _lock:
        t = _turns.get(turn_id)
        p = t and t["proc"]
        if not p or t["finished"]:
            return False
        t["stopped"] = True
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
    else:
        p.kill()
    return True


FAKE = """import json, sys
sys.stdin.read()
if "--resume" in sys.argv:
    sys.stderr.write("No conversation found with session ID: gone\\n")
    sys.exit(1)
print(json.dumps({"type": "system", "subtype": "init", "session_id": "fresh-sid"}), flush=True)
print(json.dumps({"type": "result", "subtype": "success", "session_id": "fresh-sid", "total_cost_usd": 0}), flush=True)
"""


def demo():
    """Self-check: a --resume id Claude Code no longer has recovers instead of bricking the project's chat.
    No claude, no network: a fake stands in for it, failing on --resume the way the real one does."""
    global argv
    import tempfile
    real = argv
    with tempfile.TemporaryDirectory() as td:
        fake = Path(td) / "fake_claude.py"
        fake.write_text(FAKE, encoding="utf-8")
        argv = lambda sid=None: [sys.executable, "-I", str(fake)] + (["--resume", sid] if sid else [])   # noqa: E731
        try:
            tid = start("hello", "gone")
            for _ in range(300):
                if events(tid)[2]:
                    break
                time.sleep(0.05)
            evs = events(tid)[0]
        finally:
            argv = real
    kinds = [e["type"] for e in evs]
    assert "error" not in kinds, evs                      # before the retry this was the only event
    assert session_of(tid) == "fresh-sid", evs            # the new session, not the stale one
    assert session_reset(tid) is True, evs                # so the caller stops storing "gone"
    assert kinds.count("session") == 1, kinds             # the failed attempt left nothing behind

    t = {"events": [{"type": "text", "text": "hi"}], "resume": "x", "stopped": False}
    assert not _nothing_yet(t) and _nothing_yet({"events": []})
    print("chat ok")
    return 0


def main(args):
    sid = args[args.index("--resume") + 1] if "--resume" in args else None
    text = next((a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--resume")), "")
    tid = start(text, sid)
    n, done = 0, False
    while not done:
        evs, n, done = events(tid, n)
        for e in evs:
            print(json.dumps(e, ensure_ascii=False), flush=True)
        time.sleep(0.2)
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--argv":
        print(argv(sys.argv[2] if len(sys.argv) > 2 else None))
    elif len(sys.argv) > 1 and sys.argv[1] == "demo":
        sys.exit(demo())
    else:
        sys.exit(main(sys.argv[1:]))
