# NLD-NAO route analysis, pass 1: instructions for the coding agent

As of 2026-10-06

## Goal and ground rules

Use NLD-NAO's per-game metadata to find which milestones ascenders achieve, where ordinary runs end, and which optional milestones actually help. Pass 1 uses metadata only, no recordings, so it should run in hours rather than days.

The outputs decide three things: which milestones the backbone requires, which are optional, and whether passes 2 and 3 (route order and kits from recordings) are worth building.

- **Read-only.** Never modify the NLD database; write everything to a separate `outputs/` directory.
- **Reproducible.** One script per step below, all filters logged with the number of games each removes, and fixed seeds wherever sampling is used.
- **No skill leakage.** A game's skill band may only use that player's *earlier* games (Step 2).
- **Version match.** NetHack 3.6 games are the main analysis set, because NLE and fast-nle are 3.6-based. Report 3.4.3 games separately, and only where cheap.
- **Honest numbers.** Every percentage comes with its count, and every rate with a bootstrap 95% interval.

## Setup and schema check

NLD-NAO pairs about 1.5 million human games recorded on NAO between 2009 and 2020 with each game's xlogfile entry ([Dungeons and Data](https://arxiv.org/abs/2211.00539v2)). NLE's `nle.dataset` loader indexes both into an SQLite database; confirm every name below before relying on it.

