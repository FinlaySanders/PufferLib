#!/bin/bash
# EQUIVALENCE RUN on the one tree (/workspace/pufferlib, branch nle-stock, engine per ENGINE.txt).
# The same weights evaluated three ways on the same code:
#   rung 1  fork engine, training interface        ./puffer eval, NH_NLE_OPTS=1
#   rung 3  untouched stock, challenge configuration ./puffer_nethack_stock, STRICT + NLE literal options
#   rung 4  real NetHackChallenge-v0 in Python        nhc_agent.py (reset/step only), CPU policy
# The goal is rung 1 == rung 4 within noise; rung 3 is the fast proxy for rung 4 (proven deterministic-
# equivalent to it under a frozen clock). Every line logs the git SHAs and binary md5s it ran on.
#
#   T=/workspace/pufferlib LANE=pkgnle_s406 G1="4 6" G3="0 7" W4=32 K4=20 bash box_equiv.sh
# G1/G3 = GPUs for the two rung-1 / rung-3 arms (seeds 7,11 / 21,32); W4 x K4 = python workers x episodes.
# Any of R1/R3/R4 can be set to 0 to skip that rung.
T=${T:-/workspace/pufferlib}; C=${C:-/workspace/sweeps/certq/equiv}; L=$C/equiv.log
LANE=${LANE:-pkgnle_s406}; PY=${PY:-/workspace/nle-venv/bin/python}
R1=${R1:-1}; R3=${R3:-1}; R4=${R4:-1}; G1=${G1:-"4 6"}; G3=${G3:-"0 7"}; W4=${W4:-32}; K4=${K4:-20}
STOCK=${STOCK:-/workspace/nle-stock/build}
OPTS='autopickup,color,disclose:+i +a +v +g +c +o,mention_walls,nobones,nocmdassist,nolegacy,nosparkle,pickup_burden:unencumbered,pickup_types:$?!/,runmode:teleport,showexp,showscore,time,name:Agent-@,race:random,gender:random,align:random'
mkdir -p $C; cd $T; ulimit -n 65536
W=$(ls -1 /workspace/sweeps/nh/checkpoints/nethack/$LANE/*.bin | sort | tail -1)
SHA="pufferlib=$(git rev-parse --short HEAD)+$(git status --porcelain | grep -c '^ M')dirty engine=$(git -C vendor/fast-nle rev-parse --short HEAD)+$(git -C vendor/fast-nle status --porcelain | grep -c '^ M')dirty lib=$(md5sum vendor/fast-nle/build/libnethack.so | cut -c1-12) puffer=$(md5sum puffer | cut -c1-12) stock=$(md5sum puffer_nethack_stock | cut -c1-12) libnhagent=$(md5sum scripts/nle_stock/libnhagent.so | cut -c1-12) stocklib=$(md5sum $STOCK/libnethack.so | cut -c1-12) weights=$(basename $W)/$(md5sum $W | cut -c1-12)"
echo "$(date +%T) START equiv lane=$LANE $SHA" >> $L
A="eval --headless --base.load_model_path=$W --policy.hidden_size=1024 --policy.num_layers=4 --base.eval_agents=512"
rung1() { gpu=$1; seed=$2; id=r1_${LANE}_s$seed; rm -f $C/$id.ep
  NH_NLE_OPTS=1 NETHACKDIR=$T/vendor/fast-nle/build/dat NH_EPLOG=$C/$id.ep CUDA_VISIBLE_DEVICES=$gpu \
    timeout 14400 ./puffer $A --base.eval_episodes=14000 --base.seed=$seed > $C/$id.out 2> $C/$id.err
  rc=$?
  echo "$(date +%T) DONE $id rc=$rc nleopts=$(grep -ac 'NH_NLE_OPTS active' $C/$id.err) $(python3 scripts/nle_stock/box/analyze.py $C/$id.ep 2>&1 | tail -1 | cut -c1-170)" >> $L; }
rung3() { gpu=$1; seed=$2; id=r3_${LANE}_s$seed; rm -f $C/$id.ep
  NH_STOCK_STRICT=1 NH_STOCK_LITERALOPTS="$OPTS" NH_STOCK_NOSDESC=1 NH_STOCK_NOREDRAW=1 NH_STOCK_STOCKSORT=1 \
  NH_STOCK_NODARKFIX=1 NH_STOCK_NOTOPL=1 NH_STOCK_REALCLOCK=1 NH_STOCK_TERRAIN_PROBE=1 NH_STOCK_STALLCAP=1000000 \
  NETHACKDIR=$STOCK/nethackdir NLE_STOCK_LIB=$STOCK/libnethack.so NH_EPLOG=$C/$id.ep CUDA_VISIBLE_DEVICES=$gpu \
    timeout 43200 ./puffer_nethack_stock $A --base.eval_episodes=10000 --base.seed=$seed > $C/$id.out 2> $C/$id.err
  rc=$?
  echo "$(date +%T) DONE $id rc=$rc aborted=$(grep -ac 'aborted=1' $C/$id.err) $(python3 scripts/nle_stock/box/analyze.py $C/$id.ep 2>&1 | tail -1 | cut -c1-170)" >> $L; }
rung4() { d=$C/r4_${LANE}; mkdir -p $d; rm -f $d/*.jsonl $d/*.log
  for i in $(seq 1 $W4); do $PY scripts/nle_stock/nhc_agent.py --episodes $K4 --weights $W --out $d/w$i.jsonl > $d/w$i.log 2>&1 & done; wait
  echo "$(date +%T) DONE r4_${LANE} $W4x$K4 $($PY scripts/nle_stock/gym_analyze.py $d 2>&1 | grep -E 'EQUAL-K|episode 1 median|end status' | tr '\n' ' ' | cut -c1-230)" >> $L; }
set -- $G1; g1a=$1; g1b=$2; set -- $G3; g3a=$1; g3b=$2
[ "$R1" = 1 ] && { rung1 $g1a 7 & rung1 $g1b 11 & }
[ "$R3" = 1 ] && { rung3 $g3a 21 & rung3 $g3b 32 & }
[ "$R4" = 1 ] && { rung4 & }
wait; echo "$(date +%T) EQUIV_DONE lane=$LANE" >> $L
