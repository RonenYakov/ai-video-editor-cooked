# BRIEF

This file is the contract. Claude fills it from what you said, you correct it,
and only then does any code get written. Anything left `TBD` gets asked about,
never guessed.

## 1. Inputs

- **Subject / product:** TBD
- **URL:** TBD (real screenshots, real logo, real colours and fonts come from here)
- **Duration:** TBD seconds
- **Formats:** 9:16 primary, then 1:1 and 16:9 from the same timeline
- **Reference:** TBD (`shared/refs/...`, a frame or a video. Take its grammar, never its content)
- **Music:** TBD (a file in `audio/`, or "synthesize")
- **Voiceover:** TBD (script below, or none)
- **One real metric to show:** TBD (a real number, never an invented one)

### References read

One row per reference Ronen gave. Watched, not guessed.

| ref | take | avoid |
|---|---|---|
| TBD | TBD | TBD |

## 2. Grid

Which timeline owns the cut. This decides what the probe measures against.

- **grid:** `beats` or `vo`
- **music:** `primary` or `support`
- **barOne:** TBD seconds (set by ear, once. Never inferred as every 4th beat)
- **BPM:** TBD (from `audio/beats.json`)

When grid is `vo`, the voiceover owns the cut and music supports it. Cutting
picture to a music beat mid-sentence fights the narration.

## 3. Direction

Five lines, no more. Palette, type, texture, camera language, energy.

- TBD

## 4. Banned for this film

On top of the global list in CLAUDE.md:

- TBD

## 5. Beat sheet

**One line per beat. This is the part that decides whether the film is good.**

Every row names a timestamp, what is on screen, what actually moves, and what
is heard. Do not write "product appears with energy". Write what the frame
contains and which property animates.

A beat with nothing new on screen is a defect, not a pause. Something changes
every 2 to 4 seconds minimum, and on a music-led film, something changes on
every beat.

| t | on screen | the move | sound |
|---|---|---|---|
| 0.00 | *(example, delete me)* 5 words of problem copy, 190px, left-aligned, bottom third | words arrive one at a time, 80ms apart, y spring from +40px | downbeat, low thump |
| 0.50 | TBD | TBD | TBD |
| 1.00 | TBD | TBD | TBD |

## 6. Cuts

Hard cuts are legal but must be declared, or the probe reads them as popped
transitions. List every intentional discontinuity here and copy it into
`film.config.json` → `cuts`.

- TBD

## 7. Loop

- **Loops:** yes / no
- If yes: the last frame equals the first, **including the velocity of anything
  still moving.** Matching position alone leaves a visible hitch at the wrap.

## 8. Voiceover script

Written to be spoken, not read. Short sentences. One idea per line, because each
line becomes a timing unit in `audio/vo.json`.

- TBD

## 9. Gates

Nothing skips ahead.

1. This brief, approved by Ronen
2. Assets pulled and listed
3. `beats.json` (and `vo.json` if there is a voiceover)
4. Preview scrubbed, transitions stepped frame by frame
5. `node probe.mjs` passes
6. Draft render, contact sheet, defect pass, max 3 rounds
7. Final render, mux, all formats