1. **Find or build the database.** Use the NLD database built from the NLD-NAO directory (the loader's `add_altorg_directory`). If none exists, build it, and record the NLE version used.
2. **Dump the schema.** Run `PRAGMA table_info` on every table and save the output to `outputs/schema.txt`.
3. **Map the fields.** Confirm that each field below exists, and note any differences in naming.
4. **Decode `achieve`.** It's a hexadecimal bitfield ([xlogfile spec](https://nethackwiki.com/wiki/Xlogfile)). Store one boolean column per bit.

| Field | Meaning | Used in |
| --- | --- | --- |
| `version` | NetHack version | Step 1 |
| `flags` | 0x1 wizard mode, 0x2 discover mode, 0x4 never loaded bones | Step 1 |
| `turns`, `realtime` | Game length in turns and seconds | Steps 1, 3 |
| `death` | Cause of death, or "ascended", "quit", "escaped" | Steps 1, 5 |
| `maxlvl`, `deathlev`, `deathdnum` | Deepest level, death level, and death dungeon number | Step 5 |
| `role`, `race`, `align`, `gender` | Starting character | Steps 3–6 |
| `name`, `starttime` | Player and start time | Steps 1, 2 |
| `achieve` | Milestone bitfield | Steps 4, 6 |
| `points` | Final score | Step 3 |

The `achieve` bits in 3.6:

| Bit | Milestone |
| --- | --- |
| 0x0001 | Got the Bell of Opening |
| 0x0002 | Entered Gehennom |
| 0x0004 | Got the Candelabrum of Invocation |
| 0x0008 | Got the Book of the Dead |
| 0x0010 | Performed the Invocation |
| 0x0020 | Got the Amulet of Yendor |
| 0x0040 | Was in the End Game |
| 0x0080 | Was on the Astral Plane |
| 0x0100 | Ascended |
| 0x0200 | Got the luckstone at Mines' End |
| 0x0400 | Finished Sokoban |
| 0x0800 | Killed Medusa |

**Confirm the `deathdnum` mapping from data, not memory.** The dungeon numbers are believed to be 0 Dungeons of Doom, 1 Gehennom, 2 Gnomish Mines, 3 Quest, 4 Sokoban, 5 Fort Ludios, 6 Vlad's Tower and 7 Elemental Planes. Check that each number's death depths and death causes look right, for example Mines deaths clustering in the low teens and shallower, before using it.

## Step 1: Cleaning and filters

Produce one cleaned table, `outputs/games_clean.parquet`, plus a filter log listing how many games each rule removed, in order.

1. **Version.** Keep `version` 3.6.x as the main set. Keep 3.4.3 in a separate table, untouched by later steps unless noted.
2. **Game modes.** Drop games with wizard mode (flag 0x1) or discover mode (flag 0x2) set.
3. **Start-scumming.** Many NAO players quit at once to reroll their starting inventory. Plot the turns distribution of games ending in "quit", pick a cutoff where the early spike ends (expected a few hundred turns), and drop quits below it. Report results at cutoffs of 100, 500 and 1,000 turns to show sensitivity.
4. **Duplicates.** Drop exact duplicates on (`name`, `starttime`), keeping one.
5. **Bots.** List the 50 accounts with the most games and inspect them for bot-like patterns: thousands of games, near-identical lengths, implausible game speeds. Drop confirmed bot accounts, and record the list.
6. **Keep, but mark.** Late quits and "escaped" games stay in the set, with an `ending` column: died, quit, escaped, ascended.

After cleaning, report the remaining game count, ascension count and number of distinct players.

## Step 2: Player skill bands without leakage

Every game gets a skill band computed only from that player's earlier games. This lets later steps separate "this route works" from "good players take this route".

1. **Order each player's games** by `starttime`. History may include their 3.4.3 games, since earlier experience counts whatever the version.
2. **Compute from strictly earlier games:** number of prior games, prior ascensions, median `maxlvl` over the last 20 games, and deepest `maxlvl` ever.
3. **Assign a band.** Start from these definitions, then adjust thresholds so no band is tiny, and record the final thresholds:

| Band | Rule, from earlier games only |
| --- | --- |
| Novice | Fewer than 20 prior games, none reaching depth 10 |
| Intermediate | Has reached depth 10, or median depth of 5 or more, but never ascended |
| Advanced | 1–4 prior ascensions |
| Expert | 5 or more prior ascensions |

4. **Add a continuous score** for regressions: prior mean `maxlvl`, shrunk toward the global mean with a pseudo-count of 10 games.
5. **Check that bands mean something.** Report game counts per band, and median `maxlvl` and ascension rate per band. Outcomes should rise steadily from Novice to Expert.

**Intermediate is the target population.** It stands for "ordinary players", the level the agent is aiming at, and Step 6's main comparisons run within it.

## Step 3: Population and ascension overview by role

This step answers which roles ordinary players get furthest with, which informs whether the agent's backbone work should start on a subset of roles rather than random roles.

1. **Per role,** one row each: games, share of all games, ascensions, ascension rate, median `maxlvl`, median `points`, and the median and interquartile range of `turns` for ascended games.
2. **The same table within the Intermediate band only.** Role rankings among ordinary players may differ from the overall picture, and that's the version that matters here.
3. **Ascension rate by role × skill band,** as a heatmap with counts annotated.
4. **Race and alignment** only as a secondary breakdown, if a role's results look split by them.

Outputs: `role_overview.csv`, `role_overview_intermediate.csv` and `role_by_band.png`.

## Step 4: Which milestones ascenders achieve or skip

A milestone most ascenders achieve is part of the backbone; one many ascenders skip is optional. The 3.6 bits cover only twelve milestones, so Mines, Minetown, Oracle and Quest progress must wait for pass 2.

1. **Sanity check on ascended games.** The endgame chain should be near 100%: Bell, Gehennom, Candelabrum, Book, Invocation, Amulet, End Game, Astral. Investigate any shortfall before going further, since it would mean the decoding is wrong.
2. **Optional milestone rates among ascensions:** finished Sokoban (0x0400), Mines' End luckstone (0x0200) and killed Medusa (0x0800). Report overall, by role, and by skill band.
3. **Route variants among ascensions.** Count the four Sokoban × luckstone combinations: both, Sokoban only, luckstone only, neither. These are the first data-backed route variants.
4. **When they happen, roughly.** Among games that didn't ascend, report the Sokoban and luckstone rates by `maxlvl` band (1–5, 6–10, 11–15, 16–20, 21+). That gives a rough sense of how deep players typically are when they do these.

Outputs: `milestones_ascended.csv`, `route_variants.csv` and `milestones_by_depth.csv`.

## Step 5: Survival by depth and branch, and death causes

This step shows where ordinary runs end and what ends them: the first bottlenecks along any backbone. Run everything within the Intermediate band first, then repeat for the other bands.

1. **Survival curve.** S(d) = share of games with `maxlvl` ≥ d, for d = 1 to 50, plotted by skill band and, for the Intermediate band, by role.
2. **Hazard by depth.** h(d) = share of games reaching depth d whose deepest level is d. This is "where runs stop", and its peaks mark the bottlenecks. Exclude ascended games, or treat them as completing.
3. **Branch of death.** Cross `deathdnum` with `deathlev`, to see how often runs end in the Mines, Sokoban or the Quest, and at what depths. It's a crude first measure of how risky each detour is.
4. **Death causes by depth band** (1–5, 6–10, 11–15, 16–20, 21+). Normalise the `death` text: strip articles and suffixes like "while helpless", and group by monster or cause. Report the top 20 per band, plus the share of non-combat deaths: starvation, poisoning, drowning, falling objects, and late quits.
5. **Pace.** Median `turns` at death per `maxlvl` band, as a rough turn budget per depth.

Outputs: `survival.png`, `hazard.png`, `death_branch.csv`, `death_causes_by_depth.csv` and `pace_by_depth.csv`.

## Step 6: Do optional milestones help ordinary players?

The question for each optional milestone (finished Sokoban, Mines' End luckstone) is whether achieving it lets Intermediate players get further, beyond the fact that stronger players achieve it more often.

**The main trap is survivorship.** A game that finished Sokoban had to live long enough to do so, so a naive comparison flatters every milestone. Use a landmark design:

1. **Pick a landmark depth L** that's deeper than where the milestone is usually completed, from Step 4's depth table (for example L = 12). Keep only games with `maxlvl` ≥ L.
2. **Outcome:** reaching a later depth, such as `maxlvl` ≥ 20, and separately, ascension.
3. **Compare with and without the milestone, three ways:**
    - *Stratified:* within the Intermediate band, by role.
    - *Regression:* logistic regression of the outcome on the milestone, the continuous skill score and role.
    - *Within-player:* only players who reached L both with and without the milestone, comparing their own games.
4. **Turn cost.** At equal `maxlvl`, compare median `turns` with and without the milestone, to show what each detour costs in time.

Report effect sizes with 95% intervals for each method, side by side. A milestone that helps under all three methods is a strong backbone candidate; one that only helps in the naive comparison is likely survivorship or skill.

**Known limit:** without event timing, some milestones may have been completed *after* depth L. Pass 2 fixes this with real timing.

Output: `cohort_effects.csv`, one row per milestone, method and outcome.

## Deliverables

All files go in `outputs/`, along with the scripts that produced them, one per step. The headline deliverable is `outputs/REPORT.md`, with these sections in this order:

1. **Data after cleaning:** games, ascensions and players, with the filter log.
2. **Roles for ordinary players:** the three roles with the best Intermediate ascension rate and median depth, with their numbers.
3. **Required and optional milestones:** a table of each milestone's rate among ascensions, overall and Intermediate.
4. **Route variants:** the Sokoban × luckstone combinations among ascensions.
5. **Where Intermediate runs end:** the three largest hazard peaks, each with its depth range, most common branch and leading death causes.
6. **Do optional milestones help?** A table with milestone, outcome, and the effect with interval under each of the three methods.
7. **Draft backbone v1:** proposed required milestones, optional milestones and starting roles, each justified by a number above.
8. **Open questions for pass 2:** what needs event timing or recordings to answer.

Every number in the report carries its count, and every rate its interval. Plots get axis labels with units, and a one-line caption saying what to read from them.

## Acceptance checks, caveats and what comes next

Pass all of these before writing the report:

- [ ] **Decoding is right.** Among ascensions, the endgame chain bits are near 100%, and `death` = "ascended" agrees with bit 0x0100.
- [ ] **The dungeon mapping holds.** Each `deathdnum` value has a plausible depth range and plausible death causes.
- [ ] **The filter log adds up.** Removed plus kept equals the starting count, which should be near NLD-NAO's roughly 1.5 million games across all versions.
- [ ] **No leakage.** A unit test shows that changing a player's later games leaves an earlier game's skill features unchanged.
- [ ] **Skill bands are monotone** in median depth and ascension rate.
- [ ] **Results are stable** across start-scumming cutoffs of 100, 500 and 1,000 turns.

**Caveats to state in the report:**

- **Only twelve milestones.** 3.6 records nothing about entering the Mines, Minetown, the Oracle or the Quest.
- **`maxlvl` isn't branch-aware.** A Mines level and a main-dungeon level at the same depth count the same.
- **Observational data.** Skill controls reduce confounding but don't remove it.
- **NAO players aren't the agent.** The Intermediate band is a stand-in, not a match.

**What passes 2 and 3 will need,** to be planned only after this report is read:

- **Pass 2, route order and timing:** read each recording's status line for depth over turns, and label branches with a small classifier on map screens, using NLD's streaming dataset API.
- **Pass 3, kits:** experience level, HP, armour class and visible inventory at each milestone, for readiness profiles and kit-based starts.