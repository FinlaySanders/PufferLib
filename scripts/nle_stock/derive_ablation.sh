#!/bin/bash
# Reconstruction ablation on the fork engine (rung 2 without the engine change): the harness runs the fork
# with every hook the env reads wrapped; NH_DERIVE_MODE picks what the policy sees.
#   mode -1  log-only: real observation, no probes                     -> the true reference
#   mode  0  real observation, probes sent, derive computed alongside  -> probe side-effects on the game + mismatch table
#   mode  1  derived observation                                        -> reconstruction + probes
#   mode  1 + NH_DERIVE_REAL=<channel>  everything derived except one   -> the cost of reconstructing that channel
# Same seed and deterministic flags in every arm, so episodes pair. NLE_GETPOS_NORMAL=1 is REQUIRED on the fork:
# without it the fork answers getpos instantly and the farlook probe keys land in the game (2026-09-12 morning: invalid run).
#   local (one GPU, two arms share it, gated on free memory):  EPS=3000 SEED=21 OUT=/tmp/ablate bash derive_ablation.sh
#   box   (one worker per GPU, gated on that GPU being idle):  GPUS="4 6" S=/workspace/pufferlib W=<weights> OUT=... bash derive_ablation.sh
S=${S:-/puffertank/pufferlib}; OUT=${OUT:-/tmp/ablate}; EPS=${EPS:-3000}; SEED=${SEED:-21}; W=${W:-resources/nethack/pkgnle_s406.bin}
GPUS=${GPUS:-"0 0"}   # one worker per entry; repeated entries share a GPU and gate on free memory instead of idleness
CHANNELS=${CHANNELS:-"terrain food_underfoot container_at shop_price inside_shop peaceful_at spells lnc_bits weight capacity intrinsics cast_blocked path engraving_bits hero_tile inv_state inv_true_glyph identity"}
mkdir -p $OUT; cd $S; ulimit -n 65536
Q=$OUT/queue.txt; : > $Q
echo "logonly -1 -" >> $Q; echo "real0 0 -" >> $Q; echo "derived 1 -" >> $Q
for c in $CHANNELS; do echo "keep_$c 1 $c" >> $Q; done
echo "$(date +%T) START ablation eps=$EPS seed=$SEED weights=$W harness=$(md5sum puffer_nethack_harness | cut -c1-12) pufferlib=$(git rev-parse --short HEAD)+$(git status --porcelain | grep -c '^ M')dirty engine=$(git -C vendor/fast-nle rev-parse --short HEAD) arms=$(wc -l < $Q) gpus=[$GPUS]" >> $OUT/log
shared=$([ "$(echo $GPUS | tr ' ' '\n' | sort -u | wc -l)" -lt "$(echo $GPUS | wc -w)" ] && echo 1 || echo 0)
gpu_ok() { if [ $shared = 1 ]; then [ $(( $(nvidia-smi -i $1 --query-gpu=memory.total --format=csv,noheader,nounits) - $(nvidia-smi -i $1 --query-gpu=memory.used --format=csv,noheader,nounits) )) -ge 12500 ]; else [ $(nvidia-smi -i $1 --query-gpu=memory.used --format=csv,noheader,nounits) -lt 100 ]; fi; }
worker() { gpu=$1
  while true; do
    job=$(flock $Q.lock sh -c "head -1 $Q; sed -i 1d $Q"); [ -z "$job" ] && break
    set -- $job; id=$1; mode=$2; real=$3
    until gpu_ok $gpu; do sleep 30; done
    rm -f $OUT/$id.ep
    env NH_NLE_OPTS=1 NLE_GETPOS_NORMAL=1 NETHACKDIR=$S/vendor/fast-nle/build/dat NH_DERIVE_MODE=$mode $( [ "$real" != "-" ] && echo NH_DERIVE_REAL=$real ) \
      NH_STOCK_TERRAIN_PROBE=1 NH_STOCK_STALLCAP=1000000 NH_EPLOG=$OUT/$id.ep CUDA_VISIBLE_DEVICES=$gpu \
      timeout 14400 ./puffer_nethack_harness eval --headless --base.load_model_path=$W --policy.hidden_size=1024 --policy.num_layers=4 \
      --base.eval_agents=512 --base.eval_episodes=$EPS --base.seed=$SEED --base.async=0 --vec.num_buffers=1 > $OUT/$id.out 2> $OUT/$id.err
    rc=$?
    echo "$(date +%T) DONE $id mode=$mode real=$real gpu=$gpu rc=$rc eps=$(wc -l < $OUT/$id.ep) raw_mean=$(python3 $S/scripts/nle_stock/box/analyze.py $OUT/$id.ep 2>/dev/null | grep -oE 'raw mean=[0-9]+ \(se [0-9]+\)') worst_zt_max=$(awk '{if($4>m)m=$4} END{print m+0}' $OUT/$id.ep) $(grep -A30 'DERIVE_HARNESS mode' $OUT/$id.err | awk '$3+0>0 && $4+0>0 {printf "%s=%s ", $1, $4}' | cut -c1-300)" >> $OUT/log
  done
}
first=1; for g in $GPUS; do [ $first = 1 ] || sleep 90; first=0; worker $g & done; wait
echo "$(date +%T) ABLATION_DONE" >> $OUT/log
