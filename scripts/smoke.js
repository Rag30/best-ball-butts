// Sanity check: the page script parses and renders the derived data without throwing,
// for each kind of visitor the launcher can send — a public viewer, the owner, a guest
// with a few tabs (fed exactly what the Worker's trimToTabs() would give them), and a
// guest with no tabs at all (the "ask the owner" line).
//   python3 scripts/build.py && node scripts/smoke.js
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const html = fs.readFileSync(path.join(__dirname, '..', 'worker', 'public', 'index.html'), 'utf8');
const m = html.match(/<script>([\s\S]*)<\/script>/);
if (!m) { console.error('no <script> found'); process.exit(1); }
const latestRun = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'prediction', 'runs', 'index.json'), 'utf8')).editions[0];
const brief = { run: latestRun.run, week: latestRun.week, title: latestRun.title, hasPdf: true, editions: [latestRun],
  markdown: fs.readFileSync(path.join(__dirname, '..', 'prediction', 'runs', latestRun.brief), 'utf8') + '\n<script>alert(1)</script>\n' };
const snapshot = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'derived', 'seasons.json'), 'utf8'));

function makeEl(id = '') {
  const el = {
    innerHTML: '', id, textContent: '', style: {}, offsetWidth: 0, offsetHeight: 0, disabled: false, hidden: false, href: '',
    className: '', children: [],
    classList: { add(){}, remove(){}, toggle(){}, contains(){ return false; } },
    dataset: {}, querySelectorAll() { return []; }, addEventListener() {},
    appendChild(c) { el.children.push(c); return c; }, closest() { return null; }, contains() { return false; },
  };
  return el;
}
// One document per run, with stable elements per id so a scenario can look at what the page did.
function makeDoc() {
  const byId = new Map();
  const get = id => { if (!byId.has(id)) byId.set(id, makeEl(id)); return byId.get(id); };
  return { byId, doc: { body: makeEl('body'), getElementById: get, querySelectorAll() { return []; }, createElement: () => makeEl(), addEventListener() {} } };
}
const textOf = el => (el.textContent || '') + el.children.map(textOf).join('');

process.on('unhandledRejection', e => { console.error('SMOKE FAILED:', e); process.exit(1); });
process.on('uncaughtException', e => { console.error('SMOKE FAILED:', e); process.exit(1); });

async function run(name, me, data, check) {
  const { byId, doc } = makeDoc();
  const calls = [];
  global.window = { innerWidth: 1200, innerHeight: 800 };
  global.document = doc;
  global.location = { protocol: 'https:', hostname: 'bestballbutts.rrr-projects.com' };
  global.fetch = async (url) => {
    const u = String(url); calls.push(u);
    if (u.endsWith('/.rrr/me')) return me === null ? { ok: false, status: 404, json: async () => ({}) } : { ok: true, status: 200, json: async () => me };
    if (u.endsWith('/brief')) return { ok: true, status: 200, json: async () => brief };
    if (u.endsWith('/data')) return { ok: true, status: 200, json: async () => data };
    return { ok: true, status: 200, json: async () => ({ ok: true }) };
  };
  new Function(m[1])();
  await new Promise(r => setTimeout(r, 300));   // let the async load + render run
  // The page reports a render failure into #liveStatus rather than throwing; treat that as a failure too.
  const status = byId.has('liveStatus') ? byId.get('liveStatus').textContent : '';
  try {
    if (/Could not load data|failed/i.test(status)) throw new Error(`page reported: ${status}`);
    check({ byId, calls });
  }
  catch (e) { console.error(`SMOKE FAILED (${name}):`, e.message); process.exit(1); }
  console.log(`ok  ${name}`);
}

(async () => {
  const { trimToTabs } = await import(pathToFileURL(path.join(__dirname, '..', 'worker', 'src', 'index.js')).href);
  const owner = { email: 'owner@example.com', name: 'Owner', role: 'write', tabs: ['standings', 'luck', 'luck-net', 'luck-schedule', 'luck-roster', 'luck-sos', 'reports', 'brief'] };
  const guest = tabs => ({ email: 'guest@example.com', name: 'Guest', role: 'read', tabs });
  const rendered = ({ byId }) => {
    if (!byId.get('season-career').innerHTML.includes('All-Time Standings')) throw new Error('career panel did not render');
    if (!byId.get('2025-standings') && !byId.get('2025-ui3') && !byId.get('2025-reports')) throw new Error('no 2025 panel was rendered');
  };

  await run('public viewer: everything, no Refresh button', { public: true }, snapshot, s => {
    rendered(s);
    const b = s.byId.get('season-brief').innerHTML;
    if (s.byId.get('briefBtn').hidden) throw new Error('Weekly Brief tab should show for a public viewer');
    for (const want of ['<h1>', '<table>', '<li>', '/brief.pdf?run=' + latestRun.run]) if (!b.includes(want)) throw new Error(`brief panel lacks ${want}`);
    if (b.includes('<script>')) throw new Error('brief markdown was not escaped');
    if (!s.byId.get('refreshBtn').hidden) throw new Error('Refresh button should be hidden for a public viewer');
  });
  await run('no /.rrr/me at all (dev server): everything', null, snapshot, rendered);
  await run('owner: everything, Refresh button shown', owner, snapshot, s => {
    rendered(s);
    if (s.byId.get('refreshBtn').hidden) throw new Error('Refresh button should show for role write');
  });
  for (const tabs of [['standings'], ['luck', 'luck-net'], ['luck', 'luck-sos'], ['luck', 'luck-schedule', 'luck-roster'], ['reports']]) {
    await run(`guest with ${JSON.stringify(tabs)} renders the trimmed feed`, guest(tabs), trimToTabs(snapshot, tabs), s => {
      if (!s.byId.get('refreshBtn').hidden) throw new Error('Refresh button should be hidden for role read');
      if (!s.byId.has('season-2025')) throw new Error('2025 season panel was not built');
      if (s.calls.some(u => u.includes('/brief'))) throw new Error('/brief was fetched without the brief tab');
      if (!s.byId.get('briefBtn').hidden) throw new Error('Weekly Brief tab should be hidden without the brief tab');
    });
  }
  await run('guest with no tabs: the ask-the-owner line, and /data is never asked for', guest([]), snapshot, s => {
    if (s.calls.some(u => u.endsWith('/data'))) throw new Error('/data was fetched for a no-tab guest');
    const text = textOf(s.byId.get('season-career'));
    for (const want of ['guest@example.com', 'ask the owner', 'rrr-projects.com']) if (!text.includes(want)) throw new Error(`no-access line lacks "${want}": ${text}`);
    if (!s.byId.get('seasonTabs').hidden) throw new Error('season tabs should be hidden');
  });
  console.log('SMOKE TEST PASSED');
})();
