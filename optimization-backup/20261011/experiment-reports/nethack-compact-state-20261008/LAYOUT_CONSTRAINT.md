# Existing lock-state layout constraint

Observed in the retained benchmark engine source, not established for upstream or the live production build. No production change was made.

The lock implementation represents its state through a struct overlay beginning at g_lock_c_xlock_door_p. The generated context declares only that pointer, followed by restore-related fields. The overlay therefore relies on storage outside the declared pointer field. Independently moving that field in the first hotpack experiment made lock reset write into role state, causing its first golden check to fail. A data watchpoint identified reset_occupations as the writer. The initial failing library and gate metadata are retained as engines/hotpack/initial_failed.so and checks/results_hotpack_initial_failed.json.

The performance experiment now excludes the complete original region from reordering, including its adjacent restore fields. It passes the original quick gates without modifying reference outputs. This preserves baseline behavior for the performance comparison; it does not repair the underlying representation defect.

A separate corrective change should give lock state its own properly sized typed storage, remove the overlay assumption, and check lock interactions and level save/restore. Such a fix must be evaluated separately from throughput improvements and may legitimately change previously incorrect behavior. It has not been implemented or credited as an optimization here.
