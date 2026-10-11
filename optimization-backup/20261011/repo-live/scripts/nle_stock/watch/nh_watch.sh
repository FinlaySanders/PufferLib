#!/bin/bash
# nh_watch.sh <env_idx> <episode> [ms=40] [eval_agents=64] [seed=73]
# replays the identical deterministic eval and draws only that (env, episode), exits when it ends
cd /puffertank/pufferlib
ENV="$1"; EPI="$2"; MS="${3:-40}"; AG="${4:-64}"; SEED="${5:-73}"
NH_WATCH_ENV=$ENV NH_WATCH_EP=$EPI NH_WATCH_MS=$MS NH_WATCH_STOP=1 ./puffer_find eval --headless \
  --base.load_model_path=resources/nethack/fixwt4b_s705.bin --policy.hidden_size=1024 --policy.num_layers=4 \
  --base.eval_agents=$AG --base.eval_episodes=1000000 --base.seed=$SEED --vec.num_buffers=1 --base.async=0
