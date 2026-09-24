# Best Ball Butts weekly brief: runbook

This is a weekly prediction for the whole Best Ball Butts league (Sleeper league `1312511085802180608`, 8 teams, best ball, PPR, 6-pt pass TD).

Output is a **2-page PDF** written for all 8 managers:
- Neutral third-person voice. Nothing is framed as "your team", and Raghav doesn't get his own section.
- Every manager gets one equal line.

It's saved to Google Drive (personal account raghav.ringshia@gmail.com), in the folder **Best Ball Butts Weekly** (id `1btM-W2ckqrx6la0JdIAnfrkonAQjy-3s`).

It runs from the MacBook, or from any Claude cloud session whose environment has Network access **Full** and the **Raghav-MCP-Server** connector (tools named `gateway__*`, `sleeper-draft__*`, `gws-personal__*`).

- `P` = this `prediction/` directory in the `Rag30/best-ball-butts` checkout.
  - `P/pipeline` holds the code, `P/cache` holds the static 2025 inputs, and `P/runs/<YYYY-MM-DD>/` holds one folder per edition.
- Every script runs **from the run dir**: `python3 "$P/pipeline/<script>"`.
  - numpy/scipy scripts need `uv run -q --with numpy --with scipy python ...`.
  - If `uv` is missing, use `pip install numpy scipy markdown` once, then plain `python3`.
- `week.json` (written in step 1) sets `start`, the first unplayed week, and everything else keys off it.
- `src_agg.py` compares against the newest earlier `runs/*/agg.json`. That's why step 9 commits the small outputs back to the repo.

## Steps

1. **Get the Sleeper data through Raghav's gateway MCP.** Don't call the Sleeper API directly.
   - Create the run dir: `R="$P/runs/$(date +%F)"; mkdir -p "$R"; cd "$R"`.
   - Call `sleeper-draft__export_league_snapshot` with no arguments. It writes about 55 MB into the gateway workspace and returns `{filename, sha256, last_completed_week}`.
   - Call `gateway__upload_direct_lane` to get the `/files` URL and the scoped bearer token.
   - Download: `curl -sS -o snapshot.json -H "Authorization: Bearer <token>" https://mcp.rrr-projects.com/files/<filename>`.
   - Check the file with `shasum -a 256 snapshot.json` (or `sha256sum`); it must match the returned sha256. **Never write the token to a file.**
   - Run `python3 "$P/pipeline/fetch_data.py" --snapshot snapshot.json`.
   - Delete the workspace copy with `gateway__delete_file`.

   This builds the rosters, byes and Sleeper projections. It also checks each D/ST score against a recount from raw stats and writes the result to `dst_check.json`.

   - **Fallback, only if the gateway is unreachable:** run `python3 "$P/pipeline/fetch_data.py"` with no flag, which calls the public Sleeper API directly. Say so in the brief's Data checks section.
   - **If `start` equals the previous run's `start`, no new week has finished.** Produce the brief anyway and say so.
   - If the D/ST check reports any mismatch or zero scores, report it in Data checks.
2. **Injury research.**
   - Copy the previous run's `injury_adjustments.json` into the run dir.
   - Update it for the coming weeks: drop healed players and roll the `weeks_out` windows forward. Only weeks ≥ `start` matter, and each player's bye week is excluded.
   - Research every rostered player with a non-null `injury_status` in `rostered_players.json`, plus any starter whose role changed. Use WebSearch/WebFetch, current news only, and cite a source for each entry.
   - Format: `{sleeper_id: {name, manager, weeks_out:[...], multiplier, multiplier_weeks:[...], reason, confidence, source}}`.
   - Never invent timelines. Low confidence is fine.
3. **Build the projection engines**, in this order:
   - ESPN: `python3 "$P/pipeline/src_espn_fetch.py" && uv run -q --with numpy python "$P/pipeline/src_espn_build.py"`
   - Market: `python3 "$P/pipeline/src_market_build.py"`
   - Sleeper kicker fix: `python3 "$P/pipeline/src_fix_kfg.py"`
   - Production: `python3 "$P/pipeline/src_prod_build.py"`
   - Blend: `python3 "$P/pipeline/src_blend_build.py"`
4. **Simulate.** Run `bash "$P/pipeline/run_engine.sh" <e>` for each of `sleeper_kfix espn market production blend blend_inj`. They can run in parallel with `&` and `wait`. Each engine writes both locked and `_nolock` results.
5. **Aggregate.** Run `python3 "$P/pipeline/src_agg.py"`. It writes `agg.json` and prints the consensus next to the previous edition.
6. **Write `brief.md`**, following the previous run's `brief.md` (template: `P/pipeline/brief_template.md`). Sections:
   - Title with the upcoming week, and an "As of" line
   - TL;DR: 3 bullets
   - Standings odds: record, PF, title %, range, playoff %, bye %, previous edition, Δ
   - What changed since last week: the latest week's results, big injuries, waiver moves and hot players
   - Team by team: one neutral line for each of the 8 managers
   - Data checks: the D/ST check, whether the data came through the MCP, and caveats

   Every number must come from the run's files.
7. **Make the PDF.** Run `uv run -q --with markdown python "$P/pipeline/make_pdf.py" brief.md "Best Ball Butts 2026 - Week <start> brief"`.
   - It exits with code 3 if the PDF runs over 2 pages. Tighten the text and rerun.
   - It finds macOS Chrome or the cloud's Chromium on its own.
8. **Upload to Drive.** Use body `{"name":"Best Ball Butts 2026 - Week <start> brief.pdf","parents":["1btM-W2ckqrx6la0JdIAnfrkonAQjy-3s"],"mimeType":"application/pdf"}` and params `{"uploadType":"multipart","fields":"id,webViewLink"}`.
   - **Cloud session, or any session using the gateway connector:**
     - PUT the PDF into the gateway workspace: `curl -sS -T "<pdf>" -H "Authorization: Bearer <token>" "https://mcp.rrr-projects.com/files/bbb_week<start>_brief.pdf"`.
     - Call `gws-personal__drive_files_create` with `upload` set to that plain filename. The gateway's gws reads it from its workspace.
     - Delete the workspace copy with `gateway__delete_file`.
   - **MacBook desktop app, using its own local gws-personal connector:** set `upload` to the PDF path relative to `/`, with no leading slash.
   - If a file with the same name already exists, upload anyway. Never delete or share anything in Drive.
9. **Commit the outputs.** Commit the run's small outputs, which `runs/.gitignore` allows: `agg.json`, `injury_adjustments.json`, `brief.md`, `week.json`, `dst_check.json` and the PDF.
   - Message: `prediction: Week <start> brief`.
   - Push to `main` of `Rag30/best-ball-butts`, the same way the data Action commits its snapshots. Next week's run needs this `agg.json`.
   - If the push is rejected, open a PR instead and say so.

## Engines (same as the Week 1 and Week 3 editions)

| Engine | What it uses |
|---|---|
| sleeper_kfix | Sleeper weekly projections, rescored, plus a kicker distance-bonus estimator |
| espn | ESPN weekly projections, rebuilt from raw stats |
| market | 2025 ADP→ppg curves applied to 2026 ADP |
| production | 2025 and 2026-to-date points per game, shrunk toward a prior |
| blend | Weighted mix (Sleeper .30, ESPN .25, production .10, market .10), updated with the 2026 games played (K=6) |
| blend_inj | blend plus the injury multipliers |

Each engine runs 2 noise configs: base, and gci (gamma, corr 0.25, injury 1). Each run is 8,000 simulations, so there are 12 runs in total. The consensus is their mean.
