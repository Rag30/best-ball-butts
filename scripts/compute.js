/* Best Ball Butts — all league math in one place.
 *
 * Runs in two places with the same code:
 *   - Node (scripts/compute-node.js): data/raw -> data/derived/seasons.json   (archive)
 *   - Browser (docs/index.html): archive + live Sleeper fetch -> recompute      (refresh)
 *
 * Everything is a pure function of its inputs. No I/O in this file.
 */
const BBB = (() => {
  // Sleeper display name -> the name the league actually uses
  const MANAGERS = {
    plankrad: "Conrad", bballlauren: "Lauren", lilmisseb: "Emma", Raghavr7: "Raghav",
    "1babyjesus": "Steve", averymc03: "Avery", mac003: "Avery",
    dragonslayyyer69: "Ben", NoLsHere: "Noelle", TheDragon96: "Henry",
  };
  // Career stats are per person. Seat 5 was Steve (2024) then Avery (2025+): different people, kept separate.
  const CAREER_ALIAS = {};
  const FLEX = new Set(["RB", "WR", "TE"]);
  const NON_FLIP_WEIGHT = 0.35;

  const r2 = x => Math.round((x + Number.EPSILON) * 100) / 100;
  const sign = x => (x > 0) - (x < 0);
  const mean = a => a.reduce((s, v) => s + v, 0) / a.length;
  const pstdev = a => { const m = mean(a); return Math.sqrt(mean(a.map(v => (v - m) ** 2))); };
  const median = a => { const s = [...a].sort((x, y) => x - y); const n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };
  const argmax = (obj, keys) => keys.reduce((b, k) => (b === null || obj[k] > obj[b] ? k : b), null);
  const argmin = (obj, keys) => keys.reduce((b, k) => (b === null || obj[k] < obj[b] ? k : b), null);

  // ---------- projections ----------
  function playerPts(stats, scoring) {
    let t = 0;
    for (const k in stats) if (k in scoring && typeof stats[k] === "number") t += scoring[k] * stats[k];
    return t;
  }
  function optimalLineup(byPid, rosterPids, slots) {
    const pool = rosterPids.map(pid => byPid[pid] && [byPid[pid].pts, byPid[pid].pos, pid]).filter(Boolean)
      .sort((a, b) => b[0] - a[0] || (a[1] < b[1] ? 1 : -1));
    const used = new Set(); let total = 0;
    for (const s of slots.filter(s => s !== "FLEX" && s !== "BN")) {
      for (const [pts, pos, pid] of pool) if (!used.has(pid) && pos === s) { used.add(pid); total += pts; break; }
    }
    for (const _ of slots.filter(s => s === "FLEX")) {
      for (const [pts, pos, pid] of pool) if (!used.has(pid) && FLEX.has(pos)) { used.add(pid); total += pts; break; }
    }
    return r2(total);
  }
  /** {rosterId: projectedPts} for one week from a projections payload + that week's matchups. */
  function weekTeamProjections(projections, matchups, league) {
    const scoring = league.scoring_settings, slots = league.roster_positions;
    const byPid = {};
    for (const e of projections) byPid[e.player_id] = { pts: playerPts(e.stats || {}, scoring), pos: (e.player || {}).position };
    const out = {};
    for (const e of matchups) out[e.roster_id] = optimalLineup(byPid, e.players || [], slots);
    return out;
  }

  // ---------- league helpers ----------
  function nameMapFrom(users, rosters) {
    const byUser = {}; for (const u of users) byUser[u.user_id] = u.display_name;
    const nm = {};
    for (const r of rosters) { const dn = byUser[r.owner_id]; nm[r.roster_id] = MANAGERS[dn] || dn || `Seat ${r.roster_id}`; }
    return nm;
  }
  const lastRegularWeek = league => (league.settings && league.settings.playoff_week_start || 15) - 1;
  const weekHasScores = matchups => Array.isArray(matchups) && matchups.some(e => (e.points || 0) > 0);

  /** matchupsByWeek {w: [...]} -> {scores, opponent, result} keyed by roster id. */
  function inputFromMatchups(matchupsByWeek, weeks) {
    const scores = {}, opponent = {}, result = {};
    const add = (r) => { scores[r] ??= {}; opponent[r] ??= {}; result[r] ??= {}; };
    for (const w of weeks) {
      const byMid = {};
      for (const e of matchupsByWeek[w]) (byMid[e.matchup_id] ??= []).push(e);
      for (const pair of Object.values(byMid)) {
        if (pair.length !== 2) continue;
        const [a, b] = pair; add(a.roster_id); add(b.roster_id);
        scores[a.roster_id][w] = r2(a.points); scores[b.roster_id][w] = r2(b.points);
        opponent[a.roster_id][w] = b.roster_id; opponent[b.roster_id][w] = a.roster_id;
        if (a.points > b.points) { result[a.roster_id][w] = "W"; result[b.roster_id][w] = "L"; }
        else if (b.points > a.points) { result[b.roster_id][w] = "W"; result[a.roster_id][w] = "L"; }
        else { result[a.roster_id][w] = "T"; result[b.roster_id][w] = "T"; }
      }
    }
    return { scores, opponent, result };
  }

  // ---------- the season ----------
  /**
   * @param weeks     ascending list of scored regular-season weeks
   * @param nameMap   {rosterId: name}
   * @param scores    {rid: {w: pts}}   opponent {rid: {w: rid}}   result {rid: {w: 'W'|'L'|'T'}}
   * @param projected {rid: {w: pts}} optional (missing weeks -> roster/net luck blank)
   */
  function buildSeason({ weeks, nameMap, scores, opponent, result, projected = {} }) {
    const rids = Object.keys(nameMap).map(k => (isNaN(k) ? k : Number(k))).sort((a, b) => (a > b) - (a < b));
    const nm = r => nameMap[r];
    const seasonAvg = {}; for (const r of rids) seasonAvg[r] = mean(weeks.map(w => scores[r][w]));
    const expandingAvg = (r, w) => { const i = weeks.indexOf(w); return i === 0 ? null : r2(mean(weeks.slice(0, i).map(x => scores[r][x]))); };

    // Schedule luck: opponent vs their prior average, outcome-gated
    const ui3 = {}, flips3 = {};
    for (const r of rids) { ui3[r] = {}; flips3[r] = {}; for (const w of weeks) {
      const opp = opponent[r][w], base = expandingAvg(opp, w);
      if (base === null) { ui3[r][w] = null; flips3[r][w] = null; continue; }
      const d = r2(scores[opp][w] - base), m = r2(scores[r][w] - scores[opp][w]);
      const fl = sign(m) !== sign(r2(m - d));
      ui3[r][w] = r2(d * (fl ? 1 : NON_FLIP_WEIGHT)); flips3[r][w] = fl;
    } }

    // Roster luck (vs projection, relative to league error that week) and Net luck
    const projMean = {};
    for (const w of weeks) {
      const errs = rids.filter(r => projected[r] && projected[r][w] != null).map(r => scores[r][w] - projected[r][w]);
      projMean[w] = errs.length ? r2(mean(errs)) : null;
    }
    const ui4 = {}, flips4 = {}, ui5 = {}, flips5 = {}, projinfo = {};
    for (const r of rids) { ui4[r] = {}; flips4[r] = {}; ui5[r] = {}; flips5[r] = {}; projinfo[r] = {}; for (const w of weeks) {
      const opp = opponent[r][w], m = r2(scores[r][w] - scores[opp][w]);
      const pMe = projected[r] ? projected[r][w] : null; projinfo[r][w] = pMe ?? null;
      if (pMe == null || projMean[w] === null) { ui4[r][w] = null; flips4[r][w] = null; ui5[r][w] = null; flips5[r][w] = null; continue; }
      const dMe = r2(scores[r][w] - pMe - projMean[w]);
      const fl = sign(m) !== sign(r2(m - dMe));
      ui4[r][w] = r2(-dMe * (fl ? 1 : NON_FLIP_WEIGHT)); flips4[r][w] = fl;
      const base = expandingAvg(opp, w);
      if (base === null) { ui5[r][w] = null; flips5[r][w] = null; continue; }
      const dOpp = r2(scores[opp][w] - base);
      const fl2 = sign(m) !== sign(r2(m - dOpp - dMe));
      ui5[r][w] = r2((dOpp - dMe) * (fl2 ? 1 : NON_FLIP_WEIGHT)); flips5[r][w] = fl2;
    } }

    const weeklyMedian = {}; for (const w of weeks) weeklyMedian[w] = r2(median(rids.map(r => scores[r][w])));
    const medianResult = {}, margin = {};
    for (const r of rids) { medianResult[r] = {}; margin[r] = {}; for (const w of weeks) {
      const s = scores[r][w], md = weeklyMedian[w];
      medianResult[r][w] = s > md ? "W" : s < md ? "L" : "T";
      margin[r][w] = r2(s - scores[opponent[r][w]][w]);
    } }

    const summarize = ui => { const out = {}; for (const r of rids) {
      const vals = weeks.map(w => ui[r][w]).filter(v => v !== null);
      const total = r2(vals.reduce((s, v) => s + v, 0));
      out[nm(r)] = { unlucky: vals.filter(v => v > 0).length, lucky: vals.filter(v => v < 0).length, total, weekly: vals.length ? r2(total / vals.length) : 0 };
    } return out; };

    const standings = [], medianStandings = [];
    for (const r of rids) {
      const res = weeks.map(w => result[r][w]), mres = weeks.map(w => medianResult[r][w]);
      const wins = res.filter(v => v === "W").length, losses = res.filter(v => v === "L").length;
      const sc = weeks.map(w => scores[r][w]);
      const pf = r2(sc.reduce((s, v) => s + v, 0)), pa = r2(weeks.reduce((s, w) => s + scores[opponent[r][w]][w], 0));
      standings.push({ name: nm(r), wins, losses, pf, pa, avg: r2(mean(sc)), sd: r2(pstdev(sc)) });
      medianStandings.push({ name: nm(r), wins: wins + mres.filter(v => v === "W").length, losses: losses + mres.filter(v => v === "L").length, pf });
    }
    const byRecord = (a, b) => b.wins - a.wins || b.pf - a.pf;
    standings.sort(byRecord); medianStandings.sort(byRecord);

    // Weekly reports
    const cumW = {}, cumL = {}, streak = {}; for (const r of rids) { cumW[r] = 0; cumL[r] = 0; streak[r] = 0; }
    let prevRank = null; const weeklyReports = [];
    for (const w of weeks) {
      const wk = {}; for (const r of rids) wk[r] = scores[r][w];
      const losers = rids.filter(r => result[r][w] === "L"), winners = rids.filter(r => result[r][w] === "W");
      const mg = {}; for (const r of winners) mg[r] = margin[r][w];
      const over = {}; for (const r of rids) over[r] = r2(wk[r] - seasonAvg[r]);
      const top = argmax(wk, rids), low = argmin(wk, rids);
      const hil = losers.length ? argmax(wk, losers) : null, liw = winners.length ? argmin(wk, winners) : null;
      const big = winners.length ? argmax(mg, winners) : null, nar = winners.length ? argmin(mg, winners) : null;
      const oa = argmax(over, rids), ua = argmin(over, rids);
      for (const r of rids) {
        if (result[r][w] === "W") { cumW[r]++; streak[r] = streak[r] >= 0 ? streak[r] + 1 : 1; }
        else if (result[r][w] === "L") { cumL[r]++; streak[r] = streak[r] <= 0 ? streak[r] - 1 : -1; }
      }
      const pfTo = r => weeks.filter(x => x <= w).reduce((s, x) => s + scores[r][x], 0);
      const order = [...rids].sort((a, b) => cumW[b] - cumW[a] || pfTo(b) - pfTo(a));
      const rank = {}; order.forEach((r, i) => rank[r] = i + 1);
      weeklyReports.push({
        week: w,
        topScorer: { name: nm(top), score: wk[top] }, lowScorer: { name: nm(low), score: wk[low] },
        highestInLoss: hil === null ? null : { name: nm(hil), score: wk[hil] },
        lowestInWin: liw === null ? null : { name: nm(liw), score: wk[liw] },
        biggestVictory: big === null ? null : { name: nm(big), margin: mg[big], opp: nm(opponent[big][w]) },
        narrowestVictory: nar === null ? null : { name: nm(nar), margin: mg[nar], opp: nm(opponent[nar][w]) },
        overachiever: { name: nm(oa), delta: over[oa] }, underachiever: { name: nm(ua), delta: over[ua] },
        standings: order.map(r => ({ name: nm(r), wins: cumW[r], losses: cumL[r], rankChange: prevRank ? prevRank[r] - rank[r] : 0, streak: streak[r] })),
      });
      prevRank = rank;
    }

    const byName = f => { const o = {}; for (const r of rids) o[nm(r)] = f(r); return o; };
    const perWeek = obj => byName(r => weeks.map(w => obj[r][w]));
    return {
      managers: rids.map(nm), weeks,
      scores: perWeek(scores), opponents: byName(r => weeks.map(w => nm(opponent[r][w]))),
      oppScores: byName(r => weeks.map(w => scores[opponent[r][w]][w])),
      results: perWeek(result), medianResults: perWeek(medianResult), weeklyMedian: weeks.map(w => weeklyMedian[w]),
      margin: perWeek(margin), seasonAvg: byName(r => r2(seasonAvg[r])),
      ui3: perWeek(ui3), flips3: perWeek(flips3), sum3: summarize(ui3),
      ui4: perWeek(ui4), flips4: perWeek(flips4), sum4: summarize(ui4),
      ui5: perWeek(ui5), flips5: perWeek(flips5), sum5: summarize(ui5),
      projected: perWeek(projinfo), projMean: weeks.map(w => projMean[w]),
      standings, medianStandings, weeklyReports,
    };
  }

  function playoffFinish(bracket, nameMap) {
    if (!Array.isArray(bracket)) return {};
    const final = bracket.find(m => m.p === 1 && m.w), third = bracket.find(m => m.p === 3 && m.w);
    if (!final) return {};
    const out = { [nameMap[final.w]]: "Champion", [nameMap[final.w === final.t1 ? final.t2 : final.t1]]: "Runner-up" };
    if (third) { out[nameMap[third.w]] = "3rd Place"; out[nameMap[third.w === third.t1 ? third.t2 : third.t1]] = "4th Place"; }
    return out;
  }
  function applyPlayoffs(season, bracket, nameMap) {
    const fin = playoffFinish(bracket, nameMap);
    for (const row of season.standings) row.playoffResult = fin[row.name] || "—";
    return season;
  }

  function career(seasons) {
    const stats = {};
    const ensure = k => stats[k] ??= { seasons: 0, wins: 0, losses: 0, pf: 0, medianWins: 0, medianLosses: 0, championships: 0, runnerUps: 0, thirds: 0 };
    for (const yr of Object.keys(seasons).sort()) {
      const s = seasons[yr]; if (!s || !s.standings) continue;
      for (const row of s.standings) {
        const c = ensure(CAREER_ALIAS[row.name] || row.name);
        c.seasons++; c.wins += row.wins; c.losses += row.losses; c.pf += row.pf;
        if (row.playoffResult === "Champion") c.championships++;
        else if (row.playoffResult === "Runner-up") c.runnerUps++;
        else if (row.playoffResult === "3rd Place") c.thirds++;
      }
      for (const row of s.medianStandings) { const c = ensure(CAREER_ALIAS[row.name] || row.name); c.medianWins += row.wins; c.medianLosses += row.losses; }
    }
    return Object.entries(stats).map(([name, v]) => ({ ...v, name, pf: r2(v.pf) }))
      .sort((a, b) => b.championships - a.championships || b.wins - a.wins || b.pf - a.pf);
  }

  /** Full pipeline for one season from raw Sleeper payloads. Returns null-ish placeholder if no scored weeks. */
  function seasonFromRaw({ league, users, rosters, bracket, matchupsByWeek, projectionsByWeek }) {
    const nameMap = nameMapFrom(users, rosters);
    const meta = { leagueId: league.league_id, status: league.status, rosterPositions: league.roster_positions,
                   scoring: league.scoring_settings, nameMap, lastRegularWeek: lastRegularWeek(league) };
    const weeks = [];
    for (let w = 1; w <= meta.lastRegularWeek; w++) if (weekHasScores(matchupsByWeek[w])) weeks.push(w);
    if (!weeks.length) {
      return { notStarted: true, status: league.status, managers: Object.keys(nameMap).sort((a, b) => a - b).map(r => nameMap[r]), meta };
    }
    const input = inputFromMatchups(matchupsByWeek, weeks);
    const projected = {};
    for (const w of weeks) if (projectionsByWeek[w]) {
      const tp = weekTeamProjections(projectionsByWeek[w], matchupsByWeek[w], league);
      for (const r in tp) (projected[r] ??= {})[w] = tp[r];
    }
    const season = applyPlayoffs(buildSeason({ weeks, nameMap, ...input, projected }), bracket, nameMap);
    season.meta = meta;
    return season;
  }

  return { MANAGERS, r2, playerPts, optimalLineup, weekTeamProjections, nameMapFrom, lastRegularWeek, weekHasScores,
           inputFromMatchups, buildSeason, playoffFinish, applyPlayoffs, career, seasonFromRaw };
})();
if (typeof module !== "undefined") module.exports = BBB;
