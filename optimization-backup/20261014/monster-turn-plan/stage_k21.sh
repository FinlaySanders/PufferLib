#!/bin/bash
# consolidation of v1.6c (if its corpus hash passed): PGO build, PGO gates, landing-style A/B (P-core + E-core) vs the landed engine,
# trainer live digest + the 5M/2048 pair (information only), eligible share census
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; X=/puffertank/experiments/nethack-scheduler-20261012; C=/puffertank/experiments/nethack-compact-state-20261008; N=/puffertank/experiments/nethack-engine-lines-20261014
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions; L=$P/stage_k21.log
echo "stage K21 waiting for K19 $(date -u +%T)" > $L
while ! grep -q STAGEK19_DONE $P/stage_k19.log 2>/dev/null; do sleep 15; done
grep -q "full hash rc=0" $P/stage_k19.log || { echo "v1.6c did not pass — not consolidating" >> $L; echo "STAGEK21_DONE $(date -u +%T)" >> $L; exit 1; }
cd $N && python3 build_pgo.py mt2pgo > $N/mt2pgo_v16.build.out 2>&1; echo "pgo build rc=$? $(grep 'PGO READY' $N/mt2pgo_v16.build.out) $(date -u +%T)" >> $L
cd $C && python3 check.py --quick lines_mt2pgo > $P/mt2pgo_gates_k21.log 2>&1; echo "pgo quick gates rc=$? passes=$(grep -c '^PASS' $P/mt2pgo_gates_k21.log) $(date -u +%T)" >> $L
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
run() { env LD_LIBRARY_PATH=$1 NH_MT2=$2 SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c $5 $X/replay_sched6 128 1 4096 16384 $ACT > $3 2>&1; echo "NATIVE rot16 $4 $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $3 | tr '\n' ' ') $(date -u +%T)" >> $L; }
for rep in 1 2; do run $N/engines/fastnle_ade/build 1 $P/ab_k21_ade_${rep}.log "PGO landed(fastnle_ade) rep$rep" 2; run $N/engines/mt2pgo/build 1 $P/ab_k21_pgo1_${rep}.log "PGO mt2 v1.6c NH_MT2=1 rep$rep" 2; done
run $N/engines/fastnle_ade/build 1 $P/ab_k21_ade_e.log "E-core PGO landed" 16; run $N/engines/mt2pgo/build 1 $P/ab_k21_pgo1_e.log "E-core PGO mt2 v1.6c" 16
env LD_LIBRARY_PATH=$E/build_cg NH_MT2=1 NH_MT2_STATS=$P/mt2_elig_v16_rot16.txt SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > /dev/null 2>&1; echo "eligible share: $(head -1 $P/mt2_elig_v16_rot16.txt)" >> $L
python3 - <<'PY'
import json
P='/puffertank/experiments/nethack-monster-turn-plan-20261014'; N='/puffertank/experiments/nethack-engine-lines-20261014'
jobs=[a for a in json.load(open(f'{P}/ab_mt2v14.json')) if a['label'] in ('mt2v14_live_on_v22','mt2v14_fast_off_v22_a','mt2v14_fast_on_v22_a')]
for a in jobs: a['label']=a['label'].replace('mt2v14_','mt2v16_'); a['env']['LD_LIBRARY_PATH']=f'{N}/engines/mt2pgo/build'
json.dump(jobs,open(f'{P}/ab_mt2v16.json','w'),indent=1)
PY
rm -f $P/ab_mt2v16.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $P/ab_mt2v16.json > $P/ab_mt2v16.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $L)
grep -E '^DONE' $P/ab_mt2v16.log >> $L
python3 - >> $L <<'PY'
import hashlib
t=open('/puffertank/experiments/nethack-24h-20261009/runs/mt2v16_live_on_v22/run.log',errors='replace').read(); lines=[l.strip() for l in t.splitlines() if l.startswith('LIVE_PROOF')]
print('mt2v16_live_on_v22', len(lines), 'epochs digest', hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:16], '(exact target 31e2e3deae720ef4)')
PY
echo "STAGEK21_DONE $(date -u +%T)" >> $L
