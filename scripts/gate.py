"""Decide what this scheduled run should do, based on the real NFL schedule.

The workflow fires every 5 minutes. This script looks at today's NFL games
(ESPN public scoreboard, no key) and writes GitHub Actions outputs:

  run      = true|false   whether to fetch/compute/deploy at all
  mode     = game|hourly|archive|manual
  archive  = true|false   whether to commit data/raw + docs to git

Rules (all in America/New_York):
  * Game day  (any NFL game today)      -> run every 5 minutes
  * Other day                           -> run once an hour (the :00-:04 slot)
  * Tue & Fri 09:00 ET slot             -> also commit to git (the archive run)
  * Manual / button runs                -> rebuild only, unless the `archive` input is true
  * Off-season (no games this week and none next week) -> hourly still runs
    (cheap: fetch.py exits fast when the league is complete/pre-draft)
If ESPN is unreachable we assume it's a game day (better a few extra runs than
a stale page on Sunday).

Also snapshots the day's schedule into data/raw/nfl_schedule/<date>.json on
archive runs so game days are documented alongside the league data.
"""
import json, os, sys, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

ET = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parent.parent
ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={}"


def games_on(date_yyyymmdd: str):
    with urllib.request.urlopen(ESPN.format(date_yyyymmdd), timeout=20) as r:
        d = json.load(r)
    return [{"date": e["date"], "name": e["name"], "status": e.get("status", {}).get("type", {}).get("name")}
            for e in d.get("events", [])]


def main():
    now = datetime.now(ET)
    event = os.environ.get("GITHUB_EVENT_NAME", "schedule")
    today = now.strftime("%Y%m%d")

    try:
        games = games_on(today)
        espn_ok = True
    except Exception as e:  # noqa: BLE001
        print(f"ESPN unreachable ({e}); assuming game day", file=sys.stderr)
        games, espn_ok = [], False

    game_day = (not espn_ok) or bool(games)
    hourly_slot = now.minute < 5
    archive_slot = now.weekday() in (1, 4) and now.hour == 9 and hourly_slot  # Tue/Fri 09:00 ET

    if event == "push":
        run, mode, archive = True, "push", False      # code change: always rebuild + deploy
    elif event == "workflow_dispatch":
        # Manual/button runs rebuild the page but only commit the archive if explicitly asked
        run, mode, archive = True, "manual", os.environ.get("ARCHIVE_INPUT", "false").lower() == "true"
    elif archive_slot:
        run, mode, archive = True, "archive", True
    elif game_day:
        run, mode, archive = True, "game", False
    else:
        run, mode, archive = hourly_slot, "hourly", False

    if archive and espn_ok:
        out = ROOT / "data" / "raw" / "nfl_schedule"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{today}.json").write_text(json.dumps(games, indent=1))

    summary = f"{now:%a %Y-%m-%d %H:%M ET} | games today: {len(games) if espn_ok else '?'} | run={run} mode={mode} archive={archive}"
    print(summary)
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"run={'true' if run else 'false'}\nmode={mode}\narchive={'true' if archive else 'false'}\n")


if __name__ == "__main__":
    main()
