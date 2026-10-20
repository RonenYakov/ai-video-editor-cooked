// node preview.mjs <film-folder>
// Serves the engine and the film and prints the scrub URL. Taste decisions happen here, in
// seconds, instead of waiting on a render.
import { fileURLToPath } from 'node:url';
import { resolve, join, dirname } from 'node:path';
import { serve } from './serve.mjs';

const ENGINE = dirname(fileURLToPath(import.meta.url));
const film = resolve(process.argv[2] ?? join(ENGINE, 'template'));
const srv = await serve(ENGINE, film);
console.log('\n  ' + srv.url + '/engine/preview.html?film=' + encodeURIComponent(film) + '\n\n  ctrl-c to stop\n');
