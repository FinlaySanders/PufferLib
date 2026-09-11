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
# guard: the binary must link THIS tree's engine, not a stale side build (the 2026-09-11 wrong-library trap, twice)
_bin=$( [ "$(basename $0)" = build_cpu_fork.sh ] && echo $S/scripts/nle_stock/nh_cpu_fork || echo $S/puffer_nethack_harness )
_lib=$(ldd $_bin 2>/dev/null | grep -o '/[^ ]*libnethack.so' | head -1)
[ "$_lib" = "$S/vendor/fast-nle/build/libnethack.so" ] || { echo "LINK GUARD: $_bin links '$_lib', expected $S/vendor/fast-nle/build/libnethack.so" >&2; exit 2; }
echo "link guard ok: $_bin -> $_lib"
