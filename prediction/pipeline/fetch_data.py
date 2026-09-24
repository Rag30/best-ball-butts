"""Step 1: pull everything from the public Sleeper API into the current run dir and build the base files.
Writes: week.json {start, last_scored}, l_2026/r_2026/u_2026/wb_2026, m26_w1..14, s26_w1..L, tx_w1..L+1, p26_w*/p26_season,
players_fresh.json, scoring.json, byes_2026.json, rostered_players.json (wk{i}_pts / wk{i}_played for every completed week),
proj_sleeper.json (weeks START..17), dst_check.json (league D/ST points vs recount), and links the static caches.
Run from the run dir:  python3 <pipeline>/fetch_data.py --snapshot bbb_snapshot_wN.json   (MCP export; preferred)
                   or python3 <pipeline>/fetch_data.py                                  (direct Sleeper API fallback)
"""
import json, os, urllib.request
from collections import defaultdict
LG = "1312511085802180608"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache")
MAN = {"plankrad": "Conrad", "bballlauren": "Lauren", "lilmisseb": "Emma", "Raghavr7": "Raghav", "averymc03": "Avery",
       "mac003": "Avery", "dragonslayyyer69": "Ben", "NoLsHere": "Noelle", "TheDragon96": "Henry"}
POSQ = "position[]=QB&position[]=RB&position[]=WR&position[]=TE&position[]=K&position[]=DEF"
def get(url, out=None):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=120) as r:
                d = json.load(r)
            break
        except Exception as e:
            if i == 3: raise
    if out: json.dump(d, open(out, "w"))
    return d
import sys
SNAP = sys.argv[sys.argv.index("--snapshot") + 1] if "--snapshot" in sys.argv else None
if SNAP:
    # Preferred path: bundle written by the gateway's sleeper-draft__export_league_snapshot tool (Raghav's MCP),
    # downloaded from the gateway /files lane. Same data as the direct API calls below, one file.
    b = json.load(open(SNAP))
    dump = lambda d, out: json.dump(d, open(out, "w"))
    L = b["league"]; dump(L, "l_2026.json"); last = int(b["last_completed_week"]); START = last + 1
    dump(b["rosters"], "r_2026.json"); dump(b["users"], "u_2026.json"); dump(b["winners_bracket"], "wb_2026.json")
    for w, d in b["matchups"].items(): dump(d, f"m26_w{w}.json")
    for w, d in b["transactions"].items(): dump(d, f"tx_w{w}.json")
    for w, d in b["stats"].items(): dump(d, f"s26_w{w}.json")
    for w, d in b["projections"].items(): dump(d, f"p26_w{w}.json")
    dump(b["projections_season"], "p26_season.json"); players = b["players"]; dump(players, "players_fresh.json")
    json.dump({"start": START, "last_scored": last, "source": "mcp snapshot " + os.path.basename(SNAP)}, open("week.json", "w"))
else:
    L = get(f"https://api.sleeper.app/v1/league/{LG}", "l_2026.json")
    last = int(L["settings"].get("last_scored_leg") or 0)
    # guard: a week only counts as complete if its matchups have non-zero points
    while last > 0 and not any((e.get("points") or 0) > 0 for e in get(f"https://api.sleeper.app/v1/league/{LG}/matchups/{last}")):
        last -= 1
    START = last + 1
    json.dump({"start": START, "last_scored": last, "source": "direct Sleeper API"}, open("week.json", "w"))
    get(f"https://api.sleeper.app/v1/league/{LG}/rosters", "r_2026.json"); get(f"https://api.sleeper.app/v1/league/{LG}/users", "u_2026.json")
    get(f"https://api.sleeper.app/v1/league/{LG}/winners_bracket", "wb_2026.json")
    for w in range(1, 15): get(f"https://api.sleeper.app/v1/league/{LG}/matchups/{w}", f"m26_w{w}.json")
    for w in range(1, START + 1): get(f"https://api.sleeper.app/v1/league/{LG}/transactions/{w}", f"tx_w{w}.json")
    for w in range(1, START): get(f"https://api.sleeper.app/v1/stats/nfl/regular/2026/{w}", f"s26_w{w}.json")
    for w in range(1, 18): get(f"https://api.sleeper.app/projections/nfl/2026/{w}?season_type=regular&{POSQ}", f"p26_w{w}.json")
    get(f"https://api.sleeper.app/projections/nfl/2026?season_type=regular&{POSQ}", "p26_season.json")
    players = get("https://api.sleeper.app/v1/players/nfl", "players_fresh.json")
