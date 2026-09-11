#!/bin/bash
set -e
T=/workspace/PufferLib_pkg; L=/workspace/sweeps/nh/long.log; C=/workspace/sweeps/certq
# LANDMINE: an rsync-copied fast-nle build dir keeps CMAKE_HOME_DIRECTORY pointing at the ORIGINAL tree, so
# `cmake --build` there silently compiles the original sources. Configure fresh.
cd $T/vendor/fast-nle && rm -rf build && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release > $C/pkg_cmake.log 2>&1
cmake --build build -j 16 > $C/pkg_lib.log 2>&1
echo "$(date +%T) pkg lib $(md5sum $T/vendor/fast-nle/build/libnethack.so | cut -c1-12)" >> $L
cd $T && ./build.sh nethack > $C/pkg_env.log 2>&1
echo "$(date +%T) pkg puffer $(md5sum $T/puffer | cut -c1-12)" >> $L
# stock backend with the CURRENT derive, for the certs
sed -e "s#^cd /workspace/PufferLib\$#cd $T#" -e "s#-o puffer_nethack_stock #-o puffer_nethack_stock #" /workspace/nle_stock_src/build_vec_stock_box2.sh > /workspace/nle_stock_src/build_pkg_stock.sh
bash /workspace/nle_stock_src/build_pkg_stock.sh > $C/pkg_stock.log 2>&1
echo "$(date +%T) pkg stock backend $(md5sum $T/puffer_nethack_stock | cut -c1-12)" >> $L
echo PKG_BUILD_OK >> $L
