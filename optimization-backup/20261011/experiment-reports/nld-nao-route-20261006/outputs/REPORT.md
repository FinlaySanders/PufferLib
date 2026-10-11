# NetHack route analysis: NAO xlog metadata, pass 1

Source: the standalone [NLD-NAO xlog archive](https://github.com/facebookresearch/nle/blob/main/DATASET.md), SHA-256 `309c4b1f3fd57e3dc21774a0d35eb58482046f78ad1a1e08c4d28f6369998a0a`. It is **not** restricted to the ~1.5M games with ttyrecs described in the NLD paper. Analysis uses xlog metadata only; no move order, inventory timeline, or exact Castle visits. Scripts 01–06 in the parent directory recreate the outputs.

## 1. Data after cleaning

The archive contains 2,969,906 3.6.x xlogs across 2015–2022, plus 3,547,518 3.4.3 entries kept separate. The cleaned 3.6 cohort has **734,996 games, 6,974 ascensions and 19,827 players**. Ending strings include suffixes such as `ascended while helpless` and are classified by prefix.

| Sequential rule | Removed | Kept |
|---|---:|---:|
| normal game mode | 231 | 2,969,675 |
| no early quit or escape (<500 turns) | 2,234,588 | 735,087 |
| deduplicate player and start timestamp | 27 | 735,060 |
| exclude identified automation/test accounts | 64 | 734,996 |

The dominant early spike is quit/escape at one turn. A 500-turn cutoff is used; cutoffs 100 and 1,000 retain 761,475, 735,023, 721,962 games respectively before deduplication, while all three retain 6976, 6976, 6976 ascensions. Only obvious `StellaAuto*` and `paxedtest` accounts are removed after that; some automation may remain. Older 3.4.3 games with timestamps contribute to **prior** skill histories only.

## 2. Roles for ordinary players

A game is Intermediate when the player had never previously ascended but had reached depth 10 in an earlier game, or had at least 20 prior games with median depth ≥5 over the preceding 20. This band contains 387,409 games. The skill label uses earlier games only; the no-future-leakage check passed. Median max depths are reported in `skill.json`.

| Role | Intermediate games | Ascensions | Ascension rate (player-bootstrap 95% CI) | Median max depth |
|---|---:|---:|---:|---:|
| Val | 65,929 | 220 | 0.33% (0.25%–0.43%) | 5.0 |
| Bar | 12,320 | 33 | 0.27% (0.17%–0.40%) | 5.0 |
| Sam | 14,238 | 33 | 0.23% (0.15%–0.34%) | 6.0 |
| Mon | 15,640 | 19 | 0.12% (0.07%–0.19%) | 6.0 |
| Arc | 19,805 | 33 | 0.17% (0.09%–0.26%) | 5.0 |

Valkyrie has the strongest observed Intermediate ascension rate; Samurai and Monk have median depth 6. These are candidate curriculum roles, **not** a reason to abandon random-role challenge training. Archaeologist remains useful for the agent’s pickaxe-based depth curriculum even though it is not a top human ascension role.

## 3. Required and optional milestones

| Achievement | All ascensions | Intermediate ascensions |
|---|---:|---:|
| Bell | 6974/6974 (100.0%; 100.0%–100.0%) | 669/669 (100.0%; 100.0%–100.0%) |
| Gehennom | 6974/6974 (100.0%; 100.0%–100.0%) | 669/669 (100.0%; 100.0%–100.0%) |
| Candelabrum | 6974/6974 (100.0%; 100.0%–100.0%) | 669/669 (100.0%; 100.0%–100.0%) |
| Book | 6974/6974 (100.0%; 100.0%–100.0%) | 669/669 (100.0%; 100.0%–100.0%) |
| Invocation | 6974/6974 (100.0%; 100.0%–100.0%) | 669/669 (100.0%; 100.0%–100.0%) |
| Amulet | 6974/6974 (100.0%; 100.0%–100.0%) | 669/669 (100.0%; 100.0%–100.0%) |
| Mines End prize | 5842/6974 (83.8%; 81.6%–86.0%) | 558/669 (83.4%; 80.7%–86.2%) |
| Sokoban prize | 6500/6974 (93.2%; 92.0%–94.2%) | 625/669 (93.4%; 91.6%–95.2%) |
| Killed Medusa | 6880/6974 (98.7%; 98.1%–99.1%) | 659/669 (98.5%; 97.5%–99.3%) |

All 7,897 games that acquired the Amulet also had Bell, Candelabrum, Book, Gehennom, and Invocation bits. But 114 of them had **not** killed Medusa; 553 had not collected the Sokoban prize, and 1309 had not collected the Mines End prize. Those three are therefore optional for reaching the Amulet. “Finished Sokoban” and “Mines End” bits actually record collecting the special prizes, not mere branch entry. The End Game and Astral bits in xlog code report location **at game end**; they are not historical visit flags for games that died earlier.

## 4. Route variants among ascensions

| Sokoban prize | Mines End prize | Ascensions | Share (player-bootstrap 95% CI) |
|---|---|---:|---:|
| True | True | 5,488 | 78.7% (76.7%–80.9%) |
| True | False | 1,012 | 14.5% (12.8%–16.6%) |
| False | True | 354 | 5.1% (4.2%–6.0%) |
| False | False | 120 | 1.7% (1.3%–2.2%) |

These are end-of-game combinations, not the order in which the two branches were visited. All four combinations occur; both prizes are common but neither is mandatory.

## 5. Where Intermediate runs stop

A depth-band hazard is the share of games that reached the first depth in the band and whose deepest recorded level lies in that band, excluding ascensions. Branch is the dungeon number **where the run ended**, not necessarily the branch of its deepest level.

| Max-depth band | Stopped / reached | Hazard (player-bootstrap 95% CI) | Most common death branches | Leading recorded death causes |
|---|---:|---:|---|---|
| 7–8 | 56,186/99,219 | 56.6% (54.8%–58.2%) | 2: 24,873, 0: 23,916, 4: 4,891 | killed by a soldier ant: 3,482, killed by a giant spider: 1,860, killed by a fire ant: 1,271 |
| 10–12 | 20,142/31,033 | 64.9% (63.4%–66.6%) | 2: 8,944, 0: 7,685, 4: 2,358 | killed by a leocrotta: 661, killed by a soldier ant: 624, killed by a mumak: 524 |
| 25–28 | 1,892/3,894 | 48.6% (45.5%–51.4%) | 0: 1,327, 3: 126, 1: 117 | killed by a minotaur: 226, petrified by Medusa: 60, drowned in a pool of water by an electric eel: 41 |

Death-dungeon numbers were checked against actual level ranges and causes: 0 main dungeon, 1 Gehennom, 2 Mines, 3 Quest, 4 Sokoban, 5 Fort Ludios, 6 Vlad’s Tower, 7 Planes. `maxlvl` is not branch-aware, so a given depth band mixes branches. The 25–28 band is **consistent with** the Medusa/Castle region; it does not prove Castle entry. For the agent, the 7–12 hazards argue for better early survival and kit assembly before deeper descent.

## 6. Do optional milestones help?

Among 8,073 Intermediate games whose `maxlvl` reached 15, both prize flags strongly **associate** with reaching depth 20 and ascension. Example:

| Prize flag | Outcome | Flag yes | Flag no | Raw risk difference (player-bootstrap 95% CI) | Adjusted odds ratio (player-cluster 95% CI) | Within-player difference (player-bootstrap 95% CI) |
|---|---|---:|---:|---:|---:|---:|
| mines | depth20 | 83.2% (4542 games) | 57.9% (3531 games) | +25.3% (17.5%–32.1%) | 3.65 (2.75–4.86) | +23.9% (19.7%–27.5%; 573 players) |
| mines | ascended | 12.3% (4542 games) | 3.1% (3531 games) | +9.1% (7.5%–10.8%) | 4.49 (2.97–6.78) | +7.9% (5.0%–10.9%; 573 players) |
| soko | depth20 | 81.3% (5177 games) | 55.7% (2896 games) | +25.6% (16.9%–33.0%) | 4.29 (3.35–5.51) | +33.8% (29.5%–38.6%; 370 players) |
| soko | ascended | 12.1% (5177 games) | 1.5% (2896 games) | +10.6% (9.5%–11.7%) | 11.24 (6.67–18.95) | +4.6% (1.9%–7.3%; 370 players) |

The regression adjusts for prior shrunk mean depth, role and version; the within-player column uses players with both prize and no-prize games. **None of these contrasts estimates the benefit of taking the detour.** The xlog has no event timestamp: a prize may have been collected after depth 15 or even after depth 20. Players also select detours according to their current kit and prospects. This is a candidate to test with recordings or policy experiments, not a causal finding.

## 7. Draft backbone v1 for our agents

1. **Survive and build a kit before rushing.** Train an early phase that reliably gains experience, armour and usable items through roughly depth 12. The human failure concentration at depths 7–12, and our depth policy’s Castle deaths, both make a pure digging objective incomplete.
2. **Keep optional branches conditional on the kit.** Mines and Sokoban prizes are common among human winners but demonstrably skippable. Teach branch navigation and reward their useful items, then compare skip/take policies at equal compute. Do not bake in a compulsory detour from these observational rates.
3. **Reach Castle when ready, potentially bypassing Medusa.** Getting Castle’s wand of wishing is a useful subgoal for equipment; killing Medusa is not required for Amulet acquisition. Gate descent on a practical survival kit rather than dungeon depth alone. The xlog cannot tell which kit or exact path works.
4. **Collect the mandatory invocation chain:** Quest Bell, Vlad’s Candelabrum, and Wizard’s Book, then perform the Invocation and acquire the Amulet. These bits are present in all 7,897 recorded Amulet-acquiring games. The order of Castle, Quest and other preparatory tasks is unresolved by this metadata; a staged policy should allow different orders according to its kit.
5. **Train ascension separately after Amulet.** Escaping with it and clearing the Planes are further phases, not addressed by the current depth or score objective.

For role curricula, start survival/kit learning with Valkyrie, Barbarian or Samurai; use Archaeologist as a controlled tool-rich depth curriculum. Keep random role/race/gender evaluation as the target.

## 8. Questions for recordings and experiments

- At what turn and dungeon depth are Mines End and Sokoban prizes actually obtained, and which came first?
- Which ascenders bypass Medusa, and what terrain or resources do they use?
- What exact inventory, resistances, HP, armour class, experience and movement tools do successful runs carry into the Medusa/Castle region?
- What fraction of Castle visitors obtain and use the wand of wishing, and how do they cross the moat? `maxlvl` cannot answer this.
- Can a score policy with a learned kit switch to controlled descent and beat the depth policy on Castle survival at the same step budget?

The NAO population is not the agent, and the xlog metadata has no inventory, action sequence or event timing. All intervals here are player-cluster bootstraps with fixed seed 20261006 except the regression odds-ratio intervals, which use player-cluster robust standard errors. The raw xlog SQLite is untouched.
