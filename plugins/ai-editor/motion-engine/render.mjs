// node render.mjs <film-folder> [--draft] [--nograde] [--format 9:16] [--range 6-8[,a-b]] [--full]
//
// Walks time, screenshots each subframe, pipes to ffmpeg. Nothing depends on a
// live clock, so the same film renders identically every time.
//
// Only what changed is rendered again. The film is rendered in pieces of `segment` seconds (film.config.json,
// default 1) kept in out/seg-<format>/. Before rendering, a quick pass draws every frame at a quarter size and
// hashes it: a piece whose frames, settings and engine are unchanged is reused, the rest are rendered, and the
// pieces are joined without re-encoding. --range forces the pieces over those seconds (the times a note named);
// --full renders everything. Each piece starts on a whole frame, so motion blur never mixes two pieces.
import { spawn } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync, existsSync, statSync, renameSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { resolve, join, dirname } from 'node:path';
import { serve } from './serve.mjs';
import { launch } from './lib/chrome.mjs';
import { gradeFilter } from './lib/grade.mjs';

const ENGINE = dirname(fileURLToPath(import.meta.url));
const film = process.argv[2];
if (!film) {
  console.error('usage: node render.mjs <film-folder> [--draft] [--nograde] [--format 9:16] [--range 6-8] [--full]');
  process.exit(1);
}
const dir = resolve(film);
const draft = process.argv.includes('--draft');

// A cooked. film (home.py writes .gate) renders nothing, draft or final, until the user approved the beat sheet's
// stills on the review page: review.py writes beats.approved.json with the sheet's hash. A changed sheet needs a new Approve.
if (existsSync(join(dir, '.gate'))) {
  let ok = false;
  try {
    const want = JSON.parse(readFileSync(join(dir, 'beats.approved.json'), 'utf8')).sheet_sha256;
    ok = want === createHash('sha256').update(readFileSync(join(dir, 'beats.sheet.json'))).digest('hex');
  } catch {}
  if (!ok) {
    console.error('The beat sheet is not approved. Draw one still per beat (tools/still.mjs), show them with ' +
      '`review.py beats <film>` and wait for the user to Approve before any render. A changed sheet needs approving again.');
    process.exit(3);
  }
}
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
const segDir = join(dir, 'out', 'seg-' + tag);
mkdirSync(segDir, { recursive: true });

const sha = (x) => createHash('sha256').update(x).digest('hex');
const N = Math.round(dur * fps);                                  // output frames
const F = Math.max(1, Math.round((cfg.segment ?? 1) * fps));      // frames per piece
const pieces = Array.from({ length: Math.ceil(N / F) }, (_, i) => ({ i, f0: i * F, f1: Math.min(N, (i + 1) * F) }));
// Anything that changes every frame's pixels without changing film.html: the settings, the filters, this engine.
const key = sha(JSON.stringify({ fps, sub, shutter, scale, fmt, vf, draft, F }) +
  readFileSync(fileURLToPath(import.meta.url)) + readFileSync(join(ENGINE, 'lib', 'motion.js')));

const ranges = [];
const ri = process.argv.indexOf('--range');
if (ri > 0) {
  for (const r of String(process.argv[ri + 1] ?? '').split(',')) {
    const m = r.match(/^\s*([\d.]+)\s*-\s*([\d.]+)\s*$/);
    if (!m) { console.error('--range wants seconds like 6-8 or 1.5-2,6-8'); process.exit(1); }
    ranges.push([+m[1], +m[2]]);
  }
}
const full = process.argv.includes('--full');
const idxPath = join(segDir, 'index.json');
let idx = {};
try { idx = JSON.parse(readFileSync(idxPath, 'utf8')); } catch {}
const old = !full && idx.key === key ? idx.pieces ?? {} : {};

const srv = await serve(ENGINE, dir);
const browser = await launch();
const open = async (w, h, s) => {
  const p = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: s });
  await p.goto(srv.url + '/film/film.html?w=' + w + '&h=' + h);
  // A film exposes window.ready once its grids and fonts have loaded. Without this,
  // early frames can render before beats.json arrives, which breaks determinism.
  await p.evaluate(() => (window.ready ?? document.fonts.ready).then(() => true));
  return p;
};

