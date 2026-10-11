# Compact floor metadata: no substantial throughput gain

The complete prototype is parked. It did not recover the large locality benefit
seen when warming whole object records. This does not rule out a broader compact
state design; it rejects this narrow cached-view implementation as a substantial
speedup. Production files and the retained engine are unchanged.

## What was tried

The first version adds a packed four-byte type/class/coordinate word to the
existing floor index and consumes it in movement filtering. The second also passes
cached type/class into searches_for_item, avoiding an immediate re-read there.
Other callers retain their original interface. Full objects remain authoritative;
53 type/class stores invalidate the derived view when the object is on the floor.
Extra allocation is 8 KiB/game (64 MiB at 8192). Details: AUDIT.md, type_stores.json,
candidate.patch, utility.patch and complete.patch. Rare fields and side-effecting
operations still use the full object. The inherited utility-build cleanup guard
is repaired only in the isolated copies.

## CPU replay results

Both arms use GCC Release + LTO and identical settings. The reference source is
the latest retained source, built without PGO. These numbers are NOT comparisons
to stock NLE/upstream, nor against the retained PGO binary, nor training gains.
24 pinned workers, four submitters, unchanged mature recorded score-policy actions,
8192 warmup decisions/game, ordinary one-action stepping during measurements.

First version:

| Envs | Control SPS | Candidate SPS | Change |
| ---: | ---: | ---: | ---: |
| 512 | 264,224 | 263,219 | -0.38% |
| 2,048 | 204,555 | 203,644 | -0.45% |

Complete version:

| Envs | Control SPS | Candidate SPS | Change |
| ---: | ---: | ---: | ---: |
| 512 | 262,586 | 263,578 | +0.38% |
| 2,048 | 203,813 | 205,000 | +0.58% |
| 8,192 | 202,614 | 203,127 | +0.25% |

512/2048 use A-B-B-A process order with two timed snapshot trials per process.
8192 uses A-B-A with two trials per process. Warmup is separate for each engine;
no saved stacks are transferred between builds. Snapshot restoration includes
private files, FD offsets and quiesced workers. Exact commands, library and harness
hashes are under ../fast_loop_20261009/runs/floor_meta*/command.json.

Windows differ by population in the candidate screen: 2048 decisions/game at 512,
512 at 2048, 256 at 8192. Compare each candidate with its own matched control; do not
use those absolute SPS values to infer scaling across populations. Raw repeats and
ranges are in screen.json, utility_screen.json and summary.json. No statistical
significance or training speedup is claimed from these small timing differences.

## Matched scaling window

The following control-only runs all measure decisions 8192 through 8447, allowing
the same mature workload to be compared at each population. CPU us includes worker
and submitter CPU time; it is not an isolated engine-function latency.

| Envs | Control SPS | CPU us/decision | Peak child RSS MiB |
| ---: | ---: | ---: | ---: |
| 512 | 261,115 | 107.12 | 297 |
| 2,048 | 202,814 | 137.96 | 1113 |
| 8,192 | 202,614 | 137.96 | 4413 |

The 8192 workload contains 16 independent engine copies of each of 512 recorded
game streams. This tests population/working-set scaling, not 8192 unique policies
or independently sampled game histories. All measured native windows had
0 major page faults. Resident memory fits comfortably on this host.
There are no hardware cache-miss/TLB counters available, so no exact cache-level
attribution is asserted. Smaller-population matched measurements are descriptive
two-trial samples, not a new full scaling study.

## Correctness and decision

- Both versions pass all five existing suites: 34 goldens, 26 fuzz trajectories,
  status-disabled, interleaved and shuffled execution. Immutable expectations.
- The focused independent-list test matches 974,402 queries/969,602 returned items,
  including automatic type/class invalidation, changing bounds, signed extrema,
  list mutation and 5000-item overflow. The reference and first prototype pass
  Valgrind with zero errors and no leaks; the second preserves that index code.
- Each version matches 262,144 immutable per-decision hashes for observations,
  rewards, terminals and masks. These are the same workload window for each build.
- All 42 native timing windows match their control end state,
  world-turn count and mean age at the same population/window.
- 8 protected production files,1,290 retained source files, retained library and
  the original reference hash are unchanged; integrity_after.json.

The small net change does not justify promoting this duplicated representation.
No fresh PGO build, full-corpus gate or training-pipeline benchmark was performed
for these parked candidates. A future serious winner would still need those gates,
including fresh-process timing to exclude snapshot COW effects.
