---
name: constellation-web-build
description: "How to rebuild a Constellation sweep page for the web from a box's result inis (cache_data + emcc recipe) and the shader-preload gotcha that makes the page render blank"
metadata: 
  node_type: memory
  type: reference
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-09-04T22:02:07.605Z
---

Recipe (2026-09-04, verified for NetHack + drone sweeps):
1. Pull the box's `logs/<env>/sweep_*.ini` (base64 tar over ssh; the vast banner breaks rsync/scp streams).
2. `mkdir -p $D/logs/<env> $D/resources/constellation`, copy the inis in, `cd $D && /puffertank/pufferlib/cache_data --full`
   -> writes `$D/resources/constellation/experiments.ini` (scans `logs/` relative to cwd; the dir must pre-exist).
3. COPY THE SHADERS: `cp resources/constellation/{blur,point_particle}_*.{vs,fs} resources/constellation/puffer.rgs $D/resources/constellation/`.
   The web build preloads that whole dir; without the shaders the page shows axes and hyper bars but NO points and dim
   dropdown text ("WebGL: too many errors") -- looked like a data problem, was a missing-file problem.
4. `./build.sh constellation --web` refuses ("standalone app"); use the emcc line directly:
   `/puffertank/emsdk/upstream/emscripten/emcc -o build/web/<page>/game.html src/constellation.c -O2 -Wall -Wno-narrowing
   -Wno-unused-function -I. -Isrc -Ivendor -Iraylib-5.5_webassembly/include -L./raylib-5.5_webassembly/lib -lraylib
   -sUSE_GLFW=3 -sUSE_WEBGL2=1 -sASYNCIFY -sASYNCIFY_STACK_SIZE=4194304 -sFILESYSTEM -sFORCE_FILESYSTEM=1
   -sINITIAL_MEMORY=512MB -sALLOW_MEMORY_GROWTH -sSTACK_SIZE=33554432 -DPLATFORM_WEB -DGRAPHICS_API_OPENGL_ES3
   --shell-file vendor/minshell.html --preload-file resources/shared@resources/shared
   --preload-file $D/resources/constellation@resources/constellation`
5. Pages live under build/web/ served on :8002 (constellation = NetHack, constellation_drone = local drone sweep,
   constellation_drone_box = 8-GPU box drone sweep). Verify with
   `xvfb-run -a -s "-screen 0 1600x1000x24" /puffertank/pwenv/bin/python scratchpad/const_web_test2.py <url> shot.png`
   (playwright lives in /puffertank/pwenv; headless chromium has no WebGL, xvfb is required).

**Why:** the user asks for refreshed constellations after every sweep check-in; each rebuild used to be re-derived.
**How to apply:** follow the steps; if the page is blank, check step 3 first. Related: [[vast-8gpu-box]], [[nethack-5.0-scaling]].

**Per-sweep tables (2026-09-06):** the cache names each table after its subdirectory under logs/ (constellation.c scandir("logs")), so one page can hold one constellation per sweep plus a merged one: lay the inis out as logs/<label>/ (e.g. drone_64x2_fixed, drone_128x2, drone_all_sweeps, drone_seed_panels) and run cache_data --full once. Env dropdown lists each label; "all" merges tables and colors by env_name. Built page: build/web/constellation_drone_sweeps (56 MB, 9 tables, 6,226 sweep trials + 260 seed-panel replays), dataset dir build/const_drone_sweeps. Drone-box pull: `ssh drone 'tar cz <dirs> | base64 -w0'` then grep the long base64 line and decode (banner-safe). Server: python3 -m http.server 8002 in build/web (was not running; started 2026-09-06). Screenshot check: prof/const_shot.py under xvfb-run with /puffertank/pwenv.

2026-09-07 SITE CONSTELLATION REFRESH: the puffer.ai bundle (docs/assets/constellation, April 2026) preloads resources/constellation/experiments.json = {env: {column: "v1,v2,..."}} for 20 envs (old format); the current constellation.c reads experiments.ini ([env] sections, column = comma list) and REJECTS ragged columns ("column X has N values, expected M"). Recipe used: extract experiments.json from game.data via the loadPackage metadata in game.js (regex filename/start/end), convert each env to an ini section keeping only columns whose length == len(agent_steps) (breakout dropped 10, drone 5, nmmo3 5, pong 4, tower_climb 1), append [nethack] from cache_data --full over the 1176 vast sweep #2 inis (scratchpad const_nh), copy shaders + puffer.rgs, emcc recipe from [[constellation-web-build]] -> build/web/constellation_site; xvfb screenshot shows all 21 tables (nethack max 6358). Committed on puffer.ai nethack-release as 2nd commit "constellation" (game.wasm.map removed). Merged dataset: scratchpad const_merge/resources/constellation/experiments.ini (11.3 MB).
FINAL site dataset (commit 0e005dd on puffer.ai nethack-release): base = upstream/5.0 resources/constellation/experiments.ini (13 current-format tables, Joseph 2026-09-02) + 10 old-only envs converted from the April json (connect4 drive enduro freeway go moba pong slimevolley trash_pickup tripletriad) + [nethack] sweep #2 = 24 tables. A constellation table exists only for swept envs (~60 envs on the Ocean page, 24 swept).
UNDONE 2026-09-07: user will send the constellation to the maintainer themselves; puffer.ai nethack-release reset to eae910b (demo only). Artifacts saved OUTSIDE the repos at /puffertank/constellation_nethack/ (page/ = built viewer bundle, data/ = nethack-only ini, merged 24-table ini, raw sweep inis tar, README.txt with provenance).
BACKUP: /puffertank/backups/constellation_nethack_2026-09-07_final1200.tar.gz (13.5 MB, md5 4157e766..., 11 entries) + unpacked /puffertank/constellation_nethack (38 MB) + host-visible copy /puffertank/docker/constellation_nethack.tar.gz.

2026-09-09 NETHACK LADDER CONSTELLATION: build/web/constellation_nh2 (served :8002) = tables nethack_sweep (1200 sweep-2 trials from /puffertank/constellation_nethack/data/nethack_sweep2_inis.tar.gz) + box lane inis (/workspace/sweeps/nh/logs/nethack, 100 files) bucketed by total_timesteps into nethack_rerun (>=100M, 37) / nethack_1B (46) / nethack_2B (5) / nethack_4B (4). Dataset+page+shot saved at /puffertank/constellation_nethack/ladder_2026-09-09/. Default view "all" x=uptime(log) y=perf c=env_name shows the ladder. GOTCHA: raygui dropdowns don't open under the playwright click script (const_pick.py) - the header highlights but no list renders; screenshots use the default axes.
