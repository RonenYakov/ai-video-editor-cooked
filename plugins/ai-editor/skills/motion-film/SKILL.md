---
name: motion-film
description: Builds a whole motion video from scratch on the Motion Studio engine (code-drawn frames, true accumulation motion blur, per-shot shutter), from an idea, the profile's brand kit and optional references (motion videos, talking-head videos, websites, still images). Measures each reference, writes the brief, shows a beat sheet with one still per beat on the review page for approval, then has the motion-builder agent compose and probe the film, takes timed notes on the draft through the motion-reviser agent, and renders and muxes the final into the library's films folder. Use for the home page's new motion video job (JOB motion), or when the user asks for a new motion film, a motion video from scratch or a video built from code. Not for animated clips laid over a talking head (motion), not for a cut or styled edit of footage (cut, style-edit), not for a product demo from a site (product-video).
license: MIT
compatibility: Node 20+, ffmpeg, Python 3.9+ with the tool venv, and the motion engine that the setup skill's motion-engine step copies to AI_EDITOR_HOME/motion-engine (about 1 minute, once; it reuses the Chrome the renderer step downloads). Runs from the full ai-editor plugin folder.
---

# Motion film

Paths: `${CLAUDE_SKILL_DIR}` means the folder containing this SKILL.md, and `${CLAUDE_PLUGIN_ROOT}` the plugin folder two levels above it.

Every question goes in the question box: the AskUserQuestion tool (2-4 options, recommended first).

An idea, a brand and some references in. A finished MP4 out, built from `film.html`, a pure function of time
(`window.seek(t)`), never a template. Run the scripts with `python3` on Mac and Linux, `py` on Windows.
`ENGINE` is `<AI_EDITOR_HOME or ~/.ai-video-editor>/motion-engine`. `R="${CLAUDE_PLUGIN_ROOT}/lib/ai_editor/review.py"`.
`FILM` is `<library>/films/<name>`, absolute. The library: `python3 "${CLAUDE_PLUGIN_ROOT}/lib/ai_editor/library.py" path`.
Films live in the library, never in the plugin folder (an update overwrites it). No `&` in any path.

```
idea + refs + brand -> refs.py measure -> BRIEF.md [GATE brief] -> assets, grids
  -> beats.sheet.json + stills [GATE beat sheet, review page] -> motion-builder (opus, xhigh) -> probe
  -> draft -> notes [review page] -> motion-reviser (opus, medium) -> final render -> mux
```

Main-session gates (brief, beat sheet, draft notes) stay here: a subagent cannot ask the user anything.
Nothing skips ahead. Never claim a render worked without checking the file exists and is non-empty.

## 0. Start

