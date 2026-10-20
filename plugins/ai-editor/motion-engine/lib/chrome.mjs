// Finds an existing headless Chrome so no browser is downloaded here.
// Order: MOTION_CHROME, the Remotion chrome-headless-shell, the HyperFrames Chrome.
import { existsSync, readdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { chromium } from 'playwright-core';

const HOME = process.env.AI_EDITOR_HOME ?? join(homedir(), '.ai-video-editor');
const EXE = process.platform === 'win32' ? 'chrome-headless-shell.exe' : 'chrome-headless-shell';

// <dir>/chrome-headless-shell/<platform>/<folder>/chrome-headless-shell[.exe]
function inShellDir(dir) {
  try {
    for (const p of readdirSync(dir)) for (const f of readdirSync(join(dir, p))) {
      const exe = join(dir, p, f, EXE);
      if (existsSync(exe)) return exe;
    }
  } catch {}
  return null;
}

export function chromePath() {
  const env = process.env.MOTION_CHROME;
  if (env) {
    if (!existsSync(env)) throw new Error('MOTION_CHROME is set but not found: ' + env);
    return env;
  }
  const remotion = inShellDir(join(HOME, 'remotion', 'node_modules', '.remotion', 'chrome-headless-shell'));
  if (remotion) return remotion;
  const bin = join(HOME, 'motion', 'node_modules', '.bin', process.platform === 'win32' ? 'hyperframes.cmd' : 'hyperframes');
  if (existsSync(bin)) {
    const r = spawnSync(bin, ['browser', 'path'], { encoding: 'utf8', shell: process.platform === 'win32', timeout: 60000 });
    const p = (r.stdout ?? '').trim().split(/\r?\n/).pop();
    if (r.status === 0 && p && existsSync(p)) return p;
  }
  throw new Error('no headless Chrome found. Run: python plugins/ai-editor/skills/setup/scripts/setup.py bootstrap (or set MOTION_CHROME to a chrome path)');
}

export const launch = () => chromium.launch({ executablePath: chromePath() });
