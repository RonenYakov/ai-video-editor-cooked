// node render.mjs <film-folder> [--draft] [--nograde] [--format 9:16]
//
// Walks time, screenshots each subframe, pipes to ffmpeg. Nothing depends on a
// live clock, so the same film renders identically every time.
import { spawn } from 'node:child_process';
import { readFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve, join, dirname } from 'node:path';
import { serve } from './serve.mjs';
import { launch } from './lib/chrome.mjs';
import { gradeFilter } from './lib/grade.mjs';

const ENGINE = dirname(fileURLToPath(import.meta.url));
const film = process.argv[2];
if (!film) {
  console.error('usage: node render.mjs <film-folder> [--draft] [--nograde] [--format 9:16]');
  process.exit(1);
}
const dir = resolve(film);
const draft = process.argv.includes('--draft');
const cfg = JSON.parse(readFileSync(join(dir, 'film.config.json'), 'utf8'));

const fi = process.argv.indexOf('--format');
const fmt = fi > 0 ? cfg.formats.find((f) => f.name === process.argv[fi + 1]) : cfg.formats[0];
if (!fmt) {
  console.error('unknown format. have: ' + cfg.formats.map((f) => f.name).join(', '));
  process.exit(1);
}

// Draft trades every quality knob for speed. Final honours the config.
const fps = draft ? 30 : cfg.fps;
const sub = draft ? 1 : cfg.subframes;              // time samples per output frame
const shutter = draft ? 360 : (cfg.shutter ?? 180); // degrees; 180 is filmic, 360 smears
const scale = draft ? 1 : (cfg.scale ?? 2);         // deviceScaleFactor, spatial supersampling
const dur = cfg.duration;

// Shutter angle decides how many of each group of `sub` samples get averaged.
// 4 subframes at 180 degrees averages 2 of every 4 and drops the rest.
const blend = Math.max(1, Math.min(sub, Math.round((sub * shutter) / 360)));
const keep = String(blend - 1);
const vf = [];
if (blend > 1) vf.push('tmix=frames=' + blend);
vf.push("select='eq(mod(n\\," + sub + ")\\," + keep + ")'");
vf.push('setpts=N/' + fps + '/TB');
if (scale > 1) vf.push('scale=' + fmt.w + ':' + fmt.h + ':flags=lanczos');

// Optional grade: film.config.json "grade" is an inline block or a json path (relative to the film)
// holding a grade block, or a style.json with a "grade" key. --nograde skips it.
let grade = cfg.grade;
if (typeof grade === 'string') {
  const g = JSON.parse(readFileSync(resolve(dir, grade), 'utf8'));
  grade = g.grade ?? g;
}
const gf = process.argv.includes('--nograde') ? '' : gradeFilter(grade);
if (gf) vf.push(gf);

const tag = fmt.name.replace(':', 'x') + (draft ? '-draft' : '');
const out = join(dir, 'out', 'silent-' + tag + '.mp4');
mkdirSync(join(dir, 'out'), { recursive: true });

const ff = spawn('ffmpeg', [
  '-y', '-f', 'image2pipe', '-framerate', String(fps * sub), '-i', '-',
  '-vf', vf.join(','), '-r', String(fps),
  '-c:v', 'libx264', '-preset', draft ? 'veryfast' : 'slow', '-crf', draft ? '28' : '16',
  '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out,
], { stdio: ['pipe', 'inherit', 'inherit'] });

const srv = await serve(ENGINE, dir);
const browser = await launch();
const page = await browser.newPage({
  viewport: { width: fmt.w, height: fmt.h },
  deviceScaleFactor: scale,
});
await page.goto(srv.url + '/film/film.html?w=' + fmt.w + '&h=' + fmt.h);
// A film exposes window.ready once its grids and fonts have loaded. Without this,
// early frames can render before beats.json arrives, which breaks determinism.
await page.evaluate(() => (window.ready ?? document.fonts.ready).then(() => true));

console.log(dir + '  ' + fmt.name + '  ' + fps + 'fps  sub=' + sub + '  shutter=' + shutter + 'deg  scale=' + scale + 'x');
const total = Math.round(dur * fps * sub);
for (let i = 0; i < total; i++) {
  await page.evaluate((t) => window.seek(t), i / (fps * sub));
  const png = await page.screenshot({ type: 'png' });
  if (!ff.stdin.write(png)) await new Promise((r) => ff.stdin.once('drain', r));
  if (i % (fps * sub) === 0) process.stdout.write('\r  ' + (i / (fps * sub)).toFixed(0) + 's / ' + dur + 's');
}
ff.stdin.end();
await new Promise((r) => ff.on('close', r));
await browser.close();
srv.close();
console.log('\n  -> ' + out);
