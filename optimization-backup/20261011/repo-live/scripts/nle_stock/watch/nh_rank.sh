#!/bin/bash
# nh_rank.sh <eplog> [min_score=0] -> episodes by max_depth then score; cols: env ep score how time role race gend max_depth last_turn
awk -v m="${2:-0}" '$3>=m' "$1" | sort -k9,9nr -k3,3nr | head -${3:-15} | \
  awk '{printf "env=%-3s ep=%-3s depth=%-3s score=%-7s how=%s last_turn=%s\n",$1,$2,$9,$3,$4,$10}'
