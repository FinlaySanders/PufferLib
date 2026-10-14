#!/bin/bash
# consolidation of kernel v1.4: PGO build, PGO gates, landing-style A/B vs the landed PGO engine, trainer A/B (fast protocol) + live digest
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; X=/puffertank/experiments/nethack-scheduler-20261012; C=/puffertank/experiments/nethack-compact-state-20261008; N=/puffertank/experiments/nethack-engine-lines-20261014
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions; L=$P/stage_k12.log
echo "stage K12 start $(date -u +%T)" > $L
cd $N && python3 build_pgo.py mt2pgo > $N/mt2pgo_v14.build.out 2>&1; echo "pgo build rc=$? $(grep 'PGO READY' $N/mt2pgo_v14.build.out) $(date -u +%T)" >> $L
cd $C && python3 check.py --quick lines_mt2pgo > $P/mt2pgo_gates_k12.log 2>&1; echo "pgo quick gates rc=$? passes=$(grep -c '^PASS' $P/mt2pgo_gates_k12.log) $(date -u +%T)" >> $L
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
run() { env LD_LIBRARY_PATH=$1 NH_MT2=$2 SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $3 2>&1; echo "NATIVE rot16 $4 $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $3 | tr '\n' ' ') $(date -u +%T)" >> $L; }
for rep in 1 2; do run $N/engines/fastnle_ade/build 1 $P/ab_k12_ade_${rep}.log "PGO landed(fastnle_ade) rep$rep"; run $N/engines/mt2pgo/build 1 $P/ab_k12_pgo1_${rep}.log "PGO mt2 v1.4 NH_MT2=1 rep$rep"; done
env LD_LIBRARY_PATH=$N/engines/mt2pgo/build NH_MT2=1 SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 16 $X/replay_sched6 128 1 4096 16384 $ACT > $P/ab_k12_pgo1_e.log 2>&1; echo "NATIVE rot16 E-core PGO mt2 v1.4 $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $P/ab_k12_pgo1_e.log | tr '\n' ' ') $(date -u +%T)" >> $L
env LD_LIBRARY_PATH=$N/engines/fastnle_ade/build NH_MT2=1 SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 16 $X/replay_sched6 128 1 4096 16384 $ACT > $P/ab_k12_ade_e.log 2>&1; echo "NATIVE rot16 E-core PGO landed $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $P/ab_k12_ade_e.log | tr '\n' ' ') $(date -u +%T)" >> $L
rm -f $P/ab_mt2v14.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $P/ab_mt2v14.json > $P/ab_mt2v14.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $L)
grep -E '^DONE' $P/ab_mt2v14.log >> $L
python3 - >> $L <<'PY'
import hashlib, json
t=open('/puffertank/experiments/nethack-24h-20261009/runs/mt2v14_live_on_v22/run.log',errors='replace').read(); lines=[l.strip() for l in t.splitlines() if l.startswith('LIVE_PROOF')]
print('mt2v14_live_on_v22', len(lines), 'epochs digest', hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:16], '(exact target 31e2e3deae720ef4)')
P='/puffertank/experiments/nethack-monster-turn-plan-20261014'
r={x['label']:x for x in json.load(open(f'{P}/ab_mt2v14.results.json'))}
for b in ('v22','v12'):
    off=[r[f'mt2v14_fast_off_{b}_{k}']['sps'] for k in 'ab']; on=[r[f'mt2v14_fast_on_{b}_{k}']['sps'] for k in 'ab']
    print(f"trainer {b}: off {off[0]:.0f}/{off[1]:.0f} on {on[0]:.0f}/{on[1]:.0f}  +{100*(sum(on)/sum(off)-1):.1f}%")
PY
echo "STAGEK12_DONE $(date -u +%T)" >> $L
