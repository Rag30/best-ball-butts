// data/raw -> data/derived/seasons.json using the same math the page runs live.
//   node scripts/compute-node.js
const fs = require("fs");
const path = require("path");
const BBB = require("./compute.js");

const ROOT = path.resolve(__dirname, "..");
const RAW = path.join(ROOT, "data", "raw");
const OUT = path.join(ROOT, "data", "derived", "seasons.json");
const readJson = p => JSON.parse(fs.readFileSync(p, "utf8"));
const maybe = p => (fs.existsSync(p) ? readJson(p) : null);

const seasons = {};
const generatedFrom = {};
for (const season of fs.readdirSync(RAW).filter(d => fs.existsSync(path.join(RAW, d, "league.json"))).sort()) {
  const dir = path.join(RAW, season);
  const league = readJson(path.join(dir, "league.json"));
  const matchupsByWeek = {}, projectionsByWeek = {};
  for (let w = 1; w <= BBB.lastRegularWeek(league); w++) {
    const ww = String(w).padStart(2, "0");
    const m = maybe(path.join(dir, "matchups", `week_${ww}.json`));
    if (m) matchupsByWeek[w] = m;
    const p = maybe(path.join(dir, "projections", `week_${ww}.json`));
    if (p) projectionsByWeek[w] = p;
  }
  seasons[season] = BBB.seasonFromRaw({
    league, users: readJson(path.join(dir, "users.json")), rosters: readJson(path.join(dir, "rosters.json")),
    bracket: maybe(path.join(dir, "winners_bracket.json")) || [], matchupsByWeek, projectionsByWeek,
    draftPicks: maybe(path.join(dir, "draft_picks.json")),
  });
  generatedFrom[season] = seasons[season].weeks || [];
}

const out = { seasons, career: BBB.career(seasons), generatedFrom, generatedAt: new Date().toISOString() };
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
console.log("wrote", path.relative(ROOT, OUT), fs.statSync(OUT).size, "bytes;",
  Object.fromEntries(Object.entries(generatedFrom).map(([s, w]) => [s, w.length])), "scored weeks");
