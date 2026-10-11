#!/bin/bash
# nh_find.sh <eplog> [eval_agents=64] [eval_episodes=150] [seed=73] [actdir=<eplog>.acts]
# headless vec eval; per-episode log: env ep score how time role race gend max_depth last_turn steps act_off
cd /puffertank/pufferlib; ulimit -n 8192
EP="$1"; AG="${2:-64}"; N="${3:-150}"; SEED="${4:-73}"; ACT="${5:-$1.acts}"
NH_EPLOG="$EP" NH_ACTLOG="$ACT" ./puffer_find eval --headless --base.load_model_path=resources/nethack/fixwt4b_s705.bin \
  --policy.hidden_size=1024 --policy.num_layers=4 --base.eval_agents=$AG --base.eval_episodes=$N \
  --base.seed=$SEED --vec.num_buffers=1 --base.async=0
