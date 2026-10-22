#!/usr/bin/env python3
"""Stop and the skills a video used. Stdlib only.

A PreToolUse hook on every tool (hooks/hooks.json) runs this with the hook JSON on stdin.

Stop: the window's Stop (home.py POST /stop) writes $AI_EDITOR_HOME/stop/<session>. While that file is under STOP_S
old, every tool call of that Claude Code session is denied with a reason that tells Claude to stop, so a Claude deep in
a long run stops at its next step. After STOP_S the file goes and the session works again (the user can type in it).

Skills: each Skill call is added to the video it is about (askhook.asking_edit) as a line of
<edit>/review/skills.jsonl, {"skill", "at"}; Your videos and the video's editor show them.

Claude needs you in the Terminal: a Notification hook (a permission prompt, a question no page took, Claude idle and
waiting) from a Claude the editor knows (one holding a job, listening, or on a video) writes $AI_EDITOR_HOME/terminal.json,
{"session", "message", "at"}; every open page shows it and chimes once (ask.js). That session's next tool call or the
user typing in it (UserPromptSubmit) clears it.

    python3 toolhook.py          the hook (stdin: hook JSON); prints nothing unless it denies; always exits 0
    python3 toolhook.py notify   the Notification hook          python3 toolhook.py clear   the UserPromptSubmit hook
    python3 toolhook.py stop     the Stop hook: a turn that ends on a question typed in the Terminal shows on the pages
    python3 toolhook.py demo     self-check
"""
import contextlib
import io
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import askhook  # noqa: E402

STOP_S = 120
REASON = ("The user pressed Stop in the cooked. window. Stop now: run nothing else. Say in one line what was left "
          "unfinished, then wait for the user to type in this Terminal.")


def stop_file(sid):
    return askhook.pages().parent / "stop" / sid


def stopped(sid, now=None):
    """True while the window's Stop holds this session; an old Stop file is removed."""
    if not sid:
        return False
    f = stop_file(sid)
    try:
        if (now or time.time()) - f.stat().st_mtime < STOP_S:
            return True
        f.unlink()
    except OSError:
        pass
    return False


# Paid generations (Higgsfield credits, ElevenLabs): at most PAID_PER_MESSAGE per message the user sends. The count
# starts again when the user types (UserPromptSubmit, `clear`); past it every paid call is denied until they answer.
PAID_PER_MESSAGE = int(os.environ.get("AI_EDITOR_PAID_PER_MESSAGE") or 2)
PAID = (("mcp__higgsfiled__", "mcp__higgsfield__"),
        ("generate_", "upscale_", "execute_preset", "motion_control", "reframe", "outpaint_", "remove_background",
         "dubbing", "voice_change", "create_voice", "ai_influencer_generate", "shorts_studio_create", "build_ai_influencer"))
PAID_ELEVEN = ("mcp__ElevenLabs__creative_generate_", "mcp__ElevenLabs__creative_edit_", "mcp__ElevenLabs__creative_design_",
               "mcp__ElevenLabs__creative_run_flow")


def paid(tool):
    t = str(tool or "")
    return t.startswith(PAID_ELEVEN) or any(t.startswith(p + k) for p in PAID[0] for k in PAID[1])


def spend_file(sid):
    return askhook.pages().parent / "spend" / sid


def spend(sid, tool):
    """A deny reason when this paid call is over the limit for the user's last message, else None (and counted)."""
    if not sid or not paid(tool):
        return None
    f = spend_file(sid)
    try:
        n = int(f.read_text(encoding="utf-8") or 0)
    except (OSError, ValueError):
        n = 0
    if n >= PAID_PER_MESSAGE:
        return (f"Spending limit: {PAID_PER_MESSAGE} paid generations (Higgsfield or ElevenLabs credits) per message from the "
                f"user, and this message has used them. Do not try again or another way. Show what you made, say what the "
                f"next one would make and roughly what it costs, and ask the user before spending more.")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(str(n + 1), encoding="utf-8")
    return None


