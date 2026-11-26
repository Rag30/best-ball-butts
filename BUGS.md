# Bugs

The real cause of each bug, once it is found, so the next session reads it before guessing.

Newest first. One entry per bug, in this shape:

```
## YYYY-MM-DD · Area
- **Symptom:** what someone saw.
- **Real cause:** why it happened.
- **Fix:** what changed, with the PR number (or commit if there was no PR).
```

This repo is public: no secrets, tokens, home network details or personal data in here.

---

## 2026-10-28 · Standings
- **Symptom:** From the Thursday game until Sunday's games were final, the standings showed the manager who was behind as already having lost that week.
- **Real cause:** Any week with points was counted as a played game, so the nightly refresh locked in an in-progress matchup as decided.
- **Fix:** Weeks count only up to Sleeper's `league.settings.last_scored_leg`; the live week stays on the remaining schedule until then. Test in `worker/test/weeks.test.mjs`. (#8)

## 2026-10-02 · Page: Weekly Brief tab
- **Symptom:** The Weekly Brief tab, and season buttons added later, did nothing when `/data` failed to load.
- **Real cause:** The season tab click handlers were attached only after the `/data` fetch succeeded, and only to the buttons that existed then.
- **Fix:** One delegated click listener on `#seasonTabs`, set up before the fetch. (#6, commit 082ecee)

## 2026-10-02 · Worker: Weekly Brief
- **Symptom:** The Weekly Brief tab showed a 502 error.
- **Real cause:** `prediction/runs/index.json` did not exist on `main` yet, and the Worker treated that 404 as a failure.
- **Fix:** A missing index now means "no brief yet". Test in `worker/test/tabs.test.mjs`. (#6, commit 5c85012)

## 2026-09-23 · Prediction: run folder date
- **Symptom:** A same-day cloud run could overwrite the Week 3 edition.
- **Real cause:** The run folder was named by UTC date, so the Tuesday-evening Week 3 edition landed under Wednesday's date, the same folder a later cloud run that day would write into.
- **Fix:** Editions are filed under the Pacific date. (#1, commit a89d34c)

## 2026-09-04 · Worker: KV writes
- **Symptom:** The cron was on track to use up the Cloudflare KV free tier (1,000 writes a day) on quiet days.
- **Real cause:** Every refresh rewrote each season, the snapshot and the `lastRefresh` stamp, even when nothing had changed. Also, if ESPN could not be reached the cron assumed a game day and ran every 5 minutes.
- **Fix:** Write a key only when its JSON changed; stamp `lastRefresh` only for manual presses; fall back to hourly when ESPN fails. (commit 3d283e8, no PR)

## 2026-09-03 · Career table
- **Symptom:** Two different managers who held the same seat in different seasons showed as one person in the career table.
- **Real cause:** `CAREER_ALIAS` in `scripts/compute.js` merged the seat's old owner into the new one.
- **Fix:** Alias removed; career stats are per person. (commit a360b58, no PR)
