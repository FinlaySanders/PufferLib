#!/bin/bash
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad; R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008; H=/puffertank/experiments/nethack-24h-20261009; P=/puffertank/experiments/nethack-rng-freedom-20261011
while ! grep -q 'BUILT rm1\|rror' $S/build_rm1.log; do sleep 10; done
[ -f $CS/engines/rm1/build/libnethack.so ] || { echo RM1_BUILD_FAILED; grep -m3 'error' $S/build_rm1.log $CS/engines/rm1/build.log; exit 1; }
echo "RM1_BUILT $(date -u +%T)"
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $H && python3 campaign_ablate.py ablate_rm1.json > $P/campaign_rm1.log 2>&1
for A in ctrl_a cand_a cand_b ctrl_b; do printf "%-16s " rm1_5m4k_$A; python3 sps_from_log.py runs/rm1_5m4k_$A/run.log 4096 2>&1 | tail -1; done
cmp -s <(grep BATCH_PROOF runs/rm1_5m4k_ctrl_a/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/rm1_5m4k_ctrl_b/run.log | sed 's/epoch=[0-9]* //') && echo "PROOF ctrl_a==ctrl_b" || echo "PROOF ctrl_a!=ctrl_b"
cmp -s <(grep BATCH_PROOF runs/rm1_5m4k_ctrl_a/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/rm1_5m4k_cand_a/run.log | sed 's/epoch=[0-9]* //') && echo "PROOF cand==ctrl (unexpected)" || echo "PROOF cand!=ctrl (expected: new RNG stream)"
echo "ABBA_RM1_DONE $(date -u +%T)"
while ! grep -q 'BUILT rc1\|rror' $S/build_rc1.log; do sleep 10; done
[ -f $CS/engines/rc1/build/libnethack.so ] || { echo RC1_BUILD_FAILED; grep -m3 'error' $S/build_rc1.log $CS/engines/rc1/build.log; exit 1; }
cd $R && NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0 LD_LIBRARY_PATH=$CS/engines/rc1/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > $P/rc1_census_run.log 2>&1
grep -E 'RESULT|NH_CENSUS' $P/rc1_census_run.log | cut -c1-600
echo "CHAIN_RNG0_DONE $(date -u +%T)"
