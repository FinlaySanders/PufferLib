#!/bin/bash
# Core-type tuning test: PGO builds of the landed engine with -mtune=gracemont (E-core) and -mtune=alderlake (P-core) vs the default tune;
# rotation-16 harness on an E-core (cpu 16) and a P-core (cpu 2), 2 reps each, interleaved.
N=/puffertank/experiments/nethack-engine-lines-20261014; X=/puffertank/experiments/nethack-scheduler-20261012; L=$N/tune.log; echo "tune start $(date -u +%T)" > $L
for v in gm:gracemont adl:alderlake; do n=${v%%:*}; tune=${v##*:}
  rm -rf $N/engines/fastnle_ade_$n; mkdir -p $N/engines/fastnle_ade_$n; cp -r $N/engines/fastnle_ade/source $N/engines/fastnle_ade_$n/source
  (cd $N && python3 build_pgo.py fastnle_ade_$n -mtune=$tune > engines/fastnle_ade_$n.build.out 2>&1); echo "$n build: $(tail -1 $N/engines/fastnle_ade_$n.build.out)" >> $L
done
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
for rep in 1 2; do for cpu in 16 2; do for e in fastnle_ade fastnle_ade_gm fastnle_ade_adl; do
  out=$N/tune_${e}_cpu${cpu}_$rep.log
  env LD_LIBRARY_PATH=$N/engines/$e/build SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c $cpu $X/replay_sched6 128 1 4096 16384 $ACT > $out 2>&1
  echo "TUNE cpu=$cpu $e rep$rep $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $out | tr '\n' ' ') $(date -u +%T)" >> $L
done; done; done
echo "TUNE_DONE $(date -u +%T)" >> $L
