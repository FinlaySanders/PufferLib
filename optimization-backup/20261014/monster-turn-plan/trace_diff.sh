#!/bin/bash
# usage: trace_diff.sh <golden.golden> — replays one golden with NH_MT2=0 and NH_MT2=1 on the trace build, diffs the per-decision traces
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2/build_trace; OLD=/puffertank/experiments/nethack-perf-20260917
G=${1:?golden}; N=$(basename $G .golden)
export NETHACKDIR=$OLD/dat NH_ZT_MASK=0
for f in 0 1; do env LD_LIBRARY_PATH=$E NH_MT2=$f NH_MT2_TRACE=$P/trace_${N}_$f.txt $OLD/gates/replay_golden $E/libnethack.so $OLD/dat $G > $P/trace_${N}_$f.log 2>&1; echo "NH_MT2=$f rc=$? lines=$(wc -l < $P/trace_${N}_$f.txt)"; done
cmp $P/trace_${N}_0.txt $P/trace_${N}_1.txt && echo "TRACES IDENTICAL" || { L=$(cmp $P/trace_${N}_0.txt $P/trace_${N}_1.txt | grep -oE 'line [0-9]+' | grep -oE '[0-9]+'); echo "first difference at trace line $L"; echo "--- old"; sed -n "$((L>2?L-2:1)),$((L+1))p" $P/trace_${N}_0.txt; echo "--- new"; sed -n "$((L>2?L-2:1)),$((L+1))p" $P/trace_${N}_1.txt; }
