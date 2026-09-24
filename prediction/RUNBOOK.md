# Best Ball Butts weekly brief: runbook

Weekly league-wide prediction for Best Ball Butts (Sleeper league `1312511085802180608`, 8 teams, best ball, PPR, 6-pt pass TD).
Output: a **2-page PDF** written for the whole league, in neutral voice. No "your team" framing, and every manager gets an equal line.
It's saved to Google Drive (personal account raghav.ringshia@gmail.com), folder **Best Ball Butts Weekly** (id `1btM-W2ckqrx6la0JdIAnfrkonAQjy-3s`).

- `P = ~/Coding Project MBP/bbb-weekly`; code in `P/pipeline`, cached 2025 inputs in `P/cache`, one folder per run in `P/runs/<YYYY-MM-DD>/`.
- Every script runs **from the run dir**: `python3 "$P/pipeline/<script>"`. numpy scripts need `uv run -q --with numpy [--with scipy] python ...` (the system python has no numpy).
- `week.json` (written by step 1) sets `start` = the first unplayed week. Everything else keys off it.

## Steps

1. **Pull the Sleeper data through Raghav's gateway MCP** (connector with `gateway__*` / `sleeper-draft__*` tools), not straight from the API:
   - `R="$P/runs/$(date +%F)"; mkdir -p "$R"; cd "$R"`
   - Call `sleeper-draft__export_league_snapshot` with no arguments. It returns `{filename, sha256, last_completed_week}` and writes ~55 MB into the gateway workspace.
   - Call `gateway__upload_direct_lane` to get the `/files` URL and the scoped bearer. Download with `curl -sS -o snapshot.json -H "Authorization: Bearer <token>" https://mcp.rrr-projects.com/files/<filename>`, then check the sha256 (`shasum -a 256 snapshot.json`). Never write the token to any file.
   - Run `python3 "$P/pipeline/fetch_data.py" --snapshot snapshot.json`, then delete the workspace copy with `gateway__delete_file`.
   - This builds the rosters, byes and Sleeper projections, and checks D/ST scores against a recount from raw stats (`dst_check.json`).
   - **Fallback:** only if the gateway is unreachable, run `python3 "$P/pipeline/fetch_data.py"` with no flag (direct public Sleeper API), and say in the brief's Data checks that the MCP was skipped.
   - **If `start` equals the previous run's `start`, no new week has finished.** Still produce the brief, but say so.
   - If the D/ST check reports any mismatch or zeros, say so in the brief's Data checks section.
2. **Injury research.** Copy the previous run's `injury_adjustments.json` into the run dir, then update it for the coming weeks.
   - Drop healed players and roll the `weeks_out` windows forward. Only weeks ≥ `start` matter, and each player's bye is excluded.
   - Research every rostered player with a non-null `injury_status` in `rostered_players.json`, plus any starter whose role changed. Use WebSearch/WebFetch, current news only, and cite a source per entry.
   - Format: `{sleeper_id: {name, manager, weeks_out:[...], multiplier, multiplier_weeks:[...], reason, confidence, source}}`.
   - Never invent timelines. Low confidence is fine.
3. Build the projection engines, in order:
   - `python3 "$P/pipeline/src_espn_fetch.py" && uv run -q --with numpy python "$P/pipeline/src_espn_build.py"` (ESPN)
   - `python3 "$P/pipeline/src_market_build.py"` (ADP curves)
   - `python3 "$P/pipeline/src_fix_kfg.py"` (writes `proj_sleeper_kfix.json`)
   - `python3 "$P/pipeline/src_prod_build.py"` (production; reads `injury_adjustments.json`)
   - `python3 "$P/pipeline/src_blend_build.py"` (blend + blend_inj)
4. Simulate. Run `bash "$P/pipeline/run_engine.sh" <e>` for each e in `sleeper_kfix espn market production blend blend_inj`. They can run in parallel with `&` and `wait`. Each run produces locked and `_nolock` results.
5. Aggregate with `python3 "$P/pipeline/src_agg.py"`. This writes `agg.json` and prints the consensus against the previous run's `agg.json`.
6. Write `brief.md` following `P/pipeline/brief_template.md`, with the same sections:
   - Title with the upcoming week
   - "As of" line
   - TL;DR (3 bullets)
   - Standings odds table (record, PF, title %, range, playoff %, bye %, previous edition, Δ)
   - What changed since last week: the latest week's results from `m26_w<last>.json`, plus big injuries, waiver moves (`tx_w*.json`) and hot players
   - Team by team: one neutral line per manager, all 8
   - Data checks: the D/ST check, plus caveats
   Every number must come from the run's files.
7. `uv run -q --with markdown python "$P/pipeline/make_pdf.py" brief.md "Best Ball Butts 2026 - Week <start> brief"`. It exits with code 3 if the PDF is over 2 pages; tighten the text and rerun until it passes.
8. Upload to Drive with the `gws-personal` MCP `drive_files_create`:
   - body `{"name":"Best Ball Butts 2026 - Week <start> brief.pdf","parents":["1btM-W2ckqrx6la0JdIAnfrkonAQjy-3s"],"mimeType":"application/pdf"}`
   - params `{"uploadType":"multipart","fields":"id,webViewLink"}`
   - upload = the PDF path **relative to `/`** with no leading slash (the MCP server's cwd is `/`), e.g. `Users/raghavringshiambp/Coding Project MBP/bbb-weekly/runs/<date>/Best Ball Butts 2026 - Week <start> brief.pdf`
   - If a file with the same name already exists in the folder, upload anyway; don't delete anything.

## Engines (same as the Week 1 and Week 3 editions)

- **sleeper_kfix:** Sleeper weekly projections rescored, plus a kicker distance-bonus estimator.
- **espn:** ESPN weekly projections, rebuilt from raw stats.
- **market:** 2025 ADP→ppg curves applied to 2026 ADP.
- **production:** 2025 plus 2026-to-date ppg, shrunk to a prior.
- **blend:** Sleeper .30, ESPN .25, production .10, market .10, plus a Bayesian update on the 2026 games played (K=6).
- **blend_inj:** blend plus injury multipliers.

Each engine gets 2 noise configs (base; gci = gamma, corr 0.25, injury 1), n=8,000, which makes 12 runs; the consensus is their mean.