console.log(dir + '  ' + fmt.name + '  ' + fps + 'fps  sub=' + sub + '  shutter=' + shutter + 'deg  scale=' + scale + 'x');
const started = Date.now();
// The quick pass: every output frame at a quarter of the size, hashed. Cheap next to the render itself.
if (!full) {
  const small = await open(Math.max(2, Math.round(fmt.w / 4)), Math.max(2, Math.round(fmt.h / 4)), 1);
  for (const pc of pieces) {
    const h = createHash('sha256');
    for (let f = pc.f0; f < pc.f1; f++) {
      await small.evaluate((t) => window.seek(t), f / fps);
      h.update(await small.screenshot({ type: 'png' }));
    }
    pc.fp = h.digest('hex');
  }
  await small.close();
}
const forced = (pc) => ranges.some(([a, b]) => pc.f0 / fps < b && pc.f1 / fps > a);
for (const pc of pieces) {
  pc.file = 'p' + String(pc.i).padStart(4, '0') + '.mp4';
  const o = old[pc.file];
  const have = existsSync(join(segDir, pc.file)) && statSync(join(segDir, pc.file)).size > 0;
  pc.reuse = !full && !!pc.fp && have && !!o && o.fp === pc.fp && o.f0 === pc.f0 && o.f1 === pc.f1 && !forced(pc);
}
const todo = pieces.filter((p) => !p.reuse);
const save = () => {
  const next = { key, pieces: {} };
  for (const p of pieces) if (p.reuse || p.done) next.pieces[p.file] = { f0: p.f0, f1: p.f1, fp: p.fp ?? null };
  writeFileSync(idxPath + '.tmp', JSON.stringify(next));
  renameSync(idxPath + '.tmp', idxPath);
};

const page = todo.length ? await open(fmt.w, fmt.h, scale) : null;
let n = 0;
for (const pc of todo) {
  const tmp = join(segDir, pc.file.replace('.mp4', '.part.mp4'));
  const ff = spawn('ffmpeg', [
    '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps * sub), '-i', '-',
    '-vf', vf.join(','), '-r', String(fps),
    '-c:v', 'libx264', '-preset', draft ? 'veryfast' : 'slow', '-crf', draft ? '28' : '16',
    '-pix_fmt', 'yuv420p', tmp,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let s = pc.f0 * sub; s < pc.f1 * sub; s++) {
    await page.evaluate((t) => window.seek(t), s / (fps * sub));
    const png = await page.screenshot({ type: 'png' });
    if (!ff.stdin.write(png)) await new Promise((r) => ff.stdin.once('drain', r));
  }
  ff.stdin.end();
  const code = await new Promise((r) => ff.on('close', r));
  if (code !== 0) { console.error('\nffmpeg failed on ' + (pc.f0 / fps).toFixed(1) + 's'); process.exit(1); }
  renameSync(tmp, join(segDir, pc.file));
  pc.done = true;
  save();   // an interrupted render keeps the pieces it finished
  process.stdout.write('\r  rendered ' + ++n + ' of ' + todo.length + ' changed pieces (' + pieces.length + ' in all)');
}
save();
await browser.close();
srv.close();

// Join the pieces as they are (no re-encode). Each piece is a whole number of frames, so the join is exact.
writeFileSync(join(segDir, 'list.txt'), pieces.map((p) => "file '" + p.file + "'").join('\n') + '\n');
const cat = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', join(segDir, 'list.txt'),
  '-c', 'copy', '-movflags', '+faststart', out], { stdio: ['ignore', 'inherit', 'inherit'] });
if ((await new Promise((r) => cat.on('close', r))) !== 0) { console.error('\njoining the pieces failed'); process.exit(1); }

const span = (ps) => {   // [[0,1],[1,2],[6,7]] -> "0-2s, 6-7s"
  const out = [];
  for (const p of ps) {
    const a = p.f0 / fps, b = p.f1 / fps;
    if (out.length && Math.abs(out[out.length - 1][1] - a) < 1e-6) out[out.length - 1][1] = b; else out.push([a, b]);
  }
  return out.map(([a, b]) => +a.toFixed(2) + '-' + +b.toFixed(2) + 's').join(', ');
};
const report = { video: out, pieces: pieces.length, rendered: todo.length, reused: pieces.length - todo.length,
  rendered_at: span(todo), seconds: Math.round((Date.now() - started) / 100) / 10 };
writeFileSync(join(dir, 'out', 'render-' + tag + '.json'), JSON.stringify(report, null, 1));
console.log('\n  ' + (todo.length === pieces.length ? 'rendered all of it' : todo.length ? 'rendered ' + report.rendered_at + ', reused the rest'
  : 'nothing changed, reused every piece') + ' in ' + report.seconds + 's');
console.log('  -> ' + out);
