#!/bin/bash
# box side: rebuild fork lib, eval binary, stock backend; then start the cert queue
set -e; cd /workspace/PufferLib
cd vendor/fast-nle && cmake --build build -j 16 > /workspace/sweeps/certq/build_lib.log 2>&1; cd /workspace/PufferLib; echo "lib $(md5sum vendor/fast-nle/build/libnethack.so | cut -c1-12)"
./build.sh nethack > /workspace/sweeps/certq/build_env.log 2>&1; ls -la puffer | awk '{print "puffer", $5, $6, $7, $8}'
bash /workspace/nle_stock_src/build_vec_stock_box2.sh > /workspace/sweeps/certq/build_stock.log 2>&1; ls -la puffer_nethack_stock | awk '{print "stock", $5, $6, $7, $8}'; nm -D puffer_nethack_stock | grep -c " T tmt_write"
nohup bash /workspace/sweeps/certq/box_certq.sh > /workspace/sweeps/certq/queue.log 2>&1 &
echo SETUP_DONE
