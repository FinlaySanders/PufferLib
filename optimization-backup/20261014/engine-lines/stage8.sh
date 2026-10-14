#!/bin/bash
# Stage 8 (after stage 7): gate the fast-nle backup worktree source with the landed A+D commit (LTO build, no PGO): quick gates + full corpus.
N=/puffertank/experiments/nethack-engine-lines-20261014; C=/puffertank/experiments/nethack-compact-state-20261008; F=/puffertank/optimization-backup-20261008/fast-nle
L=$N/stage8.log; echo "stage8 waiting $(date -u +%T)" > $L
while ! grep -q STAGE7_DONE $N/stage7.log 2>/dev/null; do sleep 15; done
d=$N/engines/fastnle_check; rm -rf $d; mkdir -p $d; rsync -a --exclude .git $F/ $d/source/
F2="-fno-semantic-interposition"; cmake -S $d/source -B $d/build -DCMAKE_BUILD_TYPE=Release -DNLE_TLS_INITIAL_EXEC=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON "-DCMAKE_C_FLAGS=$F2" "-DCMAKE_CXX_FLAGS=$F2" -DFETCHCONTENT_SOURCE_DIR_BZIP2=/puffertank/pufferlib/vendor/fast-nle/build/_deps/bzip2-src -DFETCHCONTENT_SOURCE_DIR_DEBOOST_CONTEXT=/puffertank/pufferlib/vendor/fast-nle/build/_deps/deboost_context-src -DFETCHCONTENT_SOURCE_DIR_PYBIND11=/puffertank/pufferlib/vendor/fast-nle/build/_deps/pybind11-src > $d/configure.log 2>&1 && cmake --build $d/build --target nethack -j8 > $d/build.log 2>&1; echo "fastnle_check build rc=$? (commit $(cd $F && git log --oneline -1 | cut -c1-9))" >> $L
ln -sfn $d $C/engines/lines_fastnle_check
(cd $C && timeout 3600 python3 check.py lines_fastnle_check > $N/gates_full_fastnle_check.log 2>&1; echo "fastnle_check gates rc=$? $(grep -c PASS $N/gates_full_fastnle_check.log) passes $(grep -E 'HASHES' $N/gates_full_fastnle_check.log | tail -1) $(date -u +%T)" >> $L)
echo "STAGE8_DONE $(date -u +%T)" >> $L
