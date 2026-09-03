"""Recompute every derived table from data/raw -> data/derived/seasons.json.

Pure function of the raw Sleeper snapshots; safe to re-run any time (e.g. after a
stat correction or a formula change).
"""
import json, statistics, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DERIVED = ROOT / "data" / "derived"

def raw(season, *parts):
    return RAW / str(season) / Path(*parts)

def load_json(p):
    with open(p) as f:
        return json.load(f)

# ---------------- projections -> optimal projected lineup per team/week ----------------
FLEX = {"RB", "WR", "TE"}

def player_pts(stats, scoring):
    return sum(scoring[k] * v for k, v in stats.items() if k in scoring and isinstance(v, (int, float)))

def optimal_lineup(proj_by_pid, roster_pids, slots):
    pool = sorted(((p["pts"], p["pos"], pid) for pid in roster_pids if (p := proj_by_pid.get(pid))), reverse=True)
    used, total = set(), 0.0
    for s in [s for s in slots if s not in ("FLEX", "BN")]:
        for pts, pos, pid in pool:
            if pid not in used and pos == s:
                used.add(pid); total += pts; break
    for _ in [s for s in slots if s == "FLEX"]:
        for pts, pos, pid in pool:
            if pid not in used and pos in FLEX:
                used.add(pid); total += pts; break
    return round(total, 2)

def team_projections(season, name_map, weeks):
    """{name: {week: projected_pts}} for weeks that have both matchups and projections."""
    lg = load_json(raw(season, "league.json"))
    scoring, slots = lg["scoring_settings"], lg["roster_positions"]
    out = {}
    for w in weeks:
        pf = raw(season, "projections", f"week_{w:02d}.json")
        mf = raw(season, "matchups", f"week_{w:02d}.json")
        if not (pf.exists() and mf.exists()):
            continue
        by_pid = {e["player_id"]: {"pts": player_pts(e.get("stats") or {}, scoring),
                                   "pos": (e.get("player") or {}).get("position")} for e in load_json(pf)}
        for e in load_json(mf):
            out.setdefault(name_map[e["roster_id"]], {})[w] = optimal_lineup(by_pid, e.get("players") or [], slots)
    return out

NAME_MAP = {1:"Conrad",2:"Lauren",3:"Emma",4:"Raghav",5:"Avery",6:"Ben",7:"Noelle",8:"Henry"}

def load_season(weeks_dir, weeks_range):
    rids = list(NAME_MAP.keys())
    scores = {r: {} for r in rids}
    opponent = {r: {} for r in rids}
    result = {r: {} for r in rids}
    for w in weeks_range:
        data = load_json(raw(weeks_dir, "matchups", f"week_{w:02d}.json"))
        by_mid = {}
        for e in data:
            by_mid.setdefault(e['matchup_id'], []).append(e)
        for mid, entries in by_mid.items():
            if len(entries) != 2:
                continue
            a, b = entries
            scores[a['roster_id']][w] = round(a['points'],2)
            scores[b['roster_id']][w] = round(b['points'],2)
            opponent[a['roster_id']][w] = b['roster_id']
            opponent[b['roster_id']][w] = a['roster_id']
            if a['points'] > b['points']:
                result[a['roster_id']][w] = 'W'; result[b['roster_id']][w] = 'L'
            elif b['points'] > a['points']:
                result[b['roster_id']][w] = 'W'; result[a['roster_id']][w] = 'L'
            else:
                result[a['roster_id']][w] = 'T'; result[b['roster_id']][w] = 'T'
    return rids, scores, opponent, result

