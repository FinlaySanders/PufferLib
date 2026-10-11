#!/bin/bash
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad; R=/puffertank/experiments/nethack-engine-scaling-20261010
until grep -q FOOTPRINT_HEAT1_DONE $S/chain_f.log 2>/dev/null; do sleep 15; done
cd $R && ./pf_screen.sh 2048 pf2048 0 1 13 29 61 0 13 29 0; echo PF2048_DONE
./pf_screen.sh 512 pf512 0 13 29 0; echo PF512_DONE
