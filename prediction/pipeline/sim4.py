import sys as _s, os as _o; _s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__))); from wk import START
"""Best Ball Butts 2026 season simulator, Week-3 edition (sim3.py + the Week-1 repair-pass fixes + multi-week locking).
Usage: uv run --with numpy --with scipy python sim4.py --proj proj_X.json [--noise normal|gamma] [--corr 0.25] [--injury 1]
       [--lock 2] [--teamsd 4.0] [--weeksd 0.0] [--sdA 3.5] [--sdB 0.28] [--n 8000] [--seed 11] [--out result_X.json]
Projection format: {player_id: {"3": pts, ..., "17": pts}}  OR  {player_id: {"ros": total_pts_weeks_(lock+1)_to_17}}
  ("ros" is spread evenly over the player's non-bye remaining weeks).
--lock L : weeks 1..L are locked to the actual Sleeper results in m26_w{w}.json (L=0 = pure roster strength, nothing locked).
Carried over from the Week-1 repair pass: weeksd default 0 (player model alone matches 2025 weekly SD); one shared
same-NFL-team shock per week across all rosters; bracket = Sleeper's own (1 v W(4v5), 2 v W(3v6)); non-skill (DB) excluded.
"""
import json, argparse, numpy as np
from collections import defaultdict
ap=argparse.ArgumentParser()
ap.add_argument("--proj",required=True); ap.add_argument("--noise",default="normal"); ap.add_argument("--corr",type=float,default=0.0)
ap.add_argument("--injury",type=float,default=0.0); ap.add_argument("--lock",type=int,default=START-1)
ap.add_argument("--teamsd",type=float,default=4.0); ap.add_argument("--weeksd",type=float,default=0.0)
ap.add_argument("--sdA",type=float,default=3.5); ap.add_argument("--sdB",type=float,default=0.28)
ap.add_argument("--n",type=int,default=8000); ap.add_argument("--seed",type=int,default=11); ap.add_argument("--out",default=None)
a=ap.parse_args(); rng=np.random.default_rng(a.seed); N=a.n; L=a.lock
rost=json.load(open("rostered_players.json")); byes=json.load(open("byes_2026.json")); raw=json.load(open(a.proj))
POS={"QB":0,"RB":1,"WR":2,"TE":3,"K":4,"DEF":5}; NEED={"QB":1,"RB":2,"WR":2,"TE":1,"K":1,"DEF":1}
INJ_RATE={"QB":0.012,"RB":0.030,"WR":0.022,"TE":0.022,"K":0.003,"DEF":0.0}
SW=list(range(L+1,18))  # simulated weeks
def weekly(pid):
    d=raw.get(pid) or {}
    if "ros" in d:
        t=rost[pid]["team"]; g=[w for w in SW if w>=START and w not in byes.get(t,[])]; per=d["ros"]/len(g) if g else 0
        return {w:(per if (w in g or w<START) else 0.0) for w in SW}
    out={w:float(d.get(str(w),0) or 0) for w in SW if w>=START}
    if any(w<START for w in SW):  # --lock 0/1: weeks 1-2 have no projection -> the player's mean non-bye week 3-17 projection
        t=rost[pid]["team"]; g=[w for w in range(START,18) if w not in byes.get(t,[])]; avg=sum(out.get(w,0) for w in g)/len(g) if g else 0
        out.update({w:avg for w in SW if w<START})
    return out
rost={p:v for p,v in rost.items() if v["pos"] in POS}
P={pid:weekly(pid) for pid in rost}
mgrs=sorted({v["manager"] for v in rost.values()}); rid={v["manager"]:v["roster_id"] for v in rost.values()}
byr={m:[p for p,v in rost.items() if v["manager"]==m] for m in mgrs}
avail={}
if a.injury>0:
    for pid,v in rost.items():
        r=INJ_RATE[v["pos"]]*a.injury; mask=np.ones((N,18),bool); out=np.zeros(N,int)
        for w in SW:
            new=(rng.random(N)<r)&(out==0); dur=rng.geometric(1/3.0,N)
            out=np.where(new,dur,out); mask[:,w]=out==0; out=np.maximum(out-1,0)
        avail[pid]=mask
ALLTEAMS=sorted({(v["team"] or "FA") for v in rost.values()}); _TZ={}
def team_z(w):
    if w not in _TZ: _TZ[w]={t:rng.normal(size=N) for t in ALLTEAMS}
    return _TZ[w]
def team_scores(pids,w):
    pv=np.array([P[p][w] for p in pids]); ps=np.array([POS[rost[p]["pos"]] for p in pids]); teams=[rost[p]["team"] or "FA" for p in pids]
    sd=a.sdA+a.sdB*pv; mu=pv; z=rng.normal(size=(N,len(pids)))
    if a.corr>0:
        tz=team_z(w); z=np.sqrt(a.corr)*np.stack([tz[t] for t in teams],axis=1)+np.sqrt(1-a.corr)*z
    if a.noise=="normal": sim=np.maximum(mu+sd*z,-2)
    else:
        from scipy.stats import norm, gamma as G
        m=np.maximum(mu,0.05); k=(m/sd)**2; th=sd**2/m; sim=G.ppf(norm.cdf(z),k[None,:],scale=th[None,:])
    sim[:,pv<=0]=0
    if avail:
        for j,p in enumerate(pids): sim[:,j]*=avail[p][:,w]
    tot=np.zeros(N); flex=[]
    for pos,k in NEED.items():
        cols=np.where(ps==POS[pos])[0]
        if len(cols)==0: continue
        s=-np.sort(-sim[:,cols],axis=1); tot+=s[:,:k].sum(1)
        if pos in("RB","WR","TE"): flex.append(s[:,k:])
    fx=np.concatenate(flex,axis=1) if flex else np.zeros((N,0))
    if fx.shape[1]: tot+=(-np.sort(-fx,axis=1))[:,:2].sum(1)
    return tot
