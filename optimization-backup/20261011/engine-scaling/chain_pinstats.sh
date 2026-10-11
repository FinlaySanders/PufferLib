#!/bin/bash
# build cohort_pin (per-worker stats + generalised pinning), then 24 pinned / 24 unpinned / 32 pinned at 5M/4096 with per-worker µs/step
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad; R=/puffertank/experiments/nethack-engine-scaling-20261010; T=$R/trainer_cohort; H=/puffertank/experiments/nethack-24h-20261009
while ! grep -q "CHAIN_KNOBS4K_DONE" $S/chain_knobs4k.log; do sleep 5; done
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $T && rm -rf snapshots/cohort_pin && python3 build.py cohort_pin -DPUF_MUON_OUTPLACE -lcuda > $T/build_cohort_pin.out 2>&1; rc=$?; echo "BUILD_cohort_pin rc=$rc $(date -u +%T)"
[ $rc -eq 0 ] || { grep -m5 "error" $T/cohort_pin-build.log | cut -c1-200; echo CHAIN_ABORT_BUILD; exit 1; }
ln -sfn $T/binaries/cohort_pin $H/binaries/cohort_pin
cd $H && python3 campaign_ablate.py ablate_pinstats.json
for L in pin24_stats unpin24_stats pin32_stats; do printf "%-14s " $L; python3 sps_from_log.py runs/$L/run.log 4096 2>&1 | tail -1
  grep -h "POOL_WORKER" runs/$L/run.log | awk -F'[ =]' '{id=$5; st[id]+=$7; b[id]+=$9} END{for(i in st) printf "%s %d %.1f\n", i, st[i], st[i]?1000*b[i]/st[i]:0}' | sort -n | awk -v L=$L '{printf "  id=%-2s steps=%-7d us/step=%s\n",$1,$2,$3}' | head -40; done
echo CHAIN_PINSTATS_DONE
