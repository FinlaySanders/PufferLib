#!/bin/bash
# fold dv4: wait for the PGO build, quick gates on dv4_pgo, trainer ABBA vs mt7_pgo in the cohort regime (5M/4096, 15M/2048)
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008; H=/puffertank/experiments/nethack-24h-20261009
while pgrep -f "build_pgo[.]py dv4" >/dev/null; do sleep 10; done
[ -f $CS/engines/dv4_pgo/build/libnethack.so ] || { echo "PGO_BUILD_FAILED"; tail -5 /tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad/build_pgo_dv4.log; echo CHAIN_ABORT; exit 1; }
echo "PGO_dv4_DONE $(date -u +%T) sha=$(sha256sum $CS/engines/dv4_pgo/build/libnethack.so | cut -c1-16)"
cd $CS && nice -n 5 python3 check.py dv4_pgo --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback"; echo GATES_dv4_pgo_DONE
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $H && python3 campaign_ablate.py ablate_landing5.json
for T in land5_5m4k:4096 land5_15m2k:2048; do IFS=: read TAG AG <<<"$T"; for S in ctrl_a cand_a cand_b ctrl_b; do printf "%-20s " ${TAG}_$S; python3 sps_from_log.py runs/${TAG}_$S/run.log $AG 2>&1 | tail -1; done; done
for T in land5_5m4k land5_15m2k; do cmp -s <(grep BATCH_PROOF runs/${T}_ctrl_a/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/${T}_cand_a/run.log | sed 's/epoch=[0-9]* //') && echo "PROOF $T cand vs ctrl: identical" || echo "PROOF $T: DIFFERS"; done
echo CHAIN_LAND5_DONE
