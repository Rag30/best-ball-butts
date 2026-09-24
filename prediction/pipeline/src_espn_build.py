import sys as _s, os as _o; _s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__))); from wk import START
import json, collections, src_espn_lib as L
pool=json.load(open('src_espn_pool.json'))
rost=json.load(open('rostered_players.json'))
byes=json.load(open('byes_2026.json'))

# index ESPN pool
esp_by_id={str(p['id']):p for p in pool.values()}
esp_by_name=collections.defaultdict(list)
esp_def={}
for p in pool.values():
    pos=L.POSMAP.get(p['defaultPositionId'])
    if pos=='DEF': esp_def[L.team_of(p)]=p
    elif pos: esp_by_name[(L.nkey(p['fullName']),pos)].append(p)

proj={}; miss=[]; how=collections.Counter(); matched={}
for pid,v in rost.items():
    pos=v['pos']
    if pos not in ('QB','RB','WR','TE','K','DEF'):
        miss.append((v['name'],pos,v['team'],'non-scoring position (sim ignores)')); continue
    p=None; via=None
    if pos=='DEF':
        p=esp_def.get(v['team']); via='team'
    else:
        if v.get('espn_id') and str(v['espn_id']) in esp_by_id:
            p=esp_by_id[str(v['espn_id'])]; via='espn_id'
        if p is None:
            cands=esp_by_name.get((L.nkey(v['name']),pos),[])
            if len(cands)==1: p,via=cands[0],'name+pos'
            elif len(cands)>1:
                t=[c for c in cands if L.team_of(c)==v['team']]
                if len(t)==1: p,via=t[0],'name+pos+team'
                elif t: p,via=t[0],'name+pos+team(ambig)'
    if p is None:
        miss.append((v['name'],pos,v['team'],'no ESPN match')); continue
    wk={}
    for s in p.get('stats',[]):
        if s['seasonId']==2026 and s['statSourceId']==1 and s['statSplitTypeId']==1 and 3<=s["scoringPeriodId"]<=17 and s.get('stats'):
            d={int(k):val for k,val in s['stats'].items()}
            wk[str(s['scoringPeriodId'])]=round(L.score(d,pos),2)
    if not wk:
        miss.append((v['name'],pos,v['team'],'ESPN rows for wks 3-17 exist but are EMPTY (ESPN blanked rest-of-season; injury=%s)'%p.get('injuryStatus'))); continue
    for w in range(START,18):
        wk.setdefault(str(w),0.0)
        if w in byes.get(v['team'],[]): wk[str(w)]=0.0
    proj[pid]=wk; how[via]+=1; matched[pid]=(v['name'],pos,v['team'],p['fullName'],L.team_of(p))

json.dump(proj,open('proj_espn.json','w'),indent=1)
print(f"WROTE proj_espn.json : {len(proj)} / {len(rost)} rostered ids  (rostered non-DB = {sum(1 for v in rost.values() if v['pos']!='DB')})")
print("match method:",dict(how))
print("\nNOT COVERED (%d):"%len(miss))
for n,ps,t,why in miss: print(f"   {n:26} {ps:4} {t or '--':4}  {why}")
# team disagreements among matches (sanity)
bad=[(a[0],a[2],a[4]) for a in matched.values() if a[1]!='DEF' and a[2] and a[4] and a[2]!=a[4]]
print("\nteam mismatch between Sleeper and ESPN (info only): %d"%len(bad))
for n,st,et in bad[:20]: print(f"   {n:26} sleeper={st} espn={et}")
