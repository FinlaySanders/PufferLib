# Final PR integration check

Upstream freshly fetched: 6ffa5b10dbbbe4d1e8288367c7d9d3acd3bad4a2. PR HEAD: 3719caaaf945025e4e1e59c6556560d2ba9e3d1c. Upstream is an ancestor of HEAD; no merge conflicts or newer upstream changes. The combined upstream + PR tree is the current branch.

- Executable source lines in src/algo.cu, src/pufferl.cu and tests/profile_kernels.cu are identical to tested commit 1cb95a8a; the subsequent commit changes only standalone comments.
- Existing 15-configuration determinism/performance results therefore cover this implementation. See ../cublas-all-env-perf-20260918/REPORT.md and the prior determinism reports.
- Fresh isolated CPU and GPU Breakout builds from current HEAD both completed training and final evaluation. Every saved checkpoint matches its upstream reference exactly. Commands and hashes: results.json.
- git diff --check upstream/5.0...HEAD passes. Tracked working tree remains clean. No changes committed or pushed by this check.

## Existing profiler failure

The extra check `./build.sh minimal --profile` fails with 22 compilation errors, principally missing NMMO3 constants in the generic profiler. Repeating with pristine upstream versions of all three changed files produces the identical 22 error messages. This failure predates the PR and is not a new regression. Logs: build-profile.log, build-profile-upstream.log. The profiler cannot be runtime-validated through this build until that separate issue is fixed.

Scope: one RTX 4090, tested configurations/toolchain. No claim of exhaustive hardware or multi-GPU coverage.
