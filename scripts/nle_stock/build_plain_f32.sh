#!/bin/bash
S=${S:-/puffertank/pufferlib}
# Same fork vec binary, but activations in fp32 instead of bf16, to test whether
# the CPU port's fp32 arithmetic is what costs it against the CUDA policy.
set -e
cd $S
ccache /usr/local/cuda/bin/nvcc -O2 --threads 0 -arch=native -std=c++17 \
  -I. -Isrc -Iocean/nethack -Ivendor -I./raylib-5.5_linux_amd64/include -I./src -I./vendor \
  -I./vendor/fast-nle/include -I./vendor/fast-nle/build/_deps/deboost_context-src/include \
  -I/usr/local/cuda/include -I/usr/local/cuda/include/cccl -I/usr/include \
  '-DENV_HEADER="ocean/nethack/nethack.h"' -DENV_NAME=nethack '-DPUFFER_ENV_NAME="nethack"' \
  -DPUFFERLIB_BUILD_MAIN -Xcompiler=-DPLATFORM_DESKTOP -Xcompiler=-fopenmp \
  -Xcompiler=-Wno-narrowing --diag-suppress=2361 -DPUFFER_NETHACK -DPRECISION_FLOAT \
  src/pufferl.cu raylib-5.5_linux_amd64/lib/libraylib.a \
  -L/usr/local/cuda/lib64 -L/usr/lib/x86_64-linux-gnu \
  -L$S/vendor/fast-nle/build -lnethack \
  -Xlinker -rpath -Xlinker $S/vendor/fast-nle/build \
  -ldl -lcudart -lnccl -lnvidia-ml -lcublas -lcusolver -lcurand -lm -lpthread -lomp5 -lGL \
  -o puffer_nethack_f32
echo Built
