#!/bin/bash
cd /workspace/PufferLib; R=/workspace/sweeps/certq/results.log; ulimit -n 65536
cd vendor/fast-nle && cmake --build build -j 16 > /workspace/sweeps/certq/build_lib2.log 2>&1; cd /workspace/PufferLib; echo "$(date +%T) lib rebuilt $(md5sum vendor/fast-nle/build/libnethack.so | cut -c1-12) (gem switch)" >> $R
cp ocean/nethack/netlib.h /tmp/netlib.h.keep; sed -i 's/pickup_burden:unencumbered,pile_limit:0,/pickup_burden:unencumbered,/' ocean/nethack/netlib.h; ./build.sh nethack > /workspace/sweeps/certq/build_env_nopile.log 2>&1 && cp puffer /workspace/sweeps/certq/puffer_nopile; cp /tmp/netlib.h.keep ocean/nethack/netlib.h
CH=/workspace/PufferLib/resources/nethack/nethack_t1122_2B_weights.bin
A="eval --headless --base.load_model_path=$CH --policy.hidden_size=1024 --policy.num_layers=4 --base.eval_agents=512 --base.eval_episodes=14000 --base.seed=7"
run() { id=$1; gpu=$2; shift 2; rm -f /workspace/sweeps/certq/$id.ep; echo "$(date +%T) START $id gpu$gpu" >> $R; env "$@" NETHACKDIR=/workspace/PufferLib/vendor/fast-nle/build/dat NH_EPLOG=/workspace/sweeps/certq/$id.ep CUDA_VISIBLE_DEVICES=$gpu timeout 14400 ${BIN:-./puffer} $A > /workspace/sweeps/certq/$id.out 2> /workspace/sweeps/certq/$id.err; echo "$(date +%T) DONE $id rc=$? $(python3 /workspace/sweeps/certq/analyze.py /workspace/sweeps/certq/$id.ep 2>&1 | cut -c1-160)" >> $R; }
run gemtrue2b_s7 0 NLE_GEM_TRUE=1 NLE_ABL=15 &
run gemtrue2b_s11 1 NLE_GEM_TRUE=1 NLE_ABL=15 &
BIN=/workspace/sweeps/certq/puffer_nopile run nopile2b_s7 2 NLE_ABL=15 &
run pubbase2b_s11 4 NLE_GEM_TRUE=1 NLE_ABL=7 &
wait; echo "$(date +%T) ATTR2_DONE" >> $R
