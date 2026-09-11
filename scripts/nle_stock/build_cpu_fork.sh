#!/bin/bash
set -e
S=${S:-/puffertank/pufferlib}
cd $S
clang -O2 -fopenmp -I. -Isrc -Iocean/nethack -Ivendor -Ivendor/fast-nle/include \
  -Ivendor/fast-nle/build/_deps/deboost_context-src/include -Iraylib-5.5_linux_amd64/include \
  -DPLATFORM_DESKTOP -DPUFFER_NETHACK $S/scripts/nle_stock/nh_cpu_fork.c \
  -L$S/vendor/fast-nle/build -lnethack -Wl,-rpath,$S/vendor/fast-nle/build \
  -lm -lpthread -ldl -o $S/scripts/nle_stock/nh_cpu_fork
echo Built
