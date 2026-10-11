#!/bin/bash
# Unattended finish: wait for mt7's chain, pick the final engine (mt7 if its ABBA is not negative in either regime, else mt5), fold.
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad; R=/puffertank/experiments/nethack-engine-scaling-20261010
while ! grep -q "CHAIN_mt7_DONE\|CHAIN_ABORT" $S/chain_mt7.log; do sleep 30; done
FINAL=$(python3 - <<'PY'
import re
L=open('/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad/chain_mt7.log').read()
def mean(tag,n): 
    v=[float(x) for x in re.findall(tag+r'_[ab] '+str(n)+r' sps=([0-9.]+)',L)]; return sum(v)/len(v) if v else 0
ok=all(mean('cand',n)>=mean('ctrl',n)*0.998 for n in (512,2048)) and 'HASHES mt7 16777216 0' in L
print('mt7' if ok else 'mt5')
PY
)
echo "FINAL=$FINAL" | tee -a $R/PROGRAM.md
cd $R && ./chain_finish_fold.sh $FINAL
