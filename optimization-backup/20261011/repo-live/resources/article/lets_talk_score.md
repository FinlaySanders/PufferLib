## Let's Talk Score

Anyone familiar with NetHack will know that score is not a good measure of progress. Score rewards killing things, hoarding gold and, above all, staying alive; it says nothing about the Amulet. Having said that, if your agent can't learn to farm score, it definitely won't learn to beat the game. The plan here is deliberately two-stage: first get an agent that is competent but misaligned, farming score for all it's worth, and only then point it at the true goal, ascension. This section is about stage one, and about being honest that it is only stage one.

A word on what the NetHack Challenge actually measures. Every game rolls a random character: role, race, gender and alignment. You are scored on the **median** over many games, on an unmodified NetHack, with no test-time tricks. That protocol is the bar AutoAscend set in 2021 and has held since, and it is the one every number below is measured against.

### The result

[FIGURE: bars_median_gym.png]
*Median score on the real NetHackChallenge-v0 environment. AutoAscend's 2021 challenge median against the same agent architecture trained for 1, 2 and 4 billion steps.*

On the real NetHackChallenge-v0 environment, over 8,064 games, the 4B agent scores a **median of 11,516** and a mean of 19,705. AutoAscend's challenge median was 5,336; a 2023 re-evaluation put it at 4,918 with a mean of 8,556.[^aa] That is 2.16× on the median and 2.30× on the mean. It isn't one lucky seed either: the two independently trained 4B agents came in at 11,674 and 11,343.

### How I measured it

A result like this is only worth what its evaluation is worth, so here is exactly what sits behind the numbers.

Training runs on a fast fork of the NetHack engine (more on that in the next section), so the obvious question is whether the fork is quietly making the game easier. To rule that out, every set of weights is evaluated three ways with nothing changed but the engine underneath:

- **fork engine** — our fast build, with the agent's observations read straight out of engine memory. Cheap enough for 20,000-game evaluations, so this is where the scaling comparisons come from.
- **stock NLE** — the unmodified NetHack Learning Environment engine, with the same observations reconstructed from what the game shows on screen.
- **NetHackChallenge-v0** — the real gym environment, exactly as the challenge ran it.

[FIGURE: gap_median.png]
*The same policies evaluated three ways. Percentages are the gap to the fork-engine result of the same size.*

At 4B the stock engine lands 1.9% below the fork on median and the real gym 2.5% above it. The fork is a speed tool, not a scoring advantage. (The stock engine sits about 6% below on the mean; that gap is a small tax on a few very long games, where reconstructing observations from the screen occasionally gets something wrong.)

Evaluation runs hundreds of games in parallel and short games finish first, so a naive average over the first N completions is biased towards early deaths. The fork and stock certs therefore drop the first 4,000 completions and keep the next 10,000 (6,000 per seed on stock); the gym runs give every worker an equal number of games instead. Means are quoted with standard errors; medians are pooled over the kept games.

| training steps | fork engine | stock NLE | NetHackChallenge-v0 |
|---|---|---|---|
| 1B | 9,098 · 13,783 ± 111 (20,000) | 8,687 · 13,103 ± 96 (24,166) | 8,919 · 13,362 ± 168 (8,064) |
| 2B | 10,084 · 17,246 ± 161 (20,000) | 10,036 · 16,614 ± 137 (24,109) | 10,345 · 16,753 ± 234 (8,064) |
| 4B | 11,225 · 19,906 ± 188 (20,000) | 11,016 · 18,758 ± 218 (12,071) | **11,516 · 19,705** (8,064) |

*Median · mean ± s.e. (games). Two seeds per size, pooled. Source: `resources/article/certificates/RESULTS.md`.*

### What more training buys

The medians rise steadily with training: 9,098 → 10,084 → 11,225 on the 20,000-game fork certs, about 11% per doubling. The means rise much faster: 13,783 → 17,246 → 19,906. The difference tells you where the learning is happening.

Roughly a third of games end below 5,000 points at every size, and about 18% below 2,000. Those are the early deaths, and more training does nothing for them; the bottom third of the score distribution is the same at 1B, 2B and 4B. The median sits just above that fixed floor, so it can only creep. The gains all go into the tail: the share of games scoring over 20,000 climbs from 22% to 33%, and over 50,000 from 3.7% to 9.8%. Extra compute buys longer survival and bigger farms, not fewer disasters.

### Thirteen games in one

[FIGURE: roles_median.png]
*Median score by role at 1B, 2B and 4B, sorted by the 4B value. About 1,500 games per role per size.*

Because the challenge randomises the character, a single policy is really thirteen policies of very different quality. At 4B the Monk (21,270), Barbarian (20,949) and Valkyrie (18,893) sit at the top; the Tourist (3,871), Healer (4,506) and Wizard (6,411) at the bottom, and those three do not clear AutoAscend's median on their own. The overall median is dragged down by the weak roles, and the improvement with training is uneven: the Ranger gained 45% across the range while the Tourist barely moved. Anyone who has tried to keep a Tourist alive past the first few floors will sympathise.

### The catch

[FIGURE: score_up_depth_down.png]
*Left: median score. Right: share of games reaching dungeon level 8 or deeper. Fork engine, 20,000 games per size.*

Now for the part the opening paragraph warned about. Every doubling of training made the agent play higher-scoring, longer, and shallower. The share of games reaching Dlvl 8 or deeper fell from 9.6% to 7.2% to 4.8%; games reaching Dlvl 10 went from 5.8% to 1.3%. The average deepest level drifted from 3.9 to 3.5 while games got longer, from 26,000 to 31,000 turns. The agent is learning that the way to score is to find a comfortable floor and farm it.

[FIGURE: depth_vs_score.png]
*Score against the deepest level reached, one dot per game. White markers are the median and interquartile range at each depth.*

Score does rise with depth: the median at Dlvl 3 is already double AutoAscend's, and it keeps climbing as the agent goes down. But 74% of games never pass Dlvl 4, and the single best game of 20,000, **385,778 points, was farmed at Dlvl 7**. The agent found the score optimum, and it isn't at the bottom of the dungeon.

That is exactly the misalignment this stage was meant to produce. We now have an agent that survives, fights, and manages its kit well enough to double the best scripted bot, on the bot's own terms. Pointing that competence at the Amulet is the next problem.

[^aa]: AutoAscend, NetHack Challenge 2021 winner, median 5,336 (competition result). The 2023 re-evaluation (median 4,918, mean 8,556) comes from [cite the re-evaluation source].
