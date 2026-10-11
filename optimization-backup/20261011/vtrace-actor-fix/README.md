# V-trace actor term: double importance correction — 2026-10-11

## Finding
`puff_advantage` (src/algo.cu, commit 3719caaa) emits one quantity, the critic residual
A_v = ρ_t δ_t + γλ c_t (1-d) A_v(t+1), and the trainer uses it as both the return (V + A_v)
and the policy-gradient advantage. With `vtrace = 1` the importance buffer is
exp(new_logp − old_logp) from the same minibatch forward, i.e. the PPO ratio. At equal
clips the residual factorises as A_v = min(ratio, ρ̄) × A_pg where
A_pg = δ_t + γλ(1-d) A_v(t+1) is the IMPALA actor advantage. The PPO surrogate multiplies
by the ratio again, so the actor's effective weight is ratio × min(ratio, ρ̄) instead of
ratio. IMPALA applies ρ_s once; PPO's ratio replaces it. Net: with ρ̄ = 1 every action the
current policy made less likely has its update shrunk by its ratio, uncapped by the PPO clip
on the positive-advantage side (clip only zeroes the gradient below 1-ε for negative
advantages). The critic target is correct and unchanged by this.

Precedent: Sample Factory's V-trace + PPO does the same. `vtrace` defaults to 0 in
default.ini and in ocean/nethack configs, so no current run is affected.

## Fix (vtrace_actor_fix.patch, applies with `patch -p1` at the repo root)
Two accumulators in the kernel: the ρ/c-weighted residual feeds `returns` as before; the
actor advantage drops only the current-step ρ and c and keeps everything from t+1 onward
(PPO's ratio corrects the current action and nothing else). `importance == NULL` (vtrace=0)
takes the plain GAE branch. Behaviour changes: (1) vtrace=0: bit-identical; (2) vtrace=1:
returns unchanged, advantages lose the min(ratio, clip) factor; (3) degenerate vtrace=0
with a clip < 1 used to scale by the clip, now ignores the clips.

## Check (test_vtrace_kernel.cu; nvcc -O2 -std=c++17 -arch=native, trainer flags, no fast-math)
B=512 rows × T=64, γ 0.995, λ 0.90, values 2·N(0,1), rewards U(-1,1), dones 5%,
ratios exp(0.3·N(0,1)). Double-precision reference of the paper recursion. Both bf16 (shipped)
and float builds: RESULT PASS, 0 failures (logs test_vtrace_bf16.log, test_vtrace_float.log).

| check | bf16 | float |
|---|---|---|
| vtrace=0: old vs new advantages, returns | 0 differing bytes | 0 differing bytes |
| returns vs V-trace target (old and new, 4 clip settings) | max_rel 3.9e-3 (bf16 rounding) | max_rel ≤ 1.1e-4 |
| old advantages = critic residual A_v | PASS | PASS |
| new advantages = actor A_pg | PASS | PASS |
| old advantages = min(ratio, ρ̄) × A_pg (equal clips) | PASS | PASS |
| shipped/actor factor, ρ̄=c̄=1 | mean 0.900, min 0.319, 48.6% of steps < 0.99 | mean 0.900, min 0.318, 48.5% |

The factor statistics depend on the synthetic ratio spread; real PPO ratios within one batch
are tighter, so the mean effect in training is smaller than 0.90, but the directional bias
(damping recovery of good actions the policy drifted away from) is structural.

## Status
Handoff only: src/algo.cu is trainer infrastructure and was not edited. Raised with the
maintainer by the user. Before anyone turns `vtrace = 1` on with this fix, a paired-seed
learning A/B against the shipped kernel is needed; existing V-trace users are implicitly
tuned to the double factor.

Files: vtrace_actor_fix.patch (73 lines), algo_patched.cu (full patched copy), test_vtrace_kernel.cu,
test_vtrace_{bf16,float}.log.
