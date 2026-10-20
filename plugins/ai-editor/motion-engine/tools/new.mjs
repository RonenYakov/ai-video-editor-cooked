// node tools/new.mjs <target-folder>
// Copies template/ to the target (anywhere on disk). The engine is never copied, only imported.
import { cpSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve, join, dirname } from 'node:path';

const target = process.argv[2];
if (!target) { console.error('usage: node tools/new.mjs <target-folder>'); process.exit(1); }
const dest = resolve(target);
if (existsSync(dest)) { console.error(dest + ' already exists'); process.exit(1); }

cpSync(join(dirname(fileURLToPath(import.meta.url)), '..', 'template'), dest, { recursive: true });
console.log('  ' + dest + '\n\n  1. fill ' + join(dest, 'BRIEF.md') + '\n  2. node preview.mjs ' + dest);
