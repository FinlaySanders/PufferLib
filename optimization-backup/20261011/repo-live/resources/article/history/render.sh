#!/bin/bash
set -e
cd "$(dirname "$0")/../../.."
clang -O2 -I. -I./raylib-5.5_linux_amd64/include -I./src -I./vendor -Iresources resources/article/history.c resources/trailer/fonts.c -o resources/article/history_chart raylib-5.5_linux_amd64/lib/libraylib.a -lGL -lm -lpthread -DPLATFORM_DESKTOP
xvfb-run -a resources/article/history_chart