def paper(pids,w):
    tot=0; flex=[]
    for pos,k in NEED.items():
        s=sorted([P[p][w] for p in pids if rost[p]["pos"]==pos],reverse=True); tot+=sum(s[:k])
        if pos in("RB","WR","TE"): flex+=s[k:]
    return tot+sum(sorted(flex,reverse=True)[:2])
def pairs(M):
    by=defaultdict(list)
    for e in M: by[e["matchup_id"]].append(e["roster_id"])
    return [tuple(v) for v in by.values()]
MW={w:json.load(open(f"m26_w{w}.json")) for w in range(1,15)}
sched={w:pairs(MW[w]) for w in range(1,15)}; actual={w:{e["roster_id"]:e["points"] for e in MW[w]} for w in range(1,L+1)}
ids=[rid[m] for m in mgrs]; name={rid[m]:m for m in mgrs}
S={}; PAPER={}; eff={r:rng.normal(0,a.teamsd,N) for r in ids}
for w in SW:
    for r in ids:
        S[(w,r)]=team_scores(byr[name[r]],w)+eff[r]+(rng.normal(0,a.weeksd,N) if a.weeksd>0 else 0); PAPER[(w,r)]=paper(byr[name[r]],w)
W={r:np.zeros(N) for r in ids}; PF={r:np.zeros(N) for r in ids}
for w in range(1,15):
    for x,y in sched[w]:
        if w<=L: sx=np.full(N,actual[w][x]); sy=np.full(N,actual[w][y])
        else: sx=S[(w,x)]; sy=S[(w,y)]
        PF[x]+=sx; PF[y]+=sy; W[x]+=(sx>sy)+0.5*(sx==sy); W[y]+=(sy>sx)+0.5*(sx==sy)
key=np.stack([-(W[r]*1e6+PF[r]) for r in ids],axis=1); seeds=np.array(ids)[np.argsort(key,axis=1)]
def g(x,y,w):
    sx=np.array([S[(w,v)][i] for i,v in enumerate(x)]); sy=np.array([S[(w,v)][i] for i,v in enumerate(y)]); return np.where(sx>sy,x,y)
s1,s2,s3,s4,s5,s6,s7,s8=[seeds[:,i] for i in range(8)]
wA=g(s3,s6,15); wB=g(s4,s5,15); f1=g(s1,wB,16); f2=g(s2,wA,16); c=g(f1,f2,17); ru=np.where(c==f1,f2,f1)
l1=np.where(f1==s1,wB,s1); l2=np.where(f2==s2,wA,s2); third=g(l1,l2,17); fourth=np.where(third==l1,l2,l1)
r1a=np.where(wA==s3,s6,s3); r1b=np.where(wB==s4,s5,s4); fifth=g(r1a,r1b,16); sixth=np.where(fifth==r1a,r1b,r1a)
seventh=g(s7,s8,15); eighth=np.where(seventh==s7,s8,s7)
place=np.stack([c,ru,third,fourth,fifth,sixth,seventh,eighth],axis=1)
RW=[w for w in SW if w<=14]
res={}
for r in ids:
    fin={k:float(np.mean(place[:,k-1]==r)) for k in range(1,9)}; sd_={k:float(np.mean(seeds[:,k-1]==r)) for k in range(1,9)}
    res[name[r]]=dict(locked_w=float(sum((actual[w][r]>actual[w][[p for p in sum(sched[w],()) if p!=r and (r,p) in [(x,y) for x,y in sched[w]]+[(y,x) for x,y in sched[w]]][0]]) for w in range(1,L+1))),
        locked_pf=float(sum(actual[w][r] for w in range(1,L+1))),x_wins=float(W[r].mean()),x_pf=float(PF[r].mean()),
        bb_avg=float(np.mean([S[(w,r)].mean() for w in RW])),paper_avg=float(np.mean([PAPER[(w,r)] for w in RW])),
        wk_sd=float(np.mean([S[(w,r)].std() for w in RW])),
        playoff=sum(sd_[k] for k in range(1,7)),bye=sd_[1]+sd_[2],seed1=sd_[1],final=fin[1]+fin[2],title=fin[1],
        x_finish=sum(k*v for k,v in fin.items()),finish=fin,seed=sd_,weekly_bb={w:float(S[(w,r)].mean()) for w in SW},
        weekly_paper={w:PAPER[(w,r)] for w in SW})
print(f"config: {vars(a)}\n{'Manager':8}{'rec':>5}{'paper':>7}{'BBavg':>7}{'wkSD':>6}{'xW':>6}{'xPF':>6}{'PO':>6}{'Bye':>6}{'Final':>7}{'Title':>7}{'xFin':>6}")
for m,v in sorted(res.items(),key=lambda kv:-kv[1]["title"]):
    print(f"{m:8}{int(v['locked_w']):>3}-{L-int(v['locked_w'])}{v['paper_avg']:7.1f}{v['bb_avg']:7.1f}{v['wk_sd']:6.1f}{v['x_wins']:6.2f}{v['x_pf']:6.0f}{v['playoff']:6.0%}{v['bye']:6.0%}{v['final']:7.0%}{v['title']:7.1%}{v['x_finish']:6.2f}")
if a.out: json.dump({"config":vars(a),"results":res},open(a.out,"w"),indent=1)
