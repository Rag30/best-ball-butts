import sys as _s, os as _o; _s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__))); from wk import START
"""FIX (blocking: kicker FG distance bonus).

scoring.json pays fgm_yds_over_30 = 0.1/yd and zeroes every distance tier, so that key IS the
league's whole distance reward.  Sleeper's weekly projection rows (p26_w*.json) never contain
fgm_yds_over_30, so the recompute behind proj_sleeper.json scores it as 0 for all 14 kickers.
proj_sleeper.json is frozen, so this writes a corrected copy, proj_sleeper_kfix.json
( = proj_sleeper.json with an estimated distance bonus added to the K rows ).

Estimator: bonus(week) = 0.1 * rate(kicker) * fgm_proj(week)
  rate = yards-over-30 per made FG, from 2025 Sleeper actuals, shrunk to the league mean
         (10.19 yd/FGm over 931 made FGs) with K=20 made FGs of prior weight.
Sleeper's own tier keys (fgm_0_19..fgm_50p) are NOT used: they are incomplete in the 2026
projection rows (they sum to ~60% of projected fgm), whereas fgm itself is always present.
"""
import json
from collections import defaultdict

rost = json.load(open("rostered_players.json"))
ks   = {p for p, v in rost.items() if v["pos"] == "K"}

# --- 2025 per-kicker distance rate ---
made = defaultdict(float); over = defaultdict(float)
lg_m = lg_o = 0.0
for w in range(1, 19):
    for pid, st in json.load(open(f"src_slp_2025_w{w}.json")).items():
        if pid.startswith("TEAM_"): continue
        if "fgm" not in st: continue
        m = float(st.get("fgm", 0) or 0); o = float(st.get("fgm_yds_over_30", 0) or 0)
        made[pid] += m; over[pid] += o; lg_m += m; lg_o += o
LG = lg_o / lg_m
KSH = 20.0
rate = {p: (over[p] + KSH * LG) / (made[p] + KSH) for p in ks}

# --- projected made FGs per kicker-week ---
fgm = defaultdict(dict)
for w in range(START,18):
    for x in json.load(open(f"p26_w{w}.json")):
        pid = str(x.get("player_id"))
        if pid in ks:
            fgm[pid][str(w)] = float((x.get("stats") or {}).get("fgm", 0) or 0)

slp = json.load(open("proj_sleeper.json"))
fix = {p: dict(d) for p, d in slp.items()}
bonus_tot = {}
for p in ks:
    if p not in fix: continue
    b = 0.0
    for w in [str(x) for x in range(START,18)]:
        base = float(fix[p].get(w, 0) or 0)
        if base <= 0:            # bye / projected out -> stays 0
            continue
        add = 0.1 * rate[p] * fgm[p].get(w, 0.0)
        fix[p][w] = round(base + add, 4); b += add
    bonus_tot[p] = b

json.dump(fix, open("proj_sleeper_kfix.json", "w"), indent=0, sort_keys=True)
json.dump({p: {"name": rost[p]["name"], "fgm25": round(made[p],1), "over30_25": round(over[p],1),
               "rate_yd_per_fgm": round(rate[p],3), "ros_bonus_pts": round(bonus_tot[p],2)} for p in sorted(bonus_tot)},
          open("src_fix_kfg_detail.json","w"), indent=1)

print(f"league 2025 rate: {LG:.3f} yd over 30 per made FG  ({lg_m:.0f} made FGs)")
print(f"{'kicker':22}{'2025 fgm':>9}{'rate':>7}{'slp ROS':>9}{'+bonus':>8}{'new':>9}")
for p in sorted(bonus_tot, key=lambda p: -bonus_tot[p]):
    o = sum(float(v or 0) for v in slp[p].values()); n = sum(float(v or 0) for v in fix[p].values())
    print(f"{rost[p]['name']:22}{made[p]:9.0f}{rate[p]:7.2f}{o:9.1f}{bonus_tot[p]:8.1f}{n:9.1f}")
