# Ready-buffer recheck diagnostic

The earlier ordering-only screen gained0.09%; it still visited all ready buffers each sweep. This variant returns a useful-work count from ep_claim, drops its region lease as usual, and restarts the ready-buffer scan after doing work when focus is enabled. If no useful work is found it still uses the original epoch/condition wait. No new waiting for future actions, no grouping of decisions, and no engine mutation. Warm-up uses the original scheduling path. Submitting threads still contribute to their own buffers, and all buffers must finish their original finite window.

Risks: priority may produce uneven progress and weaker GPU overlap; a replay gain would need pipeline validation. This is an isolated diagnostic, not a retained scheduler. Exact observation/turn endpoints are required; every-decision hashes are a follow-up gate for a positive screen.
