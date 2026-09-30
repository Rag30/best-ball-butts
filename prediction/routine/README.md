# Weekly brief routine

The Claude Code routine (a scheduled trigger on claude.ai) that runs [RUNBOOK.md](../RUNBOOK.md) every week. It writes the league prediction brief, uploads the PDF to Google Drive, commits the run outputs to `main`, and posts a summary in a Claude project thread.

| | |
|---|---|
| Schedule | `2 4 * * 3`, Wednesdays 04:02 UTC (Tuesday evening US time, after Monday Night Football) |
| Model | Opus 5.5 |
| Where it runs | the "Weekly routine" thread in the NFL fantasy Claude project (trigger `trig_01B1zqNCwjzq3T1nGP889TGk`) |
| Connector | Raghav-MCP-Server |
| Prompt | [prompt.md](prompt.md), identical to the live routine's prompt |
| Config | [routine.json](routine.json) |

This folder is the source of truth for the routine. The live routine is the trigger on claude.ai, so editing these files does not change it. After you change the prompt here, apply it to the trigger (for example with `update_trigger` from the Weekly routine thread) so the two stay in sync.

## Keep the thread open

The routine is tied to the Weekly routine thread's session. If that thread is resolved, cleaned up, or its session is deleted, the routine is deleted with it. That's what happened to the copy created on 2026-09-27. Don't close or delete that thread.

If the routine disappears anyway, recreate it from that thread (or a new project thread) with `create_trigger`, using the cron above and `prompt.md` as the prompt. A fresh-session routine avoids the problem entirely, but it can't be created from inside a private Claude project. It has to be created on claude.ai/code/routines or from a regular Claude Code session.

## Dependencies

- **Raghav-MCP-Server connector** (the gateway at `mcp.rrr-projects.com/mcp`):
  - `sleeper-draft` provides `export_league_snapshot`, and all Sleeper data comes through it.
  - `gateway` provides the `/files` lane (`upload_direct_lane`, `delete_file`), which moves the snapshot and the PDF in and out of the session.
  - `gws-personal` provides `drive_files_create` for the "Best Ball Butts Weekly" folder.
- `.claude/settings.json` in this repository allows only `python3 /home/user/best-ball-butts/prediction/pipeline/gateway_files.py`, the guarded wrapper for the gateway `/files` lane, so auto mode doesn't block the snapshot download or the PDF upload. That path is why the prompt keeps the checkout at `/home/user/best-ball-butts`.
- Web search and fetch, for current injury news.

## Secrets

None are stored here. The connector authenticates to the gateway through claude.ai OAuth. The `/files` token from `gateway__upload_direct_lane` is persistent, and the prompt forbids writing it to any file or commit.
