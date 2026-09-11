#!/bin/bash
# Certification of the CHALLENGE interface on the stock C backend.
#
# The binding and this backend were shown bit-identical under a pinned configuration,
# so this measures what NetHackChallenge-v0 would produce, at ~45x the throughput of
# driving the gym env from Python. Every deviation the challenge could not reproduce
# is switched off here:
#   STRICT      1e6 step cap + 10,000 no-progress abort, probes charged to both
#   LITERALOPTS NLE's exact option string (no rc file, no !status_updates, name:Agent-@)
#   NOSDESC     no screen_descriptions / raw terminal stream
#   NOREDRAW    no print_glyph hook, so the derive gets no `redrawn` hints
#   STOCKSORT   stock's own room ordering, not the fork-matching total order
#   NODARKFIX   no dark_room poke during probes
#   NOTOPL      no engine top-line restore across a probe group
#   REALCLOCK   the challenge does not fake time()/localtime()
#   (NH_STOCK_CLEAREOS deliberately NOT set: the challenge cannot inject it)
T=/workspace/PufferLib_pkg
C=/workspace/sweeps/certq/chal
L=/workspace/sweeps/certq/chalcert.log
W=/workspace/sweeps/nh/checkpoints/nethack/pkgnle_s406/0000000999817216.bin
OPTS='autopickup,color,disclose:+i +a +v +g +c +o,mention_walls,nobones,nocmdassist,nolegacy,nosparkle,pickup_burden:unencumbered,pickup_types:$?!/,runmode:teleport,showexp,showscore,time,name:Agent-@,race:random,gender:random,align:random'
mkdir -p $C; cd $T
ulimit -n 65536   # 512 envs each dlopen a private memfd copy; the default 1024 is not enough
ARGS="eval --headless --base.load_model_path=$W --policy.hidden_size=1024 --policy.num_layers=4 --base.eval_agents=512 --base.eval_episodes=10000"

arm() { # gpu seed clockmode
  gpu=$1; seed=$2; clk=$3; id=chal_s${seed}_${clk}
  echo "$(date +%T) gpu$gpu START $id  binary=$(md5sum $T/puffer_nethack_stock | cut -c1-12) clock=$clk" >> $L
  if [ "$clk" = "real" ]; then export NH_STOCK_REALCLOCK=1; else unset NH_STOCK_REALCLOCK; fi
  NH_STOCK_STRICT=1 \
  NH_STOCK_LITERALOPTS="$OPTS" \
  NH_STOCK_NOSDESC=1 NH_STOCK_NOREDRAW=1 NH_STOCK_STOCKSORT=1 \
  NH_STOCK_NODARKFIX=1 NH_STOCK_NOTOPL=1 \
  NH_STOCK_TERRAIN_PROBE=1 NH_STOCK_STALLCAP=1000000 \
  NETHACKDIR=/workspace/nle-stock/build/nethackdir \
  NLE_STOCK_LIB=/workspace/nle-stock/build/libnethack.so \
  NH_EPLOG=$C/$id.ep CUDA_VISIBLE_DEVICES=$gpu \
    timeout 86400 ./puffer_nethack_stock $ARGS > $C/$id.out 2> $C/$id.err
  echo "$(date +%T) gpu$gpu DONE $id rc=$? $(python3 /workspace/sweeps/certq/analyze.py $C/$id.ep 2>/dev/null || echo "eps=$(wc -l < $C/$id.ep)")" >> $L
}
arm 0 21 real &
arm 4 22 real &
arm 6 23 real &
arm 7 24 fake &
wait
echo "$(date +%T) CHALCERT_DONE" >> $L
