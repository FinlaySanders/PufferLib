#!/bin/bash
# Reconstruction ablation on the fork engine (rung 2 without the engine change): the harness runs the fork
# with every hook the env reads wrapped; NH_DERIVE_MODE picks what the policy sees.
#   mode -1  log-only: real observation, no probes                     -> the true reference
#   mode  0  real observation, probes sent, derive computed alongside  -> probe side-effects on the game + mismatch table
#   mode  1  derived observation                                        -> reconstruction + probes
#   mode  1 + NH_DERIVE_REAL=<channel>  everything derived except one   -> the cost of reconstructing that channel
# Same seed and deterministic flags in every arm, so episodes pair. Two arms run at a time (~12 GB each).
#   EPS=3000 SEED=21 OUT=/tmp/ablate bash scripts/nle_stock/derive_ablation.sh
S=${S:-/puffertank/pufferlib}; OUT=${OUT:-/tmp/ablate}; EPS=${EPS:-3000}; SEED=${SEED:-21}; W=${W:-resources/nethack/pkgnle_s406.bin}
CHANNELS=${CHANNELS:-"terrain food_underfoot container_at shop_price inside_shop peaceful_at spells lnc_bits weight capacity intrinsics cast_blocked path engraving_bits hero_tile inv_state inv_true_glyph identity"}
mkdir -p $OUT; cd $S; ulimit -n 65536
Q=$OUT/queue.txt; : > $Q
echo "logonly -1 -" >> $Q; echo "real0 0 -" >> $Q; echo "derived 1 -" >> $Q
for c in $CHANNELS; do echo "keep_$c 1 $c" >> $Q; done
echo "$(date +%T) START ablation eps=$EPS seed=$SEED weights=$W harness=$(md5sum puffer_nethack_harness | cut -c1-12) pufferlib=$(git rev-parse --short HEAD)+$(git status --porcelain | grep -c '^ M')dirty engine=$(git -C vendor/fast-nle rev-parse --short HEAD) arms=$(wc -l < $Q)" >> $OUT/log
worker() {
  while true; do
    job=$(flock $Q.lock sh -c "head -1 $Q; sed -i 1d $Q"); [ -z "$job" ] && break
    set -- $job; id=$1; mode=$2; real=$3
    while [ $(( 24564 - $(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits) )) -lt 12500 ]; do sleep 30; done
    rm -f $OUT/$id.ep
    env NH_NLE_OPTS=1 NETHACKDIR=$S/vendor/fast-nle/build/dat NH_DERIVE_MODE=$mode $( [ "$real" != "-" ] && echo NH_DERIVE_REAL=$real ) \
      NH_STOCK_TERRAIN_PROBE=1 NH_STOCK_STALLCAP=1000000 NH_EPLOG=$OUT/$id.ep CUDA_VISIBLE_DEVICES=0 \
      timeout 14400 ./puffer_nethack_harness eval --headless --base.load_model_path=$W --policy.hidden_size=1024 --policy.num_layers=4 \
      --base.eval_agents=512 --base.eval_episodes=$EPS --base.seed=$SEED --base.async=0 --vec.num_buffers=1 > $OUT/$id.out 2> $OUT/$id.err
    rc=$?
    echo "$(date +%T) DONE $id mode=$mode real=$real rc=$rc eps=$(wc -l < $OUT/$id.ep) raw_mean=$(python3 scripts/nle_stock/box/analyze.py $OUT/$id.ep 2>/dev/null | grep -oE 'raw mean=[0-9]+ \(se [0-9]+\)') worst_zt_max=$(awk '{if($4>m)m=$4} END{print m+0}' $OUT/$id.ep) $(grep -A30 'DERIVE_HARNESS mode' $OUT/$id.err | awk '$3+0>0 && $4+0>0 {printf "%s=%s ", $1, $4}' | cut -c1-300)" >> $OUT/log
  done
}
worker & sleep 90; worker & wait
echo "$(date +%T) ABLATION_DONE" >> $OUT/log
