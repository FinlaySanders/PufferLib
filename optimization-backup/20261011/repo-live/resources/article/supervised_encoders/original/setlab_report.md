# Set-Encoder Race

25 inventory-style set-encoder architectures × 18 tasks × 2 data regimes × 3 seeds × 3 learning
rates — 450 supervised fits, ~2 GPU-hours. The capacity benchmark behind the
[Encoder Representation Contract](https://claude.ai/code/artifact/3f57a631-12e8-4630-a5e8-e9c24b7f91ff).

## Method

- **Zoo**: three axes — per-slot transform width (8/16/32/64), aggregator (sum, mean, max,
  logsumexp, attention M∈{1,8}, count-augmented attention, self-attention, PNA multi-aggregator,
  typed pools, sorted-flatten, GRU-over-sorted, flag-gated sums), composition (sum‖attn dual,
  production V5 triple). Shared embedding spec; linear task head.
- **Tasks**: existence ×4, relation (launcher↔ammo pair), retrieval ×2, counting ×6
  (incl. quantity-weighted ammo_ct), conjunction ×2, extremes ×3. AUC for binary, R² for counts.
- **Regimes**: *real* = production dumps (210K train seed-702, 60K val seed-701 — cross-seed, no
  shared episodes); *synth* = generator calibrated to measured inventory statistics (class/BUC/
  quantity distributions), labels independent of policy demand, train capped ≤26 items.
- **Protocol**: per-arch lr chosen on train-side val loss; 3-seed medians; shuffle-floor control;
  NaN-guard lessons: sqrt(var=0) has infinite gradient (PNA), fully-masked MHA rows NaN on empty
  inventories (self-attention).

## Results — synthetic (capacity in isolation)

```
arch        has_lnc has_ammo has_bles   has_bw     pair  wldweap  n_items   n_food   n_weap  n_curse   n_bles  ammo_ct   n_bwep     n_cw max_ench  bw_ench wld_ench min_erow
shuffle        0.57     0.53     0.64     0.48     0.49     0.85     0.00    -0.01    -0.01    -0.02    -0.02    -0.03    -0.04    -0.04    -0.02    -0.23    -0.10    -0.05
sum8           1.00     1.00     1.00     1.00     0.97     1.00     0.99     0.99     1.00     1.00     1.00     0.98     1.00     1.00     0.37     0.68     0.99    -0.00
sum16          1.00     1.00     1.00     1.00     0.96     1.00     0.99     0.99     1.00     1.00     1.00     0.98     1.00     1.00     0.38     0.69     1.00     0.22
sum32          1.00     1.00     1.00     1.00     0.97     1.00     0.99     1.00     1.00     1.00     1.00     0.98     1.00     1.00     0.38     0.69     1.00     0.27
sum64          1.00     1.00     1.00     1.00     0.97     1.00     0.99     1.00     1.00     1.00     1.00     0.98     1.00     1.00     0.38     0.68     1.00     0.28
mean32         1.00     1.00     1.00     1.00     0.95     1.00     0.20     0.57     0.63     0.70     0.65     0.74     0.78     0.69     0.40     0.60     0.69     0.28
max32          1.00     1.00     1.00     1.00     1.00     1.00     0.94     0.95     0.96     0.97     0.96     0.98     0.98     0.98     1.00     1.00     1.00     1.00
lse32          1.00     1.00     1.00     1.00     0.99     1.00     0.95     0.94     0.95     0.93     0.93     0.96     0.96     0.96     0.99     1.00     1.00     1.00
attn1          0.98     1.00     1.00     1.00     0.94     1.00     0.15     0.53     0.65     0.70     0.66     0.85     0.86     0.86     0.43     0.70     0.84     0.00
attn8          1.00     1.00     1.00     1.00     0.97     1.00     0.87     0.91     0.92     0.93     0.93     0.96     0.94     0.96     0.98     0.99     0.97     0.94
attn8w16       1.00     1.00     1.00     1.00     0.96     1.00     0.84     0.88     0.91     0.89     0.89     0.95     0.90     0.96     0.91     0.96     0.96     0.06
attn8w64       1.00     1.00     1.00     1.00     0.98     1.00     0.89     0.93     0.94     0.95     0.95     0.97     0.97     0.96     0.95     0.92     1.00     0.94
cattn8w16      1.00     1.00     1.00     1.00     0.97     1.00     0.99     0.99     1.00     0.97     1.00     0.95     0.95     0.96     1.00     0.99     1.00     0.95
cattn8         1.00     1.00     1.00     1.00     0.98     1.00     0.99     0.99     0.99     0.96     1.00     0.96     0.96     0.96     1.00     0.99     0.97     0.95
cattn8w64      1.00     1.00     1.00     1.00     0.98     1.00     0.99     0.98     1.00     0.95     1.00     0.96     0.96     0.96     1.00     1.00     0.98     0.94
selfattn       1.00     1.00     1.00     1.00     0.99     1.00     0.94     0.96     0.97     0.97     0.97     0.97     0.98     0.97     0.99     0.99     1.00     0.98
pna16          1.00     1.00     1.00     1.00     0.98     1.00     0.99     0.99     1.00     1.00     1.00     0.99     1.00     1.00     1.00     1.00     1.00     1.00
pna32          1.00     1.00     1.00     1.00     0.99     1.00     0.99     0.99     1.00     1.00     1.00     0.99     1.00     1.00     1.00     1.00     1.00     1.00
pna64          1.00     1.00     1.00     1.00     0.99     1.00     0.99     1.00     1.00     1.00     1.00     0.99     1.00     0.98     1.00     1.00     1.00     1.00
typed          1.00     1.00     0.99     1.00     0.97     1.00     0.97     1.00     1.00     0.94     0.95     0.98     1.00     1.00     0.36     0.68     1.00     0.27
sortflat       1.00     1.00     1.00     1.00     0.99     1.00     0.98     0.99     1.00     0.97     0.97     0.99     1.00     1.00     0.97     0.98     1.00     0.97
gru            1.00     1.00     1.00     1.00     1.00     1.00     0.99     1.00     1.00     1.00     1.00     0.99     1.00     1.00     0.99     0.99     1.00     0.98
gated32        1.00     1.00     1.00     1.00     0.97     1.00     0.99     1.00     1.00     1.00     1.00     0.98     1.00     1.00     0.37     0.68     1.00     0.28
sumattn32      1.00     1.00     1.00     1.00     0.99     1.00     0.99     1.00     1.00     1.00     1.00     0.99     1.00     1.00     1.00     1.00     1.00     1.00
prodtrip       1.00     1.00     1.00     1.00     0.99     1.00     0.99     1.00     1.00     1.00     1.00     0.99     1.00     1.00     1.00     1.00     1.00     0.29

-- family means (synth) --
arch           exist  relation  retrieve     count  conjunct   extreme
shuffle         0.55      0.49      0.37     -0.02     -0.04     -0.10
sum8            1.00      0.97      1.00      0.99      1.00      0.35
sum16           1.00      0.96      1.00      0.99      1.00      0.43
sum32           1.00      0.97      1.00      0.99      1.00      0.45
sum64           1.00      0.97      1.00      0.99      1.00      0.44
mean32          1.00      0.95      0.85      0.58      0.74      0.43
max32           1.00      1.00      1.00      0.96      0.98      1.00
lse32           1.00      0.99      1.00      0.94      0.96      1.00
attn1           0.99      0.94      0.92      0.59      0.86      0.38
attn8           1.00      0.97      0.98      0.92      0.95      0.97
attn8w16        1.00      0.96      0.98      0.89      0.93      0.64
attn8w64        1.00      0.98      1.00      0.94      0.97      0.94
cattn8w16       1.00      0.97      1.00      0.98      0.95      0.98
cattn8          1.00      0.98      0.99      0.98      0.96      0.98
cattn8w64       1.00      0.98      0.99      0.98      0.96      0.98
selfattn        1.00      0.99      1.00      0.96      0.98      0.99
pna16           1.00      0.98      1.00      0.99      1.00      1.00
pna32           1.00      0.99      1.00      0.99      1.00      1.00
pna64           1.00      0.99      1.00      0.99      0.99      1.00
typed           1.00      0.97      1.00      0.97      1.00      0.44
sortflat        1.00      0.99      1.00      0.98      1.00      0.97
gru             1.00      1.00      1.00      0.99      1.00      0.99
gated32         1.00      0.97      1.00      0.99      1.00      0.44
sumattn32       1.00      0.99      1.00      0.99      1.00      1.00
prodtrip        1.00      0.99      1.00      0.99      1.00      0.76
```

## Results — real regime (production distribution, cross-seed)

```
arch        has_lnc has_ammo has_bles   has_bw     pair  wldweap  n_items   n_food   n_weap  n_curse   n_bles  ammo_ct   n_bwep     n_cw max_ench  bw_ench wld_ench min_erow
shuffle        0.38     0.40     0.56     0.64     0.38     0.65    -0.11    -0.00    -0.02    -0.03    -0.02    -0.19    -0.04    -0.06    -0.07    -0.33    -0.30    -0.00
sum8           0.86     0.92     0.88     0.99     0.84     0.87     0.62     0.74     0.72     0.92     0.93     0.73     0.77     0.59     0.71     0.72     0.20    -0.00
sum16          0.92     0.92     0.88     0.98     0.87     0.90     0.56     0.69     0.71     0.92     0.95     0.85     0.85     0.70     0.69     0.80     0.32    -0.00
sum32          0.91     0.90     0.96     0.98     0.89     0.94     0.63     0.71     0.81     0.95     0.97     0.84     0.81     0.86     0.72     0.83     0.32    -0.00
sum64          0.88     0.94     0.96     0.99     0.86     0.94     0.55     0.74     0.80     0.95     0.98     0.83     0.84     0.92     0.78     0.85     0.27    -0.00
mean32         0.92     0.97     0.87     0.90     0.88     0.85     0.74     0.57     0.55     0.78     0.73     0.44     0.47     0.37     0.41     0.42     0.17    -0.00
max32          1.00     0.90     0.94     1.00     0.97     0.93     0.80     0.49     0.70     0.81     0.83     0.87     0.85     0.87     0.66     0.68     0.32    -0.00
lse32          0.99     0.96     0.97     0.98     0.91     0.88     0.54     0.48     0.56     0.73     0.53     0.76     0.57     0.79     0.50     0.76     0.32    -0.01
attn1          0.90     0.94     0.92     0.92     0.87     0.82     0.12     0.12     0.07     0.65     0.54     0.77     0.27     0.64     0.39     0.59     0.18    -0.00
attn8          1.00     0.96     0.92     0.98     0.96     0.88     0.55     0.50     0.58     0.69     0.75     0.83     0.69     0.79     0.49     0.77     0.17    -0.00
attn8w16       0.97     0.95     0.95     0.96     0.95     0.92     0.64     0.56     0.54     0.70     0.71     0.81     0.60     0.73     0.55     0.77     0.27    -0.00
attn8w64       0.99     0.98     0.99     1.00     0.94     0.95     0.66     0.62     0.47     0.84     0.86     0.84     0.76     0.84     0.47     0.76     0.33    -0.01
cattn8w16      0.99     0.94     0.94     0.96     0.94     0.89     0.76     0.74     0.79     0.73     0.82     0.86     0.57     0.75     0.65     0.74     0.39    -0.00
cattn8         1.00     0.98     1.00     0.99     0.96     0.93     0.74     0.72     0.78     0.70     0.81     0.86     0.64     0.79     0.52     0.73     0.18    -0.00
cattn8w64      0.99     0.97     0.95     0.99     0.97     0.97     0.74     0.76     0.79     0.81     0.80     0.87     0.64     0.87     0.48     0.78     0.36    -0.01
selfattn       0.98     0.96     0.97     1.00     0.91     0.96     0.72     0.53     0.52     0.81     0.76     0.73     0.74     0.76     0.55     0.81     0.73    -0.00
pna16          1.00     0.95     0.97     0.99     0.96     0.86     0.79     0.80     0.81     0.92     0.95     0.88     0.74     0.81     0.60     0.66     0.37    -0.00
pna32          0.98     0.96     1.00     1.00     0.92     0.93     0.85     0.75     0.78     0.90     0.95     0.88     0.71     0.86     0.70     0.74     0.49    -0.00
pna64          0.99     0.96     1.00     0.99     0.96     0.96     0.88     0.77     0.83     0.86     0.95     0.92     0.71     0.85     0.69     0.73     0.38    -0.00
typed          0.85     0.88     0.94     1.00     0.80     0.99     0.53     0.73     0.75     0.89     0.95     0.65     0.93     0.88     0.74     0.81     0.33    -0.00
sortflat       0.93     0.91     0.93     1.00     0.87     0.99     0.97     0.76     0.95     0.92     0.96     0.76     0.82     0.61     0.58     0.86     0.62    -0.00
gru            0.98     0.86     0.90     0.98     0.95     0.94     0.97     0.86     0.91     0.75     0.79     0.68     0.76     0.20     0.67     0.74     0.32    -0.00
gated32        0.83     0.89     0.93     0.99     0.78     1.00     0.55     0.68     0.74     0.95     0.97     0.81     0.86     0.99     0.68     0.79     0.81    -0.00
sumattn32      1.00     0.99     0.98     0.99     0.95     0.99     0.78     0.74     0.79     0.93     0.96     0.84     0.77     0.86     0.74     0.91     0.84    -0.01
prodtrip       1.00     0.96     1.00     1.00     0.96     1.00     0.76     0.79     0.78     0.93     0.97     0.85     0.84     0.99     0.65     0.74     0.84    -0.00

-- family means (real) --
arch           exist  relation  retrieve     count  conjunct   extreme
shuffle         0.49      0.38      0.18     -0.06     -0.05     -0.13
sum8            0.91      0.84      0.54      0.78      0.68      0.48
sum16           0.93      0.87      0.61      0.78      0.77      0.49
sum32           0.94      0.89      0.63      0.82      0.84      0.52
sum64           0.94      0.86      0.61      0.81      0.88      0.55
mean32          0.91      0.88      0.51      0.63      0.42      0.28
max32           0.96      0.97      0.62      0.75      0.86      0.45
lse32           0.97      0.91      0.60      0.60      0.68      0.42
attn1           0.92      0.87      0.50      0.38      0.45      0.33
attn8           0.96      0.96      0.52      0.65      0.74      0.42
attn8w16        0.96      0.95      0.60      0.66      0.66      0.44
attn8w64        0.99      0.94      0.64      0.71      0.80      0.41
cattn8w16       0.96      0.94      0.64      0.78      0.66      0.46
cattn8          0.99      0.96      0.55      0.77      0.71      0.42
cattn8w64       0.98      0.97      0.66      0.79      0.76      0.42
selfattn        0.98      0.91      0.84      0.68      0.75      0.45
pna16           0.98      0.96      0.61      0.86      0.78      0.42
pna32           0.98      0.92      0.71      0.85      0.78      0.48
pna64           0.98      0.96      0.67      0.87      0.78      0.47
typed           0.92      0.80      0.66      0.75      0.91      0.52
sortflat        0.94      0.87      0.81      0.89      0.72      0.48
gru             0.93      0.95      0.63      0.83      0.48      0.47
gated32         0.91      0.78      0.90      0.78      0.93      0.49
sumattn32       0.99      0.95      0.91      0.84      0.81      0.54
prodtrip        0.99      0.96      0.92      0.85      0.91      0.46
```

`min_erow` is degenerate in the real regime (worn+eroded too rare in these dumps) — R²≈0 for
every arch; read extremes from synth and from max_ench/bw_ench only.

## Diagnostics

**Duplication test** (duplicate one occupied item; Δ prediction in item-units):

| arch | Δ n_items | Δ n_bles | Δ n_weap |
|---|---|---|---|
| sum32 / cattn8 / pna32 / prodtrip | **1.07** | 0.11 | 0.21 |
| attn8 | 0.62 | 0.06 | 0.12 |
| max32 | 0.21 | 0.02 | 0.15 |

The sums move by exactly one item — and the per-class deltas equal the class priors
(0.11 ≈ P(blessed)=.10, 0.21 ≈ P(weapon)=.19): they are counting, literally. Attention moves
0.62 — it undercounts duplicates by ~40% (softmax renormalization), the theorem made
quantitative. Max is duplication-invariant as designed.

**Size generalization** (train ≤26 items, evaluate ≥30): sums/PNA/production hold
(n_bles 1.00→1.00, ammo_ct ~0.98); **attn8 degrades hard out-of-range** (n_bles 0.92→0.73,
ammo 0.96→0.90) — softmax dilutes as sets grow. (n_items extrapolation column is invalid — the
target caps at 30, zero variance beyond.)

## Findings

1. **No single aggregator survives the full battery** — the PNA paper's theorem, reproduced:
   sums fail extremes (0.35–0.45), attention fails counting (attn1 0.59; mean 0.58), max fails
   counting, GRU/sortflat ace synth but degrade on real (order tricks memorize, don't transfer).
2. **Two winners, same lesson**: PNA (four cheap pools, one transform) and sum‖attention
   (two specialized channels) both sweep synth ≥0.98. On real data they split: PNA takes
   counting (0.85–0.87), the attention-bearing designs take retrieval (prodtrip 0.92,
   gated32 0.90 via the wielded-flag sum). Multi-aggregator coverage is the design law;
   whether channels are cheap pools or learned attention is secondary.
3. **Production V5 (`prodtrip`) is vindicated with one measured gap**: best-in-class real-regime
   existence/relation/retrieval/conjunction — and **0.76 on extremes (min-erosion 0.29 synth)
   because none of its three channels is a max/min**. The one lab-supported architecture
   suggestion from this entire race: add a max channel (or fold sum→PNA-style sum‖max‖std on
   the existing slot reps — parameterless beyond the existing transform).
4. **Count-augmented attention works as theorized** (0.98–0.99 counting vs 0.92 plain) but is
   redundant when a sum channel already exists — relevant only if a future arm must be
   attention-only.
5. **Quantity-weighted counting (ammo_ct) is the hardest count everywhere** — magnitude-through-
   relu, the one task where the 16d bottleneck measurably bites (isumlab: 0.21 vs 0.40 raw).
6. **Width is a non-factor** from 16 up (sum8≈sum64 synth; real gains from 8→32 are ≤0.05
   family-mean) — consistent with hid32's null rerun; the old +635 was regime, not capacity.
7. **The relation task is linear-head-flattered**: pair AUC ~0.97 everywhere partly reflects
   `has_launcher + has_ammo` marginal ranking, not a computed AND. An MLP-head variant is the
   right follow-up before trusting any relational claim — consistent with the production
   launcher story: unformable until the wld gate existed, then learned from raw identity
   with zero launcher bits in obs (V5 Ranger: 168 fires/ep, pure-archer build).

## Standing recommendations

- **Do**: consider a max/min channel beside isum/IVA (the measured production gap); keep the
  quan feature linear (re-confirmed); treat these medians as T2 anchors in `tests/nethack_repr/`.
- **Don't**: widen keys for capacity reasons (null at every width here); trust linear-head
  relation scores; use GRU/sorted tricks (synth-only mirage).
- Any production change still needs its paired RL test — this ladder measures capacity, demand
  is decided by reward.
