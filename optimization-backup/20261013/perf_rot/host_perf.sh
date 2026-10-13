#!/bin/bash
# Run on the HOST (pufferbox3) with sudo: attaches perf stat to each rotation run the container starts (process name replay_sched6),
# tags it by its SCHED_A value, and writes the counters next to this script. Stops after 4 runs or 15 minutes.
D=$(cd "$(dirname "$0")" && pwd); PERF=$(command -v perf || ls /usr/lib/linux-tools/*/perf | tail -1)
EV=cycles,instructions,L1-dcache-loads,L1-dcache-load-misses,L1-icache-load-misses,dTLB-loads,dTLB-load-misses,iTLB-load-misses,branch-instructions,branch-misses,LLC-loads,LLC-load-misses
seen=""; n=0; t0=$(date +%s)
while [ $n -lt 4 ] && [ $(( $(date +%s) - t0 )) -lt 900 ]; do
  pid=$(pgrep -f 'replay_sched6 128 1 4096' | head -1)
  if [ -n "$pid" ] && ! echo " $seen " | grep -q " $pid "; then
    tag=$(tr '\0' '\n' < /proc/$pid/environ | grep '^SCHED_A=' | cut -d= -f2); tag=${tag:-unknown}
    sleep 18   # let warm-up (young games) pass; measure the mature window
    echo "attaching to pid $pid (rotation A=$tag) for 40 s"
    $PERF stat -e $EV -p $pid -- sleep 40 > $D/perf_rot$tag.txt 2>&1
    echo "wrote $D/perf_rot$tag.txt"; seen="$seen $pid"; n=$((n+1))
    while kill -0 $pid 2>/dev/null; do sleep 1; done
  else sleep 1; fi
done
echo HOST_PERF_DONE | tee -a $D/host_perf.log
