# Fairness audit — 2026-09-13

The measurements support a **controlled replay microbenchmark**, not an overall
training-speed claim.

## Controlled

- Eight distinct physical performance cores, the same affinity in every arm.
- The same total environment count, seeds, options, recorded keys and fixed clock.
- In the challenge comparison, all 14 public observation fields are requested in
  each arm, including terminal and inventory arrays. Their hashes agree after
  every key in the validated prefixes. Batched final hashes and turn advances
  agree across the backends. This is stronger than checking only elapsed steps.
- Stock Python and stock C use the same unmodified engine binary. Stock gets
  eight worker processes, avoiding a shared Python GIL across cores. There is no
  per-key interprocess transport added to the baseline.
- The timer covers stepping only; all arms exclude loading, reset, final hashing
  and shutdown. Three measured repetitions follow a discarded first repetition,
  with rotated execution order.
- Both installed libraries contain GCC 13.3.0 compiler identification strings.
  Exact build-flag parity has not been established. Binary hashes are recorded.

## What the comparisons mean

**Stock C versus fast-nle C** is the most direct native-engine comparison. Both
write the same requested observation fields and execute the same keys. It measures
all native implementation differences together, including per-environment library
copies versus shared-engine contexts. It cannot attribute a gain to game logic
alone, and it is not a comparison against every possible stock scheduling strategy.

**Python challenge versus stock C** measures the additional Python binding and
challenge-wrapper work, including observation copies, reward computation and
termination accounting. It is not a language-only overhead measurement: the C arm
does not implement that wrapper's reward and accounting operations.

**Python challenge versus fast-nle C** is their combined pipeline comparison.
The fast arm does NOT run PufferLib's `nethack_pack_obs`, `nethack_reward`, action
masks or policy. Calling its ratio the speedup of our full training interface would
be misleading. No neural-network inference, GPU transfer or learning is measured.

## Generalization limits

All environments within a trial duplicate one short, shallow trajectory. The
three trajectories end with zero score and do not exercise deep gameplay or
reset/death costs. They were selected for observation agreement before timing;
most of the older corpus diverged between the installed builds. Matching this
subset does not establish general trajectory equivalence.

Identical trajectories may affect instruction/data cache behavior differently
from independently playing agents. The large memory reduction is measured, but
we have not profiled cache misses to establish why throughput changes. At a fixed
eight cores, increasing environment count increases working-set pressure; this
is not the same experiment as adding cores along with games.

Small-batch trials are only milliseconds long, and process workers use the maximum
local duration while the threaded arm measures a common barrier interval. Starts
are released through pipes rather than a hardware-synchronized timer. This matters
more for tiny trials than the multi-second large batches. Final hashes are computed
after local timing; a worker that finishes early may perform that check while another
worker is still stepping. These are additional reasons not to overinterpret small
percentage differences or claim a formal uncertainty bound from three repeats.

For the article, state the workload, environment count and CPU count alongside any
ratio. A representative overall training/interface claim needs an end-to-end
comparison with the agent and its wrappers included, rather than relabeling these
engine-call measurements.
