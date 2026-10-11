# NetHack

PufferLib environment for NetHack 3.6.6 over
[fast-nle](https://github.com/FinlaySanders/fast-nle): 26-verb factored
action space (verb, item slot, direction, spell slot), legality masking,
decomposed-score reward, custom CUDA encoder/decoder (`ocean/nethack/nethack.cu`).

## Setup

```bash
pip install -e .
./build.sh nethack    # clones + builds vendor/fast-nle, then the training backend
```

Run from the repo root — the engine finds its data at
`vendor/fast-nle/build/dat` (override with `NETHACKDIR`).

## Train

```bash
./puffer train nethack
```

Reward coefficients and hypers live in `config/nethack.ini`.

## Watch a policy

```bash
./build.sh nethack --fast    # builds the ./nethack demo binary
./nethack                    # interactive TTY demo
NH_WEIGHTS=checkpoints/nethack/<run>/<step>.bin ./nethack
```

Interactive controls (default when stdin is a TTY):

| Key | Action |
|-----|--------|
| `Space` | one policy step; hold advances at **5 Hz** |
| `Shift+Space` | hold advances at **20 Hz** (fallback: hold `S`) |
| `q` / `Esc` | quit |

Weight resolution: `NH_WEIGHTS` if set (`score` / `depth` shorthands, or
a path), else `resources/nethack/nethack_score_weights.bin`.
`NH_MULTI=1` randomizes role/race/gender/align. `NH_TTY=1` shows the
engine tty map. Set `NH_SEED` to replay a seed.

```bash
./nethack 10000 0            # headless 10k steps (prints avg_score / avg_max_depth)
./nethack 1000 50            # auto-run at 50 ms/frame
```

GPU eval (same stack as training rollouts):

```bash
./puffer eval nethack --load-model-path=latest
# or pin a run:
./puffer eval nethack --load-model-path=checkpoints/nethack/<run>/<step>.bin
```

### Identification target head

The decoder has 21 sampled heads: verb, 12 verb-specific inventory pointers,
identification target, six direction heads, and spell slot. The target shares
inventory keys and is sampled in parallel. READ preserves its inventory letter
before consuming the scroll and selects it when an identify menu appears.
Unavailable targets and remaining identification allowance use the existing
select-all/menu-order fallback; automatic identify-all needs no choice.

The environment marks whether the sampled target was selected in an identify
menu. Rollout log-probabilities are finalized after the step, and PPO excludes
the head from both log-probability and entropy when unused (including other
scrolls, failed reads, and automatic identify-all). No hidden scroll identity is
used. This adds one query projection and changes action/logit
layout; old checkpoints require conversion before loading.

Validation: `python3 tests/test_nethack_encoder.py` checks CUDA forward/backward
against numerical and PyTorch references. Then `python3 tests/test_nethack_identify.py`
checks a live one-item identification, menu selection/fallback, and verb gating.

### Discovered inventory identities

Known item types replace their appearance glyph in the inventory observation.
Unknown items retain the public appearance glyph. The separate additive
identity channel is padded out; item-state features (including the type-known
flag, enchantment and blessed/cursed knowledge) are unchanged. Internal raw
inventory glyphs and action eligibility are unchanged.

This is the default for new training and evaluation. Set `NH_DISC_SWAP=0` to
reproduce the additive observation semantics of older identify-head policies;
`NH_DISC_SWAP=1` explicitly selects replacement. Tensor sizes and checkpoint
layout are unchanged, but the observation semantics must match training.
