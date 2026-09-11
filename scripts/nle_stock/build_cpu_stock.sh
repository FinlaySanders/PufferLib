#!/bin/bash
set -e
S=${S:-/puffertank/pufferlib}
cd $S
clang -O2 -fPIC -c -I. -Ivendor/fast-nle/include -Ivendor/fast-nle/build/_deps/deboost_context-src/include -I$S/scripts/nle_stock \
  $S/scripts/nle_stock/nh_stock_backend.c -o $S/scripts/nle_stock/nh_stock_backend_cpu.o
clang -O2 -fopenmp -I. -Isrc -Iocean/nethack -Ivendor -Ivendor/fast-nle/include \
  -Ivendor/fast-nle/build/_deps/deboost_context-src/include -Iraylib-5.5_linux_amd64/include \
  -DPLATFORM_DESKTOP -DPUFFER_NETHACK $S/scripts/nle_stock/nh_cpu_fork.c $S/scripts/nle_stock/nh_stock_backend_cpu.o \
  -Wl,--export-dynamic-symbol=create_fcontext_stack -Wl,--export-dynamic-symbol=tmt_write \
  -lm -lpthread -ldl -o $S/scripts/nle_stock/nh_cpu_stock
echo Built
