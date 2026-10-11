# Follow-up candidate, not built or accepted

Repaired pool currently uses atomic fetch-add even when a home set is exhausted. This creates unnecessary write traffic at high worker counts. The original parked patch prechecked the bound and used CAS only when actual work remained. Restore that claim behaviour while keeping the new region leases and shutdown safety. This is one isolated change, not a claimed cause or win until measured.

Need regular/ASAN/TSAN stress, exact fixed-action bothpolicy checks, and incremental priorpool/CASpool/priorpool timings under the same counts/workload. Then realtraining if the replay result justifies it. Do not alter the currently running binaries/sources.
