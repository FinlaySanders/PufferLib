#!/bin/bash
# E-core rotation ladder (cpu 16, 128 games, warm 4096, measure 16384), then the slots x cap trainer sweep at 5M/2048.
L=/puffertank/experiments/nethack-latency-20261014; X=/puffertank/experiments/nethack-scheduler-20261012; C=/puffertank/experiments/nethack-compact-state-20261008
G=$L/stage1.log; echo "stage1 start $(date -u +%T)" > $G
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0 LD_LIBRARY_PATH=$C/engines/tile_signed_pgo/build
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
for cpu in 16 2; do for A in 1 4 16; do
  out=$L/ladder_cpu${cpu}_A$A.log
  env SCHED_C=1 SCHED_A=$A SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c $cpu $X/replay_sched6 128 1 4096 16384 $ACT > $out 2>&1
  echo "LADDER cpu=$cpu A=$A $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $out | tr '\n' ' ') $(date -u +%T)" >> $G
done; done
echo "LADDER_DONE $(date -u +%T)" >> $G
python3 - <<'PY'
import json
L='/puffertank/experiments/nethack-latency-20261014'; X='/puffertank/experiments/nethack-scheduler-20261012'
base=[a for a in json.load(open(f'{X}/trainer/ab_tpause.json')) if a['label']=='tp_spin_a'][0]
def arm(label, slots, cap):
    a=json.loads(json.dumps(base)); a['label']=label; a['env']['PUF_SCHED_SLOTS']=slots
    if cap is None: a['env'].pop('PUF_SCHED_HOT_CAP',None)
    else: a['env']['PUF_SCHED_HOT_CAP']=cap
    return a
arms=[arm('lat_s4_cap12',4,12),arm('lat_s8_adapt',8,None),arm('lat_s16_adapt',16,None),arm('lat_s16_cap4',16,4),arm('lat_s8_cap6',8,6),arm('lat_s4_cap6',4,6),arm('lat_s4_cap12_b',4,12)]
json.dump(arms,open(f'{L}/ab_latency.json','w'),indent=1); print([a['label'] for a in arms])
PY
rm -f $L/ab_latency.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $L/ab_latency.json > $L/ab_latency.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $G)
for lab in lat_s4_cap12 lat_s8_adapt lat_s16_adapt lat_s16_cap4 lat_s8_cap6 lat_s4_cap6 lat_s4_cap12_b; do
  r=/puffertank/experiments/nethack-24h-20261009/runs/$lab/run.log
  echo "ARM $lab $(grep -E '^DONE '"$lab"' ' $L/ab_latency.log | grep -oE 'sps [0-9]+') | $(grep SCHED_INFER $r | tail -1 | grep -oE 'rows_per_forward=[^ ]+|forward_us=[^ ]+' | tr '\n' ' ') | $(grep SCHED_STATS $r | tail -1 | grep -oE 'borrow_pct=[^ ]+|cap_mean=[^ ]+|rt_us=[^ ]+|step_us=[^ ]+|hot_set_mean=[^ ]+|us_per_step=[^ ]+|idle_mean=[^ ]+' | tr '\n' ' ')" >> $G
done
echo "STAGE1_DONE $(date -u +%T)" >> $G
