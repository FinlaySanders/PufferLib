#!/bin/bash
# Article figure renderers: resources/article/bars (the bar chart) and resources/article/results (extra figures)
cd "$(dirname "$0")/../.."
python3 resources/article/gen_data.py > /dev/null || exit 1
FLAGS=(-O2 -I. -I./raylib-5.5_linux_amd64/include -I./src -I./vendor -Iresources)
LIBS=(raylib-5.5_linux_amd64/lib/libraylib.a -lGL -lm -lpthread -DPLATFORM_DESKTOP)
${CC:-clang} "${FLAGS[@]}" resources/article/bars.c resources/trailer/fonts.c -o resources/article/bars "${LIBS[@]}" && echo "Built: resources/article/bars"
${CC:-clang} "${FLAGS[@]}" resources/article/viz.c resources/trailer/fonts.c -o resources/article/viz "${LIBS[@]}" && echo "Built: resources/article/viz"
${CC:-clang} "${FLAGS[@]}" resources/article/results.c resources/trailer/fonts.c -o resources/article/results "${LIBS[@]}" && echo "Built: resources/article/results"
