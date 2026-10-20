// Pure functions of time. No state, no timers, no Math.random.
// Imported by every film and by probe.mjs. Browser-safe (no node imports).

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));

// Damped spring, 0 -> 1, as a closed form so any frame can be drawn directly.
// k = stiffness, d = damping. At k=170: d=26 is near-critical (no overshoot),
// d=20 gives a small settle, d=14 is visibly bouncy.
export function spring(t, k = 170, d = 20) {
  if (t <= 0) return 0;
  const w0 = Math.sqrt(k);
  const z = d / (2 * w0);
  if (z < 1) {
    const wd = w0 * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + (z * w0 / wd) * Math.sin(wd * t));
  }
  return 1 - Math.exp(-w0 * t) * (1 + w0 * t);
}

// keys: [[time, value], ...]. One spring per change, summed.
// Superposition is valid for a linear system, which is what keeps this seek-safe:
// no replaying earlier frames to know where we are now.
export function track(t, keys, k = 170, d = 20) {
  let v = keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    v += (keys[i][1] - keys[i - 1][1]) * spring(t - keys[i][0], k, d);
  }
  return v;
}

// Deterministic stand-in for Math.random. Same i, same seed, same value, forever.
export function noise(i, seed = 1) {
  let h = (i | 0) + Math.imul(seed, 0x9e3779b9);
  h = Math.imul(h ^ (h >>> 16), 0x21f0aaad);
  h = Math.imul(h ^ (h >>> 15), 0x735a2d97);
  return ((h ^ (h >>> 15)) >>> 0) / 4294967296;
}

// Nearest timestamp in a grid: beats.json beats/hits, or vo.json word starts.
export const snap = (t, grid) =>
  grid.reduce((best, x) => (Math.abs(x - t) < Math.abs(best - t) ? x : best), grid[0]);

// GSAP eases by name, so a film can replay an ease measured from a reference
// (graphics.py emits none, power1-4.out/.in/.inOut, expo.out, sine.inOut, back.out(s)).
// ease("power2.out", t): t clamped to [0,1]. Bare "power2" means .out, as in GSAP.
// Families: none/linear/power0-4, quad/cubic/quart/quint/strong, sine, expo, circ,
// back(overshoot=1.7), elastic(amp=1, period=0.3), bounce.
const POW = { none: 0, linear: 0, power0: 0, power1: 1, quad: 1, power2: 2, cubic: 2, power3: 3, quart: 3, power4: 4, quint: 4, strong: 4 };
const bounceOut = (t) => {
  const n = 7.5625, d = 2.75;
  if (t < 1 / d) return n * t * t;
  if (t < 2 / d) return n * (t -= 1.5 / d) * t + 0.75;
  if (t < 2.5 / d) return n * (t -= 2.25 / d) * t + 0.9375;
  return n * (t -= 2.625 / d) * t + 0.984375;
};
// Each family builds its .in; out/inOut are derived or given where GSAP's differ.
const FAMILY = {
  sine: { in: (t) => 1 - Math.cos(t * Math.PI / 2), out: (t) => Math.sin(t * Math.PI / 2), inOut: (t) => -(Math.cos(Math.PI * t) - 1) / 2 },
  expo: { in: (t) => (t ? Math.pow(2, 10 * (t - 1)) : 0) },
  circ: { in: (t) => 1 - Math.sqrt(1 - t * t) },
  bounce: { out: bounceOut, in: (t) => 1 - bounceOut(1 - t) },
  back: (o = 1.7) => ({
    in: (t) => t * t * ((o + 1) * t - o),
    out: (t) => (t -= 1) * t * ((o + 1) * t + o) + 1,
  }),
  elastic: (a = 1, per = 0.3) => {
    const p1 = a >= 1 ? a : 1, p2 = per / (a < 1 ? a : 1), p3 = p2 / (2 * Math.PI) * (Math.asin(1 / p1) || 0), w = 2 * Math.PI / p2;
    const o = (t) => (t === 1 ? 1 : p1 * Math.pow(2, -10 * t) * Math.sin((t - p3) * w) + 1);
    return {
      out: o,
    };
  },
};
export function ease(name, t) {
  const m = /^\s*([a-z0-9]+)(?:\.(in|out|inout))?\s*(?:\(([^)]*)\))?\s*$/i.exec(String(name));
  const fam = m && m[1].toLowerCase();
  const dir = (m && m[2] ? m[2].toLowerCase() : 'out').replace('inout', 'inOut');
  const args = m && m[3] != null && m[3].trim() ? m[3].split(',').map(Number) : [];
  let f;
  if (fam && fam in POW) {
    const e = POW[fam] + 1;
    f = { in: (x) => Math.pow(x, e), out: (x) => 1 - Math.pow(1 - x, e), inOut: (x) => (x < 0.5 ? 0.5 * Math.pow(2 * x, e) : 1 - 0.5 * Math.pow(2 * (1 - x), e)) }[dir];
    if (POW[fam] === 0) f = (x) => x;
  } else if (fam && FAMILY[fam]) {
    const F = typeof FAMILY[fam] === 'function' ? FAMILY[fam](...(fam === 'elastic' && dir === 'inOut' && args[1] == null ? [args[0], 0.45] : args)) : FAMILY[fam];
    // GSAP derives what a family lacks: from .in (out = 1-in(1-t)) or from .out (elastic).
    const { in: inn, out: outf } = F;
    const o = outf || ((x) => 1 - inn(1 - x));
    const i = inn || ((x) => 1 - o(1 - x));
    f = F[dir] || (dir === 'out' ? o : dir === 'in' ? i
      : (x) => (x < 0.5 ? (1 - o(1 - 2 * x)) / 2 : 0.5 + o(2 * x - 1) / 2));
  }
  if (!f || args.some(Number.isNaN)) throw new Error('unknown ease: ' + name);
  const x = clamp(t);
  return x === 0 ? 0 : x === 1 ? 1 : f(x);
}

