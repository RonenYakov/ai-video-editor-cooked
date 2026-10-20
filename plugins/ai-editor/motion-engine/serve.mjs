// Static file server on 127.0.0.1. Both render.mjs and preview.mjs use it.
// Needed because Chromium blocks ES module imports over file://, so a film
// cannot import /engine/lib/motion.js unless it is served over http.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';

const TYPES = {
  '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
  '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.woff': 'font/woff',
  '.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4', '.mp4': 'video/mp4',
};

// /engine/* from the engine folder, /film/* from the film folder.
export function serve(engine, film) {
  const s = createServer(async (req, res) => {
    const rel = normalize(decodeURIComponent(req.url.split('?')[0]))
      .replace(/^([/\\]|\.\.[/\\])+/, '');
    try {
      const m = /^(engine|film)[/\\](.*)$/.exec(rel);
      if (!m) throw 0;
      const body = await readFile(join(m[1] === 'engine' ? engine : film, m[2]));
      res.writeHead(200, { 'content-type': TYPES[extname(rel)] ?? 'application/octet-stream' });
      res.end(body);
    } catch {
      res.writeHead(404, { 'content-type': 'text/plain' });
      res.end('not found: ' + rel);
    }
  });
  return new Promise((r) => s.listen(0, '127.0.0.1', () =>
    r({ url: 'http://127.0.0.1:' + s.address().port, close: () => s.close() })));
}