def build_season(weeks_dir, weeks_range, name_map=NAME_MAP, projections=None):
    rids, scores, opponent, result = load_season(weeks_dir, weeks_range)
    weeks = list(weeks_range)
    # projections: {name: {week: projected_pts}} -> remap to roster id
    proj = {}
    if projections:
        for r in rids:
            proj[r] = {int(w): v for w, v in projections.get(name_map[r], {}).items()}
    season_avg = {r: statistics.mean(scores[r].values()) for r in rids}

    def last3_avg_strict(r, w):
        idx = weeks.index(w)
        if idx < 3: return None
        prior_weeks = weeks[idx-3:idx]
        window = [scores[r][x] for x in prior_weeks]
        return round(statistics.mean(window), 2)

    ui1 = {r: {w: round(scores[opponent[r][w]][w] - season_avg[opponent[r][w]],2) for w in weeks} for r in rids}
    ui2 = {}
    last3vals = {}
    for r in rids:
        ui2[r] = {}; last3vals[r] = {}
        for w in weeks:
            opp = opponent[r][w]
            la = last3_avg_strict(opp, w)
            last3vals[r][w] = la
            ui2[r][w] = round(scores[opp][w] - la, 2) if la is not None else None

    # ---- Recommended flavor: outcome-weighted, expanding (no-lookahead) baseline ----
    def expanding_avg(r, w):
        idx = weeks.index(w)
        if idx == 0: return None
        prior_weeks = weeks[:idx]
        return round(statistics.mean(scores[r][x] for x in prior_weeks), 2)

    def sign(x):
        return (x > 0) - (x < 0)

    ui3 = {}
    flips = {}
    for r in rids:
        ui3[r] = {}; flips[r] = {}
        for w in weeks:
            opp = opponent[r][w]
            base = expanding_avg(opp, w)
            if base is None:
                ui3[r][w] = None; flips[r][w] = None
                continue
            d = round(scores[opp][w] - base, 2)
            my_margin = round(scores[r][w] - scores[opp][w], 2)
            counterfactual = round(my_margin - d, 2)
            flipped = sign(my_margin) != sign(counterfactual)
            weight = 1.0 if flipped else 0.35
            ui3[r][w] = round(d * weight, 2)
            flips[r][w] = flipped

    # ---- Roster Luck (vs Sleeper projection) and Net Luck (roster + schedule), outcome-gated ----
    # Best-ball optimal lineups beat projections for everyone, so measure each team's
    # projection error RELATIVE to the league's mean error that week.
    proj_mean = {}
    for w in weeks:
        errs = [scores[r][w] - proj[r][w] for r in rids if proj.get(r, {}).get(w) is not None]
        proj_mean[w] = round(statistics.mean(errs), 2) if errs else None
    ui4 = {}; flips4 = {}; ui5 = {}; flips5 = {}; projinfo = {}
    for r in rids:
        ui4[r] = {}; flips4[r] = {}; ui5[r] = {}; flips5[r] = {}; projinfo[r] = {}
        for w in weeks:
            opp = opponent[r][w]
            my_margin = round(scores[r][w] - scores[opp][w], 2)
            p_me = proj.get(r, {}).get(w)
            projinfo[r][w] = p_me
            if p_me is None or proj_mean[w] is None:
                ui4[r][w] = None; flips4[r][w] = None; ui5[r][w] = None; flips5[r][w] = None
                continue
            d_me = round(scores[r][w] - p_me - proj_mean[w], 2)   # my error vs league's error that week
            # Roster luck: positive = I underperformed = unlucky
            cf = round(my_margin - d_me, 2)                # margin if I had hit my projection
            fl = sign(my_margin) != sign(cf)
            ui4[r][w] = round(-d_me * (1.0 if fl else 0.35), 2); flips4[r][w] = fl
            # Net luck: schedule deviation (opp vs trailing avg) + roster deviation
            base = expanding_avg(opp, w)
            if base is None:
                ui5[r][w] = None; flips5[r][w] = None
                continue
            d_opp = round(scores[opp][w] - base, 2)
            cf2 = round(my_margin - d_opp - d_me, 2)
            fl2 = sign(my_margin) != sign(cf2)
            ui5[r][w] = round((d_opp - d_me) * (1.0 if fl2 else 0.35), 2); flips5[r][w] = fl2

    weekly_median = {w: round(statistics.median([scores[r][w] for r in rids]), 2) for w in weeks}
    median_result = {r: {w: ('W' if scores[r][w] > weekly_median[w] else ('L' if scores[r][w] < weekly_median[w] else 'T')) for w in weeks} for r in rids}
    margin = {r: {w: round(scores[r][w] - scores[opponent[r][w]][w], 2) for w in weeks} for r in rids}

    def summarize(ui):
        out = {}
        for r in rids:
            vals = [v for v in ui[r].values() if v is not None]
            unlucky = sum(1 for v in vals if v > 0)
            lucky = sum(1 for v in vals if v < 0)
            total = round(sum(vals),2)
            weekly = round(total/len(vals),2) if vals else 0
            out[name_map[r]] = dict(unlucky=unlucky, lucky=lucky, total=total, weekly=weekly)
        return out

    sum1 = summarize(ui1)
    sum2 = summarize(ui2)
    sum3 = summarize(ui3)
    sum4 = summarize(ui4)
    sum5 = summarize(ui5)

    standings = []
    median_standings = []
    for r in rids:
        wins = sum(1 for v in result[r].values() if v=='W')
        losses = sum(1 for v in result[r].values() if v=='L')
        mwins = sum(1 for v in median_result[r].values() if v=='W') + wins
        mlosses = sum(1 for v in median_result[r].values() if v=='L') + losses
        pf = round(sum(scores[r].values()),2)
        pa = round(sum(scores[opponent[r][w]][w] for w in weeks),2)
        avg = round(statistics.mean(scores[r].values()),2)
        sd = round(statistics.pstdev(scores[r].values()),2)
        standings.append(dict(name=name_map[r], wins=wins, losses=losses, pf=pf, pa=pa, avg=avg, sd=sd))
        median_standings.append(dict(name=name_map[r], wins=mwins, losses=mlosses, pf=pf))
    standings.sort(key=lambda x: (-x['wins'], -x['pf']))
    median_standings.sort(key=lambda x: (-x['wins'], -x['pf']))

    # ---- weekly reports ----
    cum_w = {r: 0 for r in rids}
    cum_l = {r: 0 for r in rids}
    streak = {r: 0 for r in rids}  # positive = win streak, negative = loss streak
    prev_rank = None
    weekly_reports = []
    for w in weeks:
        # scores this week
        wk_scores = {r: scores[r][w] for r in rids}
        top_r = max(wk_scores, key=wk_scores.get)
        low_r = min(wk_scores, key=wk_scores.get)

        losers_scores = {r: wk_scores[r] for r in rids if result[r][w] == 'L'}
        winners_scores = {r: wk_scores[r] for r in rids if result[r][w] == 'W'}
        highest_in_loss = max(losers_scores, key=losers_scores.get) if losers_scores else None
        lowest_in_win = min(winners_scores, key=winners_scores.get) if winners_scores else None

        margins_this_wk = {r: margin[r][w] for r in rids if result[r][w] == 'W'}
        biggest_vic = max(margins_this_wk, key=margins_this_wk.get) if margins_this_wk else None
        narrowest_vic = min(margins_this_wk, key=margins_this_wk.get) if margins_this_wk else None

        over = {r: round(wk_scores[r] - season_avg[r], 2) for r in rids}
        overachiever = max(over, key=over.get)
        underachiever = min(over, key=over.get)

        # update cumulative records + streaks
        for r in rids:
            if result[r][w] == 'W':
                cum_w[r] += 1
                streak[r] = streak[r] + 1 if streak[r] >= 0 else 1
            elif result[r][w] == 'L':
                cum_l[r] += 1
                streak[r] = streak[r] - 1 if streak[r] <= 0 else -1

        # rank after this week
        rank_order = sorted(rids, key=lambda r: (-cum_w[r], -sum(scores[r][x] for x in weeks if x <= w)))
        rank = {r: i+1 for i, r in enumerate(rank_order)}
        rank_change = {r: (prev_rank[r] - rank[r]) if prev_rank else 0 for r in rids}
        prev_rank = rank

        weekly_reports.append(dict(
            week=w,
            topScorer=dict(name=name_map[top_r], score=wk_scores[top_r]),
            lowScorer=dict(name=name_map[low_r], score=wk_scores[low_r]),
            highestInLoss=(dict(name=name_map[highest_in_loss], score=wk_scores[highest_in_loss]) if highest_in_loss else None),
            lowestInWin=(dict(name=name_map[lowest_in_win], score=wk_scores[lowest_in_win]) if lowest_in_win else None),
            biggestVictory=(dict(name=name_map[biggest_vic], margin=margins_this_wk[biggest_vic], opp=name_map[opponent[biggest_vic][w]]) if biggest_vic else None),
            narrowestVictory=(dict(name=name_map[narrowest_vic], margin=margins_this_wk[narrowest_vic], opp=name_map[opponent[narrowest_vic][w]]) if narrowest_vic else None),
            overachiever=dict(name=name_map[overachiever], delta=over[overachiever]),
            underachiever=dict(name=name_map[underachiever], delta=over[underachiever]),
            standings=[dict(name=name_map[r], wins=cum_w[r], losses=cum_l[r], rankChange=rank_change[r], streak=streak[r]) for r in rank_order],
        ))

    return {
        "managers": [name_map[r] for r in rids],
        "weeks": weeks,
        "scores": {name_map[r]: [scores[r][w] for w in weeks] for r in rids},
        "opponents": {name_map[r]: [name_map[opponent[r][w]] for w in weeks] for r in rids},
        "oppScores": {name_map[r]: [scores[opponent[r][w]][w] for w in weeks] for r in rids},
        "results": {name_map[r]: [result[r][w] for w in weeks] for r in rids},
        "medianResults": {name_map[r]: [median_result[r][w] for w in weeks] for r in rids},
        "weeklyMedian": [weekly_median[w] for w in weeks],
        "margin": {name_map[r]: [margin[r][w] for w in weeks] for r in rids},
        "seasonAvg": {name_map[r]: round(season_avg[r],2) for r in rids},
        "last3Avg": {name_map[r]: [last3vals[r][w] for w in weeks] for r in rids},
        "ui1": {name_map[r]: [ui1[r][w] for w in weeks] for r in rids},
        "ui2": {name_map[r]: [ui2[r][w] for w in weeks] for r in rids},
        "ui3": {name_map[r]: [ui3[r][w] for w in weeks] for r in rids},
        "flips3": {name_map[r]: [flips[r][w] for w in weeks] for r in rids},
        "sum3": sum3,
        "ui4": {name_map[r]: [ui4[r][w] for w in weeks] for r in rids},
        "flips4": {name_map[r]: [flips4[r][w] for w in weeks] for r in rids},
        "sum4": sum4,
        "ui5": {name_map[r]: [ui5[r][w] for w in weeks] for r in rids},
        "flips5": {name_map[r]: [flips5[r][w] for w in weeks] for r in rids},
        "sum5": sum5,
        "projected": {name_map[r]: [projinfo[r][w] for w in weeks] for r in rids},
        "projMean": [proj_mean[w] for w in weeks],
        "sum1": sum1,
        "sum2": sum2,
        "standings": standings,
        "medianStandings": median_standings,
        "weeklyReports": weekly_reports,
    }

