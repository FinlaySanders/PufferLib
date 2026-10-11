# NetHack development timeline

Figure: ../out/score_progress_history.png.
Source rows: milestones.csv and milestones.json. Renderer: ../history.c.

This is a **selected development-milestone timeline**, not a learning curve
from one run, a complete best-so-far frontier, or a controlled scaling experiment.
The x-axis is calendar date, not accumulated training compute. Connecting lines
are visual guides between sparse observations.

The plotted historical values are reported scores, mostly means. The July 8
commit reports approximately 1,100 without specifying aggregation. The July 3
zero point is a user-confirmed project-start anchor, not a measured evaluation. They include different
training budgets, architectures, engines, and evaluation procedures. In particular,
the August 13–15 final-panel values have not been re-certified using today's
burn-in procedure. Do not call these historical points modern certificates.
Seed panels average reported means; only the final Python point pools raw episodes.

## Provenance

- July 3: user-confirmed first day, shown at zero as the project-start anchor.
  Commit 1cbd975d ("nethack encoder") corroborates work on this date.
- July 6: dated campaign notes report 406.9 after 259M training steps.
- July 8: commit 9ceeab2a is titled "1100 score"; approximate historical report.
- July 14: dated campaign notes give five completed 340M runs: 3,287, 3,392,
  3,807, 3,816 and 3,873.6. The average is 3,635.12. The last value is the
  completed rerun replacing the earlier crashed run, not its partial score.
  Most inputs were rounded in the notes; this is not a modern certificate.

- July 31: commit 7919bbda documents a Monk 250M policy's 10K-game eval, 3,604.8.
  Retained in the source table but excluded from the chart: this is a shorter-budget
  trainer-port validation, not a champion milestone. Its inclusion incorrectly
  suggested a July plateau. No intermediate scores have been invented; the line
  now joins the July 14 and August 4 milestones as a visual guide.
- August 4: certify_all.log timestamps seven sc1b_s401–407 evaluation means.
  Their arithmetic mean is 7,392.574. All seven are included, rather than selecting
  the highest seed.
- August 13: new1b_s305.log contains the final reported score 12,863.855.
  The run starts August 13 at 21:21 (W&B run directory) and lasts about 1h53m.
- August 14: multi1b_s305.log contains the final reported score 6,608.454.
  Commit 58d36aaf on August 14 lands the random-character challenge support.
  The two stages are intentionally not connected across this task change.
- August 15: idemb1b_s311.log contains the final reported score 7,034.814.
- September 7: the first three t1122 1B seeds average 12,957.553.
- September 8: three t1122 2B seeds average 16,702.212.
- September 9: four t1122 4B seeds average 18,155.127.
  These three dates are corroborated by the dated scaling campaign notes;
  drone_long.log itself records times of day only.
- September 13: fixed 4B policies s705/s706, Python NetHackChallenge-v0:
  8,064 pooled episodes, mean 19,705.191, from ../certificates/results.json.

The September historical policies precede the final weight-export fix.
They are not the fixed policies used for the headline article results.

The earliest July milestones use contemporaneous campaign notes and commit
reports rather than raw episode logs; see each row’s measurement field.

## Rebuild

From the repository root:
    python3 resources/article/history/build_data.py
    bash resources/article/history/render.sh

build_data.py requires the original /tmp historical logs, already copied into
evidence/ for preservation. render.sh only needs the generated data.h.
Evidence snapshots have SHA-256 hashes in evidence_hashes.json.

Suggested caption:
Selected development milestones, from Monk-only training to randomised challenge
characters. Historical means use differing training budgets and evaluation
protocols; the final teal point is the pooled Python challenge certificate.
