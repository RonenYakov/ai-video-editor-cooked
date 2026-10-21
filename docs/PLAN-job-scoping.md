# Job Scoping Plan

## Goal

Each job the home page launches (Talking head, New motion video, Quick edit) starts a Claude that can see only
the plugins, skills, agents and MCPs that job uses. Success: in a launched job window `/context` shows no skill,
MCP tool or plugin from outside the job's list, and the three jobs still finish end to end.

## Constraints

- Windows and Mac. Jobs open through `lib/ai_editor/launcher.py` (`plan()` builds `claude --plugin-dir ... --settings {...} <prompt>`).
- One plugin today (`ai-editor`, plus its dependency `creator-teardown`). Skills call `${CLAUDE_PLUGIN_ROOT}/lib/...` everywhere, so moving files is expensive.
- Window needs its hooks (`askhook.py`, `toolhook.py`), so `--bare` is out.
- Claude Code 2.1.306. Flag behaviour below is read from `claude --help`; precedence is NOT yet tested (Phase 0).
- The user's personal setup (17 plugins, ~190 skills, ~25 MCP servers) is the worst case; the fix lives in the launcher so every install benefits.

## Out of Scope

- Rewriting any skill's content, or shrinking the large reference files (style-edit 26k words) in this pass.
- Splitting `ai-editor` into several plugins (decided in Phase 3, only if Phase 1 numbers say it pays).
- Quick edit's routing logic itself (docs/PLAN-motion-film.md, Phase 6). This plan only gives it a scope.
- Product video and Clips as buttons. They get a profile row below, no new UI.

## Architecture

### What exists (mapped)

| Layer | Items |
|---|---|
| Plugin `ai-editor` skills (17) | start, setup, taste, cut, style-edit, clips, overlays, logo-pack, motion, motion-film, motion-design, product-video, post, update, improve, skill-improver, skill-maker |
| Plugin `creator-teardown` | skill creator-teardown, agent video-analyst |
| Agents (11) | cut-judge, cut-reader, visual-prep, template-filler, stills-critic, clip-editor, clip-builder, motion-builder, motion-reviser, render-watcher, storyboard-critic |
| Hooks | SessionStart doctor, PreToolUse AskUserQuestion + `*`, Notification, Stop (all needed by the window) |
| Engines (not tokens, code) | Remotion (`plugins/ai-editor/remotion`), Motion Studio (`motion-engine`), HyperFrames CLI (per-beat clips), ffmpeg, Modal/Lambda |
| MCPs used by cooked skills | **None.** No SKILL.md, agent or lib file references an MCP tool. ElevenLabs, Gemini, Zernio, Modal are called by scripts with keys. |
| Leaks from the user level | ~170 non-cooked skills (design, hyperframes-*, remotion-*, figma, legal, marketing, adobe, superpowers...), ~25 MCP servers (Vercel 200+ tools, Higgsfield, Notion, ElevenLabs, Canva, Gamma, Gmail...), plugins like supabase, telegram, figma, github |

### Job scopes (who sees what)

Core is on in every video job: `start` (as router only), `taste`, `setup` (used only when doctor prints FIX), `creator-teardown`.

| | Talking head | New motion video | Quick edit (later) |
|---|---|---|---|
| ai-editor skills | core + cut, style-edit, overlays, logo-pack, motion, clips, post | core + motion-film | core + cut, overlays, logo-pack, motion, post |
| Agents | cut-judge, cut-reader, visual-prep, template-filler, stills-critic, clip-editor, clip-builder, render-watcher | motion-builder, motion-reviser, render-watcher | clip-builder, render-watcher |
| Global skills | hyperframes, hyperframes-core, hyperframes-animation, hyperframes-keyframes (only for `motion` beats) | none | same four, only if `motion` is chosen |
| MCPs | none | none | none |
| Engine | Remotion, ffmpeg, HyperFrames CLI | Motion Studio, ffmpeg | ffmpeg, plus whichever skill it routes to |
| Off | product-video, motion-film, motion-design, update, improve, skill-improver, skill-maker | everything else in ai-editor | product-video, motion-film, maintenance skills |

