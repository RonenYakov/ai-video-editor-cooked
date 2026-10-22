// The Edit and Motion project pages are a room (chat + one Materials panel), not a step ladder; talking-head
// keeps its steps; the home page has a Finished videos button. No browser: the page functions are read out of
// home.html and run with small stand-ins for what they touch.
import {readFileSync} from 'node:fs'
import assert from 'node:assert'

const html = readFileSync(new URL('../plugins/ai-editor/lib/ai_editor/home.html', import.meta.url), 'utf8')
const lines = html.split('\n')
// one top-level definition: a one-liner, or from "function x(" to the closing "}" at column 0
const grab = name => {
  const i = lines.findIndex(l => l.startsWith(`function ${name}(`) || l.startsWith(`async function ${name}(`) || l.startsWith(`const ${name}=`))
  assert.ok(i >= 0, name + ' not found in the page')
  if (!/\{\s*$/.test(lines[i])) return lines[i]
  let j = i + 1; while (lines[j] !== '}') j++
  return lines.slice(i, j + 1).join('\n')
}
const names = ['PH_STEP', 'esc', 'J', 'base', 'isLink', 'shortLink', 'newestEdit', 'isRun', 'fileRow', 'editRow', 'upRows', 'pjBtn', 'refsBody', 'creatorPick',
  'pjPlan', 'pjSteps', 'vProject', 'isRoom', 'matSec', 'rmBtn', 'isHandle', 'roomMats', 'finBtn', 'vHome']
const src = names.map(grab).join('\n')
const env = {
  S: {jobs: [], finished: {path: '/f', count: 3}}, L: {videos: [{}, {}], styles: []}, PJ: [], nv: {up: []}, ui: {},
  ic: () => '', CROSS: 'x', vPh: () => '', vStat: () => ({txt: 'ok'}), farStep: () => null, clipOf: () => ({}), styleName: s => s, dname: c => c.id,
  jobCard: () => '', kindOf: k => ({name: k, ico: 'x'}), pjJobProject: () => '', KINDS: [], kindCard: () => '', pjRow: () => '', firstRun: () => false, gsDone: () => true,
  obView: () => '', firstVideoHome: () => '', $: () => null,
}
const keys = Object.keys(env)
const run = new Function(...keys, src + '; return {vProject, vHome, setUi: u => Object.assign(ui, u)}')(...keys.map(k => env[k]))
const page = (kind, extra = {}) => {
  env.ui.pslug = 'p1'
  env.ui.pj = {project: {slug: 'p1', name: 'My project', kind, sources: ['/v/a.mp4'], refs: ['https://x.co/r', '/tmp/pic.png'], status: '', ...extra}, edits: [{name: 'cut one', dir: '/lib/e1'}]}
  return run.vProject()
}

for (const kind of ['edit', 'motion']) {
  const h = page(kind)
  assert.ok(!h.includes('ol class="stp"'), kind + ' must not draw the step ladder')
  assert.ok(h.includes('aria-label="Materials"'), kind + ' must show the Materials panel')
  for (const w of ['References', 'Brief', 'Results', 'Open finished folder', 'Open review']) assert.ok(h.includes(w), kind + ' room lacks ' + w)
  assert.ok(h.includes("pjUnlink(&quot;refs&quot;,&quot;https://x.co/r&quot;)"), kind + ' refs must be removable')
  assert.ok(!h.includes('Write the brief'), kind + ' must not ask for a brief first')
}
const edit = page('edit'), motion = page('motion')
assert.ok(edit.includes('Footage') && edit.includes('Optional'), 'edit has Footage and an Optional label')
assert.ok(!motion.includes('Footage'), 'motion has no Footage section')
assert.ok(motion.includes('Add references, then tell Claude what you want in a line.'), 'motion hint')
assert.ok(motion.indexOf('References') < motion.indexOf('Brief'), 'references come first on motion')

const th = page('talking-head')
assert.ok(th.includes('ol class="stp"'), 'talking-head keeps its steps')
assert.ok(!th.includes('aria-label="Materials"'), 'talking-head has no room')

const home = run.vHome()
assert.ok(home.includes('id="fin-btn"') && home.includes('openFinished()'), 'home has the Finished videos button')
assert.ok(home.includes('Finished videos (3)'), 'the count comes from the state')
env.S.finished = undefined
assert.ok(run.vHome().includes('Finished videos') && !run.vHome().includes('Finished videos ('), 'no count when the state has none')

// the chat is mounted once, outside #main, so a repaint cannot remove it; the placeholder differs per kind
assert.ok(html.includes("ROOMPH={edit:'Tell Claude what to do with your footage',motion:'Say what you want. One line is enough.'}"), 'placeholders')
assert.ok(html.includes('<aside id="chatdock"') && html.indexOf('<aside id="chatdock"') > html.indexOf('</main>'), 'the chat dock stays outside #main')
// an unsent brief survives a refresh
assert.ok(/keepView\(\)\{[^\n]*noteDraft:nv\.noteDraft/.test(html), 'keepView saves the brief draft')
console.log('room ok')