def terminal_file():
    return askhook.pages().parent / "terminal.json"


def ours(payload, sid):
    """A Claude the editor knows: it holds or held a job, listens for jobs, or works on a video."""
    if any(j.get("owner") == sid for j in askhook.home_jobs()):
        return True
    try:
        if (askhook.pages().parent / "home" / ".listening").read_text(encoding="utf-8").strip() == sid:
            return True
    except OSError:
        pass
    return bool(askhook.asking_edit(payload, sid))


def notify(payload):
    sid = payload.get("session_id") or ""
    if not sid or not ours(payload, sid):
        return None
    return askhook.say_terminal(sid, payload.get("message") or "")


def last_text(transcript):
    """The last thing Claude wrote to the user in this session (its transcript), or ""."""
    try:
        with open(transcript, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - (1 << 20)))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except (OSError, TypeError):
        return ""
    for ln in reversed(lines):
        try:
            m = json.loads(ln).get("message") or {}
        except ValueError:
            continue
        if m.get("role") == "assistant":
            t = " ".join(c.get("text", "") for c in m.get("content") or [] if isinstance(c, dict) and c.get("type") == "text").strip()
            if t:
                return t
    return ""


def ended_on_question(payload):
    """A Stop hook: Claude ended its turn on a question typed in the Terminal (not through AskUserQuestion), so the
    pages say so. The question is the last sentence with a "?" near the end of what it wrote."""
    sid = payload.get("session_id") or ""
    t = last_text(payload.get("transcript_path"))
    tail = t[-400:]
    if not sid or "?" not in tail or not ours(payload, sid):
        return None
    q = [x.strip() for x in tail.replace("\n", " ").split("?")[:-1] if x.strip()]
    q = q[-1].split(". ")[-1].split(": ")[-1] + "?" if q else "Claude asked you something."
    return askhook.say_terminal(sid, "Claude asked: " + q)


def clear(sid):
    """The Terminal notice goes once that session moves on."""
    f = terminal_file()
    try:
        if sid and json.loads(f.read_text(encoding="utf-8")).get("session") == sid:
            f.unlink()
    except (OSError, ValueError, AttributeError):
        pass


def record(payload):
    """A Skill call: the skill on its video's skills.jsonl. Nothing when no video is known."""
    name = str((payload.get("tool_input") or {}).get("skill") or "").strip().lstrip("/")
    if not name:
        return None
    edit = askhook.asking_edit(payload, payload.get("session_id") or "")
    if not edit:
        return None
    d = Path(edit) / "review"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "skills.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"skill": name, "at": round(time.time(), 2)}) + "\n")
    return d / "skills.jsonl"


def used(edit):
    """The skills a video ran, in first-run order, with the last one run: [{"skill", "at"}]."""
    out = {}
    try:
        for ln in (Path(edit) / "review" / "skills.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
                out.setdefault(r["skill"], r)["last"] = r["at"]
            except (ValueError, KeyError, TypeError):
                pass
    except OSError:
        pass
    return list(out.values())


def main(mode=None):
    try:
        payload = json.load(sys.stdin)
        if mode == "notify":
            return notify(payload) and 0
        if mode == "stop":
            return ended_on_question(payload) and 0
        clear(payload.get("session_id") or "")
        if mode == "clear":   # the user typed: their paid generations count from zero again
            spend_file(payload.get("session_id") or "x").unlink(missing_ok=True)
            return 0
        if stopped(payload.get("session_id") or ""):
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                     "permissionDecisionReason": REASON}}))
            return 0
        why = spend(payload.get("session_id") or "", payload.get("tool_name"))
        if why:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                     "permissionDecisionReason": why}}))
            return 0
        if payload.get("tool_name") == "Skill":
            record(payload)
    except Exception:
        pass
    return 0