NAME_MAP_2024 = {1:"Conrad",2:"Lauren",3:"Emma",4:"Raghav",5:"Steve",6:"Ben",7:"Noelle",8:"Henry"}
NAME_MAP_2025 = {1:"Conrad",2:"Lauren",3:"Emma",4:"Raghav",5:"Avery",6:"Ben",7:"Noelle",8:"Henry"}

# ---------------- discover seasons from data/raw ----------------
def scored_weeks(season):
    """Regular-season weeks that have a matchup snapshot with real scores."""
    lg = load_json(raw(season, "league.json"))
    last_reg = lg["settings"].get("playoff_week_start", 15) - 1
    weeks = []
    for w in range(1, last_reg + 1):
        f = raw(season, "matchups", f"week_{w:02d}.json")
        if f.exists() and any((e.get("points") or 0) > 0 for e in load_json(f)):
            weeks.append(w)
    return weeks

SEASONS = sorted(p.name for p in RAW.iterdir() if p.is_dir() and (p / "league.json").exists())

def league_name_map(season):
    """roster_id -> manager first name, via users.json display names (mapped in MANAGERS)."""
    users = {u["user_id"]: u["display_name"] for u in load_json(raw(season, "users.json"))}
    return {r["roster_id"]: MANAGERS.get(users.get(r["owner_id"]), users.get(r["owner_id"], f"Seat {r['roster_id']}"))
            for r in load_json(raw(season, "rosters.json"))}

