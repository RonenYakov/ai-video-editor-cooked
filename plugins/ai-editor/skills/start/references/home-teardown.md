# Creator teardown and skill-build jobs

The shared rules (waiting, status, questions, keys) are in `home.md`.

### `JOB teardown @handle platform=<p> take=<parts> [notes=<file>] root=<dir>`

The user pasted a creator and pressed "Copy this style". Run the creator-teardown skill's
**Quick mode** (its SKILL.md) on that handle and platform, in `root`. With `urls=<file>` instead of
a platform, use `list <handle> --urls <file>`. Do not ask the parts question: the page asks it.
With `notes=<likes.md>`, read it first: what the user wrote they like about these videos, and their own
files (example videos, screenshots, PDFs, notes, all in `<root>/references/`). Look closer at what they
named: watch those moments frame by frame, measure them, and say what you found first in `look.md` and in
the style's notes. Read or look at every file. An example video is one more video of the format: pull
frames from it with ffmpeg and compare it with the downloaded ones (fetch.py takes links only).
No Gemini key: skip `gemini.py` (do not offer the key in the chat; the page has it).

The scripts report these steps themselves; use these words if you report one (the page lists the ones still to come):

1. `Listed their videos` (fetch.py list)
2. `Downloaded the top 5 and 2 median` (visual.py download --top 5)
3. `Transcribed every word` (fetch.py transcribe --top 5)
4. `Measured cuts, zooms and camera moves` (visual.py measure)
5. `Reading captions and faces` (look.py measure; `--detail "video N of 9"` as it goes; then format_check.py
   check, and when it leaves videos out its first line as `--detail`)
6. `Naming graphics` (graphics.py measure, gemini.py kinds)
7. `Sound effects and music` (sound.py measure)
8. `Writing the style` (report.py build)

The page reads every number itself from `creator-teardowns/<handle>/style.json` and `videos.json`,
so it fills in as each script writes. `report.py build` also prints the style's skill
(`skill edit-like-<handle> -> <path>`). Then read `look.md` and end the job with what not to copy,
one plain sentence per BAN-level AI tell and per move the teardown rejects:
`--result '{"reject": ["..."]}' --done`. Do not open `teardown.html`: the page links it. The style's
`warnings` (report.py: not one format, graphics on the face) show on the finished analysis and the style page by
themselves; say them in chat as well, and never say something is on the page that the page does not show.

A step that stops: say why with `--failed`, in the words of the skill's "If a script stops" table.

### `JOB skill @handle take=<parts> root=<dir>`

The user ticked what to copy and pressed "Build my skill".

1. `--step "Saving your style"`: `profile.py set 'creators=[{"handle":"<h>","take":[...]}]'`, the
   parts mapped `captions`->captions, `pace`->pace, `graphics` (with `entrances` and `layout`)->visuals,
   `sound` kept for the sound answer (`sound.sfx=true`). Then creator-teardown's
   `editplan.py blend <h>-mine --from <h> --take <parts>`: it refreshes the style's skill
   `edit-like-<h>` on the ticked parts and prints its name.
2. `--step "Checking whether it is a format of its own"`: creator-teardown's
   `references/skill-handoff.md` gate, from the numbers in `look.md` and `videos.json`.
3. Pass: `--step "Writing the skill"`, build it as that file says, link it with
   `python3 "${CLAUDE_PLUGIN_ROOT}/lib/ai_editor/styleskill.py" write creator-teardowns/<h>-mine/style.json --format <name>`,
   then `--step "Testing it with one script"` (its "Finally"). Fail: no format skill; the style and its skill are saved.
4. `--result` then `--done`, the JSON the page shows:

```json
{"passed": true, "check": "5 of 5 top videos use this format, all above their median", "style_skill": "edit-like-handle",
 "name": "format-name", "what": "one sentence: what it edits and how, with measured numbers",
 "use_for": "...", "not_for": "...", "path": "~/.claude/skills/format-name",
 "prompts": [{"text": "edit my video like @handle", "what": "one line"}],
 "tools": [{"name": "Your photos folder", "why": "one line", "prompt": "use my photos folder for the cards"}],
 "tested": "Claude wrote one script with it: \"<title>\". 7 beats, 100 words."}
```

A fail sends `{"passed": false, "why": "<which gate question said no>", "style_skill": "edit-like-<h>", "prompts": [...], "tools": [...]}`.
Five prompts, each one the user can paste into Claude Code as it is. Every number in `what`,
`check` and `tested` comes from the teardown or the script; leave a field out rather than guess.

### `JOB cancel teardown @handle`

The user pressed Stop on that creator's analysing card. Stop that teardown's running commands (TaskStop),
leave any other analysis running, and say so in one line.

