# Trained NetHack network: silent channels and entity selection

Five matched 1B baseline score policies (`baseline_s2901`–`baseline_s2905`) were audited using the frozen CPU demo source and engine in `../nethack-linear-entity-20261006/`. Each policy played two independently seeded 4,000-decision games; activations were sampled every eight decisions. This is 5,000 sampled frames over 40,000 decisions, but only six episode endings: it is an early-game-heavy, temporally correlated sample. The audit reconstructs every entity MLP output and asserts that its sum/max pooling agrees with the actual policy input. No production source was changed.

## Exact-zero channels at 1B

Each range below is the number of channels that were exactly zero on *all* sampled inputs for a given policy, pooled over its two games. A zero on this sample is not necessarily a structurally dead neuron.

| Path / stage | Zero channels per policy |
|---|---:|
| Local hidden / output, each 256 | 0 / 0–3 |
| Terrain hidden 256 / output 128 | 4–12 / 2–8 |
| Stats MLP 64 | 2–6 |
| Message features 256 | 0 |
| Trunk projection 1024 / recurrent output 1024 | 1–4 / 0 |
| Inventory slot projection 16 / hidden 64 / value 64 | 0–1 / 0–3 / 2–14 |
| Monster representation 16 / hidden 64 / value 64 | 0 / 0–2 / 0–8 |
| Floor-item representation 16 / hidden 64 / value 64 | 0 / 5–13 / 2–13 |
| Spell key 16 / hidden 64 / value 64 | 13–15 / 60–64 / 36–52 |

The same channel indices are generally **not** silent across all five independent policies. The exception is the spell arm, where 10/16 key dimensions and 59/64 hidden dimensions are silent in every policy. This is concentrated encoder sparsity, not a blanket failure of the shared trunk. It does not rule out correlated or low-rank features among active trunk channels.

## Spell arm: a clear collapse in some policies

The two dedicated Wizard policies were evaluated over five independently seeded 2,000-decision games each. Each sampled state had two known spells; the second spell differed across seeds, and each policy cast over 1,200 times. In seed 2902, the learned spell MLP hidden layer was **64/64 zero**, and all 64 max-pool channels tied across the two spells. Seed 2901 had 60/64 hidden channels zero. The policy can still receive four handcrafted aggregate spell statistics and use its separate spell pointer keys, so this does not mean the entire policy is blind to spells.

The actual CAST choices are highly concentrated too: across those ten Wizard games, the two policies chose **force bolt (spell ID 350) on all 2,416 casts**. This was not merely forced by the action mask. In two replayed games, both starting spells were legal for 278 and 186 CAST decisions respectively; force bolt was chosen on every one. The other starting spell varied by game. This demonstrates a one-spell *behavior* in this sample, but the pooled-summary collapse does not mathematically force it: the decoder scores the separate 16-dimensional spell keys. Force bolt might also be preferred for gameplay reasons. We have not shown how these policies behave after learning more spells later in a run.

A synthetic stress test swept 40 real spell IDs (340–379), spell levels 1–7, fail rates 0–100%, and retention 0–20,000. At 1B, hidden channels that never activated in 4,200 combinations were 29, 54, **64**, 17, and 37 out of 64 for seeds 2901–2905 respectively. Seed 2903's entire hidden layer remained below the ReLU threshold on *every* tested combination; its MLP value output is therefore bias-only and cannot encode spell identity over this domain. In seed 2902, the synthetic sweep revived 10 hidden channels that the natural Wizard games did not activate, showing why observed inactivity must not be equated with structural death.

The collapse developed during training. In seed 2903's checkpoint series, the synthetic-sweep hidden dead count was **0/64 at 131M**, **53/64 at 393M**, and **64/64 by 524M**, remaining there at 1B. Other seeds also became sparser, at different rates. The immediate mechanism is the stack of ReLUs: negative pre-activations give exact zeros, and a unit that is off on all visited inputs receives no ordinary backward gradient through that gate. This establishes *where* the information is lost and *when* it emerged, but not whether Muon, the reward, data distribution, or their interaction drove the weights there. Muon was common to all these runs, so this audit cannot attribute the effect to Muon.

## Which entities win the max pools?

For one 4,000-decision game per policy, among channel pairs with at least 100 states in which both had a unique max, **24–80 inventory pairs per policy** selected the same slot at least 95% of the time; there were 827–1,578 eligible pairs. Inventory pools used **9.6–14.9 distinct winning slots per sampled state** when at least two channels had unique winners. Floor-item pools had **4–29** such agreeing pairs among 450–996 eligible pairs. The monster sample was too sparse in most games to judge pairwise agreement. The spell pool was dominated by ties, as expected from its inactive MLP.

Some inventory pairs do appear redundant on these trajectories. In seed 2901, eight pairs had both >95% co-winner agreement and >0.95 correlation in their max values **in each of two independent games**. For example, channels 7 and 48 always co-selected the same inventory item when they had a unique max (478 and 233 sampled states); their pooled values correlated 1.00 and 0.99 respectively. They selected many different slots as inventory changed, but the winners were always the same item class in those games. This looks like duplicate or closely related item detectors, not a hard-coded slot preference. In seed 2902, no pair met both criteria in both games, so this is not a universal pattern. It is not proof that the channels are interchangeable for downstream behavior.

In the original two-game samples, each policy had only **0–2 inventory channels** and **0–1 floor-item channels** that picked one fixed slot in >90% of at least 100 unique-winner states. Common item-pointer actions also varied their target slots; for example EAT had 854 multi-choice uses and THROW 1,317, with their top slot chosen only 6.8% and 5.6% of the time. Low-use heads cannot be judged from this sample.

The architecture provides a plausible route to local redundancy: narrow per-entity projections feed ReLU MLPs, then max pooling routes each channel's gradient through its current winner. Similar channels can therefore specialize on the same salient item. The audit observes repeated winners and correlated values, but cannot identify the optimizer or reward as the root cause without a controlled training ablation. A next focused test would compare spell-path gradients and channel activity through training, then try a less easily gated spell projection or a supervised spell-identity probe; inventory co-winner pairs should be checked on more diverse late-game inventories before changing that arm.

Audit code and raw outputs: `audit.c`, `spell_sweep.c`, `cast_choices.c`, `baseline_s*_game*.txt`, `wizard_s*_game*.txt`, `cast_s*_game*.txt`, `pair_s*_game811.txt`, and `corr_s{2901,2902}_game{811,1447}.txt` in this directory.
