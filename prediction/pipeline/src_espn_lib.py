"""Shared: ESPN stat-id -> league points, using scoring.json. Validated in src_espn_validate2.py."""
import json, re, unicodedata
SC=json.load(open('scoring.json'))
FGCAL=json.load(open('src_espn_fgcal.json'))['fg_bonus_yds_over_30']
TIER_18_21_LE20=0.7473   # empirical share of ESPN 18-21 tier that is <=20 (Sleeper 14_20), from 2025 actuals

# ESPN stat id -> (scoring.json key, multiplier on the stat value)
OFF={3:('pass_yd',1),4:('pass_td',1),20:('pass_int',1),19:('pass_2pt',1),
     24:('rush_yd',1),25:('rush_td',1),26:('rush_2pt',1),
     42:('rec_yd',1),43:('rec_td',1),44:('rec_2pt',1),53:('rec',1),
     72:('fum_lost',1),63:('st_td',1)}
DEF={99:('sack',1),95:('int',1),96:('fum_rec',1),106:('ff',1),97:('blk_kick',1),
     98:('safe',1),105:('def_td',1)}
PA={89:'pts_allow_0',90:'pts_allow_1_6',91:'pts_allow_7_13',92:'pts_allow_14_20',
    122:'pts_allow_21_27',123:'pts_allow_28_34',124:'pts_allow_35p',125:'pts_allow_35p'}

def score(d, pos):
    """d: {int stat id: value}. pos: QB/RB/WR/TE/K/DEF. -> league fantasy points."""
    t=0.0
    if pos=='K':
        t+=d.get(80,0)*(SC['fgm']+SC['fgm_0_19']*0+SC['fgm_yds_over_30']*FGCAL['0_39'])
        t+=d.get(77,0)*(SC['fgm']+SC['fgm_40_49']+SC['fgm_yds_over_30']*FGCAL['40_49'])
        t+=d.get(74,0)*(SC['fgm']+SC['fgm_50p']  +SC['fgm_yds_over_30']*FGCAL['50p'])
        t+=d.get(85,0)*SC['fgmiss']+d.get(86,0)*SC['xpm']+d.get(88,0)*SC['xpmiss']
        return t
    if pos=='DEF':
        for sid,(k,m) in DEF.items(): t+=d.get(sid,0)*m*SC[k]
        for sid,k in PA.items(): t+=d.get(sid,0)*SC[k]
        t+=d.get(121,0)*(TIER_18_21_LE20*SC['pts_allow_14_20']+(1-TIER_18_21_LE20)*SC['pts_allow_21_27'])
        return t
    for sid,(k,m) in OFF.items(): t+=d.get(sid,0)*m*SC[k]
    return t

def espn_default(d,pos):
    """ESPN's own default-PPR recompute, for mapping validation vs appliedTotal."""
    if pos=='K': return d.get(74,0)*5+d.get(77,0)*4+d.get(80,0)*3+d.get(85,0)*-1+d.get(86,0)*1
    if pos=='DEF': return None
    return (d.get(3,0)*.04+d.get(4,0)*4+d.get(20,0)*-2+d.get(19,0)*2+d.get(24,0)*.1+d.get(25,0)*6
            +d.get(26,0)*2+d.get(42,0)*.1+d.get(43,0)*6+d.get(44,0)*2+d.get(53,0)*1+d.get(72,0)*-2+d.get(63,0)*6)

def norm(n):
    n=unicodedata.normalize('NFKD',n or '').encode('ascii','ignore').decode()
    n=n.lower().replace('.','').replace("'",'').replace('-',' ')
    n=re.sub(r'\b(jr|sr|ii|iii|iv|v)\b','',n)
    return re.sub(r'[^a-z ]','',n).split()
def nkey(n):
    p=norm(n)
    return (p[0]+' '+p[-1]) if len(p)>1 else ' '.join(p)
POSMAP={1:'QB',2:'RB',3:'WR',4:'TE',5:'K',16:'DEF'}
TEAM=json.load(open('src_espn_teammap.json'))
def team_of(p):
    a=TEAM.get(str(p['proTeamId'])) or TEAM.get(p['proTeamId'])
    return {'WSH':'WAS'}.get(a,a)
