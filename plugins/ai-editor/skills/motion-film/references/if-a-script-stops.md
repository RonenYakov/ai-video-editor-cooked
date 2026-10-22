# Motion film: if a script stops

| message | do |
|---|---|
| `Cannot find` / no `render.mjs` in ENGINE | `setup.py motion-engine`, then the same command |
| `no Chrome Headless Shell` | `setup.py remotion`, then again |
| probe fails: undeclared jump, dead stretch, loop seam | the builder fixes it; declare only cuts meant, in `film.config.json` `cuts` |
| `no render found` (sheets.mjs) | render the draft first: `render.mjs "$FILM" --draft` |
| `no beats in ...beats.sheet.json` | write the sheet as in step 4 |
| the joined video skips, stutters or shows an old frame at a whole second | `render.mjs "$FILM" --full` once (renders every piece again), then tell the maintainers |
