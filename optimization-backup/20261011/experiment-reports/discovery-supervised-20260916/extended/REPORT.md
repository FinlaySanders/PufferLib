# Extended additive-encoder supervised fits

## Result

All six fits have zero training and validation identity errors after continuation. All three scroll fits also have zero held-out identity errors. Two ring fits retain a few held-out errors, clustered in particular appearance–identity pairs; one ring fit reaches zero. This supports a residual generalisation/interference issue rather than evidence of an absolute representational capacity limit.

| Class | Seed | Extra epochs run | Selected extra epoch | Training errors before → after | Validation errors before → after | Test errors before → after | Known test examples | Final test accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| rings | 1 | 3000 | 2975 | 0 → 0 | 2 → 0 | 3 → 8 | 5376 | 99.8512% |
| rings | 2 | 1600 | 1000 | 0 → 0 | 5 → 0 | 30 → 31 | 5376 | 99.4234% |
| rings | 3 | 3000 | 3000 | 0 → 0 | 28 → 0 | 49 → 0 | 5376 | 100.0000% |
| scrolls | 1 | 3000 | 3000 | 0 → 0 | 23 → 0 | 0 → 0 | 6048 | 100.0000% |
| scrolls | 2 | 3000 | 3000 | 0 → 0 | 13 → 0 | 9 → 0 | 6048 | 100.0000% |
| scrolls | 3 | 3000 | 2975 | 0 → 0 | 0 → 0 | 4 → 0 | 6048 | 100.0000% |

## Remaining ring errors

These are supervised classifier mistakes on synthetic inputs, not observed in-game decisions. Each held-out pairing has 32 state templates.

| Seed | True identity | Shuffled appearance | Readout predicts | Errors |
|---|---|---|---|---:|
| 1 | increase accuracy | engagement | protection | 4 |
| 1 | teleportation | black onyx | polymorph | 2 |
| 1 | protection from shape changers | black onyx | invisibility | 2 |
| 2 | invisibility | twisted | levitation | 18 |
| 2 | protection from shape changers | engagement | free action | 9 |
| 2 | searching | silver | see invisible | 3 |
| 2 | invisibility | twisted | free action | 1 |

The strongest remaining cluster is invisibility with a twisted appearance in seed 2: 19 of its 32 test state templates are misclassified (18 as levitation, one as free action). Aggregate accuracy conceals this local failure. The pair was held out from encoder training, although both the identity and appearance individually occurred in training.

## What changed with longer training?

Ring test error counts changed from 3/30/49 to 8/31/0. Scroll errors changed from 0/9/4 to 0/0/0. More optimization does not improve held-out identity uniformly: training identity was already perfect, while validation multitask loss continued to improve.

The additive architecture can reach perfect readout, so these data do not show that it is fundamentally unable to encode identity. They do show that learning appearance invariance is not guaranteed, even under direct supervision. Appearance replacement guarantees that a known item’s representation does not depend on its shuffled appearance; that remains a reasonable inductive-bias experiment for RL.

This still cannot establish whether the small residual errors are information lost by the encoder, limitations of the jointly trained linear readout, the finite dataset/split, or the multitask optimization trajectory. No RL advantage is established.

## Protocol

Continue each of the six validation-selected 500-epoch additive checkpoints from the independent-state experiment, using the exact same dataset, split and multitask loss. Up to 3,000 additional epochs, Adam at 0.001 with ReduceLROnPlateau on validation multitask loss (factor 0.5, patience 150 epochs, minimum 1e-6). Early stop after 1,000 extra epochs if validation fails to improve for 600 epochs. Select by minimum validation multitask loss, never test accuracy.

Original optimizer states were not saved, so Adam moments were restarted. Baseline checkpoints and results are preserved. This is continuation of learned weights, not a bit-identical continuation of the original optimizer. Full train/validation/test mistakes, state features and learning curves are saved for every seed.

No production code or RL policies were changed.
