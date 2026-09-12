#!/bin/bash
# Parallel offline derive replay over a recording directory (one nh_derive_replay per file, J at a time); prints the
# merged per-channel mismatch table, divergence counts and the first EX examples per channel.
#   bash derive_replay.sh /tmp/drec            (J=cores, EX=3, OUT=<dir>/replay)
#   BASE=<rates file> ...                       also diff against a saved merged table (from a previous OUT/merged.rates)
S=${S:-/puffertank/pufferlib}; D=${1:?recording dir}; J=${J:-$(nproc)}; EX=${EX:-3}; OUT=${OUT:-$D/replay}
mkdir -p $OUT; rm -f $OUT/*.rates $OUT/*.mis
ls $D/*.drec.gz | xargs -P $J -I{} sh -c 'f={}; b=$(basename $f .drec.gz); '$S'/scripts/nle_stock/nh_derive_replay --examples 50 --out '$OUT'/$b.rates $f > '$OUT'/$b.mis 2>&1'
grep -h '^DERIVE_REPLAY' $OUT/*.mis | awk '{for(i=2;i<=NF;i++){split($i,a,"="); s[a[1]]+=a[2]}} END{printf "DERIVE_REPLAY"; for (k in s) printf " %s=%d", k, s[k]; print ""}'
awk '{b[$1]+=$2; q[$1]+=$3} END{for (c in b) printf "%s %d %d\n", c, b[c], q[c]}' $OUT/*.rates | sort > $OUT/merged.rates
printf "  %-18s %10s %10s %9s\n" channel queries mismatch rate; awk '{printf "  %-18s %10d %10d %8.3f%%\n", $1, $3, $2, 100*$2/($3?$3:1)}' $OUT/merged.rates
grep -h '^DIVERGED' $OUT/*.mis | head -5
for c in $(awk '{print $1}' $OUT/merged.rates); do grep -h "^MIS $c " $OUT/*.mis | head -$EX; done
[ -n "$BASE" ] && join <(sort $BASE) $OUT/merged.rates | awk '{was=$2/($3?$3:1); now=$4/($5?$5:1); if (now>was+1e-4 && $4>$2) {print "WORSE", $1, was*100"% ->", now*100"%"; rc=1} else if (now+1e-4<was) print "BETTER", $1, was*100"% ->", now*100"%"} END{print rc?"REPLAY_REGRESSION":"REPLAY_OK"; exit rc}'
