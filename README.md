# Best Ball Butts

League archive and the Unluckiness Index™ for the *Best Ball Butts* Sleeper league.

**Live site:** https://bestballbutts.rrr-projects.com

## How it works

```
                 ┌──────────────────────── Cloudflare Worker (worker/) ────────────────────────┐
Sleeper API ───▶ │ POST /refresh  ─▶ compute.js ─▶ KV  season:<yr>, proj:<yr>:<wk>, snapshot   │
   (public)      │ cron 9 PM ET nightly ─▶ same                                               │
                 │ GET /data  ◀── KV snapshot          GET /  ◀── public/index.html (static)   │
                 └───────────────────────────────────────────────────────────────────────────────┘
                                             ▲ page fetches /data on load; Refresh button = POST /refresh

Sleeper API ──fetch.py──▶ data/raw/ (git)   ◀── GitHub Action, nightly 10 PM ET: the immutable archive
```

- **Cloudflare KV is the live database.** One computed JSON per season plus a `snapshot` the page
  renders. Completed seasons (`status: complete`) are written once and frozen; the current season is
  recomputed on every refresh. The Worker refreshes itself once a night at 9 PM ET, and anyone can press **Refresh** on the page.

- **git `data/raw/` is the archive.** Raw Sleeper responses, committed nightly at 10 PM ET by the Action. It's the
  source of truth if Sleeper ever changes; `scripts/seed-kv.js` rebuilds KV from it.
- **One implementation of the math** — `scripts/compute.js` runs in the Worker (live) and in Node
  (`compute-node.js`, archive). No credentials anywhere: Sleeper is public and KV is bound to the Worker.

## Deploy / operate

```bash
# page or worker code changed:
python3 scripts/build.py && cd worker && npx wrangler@4 deploy

# rebuild a completed season in KV from the git archive (rare):
node scripts/compute-node.js && node scripts/seed-kv.js 2025

# local check that the page script renders the derived data:
python3 scripts/build.py && node scripts/smoke.js
```

`wrangler` uses the OAuth login on this machine. The KV namespace id is in `worker/wrangler.toml`.

## Unluckiness Index

All three are per manager per week and **outcome-gated**: a deviation counts at full strength only if
it flipped that game's result, otherwise ×0.35. Positive = unlucky, negative = lucky; season total is the sum.

| Tab | Deviation |
|---|---|
| **Schedule Luck** | Opponent's score − opponent's average over games *before* that week |
| **Roster Luck** | Your (score − Sleeper projection), relative to the league's mean projection error that week |
| **Net Luck** | Both combined |

Projections are Sleeper's stored player projections re-scored under the league's own scoring and
assembled into the optimal projected lineup.

## Managers

Sleeper display names → first names live in `scripts/compute.js` (`MANAGERS`). Seat 5 was Steve in
2024 and Avery from 2025 — different people, tracked separately in the career table.
