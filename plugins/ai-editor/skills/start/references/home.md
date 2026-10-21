# The home page

The editor's window in the browser. A first run gets setup checks, optional keys, pick a creator, watch
their style get copied, see the style and the skill it became, drop a video. After that it opens on
Home (welcome back), New video (pick clips, then pick a style), Your videos, My style and Settings.
The page only queues jobs. Claude does every job with the usual skills and reports back, so the page
never decides anything itself.

Ask the user only through AskUserQuestion: the window shows it as a card on the open page. A question typed in your
reply never reaches the page; the Stop hook (toolhook.py) can only put "Claude needs you in the Terminal" on it.

The `nextwork-editor` command (`setup.py install-launcher`) starts Claude Code in the library with the
prompt "/ai-editor:start open the home page". When the page is already served it reopens it, and when no
Claude is listening it also opens a new Terminal window with a listening Claude (`--window-only` skips
that). Inside Claude Code, `/ai-editor:start` and "open the home page" do the same.

**Connect Claude.** When nobody listens, the page shows one button, Connect Claude. It opens a new
Terminal window in the library running Claude Code with the prompt `/ai-editor:start listen for jobs` and
only the editor's own commands allowed (`launcher.connect`, one at a time: a second press within a minute
opens nothing). On that prompt run `python3 "$H" serve --no-open` and `python3 "$H" wait` (both in the
background) and carry on as below. Do not say the page is open: it already is.

`H="${CLAUDE_PLUGIN_ROOT}/lib/ai_editor/home.py"`. `python3` on Mac and Linux, `py` on Windows.

## Open it

Run both in the background (two Bash calls with `run_in_background`). The page always works in the
library (`library.py path`, `~/Movies/AI Editor` on a Mac), wherever Claude Code started, and every job
line names it as `root=`:

```bash
python3 "$H" serve          # same address every time (port 47821, one token per install); reuses a running server
python3 "$H" wait           # exits with the next job as one line
```

Say in one line: "The home page is open in your browser. Pick a creator there, or drop a video."
Then wait for `wait` to finish. Each time it prints a job, start a new `wait` in the background
straight away (so Cancel and the next job reach you), then do the job. `ALREADY` means a `wait` is
running: leave it.

### One page, several Claude sessions

Every job remembers the session that took it (`CLAUDE_CODE_SESSION_ID`). `status` from another session
never writes to it, `status` never takes a queued job (only `wait` does), and each session makes one
video at a time. A taken job with no report for 15 minutes belonged to a session that stopped: the next
`status` or `wait --job` from another session adopts it and prints `adopted <id>`. Every video gets a Claude of its
own: when the user presses Make my video, each new video job (one per clip for "Separate videos") opens a new
Terminal window running Claude Code in the library with the prompt `/ai-editor:start take job <id>`, unless an idle
listening Claude can take it right now (then that one does, and the rest still get their own). The same goes for a chat box: a
`style-change` (a style page), `skill-change` or `skill-new` (Make a new skill) opens a Claude for that job unless
an idle listening Claude takes it. A listening Claude is
idle only with no active job: none it holds (a creator, a skill, a video's cut) and no video whose edit it is still on
(that editor's `wait` listening, or a review command there in the last 15 minutes). Setup and the sample stay with
the listening Claude; a creator's analysis is queued for it like any job. Where no terminal can
open (Linux without x-terminal-emulator), the editor shows that command to run instead. On that prompt run
`python3 "$H" serve --no-open` and `python3 "$H" wait --job <id>` (both in the background): it prints that
job's line (or `GONE` when it is done or another session has it), then do the job as below. Do not start a
plain `wait` afterwards unless the user asks for more.

## Questions

Ask with AskUserQuestion as usual. When the home page or a review page is open and showing, a hook
(`lib/ai_editor/askhook.py`) puts the question on that page. A question about a video goes to that video's editor
only: the hook takes the video your latest command named (its edit folder), so run a command on that edit (any
`review.py <edit> ...` or script on it) before asking about it. On the page: the options, an Other box with a paperclip (an image
can also be pasted or dropped on the card), and "Answer in Claude Code instead". Images are saved on this
computer (the review page: `<edit>/review/`; the home page: `<edit>/asks/`, or `$AI_EDITOR_HOME/asks` with no
edit folder yet) and the answer ends with `Attached images: /abs/a.png (Read each one to see it)`: Read every
listed image before acting on the answer. The answer comes back as the tool's result, the same as a terminal answer. No page
showing, "Answer in Claude Code instead", or every page that had it closed: the terminal box shows (an open page
waits for the answer however long it takes). Never ask
a question in plain chat text when AskUserQuestion fits: only the tool reaches the page. A question only
reaches pages this session works on (the home page while it holds a job there or listens, the review page
of an edit it ran `review.py` on), with the job's name on the card. Another session's questions stay in its
own terminal. A Claude Code without `CLAUDE_CODE_SESSION_ID` records no session, and then every question
reaches the page, as before. Permission
prompts (Allow or Deny for a command) stay in the terminal; a hook cannot answer them.

## Keys

The page saves keys itself through `keys.py` (prefix check, one free test request, then the key
file, readable by the user only). A key never reaches the chat, `state.json` or a job line. Never
ask for a key in the chat, and never read the key file. "Skip, add later" runs `setup.py later`.

## The jobs

Progress is automatic: once your `wait` has taken a job (inside Claude Code only `wait` takes a queued
one), the long scripts (creator-teardown's, the cut's transcribe, join, build and render,
setup's install-all) post their own steps with a count ("video 3 of 7") onto the job their edit folder
or handle names, and the page shows a live strip with a clock, so it never looks stopped. You still
report the steps you own (the result, `--done`, `--failed`, steps no script covers) with `status`. The
same words as the newest step update that row, never a second one. A new `--step` closes the step before it; `--done` or
`--failed "<plain sentence>"` ends the job:

```bash
python3 "$H" status <teardown|skill|video|setup|update> --step "..." [--detail "video 3 of 7"] [--progress 0.4]
python3 "$H" status <job> --result '<json>' --done
```

**Read only the file for the job you hold** (each begins with its `JOB` line forms):

| Job line | File |
|---|---|
| `JOB teardown`, `JOB skill`, `JOB cancel teardown` | `home-teardown.md` |
| `JOB video` (and `lang=`) | `home-video.md` |
| `JOB motion`, `style-change`, `skill-change`, `skill-new`, `setup`, update, `JOB cancel <type>` | `home-other.md` |

## Setup from the page

A first run opens this page before anything is installed (setup skill step 0), then runs
`setup.py install-all --report` in the background. It reports each step itself
(`status setup --step "Installing the renderer" --progress 0.6`, the share of the whole bar) and ends
with `--done`, or `--failed "<the fixes>"`. Each step also refreshes the page's tool rows. Install
anything else (ffmpeg, Node) the same way: `status setup --step "..."`, then run `install-all --report`
again. A `JOB video` waits for `Ready.`; the page says so too.
