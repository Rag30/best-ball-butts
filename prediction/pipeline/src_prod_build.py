import sys as _s, os as _o; _s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__))); from wk import START
"""Build proj_production.json (week-3 edition): a 'what have you actually done' baseline.

Evidence: 2025 wk1-18 + 2026 wk1-2 Sleeper stats, all re-scored with the league's
scoring.json (6-pt pass TD, PPR) from raw stat keys.

  ros_ppg = (gp25*ppg25 + g26*ppg26 + K*prior) / (gp25 + g26 + K),  K = 4

  g26/ppg26 : only 2026 weeks the player actually PLAYED (stats row with gp>=1).
              Inactive / injured / bye weeks are skipped, never folded in as 0.
  prior     : gp25 >= 1 (veterans)  -> 'starter' prior  = mean 2025 ppg of the top-N
                                        by 2025 total pts (QB24/RB48/WR60/TE20/K24/DEF32)
              gp25 == 0 (rookies,   -> 'replacement' prior = mean 2025 ppg of the players
              2025 non-players)        ranked QB13-24 / RB25-48 / WR37-72 / TE13-24 /
                                        K1-24 / DEF1-32 by 2025 total pts
              Both pools: 2025 players with 8+ games played.

Output: weekly {pid: {"3".."17": pts}}, 0 on bye weeks and on injury-zeroed weeks.
Availability: injury_adjustments.json (sibling agent) weeks_out if present, else fallback
rules (IR/Out/PUP -> wks 3-6; ACL/Achilles -> wks 3-17).
"""
import json, os
from collections import defaultdict, Counter

SC   = json.load(open("scoring.json"))
ROST = json.load(open("rostered_players.json"))
BYES = json.load(open("byes_2026.json"))
PDB  = json.load(open("players_fresh.json"))
WEEKS = range(START,18)

def score(st): return sum(SC[k]*v for k, v in st.items() if k in SC)

# ---------- 1. 2025 season: per-player games + points ----------
tot25 = defaultdict(float); gp25 = defaultdict(int)
for w in range(1, 19):
    d = json.load(open(f"src_prod_stats/s2025_w{w}.json"))
    for pid, st in d.items():
        s = score(st)
        played = (st.get("gp", 0) >= 1) or abs(s) > 0.01
        if played:
            gp25[pid] += 1
            tot25[pid] += s

# ---------- 2. 2026 weeks 1-2 (played games only) ----------
g26 = defaultdict(int); tot26 = defaultdict(float); wk26 = defaultdict(dict)
for w in range(1, START):
    d = json.load(open(f"s26_w{w}.json"))
    for pid, st in d.items():
        s = score(st)
        if (st.get("gp", 0) >= 1) or abs(s) > 0.01:
            g26[pid] += 1; tot26[pid] += s; wk26[pid][w] = round(s, 2)

# ---------- 3. positional priors ----------
def pos_of(pid):
    p = PDB.get(pid) or {}
    q = p.get("position")
    if not q:
        fp = p.get("fantasy_positions") or []
        q = fp[0] if fp else None
    return q
POSES = ["QB", "RB", "WR", "TE", "K", "DEF"]
pool = defaultdict(list)                      # pos -> (total, ppg, pid), 8+ games
for pid, g in gp25.items():
    if g < 8: continue
    q = pos_of(pid)
    if q in POSES: pool[q].append((tot25[pid], tot25[pid]/g, pid))
for q in pool: pool[q].sort(key=lambda t: -t[0])

STARTER = {"QB": (1, 24), "RB": (1, 48), "WR": (1, 60), "TE": (1, 20), "K": (1, 24), "DEF": (1, 32)}
REPL    = {"QB": (13, 24), "RB": (25, 48), "WR": (37, 72), "TE": (13, 24), "K": (1, 24), "DEF": (1, 32)}
def nm(pid): return PDB.get(pid, {}).get("full_name") or pid
def prior(ranks):
    m = {}; det = {}
    for q, (a, b) in ranks.items():
        lst = pool[q][a-1:b]
        m[q] = sum(t[1] for t in lst)/len(lst)
        det[q] = dict(ranks=f"{a}-{b}", pool_8plus=len(pool[q]), used=len(lst), mean=round(m[q], 3),
                      first=[(nm(t[2]), round(t[1], 2)) for t in lst[:2]],
                      last=[(nm(t[2]), round(t[1], 2)) for t in lst[-2:]])
    return m, det
pm_start, det_start = prior(STARTER)
pm_repl,  det_repl  = prior(REPL)

