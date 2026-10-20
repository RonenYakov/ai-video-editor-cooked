// node tools/still.mjs <film-folder> <t>=<out.png> [<t>=<out.png> ...] [--format 9:16]
//
// One frame of film.html per pair, straight from seek(t), no video. The beat
// sheet's stills: each beat drawn at rest before anything is rendered.
// Paths are relative to the film folder.
import { readFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve, join, dirname } from 'node:path';
import { serve } from '../serve.mjs';
import { launch } from '../lib/chrome.mjs';

const ENGINE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const fi = args.indexOf('--format');
const fname = fi >= 0 ? args.splice(fi, 2)[1] : null;
const [film, ...pairs] = args;
const shots = pairs.map((p) => { const i = p.indexOf('='); return [+p.slice(0, i), p.slice(i + 1)]; });
if (!film || !shots.length || shots.some(([t, p]) => !(t >= 0) || !p)) {
  console.error('usage: node tools/still.mjs <film-folder> <t>=<out.png> [<t>=<out.png> ...] [--format 9:16]');
  process.exit(1);
}
const dir = resolve(film);
const cfg = JSON.parse(readFileSync(join(dir, 'film.config.json'), 'utf8'));
const fmt = fname ? cfg.formats.find((f) => f.name === fname) : cfg.formats[0];
if (!fmt) { console.error('unknown format. have: ' + cfg.formats.map((f) => f.name).join(', ')); process.exit(1); }

const srv = await serve(ENGINE, dir);
const browser = await launch();
const page = await browser.newPage({ viewport: { width: fmt.w, height: fmt.h }, deviceScaleFactor: 1 });
await page.goto(srv.url + '/film/film.html?w=' + fmt.w + '&h=' + fmt.h);
await page.evaluate(() => (window.ready ?? document.fonts.ready).then(() => true));
for (const [t, p] of shots) {
  const out = resolve(dir, p);
  mkdirSync(dirname(out), { recursive: true });
  await page.evaluate((t) => window.seek(t), t);
  await page.screenshot({ path: out, type: 'png' });
  console.log('  ok   ' + out + ' (' + t + 's)');
}
await browser.close();
srv.close();
