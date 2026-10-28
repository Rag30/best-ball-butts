// A week in progress already has live partial points on Sleeper. It must not count as a game
// (the trailing manager would carry a phantom loss) until last_scored_leg says the week is final.
//
//   cd worker && npm test

import { test } from "node:test";
import assert from "node:assert/strict";
import BBB from "../../scripts/compute.js";

const league = last => ({ settings: { playoff_week_start: 15, ...(last === undefined ? {} : { last_scored_leg: last }) } });
const week = (a, b) => [{ roster_id: 1, matchup_id: 1, points: a }, { roster_id: 2, matchup_id: 1, points: b }];
// Weeks 1-2 final, week 3 in progress (roster 1 trailing 40-90 after Thursday/Sunday), week 4 unplayed.
const matchupsByWeek = { 1: week(150, 120), 2: week(110, 140), 3: week(40, 90), 4: week(0, 0) };

test("the live week is left out until last_scored_leg reaches it", () => {
  assert.deepEqual(BBB.completedWeeks(league(2), matchupsByWeek), [1, 2]);
  assert.deepEqual(BBB.completedWeeks(league(3), matchupsByWeek), [1, 2, 3]);
});

test("no week is final yet during week 1", () => {
  assert.deepEqual(BBB.completedWeeks(league(0), { 1: week(40, 90) }), []);
});

test("without last_scored_leg every scored week counts (archived payloads)", () => {
  assert.deepEqual(BBB.completedWeeks(league(undefined), matchupsByWeek), [1, 2, 3]);
});

test("standings mid-week carry no phantom loss", () => {
  const users = [{ user_id: "a", display_name: "plankrad" }, { user_id: "b", display_name: "lilmisseb" }];
  const rosters = [{ roster_id: 1, owner_id: "a" }, { roster_id: 2, owner_id: "b" }];
  const s = BBB.seasonFromRaw({ league: { ...league(2), league_id: "x", status: "in_season", roster_positions: [], scoring_settings: {} },
                                users, rosters, bracket: [], matchupsByWeek, projectionsByWeek: {} });
  const row = name => s.standings.find(x => x.name === name);
  assert.deepEqual([row("Conrad").wins, row("Conrad").losses], [1, 1]);
  assert.deepEqual([row("Emma").wins, row("Emma").losses], [1, 1]);
});
