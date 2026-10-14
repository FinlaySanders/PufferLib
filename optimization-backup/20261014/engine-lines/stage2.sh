#!/bin/bash
# Stage 2 (after stage 1): native rotation-16 series for candidate C (harness header) vs base, both on the base engine; then a
# function-level perf record of candidate B's engine (host perf server) for comparison with annot16b.
N=/puffertank/experiments/nethack-engine-lines-20261014; C=/puffertank/experiments/nethack-compact-state-20261008; X=/puffertank/experiments/nethack-scheduler-20261012; D=/puffertank/docker/perf_rot
L=$N/stage2.log; echo "stage2 waiting $(date -u +%T)" > $L
while ! grep -q STAGE1_DONE $N/stage1.log 2>/dev/null; do sleep 10; done
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0 LD_LIBRARY_PATH=$C/engines/tile_signed_pgo/build
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
for rep in 1 2; do for b in base C; do
  bin=$X/replay_sched6; [ $b = C ] && bin=$N/replay_sched6_C
  out=$N/native_rot16_hdr${b}_$rep.log
  env SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $bin 128 1 4096 16384 $ACT > $out 2>&1
  echo "NATIVE rot16 header=$b rep$rep $(grep -oE ' sps=[^ ]+|busy_sps=[^ ]+|obs=[^ ]+' $out | tr '\n' ' ') $(date -u +%T)" >> $L
done; done
echo "C_SERIES_DONE $(date -u +%T)" >> $L
# perf record of candidate B (same harness/argv as annot16b, engine = selB)
if [ -f $N/engines/selB/build/libnethack.so ] && [ $(( $(date +%s) - $(cat $D/daemon_alive) )) -lt 120 ]; then
  rm -f $D/results/annot16_selB.*
  printf 'PATTERN=%s\nMODE=record\nEVENTS=cycles:u,branch-misses:u\nDURATION=50\nDELAY=15\n' "'^/puffertank/experiments/nethack-scheduler-20261012/replay_sched6 256 1 4096 16384'" > $D/requests/902_annot16_selB.req
  env LD_LIBRARY_PATH=$N/engines/selB/build SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 256 1 4096 16384 $ACT > $N/native_rot16_selB_256.log 2>&1
  for i in $(seq 1 60); do [ -f $D/done/902_annot16_selB.req ] && break; sleep 5; done
  PERF=/usr/lib/linux-tools/7.0.0-29-generic/perf
  $PERF report -i $D/results/annot16_selB.data --stdio --no-children --sort sym -n --percent-limit 0.7 > $D/results/annot16_selB.sym.txt 2>&1
  $PERF script -i $D/results/annot16_selB.data -F event,ip,sym,symoff,dso 2>/dev/null > $D/results/annot16_selB.script.txt
  echo "PERF_SELB_DONE $(date -u +%T) $(grep -c . $D/results/annot16_selB.script.txt) samples" >> $L
else echo "perf server not alive or no selB; skipped record" >> $L; fi
echo "STAGE2_DONE $(date -u +%T)" >> $L
