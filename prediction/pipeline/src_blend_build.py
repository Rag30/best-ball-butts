import sys as _s, os as _o; _s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__))); from wk import START
"""Build proj_blend.json (A) and proj_blend_inj.json (B), week-3 edition.

Same recipe as the week-1 edition (after its repair pass), with two weeks of evidence instead of one:
  prior    = per-week weighted average of the raw sources (sleeper_kfix .30, espn .25, production .10, market .10;
             fantasypros still has no points source) renormalized over the sources that cover the player;
             a source whose whole-season total is 0 while another covering source is >0 is dropped (availability
             is owned by injury_adjustments.json, not by a source's zero).
  posterior= (K*prior_w + sum of 2026 points in games played) / (K + games played), K=6 by default, weeks the
             prior says he plays only; K and DEF get no update; a game he did not play contributes nothing.
  hard availability (weeks_out) zeroed in both files; soft multiplier (inside multiplier_weeks) only in _inj.
Usage: python3 src_blend_build.py [--K 6] [--tag ""] [--quiet]
"""
import json, argparse
from collections import Counter
ap=argparse.ArgumentParser(); ap.add_argument("--K",type=float,default=6.0); ap.add_argument("--tag",default=""); ap.add_argument("--quiet",action="store_true")
A=ap.parse_args(); K=A.K; CAP=1.5
W={"sleeper":0.30,"espn":0.25,"production":0.10,"market":0.10}
WEEKS=[str(w) for w in range(START,18)]; UPD_POS={"QB","RB","WR","TE"}
rost={p:v for p,v in json.load(open("rostered_players.json")).items() if v["pos"] in ("QB","RB","WR","TE","K","DEF")}
byes=json.load(open("byes_2026.json")); inj=json.load(open("injury_adjustments.json"))
SRC={}
for s,f in (("sleeper","proj_sleeper_kfix.json"),("espn","proj_espn.json"),("production","proj_production.json"),("market","proj_market.json")):
    try: SRC[s]=json.load(open(f))
    except FileNotFoundError: print("MISSING SOURCE",s)
def to_weekly(pid,d):
    if "ros" in d:
        g=[w for w in range(START,18) if w not in byes.get(rost[pid]["team"],[])]; per=d["ros"]/len(g) if g else 0.0
        return {str(w):(per if w in g else 0.0) for w in range(START,18)}
    return {w:float(d.get(w,0) or 0) for w in WEEKS}
blend,detail,dropped={},{},[]
for pid,v in rost.items():
    cov={s:SRC[s][pid] for s in SRC if pid in SRC[s]}
    if not cov: detail[pid]={"sources":[],"skipped":True}; continue
    wk={s:to_weekly(pid,d) for s,d in cov.items()}; tots={s:sum(x.values()) for s,x in wk.items()}
    zeros=[s for s in cov if tots[s]<=0]
    if zeros and any(tots[s]>0 for s in cov):
        for s in zeros: cov.pop(s); wk.pop(s)
        dropped.append((v["name"],v["pos"],zeros,{s:round(tots[s],1) for s in cov}))
    tw=sum(W[s] for s in cov); wts={s:W[s]/tw for s in cov}
    pri={w:sum(wts[s]*wk[s][w] for s in cov) for w in WEEKS}; pri_tot=sum(pri.values())
    games=[v[f"wk{i}_pts"] for i in range(1,START) if v.get(f"wk{i}_played")]
    upd=bool(games) and v["pos"] in UPD_POS
    post={w:((K*pri[w]+sum(games))/(K+len(games)) if pri[w]>0 else 0.0) for w in WEEKS} if upd else dict(pri)
    capped=False
    if pri_tot>0 and sum(post.values())>CAP*pri_tot:
        f=CAP*pri_tot/sum(post.values()); post={w:x*f for w,x in post.items()}; capped=True
    a=inj.get(pid); out={str(w) for w in (a or {}).get("weeks_out",[])}
    post={w:(0.0 if w in out else post[w]) for w in WEEKS}
    blend[pid]={w:round(post[w],4) for w in WEEKS}
    detail[pid]={"sources":sorted(cov),"weights":{s:round(wts[s],4) for s in cov},"dropped_zero_sources":zeros if zeros else [],
        "src_tot":{s:round(tots[s],2) for s in cov},"prior_tot":round(pri_tot,2),"post_tot":round(sum(post.values()),2),
        "games_2026":games,"update_applied":upd,"capped":capped,"weeks_out":sorted(int(w) for w in out)}
blend_inj={}; soft=[]
for pid,wkd in blend.items():
    a=inj.get(pid)
    if not a: blend_inj[pid]=dict(wkd); continue
    m=float(a.get("multiplier",1.0)); win={str(w) for w in a.get("multiplier_weeks",[])}
    blend_inj[pid]={w:(round(wkd[w]*m,4) if w in win else wkd[w]) for w in WEEKS}
    if win and m!=1.0: soft.append((rost[pid]["name"],rost[pid]["manager"],m,sorted(int(w) for w in win),round(sum(blend_inj[pid].values())-sum(wkd.values()),1)))
json.dump(blend,open(f"proj_blend{A.tag}.json","w"),indent=0,sort_keys=True)
json.dump(blend_inj,open(f"proj_blend_inj{A.tag}.json","w"),indent=0,sort_keys=True)
json.dump(detail,open(f"src_blend_detail{A.tag}.json","w"),indent=1,sort_keys=True)
if A.quiet: raise SystemExit
print(f"K={K} sources={list(SRC)} entries={len(blend)}/{len(rost)} source-count={Counter(len(d['sources']) for d in detail.values())}")
print("update applied:",sum(d.get("update_applied",False) for d in detail.values()),"capped:",sum(d.get("capped",False) for d in detail.values()))
print("dropped whole-season-zero sources:"); [print("  ",x) for x in dropped]
print("weeks_out:"); [print(f"   {rost[p]['name']:22}{rost[p]['manager']:8}{detail[p]['weeks_out']}") for p in blend if detail[p]["weeks_out"]]
print("soft layer:"); [print("  ",x) for x in sorted(soft,key=lambda t:t[4])]
