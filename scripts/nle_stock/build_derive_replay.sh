#!/bin/bash
# offline derive replayer (no engine): re-runs nh_derive.h over NH_DERIVE_REC recordings, see nh_derive_replay.c
S=${S:-/puffertank/pufferlib}; cd $S
clang -O1 -g -Wall -Wno-unused-function -Wno-unused-variable -I$S/scripts/nle_stock -I$S/vendor/fast-nle/include $S/scripts/nle_stock/nh_derive_replay.c -o $S/scripts/nle_stock/nh_derive_replay -lm && echo "built $S/scripts/nle_stock/nh_derive_replay"
