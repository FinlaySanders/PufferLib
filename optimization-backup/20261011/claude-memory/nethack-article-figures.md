---
name: nethack-article-figures
description: 2026-09-13 article results figures (raylib, constellation style) - resources/article/ render pipeline, data provenance, headless GL gotchas
metadata:
  type: project
---

Article figures for the NetHack claim live in `resources/article/` (untracked): `gen_data.py` (certified .ep logs in
/tmp/reg/article/ep -> results_data.h + results.csv/json; burn-in protocol drop 4000 keep 10000, reproduces the drone
certs exactly), `results.c` (raylib, 1920x1080, constellation palette 6/24/24 bg, cyan/green/white + orange AutoAscend
reference, JetBrains Mono SemiBold via trailer/fonts.c), `build.sh`, `render.sh` (build + xvfb-run --shot ->
`resources/article/out/fig_{median_vs_steps,mean_vs_steps,results_table,score_cdf}.png`). Images only - user does not
want mp4s (ffmpeg 6.1.1 is installed anyway). FINAL DELIVERABLE (user: 'something much simpler'): `bars.c` -> `render.sh`
-> out/bars_median_gym.png + bars_mean_gym.png (AutoAscend bar, then 1B/2B/4B; `--interface fork|stock` variants). Added viz.c (common.h shared helpers): roles_{median,mean}.png = per-role grouped 1B/2B/4B bars from the fork logs (ROLE_*
arrays in results_data.h, NetHack role order Arc..Wiz, ~1,535 games/role/size); gap_{median,mean}.png = fork vs stock vs
gym per size with % gap vs fork. depth_vs_score.png (viz --fig depth): 4B fork 20K games, dot per game (8K subsample) at deepest level, per-depth
median+IQR, share per depth; medians rise with depth (3.3K@1 -> 12K@3 -> 25-45K@8-11), best 385,778 @Dlvl 7, Dlvl>=10 = 1.3%,
max Dlvl 15. score_up_depth_down.png (viz --fig tradeoff): two panels, median score rising 9,098/10,084/11,225 while games reaching
Dlvl8+ fall 9.6/7.2/4.8% (avg deepest level 3.91/3.63/3.55, turns 26K->31K) - training makes play shallower and longer;
same trend on stock NLE. render.sh renders all eight, then webify.py writes out/web/ (1600x900 PNG-8 ~35-45 KB + JPEG q90) - user's X article
loaded the 1920x1080 PNG-24s slowly; use web/ for uploads. Section draft: resources/article/lets_talk_score.md. The four
earlier figures are parked in out/extra/. Caveat: challenge-interface 1B (9,591, 480 games) > 2B (9,495, 960 games); fork
medians (20K games) are monotonic 9,098/10,084/11,226.

**Why:** user asked for results tables/comparisons vs AutoAscend at 1B/2B/4B in the constellation/trailer house style.
Numbers: pooled per size x interface (fork / stock NLE / NetHackChallenge-v0) - 4B challenge 8,064 games median 11,508
mean 19,705 = 2.16x AutoAscend 2021 median 5,336 (2023 re-eval 4,918 / mean 8,556).

**How to apply / gotchas:** raylib.h defines WHITE/GREEN/ORANGE etc. as Color macros - prefix own colour constants
(C_WHITE). The box's DISPLAY=:92 has no GLX fbconfigs; render under `xvfb-run -a -s "-screen 0 1920x1080x24 +extension
GLX +render -noreset"`. Standalone raylib compile line = `clang -O2 -I. -Iraylib-5.5_linux_amd64/include -Isrc -Ivendor
-Iresources <src> resources/trailer/fonts.c libraylib.a -lGL -lm -lpthread -DPLATFORM_DESKTOP`. Related:
[[nethack-cert-ledger]], [[nethack-handoff-2026-09-12]].

**Gym pooling (2026-09-13 18:00):** gen_data.py now computes NetHackChallenge-v0 stats from per-game records
(/tmp/reg/article/gym/r4_<lane>_4k/w*.jsonl, field env_score; fetch from drone /workspace/sweeps/certq/equiv) when present -
true pooled 4B median 11,516 (avg-of-medians gave 11,508); falls back to run summaries otherwise. Fetch the 1B/2B jsonl when
GYM4K_12B_DONE lands, rerun render.sh, re-copy to /puffertank/docker/nethack_article.

## Update 2026-09-13 21:05
- All figures regenerated after the 2B gym certs landed (gen_data.py gate now passes). Current PNGs = final certified numbers.
- CORRECTION: `resources/article/data/constellation_nethack_curves.ini` had vec/total_agents=4096; the fixwt lanes actually ran `--vec.total_agents=512 --vec.num_threads=24 --policy.hidden_size=1024 --policy.num_layers=4` (nh_fixwt.sh ARGS on drone). Fixed to 512 and re-staged.
- Speed facts measured for the "Making NetHack Faster" section (2026-09-13, pufferbox3 i9-14900K 24c/32t + RTX 4090, shipped config 512 agents, hidden 1024 x4): train bench 40M steps `./puffer_bench train --headless` = **112.8K SPS median over 152 epochs** (flat); eval pair same binary/weights (fixwt4b_s705) 512 agents seed 21, 4 min each: fork 26.7M steps (~112K/s) vs stock backend (LD_LIBRARY_PATH=vendor/fast-nle/stock/build, NLE_STOCK_LIB=/puffertank/nle-stock/nle/libnethack.so, NETHACKDIR=/puffertank/nle-stock/nle/nethackdir) 4.5M steps (~19K/s) = **5.9x**. Script /tmp/reg/article/pair_eval.sh, outputs /tmp/reg/article/pair/. Gym 4B games: 64,632 keys/game of which 54,105 probes = **84%**, ~5 probe keys per policy action. Fork: 42 commits on upstream 2319f298, 196 engine C files +8,018/−3,170, 471 globals migrated, 38 whitelisted, 34 goldens. Do NOT quote the July 328–333K SPS numbers (hidden-128 config).
