#!/bin/bash
# Container side: line-level annotation of the hot functions from a host perf record. Usage: annotate.sh <tag> [symfs]
# symfs = directory holding the debug-symbol twin at <symfs>/puffertank/.../tile_signed_pgo/build/libnethack.so (same code, + -g)
D=/puffertank/docker/perf_rot; PERF=/usr/lib/linux-tools/7.0.0-29-generic/perf; TAG=$1; SYMFS=${2:-}
[ -n "$SYMFS" ] && SF="--symfs $SYMFS" || SF=""
for ev in cycles:u branch-misses:u; do n=$(echo $ev | tr ':/' '__')
  $PERF report -i $D/results/$TAG.data --stdio --no-children --sort sym -n --percent-limit 0.5 --event $ev $SF > $D/results/$TAG.$n.sym.txt 2>&1
  for s in m_move mfndpos_masked.lto_priv.0 nethack_pack_obs movemon nh_fobj_next dochug; do
    $PERF annotate -i $D/results/$TAG.data --stdio --event $ev $SF -s "$s" --percent-type local-period > $D/results/$TAG.$n.annot.$s.txt 2>&1
  done
done
echo ANNOTATE_DONE $TAG
