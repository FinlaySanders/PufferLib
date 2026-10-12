#!/bin/bash
# Rerun of run10.sh on the signed-tile-accessor engine (tile_signed_pgo = mt7_pgo + nh_tile_at(int,int)), every seed under gdb so any further
# segfault leaves a backtrace in s<seed>/gdb.log. Same binary, config and environment as run10.sh. Results -> RESULTS_FIXED.txt.
OUT=/puffertank/docker/champion10_20261011/fixed; mkdir -p $OUT
T=/puffertank/experiments/nethack-engine-scaling-20261010/trainer_cohort/source; BIN=/puffertank/experiments/nethack-24h-20261009/binaries/cohort_d8
ENG=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build
eval "$(grep '^export' /puffertank/docker/champion10_20261011/run10.sh)"; export LD_LIBRARY_PATH=$ENG
cp $T/config/nethack.ini $T/config/default.ini $OUT/; sha256sum $BIN $ENG/libnethack.so > $OUT/PROVENANCE.txt
cd $T
for S in 3001 3002 3003 3004 3005 3006 3007 3008 3009 3010; do
  while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 5; done
  mkdir -p $OUT/s$S; t0=$(date +%s)
  PUF_PERF_LOADED_PROOF=$OUT/s$S/loaded.bin gdb -batch -q -ex 'set pagination off' -ex 'set print thread-events off' -ex 'set confirm off' \
    -ex "run train --headless --base.seed=$S --train.total_timesteps=1000000000 --base.run_id=champ10f_s$S --base.checkpoint_dir=$OUT/s$S/checkpoints --base.log_dir=$OUT/s$S/logs > $OUT/s$S/run.log 2>&1" \
    -ex 'echo \n=== CRASH ===\n' -ex 'p $_siginfo._sifields._sigfault.si_addr' -ex 'bt 40' -ex 'info registers' -ex 'x/12i $pc-24' -ex 'thread apply all bt 12' --args $BIN train > $OUT/s$S/gdb.log 2>&1
  sig=$(grep -o 'received signal [A-Z]*' $OUT/s$S/gdb.log | head -1); ex=$(grep -o 'exited normally\|exited with code [0-9]*' $OUT/s$S/gdb.log | head -1); st="${sig:-${ex:-unknown}}"
  echo "SEED $S status=\"$st\" wall=$(( ($(date +%s)-t0)/60 ))min epochs=$(grep -c BENCH_CLOCK $OUT/s$S/run.log) last_score=$(grep -o 'score *[0-9.]*' $OUT/s$S/run.log | tail -1) $(date -u +%T)" | tee -a $OUT/RESULTS_FIXED.txt
done
echo "RUN10_FIXED_DONE $(date -u +%FT%TZ)" | tee -a $OUT/RESULTS_FIXED.txt
