#!/bin/bash
ENVS="breakout pong snake squared tetris connect4 drone cartpole asteroids"
for T in /puffertank/pr693 /puffertank/pr693-base; do cd $T; for e in $ENVS; do [ -x puffer_$e ] && { echo "$(basename $T) $e exists"; continue; }; ./build.sh $e puffer_$e > build_$e.log 2>&1; echo "$(basename $T) $e rc=$? $(grep -cE 'error' build_$e.log) errors"; done; done
echo BUILD_ENVS_DONE
