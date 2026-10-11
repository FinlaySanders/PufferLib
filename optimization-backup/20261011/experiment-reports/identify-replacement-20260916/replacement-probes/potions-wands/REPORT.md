# Frozen policy identity readouts

Two 1B s701 policies; frozen trained encoders, supervised linear or 128-unit MLP readouts. Balanced synthetic inputs; identical held-out identity/appearance pairs and state templates. Two probe seeds, two learning rates selected on validation loss. No RL training or encoder updates.

| Policy | Class | Representation | Readout | Mean test accuracy |
|---|---|---|---|---:|
| identify1b_s701 | potions | pre | linear | 96.05% |
| identify1b_s701 | potions | pre | MLP | 97.85% |
| identify1b_s701 | potions | post | linear | 67.35% |
| identify1b_s701 | potions | post | MLP | 71.45% |
| identify1b_s701 | potions | pooled | linear | 17.80% |
| identify1b_s701 | potions | pooled | MLP | 17.15% |
| identify1b_s701 | wands | pre | linear | 96.01% |
| identify1b_s701 | wands | pre | MLP | 97.61% |
| identify1b_s701 | wands | post | linear | 79.08% |
| identify1b_s701 | wands | post | MLP | 81.47% |
| identify1b_s701 | wands | pooled | linear | 15.06% |
| identify1b_s701 | wands | pooled | MLP | 15.23% |
| idreplace1b_s701 | potions | pre | linear | 100.00% |
| idreplace1b_s701 | potions | pre | MLP | 100.00% |
| idreplace1b_s701 | potions | post | linear | 100.00% |
| idreplace1b_s701 | potions | post | MLP | 100.00% |
| idreplace1b_s701 | potions | pooled | linear | 28.80% |
| idreplace1b_s701 | potions | pooled | MLP | 31.15% |
| idreplace1b_s701 | wands | pre | linear | 100.00% |
| idreplace1b_s701 | wands | pre | MLP | 100.00% |
| idreplace1b_s701 | wands | post | linear | 100.00% |
| idreplace1b_s701 | wands | post | MLP | 100.00% |
| idreplace1b_s701 | wands | pooled | linear | 11.72% |
| idreplace1b_s701 | wands | pooled | MLP | 11.55% |

Replacement removes appearance dependence for known items by construction. Improved identity readout therefore need not mean improved item-use decisions. The pooled test includes one known target and seven unknown distractors; it excludes equipped-item passthrough. These are synthetic representation diagnostics, not on-policy behaviour or evidence of optimal item use.
