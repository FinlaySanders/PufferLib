#!/bin/bash
# nh_replay.sh <eplog> <env> <ep> [ms=40] [actdir=<eplog>.acts]
# Instant replay of one recorded eval episode in the C demo view (no policy/GPU). ms=0: verify only.
# Prints FAITHFUL/MISMATCH by comparing the replay's own episode line (score..steps) with the find line.
cd /puffertank/pufferlib
EP="$1"; E="$2"; K="$3"; MS="${4:-40}"; ACT="${5:-$1.acts}"
line=$(awk -v e="$E" -v k="$K" '$1==e && $2==k' "$EP"); [ -z "$line" ] && { echo "no episode env=$E ep=$K in $EP" >&2; exit 1; }
set -- $line; echo "episode: env=$1 ep=$2 score=$3 max_depth=$9 steps=${11}" >&2
chk=$(mktemp)
NH_EPLOG="$chk" NH_MULTI=1 NH_REPLAY_DIR="$ACT" NH_REPLAY_ENV="$E" NH_REPLAY_EP="$K" NH_REPLAY_OFF="${12}" NH_REPLAY_N="${11}" ./nethack 1 "$MS"
if [ "$(cut -d' ' -f1-11 "$chk")" = "$(echo "$line" | cut -d' ' -f1-11)" ]; then echo "replay FAITHFUL: $(cut -d' ' -f1-11 "$chk")" >&2
else echo "replay MISMATCH: got '$(cat "$chk")' want '$line'" >&2; fi
rm -f "$chk"
