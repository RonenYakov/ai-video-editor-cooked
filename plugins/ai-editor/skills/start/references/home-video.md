# Video jobs (talking head, clips) and the lang= line

The shared rules (waiting, status, questions, keys) are in `home.md`.

### `lang=<code>` on a video or motion job

The video's language, from the page or the profile's `language`. `lang=he` (Hebrew) means this Claude was opened
with two extra skills: use `hebrew-content-writer` for every line of text you write for the video (caption wording,
cards, titles, calls to action, a motion film's text), and `israeli-social-content` for post copy, titles and hashtags
(post, clips). Hebrew copy follows the same rule as English: no dashes as punctuation. A job with no `lang=` is
English; do not load either skill. Right-to-left text must be checked on a still before the render.

### `JOB video <path> as=<mine|@handle|defaults> aspect=<9:16|16:9> edit=<dir> root=<dir>`
### `JOB video takes=<dir>/takes.txt as=... aspect=... edit=<dir> root=<dir>`
### either one with ` script=<edit>/script.md`, ` skill=<skill>`, ` chain=<steps>`, ` sample=1` and/or ` assets=<edit>/assets.json` before `root=`

The user picked clips and a style and pressed "Make my video" (or "Start the cut" on a first run).
`edit=` is the edit folder the page already made and listed in the library: use it, never make
another. `takes=` lists several clips, one path per line, in the order the user set: they are one
video, so join them first (`cut/references/takes.md`, `join.py <edit>/joined.mp4 <the paths in order>`,
no question: the page asked it). "Separate videos" arrives as one JOB per clip; take them one by one.

`as=` is this video's style only: never `profile.py set creators` for it (only the page's Make default changes the
saved style). The page already wrote `<edit>/style.json` from it (when the job was made, and again when `wait`
handed it to you): skip start step 3's blend, never run `profile.py style` on this edit without `--as <the job's
value>`. `check.py plan` fails when the edit's style is not the one `as=` names. When
`creator-teardowns/<h>/style.json` is not there yet, that creator is still being copied: cut now
(the cut needs no style) and start the styled pass once the teardown job is done.
`aspect`: `profile.py set aspect=<a>`.
The clip's transcription started when the user added it on New video (before Make); `transcribe.py` reuses it.
`script=`: the user added their script on the page. The page wrote it to `<edit>/script.md` (copy it
there if the path is elsewhere). Pass `--script <edit>/script.md` to `transcribe.py`; the cut then runs
`script_match.py` before deciding spans (cut skill step 2).
`skill=`: a skill style (its `style.json` has `"skill"`), see Skill style below.
`chain=`: the style page's "What runs" when it is not the default. With no `chain=`, run logo-pack as usual (after
the cut's approve, before the edit, when the video names two or more products). `chain=none`: never run
logo-pack on this video. `chain=logo-pack,motion` or `chain=motion` (a skill style only): see Skill style below.
`before:<skill>` and `after:<skill>` in `chain=` are skills the user chained onto the style's What runs, in order.
Each `before:` skill runs after the cut's approve, before the edit, on `<edit>/cut.mp4`; each `after:` skill runs
after the final approve, on the finished video, its files into `<edit>/`. Invoke each with the Skill tool (the
editor shows every skill a video ran), say each on the page (`review.py status "Running /<skill>"`), and treat a
skill this session doesn't have as the Skill style section does.
`assets=`: images and links the user added on the page ("Add images or links"; more can come from the editor's
"Anything to add?", and review.py `wait` then prints an `assets:` line). Images are in `<edit>/assets/`. Hand the
file to visual-prep and style-edit: each item goes in first, as a card on its `say` words (else the line it is
about), before anything is searched for.

The page already opened the editor on the raw clip when the user pressed Make my video (round 0, "Your
clip, before the cut", `review.json` is there) and lists every step of the cut beside it, ticked as the
scripts report them (review.py `CUT_STEPS`). Serve it and report its URL before transcribing; for `takes=`,
swap in the joined clip after the join:

```bash
R="${CLAUDE_PLUGIN_ROOT}/lib/ai_editor/review.py"
python3 "$R" <edit> start --raw --video <edit>/joined.mp4 --stage cut   # takes= only, after join.py; no review.json: the clip
python3 "$R" <edit> serve --no-open                                     # background; prints the URL
python3 "$H" status video --result '{"review_url": "<that URL>"}'
```

`serve` opens no browser tab while the home window is showing this job: the home window goes to the
review page in its own tab. Otherwise (no home window, or Claude Code alone) it opens a tab. Round 0 has no Approve; notes left on it wait for the cut. Then the start skill from step 2 on, with
this file (or joined.mp4) as the video. The steps
`Joining your clips` (takes only), `Writing down every word`, `Finding retakes and pauses`, `Cutting out
the mistakes`, `Rendering the cut`, `Checking the cut` reach the home page and the editor by themselves
(join.py, transcribe.py, build_timeline.py, render.py, verify_cut.py): never report them yourself. After the cut's approve the style-edit scripts
put their own `--step` on the page's Making the edit card (style-edit `references/review.md`). The cut's
own `start` (cut skill step 6) then opens round 1 on the same page, with the round 0 notes moved onto
the cut: run `wait` and carry on there. `status video --done` once round 1 is up. When that `wait` prints
`EDITS <n> transcript edits applied to spans.json`, the user restored or cut words in the transcript beside the player:
run `build_timeline.py`, `render.py`, `verify_cut.py`, then `review.py <edit> round --video <edit>/cut.mp4`
(`../../style-edit/references/review.md`, Transcript edits).

#### Sample video (`sample=1`)

The user pressed "Try it with a sample video" to see the whole flow before using their own footage. The page
downloaded the repo's public sample take and put its decisions in `edit=`: `words.raw.json`, `spans.json`,
`style.json` (the Card edit sample, cards not behind the head) and `visuals.json`. Do these steps instead of
the start skill's steps 2-4, fast and exact:
ask nothing, never change the profile or the taste, and skip transcribe, `retakes.py propose`, the judge,
verify, visual-prep, logo-pack, the motion skill, music, the render and loudness questions. Notes the user
sends are handled as usual. `C="${CLAUDE_PLUGIN_ROOT}/skills/cut/scripts"`, `SE="${CLAUDE_PLUGIN_ROOT}/skills/style-edit/scripts"`.

1. Serve the review page and report its URL, as above.
2. The cut, then `status video --done` and review.py `wait` in the background:

```bash
python3 "$C/build_timeline.py" <path> <edit> && python3 "$C/render.py" <path> <edit> && \
cp <edit>/words.json <edit>/cut.transcript.json && \
python3 "$R" <edit> start --video <edit>/cut.mp4 --stage cut --transcript <edit>/words.json
```

3. On the cut's `APPROVE`: plan and check the stills yourself, then render (no stills round on the page):

```bash
python3 "$C/retakes.py" captions <edit> && node "$SE/capture.mjs" <edit> && \
python3 "${CLAUDE_PLUGIN_ROOT}/lib/ai_editor/run.py" "$SE/face.py" <edit> && \
python3 "$SE/plan.py" <edit>/style.json <edit>/captions.json --aspect 9:16 && python3 "$SE/edit.py" stills <edit>
```

4. Then `python3 "$SE/edit.py" render <edit>` on the laptop, then
   `python3 "$R" <edit> round --stage edit --video <edit>/render.mp4` and `wait`. Say in one line that the
   sample is done and they can drop their own clip on Home next.

#### Skill style

The style points at a skill, so that skill makes the edit instead of style-edit. Cut as usual (start
steps 2-4: the profile, blend and cut still run, so the fallback has the style's numbers). After the
cut's approve run `/<skill>` on `<edit>/cut.mp4`: it makes its own captions, visuals and render. Then
hand its render back as the edit round, as style-edit step 8 does:
`python3 "$R" <edit> round --stage edit --video <its render>`, then `wait` on the page as usual.

`chain=` with `motion` (the user switched Animations on for this skill style): before running `/<skill>`, run the
visual-prep agent on the cut (style-edit steps 1-3), then the motion skill (`motion.py pick`, one clip-builder per
clip, `motion.py check`). Hand `/<skill>` the checked clips: each `motion/<id>/` render with its `beat.json`
times, to lay over the cut on those words. With `logo-pack` in the chain, run logo-pack first and tell `/<skill>`
the logos are in `<edit>/images/` (`logos.json`). Say each step on the page (`review.py status`).

When `<skill>` is not in this session's skill list, never switch silently:
`python3 "$R" <edit> status "This style needs the <skill> skill, which this Claude session doesn't have"`,
then ask: **Continue with the generic edit, using the style's numbers (Recommended)** / **Stop here**.
Continue: style-edit with `<edit>/style.json` as usual. Stop: `status video --failed "This style needs
the <skill> skill. Open Claude Code where that skill is loaded and make the video again."`.

Notes on a skill style's video become rules in that skill's own SKILL.md (`## Learned rules`), never in a
settings file: the final approve's Teach panel does it (`review.py learn --done`), as do `learn --scope this-style` and a
`style-change` job on a skill style.

