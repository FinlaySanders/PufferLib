# Real-game armour upgrade test

Paired real-object interventions; frozen policies, persistent recurrent memory, 128 subsequent decisions. All pairs match at intervention. Player healthy, worn armour known noncursed, no hostile within eight tiles initially. Later gameplay is unrestricted.

| Policy | Eligible pairs | Upgrade equipped | Downgrade equipped | Decisions until upgrade equipped |
|---|---:|---:|---:|---|
| additive | 6 | 4/6 | 1/6 | 4, 47, 45, 10 |
| replacement | 5 | 2/5 | 1/5 | 89, 1 |

Eight search seeds per policy, up to 8,000 decisions each. Seeds with no eligible opportunity are excluded from these denominators. Policies encounter different states, so these rates are not a controlled comparison of discovery encoders.

The intervention changes carried armour to the same type/erosion as the worn piece, fully known and uncursed, with enchantment +3 or -3 relative to the worn piece. Actual equipped state is tracked by object ID. These are selected diagnostic trials, not natural equip rates or a score cert.

Key counterexample: additive seed 1701 starts with P(WEAR) about 1e-10, then equips the upgrade after four decisions; AC changes from 4 to 1. It does not equip the matched downgrade during follow-up. This invalidates using tiny immediate WEAR probability alone as evidence of a coordination failure.

Other opportunities can remain unused in this window. Later threats arise naturally, and the intervention does not establish that wearing was the optimal action throughout. No claim of perfect armour management follows. All production sources, frozen engine library and model weights remain unchanged.