Other profiles (same mechanism, no new button): **product** (core + product-video, storyboard-critic, Remotion),
**teardown/setup/update** (core only), **maintenance** (improve, skill-improver, skill-maker; for repo work, never inside a video job).

### Language add-on: Hebrew

Two skills from the user's skill list (`anthropic-skills:hebrew-content-writer`, ~2.6k words, and
`anthropic-skills:israeli-social-content`, ~3.6k words) are added **only when the job's language is Hebrew**. In every
other job they are denied like the rest of the out-of-scope skills.

| Skill | Used for | In which jobs (Hebrew only) |
|---|---|---|
| hebrew-content-writer | On-screen text: captions wording, cards, titles, CTAs, motion-film text, any copy Claude writes | Talking head, Motion video, Quick edit, Product |
| israeli-social-content | Post copy, titles, hashtags for the platform | Anywhere `post` or `clips` runs (Talking head, Quick edit) |

How the language reaches the launcher: the job line gets `lang=he` (home page field "Video language", default
from the profile, `auto` = take it from the first transcription). The launcher reads it from the job and drops the
two deny rules. A profile `language` answer is saved once, like the other intake answers, so repeat users never
see the question. Chat entry (no home page): `start` asks it in the same question box as the other intake answers.

Edge: `auto` cannot decide at launch because transcription happens after. For `auto` jobs the launch leaves the two
skills denied; if transcription reports Hebrew, the job reports `needs-lang` and the home page reopens the window
with `lang=he`. Simplest default: ask on the page, never auto.

Notes on the table:
- `motion-design` (vendored Lottie text) is read by style-edit as a reference file, not invoked as a skill, so it needs no listing in any job.
- Remotion plugin skills (`remotion:*`) are for authoring Remotion code. cooked only runs `npx remotion`, so they stay off.
- Subagents with a `tools:` line are already narrow. `template-filler` shows "All tools" in the agent list while its file says `Read, Write`; check that frontmatter parses (Phase 0).

### Mechanism: a job profile table in the launcher

`launcher.plan(job_type)` gets a `PROFILES` dict (job type to scope above) and adds three things to the existing
command, next to the allow rules it already passes:

1. `--strict-mcp-config` with no `--mcp-config`: zero MCP servers, so zero deferred tool names. One flag, biggest cut.
2. In the `--settings` JSON: `enabledPlugins` set to `false` for every installed plugin not in the profile, and `permissions.deny` for `Skill(<name>)` of every out-of-scope skill (user-level ones too).
3. Prompt goes straight to the job's skill (`/ai-editor:motion-film take job <id>`) instead of `/ai-editor:start take job <id>`, so `start` and its 5k words of references are not read for a motion job.

The profile is data (a JSON file in `lib/ai_editor/`), tested by the existing launcher self-test the way `allow_rules` is.

### Mechanism: shrink what a job reads

- Split `skills/start/references/home.md` into `home-core.md` (serve, wait, status, questions, keys) plus `jobs/video.md`, `jobs/motion.md`, `jobs/teardown.md`, `jobs/skill.md`. A job reads core plus its own file.
- `start` SKILL.md keeps intake and routing for the talking-head and chat entry only; the motion job never enters it.

## Phases

**Phase 0, measure and verify (half a day).** Retires the risk that the flags do not behave as read.
- Launch a job window as today, run `/context`, record tokens for skills, MCP tools, plugins (the baseline).
- Spike by hand: `claude --strict-mcp-config --settings '{"enabledPlugins":{"x@y":false},"permissions":{"deny":["Skill(name)"]}}'`. Confirm (a) MCP tools vanish, (b) a disabled plugin's skills vanish from the listing, (c) a denied skill is hidden from the listing, not just blocked on call, (d) the window's hooks still fire.
- Ships: a number and a yes/no per flag. If (b) or (c) fail, fall back to Phase 3 for that layer.

