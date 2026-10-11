---
name: nethack-web-build
description: "How the NetHack web page is built (ocean/nethack/web.sh sourced by build.sh --web), what it needs, and the verified checks"
metadata: 
  node_type: memory
  type: project
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-09-07T10:17:43.138Z
---

2026-09-06: `./build.sh nethack --web` works via ocean/nethack/web.sh (uncommitted, written this day). build.sh's generic web path (puffercpu.c + raylib + minshell) does not apply to NetHack; build.sh sources ocean/<env>/web.sh when it exists and NetHack is the only env with one.
What web.sh does: clones fast-nle if missing; builds the wasm engine with `emcmake cmake -S vendor/fast-nle -B vendor/fast-nle/build-web -DCMAKE_BUILD_TYPE=Release` + `cmake --build --target nethack` when build-web/libnethack.a is absent (~14 s from scratch on the puffertank box); then em++ links ocean/nethack/nethack.c with libnethack.a/libtmt.a/libbz2_static.a, ASYNCIFY, 16 MB stack, preloads build-web/dat/nhdat and the weights (`NETHACK_WEB_WEIGHTS`, default resources/nethack/nethack_score_weights.bin), shell ocean/nethack/web_shell.html (moved out of vendor 2026-09-07; OSRS precedent ocean/osrs/osrs_shell.html), output build/web/nethack/game.html. Needs an activated emsdk (`source /puffertank/emsdk/emsdk_env.sh`) and the wasm raylib include dir for src/pufferenv.h.
Rendering: no raylib on the page; nethack.c prints ANSI frames, the shell's `print` hook converts ANSI to HTML into a flush-on-timer buffer (`\x1b[2J` = frame boundary). URL knobs: multi, seed, skip, hz. Click-to-play gate removed at the user's request (page starts immediately).
Verified: node run (`node game.js <episodes> 0` in build/web/nethack) prints hidden=512 layers=3 and plays; headless Chromium screenshot shows the full terminal at 20 Hz.
LANDMINE: a fresh fork clone cannot build the wasm engine until the local fast-nle "tmp" commit (Emscripten CMake branch + fcontext shim) is pushed; build.sh clones fork main unpinned.

**Why:** the wasm engine build lives in the fast-nle fork, not in PufferLib, so the web page silently depends on an unpushed vendor commit.
**How to apply:** before shipping or on a fresh box, push/pin the fast-nle wasm commit first; run the node check after any shell or nethack.c change. See [[nethack-env-setup]], [[nethack-determinism-gate]].

2026-09-07: COMMITTED 452c13a7 "nethack cleanup" on 5.0-nethack (web.sh + ocean/nethack/web_shell.html + cleaned nethack.c/h, wandb_sync.py removed). Gate PASS 89c6f91689be3ad7 on that tree.

2026-09-07: weights lookup in web.sh follows upstream: NETHACK_WEB_WEIGHTS override > $PUFFER_WEBSITE_DIR/docs/assets/models/nethack_web_weights.bin > .../nethack_weights.bin > local resources/nethack/nethack_score_weights.bin (gitignored, backup in scratchpad weights_backup/). Verified both paths build + node plays on 5.0-nethack-release.

2026-09-07 SITE PR READY: website clone /puffertank/puffer.ai (origin = pufferai/puffer.ai, branch 5.0, has an UNPUSHED 1 Sep commit b7a543a "Add NetHack web demo" + uncommitted drone/nethack rebuilds + junk nethack_sep1/t12mb/t5mb; left untouched). Clean worktree /puffertank/puffer.ai-release on branch nethack-release = origin/5.0 + commit 500f4a2 "nethack web demo": models/nethack_weights.bin = t643 1B checkpoint (rt_1B_0643_s201 step 999,948,288, 5.5 MB, hidden 128 x 4 layers, score 4574; chosen for page load size), page built from 5.0-nethack-release via PUFFER_WEBSITE_DIR=<worktree> ./build.sh nethack --web (game.data 6.8 MB), thumbnail + games.js entry restored from b7a543a with the stale "entity lists" observation line fixed. Verified: node plays, Chromium screenshot renders at 20 Hz. build.sh exits after web.sh so the site copy is manual. User pushes (needs rights or a fork remote). Native --cpu demo has NO build.sh path on upstream (only osrs_* uses SRC_FILE as standalone source): README "--fast" is stale; fix = add nethack to that case.

2026-09-07 later: site PR branch moved INTO the main clone: /puffertank/puffer.ai is now checked out on nethack-release (99f3d79 "nethack web demo", NetHack entry placed just before craftax as silver), worktree puffer.ai-release removed. The user pushes from there (git push origin nethack-release). Their old state is preserved: local branch 5.0 still has unpushed b7a543a; stash@{0} "site wip: drone (Sep 4) + nethack (Sep 3) rebuilt assets"; stray files (nethack_sep1/, t12mb.bin, t5mb.bin) parked in scratchpad/site_stray.
