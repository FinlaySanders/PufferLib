#!/bin/bash
# Fork-engine certification on weights trained WITH the current observation export
# (pkgnle_s406, 1B, NLE options). Confirms the repo's engine reproduces what the
# box's package tree produced. Standard protocol: 512 agents, 14,000 episodes, all roles.
set -e
cd /puffertank/pufferlib
ulimit -n 65536
C=/tmp/forkcert; mkdir -p $C
W=resources/nethack/pkgnle_s406.bin
for seed in 101 102; do
  id=fork_s$seed
  echo "$(date +%T) START $id weights=pkgnle_s406 engine=$(md5sum vendor/fast-nle/build/libnethack.so | cut -c1-12)" >> $C/log
  NH_MULTI=1 NH_NLE_OPTS=1 NH_EPLOG=$C/$id.ep \
    timeout 43200 ./puffer eval --headless --base.load_model_path=$W \
      --policy.hidden_size=1024 --policy.num_layers=4 \
      --base.eval_agents=512 --base.eval_episodes=14000 --base.seed=$seed \
      > $C/$id.out 2> $C/$id.err
  echo "$(date +%T) DONE $id rc=$? $(tr '\r' '\n' < $C/$id.out | grep -ao 'score=[0-9.]*' | tail -1)" >> $C/log
done
echo "$(date +%T) FORKCERT_DONE" >> $C/log
