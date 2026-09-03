# Best Ball Butts

League archive and the Unluckiness Index™ for the *Best Ball Butts* Sleeper league.

**Live site:** https://rag30.github.io/best-ball-butts/

## How it works

```
Sleeper API ──fetch.py──▶ data/raw/        (immutable snapshots, the "database")
                                │
                           compute.py
                                │
                                ▼
                          data/derived/seasons.json
                                │
                            build.py
                                ▼
                          docs/index.html   (GitHub Pages)
```

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

`.github/workflows/update.yml` runs Tuesday and Friday mornings (UTC) September–January,
and can be triggered manually from the Actions tab.

## Run locally

```bash
python scripts/fetch.py      # incremental
python scripts/compute.py
python scripts/build.py
open docs/index.html
```

Python 3.10+, standard library only.

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