// Value at time t of an ease from `from` to `to`, starting at `start` for `dur` seconds.
// Holds before and after. No state, so any frame can be drawn directly.
export const tween = (t, start, dur, from, to, name = 'power3.out') =>
  from + (to - from) * (dur > 0 ? ease(name, (t - start) / dur) : t >= start ? 1 : 0);

// node lib/motion.js  -> self-check
if (typeof process !== 'undefined' && process.argv?.[1]?.includes('motion.js')) {
  const ok = (cond, msg) => {
    if (!cond) { console.error('FAIL ' + msg); process.exit(1); }
    console.log('ok  ' + msg);
  };
  ok(spring(0) === 0, 'spring starts at rest');
  ok(spring(5) > 0.999, 'spring settles on target');
  ok(spring(0.2, 170, 14) > spring(0.2, 170, 26), 'lower damping moves sooner');
  ok(track(0, [[0, 42]]) === 42, 'single key holds its value');
  ok(Math.abs(track(5, [[0, 0], [0.4, 100]]) - 100) < 0.1, 'track reaches the last target');
  ok(Math.abs(track(9, [[0, 0], [0.4, 100], [1, 30]]) - 30) < 0.1, 'stacked springs land on the final target');
  ok(noise(1) === noise(1) && noise(1) !== noise(2), 'noise is deterministic and varies');
  ok(snap(1.2, [0, 1, 2]) === 1, 'snap picks the nearest grid point');
  const names = ['none', 'linear', 'power0', 'power1', 'power2', 'power3', 'power4', 'quad', 'cubic', 'quart', 'quint', 'strong', 'sine', 'expo', 'circ', 'back', 'elastic', 'bounce', 'back.out(1.7)', 'back.in(2)', 'elastic.out(1,0.3)']
    .flatMap((n) => (/\.|\(/.test(n) ? [n] : [n, n + '.in', n + '.out', n + '.inOut']));
  ok(names.every((n) => ease(n, 0) === 0 && ease(n, 1) === 1), 'every ease name hits 0 and 1 (' + names.length + ' names)');
  ok(Math.abs(ease('power2.out', 0.5) - 0.875) < 1e-9 && Math.abs(ease('power2.in', 0.5) - 0.125) < 1e-9, 'power2 is cubic in GSAP: out(0.5)=0.875, in(0.5)=0.125');
  ok(Math.abs(ease('power1.out', 0.5) - 0.75) < 1e-9 && Math.abs(ease('quad.in', 0.5) - 0.25) < 1e-9, 'power1.out(0.5)=0.75, quad.in(0.5)=0.25');
  ok(Math.abs(ease('power2', 0.3) - ease('power2.out', 0.3)) < 1e-12, 'bare name means .out');
  ok([0.1, 0.3, 0.45].every((x) => Math.abs(ease('power2.inOut', x) + ease('power2.inOut', 1 - x) - 1) < 1e-9), 'power2.inOut is symmetric');
  ok(Array.from({ length: 99 }, (_, i) => ease('back.out(1.7)', (i + 1) / 100)).some((v) => v > 1), 'back.out overshoots above 1');
  ok(ease('expo.out', 0) === 0, 'expo.out(0) is 0');
  ok(ease('power3.in', 0.5) < 0.5 && ease('power3.out', 0.5) > 0.5, 'in is slow start, out is fast start');
  ok((() => { try { ease('wobble.out', 0.5); } catch (e) { return /wobble/.test(e.message); } })(), 'unknown ease throws with the name');
  ok(tween(-1, 1, 2, 10, 20, 'none') === 10 && tween(9, 1, 2, 10, 20, 'none') === 20 && tween(2, 1, 2, 10, 20, 'none') === 15, 'tween holds before and after, lerps inside');
}