def demo():
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="toolhook_demo_"))
    os.environ["AI_EDITOR_HOME"] = str(tmp)
    assert not stopped("s1")
    stop_file("s1").parent.mkdir(parents=True)
    stop_file("s1").write_text("x", encoding="utf-8")
    assert stopped("s1") and not stopped("s2"), "only that session stops"
    assert not stopped("s1", now=time.time() + STOP_S + 1) and not stop_file("s1").exists(), "Stop lifts after STOP_S"
    # paid generations: PAID_PER_MESSAGE per user message, free tools never counted, a typed message starts again
    assert paid("mcp__higgsfiled__generate_video") and paid("mcp__ElevenLabs__creative_generate_speech")
    assert not paid("mcp__higgsfiled__balance") and not paid("mcp__higgsfiled__jobs_wait") and not paid("Bash")
    assert spend("p1", "mcp__higgsfiled__balance") is None and not spend_file("p1").exists()
    assert [spend("p1", "mcp__higgsfiled__generate_image") is None for _ in range(PAID_PER_MESSAGE)] == [True] * PAID_PER_MESSAGE
    assert "Spending limit" in spend("p1", "mcp__higgsfiled__generate_video") and spend("p2", "mcp__higgsfiled__generate_video") is None
    deny = io.StringIO()
    with contextlib.redirect_stdout(deny):
        sys.stdin = io.StringIO(json.dumps({"session_id": "p1", "tool_name": "mcp__higgsfiled__upscale_video"}))
        main()
    assert json.loads(deny.getvalue())["hookSpecificOutput"]["permissionDecision"] == "deny", deny.getvalue()
    sys.stdin = io.StringIO(json.dumps({"session_id": "p1"}))
    main("clear")
    assert spend("p1", "mcp__higgsfiled__generate_video") is None, "the user typed: allowed again"
    sys.stdin = sys.__stdin__
    edit = tmp / "edits" / "take"
    (tmp / "home").mkdir()
    (tmp / "home" / "state.json").write_text(json.dumps({"jobs": [{"type": "video", "state": "taken", "owner": "s3",
                                                                    "args": {"edit": str(edit)}}]}), encoding="utf-8")
    for sk in ("ai-editor:cut", "my-card-edit", "ai-editor:cut"):
        assert record({"tool_name": "Skill", "tool_input": {"skill": sk}, "session_id": "s3"})
    assert [u["skill"] for u in used(edit)] == ["ai-editor:cut", "my-card-edit"], used(edit)
    assert record({"tool_name": "Skill", "tool_input": {"skill": "x"}, "session_id": "other"}) is None, "no video: nothing"
    # Claude waits in the Terminal: a notice for a known session only, gone once it moves on
    assert notify({"session_id": "stranger", "message": "Claude needs your permission"}) is None, "not the editor's Claude"
    assert notify({"session_id": "s3", "message": "Claude needs your permission to use Bash"})
    assert json.loads(terminal_file().read_text(encoding="utf-8"))["message"].startswith("Claude needs")
    clear("other")
    assert terminal_file().exists()
    clear("s3")
    assert not terminal_file().exists()
    # a turn that ends on a typed question: the pages say so; one that does not: nothing
    tr = tmp / "t.jsonl"
    tr.write_text("\n".join(json.dumps({"message": {"role": "assistant", "content": [{"type": "text", "text": t}]}})
                            for t in ("Working.", "The cut is ready. Should I keep the long pause at 0:42?")), encoding="utf-8")
    assert ended_on_question({"session_id": "s3", "transcript_path": str(tr)})
    assert json.loads(terminal_file().read_text(encoding="utf-8"))["message"] == "Claude asked: Should I keep the long pause at 0:42?"
    clear("s3")
    tr.write_text(json.dumps({"message": {"role": "assistant", "content": [{"type": "text", "text": "Done. Rendered."}]}}), encoding="utf-8")
    assert ended_on_question({"session_id": "s3", "transcript_path": str(tr)}) is None and not terminal_file().exists()
    assert ended_on_question({"session_id": "stranger", "transcript_path": str(tr)}) is None
    print("toolhook demo ok")


if __name__ == "__main__":
    sys.exit(demo() if sys.argv[1:] == ["demo"] else main((sys.argv[1:] or [None])[0]))
