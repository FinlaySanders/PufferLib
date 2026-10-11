# Five-seed 1B depth campaign

Recovered `mine50e_1b_s311` from commit `1aaf6722`, using current encoder and
fixed fast-nle engine. Seeds 801–805, sequential, 1B steps each. Fresh training;
512 hidden units x 3 layers; challenge characters; search20/run masks enabled.
Score-delta reward explicitly zero. Historical obsolete/neutral options omitted
and listed in manifest.json. Original config preserved in original_mine50e.ini.

Private trainer, engine library, engine data and config snapshots. Root score
config is untouched. Each trainer performs its configured 10K-game inline eval;
these are diagnostics, not burn-in-adjusted score certificates.

queue.jsonl contains start/exit events; active.json contains the current exact
trainer PID. Per-seed stdout is depth1b_sNNN.log. Checkpoints and final INI logs
are under checkpoints/nethack and logs/nethack. Queue halts on incomplete
training; a saved final checkpoint with a failed post-train eval is retained and
reported, then the next seed runs. No automatic retries or process-pattern kills.
