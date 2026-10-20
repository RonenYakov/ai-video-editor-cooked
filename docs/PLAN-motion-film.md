# Plan: Motion Studio inside cooked. ("New motion video")

## Goal

A second option in the editor: **New motion video**. Same flow as today (send a reference, it is
measured, you approve a frame-by-frame sheet, then it renders), but the video is built from scratch
on our own engine (Motion Studio), not Remotion and not HyperFrames.

## Why our engine and not cooked's HyperFrames `motion` skill

cooked already builds GSAP clips in HyperFrames (`skills/motion`, `agents/clip-builder.md`). We still use the
Motion Studio engine because it gives true accumulation motion blur, per-shot shutter, frame rates above 60, and in
side-by-side tests it gave better results. The HyperFrames path stays for talking-head clips.

## Decisions (made)

- Engine is copied into the fork: `plugins/ai-editor/motion-engine/`. Motion Studio's own repo stays the lab.
- Films live in the library, not the plugin (a plugin update overwrites the plugin folder): `<library>\films\<name>\`,
  where `<library>` comes from `library.py` `library_dir()`. Set it once to `C:\Users\97254\Desktop\cooked video library`
  with Settings > New videos folder > Move. Every finished MP4 (talking head, motion, quick edit) lands there.
- Approval = beat sheet plus one engine-rendered still per beat, on the review page.
- First build always runs on Opus 5.5 at xhigh effort. Revisions run on Opus at medium effort. See Phase 4.
- Brand comes from the profile's existing brand kit (`profile.py` `brand`, `brand_look()`), never from a reference.
- References accepted: motion-graphic videos, talking-head videos, websites, still images.

## Flow

```
reference(s) -> teardown (measure) -> style.json (+ grade)      brand kit from profile
   -> BRIEF.md -> beat sheet + stills  [GATE: you approve, main session]
   -> film.html (motion-builder agent, Opus xhigh) -> probe   [GATE: must pass]
   -> draft render -> contact sheets    [max 3 fix rounds, motion-reviser agent]
   -> final render -> mux
