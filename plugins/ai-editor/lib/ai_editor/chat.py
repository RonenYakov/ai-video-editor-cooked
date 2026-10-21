#!/usr/bin/env python3
"""Native chat: one `claude -p` per message, streamed as normalized events. Stdlib only.

    start(text, session_id=None, context=None) -> turn_id
    events(turn_id, since=0) -> (events, next_index, finished)
    stop(turn_id) -> bool
    session_of(turn_id) -> session id or None
    python3 chat.py "hello" [--resume SID]     print the events as they arrive

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


def _run(turn, text):
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
        done = any(e["type"] == "done" for e in turn["events"])
        if turn["stopped"]:
            _add(turn, [{"type": "done", "session": turn["session"], "cost": None}] if not done else [])
        elif code != 0 and not done:
            msg = ("".join(err).strip() or f"claude exited with code {code}")[-600:]
            _add(turn, [{"type": "error", "text": msg}])
    except OSError as e:
        _add(turn, [{"type": "error", "text": f"Could not start claude: {e}"}])
    finally:
        with _lock:
            turn["finished"] = True
            turn["ended"] = time.time()


def start(text, session_id=None, context=None):
    if context and not session_id:
        text = f"{context.rstrip()}\n\n{text}"
    tid = uuid.uuid4().hex
    turn = {"events": [], "finished": False, "session": session_id, "resume": session_id, "proc": None,
            "stopped": False, "streamed": False, "ended": 0}
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
    else:
        sys.exit(main(sys.argv[1:]))
