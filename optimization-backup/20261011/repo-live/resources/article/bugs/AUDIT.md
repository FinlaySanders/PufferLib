# RL finds bugs: source audit

Checked 14 September 2026. This is a source audit, not a fresh runtime reproduction on upstream builds. “Fixed” below means that code addressing the identified mechanism is present; “still present” describes a directly verified faulty code path. Matching a single unsafe line is not sufficient to prove that a crash is still reachable.

## Versions

- Challenge NLE: facebookresearch/nle `862a439a84f52abca94d1f744d57061da12c5831`, based on NetHack 3.6.6.
- Maintained NLE: NetHack-LE/nle `2319f2989f0035685017e9ea13c83b2546fe477c`. The seven relevant core-game sites below match the older NLE behavior.
- Latest released NetHack: `NetHack-5.0.0_Released`, announced 2 May 2026. Also checked the current default branch, NetHack-5.0, at `aec687db2c141282d08dee6dfe76c1cdd87ea42a`.
- Neither stock-NLE installation used for our score certificates was modified during this audit.

## Game bugs encountered and patched

| Incident | Our fix | NLE source today | NetHack 5.0 release and current branch |
|---|---|---|---|
| Kill a monster while swallowed above a level-teleport trap: landing changes level and frees the monster before the kill routine finishes using it | `76f699e1c`, defer level change while monster references remain live | Original immediate level-change and subsequent monster access remain | Fixed mechanism: level teleport waits until end of turn; kill routine also preserves a monster reference copy |
| A swallowing shapeshifter changes form and expels the hero onto a level-teleport trap: caller continues using the freed monster | `21e7e0b53`, extend level-change guard to expulsion | Original path remains | Fixed mechanism: same end-of-turn deferral; expels also places its own spoteffects call last |
| A former giant drops boulders while in a pit, kills itself, and the inventory loop follows a freed successor | `30abdf752`, rescan inventory after each drop and stop when monster dies | Loop caches successor without death guard | Fixed: explicit DEADMONSTER guard and comment describing this exact stale-inventory case |
| A thrown boomerang curves outside the map and reads the monster grid out of bounds | `30abdf752`, bounds check before grid access | Missing bounds check | Fixed: isok check before m_at; this was already known upstream when we rediscovered it |
| Altering billed merchandise can hang when the first eligible bill lacks the object: alter_cost never advances past the first one | `2bd59211a`, next_shkp(shkp->nmon, TRUE) | Faulty non-advancing loop remains | Faulty non-advancing loop remains; next_shkp still starts at its argument |
| Pet relocated during dog_move leaves a duplicate/stale grid entry when the move commits using its old coordinates | `e77bbe4c6`, remove pet from its actual occupied cell | Original remove_monster(omx, omy) remains; original bug reproduced in our fork | Same line remains, but relocation paths have changed. Upstream reachability not established by this audit |
| Shop lookup dereferences missing shopkeeper extension data; tended_shop missed guards used elsewhere in our fork | `2bd59211a`, has_eshk guard; earlier next_shkp/shop_keeper guards in `3198c3bf7` / `7b77a35d3` | Unguarded extension access remains, but original stale-object precondition needs independent verification outside our fork | Same caveat: do not claim a confirmed current-upstream crash from the missing guard alone |

The seven rows are incident categories, not seven claims of previously unknown NetHack vulnerabilities. The first two share a level-transition lifetime mechanism. The shopkeeper row groups multiple guarded lookup sites.

## Historical reproduction evidence

Archived experiment notes: `/root/.claude/projects/-puffertank-pufferlib/memory/nethack-engine-bugs.md`, `nethack-crash-hardening.md`, and `nethack-action-expansion-campaign.md`.

- Pet relocation: 12 July, seed 777, about 76M training steps / game turn 3828. Instrumentation recorded old coordinates (51,10), actual coordinates (52,11), new coordinates (52,10), and the duplicate grid pointer. Fixed run passed the former crash point.
- Shopkeeper crash: 2 August, seed 207, reproducible at 66M; backtrace inhishop <- tended_shop <- dosounds. Guarded build survived past 113.8M.
- Billing hang: 2 August, seed 209, reproducible near 161M; backtrace alter_cost <- bill_dummy_object <- costly_alteration <- touchfood <- doeat. The agent was eating billed shop food.
- Boulders: diagnosed 4 August; seed 211 failed near 131M, fixed run passed 164M. Cached inventory successor was freed through flooreffects / monster death / burial.
- Boomerang: diagnosed 9 August, seed 304 near 98M; throw_obj -> throwit -> boomhit -> m_respond. Fixed run passed former crash point.
- Level-teleport cases: July commits and archived traces identify use-after-free in xkilled and newcham/expels. Treat as separate reproductions of one broader lifetime hazard.

These are training-time incidents, not evidence that the agent deliberately learned to trigger crashes for reward.

## NLE boundary and fork-specific fixes

These belong in a separate category from game-logic bugs:

