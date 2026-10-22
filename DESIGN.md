# cooked. design

The app (`plugins/ai-editor/lib/ai_editor/home.html`, `review.html`, `chat.js`) is a tool for people who are not
professional editors. It should feel warm and friendly, and it should never make them guess what something is or
whose turn it is. The tokens live in `ui.css`. `review.html` mirrors the neutrals.

## Ground

- Warm light by default (`--page #FFFDFA`, `--side #F6F1EA`, `--panel #FFFFFF`, `--ink #1F1A16`). The OS setting
  does not switch it. Dark is only on the switch (`html[data-theme=dark]`).
- System UI font, one family. Headings are bold with tight tracking. Body text is 14–16 px.
- Cards are 16–24 px round with a soft offset shadow (`--shadow`, `--shadow-hi`). There are no hard shadows and no
  coloured side borders.

## Colour has two jobs, and nothing else

1. **Kind**: what sort of project this is. Put a `k-<kind>` class on the element, then use `--k` (base), `--kb`
   (tint), `--kt` (text on a tint) and `--kf` (a fill that holds white text at AA).
   - Edit a video: blue `k-edit`
   - Talking head: coral `k-talking-head`
   - Motion Studio: violet `k-motion`

   The kind colours the Home doors, the sidebar and list icons, the New project picker, the room (tag, first
   material, chat send button and bubbles).
2. **State**: where a project is. Use `.spill.st-<state>` (a dot and a word) or `.sdotk`.
   - `work` amber, pulsing: Claude is on it.
   - `you` pink: your turn.
   - `done` green.
   - `fail` red: stopped.
   - `new` neutral.

   The server sends `state` with every project (`home.py project_state`).

A colour never travels without its word. The primary button outside a kind is ink.

## Words

Plain words first: "Your turn", "Running a command", "your finished folder". Raw detail stays one click away. Tool
calls fold under the chat line. The full style breakdown (cuts, zooms, captions, colours and fonts, graphics and
animation, sound, hook) stays visible wherever a style is made or read.
