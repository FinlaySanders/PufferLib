#!/bin/bash
CS=/puffertank/experiments/nethack-compact-state-20261008; R=/puffertank/experiments/nethack-engine-scaling-20261010; P=/puffertank/experiments/nethack-rng-freedom-20261011; H=/puffertank/experiments/nethack-24h-20261009; G=$CS/gates; DAT=/puffertank/experiments/nethack-perf-20260917/dat
export NETHACKDIR=$DAT NH_ZT_MASK=0
cd $R
NH_LAZY=0 LD_LIBRARY_PATH=$CS/engines/lz1/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > $P/lz1/replay_lazy0.log 2>&1
echo "LAZY0_REPLAY $(grep -o 'obs=[0-9a-f]* age=[0-9.]* turns=[0-9]*' $P/lz1/replay_lazy0.log) (reference obs=b79eb25d93ca6d29 turns=115413681)"
NH_LAZY=1 LD_LIBRARY_PATH=$CS/engines/lz1_verify/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > $P/lz1/replay_verify.log 2>&1
echo "VERIFY_REPLAY $(grep -o 'seconds=[0-9.]* sps=[0-9.]* obs=[0-9a-f]* age=[0-9.]* turns=[0-9]*' $P/lz1/replay_verify.log)"
echo "VERIFY_MISMATCH count=$(grep -c LAZY_MISMATCH $P/lz1/replay_verify.log) panics=$(grep -c -i 'panic\|segmentation\|impossible' $P/lz1/replay_verify.log)"
grep LAZY_MISMATCH $P/lz1/replay_verify.log | sed 's/turn=[0-9]* //; s/at [0-9]*,[0-9]*//; s/lazy=.*//' | sort | uniq -c | sort -rn | head -6 | sed 's/^/  /'
grep -h LAZY_STATS $P/lz1/replay_verify.log | awk -F'[ =]' '{c+=$3; n+=$5; f+=$7} END{printf "VERIFY_STATS chose=%d none=%d fallback=%d (fallback share %.1f%%)\n", c, n, f, 100*f/(c+n+f)}'
for suite in fuzz goldens; do NH_LAZY=1 LD_LIBRARY_PATH=$CS/engines/lz1/build $G/replay_golden $CS/engines/lz1/build/libnethack.so $CS/dat $CS/checks/$suite/*.golden > $P/lz1/gate_$suite.log 2>&1; echo "GATE_$suite rc=$? crashes=$(grep -c -i 'panic\|segmentation\|abort\|impossible' $P/lz1/gate_$suite.log) lines=$(wc -l < $P/lz1/gate_$suite.log)"; done
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $H && python3 campaign_ablate.py ablate_lz1.json > $P/lz1/campaign_lz1.log 2>&1
for reg in 5m2k:2048:128 5m512:512:512; do IFS=: read T AG HZ <<<"$reg"; for A in ctrl_a lazy_a lazy_b ctrl_b; do printf "%-18s " lz1_${T}_$A; python3 sps_from_log.py runs/lz1_${T}_$A/run.log $AG $HZ 2>&1 | tail -1 | cut -c1-12; done; done
echo "CHAIN_LZ1_DONE $(date -u +%T)"