**Phase 1, launch profiles (1 day).** Ships: Talking head and New motion video windows scoped.
- `PROFILES` JSON, `plan(job_type)`, wire `home.py claude_for` to pass the job type, self-test cases.
- Direct-to-skill prompts for `JOB motion` and `JOB video`.
- Add `language` to the profile and `lang=` to the job line; the two Hebrew skills drop out of the deny list when `lang=he`.
- Done when `/context` in each window matches its column above (plus the two Hebrew skills on a Hebrew job only) and one real talking-head job and one motion job finish.

**Phase 2, slim the reads (half a day).** Ships: smaller per-job reading.
- Split home.md as above; update the references in `start`, `motion-film`, `cut`.
- Done when a motion job never opens a talking-head reference (check with the tool log).

**Phase 3, decide on plugin split (only if needed).** If Phase 0 shows plugin disabling does not hide skills, or Phase 1 still leaves a big listing, split into `cooked-core`, `cooked-talking-head`, `cooked-motion`, with `lib/` kept in core and `${CLAUDE_PLUGIN_ROOT}` paths repointed. Plugin boundaries are the only unit Claude Code loads wholesale, so this is the fallback, not the plan.

**Phase 1c, reference roles (1 day, Motion first).** Ships: a motion film that knows the business and copies an ad's type.
- Home page: each reference is a card with a role (Brand source / Style source) and a required "what do you want from this" note; the job line carries `refs.json` with both. Same card for Talking head and Quick edit.
- Echo line before the beat sheet; the review page shows each card's note beside the measured result.
- Site read: shared crawl plus summary in `refs/<id>.json`; BRIEF.md template gets a "What the business does" block filled from it.
- Type and spacing measure for video refs (guess flagged). Gate: on one real ad, font class, title height and margins land within a visible match on the stills sheet.

**Phase 4, Quick edit.** Add its profile row when the button is built; its router skill gets only the scope in the table.

## Key Decisions

1. **Scope at launch, not in the skills.** Chosen: profile table in `launcher.py`. Why: one place, testable, no content rewrites, works for every install. Alternatives: edit each skill's description (still listed everywhere), or split plugins now (large refactor for a gain not yet measured).
2. **No MCPs in any job.** Chosen: `--strict-mcp-config`. Why: grep shows cooked uses none, and the user-level MCPs are the largest token sink by tool-name count. Alternative: allowlist per job; add a row only when a skill actually needs one (for example ElevenLabs music for motion films later).
3. **Motion bypasses `start`.** Chosen: direct skill prompt. Why: `start` is the talking-head intake and carries ~6k words a motion job never uses. Alternative: keep one front door and gate inside it (still read in full).

## Risks

- **Flags do not hide skills from the listing.** Mitigation: Phase 0 tests this first; Phase 3 is the fallback.
- **Over-scoping breaks a hidden cross-call** (for example style-edit invoking `overlays` or `logo-pack`, or `motion` needing hyperframes). Mitigation: scopes above come from SKILL.md mentions; end-to-end run per job is the Phase 1 exit test, and `setup` stays in every profile so a missing tool can still be fixed.
- **User's own plugins are sometimes wanted** (their own taste skill, a design plugin). Mitigation: profile has an `extra_allow` list the user can set in Settings; default is closed.
- **Hebrew text may still render wrong** (right-to-left order, font, caption wrapping in Remotion and the motion engine). The skills fix the wording, not the rendering. Mitigation: one Hebrew test video per job type in Phase 1; fix the renderer separately if it fails.
- **Hebrew copy and the no-em-dash rule:** both skills must follow the global copywriting rule (no dashes as punctuation); add one line to the job prompt on Hebrew jobs.
- **Drift:** new skills added to the repo are unscoped by default. Mitigation: a launcher self-test fails when a skill in `plugins/` is in no profile.
- **Accepting:** exact token savings are unknown until Phase 0; the plan is justified by the MCP and skill-listing counts, not a measured figure.

