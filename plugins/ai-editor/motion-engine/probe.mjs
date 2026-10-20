// node probe.mjs <film-folder>
//
// Measures the motion instead of looking at it. A still frame cannot show
// velocity, so contact sheets miss popped transitions, dead beats and loop-seam
// stutters. This walks the timeline, diffs consecutive frames, and fails on:
//
//   cut      an undeclared discontinuity (a pop or an accidental hard cut)
//   dead     a stretch where nothing moves for longer than deadMax
//   seam     a loop that jumps or freezes where it wraps
//
// Declared cuts live in film.config.json "cuts": [4.0, 8.5]. Anything there is
// legal, so intentional hard cuts never trip the gate.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve, join, dirname } from 'node:path';
import { serve } from './serve.mjs';
import { launch } from './lib/chrome.mjs';

const ENGINE = dirname(fileURLToPath(import.meta.url));
const film = process.argv[2];
if (!film) { console.error('usage: node probe.mjs <film-folder>'); process.exit(1); }
const dir = resolve(film);
const cfg = JSON.parse(readFileSync(join(dir, 'film.config.json'), 'utf8'));

const SPIKE = 6;        // x median -> reads as a cut
const SEAM_JUMP = 4;    // x median at the wrap point
const SEAM_FREEZE = 0.05;
const DEAD = 0.08;      // x median -> nothing is moving
const PIXEL_STEP = 16;  // sample every 16th pixel, red channel only

const fps = cfg.fps;
const dur = cfg.duration;
const fmt = cfg.formats[0];
const cuts = cfg.cuts ?? [];
const deadMax = cfg.deadMax ?? 1.0;
const tol = 2 / fps;    // a declared cut may land within two frames

const srv = await serve(ENGINE, dir);
const browser = await launch();
const page = await browser.newPage({ viewport: { width: fmt.w, height: fmt.h }, deviceScaleFactor: 1 });
await page.goto(srv.url + '/film/film.html?w=' + fmt.w + '&h=' + fmt.h);
await page.evaluate(() => (window.ready ?? document.fonts.ready).then(() => true));

// One round trip per frame: seek, read pixels, diff against the previous frame.
const stepFrame = (t, keepFirst) => page.evaluate(([t, keepFirst, step]) => {
  window.seek(t);
  const c = document.getElementById('c');
  if (!c) throw new Error('film has no <canvas id="c">');
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  const s = (window.__s ??= {});
  let v = 0;
  if (s.prev) {
    let sum = 0, n = 0;
    for (let i = 0; i < d.length; i += 4 * step) { sum += Math.abs(d[i] - s.prev[i]); n++; }
    v = sum / n;
  }
  s.prev = d;
  if (keepFirst) s.first = d;
  return v;
}, [t, keepFirst, PIXEL_STEP]);

const total = Math.round(dur * fps);
const diffs = [];
for (let f = 0; f < total; f++) {
  const v = await stepFrame(f / fps, f === 0);
  if (f > 0) diffs.push({ t: f / fps, v });
  if (f % fps === 0) process.stdout.write('\r  probing ' + (f / fps).toFixed(0) + 's / ' + dur + 's');
}

// The wrap: the last frame followed by the first should look like any other step.
let seam = null;
if (cfg.loop) {
  seam = await page.evaluate((step) => {
    const { prev, first } = window.__s;
    let sum = 0, n = 0;
    for (let i = 0; i < prev.length; i += 4 * step) { sum += Math.abs(prev[i] - first[i]); n++; }
    return sum / n;
  }, PIXEL_STEP);
}

await browser.close();
srv.close();

const vals = diffs.map((d) => d.v).sort((a, b) => a - b);
const median = vals[vals.length >> 1] ?? 0;
const findings = [];

if (median === 0) {
  findings.push({ kind: 'static', t: 0, detail: 'nothing moves anywhere in this film' });
} else {
  for (const d of diffs) {
    if (d.v > median * SPIKE && !cuts.some((c) => Math.abs(c - d.t) <= tol)) {
      findings.push({ kind: 'cut', t: +d.t.toFixed(3), detail: 'undeclared discontinuity, ' + (d.v / median).toFixed(1) + 'x median' });
    }
  }
  let run = 0;
  for (const d of diffs) {
    run = d.v < median * DEAD ? run + 1 : 0;
    if (run === Math.round(deadMax * fps)) {
      findings.push({ kind: 'dead', t: +(d.t - deadMax).toFixed(3), detail: 'nothing moves for ' + deadMax + 's' });
    }
  }
  if (seam !== null) {
    if (seam > median * SEAM_JUMP) findings.push({ kind: 'seam', t: dur, detail: 'loop jumps, ' + (seam / median).toFixed(1) + 'x median' });
    else if (seam < median * SEAM_FREEZE) findings.push({ kind: 'seam', t: dur, detail: 'loop freezes, duplicate frame at the wrap' });
  }
}

const report = {
  film: dir, fps, duration: dur, median: +median.toFixed(4),
  seam: seam === null ? null : +seam.toFixed(4),
  findings,
  velocity: diffs.map((d) => +d.v.toFixed(3)),
};
mkdirSync(join(dir, 'out'), { recursive: true });
writeFileSync(join(dir, 'out', 'probe.json'), JSON.stringify(report, null, 1));

console.log('\n  median frame diff ' + median.toFixed(3) + (seam === null ? '' : '   seam ' + seam.toFixed(3)));
if (!findings.length) {
  console.log('  PASS  no motion defects');
  process.exit(0);
}
for (const f of findings) console.log('  ' + f.kind.toUpperCase().padEnd(7) + f.t + 's  ' + f.detail);
console.log('  FAIL  ' + findings.length + ' finding(s), see out/probe.json');
process.exit(1);