From the home page the job line is
`JOB motion <name> format=<9:16|1:1|16:9> film=<FILM> refs=<FILM>/refs.json [note=<file>] root=<library> idea=<one line>`.
The idea may be empty or one short line: the user starts from references plus a chat message, never a brief. Take the
intent from the refs and their `take` notes (and `note=`, the project's optional brief, when set); what the message says wins. Never ask for a
brief or a script. Ask at most one question, and only if two refs pull different ways (two looks, two brands).
The page opens this skill straight on `take job <id>`: read `${CLAUDE_PLUGIN_ROOT}/skills/start/references/home.md` and
`home-other.md` there (waiting, status, questions, the motion job) and nothing else from start. Run `home.py wait --job <id>`
and report with `home.py status motion --step "..."`. From chat ("new motion film", "make a motion video"): ask the idea, format and length in one
question box, then:

```bash
node "$ENGINE/tools/new.mjs" "<library>/films/<name>"
```

Engine missing (no `$ENGINE/render.mjs`) or `setup.py doctor` shows `motion engine` not ok:
`python3 "${CLAUDE_PLUGIN_ROOT}/skills/setup/scripts/setup.py" motion-engine`, then go on.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/ai_editor/profile.py" show
```

Read the taste rules too (`taste.py show`, style-edit step 0) and follow them.

## 1. References

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/refs.py" measure "$FILM"
python3 "${CLAUDE_SKILL_DIR}/scripts/refs.py" add "$FILM" <file|folder|url> --take "the whole look"
```

`measure` reads `refs.json` and writes `refs/<id>.json` (the style.json shape: `pace`, `zoom`,
`graphics.entrances` as GSAP ease names, `graphics.palette`, `grade`) and `refs/<id>.png`. `add` is for one more.
A field the script could not measure stays missing; never fill it by eye. `_measured` in each file says what ran.
Whole look only for now; a time range is measured as the whole video.

Each reference is a card: `take` is the user's own note on what they want from it, `role` says what it is for
(`brand` the business, `style` an ad or look to copy, `both`; unset: a website is brand, the rest style). A `brand`
site also gets `site_ref` (its title, description, headings, quoted lines, fonts, from a small crawl): that is what the
business does, in its own words. Before the brief run `refs.py echo "$FILM"` and say its lines back, one per card; a
wrong line is fixed in `refs.json` and re-measured. A card whose note is only the default gets one question.
Type and spacing of a style reference are not measured yet: say so, and do not name a font by eye.

Precedence, always:

1. **Brand wins** on colors, fonts, logo and text: the profile brand kit. None, or one from a site or photos:
   `python3 "${CLAUDE_PLUGIN_ROOT}/lib/ai_editor/brand.py" from-url <url> --save` or `from-images <folder> --save`
   (ask before `--save`; without it the film uses the reference's `brand_ref` and `site_ref` only).
   Photos give colors and a logo, never fonts: ask for the font.
2. **A reference decides** motion, timing and layout for the beats that cite it.
3. **The engine's own defaults** (springs) for the rest.

Never copy another creator's on-screen text, logos or footage unless the user supplies them as their own.
Grade: set `film.config.json` `"grade"` to `refs/<id>.json` of the reference whose look the user wants (ask if
two compete). `render.mjs` applies it; `--nograde` skips it.

## 2. Brief gate

Fill `FILM/BRIEF.md`: idea, script, brand (named from the profile), format, length, audio source, and for each
reference its `take` word for word, what to avoid, and for a brand site what the business does (`site_ref`). Show it back. **Gate: the user approves the brief before any code.**
Write every field you can from the refs, the idea line and the profile; do not ask for the rest and do not invent a
script or a claim: leave it out or mark it as your choice for the user to change at the gate.

## 3. Assets and grids

Put real screenshots, the logo, the brand fonts and the user's photos in `FILM/assets/` (captures: style-edit's
`capture.mjs`, or the user's files). List what you found. Never invent a screen.

- Voiceover: ElevenLabs, key `ELEVENLABS_API_KEY` in `.env`, never echoed. Transcribe it back to `audio/vo.json`.
- Music: `python3 "$ENGINE/tools/beats.py" "$FILM/audio/track.wav" > "$FILM/audio/beats.json"`.
- `film.config.json` `"grid": "beats" | "vo"`. Every cut lands on a grid timestamp, text on its spoken word.
- You cannot hear audio. Say you read the grids, never that you listened.

## 4. Beat sheet gate

One beat per 2 to 4 s (every beat on a music-led film). Write `FILM/beats.sheet.json`:

```json
{"beats": [{"id": 1, "t": 0.0, "dur": 2.4, "on_screen": "...", "moves": "...", "heard": "...",
            "refs": ["ref1@0:12"], "still": "stills/beat-01.png"}],
 "refs": [{"id": "ref1", "source": "...", "take": "the whole look", "still": "refs/ref1.png"}]}
```

"Product appears with energy" is not a beat: name what is on screen, what moves (with the ease or spring) and what
is heard. Cite a ref only for a beat that copies its motion, timing or layout.

Stills: write a first-pass `film.html` with every beat's layout at rest (final text, assets, brand; the motion can
be a stub), then draw one frame per beat, no render needed, at a time when the beat is at rest, not mid-move:

```bash
node "$ENGINE/tools/still.mjs" "$FILM" 0.8=stills/beat-01.png 3.2=stills/beat-02.png
```

One `<t>=<path>` pair per beat, paths relative to `FILM` (add `--format 9:16` to pick a format); one browser for all. (`sheets.mjs --at` is
not for this: it cuts a strip from an existing render.) Then open the page and wait in the background:

```bash
python3 "$R" beats "$FILM"
python3 "$R" "$FILM" serve
python3 "$R" "$FILM" wait
```

`wait` prints notes tagged `[beat N]` or `[whole sheet]`. Change `beats.sheet.json` (and the stills if the layout
changed), run `round`-style: rerun `beats`, wait again. **Loop until the user approves.** `film.html` is rewritten
by the builder, so the first pass is only for the stills.

## 5. First build: the motion-builder agent

Launch the `motion-builder` agent (`${CLAUDE_PLUGIN_ROOT}/agents/motion-builder.md`, opus) with the Agent tool,
**effort "xhigh" on the launch as well** (frontmatter alone may not be honored). The prompt gives `FILM` and
`ENGINE`, absolute. It reads BRIEF.md, the approved sheet, the refs and the grids, composes `film.html`, runs
probe until it passes, renders a draft, reads the contact sheets (3 fix rounds at most) and returns:

```json
{"film": "...", "probe": "pass", "draft": "...", "rounds": 2, "open_issues": []}
```

`probe` must be `pass`. Check the draft file exists and is non-empty yourself, then run probe once more:
`node "$ENGINE/probe.mjs" "$FILM"`. If it fails, send the builder's JSON back in a second launch with the probe
output; do not loosen probe. Tell the user any `open_issues`.

**Phase 4 check, after the first real run:** the builder's transcript
(`~/.claude/projects/<project>/<session>/subagents/agent-*.jsonl`) must say `claude-opus-5-5` and show xhigh. Grep
the file for `"model"`, say which model it names, and say if it is not that one.

## 6. Draft review

Look at `out/contact.png` and `out/phone.png` yourself first (`node "$ENGINE/tools/sheets.mjs" "$FILM"`). Defects by
name: text overlapping during a swap; anything sliding instead of settling; corner labels or frame borders; a
centered-on-gradient shot; blurry text scaled up; a beat with nothing new; a stutter at the loop seam. Sheets show
layout, never velocity: probe does that.

Hand the draft to the user on the review page (`${CLAUDE_PLUGIN_ROOT}/skills/style-edit/references/review.md`):

```bash
python3 "$R" "$FILM" start --video "$FILM/out/silent-9x16-draft.mp4" --stage edit
python3 "$R" "$FILM" serve
python3 "$R" "$FILM" wait
```

`serve` and `wait` in the background. Each round of notes (a time and a text) goes to the `motion-reviser` agent
(`${CLAUDE_PLUGIN_ROOT}/agents/motion-reviser.md`, opus, effort "medium" on the launch) with `FILM`, `ENGINE` and the
notes verbatim. It fixes, re-probes and re-renders the draft and returns a short JSON. Check the new draft exists,
then `python3 "$R" "$FILM" round --video <new draft> --stage edit --note "<what changed>"` and wait again.
A note that changes the beat sheet (a beat added, removed or reordered) goes back through step 4 first.

## 7. Final

On APPROVE, per format the user wants (`film.config.json` `formats`):

```bash
node "$ENGINE/render.mjs" "$FILM" --format 9:16
node "$ENGINE/tools/mux.mjs" "$FILM" --format 9:16
```

Check `FILM/out/final-9x16.mp4` exists and is non-empty (`ffprobe` its duration against `film.config.json`)
before saying it is done. Output stays in `FILM/out/` inside the library. Report the path, the length and which
formats; report nothing you did not measure. Mux normalizes to -14 LUFS. Then `home.py status motion --done` with
`--result '{"film": "<FILM>", "video": "<final path>"}'`.

## If a script stops

| message | do |
|---|---|
| `Cannot find` / no `render.mjs` in ENGINE | `setup.py motion-engine`, then the same command |
| `no Chrome Headless Shell` | `setup.py remotion`, then again |
| probe fails: undeclared jump, dead stretch, loop seam | the builder fixes it; declare only cuts meant, in `film.config.json` `cuts` |
| `no render found` (sheets.mjs) | render the draft first: `render.mjs "$FILM" --draft` |
| `no beats in ...beats.sheet.json` | write the sheet as in step 4 |
| a ref field missing | leave it; the beat falls back to the engine's springs |

## Files

- `scripts/refs.py` (add, measure, demo); `${CLAUDE_PLUGIN_ROOT}/motion-engine/` (render, probe, preview, tools).
- `${CLAUDE_PLUGIN_ROOT}/agents/motion-builder.md` (opus, xhigh), `motion-reviser.md` (opus, medium).
