// A measured style.json / refs/<id>.json -> the few things a film adapts. Pure, browser-safe,
// never throws on a sparse style (a photo-only ref has no pace or entrances).

const num = (x) => (typeof x === 'number' && Number.isFinite(x) ? x : null);
const moves = (list) =>
  (Array.isArray(list) ? list : [])
    .filter((m) => m && typeof m === 'object')
    .map((m) => ({ kind: m.kind ?? 'cut', ease: m.ease ?? 'none', dur: num(m.duration_s) ?? 0 }));

export function fromStyle(style) {
  const s = style && typeof style === 'object' ? style : {};
  const g = s.graphics && typeof s.graphics === 'object' ? s.graphics : {};
  const p = s.pace && typeof s.pace === 'object' ? s.pace : {};
  const per10 = num(p.cuts_per_10s);
  const med = num(p.median_shot_s);
  const cutEvery = per10 > 0 ? 10 / per10 : med > 0 ? med : null;
  const palette = (Array.isArray(g.palette) ? g.palette : [])
    .map((c) => (typeof c === 'string' ? c : c?.hex))
    .filter((h) => typeof h === 'string' && h);
  return {
    entrances: moves(g.entrances),
    exits: moves(g.exits),
    cutEvery,
    zoom: s.zoom && typeof s.zoom === 'object' ? s.zoom : null,
    palette,
    grade: s.grade && typeof s.grade === 'object' ? s.grade : null,
  };
}

// node lib/style.js  -> self-check
if (typeof process !== 'undefined' && process.argv?.[1]?.includes('style.js')) {
  const ok = (cond, msg) => {
    if (!cond) { console.error('FAIL ' + msg); process.exit(1); }
    console.log('ok  ' + msg);
  };
  const full = fromStyle({
    pace: { cuts_per_10s: 4, median_shot_s: 2.4 },
    zoom: { kind: 'punch', scale: 1.18 },
    graphics: {
      entrances: [{ kind: 'slide', ease: 'power3.out', duration_s: 0.4 }],
      exits: [{ kind: 'fade', ease: 'power2.in', duration_s: 0.2 }],
      palette: [{ hex: '#112233', pct: 40 }, '#ffffff'],
    },
    grade: { saturation: 0.3 },
  });
  ok(full.cutEvery === 2.5, 'cutEvery from cuts_per_10s');
  ok(full.entrances[0].ease === 'power3.out' && full.entrances[0].dur === 0.4, 'entrance mapped');
  ok(full.exits[0].kind === 'fade', 'exit mapped');
  ok(full.palette.join() === '#112233,#ffffff', 'palette hexes');
  ok(full.zoom.scale === 1.18 && full.grade.saturation === 0.3, 'zoom and grade pass through');
  const sparse = fromStyle({ graphics: { palette: [{ hex: '#abcdef' }] }, pace: { cuts_per_10s: 0 } });
  ok(sparse.cutEvery === null && sparse.entrances.length === 0 && sparse.grade === null, 'sparse style is tolerated');
  ok(fromStyle(null).cutEvery === null && fromStyle(undefined).palette.length === 0, 'null style does not throw');
}
