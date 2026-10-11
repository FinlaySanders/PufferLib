#!/bin/bash
# Per-thread CPU utilisation of a process over a window: thread_util.sh <pid> <t_start_s> <t_end_s>  (sleeps are the window, run in background)
P=$1; T1=$2; T2=$3; TCK=$(getconf CLK_TCK)
snap() { for t in /proc/$P/task/*; do [ -r $t/stat ] || continue; awk -v tid=$(basename $t) '{print tid, $14+$15}' $t/stat; done; }
sleep $T1; A=$(snap); W0=$(date +%s.%N); sleep $((T2-T1)); B=$(snap); W1=$(date +%s.%N)
join <(echo "$A" | sort) <(echo "$B" | sort) | awk -v w0=$W0 -v w1=$W1 -v tck=$TCK '{w=w1-w0; u=($3-$2)/tck/w; printf "%d %.3f\n",$1,u}' | sort -k2 -rn > /tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad/thread_util_$P.txt
awk '{n++; s+=$2; if($2>0.9)h++; else if($2>0.5)m++; else l++} END{printf "threads=%d sum_util=%.1f cores  >90%%:%d  50-90%%:%d  <50%%:%d\n",n,s,h,m,l}' /tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad/thread_util_$P.txt
echo "top/bottom:"; head -3 /tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad/thread_util_$P.txt; echo ...; sed -n '30,40p' /tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad/thread_util_$P.txt
