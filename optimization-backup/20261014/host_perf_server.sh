#!/bin/bash
# HOST side (pufferbox3, run with sudo, leave running overnight, e.g. in tmux):  sudo bash ~/puffertank/perf_rot/host_perf_server.sh
# Serves perf requests written by the container into requests/: each NNN_<tag>.req has lines PATTERN=<pgrep -f regex> MODE=stat|topdown|record
# EVENTS=<list> DURATION=<s> DELAY=<s>. Waits for a matching pid, attaches perf for DURATION, writes results/<tag>.txt (+ .report.txt for record).
D=$(cd "$(dirname "$0")" && pwd); PERF=$(command -v perf || ls /usr/lib/linux-tools/*/perf | tail -1); mkdir -p $D/results $D/done
end=$(( $(date +%s) + 12*3600 )); echo "server start $(date -u +%T) perf=$PERF" >> $D/server.log
while [ $(date +%s) -lt $end ]; do
  date +%s > $D/daemon_alive
  req=$(ls $D/requests/*.req 2>/dev/null | sort | head -1)
  if [ -z "$req" ]; then sleep 2; continue; fi
  unset PATTERN MODE EVENTS DURATION DELAY TAG; source "$req"; TAG=$(basename "$req" .req | sed 's/^[0-9]*_//')
  pid=""; t0=$(date +%s); while [ -z "$pid" ] && [ $(( $(date +%s)-t0 )) -lt 600 ]; do pid=$(pgrep -f "$PATTERN" | head -1); [ -z "$pid" ] && sleep 1; done
  if [ -z "$pid" ]; then echo "$TAG: no pid for PATTERN=$PATTERN" > $D/results/$TAG.txt; mv "$req" $D/done/; continue; fi
  sleep ${DELAY:-10}
  echo "[$(date -u +%T)] $TAG pid=$pid mode=$MODE" >> $D/server.log
  case $MODE in
    topdown) $PERF stat --topdown -p $pid -- sleep ${DURATION:-40} > $D/results/$TAG.txt 2>&1 ;;
    record)  EVS=""; for e in $(echo ${EVENTS:-cycles:u} | tr ',' ' '); do EVS="$EVS -e $e"; done
             $PERF record $EVS -F 1999 -p $pid -o $D/results/$TAG.data -- sleep ${DURATION:-30} > $D/results/$TAG.txt 2>&1
             for e in $(echo ${EVENTS:-cycles:u} | tr ',' ' '); do n=$(echo $e | tr ':/' '__')
               $PERF report -i $D/results/$TAG.data --stdio --no-children --sort dso,sym -n --percent-limit 0.3 --event $e > $D/results/$TAG.$n.report.txt 2>&1
               $PERF report -i $D/results/$TAG.data --stdio --no-children --sort dso,sym -n --percent-limit 0.3 --event $e --symfs $D/symfs > $D/results/$TAG.$n.report_symfs.txt 2>&1; done ;;
    *)       $PERF stat -e $EVENTS -p $pid -- sleep ${DURATION:-40} > $D/results/$TAG.txt 2>&1 ;;
  esac
  mv "$req" $D/done/
done
echo HOST_SERVER_EXIT $(date -u +%T) >> $D/server.log
