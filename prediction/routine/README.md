# Weekly brief routine

The Claude Code routine (a scheduled trigger on claude.ai) that runs [RUNBOOK.md](../RUNBOOK.md) every week. It writes the league prediction brief, uploads the PDF to Google Drive, and commits the run outputs to `main`.

| | |
|---|---|
| Schedule | `2 4 * * 3`, Wednesdays 04:02 UTC (Tuesday evening US time, after Monday Night Football) |
| Model | Opus 5.5 |
| Session | a fresh cloud session on each run, not tied to any thread |
| Repository | `Rag30/best-ball-butts` |
| Connector | Raghav-MCP-Server |
| Notifications | push and email when a run finishes |
| Prompt | [prompt.md](prompt.md) |
| Config | [routine.json](routine.json) |

This folder is the source of truth for the routine. The live routine is the trigger on claude.ai, so editing these files does not change it. After you change the prompt here, update the trigger to match.

## Why fresh-session

A routine that fires into a Claude project thread is tied to that thread's session. If the session is deleted or cleaned up, the routine is deleted with it. That happened to the copy created on 2026-09-27. A fresh-session routine belongs only to the account and isn't affected. Claude can't create one from inside a private project, so create it on claude.ai.

## Creating it

1. Open [claude.ai/code/routines](https://claude.ai/code/routines) and create a new routine.
2. Name it "Best Ball Butts weekly brief" and set the schedule to `2 4 * * 3` (UTC), which is weekly on Wednesdays at 04:02.
3. Pick this repository (`Rag30/best-ball-butts`) and an environment with Full network access.
4. Attach the Raghav-MCP-Server connector and choose Opus 5.5.
5. Paste in the contents of `prompt.md`.

## Dependencies

- **Raghav-MCP-Server connector** (the gateway at `mcp.rrr-projects.com/mcp`):
  - `sleeper-draft` provides `export_league_snapshot`, and all Sleeper data comes through it.
  - `gateway` provides the `/files` lane (`upload_direct_lane`, `delete_file`), which moves the snapshot and the PDF in and out of the session.
  - `gws-personal` provides `drive_files_create` for the "Best Ball Butts Weekly" folder.
- `.claude/settings.json` in this repository allows the runbook's two gateway `curl` commands, so auto mode doesn't block them.
- Web search and fetch, for current injury news.

## Secrets

None are stored here. The connector authenticates to the gateway through claude.ai OAuth. The `/files` token from `gateway__upload_direct_lane` is persistent, and the prompt forbids writing it to any file or commit.
