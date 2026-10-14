#!/bin/bash
X=/puffertank/experiments/nethack-scheduler-20261012; H=/puffertank/experiments/nethack-24h-20261009
while ! grep -q AB_DONE $X/trainer/ab_live.launcher.log 2>/dev/null; do sleep 15; done
echo "=== LIVE A/B"; grep DONE $X/trainer/ab_live.launcher.log
for L in live_ctrl live_sched; do echo "$L live_proofs=$(grep -c LIVE_PROOF $H/runs/$L/run.log) $(grep -E 'SCHED_CORES' $H/runs/$L/run.log | tail -1 | cut -c1-120)"; done
cmp <(grep LIVE_PROOF $H/runs/live_ctrl/run.log | sed 's/epoch=[0-9]* //') <(grep LIVE_PROOF $H/runs/live_sched/run.log | sed 's/epoch=[0-9]* //') && echo "LIVE_PROOF sched vs ctrl: IDENTICAL" || { echo "LIVE_PROOF sched vs ctrl: DIFFER"; diff <(grep LIVE_PROOF $H/runs/live_ctrl/run.log) <(grep LIVE_PROOF $H/runs/live_sched/run.log) | head -6; }
while pgrep -f '^\S*/puffer_|binaries/sched' >/dev/null; do sleep 5; done
cd $X/trainer && python3 build.py sched_v10 > build_v10.out 2>&1; echo "BUILD_V10 rc=$? $(date -u +%T)"; grep -E ' error' sched_v10-build.log | head -3
ln -sfn $X/trainer/binaries/sched_v10 $H/binaries/sched_v10
cd $H && for L in sv10_batch sv10_kernel sv10_batch_b sv10_ctrl sv10_batch_cap12; do rm -rf runs/$L; done
python3 campaign_ablate.py $X/trainer/ab_v10.json 2>&1 | grep DONE
for L in sv10_batch sv10_kernel sv10_batch_b sv10_batch_cap12; do echo "== $L"; grep -E 'SCHED_STATS|SCHED_INFER|SCHED_CORES' $H/runs/$L/run.log | tail -3 | sed -E 's/steps_own=[0-9]+ steps_borrow=[0-9]+ //; s/busy_min=[^ ]+ busy_max=[^ ]+ //; s/activations=[0-9]+ //; s/cap_mean/cap/; s/parked_back=[0-9]+ //; s/P_steps=[0-9]+ E_steps=[0-9]+ //; s/P_borrows.*//' | cut -c1-170; grep -E 'Assert|error' $H/runs/$L/run.log | head -2 | cut -c1-160; done
cmp <(grep BATCH_PROOF $H/runs/sv10_ctrl/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF $H/runs/sv10_batch/run.log | sed 's/epoch=[0-9]* //') && echo "BATCH_PROOF batch-gather vs ctrl: IDENTICAL" || echo "BATCH_PROOF batch-gather vs ctrl: DIFFER"
echo CHAIN_V10_DONE
