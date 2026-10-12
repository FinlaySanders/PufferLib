#!/bin/bash
# Builds replay_sched and replay_pool against the harness_cohort header set (hash lineage b97835c62aaf388f) and a chosen engine.
# Usage: ./build.sh [engine_dir]   (default: compact-state engines/tile_signed_pgo; needs <engine>/source/include and <engine>/build/libnethack.so)
set -e
X=$(cd "$(dirname "$0")" && pwd)
R=/puffertank/experiments/nethack-engine-scaling-20261010
ENG=${1:-/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo}
SFX=${2:-}
INC="-I$R/harness_cohort -I$R/harness_cohort/source/src -I$R/harness_cohort/source/ocean/nethack -I$ENG/source/include -I/puffertank/pufferlib/raylib-5.5_linux_amd64/include -I/usr/local/cuda/include -I/puffertank/pufferlib/vendor/fast-nle/build/_deps/deboost_context-src/include"
cc -O2 -g -pthread -DNVTX_DISABLE $INC $X/replay_sched.c -L$ENG/build -lnethack -lm -ldl -o $X/replay_sched$SFX
cc -O2 -g -pthread -fopenmp -DNVTX_DISABLE $INC -I$R/trainer_cohort/source/src $X/replay_pool.c -L$ENG/build -lnethack -lm -ldl -o $X/replay_pool$SFX
echo "built against $ENG"; sha256sum $ENG/build/libnethack.so $X/replay_sched$SFX $X/replay_pool$SFX
