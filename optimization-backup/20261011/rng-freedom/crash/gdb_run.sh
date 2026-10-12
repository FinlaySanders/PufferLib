#!/bin/bash
# usage: gdb_run.sh <tag> <seed> <engine_build_dir>   — one champion 1B seed under gdb, backtrace on crash
TAG=$1; S=$2; ENG=$3
OUT=/puffertank/docker/champion10_20261011/crash/$TAG; mkdir -p $OUT
T=/puffertank/experiments/nethack-engine-scaling-20261010/trainer_cohort/source; BIN=/puffertank/experiments/nethack-24h-20261009/binaries/cohort_d8
eval "$(grep '^export' /puffertank/docker/champion10_20261011/run10.sh)"
export LD_LIBRARY_PATH=$ENG PUF_PERF_LOADED_PROOF=$OUT/loaded.bin
sha256sum $ENG/libnethack.so > $OUT/engine.sha
cd $T; t0=$(date +%s)
gdb -batch -q -ex 'set pagination off' -ex 'set print thread-events off' -ex 'set confirm off' \
  -ex "run train --headless --base.seed=$S --train.total_timesteps=1000000000 --base.run_id=crash_${TAG} --base.checkpoint_dir=$OUT/checkpoints --base.log_dir=$OUT/logs > $OUT/run.log 2>&1" \
  -ex 'echo \n=== CRASH ===\n' -ex 'info signal SIGSEGV' -ex 'p $_siginfo._sifields._sigfault.si_addr' -ex 'bt 40' -ex 'info registers' -ex 'x/12i $pc-24' -ex 'info sharedlibrary' -ex 'echo \n=== ALL THREADS ===\n' -ex 'thread apply all bt 12' \
  --args $BIN train > $OUT/gdb.log 2>&1
echo "GDB_DONE $TAG seed=$S rc=$? wall=$(( ($(date +%s)-t0)/60 ))min epochs=$(grep -c BENCH_CLOCK $OUT/run.log) $(date -u +%T)" | tee -a $OUT/../CRASH_RESULTS.txt
