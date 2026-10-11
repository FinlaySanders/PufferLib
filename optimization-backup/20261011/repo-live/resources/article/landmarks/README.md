# Exact landmark visitation

Eight overnight depth-trained 2B policies (seeds 801–808), fork vec evaluation,
evaluation seed 7. Each run completes 14,000 games; discard the first 4,000 and
keep the next 10,000. Pool individual episodes, including for per-role rates.

The isolated instrumentation calls NetHack's `Is_medusa_level(&u.uz)` and
`Is_stronghold(&u.uz)` immediately after `goto_level` assigns the destination.
Flags persist for that episode and are zeroed by the next context allocation.
Reaching means entering the level, not killing Medusa or clearing the Castle.
No flags are exposed to the policy and no actions or RNG calls are added.

Episode columns 0–10 retain the existing logger format. Columns 11 and 12 are
Medusa/Castle visit flags; 13 and 14 contain their actual assigned depths.
An original-versus-instrumented deterministic 16-agent evaluation matched all
11 original fields for all 131 completed episodes (11 Medusa, 3 Castle visits).

`prepare.py` builds a separate source checkout and engine on the drone.
`run.py` gates the eight evaluations on that parity check. `refresh.py` requires
all final result artifacts, imports raw logs and patches, checks counts, and
renders `landmark_reach_by_role.png`. Run it from any directory with SSH access
to `drone`. No depth threshold is used as a substitute for landmark visitation.
