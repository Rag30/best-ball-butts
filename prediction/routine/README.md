# Weekly brief routine

The Claude Code routine (a scheduled trigger on claude.ai) that runs [RUNBOOK.md](../RUNBOOK.md) every week. It writes the league prediction brief, uploads the PDF to Google Drive, commits the run outputs to `main` (which publishes the brief on the league site's Weekly Analysis tab), and posts a summary in a Claude project thread.

| | |
|---|---|
| Schedule | `CRON_TZ=America/New_York 2 4 * * 3`, Wednesdays 4:02 AM Eastern, after that morning's waivers clear |
| Model | the project's default model (Opus 5.5 is the intent; project-level routines can't set their own) |
| Where it runs | a project-level routine in the NFL fantasy Claude project: each run starts a new project thread (trigger `trig_01KCPyLFniSxyp8q3qvb5pM5`, created 2026-11-23). Model and connectors come from the project settings |
| Connector | Routines MCP Gateway (the gateway's `routines` tier) |
| Prompt | [prompt.md](prompt.md), identical to the live routine's prompt |
| Config | [routine.json](routine.json) |

This folder is the source of truth for the routine. The live routine is the trigger on claude.ai, so editing these files does not change it. After you change the prompt here, recreate the trigger (see below) so the two stay in sync.

## Project-level routine

Since 2026-11-23 the routine is project-level: each run starts a fresh thread in the NFL fantasy project, so it no longer depends on any one thread staying open. Earlier copies were bound to a single thread's session and vanished when that session was deleted.

A project-level routine can't be edited in place with `update_trigger`. To change the prompt or schedule, delete it and create it again from a project thread with `create_trigger` (`create_new_session_on_fire: true`), using the cron above and `prompt.md`. Only switching it off works in place, and switching it back on has to be done on claude.ai.

## Dependencies

- **Routines MCP Gateway connector** (the gateway at `mcp.rrr-projects.com`, `routines` tier, shared with the FleetManager routines). Runs get the project's connectors, including the admin-tier MCP Gateway, so the prompt is what keeps it on this tier. If a tool is missing, tick it in the `routines` tier rather than pointing the routine at admin:
  - `sleeper-draft` provides `export_league_snapshot`, and all Sleeper data comes through it.
  - `gateway` provides the `/files` lane (`upload_direct_lane`, `delete_file`), which moves the snapshot and the PDF in and out of the session; `upload_base64_fallback` is the runbook's fallback when the lane can't be reached.
  - `gws-personal` provides `drive_files_create` for the "Best Ball Butts Weekly" folder.
- `.claude/settings.json` in this repository allows only `python3 /home/user/best-ball-butts/prediction/pipeline/gateway_files.py`, the guarded wrapper for the gateway `/files` lane, so auto mode doesn't block the snapshot download or the PDF upload. That path is why the prompt keeps the checkout at `/home/user/best-ball-butts`.
- Web search and fetch, for current injury news.
- Push access to `main`, which is also how the brief reaches the league site: the Worker in `worker/` reads `prediction/runs/index.json` and each edition from GitHub (`GET /brief`). No site credential or gateway tool is involved.

## Secrets

None are stored here. The connector authenticates to the gateway through claude.ai OAuth. The `/files` token from `gateway__upload_direct_lane` is persistent, and the prompt forbids writing it to any file or commit.
