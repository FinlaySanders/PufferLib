# Monster-state locality experiment

Baseline is the retained persist engine from nethack-locality-target-20261008, including glyph16 and the persistent floor index. This experiment changes neither live repository nor monster binary/save layout.

Candidates: (1) check the vault guard position before its flag in movemon, avoiding a second cache-line read for monsters not yet due to move; (2) allocate stable monster records from per-game reusable blocks instead of scattering individual mallocs across worker-thread heaps. Test independently.

Performance: identical mature recorded actions, 2048 environments, 8192 warmup decisions then 2048 measured, 24 pool workers, fixed CPU pins. Compare full-pipeline compute only for an apparent CPU winner. Goldens, fuzz, cross-thread interleaving and all 16,777,216 replay hashes must match. Keep all training compute and batch shapes unchanged.

Profile inspection: movemon samples concentrate at the guard flag load (+0x41). However, much of m_move is object-type / inventory scanning and mfndpos includes terrain and object-grid lookups. Pooling monsters does not address all of that time. Hardware cache counters are unavailable.
