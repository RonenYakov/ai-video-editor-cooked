// Pure: a measured grade block (creator-teardown grade.py) -> an ffmpeg filter chain.
// node lib/grade.mjs  -> self-check
//
// Gentle on purpose, the film is already designed; this only nudges it toward the reference.
//  levels      colorlevels: output black/white points from grade.black / grade.white
//              (black clamped 0..0.2, white 0.8..1, so a crushed or blown ref cannot wreck the film).
//  saturation  eq=saturation = 1 + 1.2 * (grade.saturation - 0.35), clamped 0.6..1.4.
//              0.35 is the neutral HSV mean of an ordinary render.
//  split tone  colorbalance: a hue (degrees) becomes an RGB direction (cos at 0/120/240, zero mean),
//              scaled to at most 0.08, on shadows (shadow_hue) and highlights (highlight_hue).
//              A null hue is skipped.
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const num = (x) => (typeof x === 'number' && Number.isFinite(x) ? x : null);
const f = (x) => String(+x.toFixed(4));

function tint(hue, amount = 0.08) {
  const r = (a) => Math.cos(((hue - a) * Math.PI) / 180);
  const v = [r(0), r(120), r(240)];
  const m = Math.max(...v.map(Math.abs)) || 1;
  return v.map((x) => clamp((x / m) * amount, -amount, amount));
}

export function gradeFilter(grade) {
  if (!grade || typeof grade !== 'object') return '';
  const out = [];
  const black = num(grade.black), white = num(grade.white);
  if (black !== null || white !== null) {
    const lo = clamp(black ?? 0, 0, 0.2), hi = clamp(white ?? 1, 0.8, 1);
    // planar first: ffmpeg 8.1 colorlevels crashes (access violation) on the packed rgb24 the PNG pipe gives
    out.push('format=gbrp,colorlevels=romin=' + f(lo) + ':romax=' + f(hi) + ':gomin=' + f(lo) + ':gomax=' + f(hi) + ':bomin=' + f(lo) + ':bomax=' + f(hi));
  }
  const sat = num(grade.saturation);
  if (sat !== null) out.push('eq=saturation=' + f(clamp(1 + 1.2 * (sat - 0.35), 0.6, 1.4)));
  const sh = num(grade.shadow_hue), hl = num(grade.highlight_hue);
  if (sh !== null || hl !== null) {
    const [rs, gs, bs] = sh !== null ? tint(sh) : [0, 0, 0];
    const [rh, gh, bh] = hl !== null ? tint(hl) : [0, 0, 0];
    out.push('colorbalance=rs=' + f(rs) + ':gs=' + f(gs) + ':bs=' + f(bs) + ':rh=' + f(rh) + ':gh=' + f(gh) + ':bh=' + f(bh));
  }
  return out.join(',');
}

if (typeof process !== 'undefined' && process.argv?.[1]?.includes('grade.mjs')) {
  const ok = (cond, msg) => {
    if (!cond) { console.error('FAIL ' + msg); process.exit(1); }
    console.log('ok  ' + msg);
  };
  ok(gradeFilter(null) === '' && gradeFilter({}) === '', 'no grade -> empty string');
  ok(+/rh=(-?[\d.]+)/.exec(gradeFilter({ highlight_hue: 30 }))[1] > 0, 'warm highlight -> positive red highlight balance');
  ok(+/bs=(-?[\d.]+)/.exec(gradeFilter({ shadow_hue: 200 }))[1] > 0, 'cool shadow -> positive blue shadow balance');
  ok(+/saturation=([\d.]+)/.exec(gradeFilter({ saturation: 0.2 }))[1] < 1, 'low saturation -> eq saturation < 1');
  ok(!gradeFilter({ shadow_hue: null, highlight_hue: null }).includes('colorbalance'), 'null hues skip colorbalance');
  ok(gradeFilter({ black: 0.9, white: 0.1 }).includes('romin=0.2:romax=0.8'), 'levels are clamped');
}
