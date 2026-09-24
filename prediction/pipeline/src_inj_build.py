"""Week-3 edition of injury_adjustments.json (built 2026-09-23/24, Wks 1-2 complete).

Conventions (carried over from the week-1 builder):
- weeks_out: weeks in 3..17 the player is expected to MISS, excluding his bye.
- multiplier: 0-1 scale on his normal projection for the weeks in multiplier_weeks
  (reduced role / managed workload / coin-flip availability when not listed out).
- Coin-flip rule: DNP Wednesday + coach "uncertain/not sure" or insider "expected to
  miss" -> weeks_out [3]; limited/"good shot"/"day-to-day, not serious" -> a Wk3
  multiplier instead.
"""
import json
r = json.load(open('rostered_players.json'))
byes = json.load(open('byes_2026.json'))
pr = json.load(open('proj_sleeper.json'))


def bye(pid):
    return byes.get(r[pid]['team'], [None])[0]


def wk(pid, a, b):
    """weeks a..b inclusive, excluding the player's bye"""
    return [w for w in range(a, b + 1) if w != bye(pid)]


# (pid, weeks_out, multiplier, multiplier_weeks, reason, confidence, source)
SPEC = [
 # ---------------- long-term / season-level ----------------
 ("12508", wk("12508", 3, 17), 1.0, [],
  "Torn MCL + meniscus and PCL sprain in Wk2 vs LAR; knee surgery ends his 2026 season (6-9 month recovery). Jameis Winston starts. Sleeper still projects ~20/wk from Wk4 (stale).",
  "high", "CBS/Yahoo/NBC Sports 2026-09-23 (season-ending surgery)"),
 ("5850", wk("5850", 3, 17), 1.0, [],
  "Still on the commissioner's exempt list (since Aug 30); pleaded no contest to misdemeanor battery/property damage, and the NFL's personal-conduct review (possible suspension) has no announced end. Cannot practice or play. Sleeper assumes a Wk8 return; a reinstatement or time-served suspension could bring him back midseason.",
  "medium", "NBC Sports/PFT exempt-list update; Sleeper tag NA/Personal"),
 ("10222", wk("10222", 3, 12), 0.70, wk("10222", 13, 17),
  "Neck injury on a hard hit in Wk2 at NYJ, carted off on a spine board, hospitalized overnight (movement in all extremities). LaFleur says it is 'way too early' to know whether he plays again this season. Taken as out through Wk12 with a diminished role if he returns; he was already WR6 on the depth chart.",
  "low", "NBC Sports 2026-09-22 'Packers unsure if Reed plays this season'; ESPN"),
 ("11566", wk("11566", 3, 5), 0.90, wk("11566", 6, 9),
  "Dislocated left elbow (no fracture) late in the first half of Wk2 at DAL; seeing specialists, no timeline yet. Mariota starts Wk3. Same elbow he dislocated last season, when he missed 3 games; a repeat dislocation raises instability/surgery risk. Expect a brace and fewer designed runs on return.",
  "low", "ESPN/NFL.com/NBC Sports 2026-09-21..23 (Mariota to start Wk3, awaiting specialist opinions)"),
 ("8142", wk("8142", 3, 8), 0.85, wk("8142", 9, 11),
  "Aggravated the heel he had surgically repaired this offseason (carted off in Wk2 vs KC). Placed on IR (minimum 4 games, Wk3-6); rehabbing rather than repeat surgery, 'several weeks' with hope of a midseason return. Surgery still possible.",
  "medium", "NBC Sports 2026-09-23 (IR); ESPN 'out weeks, hoping to return midseason'; CBS"),
 ("11583", wk("11583", 3, 8), 0.90, wk("11583", 9, 10),
  "Core-muscle (groin/abdomen) surgery Sept 23 after a Wk2 injury; placed on IR, expected to miss ~6 weeks (CAR bye Wk5), so Wk9 is the realistic return. Was RB3 behind Hubbard anyway.",
  "medium", "AP via US News 2026-09-23 (6 weeks); ESPN; CBS"),
 ("5859", wk("5859", 3, 7), 0.90, [8, 9],
  "High-ankle sprain in Wk1 vs SEA; IR since Sept 11, reported ~6-week absence. IR-eligible Wk6, realistic return Wk7-8; Wk7 included as out. Sleeper agrees (0 through Wk7).",
  "high", "NFL.com (6 weeks), NBC Sports Boston (IR, min Wk6)"),
 ("4033", wk("4033", 3, 7), 0.80, wk("4033", 8, 10),
  "Fibula injury, carted off in Wk2 vs LV; placed on IR Sept 21 (minimum 4 games, Wk3-6), LAC bye Wk7. Unclear if more serious than the IR minimum. Was TE3 on the depth chart (16% of snaps in Wk2 before the injury).",
  "high", "Chargers.com / NBC Sports 2026-09-21 (IR, fibula)"),
 ("13281", wk("13281", 3, 8), 0.85, wk("13281", 9, 11),
  "Rookie hamstring strain (Aug 13); IR-designated-to-return, reported ~2 months out. Wk7 international game + Wk8 bye make Wk9 the likeliest debut (Sleeper has Wk6-7 trickle).",
  "medium", "NFL.com (2 months), NBC Sports (IR)"),
 ("9753", wk("9753", 3, 5), 0.70, wk("9753", 6, 9),
  "Reserve/PUP after Feb ACL surgery: must miss through Wk4 (eligible Wk5). SEA did NOT open his 21-day practice window this week, though Macdonald says a start date is 'coming soon', so Wk5 is optimistic; Wk6 assumed. Must re-win work from Price (and Holani/Wilson). Sleeper zeroes the whole season (PUP artifact).",
  "medium", "FantasyPros/CBS 2026-09-23 (window not opened this week); Field Gulls (Macdonald quote)"),
 ("5022", wk("5022", 3, 5), 0.90, [6, 7],
  "MCL sprain in Wk2 vs TEN; expected to 'miss a few weeks' and back this season; IR still possible (would mean at least Wk3-6). PHI signed Zach Ertz to the practice squad. Sleeper zeroes Wk3-4 only.",
  "medium", "ESPN/NBC Sports Philadelphia/PFT 2026-09-21..22 ('a few weeks')"),
 ("12469", wk("12469", 3, 5), 0.90, [6, 7],
  "Knee injury on a Wk1 kickoff return; IR, minimum 4 games, eligible Wk6 vs BAL. RB6 on the depth chart, so negligible impact; Sleeper zeroes his entire season.",
  "high", "ESPN / news5cleveland (IR, eligible Wk6)"),
 ("13293", wk("13293", 3, 5), 0.90, [6, 7],
  "Fractured wrist in Wk1, surgery, IR (minimum 4 games); eligible Wk6 at CLE. WR10 on the depth chart.",
  "high", "Bleacher Report / ESPN (IR, eligible Wk6)"),
 ("13417", wk("13417", 3, 7), 0.85, [9, 10],
  "Moved from Out to IR with ankle surgery noted (Sleeper, Sept 19). No dedicated reporting found; an IR stint started before Wk2 covers at least Wk2-5, and Sleeper zeroes him until Wk16. Out through the Wk8 bye assumed. WR10, negligible impact.",
  "low", "Sleeper tag only (IR/Ankle, Surgery)"),

 # ---------------- short-term: expected to miss Wk3 ----------------
 ("7569", [3], 0.95, [4, 5],
  "Grade 1 hamstring strain from Wk2 practice; missed Wk2 and absent from Wednesday's Wk3 practice. Source expectation: out Wk3 vs IND (two games total); timeline 'fluid' but no long-term issue.",
  "medium", "SI Texans / Bleacher Report 2026-09-23"),
 ("9493", [3], 0.90, [4, 5],
  "Groin soreness; inactive in Wk2, DNP again Wednesday; McVay 'not sure' he plays Wk3 vs DEN (one doctor floated sports-hernia risk). Coin flip - taken as out. Sleeper still projects 17.2 in Wk3.",
  "low", "NBC Sports 2026-09-22 (McVay 'not sure'); ClutchPoints (DNP Wed)"),
 ("4199", [3], 0.90, [4],
  "Knee injury in Wk2 (finished in a brace after 23 carries/81% snaps); DNP Wednesday, O'Connell calls him uncertain for Wk3 at TB. Coin flip - taken as out. Role was clearly RB1 with Jordan Mason on IR.",
  "low", "ESPN / PFT 2026-09-23 (knee, DNP, uncertain)"),
 ("4943", [3], 0.95, [4],
  "'Unique' short-term glute soft-tissue injury from Wk1; missed Wk2. Ramping up in practice this week with 'at least a chance' to play Wk3 at WAS; decision by Friday. Coin flip - sided with Sleeper (0 in Wk3). Original estimate was ~4 weeks.",
  "low", "Seattle Sports / Seahawks.com 2026-09-23"),
 ("8210", [3], 0.95, [4],
  "Hamstring from Wk1; missed Wk2, DNP Wednesday and 'in rehab mode' per Quinn.",
  "medium", "CBS/RotoWire 2026-09-23"),
 ("13296", [3], 0.90, [4],
  "Ankle injury late in Wk2 (in a boot postgame); DNP Wednesday, Hafley non-committal for Wk3 vs KC.",
  "low", "NBC Sports / RotoWire 2026-09-23"),

 # ---------------- questionable / play-through (multiplier only) ----------------
 ("11604", [], 0.85, [3, 4],
  "Meniscus trim before the season; missed Wks1-2. Practicing and expected to debut Wk3 vs NO (Rapoport). Expect a managed snap share for his first couple of games.",
  "medium", "Newsweek/CBS/NFL.com 2026-09-22..23"),
 ("9997", [], 0.85, [3, 4],
  "Aggravated hamstring (Wk1 after 150 yds in a half), missed Wk2, DNP Wednesday again; Minter says he has a 'good shot' to play Wk3 vs DAL (Rio). Re-aggravation risk.",
  "low", "RotoWire / Yahoo 2026-09-23"),
 ("4983", [], 0.85, [3],
  "Left AC-joint sprain in Wk2 (TNF); not considered serious, 'has a chance to play' Wk3 vs LAC with 10 days of rest, but not a lock.",
  "low", "NFL.com / CBS 2026-09-18..20"),
 ("11632", [], 0.90, [3, 4, 5],
  "Right shoulder popped out and he popped it back in during Wk2; returned to the game and was limited Wednesday. Expected to play; recurrence risk.",
  "medium", "Giants.com injury report; CBS 2026-09-23"),
 ("4866", [], 0.95, [3],
  "Stinger on his first Wk2 carry (only 12 of 76 snaps); MRI described as precautionary, 'not more than a stinger'. Expected to play Wk3.",
  "medium", "NBC Sports / Gridiron Experts (Rapoport) 2026-09-20..22"),
 ("12489", [], 0.90, [3],
  "Hamstring; inactive in Wk2, limited Wednesday and 'continues to make progress'. With Dobbins (hip) limited and Coleman (ankle) DNP, he could reclaim a lead share if active.",
  "low", "Denver Gazette / Bleacher Report 2026-09-23"),
 ("6806", [], 0.90, [3],
  "Hip/hamstring (tag says hamstring, Gazette says hip) after exiting Wk2; limited Wednesday; Payton 'we're going to be alright'. Only 34% of snaps in Wk2.",
  "low", "Denver Gazette 2026-09-23"),
 ("13345", [], 0.60, [3],
  "Rookie ankle injury; DNP Wednesday. His Wk2 production (25 snaps, TD) came with Harvey inactive and Dobbins hurt - if Harvey returns he falls back to RB3. Availability and role both in doubt for Wk3.",
  "low", "Denver Gazette / SI Broncos 2026-09-23"),
 ("7021", [], 0.85, wk("7021", 3, 17),
  "Toe injury, DNP Wednesday in a walking boot, but Rapoport calls it day-to-day and not serious. Role concern too: Warren took 71% of snaps in Wk2 vs Dowdle's 26% (reversal of Wk1's 58/37).",
  "low", "Behind the Steel Curtain / RotoWire 2026-09-23; snap data Wks1-2"),
 ("8228", [], 0.95, [3],
  "Shoulder (Sleeper: undisclosed); limited Wednesday. Won the PIT backfield in Wk2 (71% of snaps), and Dowdle's toe could add volume.",
  "medium", "Steelers.com Wk3 injury report 2026-09-23"),
 ("6819", [], 0.95, [3],
  "Foot injury (different from his camp injury) kept him out of Wk2; back at practice limited Wednesday. Needs a full session by Friday to avoid a tag.",
  "medium", "CBS/RotoWire/Yahoo 2026-09-23"),
 ("7543", [], 0.90, [3, 4],
  "Hamstring, limited Wednesday (first appearance on the report). Also sharing more with the returning Alvin Kamara (54% of snaps, 8 carries in Wk2).",
  "medium", "Saints Wk3 injury report via Audacy/RotoBaller 2026-09-23"),
 ("12534", [], 0.95, [3],
  "Hamstring (Sleeper: undisclosed); missing/limited at practice ahead of CHI's Monday game. Could see extra volume if Caleb Williams and Bagent are out.",
  "low", "SI Bears / ChiCitySports 2026-09-23"),
 ("2216", [], 0.95, [3],
  "Hip injury in Wk2 (left in the second half of a blowout); Shanahan says it will be 'managed', not considered serious.",
  "medium", "PFT/RotoWire 2026-09-21"),
 ("5967", [], 0.95, [3],
  "Ankle soreness (Sleeper: undisclosed); DNP Wednesday but Saleh did not indicate he is at real risk of sitting out.",
  "medium", "RotoWire / Yahoo 2026-09-23"),
 ("13286", [], 0.95, [3],
  "Left Wk2 with what SEA now calls a shoulder issue ('intact, nothing serious'); X-rays negative, limited Wednesday. Could lose share when Charbonnet returns (handled separately).",
  "medium", "Seahawks.com / Field Gulls 2026-09-23"),
 ("12048", [], 0.95, [3],
  "Knee; limited Wednesday. RB3 with a 26% snap share in Wk2 - minor impact.",
  "medium", "FantasyPros/CBS 2026-09-23"),
 ("11646", [], 1.0, [],
  "Ankle; limited Wednesday again (played through the same issue in Wk2 with 76% of snaps). Availability not in question.",
  "high", "NBC Sports / Panthers.com 2026-09-23"),
 ("5947", [], 1.0, [],
  "Thumb; no reporting suggesting risk of missing time. Played 90% of snaps in Wk2 (1 target).",
  "low", "Sleeper tag only; snap data"),

 # ---------------- role change without an injury tag ----------------
 ("7611", [], 0.75, wk("7611", 3, 17),
  "Role loss: fumbled early in Wk2 and was out-snapped 33-20 (60% vs 36%) by TreVeyon Henderson in Henderson's season debut; Henderson got 16 carries to his 6. Wk1's 85% share came with Henderson (ankle) inactive. Sleeper still projects ~12/wk.",
  "medium", "CBS 'outplayed by Henderson', 98.5 snap counts 2026-09-21; s26_w1/w2 snap data"),
]