## References are inputs, not jobs (corrected)

A link or file given inside a job is a **reference with a role**, not a request to run another skill. Two roles:

| Role | You give | The job learns | Wins on |
|---|---|---|---|
| **Brand source** | your website | what the business is and does, logo, colours, font, tone, real product screens | colours, fonts, logo, words |
| **Style source** | an ad, any video, or still images | motion, timing, easing, layout and spacing, grade, palette, the look of the type | motion, timing, layout |

Rule: brand source wins on what appears, style source wins on how it moves and sits. Nothing from a style source's
own text, logo or footage is copied.

What the code does today, against that goal:

| Need | Today | Gap |
|---|---|---|
| Logo, colours, font from a site | `brand.from_url` (via `refs.py` for motion films) | Fine |
| **Understand the business** (what it does, who for, in its words) | Only in `product-video`: `crawl.mjs` reads the home page plus up to 20 pages into `site.json` | `refs.py` never crawls, so a motion film gets colours and a logo but not the meaning |
| Motion, pace, easing, grade, palette from an ad | `refs.py` via creator-teardown scripts | Works for whole-look; time ranges later |
| **Font and spacing of an ad** | Caption font guessing exists for talking-head captions (`look.py`); layout boxes exist for talking heads | Not measured for a motion ad's titles, so "copy the font and spacing" is not covered yet |

So the Motion job needs two additions, neither of which is the whole product-video skill:
1. **Site read**: expose `crawl.mjs` as a shared tool (move to `lib/ai_editor/site.py` or call it from `refs.py`), write a short `brand_ref.summary` (what they do, audience, tone, 3 to 5 offers, verbatim phrases) into `refs/<id>.json` for the brief. Crawl only, no recordings, no product-video skill loaded.
2. **Type and spacing measure** for video references: OCR the title frames (reuse `look.py` OCR), measure text height as a share of the frame, margins and line spacing, and name the closest font. Marked "a guess" when unsure, as `look.py` already does.

### Reference cards: every item carries your note

Each file, link or video you add becomes a card with a free-text note: **what do you want from this one**. The note
is the instruction; the role and measuring follow from it.

```
refs.json entry
  id        ref1
  source    https://myshop.co.il | ad.mp4 | folder of images
  role      brand | style | both          (suggested from the source, one click to change)
  want      "the logo wipe at 0:12 and the bold Hebrew title font, not the music"   (your words, required)
  range     optional "0:12-0:19"
  save_as   film only (default) | save to my brand kit | save as a style
```

How the note is used, so it changes the result and is not decoration:
- **Measuring is steered by it.** `want` is passed to the measure step the way `notes=` already is for teardowns ("look closer at what they named"): if it says font, the type measure runs on the title frames; if it says pace, the cuts run; what it excludes is skipped.
- **The brief quotes it.** BRIEF.md lists every reference with its `want` word for word, and the beat sheet cites it (`beat 4: ref1@0:12, "logo wipe"`). The review page shows the card with your note next to what was found, so you can see whether it understood.
- **It gets one echo check.** Before the beat sheet, Claude says back one line per card ("From the ad I take: the logo wipe and the title font. From your site: what you sell and the logo."). A wrong echo is fixed on the page, before any build cost is spent.
- **A card with no note is asked once**, in the question box, not guessed.

The same card shape is used by all three jobs. Talking head: a creator link with "copy the pace and captions, not the zooms"
(replaces the current `take=` ticks). Quick edit: the dropped video plus the note is the request. Motion: as above.

Scope consequence: notes are data in `refs.json`, so they add no skill or tool listing to any window.

Scope consequence of roles: the Motion window never needs `product-video`. It needs `crawl.mjs` and the reference measuring
scripts, which are code, not skills, so they cost no listing tokens. The link router in `start` (`links.py route`)
is not run for motion jobs: the home page already tags each reference with its role.

`product-video` itself stays a separate profile with no button, for the case "make a launch video from this site
with real click-throughs". Revisit only if you want a fourth button.
