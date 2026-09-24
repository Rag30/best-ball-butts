"""Fetch ESPN 2026 player pool (kona_player_info) + proTeam map. Writes src_espn_pool.json, src_espn_teammap.json."""
import json, urllib.request, time
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
BASE='https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026'
def get(url, flt=None):
    h={'User-Agent':UA,'Accept':'application/json'}
    if flt: h['X-Fantasy-Filter']=json.dumps(flt)
    with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=120) as r:
        return json.load(r)
pool={}; off=0; LIM=1000
while True:
    flt={"players":{"filterSlotIds":{"value":[0,2,4,6,17,16]},"limit":LIM,"offset":off,
                    "sortPercOwned":{"sortAsc":False,"sortPriority":1}}}
    d=get(BASE+'/segments/0/leaguedefaults/3?view=kona_player_info',flt)
    new=0
    for e in d['players']:
        p=e['player']
        if str(p['id']) not in pool: pool[str(p['id'])]=p; new+=1
    print(f"offset {off}: {len(d['players'])} rows, {new} new")
    if len(d['players'])<LIM or new==0: break
    off+=LIM; time.sleep(1)
json.dump(pool,open('src_espn_pool.json','w'))
t=get(BASE+'?view=proTeamSchedules_wl')
tm={str(x['id']):x['abbrev'].upper() for x in t['settings']['proTeams']}
json.dump(tm,open('src_espn_teammap.json','w'),indent=0)
print(len(pool),"players;",len(tm),"teams")