# Sleeper display name -> the name the league actually uses
MANAGERS = {
    "plankrad": "Conrad", "bballlauren": "Lauren", "lilmisseb": "Emma", "Raghavr7": "Raghav",
    "1babyjesus": "Steve", "averymc03": "Avery", "mac003": "Avery",
    "dragonslayyyer69": "Ben", "NoLsHere": "Noelle", "TheDragon96": "Henry",
}

built = {}
name_maps = {}
for s in SEASONS:
    weeks = scored_weeks(s)
    nm = league_name_map(s)
    name_maps[s] = nm
    if not weeks:
        continue
    built[s] = build_season(s, weeks, nm, team_projections(s, nm, weeks))

# ---- real playoff results (from Sleeper winners_bracket, not regular-season seed) ----
def playoff_finish(season, name_map):
    f = raw(season, "winners_bracket.json")
    bracket = load_json(f) if f.exists() else []
    if not any(m.get("p") == 1 and m.get("w") for m in bracket):
        return {}
    final = [m for m in bracket if m.get('p') == 1][0]
    third = [m for m in bracket if m.get('p') == 3][0]
    champ_r = final['w']
    runner_r = final['t1'] if final['w'] == final['t2'] else (final['t2'] if final['w'] == final['t1'] else None)
    runner_r = final['t2'] if final['w'] == final['t1'] else final['t1']
    third_r = third['w']
    fourth_r = third['t2'] if third['w'] == third['t1'] else third['t1']
    return {
        name_map[champ_r]: "Champion",
        name_map[runner_r]: "Runner-up",
        name_map[third_r]: "3rd Place",
        name_map[fourth_r]: "4th Place",
    }

