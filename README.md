# Best Ball Butts

League archive and the Unluckiness Index™ for the *Best Ball Butts* Sleeper league.

**Live site:** https://bestballbutts.rrr-projects.com (also at https://rag30.github.io/best-ball-butts/)

## How it works

```
Sleeper API ──fetch.py──▶ data/raw/        (immutable snapshots, the "database")
                                │
                        compute-node.js  ── uses scripts/compute.js
                                │
                                ▼
                          data/derived/seasons.json
                                │
                            build.py         (inlines compute.js + the data)
                                ▼
                          docs/index.html   (GitHub Pages)
                                │
   visitor's browser ◀──────────┘  on load / "Refresh live": fetches the current
                                   season from Sleeper and recomputes with the
                                   same compute.js — no server involved
```

One implementation of the math (`scripts/compute.js`) runs in both places, so the
archive and the live view can never disagree.

- `data/raw/<season>/` — untouched API responses: `league.json`, `users.json`, `rosters.json`,
  `winners_bracket.json`, `matchups/week_NN.json`, `projections/week_NN.json`.
- `data/derived/seasons.json` — everything the page needs, recomputed from raw on every run.
- `docs/index.html` — the site. Fully self-contained (data is inlined).

### Freeze / correction rules (`scripts/fetch.py`)

- A season with league status `complete` is never re-fetched.
- For the live season, the last **2** weeks are re-fetched on every run so NFL stat
  corrections get picked up. Older weeks are frozen. A file is only rewritten when its
  contents change, so `git log data/raw` is the change history.
- `python scripts/fetch.py --all` ignores the freeze rules (use if Sleeper changes something).

### Schedule

`.github/workflows/update.yml` fires every 5 minutes September–January. `scripts/gate.py`
checks the real NFL schedule (ESPN public scoreboard) and decides what each slot does:

| When | What happens |
|---|---|
| NFL game day | fetch → compute → deploy every **5 min** (page lags Sleeper by ~5–15 min) |
| Any other day | same, once an **hour** |
| Tue & Fri 09:00 ET | also **commits** `data/raw` + `docs` to git (the archive) |
| Manual run / **Rebuild for everyone** button | rebuild + deploy only (tick `archive` on a manual run to commit) |
| Push to `main` (code, not data) | rebuild + deploy |

Deploys go straight to GitHub Pages from the runner (`actions/deploy-pages`), so only the
archive runs create commits. The page header shows the build time.

**https://bestballbutts.rrr-projects.com** is a tiny Cloudflare Worker (`worker/`) that
proxies the GitHub Pages site under the league's own domain and handles the page's
**Rebuild for everyone** button (`POST /refresh`). It holds the only credential — a
fine-grained GitHub token scoped to this repo's Actions — and triggers the workflow, refusing
if a manual run started in the last 2 minutes. Deploy it with `cd worker && npx wrangler@4 deploy`.

## Run locally

```bash
python scripts/fetch.py        # incremental
node scripts/compute-node.js
python scripts/build.py
node scripts/smoke.js          # optional: page script parses and runs
open docs/index.html
```

Python 3.10+ (standard library only) and Node 18+.

### Live refresh

The page loads the archive instantly, then (and whenever you press **Refresh live from
Sleeper**) fetches the current season's matchups from Sleeper directly in the browser and
recomputes every table. Projections for the live week (~1.5 MB) are fetched once and the
computed team totals cached in the browser for an hour; settled weeks reuse the archive.
Sleeper's API is public and allows browser requests, so there is no server, key, or proxy.

## Unluckiness Index

Three flavors, all per manager per week, all **outcome-gated**: a deviation counts at full
strength only if it flipped the result of that game, otherwise it is weighted 0.35.

| Tab | Deviation measured |
|---|---|
| **Schedule Luck** | Opponent's score − opponent's average over games *before* that week |
| **Roster Luck** | Your (score − Sleeper projection), relative to the league's mean projection error that week |
| **Net Luck** | Both combined |

Positive = unlucky, negative = lucky. Season total is the sum.

Projections are Sleeper's stored player projections re-scored under the league's own
scoring settings and assembled into the optimal projected lineup.

## Managers

Sleeper display names are mapped to first names in `scripts/compute.py` (`MANAGERS`).
Seat 5 was Steve in 2024 and Avery from 2025; career stats for that seat are combined under Avery.
