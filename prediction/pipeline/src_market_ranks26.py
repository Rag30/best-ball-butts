import json
from collections import defaultdict
rost = json.load(open("rostered_players.json"))
p26 = json.load(open("p26_season.json"))
byp = defaultdict(list)
for x in p26:
    pl = x.get("player") or {}
    pos = pl.get("position"); pid = x["player_id"]
    adp = (x.get("stats") or {}).get("adp_ppr")
    if pos in ("QB","RB","WR","TE","K","DEF") and adp is not None and adp < 999:
        byp[pos].append((adp, pid))
for pos in byp: byp[pos].sort()
print("2026 ADP pool sizes:", {p: len(v) for p, v in byp.items()})
rank = {}
for pos, arr in byp.items():
    for i, (adp, pid) in enumerate(arr, 1):
        rank[pid] = (pos, i, adp)
bypos = defaultdict(list)
for pid, v in rost.items():
    r = rank.get(pid)
    bypos[v["pos"]].append((r[1] if r else None, v["name"], r[2] if r else None, r[0] if r else None))
for pos in ["QB","RB","WR","TE","K","DEF","DB"]:
    if pos not in bypos: continue
    a = sorted(bypos[pos], key=lambda t: (t[0] is None, t[0]))
    rk = [t[0] for t in a if t[0] is not None]
    print(f"\n{pos}: n={len(a)} rank range {min(rk) if rk else None}..{max(rk) if rk else None}  none={sum(1 for t in a if t[0] is None)}")
    print("   worst 6:", [(t[1], t[0], t[3]) for t in a[-6:]])