finishes = {}
for s, sd in built.items():
    finishes[s] = playoff_finish(s, name_maps[s])
    for row in sd["standings"]:
        row["playoffResult"] = finishes[s].get(row["name"], "—")

# ---- master / all-time tab ----
# Seat 5 was Steve in 2024, Avery from 2025 on -- combine career stats under "Avery"
career_stats = {}
def ensure(k):
    if k not in career_stats:
        career_stats[k] = dict(seasons=0, wins=0, losses=0, pf=0.0, medianWins=0, medianLosses=0,
                                championships=0, runnerUps=0, thirds=0)
    return career_stats[k]

for sdata, finish in [(built[s], finishes[s]) for s in sorted(built)]:
    for s in sdata["standings"]:
        name = s["name"]
        key = "Avery" if name in ("Avery", "Steve") else name
        c = ensure(key)
        c["seasons"] += 1
        c["wins"] += s["wins"]
        c["losses"] += s["losses"]
        c["pf"] += s["pf"]
        result = finish.get(name)
        if result == "Champion": c["championships"] += 1
        elif result == "Runner-up": c["runnerUps"] += 1
        elif result == "3rd Place": c["thirds"] += 1
    for ms in sdata["medianStandings"]:
        name = ms["name"]
        key = "Avery" if name in ("Avery", "Steve") else name
        c = ensure(key)
        c["medianWins"] += ms["wins"]
        c["medianLosses"] += ms["losses"]

career_list = []
for k, v in career_stats.items():
    v = dict(v)
    v["name"] = k
    v["pf"] = round(v["pf"], 2)
    career_list.append(v)
career_list.sort(key=lambda x: (-x["championships"], -x["wins"], -x["pf"]))

seasons_out = {}
for s in SEASONS:
    if s in built:
        seasons_out[s] = built[s]
    else:
        lg = load_json(raw(s, "league.json"))
        nm = name_maps[s]
        seasons_out[s] = {"notStarted": True, "status": lg.get("status", "pre_draft"),
                          "managers": [nm[r] for r in sorted(nm)]}

out = {
    "seasons": seasons_out,
    "career": career_list,
    "seatNote": "Seat 5 was Steve in 2024 and is Avery starting 2025; career stats for that seat are combined under Avery.",
    "generatedFrom": {s: scored_weeks(s) for s in SEASONS},
}

DERIVED.mkdir(parents=True, exist_ok=True)
with open(DERIVED / "seasons.json", "w") as f:
    json.dump(out, f, indent=1)
print("wrote", DERIVED / "seasons.json", os.path.getsize(DERIVED / "seasons.json"), "bytes;",
      {s: len(w) for s, w in out["generatedFrom"].items()}, "scored weeks")
