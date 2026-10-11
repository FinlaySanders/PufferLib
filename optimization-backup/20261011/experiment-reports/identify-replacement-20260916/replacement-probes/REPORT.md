# Frozen policy identity readouts

Two 1B s701 policies; frozen trained encoders, supervised linear or 128-unit MLP readouts. Balanced synthetic inputs; identical held-out identity/appearance pairs and state templates. Two probe seeds, two learning rates selected on validation loss. No RL training or encoder updates.

| Policy | Class | Representation | Readout | Mean test accuracy |
|---|---|---|---|---:|
| identify1b_s701 | rings | pre | linear | 94.12% |
| identify1b_s701 | rings | pre | MLP | 96.35% |
| identify1b_s701 | rings | post | linear | 65.51% |
| identify1b_s701 | rings | post | MLP | 70.28% |
| identify1b_s701 | rings | pooled | linear | 12.09% |
| identify1b_s701 | rings | pooled | MLP | 12.35% |
| identify1b_s701 | amulets | pre | linear | 94.10% |
| identify1b_s701 | amulets | pre | MLP | 92.71% |
| identify1b_s701 | amulets | post | linear | 57.64% |
| identify1b_s701 | amulets | post | MLP | 53.82% |
| identify1b_s701 | amulets | pooled | linear | 14.58% |
| identify1b_s701 | amulets | pooled | MLP | 19.79% |
| identify1b_s701 | scrolls | pre | linear | 96.16% |
| identify1b_s701 | scrolls | pre | MLP | 97.55% |
| identify1b_s701 | scrolls | post | linear | 79.50% |
| identify1b_s701 | scrolls | post | MLP | 81.32% |
| identify1b_s701 | scrolls | pooled | linear | 14.58% |
| identify1b_s701 | scrolls | pooled | MLP | 14.98% |
| idreplace1b_s701 | rings | pre | linear | 100.00% |
| idreplace1b_s701 | rings | pre | MLP | 100.00% |
| idreplace1b_s701 | rings | post | linear | 99.55% |
| idreplace1b_s701 | rings | post | MLP | 100.00% |
| idreplace1b_s701 | rings | pooled | linear | 44.49% |
| idreplace1b_s701 | rings | pooled | MLP | 58.18% |
| idreplace1b_s701 | amulets | pre | linear | 100.00% |
| idreplace1b_s701 | amulets | pre | MLP | 100.00% |
| idreplace1b_s701 | amulets | post | linear | 100.00% |
| idreplace1b_s701 | amulets | post | MLP | 100.00% |
| idreplace1b_s701 | amulets | pooled | linear | 11.11% |
| idreplace1b_s701 | amulets | pooled | MLP | 11.81% |
| idreplace1b_s701 | scrolls | pre | linear | 100.00% |
| idreplace1b_s701 | scrolls | pre | MLP | 100.00% |
| idreplace1b_s701 | scrolls | post | linear | 100.00% |
| idreplace1b_s701 | scrolls | post | MLP | 100.00% |
| idreplace1b_s701 | scrolls | pooled | linear | 45.83% |
| idreplace1b_s701 | scrolls | pooled | MLP | 52.88% |

Replacement removes appearance dependence for known items by construction. Improved identity readout therefore need not mean improved item-use decisions. The pooled test includes one known target and seven unknown distractors; it excludes equipped-item passthrough. These are synthetic representation diagnostics, not on-policy behaviour or evidence of optimal item use.
