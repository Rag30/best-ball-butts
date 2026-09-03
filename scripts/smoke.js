// Sanity check: the page script parses and renders the derived data without throwing.
//   node scripts/smoke.js
const fs = require('fs');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'worker', 'public', 'index.html'), 'utf8');
const m = html.match(/<script>([\s\S]*)<\/script>/);
if (!m) { console.error('no <script> found'); process.exit(1); }
const snapshot = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'derived', 'seasons.json'), 'utf8'));

function makeEl() {
  return {
    innerHTML: '', id: '', textContent: '', style: {}, offsetWidth: 0, offsetHeight: 0, disabled: false,
    classList: { add(){}, remove(){}, toggle(){}, contains(){ return false; } },
    dataset: {}, querySelectorAll() { return []; }, addEventListener() {},
    appendChild() {}, closest() { return null; }, contains() { return false; },
  };
}
global.window = { innerWidth: 1200, innerHeight: 800 };
global.document = {
  body: makeEl(), getElementById() { return makeEl(); }, querySelectorAll() { return []; },
  createElement() { return makeEl(); }, addEventListener() {},
};
global.location = { protocol: 'https:', hostname: 'bestballbutts.rrr-projects.com' };
global.fetch = async (url) => ({ ok: true, status: 200, json: async () => (String(url).endsWith('/data') ? snapshot : { ok: true }) });

process.on('unhandledRejection', e => { console.error('SMOKE FAILED:', e); process.exit(1); });
new Function(m[1])();
setTimeout(() => console.log('SMOKE TEST PASSED'), 300);   // let the async load + render run
