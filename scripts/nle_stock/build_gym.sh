#!/bin/bash
# libnhagent.so: PufferLib NetHack env + CPU policy + reconstruction, engine = NetHackChallenge-v0 via Python callbacks
set -e
S=${S:-/puffertank/pufferlib}
cd $S
INC="-I. -Isrc -Iocean/nethack -Ivendor -Ivendor/fast-nle/include -Ivendor/fast-nle/build/_deps/deboost_context-src/include -Iraylib-5.5_linux_amd64/include -I$S/scripts/nle_stock"
clang -O2 -fPIC -c $INC -DPLATFORM_DESKTOP -DPUFFER_NETHACK $S/scripts/nle_stock/nh_gym_backend.c -o $S/scripts/nle_stock/nh_gym_backend.o
clang -O2 -fPIC -c $INC -fopenmp -DPLATFORM_DESKTOP -DPUFFER_NETHACK $S/scripts/nle_stock/nh_gym_runner.c -o $S/scripts/nle_stock/nh_gym_runner.o
clang -shared -fopenmp $S/scripts/nle_stock/nh_gym_backend.o $S/scripts/nle_stock/nh_gym_runner.o -o $S/scripts/nle_stock/libnhagent.so -lm -lpthread
echo "Built: $S/scripts/nle_stock/libnhagent.so"
