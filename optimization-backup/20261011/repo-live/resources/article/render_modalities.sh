#!/bin/bash
set -e
cd "$(dirname "$0")/../.."
python3 resources/article/modalities/prepare.py
clang -O2 -I. -I./raylib-5.5_linux_amd64/include -I./src -I./vendor -Iresources resources/article/modalities.c resources/trailer/fonts.c -o resources/article/modalities_render raylib-5.5_linux_amd64/lib/libraylib.a -lGL -lm -lpthread -DPLATFORM_DESKTOP
xvfb-run -a -s '-screen 0 2200x1500x24' resources/article/modalities_render
