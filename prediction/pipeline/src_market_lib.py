"""Pure-python helpers (numpy is not installed on this machine)."""
import json, math
from collections import defaultdict

SC = json.load(open("scoring.json"))
POS = ["QB","RB","WR","TE","K","DEF"]

def score(stats):
    return sum(SC[k]*v for k, v in stats.items() if k in SC and SC[k])

def adp_ranks(payload):
    """{pos: [(adp, pid, name), ...]} sorted by adp_ppr, excluding 999 placeholders."""
    byp = defaultdict(list)
    for x in payload:
        pl = x.get("player") or {}
        pos = pl.get("position"); adp = (x.get("stats") or {}).get("adp_ppr")
        if pos in POS and adp is not None and adp < 999:
            byp[pos].append((adp, x["player_id"], (pl.get("first_name","")+" "+pl.get("last_name","")).strip()))
    for p in byp: byp[p].sort()
    return byp

def wls(x, y, w):
    """weighted least squares y = a + b*x; returns a, b, r2, wrmse"""
    W = sum(w); xb = sum(wi*xi for wi, xi in zip(w, x))/W; yb = sum(wi*yi for wi, yi in zip(w, y))/W
    b = sum(wi*(xi-xb)*(yi-yb) for wi, xi, yi in zip(w, x, y))/sum(wi*(xi-xb)**2 for wi, xi in zip(w, x))
    a = yb - b*xb
    ss_res = sum(wi*(yi-(a+b*xi))**2 for wi, xi, yi in zip(w, x, y))
    ss_tot = sum(wi*(yi-yb)**2 for wi, yi in zip(w, y))
    return a, b, 1-ss_res/ss_tot, math.sqrt(ss_res/W)
