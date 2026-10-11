---
name: no-hand-edited-hypers
description: Never hand-design reward/hyper configs — validate and promote sweep-discovered trials only
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-07-24T13:27:10.104Z
---

Do not hand-edit reward coefficients or training hypers into new configs
(midpoints, single-knob probes, "targeted attribution" hybrids). The sweep
(tinybox, e.g. project nethack-verbage) owns config discovery; this box
validates its trials (n=4 seeds) and promotes winners into nethack.ini.

**Why:** User 2026-07-24, rejecting a proposed firefly/etc336 interpolation
and a gae_lambda probe: "no we shouldnt try to edit hypers manually like
this." Consistent with the earlier division of labor (rewards = sweep box;
this box polishes the policy/env) — see [[pufferl-off-limits]] for the same
boundary on train infra.

**How to apply:** When an experiment idea reduces to "change coefficient X",
the move is: find sweep trials that already embody the hypothesis (screen by
config shape + score-per-wall-clock, e.g. eternal-cloud-336 / firm-firefly-400
promotions), validate n=4, and feed conclusions back as steering for the
sweep's next center. Budget/total_timesteps rescaling of a validated config is
allowed (it is a schedule, not a hyper — user requested the 250M firefly
stretch themselves).

2026-08-12 SWEEP LOCAL-PATCH GOTCHA: default.ini reverted to upstream on the
cleanup branch — the campaign's sweep pinning (comment out
[sweep.policy.hidden_size] + [sweep.policy.num_layers], cap
[sweep.vec.total_agents] max at 512) is NO LONGER in the tree. Any future
`puffer sweep nethack` MUST re-apply those edits locally first or the sweep
varies arch (VRAM blowups at hidden 1024+) and agent count. Child ini cannot
disable an inherited sweep dim; min==max NaNs the GP (space_normalize 0/0).
