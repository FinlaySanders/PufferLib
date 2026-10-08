from pathlib import Path
import json,hashlib,re,statistics,subprocess
r=Path(__file__).parent;rows={p.parent.name:json.loads(p.read_text()) for p in (r/'training').glob('*/result.json')}
for n in ['baseline-a','baseline-b','workspace','split','both','strict','strict-repeat','lt','workspace-d']:
 x=rows[n];assert x['rc']==0 and len(x['epochs'])==32
base=statistics.mean(rows[n]['timed_seconds'] for n in ['baseline-a','baseline-b']);strict=statistics.mean(rows[n]['timed_seconds'] for n in ['strict','strict-repeat']);steps=rows['strict']['timed_steps']
prof=json.loads((r/'profile-strict/summary.json').read_text())
checks={}
for name in ['strict_check','both_check2']:
 text=(r/(name+'.log')).read_text();errs=[float(x) for x in re.findall(r'GEMMCHECK .*? rel=([^ ]+)',text)];assert len(errs)==7 and max(errs)<.003;assert re.findall(r'GEMMROUND violations=(\d+)',text)==['0']*7;assert len(re.findall('PERF_EPOCH epoch=',text))==2;checks[name]=dict(shapes=7,max_relative_error=max(errs))
text=(r/'muon-check.log').read_text();assert len(re.findall('MUONCHECK',text))==24
old=Path('/puffertank/experiments/nethack-perf-20260917');same=subprocess.check_output(['git','-C','/puffertank/pufferlib','diff','--binary','HEAD'])==(old/'puffer-working.patch').read_bytes();assert same
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ckpt='/puffertank/pufferlib/resources/nethack/fixwt4b_s705.bin';ckhash=sha(ckpt)
for name in rows:assert sha(r/'training'/name/'loaded.bin')==ckhash
log=(r/'profile-strict/run.log').read_text(errors='replace');assert [int(x) for x in re.findall(r'PERF_EPOCH epoch=(\d+)',log)]==list(range(64));assert sha(r/'profile-strict/loaded.bin')==ckhash
summary=dict(baseline_seconds=base,strict_seconds=strict,time_reduction_percent=100*(1-strict/base),throughput_gain_percent=100*(base/strict-1),baseline_sps=steps/base,strict_sps=steps/strict,baseline_drift_percent=100*(rows['baseline-b']['timed_seconds']/rows['baseline-a']['timed_seconds']-1),strict_repeat_drift_percent=100*(rows['strict-repeat']['timed_seconds']/rows['strict']['timed_seconds']-1),checks=checks,production_diff_unchanged=same,checkpoint_sha256=ckhash,profile=prof)
(r/'RESULTS.json').write_text(json.dumps(summary,indent=2))
lines=['# NetHack training GEMM optimisation','',
'## Retained candidate','',
'**Restore the cuBLAS handle’s private workspace after setting its stream, and disallow reduced-precision reductions.** No architecture, optimiser formula, reward or hyperparameter changes. The patch is prepared but not applied to production.','',
f'On loaded 4B score-policy training, measured time falls from **{base:.2f} s to {strict:.2f} s**: **{summary["time_reduction_percent"]:.1f}% less time / {summary["throughput_gain_percent"]:.1f}% higher throughput**. Measured throughput is {steps/base:,.0f} → {steps/strict:,.0f} steps/s. This is relative to the already optimised engine/work-stealing/head-sampler baseline, not the original pre-campaign trainer.','',
'## End-to-end comparisons','',
'Each arm runs 32 updates / 8,388,608 training steps from the same fixed 4B s705 checkpoint, with a fresh optimiser. Measure updates 16–30 (3,932,160 steps); exclude warmup and the last update, which does not prefetch another rollout. 512 environments, 32 CPU workers, normal async configuration. No profiler during these timings.','',
'| Candidate | Measured seconds | Status |','|---|---:|---|']
status={'baseline-a':'Baseline before','baseline-b':'Baseline after','workspace':'Fast, but excessive actual-gradient error','split':'FP32 partial split-K; no additional benefit over simpler fix','both':'Combined; no additional benefit','strict':'Retained candidate','strict-repeat':'Retained candidate repeat','lt':'Large-operation Muon tuning; rejected on whole-training speed','workspace-d':'Workspace-only later control'}
for name in ['baseline-a','workspace','split','both','baseline-b','strict','lt','workspace-d','strict-repeat']:lines.append(f'| {name} | {rows[name]["timed_seconds"]:.3f} | {status[name]} |')
lines+=['',f'Baseline drift: {summary["baseline_drift_percent"]:.2f}%. Strict-candidate repeat drift: {summary["strict_repeat_drift_percent"]:.2f}%. The loaded policy produces mature games: mean game age during the timed blocks is roughly 22,000–24,000 turns. This is a performance experiment, not a new score certificate or a guarantee of unchanged long-run learning.','',
'## Root cause','',
'The trainer allocates a 32 MiB workspace for each cuBLAS handle, but `cublasSetStream` unconditionally resets the handle to the default workspace pool. Every dense GEMM calls it. Restoring the already allocated private workspace after that call allows cuBLAS to use faster algorithms in the large captured training graph. Main and side-stream handles retain separate workspaces; inference workers use thread-local handles.',
'',
'Official reference: [cuBLAS cublasSetWorkspace](https://docs.nvidia.com/cuda/cublas/index.html#cublassetworkspace).','',
'## Numerical validation','',
'- Explicit split-K: 9 representative shapes × 6 configurations, checked against an FP32 pedantic GEMM reference. Eight coordinates per shape additionally checked using CPU FP64 accumulation. Partial results and their deterministic final reduction use FP32; final output is BF16.',
'- Workspace-only passed random tests but failed the actual-training gradient gate: relative error 0.476% for one inventory gradient. It is not the retained candidate.',
'- Strict workspace and explicit FP32 split-K were checked on actual s705 training inputs for all seven distinct expensive gradient shapes. Both passed. Strict workspace relative errors range from about 0.12% to 0.19%, consistent with BF16 output rounding.',
'- The final gate requires relative L2 error below 0.3% and every element within `0.004*abs(reference) + 0.001*reference_RMS` of the FP32 reference. The original max-error/RMS test was inappropriate for sparse, heavy-tailed gradients; it was replaced with this BF16 rounding-aware elementwise bound while tightening the L2 requirement. The failing workspace-only configuration remains rejected.',
'- All full timing arms finished, loaded the checkpoint byte-for-byte, wrote final checkpoints, and passed finite-log checks. Graph-enabled timing uses normal training; the reference checker uses graph-disabled training (`--base.cudagraphs=-1`). In this tree zero still enables graphs, which caused an initial checker failure; that failed log is preserved.',
'- Different cuBLAS algorithms/reduction orders can change rounding. These changes are **not bitwise-equivalent training**. No long training/score-equivalence claim is made.','',
'## Muon experiments','',
'- Searched up to 64 cuBLASLt heuristic algorithms for each of 61 distinct Muon shapes, keeping BF16 tensors and FP32 computation.',
'- The initially selected small-matrix algorithms failed the complete five-step Newton–Schulz check on a structured input (29.1% relative output difference). Rejected; the tolerance was not relaxed.',
'- Restricting the candidate to the large 3072×1024 output GEMM passed 24 complete five-step tests (8 shapes × dense/sparse/structured inputs). The selected GEMM was about 8.5% faster in isolation, but its whole-training arm was slower than workspace-only controls. Rejected.',
'- Parameter batching was not implemented: the algorithm-selection experiment did not yield a retained end-to-end gain, and batching would require a separate optimiser-workspace refactor and numerical validation.','',
'## Profile after the retained fix','',
f'A fresh warmed 10-second CUDA/NVTX trace reports a mean complete PPO graph span of **{prof["mean_complete_ppo_graph_seconds"]:.3f} s**, versus **2.398 s** in the earlier detailed profile. The new capture contains {prof["complete_ppo_graph_count"]} complete PPO graphs. GPU kernel-active union is {prof["kernel_union_seconds"]["all"]:.3f}/10 seconds; this is activity, not SM occupancy.',
f'Gaps between PPO graphs (ms): {", ".join(f"{x:.1f}" for x in prof["ppo_gap_ms"])}. See `profile-strict/summary.json` for inference overlap and kernel breakdown. Profile timings are not used for the throughput claim.','',
'PPO no longer runs back-to-back: rollout completion now consumes a visible tail between updates. This identifies collection (simulation plus inference) as a new co-limiter; the CUDA-only trace does not separate CPU simulation from inference scheduling well enough to assign the entire tail to the engine.', '',
'## Artifacts','',
'- `workspace-strict.patch`: minimal proposed patch, `git apply --check` passed; not applied.',
'- `training/*/result.json`: commands, per-update timing, game age and completion status.',
'- `strict_check.log`, `both_check2.log`: actual-gradient reference checks.',
'- `split.csv`, `workspace.csv`, `lt-bench.log`, `muon-check.log`: microbenchmarks and numerical tests.',
'- `muon-check-rejected.log`, `lt-config-rejected.bin`, `workspace_check-numeric-failure.log`: rejected candidates and evidence.',
'- `profile-strict/timeline.nsys-rep`, `timeline.sqlite`, `summary.json`: updated profile.',
'- `source/`: isolated builds; production git diff unchanged.',
'- `RESULTS.json`, `MANIFEST.json`: summary and checksums.']
(r/'REPORT.md').write_text('\n'.join(lines)+'\n')
files=[r/'REPORT.md',r/'RESULTS.json',r/'workspace-strict.patch',r/'source/puffer_strict',r/'source/src/algo.cu',r/'source/src/actual_check.cuh',r/'strict_check.log',r/'both_check2.log',r/'muon-check.log',r/'split.csv',r/'workspace.csv',r/'lt-bench.log',r/'profile-strict/timeline.nsys-rep']
(r/'MANIFEST.json').write_text(json.dumps({str(p.relative_to(r)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in files},indent=2));print(json.dumps({k:v for k,v in summary.items() if k!='profile'},indent=2))
