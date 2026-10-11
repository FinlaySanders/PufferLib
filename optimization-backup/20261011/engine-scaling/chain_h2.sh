#!/bin/bash
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad; R=/puffertank/experiments/nethack-engine-scaling-20261010
until grep -q PF512_DONE $S/chain_g.log 2>/dev/null; do sleep 15; done
cd $R && ./pf_screen.sh 2048 pf2048_v2 0 29 93 221 0 93 0; echo PFV2_DONE
CPU_PIN_WORKERS=1 ./pf_screen.sh 2048 pf2048_v2pinned 0 93 221 0; echo PFV2PIN_DONE