```

## Phases

Each phase ends with something runnable. Do not start the next until the gate passes.
Ship Phases 1 to 4 first. Phase 1b span measuring, Phase 5 and Phase 6 come after.

### Phase 1: Measure motion-graphic references (creator-teardown)

- Run the existing teardown on one motion-graphic reference. List which `style.json` fields come back empty.
  Expected: `pace` has only `cuts_per_10s`, `median_shot_s`, `cut_kinds` (wpm needs a transcript, `visual.py:490`).
- New `grade.py`: per sampled frame, luma mean/std, black and white points, saturation, shadow/highlight hue.
  Writes `style.json["grade"]`. Numbers from code only, same rule as the other scripts.
- New `brand.py`: from a URL or image set, palette, closest fonts, logo files. Writes the profile's brand kit, not `style.json`.
- Photos as references: `grade.py` and the palette part of `look.py` run on a folder of images too, giving a still-only
  style (grade, palette, layout boxes). Motion and pace stay empty, because a photo has no motion.
- Add `grade` to both copies of `contracts.md` (CI checks they match).
- Gate: a teardown of a non-talking-head video has `pace.cuts_per_10s` present (0 is a valid value),
  non-empty `graphics.entrances` and `graphics.palette`, and a `grade` block with every field numeric.

### Phase 1b: References belong to the project

The "New motion video" screen has an **Add reference** box. A reference attaches to that one project and lives in
`films/<name>/refs/`. Nothing is saved to the Styles list unless you ask.

For each reference you give the video, then what to take from it, in your own words or by time range:

- "the whole look" -> full measure of the video (pace, grade, palette, eases, layout). Ships with Phase 3.
- "0:12-0:19" or "the counter and the logo wipe" -> only that span is measured. Comes later.

Results go to `films/<name>/refs/<id>.json` plus stills. The beat sheet then cites them: `beat 4: ref1@0:12`.
The review page shows each reference with what was taken from it.

Optional **Save as style** button turns the full measure into a reusable style in `creator-teardowns/`. Later.

Rules: motion, timing and layout are copied; the profile's brand, text and footage replace the original's. Exact
on-screen text, logos or footage from someone else's video are not copied unless the user supplies them as their own.

Precedence: brand wins on colors, fonts, logo and text. A reference decides motion, timing and layout for the beats
that cite it. Style fills the rest.

### Phase 2: Engine in the fork

- Copy `engine/` to `plugins/ai-editor/motion-engine/`. Add `npm run` equivalents under the plugin's own package.json.
- `render.mjs`, `probe.mjs`, `preview.mjs`, `sheets.mjs`: engine root and film folder become arguments, served from two
  roots. Films import the engine through the server path, not `../../engine/`.
- `lib/motion.js`: add `ease(name, t)` for measured GSAP eases (`power2.out` over 0.23 s). No spring fitter.
  Springs stay for anything we design ourselves.
- `lib/style.js`: reads `style.json` into engine inputs (`graphics.entrances`, `pace.cuts_per_10s`, `zoom`,
  `graphics.palette`, `grade`).
- Grade as a final pass in `render.mjs` (ffmpeg `colorlevels`/`eq`), driven by `style.json["grade"]`.
- Browser: point Playwright at the chrome-headless-shell cooked already downloads (`setup.py:786`). Add a setup row
  for the engine's npm install.
- Gate: one film renders from a measured style, `probe.mjs` passes, and each `ease()` matches GSAP within 1% of travel
  at every frame (unit test in `tests/`).

### Phase 3: Skill `motion-film`

- `plugins/ai-editor/skills/motion-film/SKILL.md`, under 200 lines, following Motion Studio's workflow: brief, assets, grids, beat sheet, compose, probe, draft, final.
- Stills for the approval gate: `sheets.mjs --at <beat time>`, one still per beat, plus the beat table.
- Review page: extend the existing stills-approval mode (`review.py --stills`) into a beat-sheet mode. Approve, or add a note per beat.
- Gate: a full run from reference to approved sheet to final MP4 on one test brief.

### Phase 4: Home page button and model tiers

- Home page: "New motion video" beside "Make my video" (`lib/ai_editor/home.html`).
- Two agent files, model fixed in frontmatter (the only place a model is guaranteed):
  - `agents/motion-builder.md`: `model: opus`, `effort: xhigh`. Composes `film.html` after the beat sheet is approved, runs probe.
  - `agents/motion-reviser.md`: `model: opus`, `effort: medium`. Note-driven fixes and re-renders.
- The skill always launches `motion-builder` for the first build and passes `effort: xhigh` on the launch as well.
  The main session keeps the brief and beat-sheet gates, because a subagent cannot ask the user anything.
- `opus` resolves to the newest Opus (today `claude-opus-5-5`). `motion.py`-style doctor check prints the resolved model at startup.
- Gate: after a test run, the builder's transcript (`~/.claude/projects/.../subagents/*.jsonl`) shows `claude-opus-5-5`
  and xhigh effort, and a re-render's shows the reviser. Checked in the file, not assumed.

### Phase 5 (later): Two polish skills

- `color-grade` skill: applies, previews and tunes `style.json["grade"]`. Works for both the motion engine and the talking-head Remotion path.
- `branding` skill: applies the profile's brand kit. Replaces the neutral card chrome rule only when the user's brand is set.
- Gate: same footage, grade on versus off, a side-by-side still sheet.

### Phase 6 (later): Quick edit (third button)

- Home page has three buttons: **Talking head** (cut + style-edit, as today), **New motion video**, **Quick edit** (any video).
- Quick edit has no fixed pipeline. You drop a video and write what you want. Claude routes the free text to a skill, or improvises with plain tools.
- Starts with `color-grade` and `branding` only. Any other skill (background via `matte.py`, reframe) is written after the same request comes up twice.
- Gate: "warmer, and a studio background" on a non-talking-head clip renders.

## Rules kept from both repos

- Motion Studio: `window.seek(t)` pure function, no `Math.random`, probe before eyes, no claims without checking the file.
- cooked.: numbers in `style.json` come from code, real assets only, no AI-slop copy, no `&` in paths.

## Risks

| Risk | Handling |
|---|---|
| `effort` in agent frontmatter not honored | Also pass `effort: xhigh` on the launch; Phase 4 gate reads the transcript |
| `look.py` assumes faces and captions | Phase 1 lists empties, new scripts fill them |
| Engine copy drifts from Motion Studio | Motion Studio is the lab; changes go there first, then copied with a version note |
| Windows paths and Playwright | Reuse cooked's Chrome, test on this machine first |

## Not in scope

Cloud rendering for the motion engine, 4K, porting existing Remotion templates.

## First action

Run one teardown on a motion-graphic reference and record which fields are empty.