# ---------- 4. availability ----------
zero_weeks = {}; inj_notes = []
INJ_FILE = "injury_adjustments.json"
if os.path.exists(INJ_FILE):
    inj_source = INJ_FILE
    IA = json.load(open(INJ_FILE))
    if isinstance(IA, list):
        IA = {str(x.get("pid") or x.get("player_id") or x.get("sleeper_id")): x for x in IA}
    for pid, a in IA.items():
        if pid not in ROST: continue
        wks = sorted(int(w) for w in (a.get("weeks_out") or []) if START <= int(w) <= 17)
        if wks: zero_weeks[pid] = set(wks)
        inj_notes.append(dict(pid=pid, name=ROST[pid]["name"], pos=ROST[pid]["pos"], team=ROST[pid]["team"],
                              injury_status=ROST[pid].get("injury_status"), body=ROST[pid].get("injury_body_part"),
                              zeroed_weeks=wks, multiplier_ignored=a.get("multiplier"),
                              rule="injury_adjustments.json weeks_out"))
else:
    inj_source = "fallback rules (injury_adjustments.json absent)"
    LONG = ("acl", "achilles")
    for pid, v in ROST.items():
        stt = (v.get("injury_status") or "").upper()
        body = (v.get("injury_body_part") or "")
        if stt not in ("IR", "OUT", "PUP"): continue
        if any(x in body.lower() for x in LONG):
            wks = list(WEEKS); why = f"{stt} ({body}) -> season-ending body part, wks 3-17"
        else:
            wks = list(range(START, START+4)); why = f"{stt} ({body}) -> 4 wks from START"
        zero_weeks[pid] = set(wks)
        inj_notes.append(dict(pid=pid, name=v["name"], pos=v["pos"], team=v["team"], injury_status=v.get("injury_status"),
                              body=body, zeroed_weeks=wks, rule=why))

# ---------- 5. blend ----------
K = 4.0
out = {}; rows = []; omitted = []
for pid, v in ROST.items():
    q = v["pos"]
    if q not in POSES:
        omitted.append(dict(pid=pid, name=v["name"], pos=q, reason="position not in lineup (sim ignores)"))
        continue
    g = gp25.get(pid, 0); p25 = (tot25[pid]/g) if g else 0.0
    n26 = g26.get(pid, 0); p26 = (tot26[pid]/n26) if n26 else 0.0
    pri_kind = "starter" if g else "replacement"
    pri = (pm_start if g else pm_repl)[q]
    den = g + n26 + K
    ppg = max((g*p25 + n26*p26 + K*pri)/den, 0.0)
    team = v["team"] or "FA"
    bye = set(BYES.get(team, []))
    z = zero_weeks.get(pid, set())
    out[pid] = {str(w): (0.0 if (w in bye or w in z) else round(ppg, 3)) for w in WEEKS}
    rows.append(dict(pid=pid, name=v["name"], pos=q, team=team, manager=v["manager"],
                     gp25=g, ppg25=round(p25, 3), g26=n26, ppg26=round(p26, 3), wk26=wk26.get(pid, {}),
                     rost_wk1_played=v.get("wk1_played"), rost_wk2_played=v.get("wk2_played"),
                     prior=pri_kind, prior_ppg=round(pri, 3),
                     w25=round(g/den, 3), w26=round(n26/den, 3), wpos=round(K/den, 3),
                     ros_ppg=round(ppg, 3), bye=sorted(bye), zeroed=sorted(z)))

json.dump(out, open("proj_production.json", "w"), indent=1)
json.dump(dict(model="ros_ppg=(gp25*ppg25+g26*ppg26+K*prior)/(gp25+g26+K)", K=K,
               prior_starter={k: round(v, 3) for k, v in pm_start.items()}, prior_starter_detail=det_start,
               prior_replacement={k: round(v, 3) for k, v in pm_repl.items()}, prior_replacement_detail=det_repl,
               injury_source=inj_source, injuries=inj_notes, rows=rows, omitted=omitted),
          open("src_prod_detail.json", "w"), indent=1, default=list)

print("players written:", len(out), "of", len(ROST), "rostered")
print("omitted:", omitted)
print("\npriors (2025 ppg, 8+ gp, ranked by 2025 total pts):")
for q in POSES:
    a, b = det_start[q], det_repl[q]
    print(f"  {q:4} starter[{a['ranks']:>5}]={a['mean']:6.2f}  replacement[{b['ranks']:>5}]={b['mean']:6.2f}  pool8+={a['pool_8plus']}  repl-edge={b['last']}")
print("\ngp25 distribution:", sorted(Counter(r['gp25'] for r in rows).items()))
print("g26 distribution:", sorted(Counter(r['g26'] for r in rows).items()))
print("replacement-prior players (gp25==0):", [(r['name'], r['pos'], r['g26'], r['ros_ppg']) for r in rows if r['prior'] == 'replacement'])
print("\ninjury source:", inj_source)
for n in inj_notes: print("  ", n["name"], n["pos"], n["injury_status"], n["body"], "->", n["zeroed_weeks"], "|", n["rule"])
