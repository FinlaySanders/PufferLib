#!/bin/bash
# One live 1B seed (3001, the seed that completed cleanly on tile_signed_pgo in 81 min) under gdb on the LANDED engine (fast-nle e038efa41 = A+D+E),
# champion config and stack exactly as champion10 run10_fixed.sh / rerun_seed.sh. Waits for the PGO build and the quick gates first.
N=/puffertank/experiments/nethack-engine-lines-20261014; C=/puffertank/experiments/nethack-compact-state-20261008; OUT=/puffertank/docker/champion10_20261011/ade
T=/puffertank/experiments/nethack-engine-scaling-20261010/trainer_cohort/source; BIN=/puffertank/experiments/nethack-24h-20261009/binaries/cohort_d8
L=$OUT/RESULTS_ADE.txt; echo "ADE run prepared $(date -u +%T)" > $L
while ! grep -q 'PGO READY\|Error\|AssertionError' $N/engines/fastnle_ade.build.out 2>/dev/null; do sleep 5; done
grep -q 'PGO READY' $N/engines/fastnle_ade.build.out || { echo "ENGINE BUILD FAILED" >> $L; exit 1; }
ln -sfn $N/engines/fastnle_ade $C/engines/lines_fastnle_ade
(cd $C && timeout 900 python3 check.py --quick lines_fastnle_ade > $OUT/gates_quick.log 2>&1; echo "quick gates rc=$? $(grep -c PASS $OUT/gates_quick.log) passes $(date -u +%T)" >> $L)
grep -q 'rc=0 5 passes' $L || { echo "GATES FAILED — not launching" >> $L; exit 1; }
ENG=$N/engines/fastnle_ade/build
eval "$(grep '^export' /puffertank/docker/champion10_20261011/run10.sh)"; export LD_LIBRARY_PATH=$ENG
cp $T/config/nethack.ini $T/config/default.ini $OUT/; sha256sum $BIN $ENG/libnethack.so > $OUT/PROVENANCE.txt; (cd /puffertank/optimization-backup-20261008/fast-nle && git log --oneline -1) >> $OUT/PROVENANCE.txt
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 5; done
S=3001; NAME=s3001_ade; mkdir -p $OUT/$NAME; t0=$(date +%s); cd $T
echo "SEED $S launched $(date -u +%T)" >> $L
PUF_PERF_LOADED_PROOF=$OUT/$NAME/loaded.bin gdb -batch -q -ex 'set pagination off' -ex 'set print thread-events off' -ex 'set confirm off' \
  -ex "run train --headless --base.seed=$S --train.total_timesteps=1000000000 --base.run_id=champ_ade_$NAME --base.checkpoint_dir=$OUT/$NAME/checkpoints --base.log_dir=$OUT/$NAME/logs > $OUT/$NAME/run.log 2>&1" \
  -ex 'echo \n=== CRASH ===\n' -ex 'p $_siginfo._sifields._sigfault.si_addr' -ex 'bt 40' -ex 'info registers' -ex 'x/12i $pc-24' -ex 'thread apply all bt 12' --args $BIN train > $OUT/$NAME/gdb.log 2>&1
sig=$(grep -o 'received signal [A-Z]*' $OUT/$NAME/gdb.log | head -1); ex=$(grep -o 'exited normally\|exited with code [0-9]*' $OUT/$NAME/gdb.log | head -1); st="${sig:-${ex:-unknown}}"
echo "SEED $S ($NAME) status=\"$st\" wall=$(( ($(date +%s)-t0)/60 ))min epochs=$(grep -c BENCH_CLOCK $OUT/$NAME/run.log) last_score=$(grep -o 'score *[0-9.]*' $OUT/$NAME/run.log | tail -1) $(date -u +%T)" | tee -a $L
echo "ADE_DONE $(date -u +%T)" >> $L
