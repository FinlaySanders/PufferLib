#!/bin/bash
source /puffertank/experiments/nethack-scheduler-20261012/overnight/lib.sh
log "=== OVERNIGHT START (waits for the cap scan)"; while ! grep -q CHAIN_CAP_DONE $X/trainer/chain_cap.log 2>/dev/null; do sleep 30; done
PGO=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build; PLAIN=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed/build
# ---------- Phase D: scheduler map (GPU, no perf) ----------
log "=== PHASE D: scheduler map"
cd $H && python3 campaign_ablate.py $X/overnight/ab_map.json 2>&1 | grep DONE | tee -a $L
# ---------- Phase A: rotation perf matrix (needs the host daemon) ----------
log "=== PHASE A: rotation perf (daemon $(daemon_up && echo up || echo DOWN))"
wait_daemon 1800 || log "daemon never came up; perf phases will be skipped"
for A in 1 4 16 64; do
  perf_req rot${A}_G1 'replay_sched6 128 1 4096' stat $G1 45 15 && { rot_run $A $PGO rot${A}_G1; perf_wait rot${A}_G1; }
  perf_req rot${A}_G3 'replay_sched6 128 1 4096' stat $G3 45 15 && { rot_run $A $PGO rot${A}_G3; perf_wait rot${A}_G3; }
  perf_req rot${A}_TD 'replay_sched6 128 1 4096' topdown '' 45 15 && { rot_run $A $PGO rot${A}_TD; perf_wait rot${A}_TD; }
done
for A in 1 16; do perf_req rot${A}_REC 'replay_sched6 128 1 4096' record '' 35 15 && { rot_run $A $PGO rot${A}_REC; perf_wait rot${A}_REC 400; }; done
# ---------- Phase B: PGO vs plain engine rotation ----------
log "=== PHASE B: engine PGO vs plain, rotation 1 and 16"
for A in 1 16; do perf_req plain_rot${A}_G1 'replay_sched6 128 1 4096' stat $G1 45 15 && { rot_run $A $PLAIN plain_rot${A}_G1; perf_wait plain_rot${A}_G1; }; done
# ---------- Phase C: trainer perf, pool vs scheduler ----------
log "=== PHASE C: trainer perf pool vs scheduler (5M/2048, 120 epochs)"
for arm in perf_pool perf_sched; do for G in G1 G3 TD; do
  ev=$G1; mode=stat; [ $G = G3 ] && ev=$G3; [ $G = TD ] && { mode=topdown; ev=''; }
  perf_req ${arm}_$G 'binaries/sched_(ctrl|v10) train' $mode "$ev" 50 25 || true
  ( cd $H && rm -rf runs/${arm}_$G && python3 campaign_ablate.py $X/overnight/ab_${arm}_$G.json 2>&1 | grep DONE | tee -a $L )
  perf_wait ${arm}_$G 60
done; done
# ---------- Phase E: live learning pair with proofs ----------
log "=== PHASE E: live learning pair (pool vs scheduler, 150 epochs, random init, LIVE_PROOF)"
cd $H && python3 campaign_ablate.py $X/overnight/ab_livelearn.json 2>&1 | grep DONE | tee -a $L
cmp <(grep LIVE_PROOF $H/runs/ll_pool/run.log | sed 's/epoch=[0-9]* //') <(grep LIVE_PROOF $H/runs/ll_sched/run.log | sed 's/epoch=[0-9]* //') && log "LIVE LEARNING PROOF pool vs sched: IDENTICAL ($(grep -c LIVE_PROOF $H/runs/ll_pool/run.log) epochs)" || log "LIVE LEARNING PROOF: DIFFER (first diff: $(diff <(grep LIVE_PROOF $H/runs/ll_pool/run.log) <(grep LIVE_PROOF $H/runs/ll_sched/run.log) | grep '^<' | head -1))"
# ---------- Phase F: PR 693 32 MB workspace comparison ----------
log "=== PHASE F: PR693 ws32"; bash /tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad/pr693/ws32_now.sh >/dev/null 2>&1 || true
log "=== OVERNIGHT DONE"
