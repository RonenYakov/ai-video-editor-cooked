# Style chat, skill chat, motion film, setup, update and cancel jobs

The shared rules (waiting, status, questions, keys) are in `home.md`.

### `JOB style-change <my-style|@handle> [style=<style.json>] text=<the user's words>`

The user typed what to change on a style's page (My styles, "Tell it what to change"). Turn the words
into corrections at that style's scope, one per thing they asked, with the taste skill's setting table
(`taste.py add <section> "<rule>" --set <key>=<value>`): `--style <style.json>` for a creator's style
(its `style.overrides.json` and its `edit-like-<slug>` skill), no `--style` for my-style (taste.json
and the `my-style` skill). A wish no setting covers is a word rule at the same scope. Do not ask the
scope question: the page named the style. Report what was saved, in plain words:
`status style-change --step "Saved: captions 6% tall" --result '{"changed": ["Captions 6% tall", "About 3 zooms a minute"]}' --done`.
The page shows `changed` and reloads the style's settings and its "Learned from your feedback" list.
A wish to run another skill on this style's videos ("make a thumbnail after", "run /my-broll before the edit", "stop
running /x") changes its What runs, not a setting: `python3 "$H" chain <style> <skill> --at before|after` (`--off` takes
it out); `<style>` is the job's style (my-style is `mine`). Only a skill this session has.
A text starting `Combined from <name> (<style.json>); ...` came from New style, Combine styles: the new style
started as a copy of the first one. Read each named style.json and set every part the user's words take from
another style (captions, zooms, cut, cards, sound, motion) to that style's values, the same way.
A style card adds "Learned from N videos" once its rules came from N edits (review notes saved at
the final approve's "Teach <style>" panel, `review.py learn --done`).
The same change said in the chat goes through the same `taste.py add`, so both land in one skill.
The page's own controls (sliders, zooms, cut, sound effects) save through `styleskill.learn` directly
and need no job.

### `JOB motion <name> format=<f> film=<FILM> refs=<FILM>/refs.json root=<library> idea=<one line>`

The user pressed "New motion video". The film folder, its `refs/` and `refs.json` already exist. Load the
`ai-editor:motion-film` skill with the Skill tool and run it from its step 1 with that `FILM`, on the Motion Studio
engine only (that skill's rule): never Remotion, HyperFrames or the `motion` skill for a film. Report each step with `status motion --step "..."`, and at
the end `status motion --result '{"film": "<FILM>", "video": "<final path>"}' --done`.

### Connect Modal and Test render (no job for Claude)

The window runs these itself (`setup.py modal-connect` and `modal-test`), as jobs `modal` and `modal-test`
owned by `home`. `wait` never hands them out and `status` never writes to them.

### `JOB setup`

The user pressed Start setup on the first-run Home. Run `setup.py install-all --report` in the background
(the setup skill's step 0); it reports its own steps onto this job, as in Setup from the page below.

### Update (no job for Claude)

The window runs Update itself, as job `update` owned by `home`: `update.py market` updates the nextwork
marketplace, then `ai-editor@nextwork` and `creator-teardown@nextwork`, and the window server restarts from the new
version's folder on the same port with the same token, so the open tab reloads itself. `wait` never hands it out.
An open Claude session keeps the version it loaded until the user types `/reload-plugins`; the page says so and
shows the command until a command from that session runs on the new version.

### `JOB cancel <type>` (any other job)

The user pressed the sidebar's Stop on that job. Stop its running commands (TaskStop), take no next
step, and say so in one line. A Stop also makes every tool call of the session that held the job fail for two
minutes with "The user pressed Stop in the cooked. window" (toolhook.py): when a tool call fails with that, stop at
once, say in one line what was left unfinished, and wait for the user to type in the Terminal.

