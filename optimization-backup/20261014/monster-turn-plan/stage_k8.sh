#!/bin/bash
# after K7: why-census (first failing eligibility clause, 128-game rotation, CG build with v1.3 predicate)
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; X=/puffertank/experiments/nethack-scheduler-20261012; L=$P/stage_k8.log
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
echo "stage K8 waiting for K7 $(date -u +%T)" > $L
while ! grep -q STAGEK7_DONE $P/stage_k7.log 2>/dev/null; do sleep 15; done
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
env LD_LIBRARY_PATH=$E/build_cg NH_MT2=1 NH_MT2_STATS=$P/mt2_why_rot16.txt SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $P/mt2_why_run.log 2>&1; echo "why census rc=$? $(grep -oE 'obs=[^ ]+' $P/mt2_why_run.log) $(date -u +%T)" >> $L
python3 - >> $L <<'PY'
P='/puffertank/experiments/nethack-monster-turn-plan-20261014'
d={}
for l in open(f'{P}/mt2_why_rot16.txt'):
    k,*v=l.split()
    if k=='eligible_moves': d['eligible']=int(v[0]); d['all']=int(v[2])
    elif k.startswith('why_'): d[k]=int(v[0])
tot=d['all']; print(f"all moves {tot:,}  eligible {100*d['eligible']/tot:.1f}%  ineligible by first failing clause:")
for k,v in sorted(((k,v) for k,v in d.items() if k.startswith('why_')), key=lambda kv:-kv[1]): print(f"  {k[4:]:62s} {100*v/tot:5.1f}%")
PY
echo "STAGEK8_DONE $(date -u +%T)" >> $L
