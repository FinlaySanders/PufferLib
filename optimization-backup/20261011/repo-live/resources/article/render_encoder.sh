#!/bin/bash
set -e
cd "$(dirname "$0")/../.."
clang -O2 -I. -I./raylib-5.5_linux_amd64/include -I./src -I./vendor -Iresources resources/article/encoder.c resources/trailer/fonts.c -o resources/article/encoder raylib-5.5_linux_amd64/lib/libraylib.a -lGL -lm -lpthread -DPLATFORM_DESKTOP
xvfb-run -a -s '-screen 0 2100x1500x24' resources/article/encoder
