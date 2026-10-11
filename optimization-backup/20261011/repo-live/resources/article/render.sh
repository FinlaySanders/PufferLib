#!/bin/bash
# Render the article bar chart(s) -> resources/article/out/bars_<metric>_<interface>.png
# usage: render.sh [--metric median|mean] [--interface gym|fork|stock]   (default: both metrics on the challenge interface)
cd "$(dirname "$0")/../.."
resources/article/build.sh || exit 1
X=(xvfb-run -a -s "-screen 0 1920x1080x24 +extension GLX +render -noreset")
if [ $# -gt 0 ]; then "${X[@]}" resources/article/bars "$@" --shot resources/article/out
else "${X[@]}" resources/article/bars --metric median --shot resources/article/out
     "${X[@]}" resources/article/bars --metric mean --shot resources/article/out
     for f in roles roles_depth gap; do for m in median mean; do "${X[@]}" resources/article/viz --fig $f --metric $m --shot resources/article/out; done; done
     "${X[@]}" resources/article/viz --fig depth --shot resources/article/out
     "${X[@]}" resources/article/viz --fig tradeoff --shot resources/article/out; fi

python3 resources/article/webify.py
