// Seed Cloudflare KV from the git archive: completed seasons are written once and frozen.
//   node scripts/compute-node.js && node scripts/seed-kv.js
// Uses the wrangler login on this machine; no tokens involved.
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");
const BBB = require("./compute.js");

const ROOT = path.resolve(__dirname, "..");
const derived = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "derived", "seasons.json"), "utf8"));
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "bbb-seed-"));

function put(key, value) {
  const f = path.join(tmp, key.replace(/[:/]/g, "_") + ".json");
  fs.writeFileSync(f, JSON.stringify(value));
  execFileSync("npx", ["--yes", "wrangler@4", "kv", "key", "put", "--binding", "DATA", "--remote", key, "--path", f],
    { cwd: path.join(ROOT, "worker"), stdio: ["ignore", "ignore", "inherit"] });
  console.log("put", key, `(${fs.statSync(f).size} bytes)`);
}

const only = process.argv.slice(2);   // optional: seasons to seed, default = all completed
for (const [yr, season] of Object.entries(derived.seasons)) {
  if (only.length && !only.includes(yr)) continue;
  if (!season.meta || season.meta.status !== "complete") { console.log("skip", yr, "(not complete)"); continue; }
  put(`season:${yr}`, season);
  // per-week projection totals so the Worker never needs the big player files for these seasons
  const byWeek = {};
  for (const [name, arr] of Object.entries(season.projected || {})) {
    const rid = Object.keys(season.meta.nameMap).find(r => season.meta.nameMap[r] === name);
    arr.forEach((v, i) => { if (v != null) (byWeek[season.weeks[i]] ??= {})[rid] = v; });
  }
  for (const [w, tp] of Object.entries(byWeek)) put(`proj:${yr}:${w}`, tp);
}
put("snapshot", { seasons: derived.seasons, career: BBB.career(derived.seasons), generatedAt: new Date().toISOString(), reason: "seed" });
console.log("done");
