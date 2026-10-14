#!/bin/bash
# Stage 4 (quiet box, after the trainer campaign): clean re-run of the candidate C native series, debug twins of selA/selB, line-level attribution of B's record.
N=/puffertank/experiments/nethack-engine-lines-20261014; C=/puffertank/experiments/nethack-compact-state-20261008; X=/puffertank/experiments/nethack-scheduler-20261012; D=/puffertank/docker/perf_rot
L=$N/stage4.log; echo "stage4 waiting $(date -u +%T)" > $L
while ! grep -q STAGE3_DONE $N/stage3.log 2>/dev/null; do sleep 15; done
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0 LD_LIBRARY_PATH=$C/engines/tile_signed_pgo/build
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
for rep in 3 4; do for b in base C; do
  bin=$X/replay_sched6; [ $b = C ] && bin=$N/replay_sched6_C
  out=$N/native_rot16_hdr${b}_$rep.log
  env SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $bin 128 1 4096 16384 $ACT > $out 2>&1
  echo "NATIVE rot16 header=$b rep$rep $(grep -oE ' sps=[^ ]+|busy_sps=[^ ]+|obs=[^ ]+' $out | tr '\n' ' ') $(date -u +%T)" >> $L
done; done
echo "C_SERIES2_DONE $(date -u +%T)" >> $L
for e in selA selB; do (cd $N && python3 build_twin.py $e >> $L 2>&1); done
if [ -f $D/results/annot16_selB.script.txt ]; then
  python3 $D/annot_script.py $D/results/annot16_selB.script.txt m_move:$N/engines/selB/build/libnethack.so:$N/engines/selB_g/build/libnethack.so:16 mfndpos_masked.lto_priv.0:$N/engines/selB/build/libnethack.so:$N/engines/selB_g/build/libnethack.so:16 > $D/results/annot16_selB.lines.txt 2>&1
  echo "SELB_LINES_DONE $(wc -l < $D/results/annot16_selB.lines.txt) lines" >> $L
fi
echo "STAGE4_DONE $(date -u +%T)" >> $L
