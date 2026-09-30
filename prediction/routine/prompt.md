Weekly routine firing: produce this week's Best Ball Butts league prediction brief, save it to Google Drive, and commit the run outputs. Post progress with update_status and finish with one reply in this thread carrying the summary below.

Setup: work in a checkout of Rag30/best-ball-butts at /home/user/best-ball-butts. If that folder is missing, clone it (git clone https://github.com/Rag30/best-ball-butts /home/user/best-ball-butts); otherwise reset it to the latest remote main with git fetch origin && git checkout -B main origin/main (an earlier run may have left a local commit whose push was rejected; that commit lives on in its PR branch).

Read prediction/RUNBOOK.md first and follow steps 1-9 exactly, in a new run folder prediction/runs/<today's date>. Use the cloud-session variants: the Raghav-MCP-Server connector gives you gateway__*, sleeper-draft__* and gws-personal__* tools.

Requirements (from the owner, Raghav):
- Sleeper data MUST come through his MCP: sleeper-draft__export_league_snapshot, download via the gateway /files lane (gateway__upload_direct_lane gives URL + token), verify sha256, fetch_data.py --snapshot, then gateway__delete_file. Only if the gateway is unreachable, use the direct-API fallback and say so in the brief. Never write the upload token to any file or commit.
- Deliverable: a 2-page PDF maximum (make_pdf.py enforces it; tighten and rerun if it fails).
- League-wide analysis to share with all 8 managers (Conrad, Lauren, Emma, Raghav, Avery, Ben, Noelle, Henry): neutral third-person voice, no 'your team' framing, no special section for Raghav, one equal line per manager in 'Team by team'.
- Same format as the previous run's brief.md: TL;DR, standings-odds table with previous-edition delta, what changed since last week, team by team, data checks (incl. the D/ST scoring check and whether data came via the MCP).
- Every number from the run's files; injury news current and sourced (WebSearch/WebFetch); never fabricate.
- Upload the PDF to Drive folder 'Best Ball Butts Weekly' (id 1btM-W2ckqrx6la0JdIAnfrkonAQjy-3s): PUT to gateway /files, then gws-personal__drive_files_create with upload = that plain filename, then gateway__delete_file. Never delete or share anything in Drive.
- If no new NFL week has completed since the last run (week.json start unchanged), still produce and upload the brief and say so in the TL;DR.
- Step 9: commit only the small tracked outputs (runs/.gitignore handles it) with message 'prediction: Week <start> brief' and push to main; if the push is rejected, open a PR instead.
- End with a short summary: Drive link, top-3 title odds, whether data came via the MCP, anything that went wrong.
