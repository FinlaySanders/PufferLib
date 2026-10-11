# Find good runs in the vec eval, then watch one by skipping to it

`./puffer_find` = `./build.sh nethack puffer_find` with `find_watch_tooling.patch` applied to
ocean/nethack/nethack.h (env-var gated, inert otherwise; NOT committed).

    ./nh_find.sh  /tmp/find.ep 128 3000 73      # headless vec eval; log: env ep score how time role race gend max_depth last_turn
    ./nh_rank.sh  /tmp/find.ep                  # by max_depth then score
    ./nh_watch.sh 18 1 40 128 73                # replay the same eval, draw only env 18 episode 1 at 40 ms/frame, exit at its end

agents and seed MUST match between find and watch (episodes are addressed as (env, ordinal) of a
deterministic run: --vec.num_buffers=1 --base.async=0). Do not use `./puffer eval` render mode: it
sets train.verb_eps=1 (= literal epsilon 1.0 -> uniform random verbs).

The watched episode is drawn with the demo's composite view (coloured map, message ring, inventory
pane, status box), extracted from nethack.c into ocean/nethack/nethack_view.h and shared with the
watch hook. Rebuild both: `./build.sh nethack --cpu` (demo) and `./build.sh nethack puffer_find`.

## Instant replay (preferred): record actions in the find pass, replay in the demo

    ./nh_find.sh   /tmp/deep.ep 512 10000 73        # also writes /tmp/deep.ep.acts/env<j>.act (3 bytes/step)
    ./nh_rank.sh   /tmp/deep.ep                      # by max_depth then score
    ./nh_replay.sh /tmp/deep.ep 66 5 40              # replay env 66 episode 5 at 40 ms/frame, instantly
    NH_SKIP=3000 ./nh_replay.sh /tmp/deep.ep 66 5 40 # start drawing at step 3000

No waiting: episode K's seed is the LCG advanced K times (K quick resets), then the recorded actions
run through the same puf_step the eval used. ms=0 replays silently and just prints FAITHFUL/MISMATCH.
