# Per-game object storage experiment

Baseline is the unchanged persist engine. This candidate preserves the96-byte object record, serialization, list traversal order and all game fields. It changes allocation ownership/locality only: stable slots in128-object blocks, held by the game context and reused through a free list.

Allocation audit: `newobj()` expands to `alloc(sizeof(struct obj))`. All five call sites in src are splitobj, bill_dummy_object and mksobj in mkobj.c, restobjchn in restore.c, and sub_one_frombill in shk.c. They overwrite the complete record from an existing object, zeroobj, or the saved record before use. Other objects constructed on the stack are not freed. Extensions continue using their existing allocation and deallocation paths.

Deallocation audit: actual object storage is freed only by dealloc_obj in mkobj.c, after timers, light sources and object extensions are released; its final free is replaced with returning a slot. `obfree` continues to perform its normal semantic cleanup. Context teardown frees all blocks after ordinary game cleanup, independently of which worker last executed the game. Growth beyond128 objects allocates another block and never moves existing slots. Memory is retained up to each game's peak object count until that game ends; RSS and early-game checks are needed.

Prepared lifecycle test covers growth across blocks, reuse while neighbouring objects remain live, isolation among four games, and80 context lifecycles. Golden/fuzz/threaded trajectories and native benchmarks are required before any conclusion; every-decision equivalence is required before retention.
