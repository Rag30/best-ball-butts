import sys as _s, os as _o; _s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__))); from wk import START
"""Build proj_market.json (week-3 edition): 2025-fitted ADP->ppg curves applied to 2026 preseason ADP.
ros = ppg * (# non-bye weeks in 3..17). IR players are NOT zeroed (availability lives in injury_adjustments.json)."""
import json, math
from collections import defaultdict

rost  = json.load(open("rostered_players.json"))
byes  = json.load(open("byes_2026.json"))
fits  = json.load(open("src_market_fits.json"))
p26   = json.load(open("p26_season.json"))
sleep = json.load(open("proj_sleeper.json"))

POS = ["QB","RB","WR","TE","K","DEF"]

# --- 2026 positional ADP ranks ---
byp = defaultdict(list)
for x in p26:
    pl = x.get("player") or {}
    pos = pl.get("position"); adp = (x.get("stats") or {}).get("adp_ppr")
    if pos in POS and adp is not None and adp < 999:
        byp[pos].append((adp, x["player_id"]))
for pos in byp: byp[pos].sort()
rank26, adp26 = {}, {}
for pos, arr in byp.items():
    for i, (adp, pid) in enumerate(arr, 1):
        rank26[pid] = i; adp26[pid] = adp

def curve(pos, r):
    f = fits[pos]
    return max(f["a"] + f["b"]*math.log(r), 0.0)

# tail value per position = curve at the deepest rank we fitted
TAIL = {p: curve(p, fits[p]["n_range"]) for p in POS}

out, notes = {}, []
zeroed, no_adp, skipped = [], [], []
for pid, v in rost.items():
    pos = v["pos"]
    if pos not in POS:
        skipped.append((pid, v["name"], pos)); continue
    r = rank26.get(pid)
    if r is None:
        ppg = TAIL[pos]; no_adp.append((pid, v["name"], pos))
    else:
        ppg = curve(pos, r)
    team = v["team"] or "FA"
    games = [w for w in range(START,18) if w not in byes.get(team, [])]
    ros = ppg * len(games)
    if (v.get("injury_status") or "").upper() in ("IR", "OUT", "PUP", "DOUBTFUL", "NA"):
        zeroed.append((pid, v["name"], pos, v.get("injury_status"), v.get("injury_body_part")))  # flagged only, value kept
    if team == "FA" or team not in byes:
        notes.append((pid, v["name"], "team %r has no bye entry -> 15 games" % team))
    out[pid] = {"ros": round(ros, 2)}

json.dump(out, open("proj_market.json","w"), indent=1)
sim_ids = [p for p, v in rost.items() if v["pos"] in POS]

print(f"wrote proj_market.json: {len(out)} of {len(sim_ids)} simulated rostered ids ({len(rost)} incl. non-sim positions)")
print(f"  valued from a real 2026 ADP rank: {len(out)-len(no_adp)}; curve-tail fallback: {len(no_adp)}")
print("team notes:", notes)
print("skipped (position not simulated):", skipped)
print("no 2026 ADP (tail value used):", no_adp)
print("injury-flagged (NOT zeroed; injury_adjustments.json handles availability):")
for z in zeroed: print("   ", z)
print("\ncurve points (ppg) at positional ADP rank 1/5/10/20/40, and tail:")
for p in POS:
    f = fits[p]
    print(f"  {p:4s} a={f['a']:6.2f} b={f['b']:+6.3f} R2={f['r2']:.3f} n_fit={f['n_fit']}/{f['n_range']}  "
          + "  ".join(f"{r}:{curve(p,r):5.2f}" for r in (1,5,10,20,40))
          + f"   tail(rank {f['n_range']}):{TAIL[p]:.2f}")

# --- sanity: manager totals vs Sleeper source ---
print("\nmanager ROS totals (weeks 3-17), market vs sleeper:")
mm, ms = defaultdict(float), defaultdict(float)
for pid, v in rost.items():
    if pid in out: mm[v["manager"]] += out[pid]["ros"]
    ms[v["manager"]] += sum(float(x or 0) for k, x in sleep.get(pid, {}).items() if 3 <= int(k) <= 17)
print(f"{'mgr':9s}{'market':>9s}{'sleeper':>9s}{'ratio':>7s}")
for m in sorted(mm, key=lambda k: -mm[k]):
    print(f"{m:9s}{mm[m]:9.0f}{ms[m]:9.0f}{mm[m]/ms[m]:7.2f}")
print(f"{'TOTAL':9s}{sum(mm.values()):9.0f}{sum(ms.values()):9.0f}{sum(mm.values())/sum(ms.values()):7.2f}")

# top/bottom players
rows = sorted(((out[p]['ros'], rost[p]['name'], rost[p]['pos'], rank26.get(p), adp26.get(p)) for p in out), reverse=True)
print("\ntop 12 by market ros:")
for t in rows[:12]: print(f"   {t[1]:24s} {t[2]:4s} rank {str(t[3]):>4s} adp {t[4]:6.1f}  ros {t[0]:7.1f}")
print("bottom 8 by market ros:")
for t in rows[-8:]: print(f"   {t[1]:24s} {t[2]:4s} rank {str(t[3]):>4s} adp {str(t[4]):>6s}  ros {t[0]:7.1f}")
