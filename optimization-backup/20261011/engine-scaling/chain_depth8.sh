#!/bin/bash
# pipeline depth 8: 64-agent buffers, 8 per group (same 512 resident) vs the 128x4 layout; 15M/2048, 15M/4096, 5M/2048
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad; R=/puffertank/experiments/nethack-engine-scaling-20261010; T=$R/trainer_cohort; H=/puffertank/experiments/nethack-24h-20261009
while ! grep -q "CHAIN_PINSTATS_DONE\|CHAIN_ABORT" $S/chain_pinstats.log; do sleep 5; done
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $T && rm -rf snapshots/cohort_d8 && python3 build.py cohort_d8 -DPUF_MUON_OUTPLACE -lcuda > $T/build_cohort_d8.out 2>&1; rc=$?; echo "BUILD_cohort_d8 rc=$rc $(date -u +%T)"
[ $rc -eq 0 ] || { grep -m5 "error" $T/cohort_d8-build.log | cut -c1-200; echo CHAIN_ABORT_BUILD; exit 1; }
ln -sfn $T/binaries/cohort_d8 $H/binaries/cohort_d8
cd $H && python3 campaign_ablate.py ablate_depth8.json
for L in d8_15m_2k:2048 d4_15m_2k_ref:2048 d8_15m_4k:4096 d8_5m_2k:2048; do IFS=: read NAME AG <<<"$L"; printf "%-14s " $NAME; python3 sps_from_log.py runs/$NAME/run.log $AG 2>&1 | tail -1; done
cmp -s <(grep BATCH_PROOF runs/d4_15m_2k_ref/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/d8_15m_2k/run.log | sed 's/epoch=[0-9]* //') && echo "PROOF d8 vs d4 (15M/2048): identical" || echo "PROOF d8 vs d4: DIFFERS"
cmp -s <(grep BATCH_PROOF runs/w26/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/d8_5m_2k/run.log | sed 's/epoch=[0-9]* //') && echo "PROOF d8_5m vs w26 (128 layout): identical" || echo "PROOF d8_5m vs w26: DIFFERS"
echo CHAIN_DEPTH8_DONE
