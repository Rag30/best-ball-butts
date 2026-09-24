"""Aggregate the 12 headline runs (6 engines x base/gci, Weeks 1-2 locked) + 12 unlocked runs into agg.json and print tables."""
import sys as _s, os as _o; _s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)))
import json, statistics as st
M=["Conrad","Lauren","Emma","Raghav","Avery","Ben","Noelle","Henry"]
ENG=["sleeper_kfix","espn","market","production","blend","blend_inj"]; CFG=["base","gci"]
L=lambda f:json.load(open(f))["results"]
R={(e,c):L(f"result_{e}_{c}.json") for e in ENG for c in CFG}
U={(e,c):L(f"result_{e}_{c}_nolock.json") for e in ENG for c in CFG}
import sys, os
from wk import START
# previous edition's consensus: newest earlier run dir that has agg.json (runs/<date>/agg.json); falls back to none
PREV={}
try:
    runs=sorted(d for d in os.listdir("..") if os.path.isfile(os.path.join("..",d,"agg.json")) and os.path.abspath(os.path.join("..",d))!=os.path.abspath("."))
    if runs:
        pc=json.load(open(os.path.join("..",runs[-1],"agg.json")))
        PREV={m:dict(title=v["title"],rank=v["rank"],edition=runs[-1]) for m,v in pc["consensus"].items()}
except Exception as e: print("no previous edition:",e)
OLD={m:PREV.get(m,dict(title=float("nan"),rank=0,edition="none")) for m in M}
def mean(xs): return sum(xs)/len(xs)
out={"engine_title":{f"{e}/{c}":{m:round(100*R[(e,c)][m]["title"],1) for m in M} for e in ENG for c in CFG}}
cons={}
for m in M:
    g=lambda k,src=R:[src[r][m][k] for r in src]
    ranks=[sorted(M,key=lambda x:-R[r][x]["title"]).index(m)+1 for r in R]
    bbr=[sorted(M,key=lambda x:-R[r][x]["bb_avg"]).index(m)+1 for r in R]
    cons[m]=dict(title=100*mean(g("title")),tmin=100*min(g("title")),tmax=100*max(g("title")),playoff=100*mean(g("playoff")),bye=100*mean(g("bye")),
        seed1=100*mean(g("seed1")),final=100*mean(g("final")),xw=mean(g("x_wins")),xfin=mean(g("x_finish")),bb=mean(g("bb_avg")),bbmin=min(g("bb_avg")),bbmax=max(g("bb_avg")),
        paper=mean(g("paper_avg")),wksd=mean(g("wk_sd")),firsts=sum(1 for r in R if max(M,key=lambda x:R[r][x]["title"])==m),ranks=sorted(ranks),bbranks=bbr,bbrank_mean=mean(bbr),
        u_title=100*mean(g("title",U)),u_min=100*min(g("title",U)),u_max=100*max(g("title",U)),u_playoff=100*mean(g("playoff",U)),
        u_bb=mean([U[r][m]["bb_avg"] for r in U]),
        u_delta_gci={e:round(100*(U[(e,"gci")][m]["title"]-R[(e,"gci")][m]["title"]),1) for e in ENG},
        finish={k:100*mean([R[r][m]["finish"][str(k)] for r in R]) for k in range(1,9)},
        seed={k:100*mean([R[r][m]["seed"][str(k)] for r in R]) for k in range(1,9)},
        rec=f"{int(R[('blend','gci')][m]['locked_w'])}-{START-1-int(R[('blend','gci')][m]['locked_w'])}",pf=R[('blend','gci')][m]['locked_pf'])
order=sorted(M,key=lambda m:-cons[m]["title"])
for i,m in enumerate(order): cons[m]["rank"]=i+1
bbo=sorted(M,key=lambda m:cons[m]["bbrank_mean"])
for i,m in enumerate(bbo): cons[m]["bbrank"]=i+1
uo=sorted(M,key=lambda m:-cons[m]["u_title"])
for i,m in enumerate(uo): cons[m]["u_rank"]=i+1
out["consensus"]=cons; out["old"]=OLD; out["order"]=order
json.dump(out,open("agg.json","w"),indent=1)
print(f"{'#':2} {'mgr':7}{'rec':>5}{'title':>7}{'min':>6}{'max':>6}{'PO':>6}{'bye':>6}{'xW':>6}{'xFin':>6}{'bb':>7}{'bbR':>5}{'#1s':>4}  | old title/rank   delta | unlocked title rank")
for m in order:
    c=cons[m]; o=OLD[m]
    print(f"{c['rank']:2} {m:7}{c['rec']:>5}{c['title']:7.1f}{c['tmin']:6.1f}{c['tmax']:6.1f}{c['playoff']:6.1f}{c['bye']:6.1f}{c['xw']:6.2f}{c['xfin']:6.2f}{c['bb']:7.1f}{c['bbrank']:5}{c['firsts']:4}  | {o['title']:5.1f} #{o['rank']}  {c['title']-o['title']:+6.1f} | {c['u_title']:5.1f} #{c['u_rank']}")
print("\nengine table (title %)")
print(f"{'engine/cfg':20}"+"".join(f"{m[:6]:>8}" for m in M))
for k,v in out["engine_title"].items(): print(f"{k:20}"+"".join(f"{v[m]:8.1f}" for m in M))
