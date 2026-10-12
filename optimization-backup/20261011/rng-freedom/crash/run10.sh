#!/bin/bash
# 10 seeds x 1B steps of the champion config (config/nethack.ini, identical to repo HEAD) on the experiment trainer stack (cohort_d8 + mt7_pgo),
# sequential on the single GPU. Outputs on the host disk. Started 2026-10-11T22:26:54Z.
OUT=/puffertank/docker/champion10_20261011; T=/puffertank/experiments/nethack-engine-scaling-20261010/trainer_cohort/source; BIN=/puffertank/experiments/nethack-24h-20261009/binaries/cohort_d8
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat PUF_POOL_WORKERS=24 PUF_INFER_PRIORITY=1 LD_LIBRARY_PATH=/puffertank/experiments/nethack-compact-state-20261008/engines/mt7_pgo/build PUF_OUTPLACE=1 PUF_OUTPLACE_RANK=1 PUF_SCAN_ROW=3 PUF_SCAN_TILE=4 NH_EMBED_REDUCE=7 NH_IDENTITY_WARP=1 NH_FUSED_BR=1 NH_PASS_FAST=3 NH_SFEAT_FAST=1 NH_ENTITY_FUSED=15 NH_ENTITY_TRAIN_FUSED=15 PUF_CUDA_WAIT=block PUF_FINISH_SLEEP=1 NH_GRAD_PIPELINE=3 CUDA_DEVICE_MAX_CONNECTIONS=32
cp $T/config/nethack.ini $T/config/default.ini $OUT/; sha256sum $BIN /puffertank/experiments/nethack-compact-state-20261008/engines/mt7_pgo/build/libnethack.so > $OUT/PROVENANCE.txt
cd $T
for S in 3001 3002 3003 3004 3005 3006 3007 3008 3009 3010; do
  while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 5; done
  mkdir -p $OUT/s$S; t0=$(date +%s)
  PUF_PERF_LOADED_PROOF=$OUT/s$S/loaded.bin $BIN train --headless --base.seed=$S --train.total_timesteps=1000000000 --base.run_id=champ10_s$S --base.checkpoint_dir=$OUT/s$S/checkpoints --base.log_dir=$OUT/s$S/logs > $OUT/s$S/run.log 2>&1
  rc=$?; echo "SEED $S rc=$rc wall=$(( ($(date +%s)-t0)/60 ))min epochs=$(grep -c BENCH_CLOCK $OUT/s$S/run.log) last_score=$(grep -o 'score *[0-9.]*' $OUT/s$S/run.log | tail -1) $(date -u +%T)" | tee -a $OUT/RESULTS.txt
done
echo "RUN10_DONE $(date -u +%FT%TZ)" | tee -a $OUT/RESULTS.txt