out = {}
for pid, weeks, mult, mweeks, reason, conf, src in SPEC:
    p = r[pid]
    assert pid not in out, pid
    b = bye(pid)
    assert b not in weeks and b not in mweeks, (pid, 'bye in weeks')
    assert not set(weeks) & set(mweeks), (pid, 'overlap')
    out[pid] = {"name": p['name'], "manager": p['manager'], "weeks_out": weeks,
                "multiplier": mult, "multiplier_weeks": mweeks, "reason": reason,
                "confidence": conf, "source": src}

# coverage check: every rostered player with an injury tag is present
missing = [(k, v['name']) for k, v in r.items() if v['injury_status'] and k not in out]
assert not missing, missing
json.dump(out, open('injury_adjustments.json', 'w'), indent=1)

# impact vs Sleeper's own projection (points Sleeper projects that this file removes)
rows = []
for pid, a in out.items():
    w = pr.get(pid, {})
    lost = sum(w.get(str(x), 0) for x in a['weeks_out'])
    lost += (1 - a['multiplier']) * sum(w.get(str(x), 0) for x in a['multiplier_weeks'])
    rows.append((lost, pid, a))
rows.sort(key=lambda t: -t[0])
print(f"{'#':<3}{'player':<22}{'mgr':<8}{'pts_removed':>11}  weeks_out")
for i, (lost, pid, a) in enumerate(rows, 1):
    wo = a['weeks_out']
    s = f"{wo[0]}-{wo[-1]}" if len(wo) > 2 else (str(wo) if wo else "none")
    print(f"{i:<3}{a['name']:<22}{a['manager']:<8}{lost:>11.1f}  {s} (x{a['multiplier']} on {a['multiplier_weeks'][:3]}{'...' if len(a['multiplier_weeks'])>3 else ''}, {a['confidence']})")
print("\nwrote injury_adjustments.json with", len(out), "entries")