sc = L["scoring_settings"]; json.dump(sc, open("scoring.json", "w"), indent=1)
score = lambda st: round(sum(sc[k] * x for k, x in (st or {}).items() if k in sc and isinstance(x, (int, float))), 2)
# byes: week where a team's whole projection is 0 (only weeks >= START matter); keep earlier-known byes from cache
teamweeks = defaultdict(lambda: defaultdict(float)); sl = defaultdict(dict)
for w in range(1, 18):
    for e in json.load(open(f"p26_w{w}.json")):
        t = e.get("team") or (e.get("player") or {}).get("team"); v = score(e.get("stats"))
        sl[e["player_id"]][str(w)] = v
        if t: teamweeks[t][w] += v
byes = {t: [w for w, v in ws.items() if v == 0 and w >= 3] for t, ws in teamweeks.items()}
byes = {t: b for t, b in byes.items() if b}
json.dump(byes, open("byes_2026.json", "w"), indent=0)
U = {u["user_id"]: u["display_name"] for u in json.load(open("u_2026.json"))}
M = {w: {e["roster_id"]: e for e in json.load(open(f"m26_w{w}.json"))} for w in range(1, START)}
ST = {w: json.load(open(f"s26_w{w}.json")) for w in range(1, START)}
rost = {}
for r in json.load(open("r_2026.json")):
    mgr = MAN.get(U.get(r["owner_id"]), U.get(r["owner_id"]))
    for p in r["players"]:
        pl = players.get(p, {})
        v = {"name": f"{pl.get('first_name','')} {pl.get('last_name','')}".strip(), "pos": pl.get("position"), "team": pl.get("team"),
             "manager": mgr, "roster_id": r["roster_id"], "age": pl.get("age"), "years_exp": pl.get("years_exp"),
             "injury_status": pl.get("injury_status"), "injury_body_part": pl.get("injury_body_part"), "injury_notes": pl.get("injury_notes"),
             "status": pl.get("status"), "espn_id": pl.get("espn_id"), "yahoo_id": pl.get("yahoo_id"),
             "depth_chart_order": pl.get("depth_chart_order"), "depth_chart_position": pl.get("depth_chart_position")}
        for w in range(1, START):
            s = ST[w].get(p)
            v[f"wk{w}_pts"] = score(s)
            v[f"wk{w}_played"] = bool(s and (s.get("gp") or s.get("off_snp") or s.get("def_snp") or s.get("st_snp") or s.get("pts_ppr")))
            v[f"wk{w}_pts_on_roster"] = M[w].get(r["roster_id"], {}).get("players_points", {}).get(p)
        rost[p] = v
json.dump(rost, open("rostered_players.json", "w"), indent=1)
json.dump({p: {k: x for k, x in sl.get(p, {}).items() if int(k) >= START} for p in rost}, open("proj_sleeper.json", "w"), indent=0)
# D/ST check: league players_points vs recount from raw stats
chk = []
for w in range(1, START):
    for rid, e in M[w].items():
        for p, pts in e["players_points"].items():
            if players.get(p, {}).get("position") == "DEF":
                chk.append({"week": w, "def": p, "roster_id": rid, "league": pts, "recount": score(ST[w].get(p))})
json.dump(chk, open("dst_check.json", "w"), indent=1)
bad = [c for c in chk if abs(c["league"] - c["recount"]) > 0.05]; zero = [c for c in chk if c["league"] == 0]
for name in ("src_espn_fgcal.json", "src_market_fits.json", "src_prod_stats", "slp2025"):
    if not os.path.exists(name): os.symlink(os.path.join(CACHE, name), name)
for w in range(1, 19):
    n = f"src_slp_2025_w{w}.json"
    if not os.path.exists(n): os.symlink(os.path.join(CACHE, "slp2025", n), n)
print(f"last completed week {last}; projecting weeks {START}-17; rostered {len(rost)}; D/ST checks {len(chk)} (mismatch {len(bad)}, zero {len(zero)})")
