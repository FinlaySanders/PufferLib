> **Correction — training reward clipping:** the raw-event attribution below is valid, but the trainer clips total rewards to [-1, 1] before GAE. These spikes become +1; the inference that their magnitudes dominate training variance was incorrect. See the [clipping correction](../clipping_correction/REPORT.md).

# Attribution of the reward spikes

The largest rewards are dominated by the positive-only experience-point shaping term. The largest observed event is a polymorph experience reset, not an increase in game score. Gain-level potions also produce large experience rewards.

## Matched replay

Replayed the two existing frozen 524M-policy captures (16,777,216 environment steps each). Every original full-stream lite record, sparse logits/actions/trunk record and pointer record matched byte for byte. These are the same observations, not new independent samples. Reward terms were reconstructed from before/after counters in a separate scratch build; the reward function and production trainer were not edited.

Logged every nonterminal step with |reward| > 20, every experience decrease, and the captured steps from two selected episodes. All original rewards above 500 were accounted for and were nonterminal. The death penalty is -0.472198129. Components are experience, gold, new floor, new maximum depth, new maximum character level, game-score change and new tiles.

| Action seed | Rewards > 500 | Minimum experience share | Largest raw reward | Component sum max absolute error |
|---|---:|---:|---:|---:|
| 31415 | 35 | 99.624% | 8,308.149 | 0 |
| 27182 | 15 | 99.615% | 4,292.359 | 0 |

## Largest events

| Seed | Agent/episode/step (zero-based) | Action | Experience points | Character level | Raw reward | Game score | Last message |
|---|---|---|---|---|---:|---|---|
| 31415 | 502/10/2784 | search20 | 47,203 → 138,212 | 13 → 14 | 8,308.149 | 9,151 → 9,151 | You stop searching.  You feel like a new dwarf! |
| 31415 | 23/3/4952 | search20 | 28,307 → 110,520 | 12 → 14 | 7,506.265 | 20,676 → 20,676 | You stop searching.  You feel warm!  You feel like a new woman! |
| 27182 | 320/6/6039 | quaff | 20,000 → 67,014 | 12 → 13 | 4,292.359 | 21,052 → 21,052 | You feel more experienced.  Welcome to experience level 13. |
| 31415 | 303/11/2326 | search20 | 13,012 → 57,268 | 11 → 13 | 4,041.614 | 8,112 → 8,112 | You must have been working on your reflexes. |
| 31415 | 269/1/3619 | drop | 21,157 → 60,306 | 12 → 13 | 3,574.455 | 6,532 → 6,532 | Your movements are now unencumbered. |
| 31415 | 326/8/2364 | run | 19,407 → 56,148 | 11 → 13 | 3,354.657 | 14,904 → 14,904 | You feel warm!  You feel like a new man! |
| 27182 | 214/6/5373 | move | 26,021 → 60,722 | 12 → 13 | 3,168.527 | 15,766 → 15,818 |  |
| 31415 | 502/10/2457 | search20 | 12,044 → 46,572 | 11 → 13 | 3,153.658 | 6,426 → 6,426 | You stop searching.  You feel like a new dwarf! |
| 31415 | 158/1/5425 | quaff | 5,403 → 38,842 | 10 → 12 | 3,054.271 | 27,898 → 27,908 | Your movements are now unencumbered. |
| 27182 | 375/6/4293 | run | 5,809 → 28,474 | 10 → 12 | 2,070.823 | 11,180 → 11,180 | Your movements are only slowed slightly by your load. |

## Mechanism

The experience reward is `0.0912783295 * max(experience_now - experience_previous, 0)`. The previous-experience tracker is updated after every nonterminal step, including losses. Thus it rewards regaining experience already lost; it does not measure improvement over the episode maximum. The separate character-level reward does use a maximum.

In the engine, `newman()` in `src/polyself.c` changes character level by a random integer from -2 through +2 (subject to level limits), then replaces experience with `rndexp(FALSE)`. It prints "You feel like a new ...!". This can happen during an action such as search or movement. It is not a special search reward. The recorded largest event prints "You stop searching.  You feel like a new dwarf!".

At agent 502 / episode 10 / step 2784, experience jumps from 47,203 to 138,212 (+91,009). That gives 8,307.1494 experience reward, plus 1 for a new maximum character level: total **8,308.1494**. Score stays 9,151 and dungeon depth stays 5. The earlier variance report shows **8,320** because rewards were rounded to BF16 to match training storage.

Experience level thresholds grow exponentially over the levels seen in these events (`newuexp` in `src/exper.c`). A level change can therefore move the raw experience counter by tens of thousands. `pluslvl(FALSE)` and blessed gain-level potions also raise/reset this counter. The replay includes the potion message "You feel more experienced. Welcome to experience level ..." on large quaff rewards.

A concrete loss: seed 31415, agent 23, episode 3, step 5023 goes from 128,560 to 52,860 experience, and character level 14 to 13. Reward is exactly zero. At step 5021 that same game had received 1,630.9612 reward for an experience increase from 110,692 to 128,560 with **no change in character level or score**.

## Interpretation and limits

This is a source of rare, extremely large shaped rewards that helps explain the tail-dominated variance measurements. It exposes an incentive to regain lost experience. The traces do not establish that the policy intentionally exploits that incentive, and not every experience jump is undesirable: genuine level gains are useful. No reward modification is made here.

Some last messages are overwritten by prompt handling or encumbrance updates, so we attribute the reward component for every spike but do not claim a specific polymorph/potion mechanism for each individual event without supporting messages. The original general-purpose variance conclusions should not be read as proof of irreducible noise: the largest events now have an identified reward mechanism.

## Artifacts

- Each capture directory contains `events.csv`, binary `.reward` traces, manifest, completion record and replay log.
- Scratch preparation: `../prepare_reward_capture.py`; hook: `../reward_vec_hook.h`.
- Replay: `../run_reward_capture.py`; analysis: `../analyze_reward_spikes.py`.
- Pinned reward code: `../capture-source/ocean/nethack/nethack.h`, function `nethack_reward`.
- Pinned engine: `../capture-source/vendor/fast-nle/src/polyself.c` and `src/exper.c`.
- Checkpoint/source/library details are retained in each replay manifest.
