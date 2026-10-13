#!/bin/bash
# Build PR head and base cleanly: nethack trainer (clones + builds vendor/fast-nle on first use), breakout (GPU env), profile target.
set -o pipefail
log(){ echo "[$(date -u +%T)] $*"; }
cd /puffertank/pr693
log "PR: build nethack (vendor clone + engine build on first run)"; ./build.sh nethack puffer_nethack > build_nethack.log 2>&1; log "PR nethack rc=$?"
log "PR: build breakout"; ./build.sh breakout puffer_breakout > build_breakout.log 2>&1; log "PR breakout rc=$?"
log "PR: build profile target"; ./build.sh nethack --profile > build_profile.log 2>&1; log "PR profile rc=$?"; ls -la profile 2>/dev/null | awk '{print $9,$5}'
cd /puffertank/pr693-base
[ -e vendor/fast-nle ] || ln -s /puffertank/pr693/vendor/fast-nle vendor/fast-nle
log "BASE: build nethack"; ./build.sh nethack puffer_nethack > build_nethack.log 2>&1; log "BASE nethack rc=$?"
log "BASE: build breakout"; ./build.sh breakout puffer_breakout > build_breakout.log 2>&1; log "BASE breakout rc=$?"
log "engine: $(git -C /puffertank/pr693/vendor/fast-nle log --oneline -1 2>/dev/null)"
ls -la /puffertank/pr693/puffer_nethack /puffertank/pr693/puffer_breakout /puffertank/pr693-base/puffer_nethack /puffertank/pr693-base/puffer_breakout 2>&1 | awk '{print $9,$5}'
echo BUILD_ALL_DONE
