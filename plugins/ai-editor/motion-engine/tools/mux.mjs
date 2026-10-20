// node tools/mux.mjs <film-folder> [--format 9:16]
//
// Joins the silent render to the audio, normalises loudness, writes final-*.mp4.
// Audio sources, in order: audio/mix.wav (anything you pre-mixed), otherwise
// audio/vo.wav and audio/track.wav mixed together, otherwise whichever exists.
import { spawnSync } from 'node:child_process';
import { readFileSync, existsSync } from 'node:fs';
import { resolve, join, dirname } from 'node:path';

const film = process.argv[2];
if (!film) { console.error('usage: node tools/mux.mjs <film-folder> [--format 9:16]'); process.exit(1); }
const dir = resolve(film);
const cfg = JSON.parse(readFileSync(join(dir, 'film.config.json'), 'utf8'));

const fi = process.argv.indexOf('--format');
const fmt = fi > 0 ? cfg.formats.find((f) => f.name === process.argv[fi + 1]) : cfg.formats[0];
if (!fmt) { console.error('unknown format'); process.exit(1); }
const tag = fmt.name.replace(':', 'x');

const video = join(dir, 'out', 'silent-' + tag + '.mp4');
if (!existsSync(video)) { console.error('missing ' + video + '. render at full quality first.'); process.exit(1); }

const a = (n) => join(dir, 'audio', n);
const mix = existsSync(a('mix.wav')) ? [a('mix.wav')] : [a('vo.wav'), a('track.wav')].filter(existsSync);
if (!mix.length) { console.error('no audio in ' + join(dir, 'audio') + ' (mix.wav, or vo.wav / track.wav)'); process.exit(1); }

const out = join(dir, 'out', 'final-' + tag + '.mp4');
const args = ['-y', '-i', video, ...mix.flatMap((f) => ['-i', f])];

// ponytail: single-pass loudnorm. Two-pass measures first and hits the target
// more exactly; switch if a platform rejects the level.
const LOUD = 'loudnorm=I=-14:TP=-1.5:LRA=11';
if (mix.length > 1) {
  // VO sits above the music. When grid is "vo" the music is support, so duck it.
  const duck = cfg.music === 'support' ? 0.35 : 0.7;
  args.push('-filter_complex',
    '[2:a]volume=' + duck + '[bed];[1:a][bed]amix=inputs=2:duration=longest:normalize=0[m];[m]' + LOUD + '[a]',
    '-map', '0:v', '-map', '[a]');
} else {
  args.push('-af', LOUD, '-map', '0:v', '-map', '1:a');
}
args.push('-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out);

const r = spawnSync('ffmpeg', args, { stdio: ['ignore', 'ignore', 'inherit'] });
if (r.status !== 0) process.exit(r.status ?? 1);
console.log('  -> ' + out);
