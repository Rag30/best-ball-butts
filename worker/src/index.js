// bestballbutts.rrr-projects.com — the whole site in one Worker.
//
//   GET  /            static page (worker/public/index.html, uploaded by `wrangler deploy`)
//   GET  /data        the computed league tables, read from KV            (page loads this)
//   POST /refresh     Sleeper -> compute.js -> KV, for every non-frozen season (Refresh button)
//   cron              same as /refresh: every 5 min on NFL game days, hourly otherwise
//
// KV keys:  season:<yr>  computed season (frozen once league status is "complete")
//           proj:<yr>:<wk>  per-week team projection totals (tiny; the 1.5 MB player file is
//                           only fetched for the current week)
//           snapshot     {seasons, career, generatedAt} — exactly what the page renders
//           lastRefresh  epoch ms, for the cooldown
// No credentials anywhere: Sleeper is public, KV is bound to this Worker.

import BBB from "../../scripts/compute.js";

const USERNAME = "raghavr7";
const LEAGUE_NAME = "Best Ball Butts";
const FIRST_SEASON = 2024;
const API = "https://api.sleeper.app";
const POS = ["QB", "RB", "WR", "TE", "K", "DEF"].map(p => "position[]=" + p).join("&");
const COOLDOWN_MS = 45 * 1000;
const ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=";

const json = (obj, status = 200, extra = {}) =>
  new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store", ...extra } });

async function getJson(url) {
  const r = await fetch(url, { headers: { "User-Agent": "bbb-worker" } });
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}

/** season -> league_id for every season of this league (cached in KV for a day). */
async function discoverLeagues(env, currentSeason) {
  const cached = await env.DATA.get("leagues", "json");
  if (cached && cached.through === currentSeason && Date.now() - cached.at < 86_400_000) return cached.map;
  const user = await getJson(`${API}/v1/user/${USERNAME}`);
  const map = {};
  for (let s = FIRST_SEASON; s <= currentSeason; s++) {
    for (const lg of (await getJson(`${API}/v1/user/${user.user_id}/leagues/nfl/${s}`)) || []) {
      if (lg.name === LEAGUE_NAME) map[String(s)] = lg.league_id;
    }
  }
  await env.DATA.put("leagues", JSON.stringify({ map, through: currentSeason, at: Date.now() }));
  return map;
}

/** Fetch + compute one season. Uses cached per-week projection totals except for `liveWeek`. */
async function computeSeason(env, yr, leagueId, currentWeek) {
  const [league, users, rosters, bracket] = await Promise.all([
    getJson(`${API}/v1/league/${leagueId}`), getJson(`${API}/v1/league/${leagueId}/users`),
    getJson(`${API}/v1/league/${leagueId}/rosters`), getJson(`${API}/v1/league/${leagueId}/winners_bracket`),
  ]);
  const lastReg = BBB.lastRegularWeek(league);
  const upTo = currentWeek == null ? lastReg : Math.min(lastReg, currentWeek);
  const matchupsByWeek = {};
  const fetched = await Promise.all(Array.from({ length: upTo }, (_, i) => getJson(`${API}/v1/league/${leagueId}/matchups/${i + 1}`)));
  fetched.forEach((m, i) => matchupsByWeek[i + 1] = m);

  // Team projection totals per week: cached; only the live (latest scored) week is refetched.
  const scored = Object.keys(matchupsByWeek).map(Number).filter(w => BBB.weekHasScores(matchupsByWeek[w]));
  const liveWeek = scored.length ? Math.max(...scored) : null;
  const projected = {};
  for (const w of scored) {
    const key = `proj:${yr}:${w}`;
    let tp = w === liveWeek ? null : await env.DATA.get(key, "json");
    if (!tp) {
      const players = await getJson(`${API}/projections/nfl/${yr}/${w}?season_type=regular&${POS}`);
      tp = BBB.weekTeamProjections(players, matchupsByWeek[w], league);
      await env.DATA.put(key, JSON.stringify(tp));
    }
    for (const r in tp) (projected[r] ??= {})[w] = tp[r];
  }
  // Re-run the pure pipeline with the (cached) projections instead of raw player files
  const nameMap = BBB.nameMapFrom(users, rosters);
  const meta = { leagueId: league.league_id, status: league.status, rosterPositions: league.roster_positions,
                 scoring: league.scoring_settings, nameMap, lastRegularWeek: lastReg };
  if (!scored.length) {
    return { notStarted: true, status: league.status, managers: Object.keys(nameMap).sort((a, b) => a - b).map(r => nameMap[r]), meta };
  }
  const input = BBB.inputFromMatchups(matchupsByWeek, scored);
  const season = BBB.applyPlayoffs(BBB.buildSeason({ weeks: scored, nameMap, ...input, projected }), bracket, nameMap);
  season.meta = meta;
  return season;
}

async function refresh(env, { force = false, reason = "manual" } = {}) {
  const last = Number(await env.DATA.get("lastRefresh")) || 0;
  if (!force && Date.now() - last < COOLDOWN_MS) {
    return { ok: false, reason: "cooldown", retryInSeconds: Math.ceil((COOLDOWN_MS - (Date.now() - last)) / 1000) };
  }
  await env.DATA.put("lastRefresh", String(Date.now()));

  const state = await getJson(`${API}/v1/state/nfl`);
  const currentSeason = Number(state.season);
  const leagues = await discoverLeagues(env, currentSeason);

  const seasons = {};
  const updated = [];
  for (const yr of Object.keys(leagues).sort()) {
    const existing = await env.DATA.get(`season:${yr}`, "json");
    if (existing && existing.meta && existing.meta.status === "complete") { seasons[yr] = existing; continue; }  // frozen
    const currentWeek = Number(yr) === currentSeason ? Number(state.week || 1) : null;
    const season = await computeSeason(env, yr, leagues[yr], currentWeek);
    await env.DATA.put(`season:${yr}`, JSON.stringify(season));
    seasons[yr] = season; updated.push(yr);
  }
  const snapshot = { seasons, career: BBB.career(seasons), generatedAt: new Date().toISOString(),
                     nflWeek: state.week, nflSeason: state.season, reason };
  await env.DATA.put("snapshot", JSON.stringify(snapshot));
  return { ok: true, updated, generatedAt: snapshot.generatedAt };
}

/** Cron gate: 5-min cadence on NFL game days, hourly otherwise (America/New_York). */
async function shouldRunNow() {
  const et = new Date(new Date().toLocaleString("en-US", { timeZone: "America/New_York" }));
  const ymd = `${et.getFullYear()}${String(et.getMonth() + 1).padStart(2, "0")}${String(et.getDate()).padStart(2, "0")}`;
  let gameDay = true;
  try { gameDay = ((await getJson(ESPN + ymd)).events || []).length > 0; } catch (e) { /* assume game day */ }
  return gameDay || et.getMinutes() < 5;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/data") {
      const snap = await env.DATA.get("snapshot");
      return snap ? new Response(snap, { headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } })
                  : json({ error: "no data yet — press Refresh" }, 503);
    }
    if (url.pathname === "/refresh") {
      if (request.method !== "POST") return json({ error: "POST only" }, 405);
      try { const r = await refresh(env); return json(r, r.ok ? 200 : 429); }
      catch (e) { return json({ ok: false, reason: "error", message: String(e.message || e) }, 502); }
    }
    return env.ASSETS.fetch(request);   // static site
  },

  async scheduled(event, env, ctx) {
    if (!(await shouldRunNow())) return;
    ctx.waitUntil(refresh(env, { force: true, reason: "cron" }).catch(e => console.error("cron refresh failed", e)));
  },
};
