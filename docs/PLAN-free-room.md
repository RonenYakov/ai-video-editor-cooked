# Free Room Plan

## Goal

Three changes from the user, 2026-10-22:

1. Every finished video lands in one folder outside the library, easy to open.
2. **Edit a video** becomes a free room. You add footage and talk to Claude. A reference or a brief is optional, and the page has no step ladder.
3. **Motion studio** starts from references plus a short chat message. You no longer have to write a brief.

**Talking head** stays as it is.

## What exists (read 2026-10-22)

- Library: `~/Videos/AI Editor` (`library.path()`). Finished videos are `render.mp4`, or `cut.mp4` for a final cut, inside `<library>/edits/<name>/`. `library.status()` says `done` when the last event is an approve with `sent`, and `review.py cmd_final` marks a cut as the final video.
- Project page: `home.html` `pjPlan` / `pjSteps` / `vProject` draw a numbered step ladder for every kind. The chat is `#chatdock` / `#chatfab`, a slide-over mounted by `syncDock()` through `CookedChat.mount(host, {slug})` from `chat.js`.
- Project data: `projects.py`. `refs` is a list of strings (creator handles or URLs). There is no note or brief field and no unlink.
- Motion: the page's `makeFilm()` refuses an empty idea. `POST /job {type:'motion', name, idea, format, lang, refs:[{source,take,role}]}` goes to `home.py`, and its demo checks bad motion jobs (around line 3514).
- Chat: `home.py chat_send(slug, text)` runs `claude -p` in the library folder with a project header as context.

## API contract (all three work packages build to this)

| Call | Does |
|---|---|
| `GET /state` (the page's main poll) gains `finished: {path, count}` | Where finished videos go, and how many are there |
| `POST /finished/open {}` | Opens that folder in Finder or Explorer (`library.reveal_cmd`) |
| `POST /finished/set {path}` | Changes the folder, saved in `library.json` as `finished` |
| `POST /project/unlink {slug, field, value}` | Removes one source or ref |
| `POST /project/note {slug, text}` | Optional brief, stored as `project.json` `note` (empty clears it) |
| `POST /project/link` with `field:'refs'` | Now also takes a local file path (an uploaded video or picture), stored absolute |
| `POST /chat/send` on a **motion** project with no edits and no running motion job | Starts the film. Queues `type:'motion'` with `idea` = the message (may be short), refs = the project's refs (role auto), `note` = the project's note. The reply goes into the chat history ("Started your film from 3 references."). Later messages are ordinary chat. |
| `POST /job type:'motion'` | `idea` may be empty when there is at least one ref. Empty idea and no refs is still an error. |

## Work packages

### WP1: Finished folder (Python: `library.py`, `review.py`, `home.py` server part)

- `library.finished_path(make=True)`: `AI_EDITOR_FINISHED` env var, else `library.json` `finished`, else `~/Videos/cooked Finished`. Also `set_finished(p)`.
- `library.deliver(edit_dir) -> Path | None`: copies the finished video to the folder as `<project or edit name> <YYYY-MM-DD>.mp4`, adding ` (2)` on a name clash. It is idempotent: it records the delivered file and its source mtime in `review.json` `delivered`, so a second call does nothing unless the video changed. It copies, never moves, because the review page still plays the original.
- Called wherever an edit becomes `done` (approve on the final round, and `cmd_final` followed by approve) and when a motion film finishes. Find the real transitions; do not guess.
- `home.py`: the `/finished/open` and `/finished/set` endpoints, `finished` in the state, and a delivery sweep in the poll as a safety net, so an edit that went `done` while the server was down is still delivered.
- Done when `library.py demo` covers path precedence, the name clash, idempotence and re-delivery after a re-render, and `home.py demo` covers both endpoints.

### WP2: Motion from references (Python + skill: `projects.py`, `home.py` chat/job part, `skills/motion-film`)

- `projects.py`: `unlink(slug, field, value)`, `set_note(slug, text)`, `note` in `new()` (old projects read as `""`), and refs that accept absolute file paths, deduplicated. Add these to `projects.py demo`.
- `home.py`: the `/project/unlink` and `/project/note` endpoints. `/job` motion allows an empty idea when refs exist. The `chat_send` motion start described above. Every project's chat header now carries `note=` when it is set.
- `skills/motion-film`: when the job has no idea or only a one-line one, take the intent from the refs and their notes. Never ask for a brief. Ask at most one question, and only when the refs disagree. Check the skill's text under `READ_BUDGET` (`tests/check_plugins.py`).
- Done when `home.py demo` covers: a motion `/job` with refs and no idea is accepted; no refs and no idea is still rejected; a motion `chat_send` queues exactly one job, and a second message does not queue another; unlink and note work.

### WP3: The page (`home.html`, maybe `chat.js`, `ui.css`)

- **Edit and Motion project pages: "room" layout.** The chat is the main column, mounted inline on the project page and not as the slide-over. Beside it, or on top on a phone, is one **Materials** panel:
  - **Footage** (Edit only): drop or choose videos, a list with remove.
  - **References** (both): paste a link, drop a video or picture, pick an analysed creator, remove any. Labelled "Optional" on Edit. On Motion it is the first thing you see, with the hint "Add references, then tell Claude what you want in a line."
  - **Brief** (both, collapsed, "Optional"): one textarea saved to `/project/note` on blur.
  - **Results**: the project's edits with Open review, plus "Open finished folder".
- No step ladder on Edit or Motion. **Talking head keeps today's steps** unchanged.
- The chat placeholder per kind: Edit "Tell Claude what to do with your footage", Motion "Say what you want. One line is enough."
- **Home page:** a "Finished videos" button in the header that calls `/finished/open`, with the count from the state.
- Keep the refresh persistence (`keepView`, `ave-home-keep`) working: an unsent brief draft survives a refresh.
- Done when a new `tests/test_room.mjs` (in `tests/demos.sh`) checks that Edit and Motion render the room with no `ol.stp` and with the Materials panel, that talking-head still renders `ol.stp`, and that the Finished button exists.

## Status

All three landed 2026-10-22 (see CHANGELOG). Suite green.

## Order

All three run at once in the same tree, on different files and functions. Each one runs its own demos. The lead then runs `tests/demos.sh`, `tests/check_plugins.py` and `claude plugin validate --strict`, and makes one commit.

## Out of scope

- Talking-head changes, the desktop icon, and the NextWork rename.
