#!/bin/bash
N=/puffertank/experiments/nethack-engine-lines-20261014; X=/puffertank/experiments/nethack-scheduler-20261012; C=/puffertank/experiments/nethack-compact-state-20261008; G=$N/stage_c2.log
echo "c2 waiting for tune series $(date -u +%T)" > $G
while ! grep -q TUNE_DONE $N/tune.log 2>/dev/null; do sleep 15; done
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0 LD_LIBRARY_PATH=$C/engines/tile_signed_pgo/build
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
for rep in 1 2; do for b in base C C2; do
  bin=$X/replay_sched6; [ $b = C ] && bin=$N/replay_sched6_C; [ $b = C2 ] && bin=$N/replay_sched6_C2
  out=$N/native_rot16_hdr${b}_c2_$rep.log
  env SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $bin 128 1 4096 16384 $ACT > $out 2>&1
  echo "NATIVE rot16 header=$b rep$rep $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $out | tr '\n' ' ') $(date -u +%T)" >> $G
done; done
rm -f $N/ab_c2.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $N/ab_c2.json > $N/ab_c2.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $G)
grep -E '^DONE' $N/ab_c2.log >> $G
python3 - >> $G <<'PY'
import hashlib
t=open('/puffertank/experiments/nethack-24h-20261009/runs/c2_live_v22/run.log',errors='replace').read(); lines=[l.strip() for l in t.splitlines() if l.startswith('LIVE_PROOF')]
print('c2_live_v22', len(lines), 'epochs digest', hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:16], '(exact target 31e2e3deae720ef4)')
PY
echo "C2_DONE $(date -u +%T)" >> $G
