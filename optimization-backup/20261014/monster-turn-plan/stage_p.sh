#!/bin/bash
# packer slices P2+P4 (headers_p): build harness binaries against the mt2 engine include, 8-game hash (must equal the C2 binary's), rotation A/B x2
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; X=/puffertank/experiments/nethack-scheduler-20261012; R=/puffertank/experiments/nethack-engine-scaling-20261010; N=/puffertank/experiments/nethack-engine-lines-20261014
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions; L=$P/stage_p.log
echo "stage P start $(date -u +%T)" > $L
while ! grep -q NIGHT_QUEUE_DONE $P/night_queue.log; do sleep 20; done; echo "night queue finished $(date -u +%T)" >> $L
cd $P && python3 apply_packer.py >> $L 2>&1 || { echo "APPLY FAILED" >> $L; exit 1; }
COMMON="-I$R/harness_cohort -I$R/harness_cohort/source/src -I$R/harness_cohort/source/ocean/nethack -I$E/source/include -I/puffertank/pufferlib/raylib-5.5_linux_amd64/include -I/usr/local/cuda/include -I/puffertank/pufferlib/vendor/fast-nle/build/_deps/deboost_context-src/include"
cc -O2 -g -pthread -DNVTX_DISABLE -I$P/headers_p $COMMON $X/replay_sched.c -L$E/build -lnethack -lm -ldl -o $P/replay_sched6_P 2> $P/build_p.log; echo "build P rc=$? $(grep -c error $P/build_p.log)" >> $L
cc -O2 -g -pthread -DNVTX_DISABLE -I$N/headers/harness_root $COMMON $X/replay_sched.c -L$E/build -lnethack -lm -ldl -o $P/replay_sched6_C2ref 2> $P/build_c2ref.log; echo "build C2ref rc=$? $(grep -c error $P/build_c2ref.log)" >> $L
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0 LD_LIBRARY_PATH=$E/build NH_MT2=1
h8() { env SCHED_C=1 SCHED_A=8 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $1 8 1 4096 16384 $ACT 2>&1 | grep -oE 'obs=[^ ]+'; }
HP=$(h8 $P/replay_sched6_P); HC=$(h8 $P/replay_sched6_C2ref); echo "8-game hash P=$HP C2ref=$HC $(date -u +%T)" >> $L
[ "$HP" = "$HC" ] || { echo "PACKER HASH MISMATCH — stopping" >> $L; echo "STAGEP_DONE $(date -u +%T)" >> $L; exit 1; }
run() { env SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $1 128 1 4096 16384 $ACT > $2 2>&1; echo "NATIVE rot16 $3 $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $2 | tr '\n' ' ') $(date -u +%T)" >> $L; }
for rep in 1 2; do run $P/replay_sched6_C2ref $P/ab_p_c2_$rep.log "header=C2ref rep$rep"; run $P/replay_sched6_P $P/ab_p_p_$rep.log "header=P rep$rep"; done
echo "STAGEP_DONE $(date -u +%T)" >> $L
