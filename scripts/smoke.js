// Sanity check: the inline script in docs/index.html parses and runs without throwing.
// node scripts/smoke.js
const fs = require('fs');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'index.html'), 'utf8');
const m = html.match(/<script>([\s\S]*)<\/script>/);
if (!m) { console.error('no <script> found'); process.exit(1); }
const js = m[1];

function makeEl() {
  return {
    innerHTML: '', id: '', textContent: '', style: {}, offsetWidth: 0, offsetHeight: 0,
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
new Function(js)();
console.log('SMOKE TEST PASSED');
