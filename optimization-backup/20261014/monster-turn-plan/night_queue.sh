#!/bin/bash
# after the v1.9 chain: RNG lean arm trainer A/B (non-exact arm; speed only), then an Ir profile of exact vs lean on 8 games (E-core)
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; L=$P/night_queue.log
echo "night queue start $(date -u +%T)" > $L
while ! grep -q STAGEK24_ALL_DONE $P/stage_k24.log; do sleep 20; done; echo "K24 finished $(date -u +%T)" >> $L
rm -f $P/ab_rng_lean.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $P/ab_rng_lean.json > $P/ab_rng_lean.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $L)
grep -E '^DONE' $P/ab_rng_lean.log >> $L
echo "NIGHT_QUEUE_DONE $(date -u +%T)" >> $L