1. **Post-death object access** (`03e0b034d`): our persistent environment accessors walked freed object/monster chains after death in the middle of a command. Nulling the maps fixed the fork's accessor path. This does not establish a bug in normal stock Python stepping or standalone NetHack.
2. **Resume after terminal state** (same commit): stray macro keys resumed a finished coroutine, with a stale return-context record. Stock NLE's low-level C code retains the conditional context update, but its Python binding rejects stepping a done game. Do not present this as a crash reachable through normal challenge reset/step usage.
3. **Coroutine stack capacity** (`30abdf752`): increased the fork stack from 64 KiB to 256 KiB after deep recursion. Stack sizing is an NLE integration concern, not a standalone NetHack bug; this audit did not establish an equivalent current-NLE runtime failure.
4. **Concurrent-environment isolation** (`2a0556e18`): TLS cached across coroutine migration, teardown using the wrong context, shared sysopt lifetime/double frees, and symbol interposition. These arose in our fast-nle multi-environment design; they should not be attributed to single-game upstream NetHack.
5. **Our command interface**: broken ring-finger responses, identify menus dismissed without selection, position-picker prompt loops, casting after a refused command, handless-form and zero-time refusal loops. These were adapter/action-space problems; refusing an invalid action without advancing time is legal NetHack behavior.
6. **Our observation exports/reconstruction**: true-type weight information leak, hallucination item parsing, wrapped identity text, stale peaceful/pile state, polymorph capacity and intrinsic tracking. These were fork/adapter correctness bugs, not bugs in unmodified stock NLE exposing hidden weights.
7. **Our training/evaluation code**: unused action heads entering PPO log-probability/entropy, misleading early parallel-evaluation averages, and instrumentation errors. Useful lessons, but not NetHack engine discoveries.

The moon/night effects are intended game mechanics, not bugs. Suspected but unroot-caused FPEs, crashes and memory-growth incidents in the notebooks are not additional confirmed bug discoveries.

## Article recommendation

Lead with the billing hang: a mundane action (eating shop food) exposed a non-advancing linked-list loop, and that faulty loop remains in current upstream source. Follow with the former-giant/boulder/pit interaction as an example of rare game rules combining into a memory-lifetime failure. Mention that several crashes we rediscovered were already fixed in newer NetHack, but remained in NLE's older engine. Avoid “we found seven new bugs in latest NetHack.”

## Source links

- [Latest NetHack release announcement](https://nethack.org/)
- [Challenge NLE](https://github.com/facebookresearch/nle)
- [NLE billing loop](https://github.com/facebookresearch/nle/blob/862a439a84f52abca94d1f744d57061da12c5831/src/shk.c#L2425)
- [Current NetHack billing loop](https://github.com/NetHack/NetHack/blob/aec687db2c141282d08dee6dfe76c1cdd87ea42a/src/shk.c#L3267)
- [NetHack level-transition fix](https://github.com/NetHack/NetHack/blob/aec687db2c141282d08dee6dfe76c1cdd87ea42a/src/teleport.c#L1429)
- [NetHack boulder guard](https://github.com/NetHack/NetHack/blob/aec687db2c141282d08dee6dfe76c1cdd87ea42a/src/mon.c#L5510)
- [NetHack boomerang bounds guard](https://github.com/NetHack/NetHack/blob/aec687db2c141282d08dee6dfe76c1cdd87ea42a/src/zap.c#L4197)
- [NetHack pet move site](https://github.com/NetHack/NetHack/blob/aec687db2c141282d08dee6dfe76c1cdd87ea42a/src/dogmove.c#L1298)

Exact repository refs and downloaded source SHA256s are in `audit_manifest.json`. Downloaded comparison sources are under `/tmp/nethack-bug-audit`.

## Correction after checking original shop trace

The actual debugger capture is preserved in `shop_hang_trace.txt`. It records a worker stopped in `alter_cost <- bill_dummy_object <- costly_alteration <- touchfood <- doeat`. It does not print the object, shopkeeper structures, bill contents, or preceding gameplay. The transcript proceeds directly from that backtrace to source inspection and patching; the “two shops with active bills” explanation in the memory note is an inferred scenario, not a captured observation.

`bill_dummy_object` creates a new dummy billing object and calls `alter_cost(dummy, -cost)` after attempting to add it to the bill. Thus the searched object at this call site is a bookkeeping copy, not directly the food being eaten. The trace does not establish why that object's lookup failed, whether two bills coexisted, or whether the player escaped a shop. Ordinary robbery clears itemized bill entries via `setpaid` and stores robbery debt separately, so escaping a shop is not a demonstrated route to the hypothetical two-bill state. One eligible shopkeeper with a missing object would also suffice to expose the non-advancing loop.

Article-safe statement: a recorded eating action hung in the billing routine; source inspection found a scan that revisits the same shopkeeper if the object is absent from that bill. The exact preceding gameplay/billing state was not captured. Do not present Alice/Bob or two outstanding bills as the observed reproduction.
