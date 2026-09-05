"""Incrementally snapshot the Best Ball Butts league from the Sleeper API into data/raw/.

Rules
-----
* A season whose league status is "complete" is frozen: nothing is re-fetched.
* For a live season, weeks older than SETTLE_WEEKS behind the current NFL week are
  frozen. The trailing window is re-fetched every run so stat corrections land;
  a file is only rewritten when its content actually changed (git diff = change log).
* League metadata (league/users/rosters/bracket) is refreshed every run for live seasons.

Usage:  python scripts/fetch.py            # incremental
        python scripts/fetch.py --all      # ignore freeze rules and re-fetch everything
"""
import json, sys, time, urllib.request, urllib.error
from pathlib import Path

USERNAME = "raghavr7"
LEAGUE_NAME = "Best Ball Butts"
FIRST_SEASON = 2024
SETTLE_WEEKS = 2
POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF"]

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
API = "https://api.sleeper.app"
FORCE = "--all" in sys.argv


def get(path, retries=3):
    url = path if path.startswith("http") else API + path
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def write_if_changed(path: Path, obj) -> bool:
    new = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    if path.exists() and path.read_text() == new:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new)
    return True


def discover_leagues():
    """season -> league_id for every season of this league the user has been in."""
    user = get(f"/v1/user/{USERNAME}")
    state = get("/v1/state/nfl")
    current = int(state["season"])
    found = {}
    for season in range(FIRST_SEASON, current + 1):
        for lg in get(f"/v1/user/{user['user_id']}/leagues/nfl/{season}") or []:
            if lg["name"] == LEAGUE_NAME:
                found[str(season)] = lg["league_id"]
    return found, state


def main():
    leagues, state = discover_leagues()
    current_season = str(state["season"])
    current_week = int(state.get("week") or 1)
    changed = []

    for season, lid in sorted(leagues.items()):
        d = RAW / season
        league_file = d / "league.json"
        frozen_season = (not FORCE) and league_file.exists() and json.loads(league_file.read_text()).get("status") == "complete"
        if frozen_season:
            print(f"{season}: complete, frozen")
            continue

        league = get(f"/v1/league/{lid}")
        drafts = get(f"/v1/league/{lid}/drafts") or []
        draft = next((x for x in drafts if x.get("status") == "complete"), drafts[0] if drafts else None)
        files = [("league.json", league),
                 ("users.json", get(f"/v1/league/{lid}/users")),
                 ("rosters.json", get(f"/v1/league/{lid}/rosters")),
                 ("winners_bracket.json", get(f"/v1/league/{lid}/winners_bracket")),
                 ("drafts.json", drafts)]
        if draft:
            files.append(("draft_picks.json", get(f"/v1/draft/{draft['draft_id']}/picks")))
        for name, obj in files:
            if write_if_changed(d / name, obj):
                changed.append(f"{season}/{name}")

        if league.get("status") in ("pre_draft", "drafting"):
            print(f"{season}: {league['status']}, no games yet")
            continue

        last_reg = league["settings"].get("playoff_week_start", 15) - 1
        # weeks that can have data: for the live season, up to the current NFL week
        upper = last_reg if season != current_season else min(last_reg, current_week)
        for w in range(1, upper + 1):
            mf = d / "matchups" / f"week_{w:02d}.json"
            pf = d / "projections" / f"week_{w:02d}.json"
            settled = (season != current_season) or (w < current_week - SETTLE_WEEKS)
            if settled and mf.exists() and pf.exists() and not FORCE:
                continue
            if write_if_changed(mf, get(f"/v1/league/{lid}/matchups/{w}")):
                changed.append(f"{season}/matchups/week_{w:02d}")
            qs = "&".join(f"position[]={p}" for p in POSITIONS)
            if write_if_changed(pf, get(f"/projections/nfl/{season}/{w}?season_type=regular&{qs}")):
                changed.append(f"{season}/projections/week_{w:02d}")
            time.sleep(0.2)
        print(f"{season}: checked weeks 1-{upper}")

    (RAW / "last_fetch.json").write_text(json.dumps({"nfl_state": state, "changed": changed}, indent=1))
    print("changed:", changed or "nothing")


if __name__ == "__main__":
    main()
