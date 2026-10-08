#!/bin/bash
set -euo pipefail
cd /puffertank/experiments/nethack-train-loop-20260918/source
NVCC_EXTRA='-DPUF_ENV_POOL -DPUF_PERF_LOAD -DPUF_HEAD_SAMPLER -DPUF_MUON_BATCH_NORM -DPUF_MINGRU_NOCOPY -DPUF_SKIP_UNUSED_LOGPS -DPUF_MUON_OUTPLACE -DPUF_PPO_ZERO -DPUF_BYTE_OBS -DPUF_REUSE_ROLLOUT -lcublasLt' ./build.sh nethack puffer_memory_audit > '/puffertank/experiments/nethack-train-loop-20260918/build-memory_audit.log' 2>&1
NVCC_EXTRA='-DPUF_ENV_POOL -DPUF_PERF_LOAD -DPUF_HEAD_SAMPLER -DPUF_MUON_BATCH_NORM -DPUF_MINGRU_NOCOPY -DPUF_SKIP_UNUSED_LOGPS -DPUF_MUON_OUTPLACE -DPUF_PPO_ZERO -DPUF_BYTE_OBS -DPUF_REUSE_ROLLOUT -lcublasLt -DPUF_DW_SERIAL' ./build.sh nethack puffer_dw_serial > '/puffertank/experiments/nethack-train-loop-20260918/build-dw_serial.log' 2>&1
NVCC_EXTRA='-DPUF_ENV_POOL -DPUF_PERF_LOAD -DPUF_HEAD_SAMPLER -DPUF_MUON_BATCH_NORM -DPUF_MINGRU_NOCOPY -DPUF_SKIP_UNUSED_LOGPS -DPUF_MUON_OUTPLACE -DPUF_PPO_ZERO -DPUF_BYTE_OBS -DPUF_REUSE_ROLLOUT -lcublasLt -DPUF_DW_DEFER' ./build.sh nethack puffer_dw_defer > '/puffertank/experiments/nethack-train-loop-20260918/build-dw_defer.log' 2>&1
python '/puffertank/experiments/nethack-train-loop-20260918/bench_extra.py' memory-repeat1 '/puffertank/experiments/nethack-train-loop-20260918/source/puffer_memory_audit' 
python '/puffertank/experiments/nethack-train-loop-20260918/bench_extra.py' baseline-final1 '/puffertank/experiments/nethack-batch-sweep-20260918/source/puffer_batch' 
python '/puffertank/experiments/nethack-train-loop-20260918/bench_extra.py' memory-state '/puffertank/experiments/nethack-train-loop-20260918/source/puffer_memory_audit' --update --env=PUF_STATE_PROOF=/puffertank/experiments/nethack-train-loop-20260918/memory-state
python '/puffertank/experiments/nethack-train-loop-20260918/bench_extra.py' dw-serial '/puffertank/experiments/nethack-train-loop-20260918/source/puffer_dw_serial' --update
python '/puffertank/experiments/nethack-train-loop-20260918/bench_extra.py' dw-defer '/puffertank/experiments/nethack-train-loop-20260918/source/puffer_dw_defer' --update
python '/puffertank/experiments/nethack-train-loop-20260918/bench_extra.py' memory-repeat2 '/puffertank/experiments/nethack-train-loop-20260918/source/puffer_memory_audit' 
