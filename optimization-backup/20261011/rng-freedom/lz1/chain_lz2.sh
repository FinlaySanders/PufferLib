#!/bin/bash
CS=/puffertank/experiments/nethack-compact-state-20261008; R=/puffertank/experiments/nethack-engine-scaling-20261010; P=/puffertank/experiments/nethack-rng-freedom-20261011; H=/puffertank/experiments/nethack-24h-20261009
while ! grep -q GATES2_DONE $P/lz1/chain_lz1_gates.log; do sleep 10; done
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
cd $R
NH_LAZY=0 LD_LIBRARY_PATH=$CS/engines/lz2/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > $P/lz1/replay2_lazy0.log 2>&1
echo "LZ2_LAZY0 $(grep -o 'obs=[0-9a-f]* age=[0-9.]* turns=[0-9]*' $P/lz1/replay2_lazy0.log) (reference obs=b79eb25d93ca6d29 turns=115413681)"
NH_LAZY=1 LD_LIBRARY_PATH=$CS/engines/lz2_verify/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > $P/lz1/replay2_verify.log 2>&1
echo "LZ2_VERIFY mismatches=$(grep -c LAZY_MISMATCH $P/lz1/replay2_verify.log) panics=$(grep -c -i 'panic\|segmentation' $P/lz1/replay2_verify.log) $(grep -o 'obs=[0-9a-f]* age=[0-9.]*' $P/lz1/replay2_verify.log)"
grep LAZY_MISMATCH $P/lz1/replay2_verify.log | sed 's/turn=[0-9]* //; s/at [0-9]*,[0-9]*//; s/lazy=.*//' | sort | uniq -c | sort -rn | head -5 | sed 's/^/  /'
grep -h LAZY_STATS $P/lz1/replay2_verify.log | awk -F'[ =]' '{c+=$3; n+=$5; l+=$7; f+=$9; u+=$12; h+=$14; t+=$16; d+=$18} END{printf "LZ2_STATS chose=%d none=%d listdone=%d fullpath=%d | unicorn=%d hero=%d tracked=%d mdisp=%d | lazy-resolved %.1f%%\n", c,n,l,f,u,h,t,d, 100*(c+n)/(c+n+l+f)}'
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $H && python3 campaign_ablate.py ablate_ml.json > $P/lz1/campaign_ml.log 2>&1
for A in ctrl_a lazy_a lazy_b ctrl_b verify_stats; do f=runs/ml_$A/run.log; printf "%-16s " ml_$A; python3 sps_from_log.py $f 512 512 $((40*262144)) 2>&1 | tail -1 | cut -c1-12; grep -h POOL_WORKER $f | grep -o 'us_per_step=[0-9.]*' | cut -d= -f2 | awk '{s+=$1;n++} END{if(n) printf "  env us/step mean %.2f over %d worker-epochs", s/n, n}'; grep -h -o 'PERF_EPOCH[^\n]*' $f | tail -1 | grep -o 'mean_turn=[0-9.]*\|turns=[0-9.]*' | head -1 | sed 's/^/  /'; echo; done
grep -h LAZY_STATS runs/ml_verify_stats/run.log | tail -1 | sed 's/^/MATURE_/'
echo "CHAIN_LZ2_DONE $(date -u +%T)"
