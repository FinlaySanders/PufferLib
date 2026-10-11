#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
clang -O2 -I. -I./raylib-5.5_linux_amd64/include -I./src -I./vendor -Iresources resources/article/message_encoder.c resources/trailer/fonts.c -o resources/article/message_encoder raylib-5.5_linux_amd64/lib/libraylib.a -lGL -lm -lpthread -DPLATFORM_DESKTOP
xvfb-run -a -s '-screen 0 1800x1020x24' resources/article/message_encoder
