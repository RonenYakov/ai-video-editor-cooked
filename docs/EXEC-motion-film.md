# Execution: motion-film (Phases 1 to 4 of PLAN-motion-film.md)

Branch `feat/motion-film`. Builders: Sonnet subagents, one task each, never two on one file.
Reviewer: Opus 5.5 (main session) reads every diff, checks the joins between tasks, runs the checks.
No commits until the user asks.

## Wave 1 (parallel, no dependencies)

| # | Task | Owns | Done when |
|---|---|---|---|
| T1 | Copy engine to `plugins/ai-editor/motion-engine/`. Engine root and film folder become arguments; `serve.mjs` serves `/engine/` and `/film/` from two roots; template imports `/engine/lib/motion.js`; `new.mjs <dir>` creates a film anywhere; Playwright uses cooked's chrome-headless-shell (`playwright-core`, no browser download) | `motion-engine/**` | `node lib/motion.js` passes; template film in a temp folder renders a 1 s draft and probes |
| T3 | `grade.py` (video or image folder -> grade block, plus palette for images) with `demo`; `grade` added to both `contracts.md` | `creator-teardown/scripts/grade.py`, both `contracts.md` | `grade.py demo` passes; `check_plugins.py` passes |
| T4 | `brand.py` (URL or image folder -> colors, font, logo) writing the profile brand kit, with `demo` | `lib/ai_editor/brand.py` | `brand.py demo` passes, profile shape matches `profile.py` |
| T5 | `agents/motion-builder.md` (opus, xhigh) and `agents/motion-reviser.md` (opus, medium) | those two files | `check_plugins.py` passes |
| T9 | Beat-sheet mode on the review page: beats table + one still per beat, approve or note per beat, extending `--stills` | `review.py`, `review.html` | `review.py demo` passes incl. a beat-sheet case |
| T10 | "New motion video" button on the home page, sends `JOB motion <name>` | `home.html`, `home.py` | `home.py demo` passes incl. the new job |

## Wave 2 (after wave 1 review)

| # | Task | Needs | Done when |
|---|---|---|---|
| T2 | `ease(name, t)` in `lib/motion.js` for GSAP eases | T1 | self-check matches GSAP within 1% of travel on every frame |
| T7 | `lib/style.js` (style.json -> engine inputs) and the grade pass in `render.mjs` | T1, T3 | render with a grade differs from render without it by the expected luma shift |
| T8 | `setup.py` row: engine npm install + doctor line | T1 | `setup.py demo` passes |
| T11 | `refs.py add <film> <video|images>` (whole-look only) -> `refs/<id>.json` + stills | T1, T3 | `refs.py demo` passes |

## Wave 3

| # | Task | Done when |
|---|---|---|
| T12 | `skills/motion-film/SKILL.md` (< 200 lines): brief, refs, beat sheet gate, motion-builder, probe, draft, reviser, final into `<library>/films/<name>/` | `check_plugins.py` passes |
| T13 | Reviewer: add every new demo to `tests/demos.sh`, a row to `AGENTS.md` | `demos.sh` all ok |

## Tests (reviewer writes, then loops until green)

`tests/test_motion_film.py`:
1. Template film in a temp library renders a 1 s draft; the MP4 exists and is non-empty.
2. `probe.mjs` passes on it and fails on a film with an undeclared jump.
3. A style with `grade` changes mean luma by the expected sign; without it, frames match.
4. `sheets.mjs --at` writes one still per beat.
5. `ease()` vs GSAP reference values.
6. `refs.py add` on a generated clip and an image folder fills `refs/<id>.json`.
7. Agent files: builder is `opus` + `xhigh`, reviser is `opus` + `medium`.

Plus `tests/check_plugins.py` and `tests/demos.sh`. Run all, fix, rerun, until every one passes.
Not covered by tests: the real model used at runtime (checked in the first real run's transcript).
