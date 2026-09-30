# Weekly brief routine

The Claude Code routine (a scheduled trigger on claude.ai) that runs [RUNBOOK.md](../RUNBOOK.md) every week. It writes the league prediction brief, uploads the PDF to Google Drive, and commits the run outputs to `main`.

| | |
|---|---|
| Schedule | `2 4 * * 3`, Wednesdays 04:02 UTC (Tuesday evening US time, after Monday Night Football) |
| Model | Opus 5.5 |
| Where it runs | the "Best Ball Butts weekly routine" thread in the NFL fantasy Claude project |
| Prompt | [prompt.md](prompt.md), identical to the live routine's prompt |
| Config | [routine.json](routine.json) |

This folder is a copy for version control and for rebuilding. The live routine is the trigger on claude.ai, so editing these files does not change it. After you change the prompt here, apply it to the trigger (for example with `update_trigger` from a Claude session) so the two stay in sync.

## Why it can disappear

A routine that fires into a thread is tied to that thread's session. If the session is deleted or cleaned up, the routine is deleted with it. That happened to the 2026-09-27 copy. A routine that starts a fresh session on each fire doesn't have this problem.

## Dependencies

- **Raghav-MCP-Server connector** (the gateway at `mcp.rrr-projects.com/mcp`):
  - `sleeper-draft` provides `export_league_snapshot`, and all Sleeper data comes through it.
  - `gateway` provides the `/files` lane (`upload_direct_lane`, `delete_file`), which moves the snapshot and the PDF in and out of the session.
  - `gws-personal` provides `drive_files_create` for the "Best Ball Butts Weekly" folder.
- Web search and fetch, for current injury news.

## Secrets

None are stored here. The connector authenticates to the gateway through claude.ai OAuth. The `/files` token from `gateway__upload_direct_lane` is persistent, and the prompt forbids writing it to any file or commit.

## Recreating it

Create a scheduled trigger with the cron above and the contents of `prompt.md` as its prompt. Attach the Raghav-MCP-Server connector and make sure this repository is available to the session. `prompt.md` assumes the routine fires into a thread. For a fresh-session routine, change its first paragraph so it no longer asks for a reply in a thread.
