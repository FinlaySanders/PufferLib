# Scroll preference and action-use certificates

Two fixed 4B policies (s705/s706), seed 7, fork engine, 512 agents, 24 threads. Drop first 4,000 completed games and retain next 10,000 for each policy.

All action counters from the previous certificate are retained. For each scroll type, record inventory availability at decision boundaries, accepted read selections, and observed consumption, each split by identification status BEFORE the action. Known means dknown and oc_name_known. Availability counts decisions with at least one such scroll, not stack quantity. Percentage of games using a type conditional on having it can be calculated from the per-episode records. Possession does not guarantee an action was legal at that moment.

The read-only external scroll_probe.so uses the existing engine context and headers, restores thread-local context, and does not use RNG or modify observations or game state. True item types are ANALYSIS ONLY. Main repo and engine library are unchanged. Only this isolated environment copy is instrumented.

Consumed means selected inventory letter disappeared/changed type or its quantity fell after read/menu handling. Terminal read actions have unknown consumption and are not counted as confirmed consumed. This does not establish successful tactical use, or completion of follow-up effects such as wishing/genocide.

columns.json maps all .ep columns. RESULTS.md and per-policy JSON report means, medians, p90s and percentages; scroll_preferences.md reports conditional use. queue.log tracks progress; DONE requires both runs to finish and pass consistency checks. The old partial run is preserved at ../action-cert-20260915 and is not pooled with this restart.
