// node tools/sheets.mjs <film-folder> [video.mp4] [--at 4.2]
//
// Turns a render into images a model can actually review. The contact sheet and
// phone test catch layout problems: overlap, blurry type, dead composition.
// They cannot catch velocity defects, which is what probe.mjs is for.
import { spawnSync } from 'node:child_process';
import { readFileSync, existsSync, mkdirSync } from 'node:fs';
import { resolve, join, dirname } from 'node:path';

const film = process.argv[2];
if (!film) { console.error('usage: node tools/sheets.mjs <film-folder> [video.mp4] [--at 4.2]'); process.exit(1); }
const dir = resolve(film);
const out = join(dir, 'out');
mkdirSync(out, { recursive: true });

const cfg = JSON.parse(readFileSync(join(dir, 'film.config.json'), 'utf8'));
const named = process.argv[3] && !process.argv[3].startsWith('--') ? process.argv[3] : null;
const tag = cfg.formats[0].name.replace(':', 'x');
const src = named
  ? resolve(named)
  : ['final-' + tag + '.mp4', 'silent-' + tag + '.mp4', 'silent-' + tag + '-draft.mp4']
      .map((f) => join(out, f)).find(existsSync);

if (!src || !existsSync(src)) { console.error('no render found in ' + out + '. render first.'); process.exit(1); }

const ai = process.argv.indexOf('--at');
const at = ai > 0 ? process.argv[ai + 1] : null;

const run = (args, label) => {
  const r = spawnSync('ffmpeg', ['-y', ...args], { stdio: ['ignore', 'ignore', 'inherit'] });
  console.log((r.status === 0 ? '  ok   ' : '  fail ') + label);
};

// 2 frames per second, 6 across. The overview pass.
run(['-i', src, '-vf', 'fps=2,scale=270:-1,tile=6x5', '-frames:v', '1', join(out, 'contact.png')], 'out/contact.png');
// How it reads at phone width, which is where it will actually be watched.
run(['-i', src, '-vf', 'fps=1,scale=360:-1,tile=5x3', '-frames:v', '1', join(out, 'phone.png')], 'out/phone.png');
// Poster frame, 1 second in.
run(['-ss', '1', '-i', src, '-frames:v', '1', join(out, 'poster.png')], 'out/poster.png');
// Played twice, to watch the wrap.
if (cfg.loop) run(['-stream_loop', '1', '-i', src, '-c', 'copy', join(out, 'loop_check.mp4')], 'out/loop_check.mp4');
// 12 consecutive frames around one moment, for inspecting a single transition.
if (at) {
  run(['-ss', String(Math.max(0, +at - 0.1)), '-i', src, '-vf', 'scale=320:-1,tile=12x1', '-frames:v', '1', join(out, 'strip.png')], 'out/strip.png (at ' + at + 's)');
}
