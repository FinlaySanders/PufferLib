#!/bin/bash
# keep a matching harness pid alive for the perf server: two more rotation-16 runs after the current one ends
D=/puffertank/docker/perf_rot
while ! grep -q ANNOT_ROT16B_DONE $D/annot_rot16b.log 2>/dev/null; do sleep 2; done
for i in 2 3; do cp $D/annot_rot16b.log $D/annot_rot16b.run$((i-1)).log; $D/annot_rot16b.sh; done
