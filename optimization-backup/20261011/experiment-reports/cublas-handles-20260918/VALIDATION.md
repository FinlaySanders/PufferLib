Handle-per-stream cuBLAS refactor

CPU and GPU Breakout: two runs each, 134,217,728 training steps, seed 901.
2048: two runs, 16,777,216 steps, seed 901.
All repeated checkpoints are byte-identical, and match the previous stream-safe workspace fix. All 14 checkpoints contain finite FP32 values; logs contain no nonfinite losses.
Commands and hashes: /tmp/validate-cublas-handles.py and results.json.

NetHack encoder/decoder gradient checks: PASS (nethack-grad.log).
Standalone minimal profiler cannot build: same 22 pre-existing errors on upstream and candidate (old scan/PPO APIs and undefined N3 constants). Direct GEMM call signatures updated; unrelated profiler repairs excluded.
