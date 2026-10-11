# Concrete inventory targets

This is a new controlled rerun, not a relabelling of the old 16-task results.
All six encoder architectures are trained jointly on these three targets:

- **Arrow quantity:** sum of the encoder-visible quantities of arrows, elven
  arrows, orcish arrows, silver arrows and ya. Its existing quantity feature
  caps each stack at 30, so this is not uncapped in-game ammunition count.
- **Best armour enchantment:** highest known enchantment among carried armour.
  Inventories with no known armour enchantment are excluded for this target.
  “Best” here means highest enchantment, not the armour a player should wear.
- **Wielding a bow:** whether the wielded item is a bow, elven bow, orcish bow,
  or yumi. Crossbows and slings are not counted as bows.

The first two metrics are held-out R²; the third is ROC-AUC (chance 0.5).
Architecture bars use medians over three supervised fit seeds. The readout plot
uses freshly fitted linear and 128-unit ReLU MLP readouts over frozen full
sum+max+passthrough representations, both supervised-trained and from RL s705.
Readout bars are three-fit-seed medians. The RL policy itself is a single seed.

The existing 65,536/16,384/16,384 observation splits, source policy and training
protocol are unchanged: separate dungeon/action seeds, up to 150 epochs,
validation-selected epochs and learning rates, no test-based selection.
Training target sets differ from the original benchmark, so compare architectures
within these new figures rather than interpreting differences from the earlier
figure as an architectural change.

`run.py` freezes the benchmark source and executes the fits, then automatically
calls `render.py` after each complete stage. Figures and source JSONs:

- `out/inventory_encoder_supervised_concrete.png`
- `out/inventory_encoder_probes_concrete.png`

Both are exported to `/puffertank/docker/nethack_article` including web variants.
The earlier figures are preserved under their original names.

Suggested caption: “Linear readouts of three target features from supervised-
trained inventory encoders on held-out games. Bars show three-seed medians;
count and enchantment use R², while wielding a bow uses ROC-AUC. Arrow quantities
follow the encoder's per-stack cap of 30; only known armour enchantments are
scored.” The separate probe figure should be captioned as a post-training
readout comparison, with encoder weights frozen.
