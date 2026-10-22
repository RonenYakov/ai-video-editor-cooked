#!/usr/bin/env python3
"""Projects: one piece of work that links videos, references and edit folders. Stdlib only.

    python3 projects.py new "<name>" --kind talking-head [--source PATH]...
    python3 projects.py list [--all]       newest first, JSON (--all adds archived)
    python3 projects.py show SLUG
    python3 projects.py link SLUG FIELD VALUE     FIELD: sources, refs, edits (append) or style (set)
    python3 projects.py rename SLUG NAME
    python3 projects.py archive SLUG [--off]
    python3 projects.py migrate            one project per existing edit folder or motion film not yet linked
    python3 projects.py demo               self-check (a temp library, no network)

Stored as <library>/projects/<slug>/project.json. Nothing is moved: a project only points at the library folders.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import library  # noqa: E402

KINDS = ("edit", "talking-head", "motion")
LISTS = ("sources", "refs", "edits")
MOTION_MARKS = ("motion-film.json", "beat-sheet.json", "beat-sheet.md", "beats.json", "refs.json")
HEAD_MARKS = ("cut.mp4", "spans.json")


def _root():
    return library.path() / "projects"


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _file(slug):
    return _root() / slug / "project.json"


def _write(p):
    p["updated"] = _now()
    f = _file(p["slug"])
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(p, indent=1), encoding="utf-8")
    os.replace(tmp, f)
    return p


def show(slug):
    try:
        return json.loads(_file(slug).read_text(encoding="utf-8"))
    except OSError:
        raise KeyError(slug) from None


def _abs(v):
    return str(Path(os.path.expanduser(str(v))).resolve())


def new(name, kind, sources=None):
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"
    slug, n = base, 2
    while _file(slug).exists():
        slug, n = f"{base}-{n}", n + 1
    now = _now()
    return _write({"slug": slug, "name": name, "kind": kind, "created": now, "updated": now,
                   "sources": [_abs(s) for s in dict.fromkeys(sources or [])], "refs": [], "style": None,
                   "edits": [], "chat_session": None, "archived": False})


def list_all(include_archived=False):
    out = []
    for f in _root().glob("*/project.json"):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if include_archived or not p.get("archived"):
            out.append(p)
    return sorted(out, key=lambda p: p.get("updated", ""), reverse=True)


def link(slug, field, value):
    p = show(slug)
    if field == "style":
        p["style"] = value
    elif field in LISTS:
        v = _abs(value) if field != "refs" else str(value)
        if v not in p[field]:
            p[field].append(v)
    else:
        raise ValueError(f"field must be one of {LISTS + ('style',)}")
    return _write(p)


def set_session(slug, session_id):
    p = show(slug)
    p["chat_session"] = session_id
    return _write(p)


def rename(slug, name):
    p = show(slug)
    p["name"] = name
    return _write(p)


def archive(slug, on=True):
    p = show(slug)
    p["archived"] = bool(on)
    return _write(p)


def for_edit(edit_dir):
    d = _abs(edit_dir)
    return next((p["slug"] for p in list_all(True) if d in p.get("edits", [])), None)


def _guess(d):
    if d.parent.name == "films" or any((d / m).exists() for m in MOTION_MARKS):
        return "motion"
    return "talking-head" if any((d / m).exists() for m in HEAD_MARKS) else "edit"


def migrate():
    """A project for every edit folder and motion film not linked yet. Safe to run again."""
    lib = library.path()
    dirs = [Path(e["dir"]) for e in library.entries()] + sorted(p for p in (lib / "films").glob("*") if p.is_dir())
    made = 0
    for d in dirs:
        if for_edit(d):
            continue
        r = library._review(d) or {}
        src = [r["video"]] if r.get("video") and Path(r["video"]).is_file() else []
        p = new(r.get("label") or r.get("name") or d.name, _guess(d), src)
        link(p["slug"], "edits", d)
        made += 1
    return made


def demo():
    """Self-check: the three kinds, their folders and the chat session that must survive a restart.
    Nothing outside a temp library (no network, no claude)."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        os.environ["AI_EDITOR_LIBRARY"] = td
        assert KINDS == ("edit", "talking-head", "motion"), KINDS

        a = new("My Talk", "talking-head", [Path(td) / "take.mov"])
        assert a["slug"] == "my-talk" and a["kind"] == "talking-head" and a["chat_session"] is None
        assert a["sources"] and Path(a["sources"][0]).is_absolute(), a["sources"]
        assert new("My Talk", "edit")["slug"] == "my-talk-2", "a repeated name gets its own folder"
        try:
            new("Nope", "launch")
            raise AssertionError("an unknown kind must not be accepted")
        except ValueError:
            pass

        # the chat session is what "it forgot everything" depends on: it has to come back off disk
        set_session("my-talk", "sid-1")
        assert show("my-talk")["chat_session"] == "sid-1"
        assert json.loads(_file("my-talk").read_text(encoding="utf-8"))["chat_session"] == "sid-1"
        set_session("my-talk", None)
        assert show("my-talk")["chat_session"] is None, "a stale id is cleared, not kept"

        link("my-talk", "refs", "https://example.com")
        link("my-talk", "refs", "https://example.com")
        assert show("my-talk")["refs"] == ["https://example.com"], "a reference is not added twice"
        link("my-talk", "edits", Path(td) / "edits" / "my-talk")
        assert for_edit(Path(td) / "edits" / "my-talk") == "my-talk"
        link("my-talk", "style", "@someone")
        assert show("my-talk")["style"] == "@someone"
        try:
            link("my-talk", "nope", "x")
            raise AssertionError("an unknown field must not be accepted")
        except ValueError:
            pass

        # _now() is second resolution, so two projects made in one run tie: age one by hand or the
        # order comes from the filesystem and the sort is never tested
        # age the one that sorts FIRST by name, so "newest first" and any name or filesystem order differ
        g = _file("my-talk")
        aged = json.loads(g.read_text(encoding="utf-8"))
        aged["updated"] = "2000-01-01T00:00:00+00:00"
        g.write_text(json.dumps(aged), encoding="utf-8")
        assert [q["slug"] for q in list_all()] == ["my-talk-2", "my-talk"], "newest first by updated"
        archive("my-talk-2")
        assert [q["slug"] for q in list_all()] == ["my-talk"]
        assert len(list_all(True)) == 2
        archive("my-talk-2", False)
        assert len(list_all()) == 2
        try:
            show("ghost")
            raise AssertionError("an unknown slug must raise")
        except KeyError:
            pass

        # _guess reads the folder, so migrate() files old work under the right kind
        d = Path(td) / "films" / "f1"
        d.mkdir(parents=True)
        assert _guess(d) == "motion"
        d2 = Path(td) / "edits" / "e1"
        d2.mkdir(parents=True)
        assert _guess(d2) == "edit"
        (d2 / "cut.mp4").write_text("x", encoding="utf-8")
        assert _guess(d2) == "talking-head"
    print("projects ok")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("new")
    s.add_argument("name")
    s.add_argument("--kind", default="edit", choices=KINDS)
    s.add_argument("--source", action="append", default=[])
    s = sub.add_parser("list")
    s.add_argument("--all", action="store_true")
    sub.add_parser("show").add_argument("slug")
    s = sub.add_parser("link")
    for a in ("slug", "field", "value"):
        s.add_argument(a)
    s = sub.add_parser("rename")
    s.add_argument("slug")
    s.add_argument("name")
    s = sub.add_parser("archive")
    s.add_argument("slug")
    s.add_argument("--off", action="store_true")
    sub.add_parser("migrate")
    sub.add_parser("demo")
    a = ap.parse_args(argv)
    if a.cmd == "demo":
        return demo()
    try:
        out = {"new": lambda: new(a.name, a.kind, a.source), "list": lambda: list_all(a.all),
               "show": lambda: show(a.slug), "link": lambda: link(a.slug, a.field, a.value),
               "rename": lambda: rename(a.slug, a.name), "archive": lambda: archive(a.slug, not a.off),
               "migrate": lambda: {"created": migrate()}}[a.cmd]()
    except (KeyError, ValueError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
