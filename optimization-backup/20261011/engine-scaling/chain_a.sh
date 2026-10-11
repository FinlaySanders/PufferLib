#!/bin/bash
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008; C=/puffertank/experiments/nethack-24h-20261009
cd $R
./native_screen.sh $CS/engines/incexport/build incexport; echo NATIVE_DONE
./native_screen2.sh $CS/engines/incexport2/build $R/harness_incpack/replay incpack; echo NATIVE2_DONE
( cd $CS && nice -n 10 python3 check.py incexport2 --quick ); echo GATES2_DONE
cd $R/trainer_incpack/source && NVCC_EXTRA="$(cat $C/build_flags.txt)" ./build.sh nethack puffer_incpack > $R/trainer_incpack/build.log 2>&1 && cp puffer_incpack $C/binaries/incpack_v38 && echo BUILD_DONE || { echo BUILD_FAILED; tail -20 $R/trainer_incpack/build.log; exit 1; }
cd $C && python3 campaign_ablate.py ablate_incpack.json; echo FULL_DONE
