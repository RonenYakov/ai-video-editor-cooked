// The home page keeps what you were doing across a refresh. Before this, keepView() was called only on
// the server-driven reload, so F5 (or a back, or a tab change) dropped everything typed, and even that
// one path saved no draft, assets, script or clips. No browser: the function is read out of the page and
// run against a fake sessionStorage.
import {readFileSync} from 'node:fs'
import assert from 'node:assert'

const html = readFileSync(new URL('../plugins/ai-editor/lib/ai_editor/home.html', import.meta.url), 'utf8')

// a real page-leave has to save, not only the version-change reload
assert.ok(html.includes("addEventListener('pagehide',keepView)"), 'pagehide must save the view')
assert.ok(html.includes("addEventListener('beforeunload',keepView)"), 'beforeunload must save the view too')

const i = html.indexOf('function keepView(){')
const j = html.indexOf('\ntry{const k=JSON.parse', i)
assert.ok(i > 0 && j > i, 'keepView not found in the page')
const src = html.slice(i, j)
const make = new Function('rv', 'ui', 'nv', 'scrollY', 'sessionStorage', src + '; return keepView')

const work = () => ({
  sel: ['take.mov'], style: 'mine', aspect: '9:16', aspectSet: true, join: true,
  draft: 'what the video must cover', script: 'a line', scriptName: 'script.md', clips: {'take.mov': [1, 2]},
  filter: 'all', assets: [{kind: 'link', url: 'https://myshop.co', say: 'our brand'},
                          {kind: 'image', data: 'data:image/png;base64,AAAA', name: 'logo.png', say: 'the logo'}],
})
const store = (box, failFirst = false) => {
  let n = 0
  return {setItem: (k, v) => { if (failFirst && ++n === 1) throw new Error('QuotaExceededError'); box[k] = v },
          getItem: k => (k in box ? box[k] : null), removeItem: k => { delete box[k] }}
}

// everything the user put in comes back
let box = {}
make('home', {sp: 2, pslug: 'my-talk'}, work(), 140, store(box))()
let k = JSON.parse(box['ave-home-keep'])
assert.equal(k.nv.draft, 'what the video must cover', 'the typed brief must survive a refresh')
assert.equal(k.nv.script, 'a line')
assert.equal(k.nv.scriptName, 'script.md')
assert.deepEqual(k.nv.clips, {'take.mov': [1, 2]})
assert.equal(k.nv.assets.length, 2, 'references must survive a refresh')
assert.equal(k.nv.assets[1].data, 'data:image/png;base64,AAAA')
assert.equal(k.rv, 'home')
assert.equal(k.ps, 'my-talk')
assert.equal(k.y, 140)

// a pasted image can blow the quota: the words and links still have to be kept
box = {}
make('home', {sp: 2, pslug: 'my-talk'}, work(), 0, store(box, true))()
k = JSON.parse(box['ave-home-keep'])
assert.equal(k.nv.draft, 'what the video must cover', 'the brief must survive the quota fallback')
assert.equal(k.nv.assets[0].url, 'https://myshop.co', 'a link costs nothing: keep it')
assert.equal(k.nv.assets[1].data, '', 'only the picture data is dropped')
assert.equal(k.nv.assets[1].say, 'the logo', 'and its note is kept')

console.log('home keep ok')
