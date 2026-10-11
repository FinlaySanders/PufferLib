# Ready-buffer focus diagnostic

Workers all visit active regions in order 0,1,2,3 instead of starting from worker-id modulo 4. Existing per-region dynamic work stealing, reader leases, synchronization, submitter work, and one-action-per-environment rule are unchanged. The flag is published atomically after the identical ordinary warm-up. All workers remain pinned as before. No engine changes, future-action batching, training defaults or GPU code changes.

Hypothesis: workers concentrate on fewer games at a time, reducing eviction before the next step. Each buffer still requests and completes exactly its original decisions. This can change completion order and load balance, and may behave differently when GPU inference delays buffer readiness. A native replay benefit is only a screen; full-pipeline and per-step correctness validation would be required to retain it.

First screen uses the same compiled executable with the runtime flag off/on. Reject a flat or negative result; repeat a material gain before escalation. All measured endpoints must match the pre-existing observation hash and world-turn count.
