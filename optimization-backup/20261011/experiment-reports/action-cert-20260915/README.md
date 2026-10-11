# Fixed 4B action-use evaluation

Both article score policies, s705 and s706. Fork engine, seed 7, 512 agents, 24 threads, synchronous vec execution. Each evaluation completes at least 14,000 episodes; reporting uses completion rows 4,000 through 13,999 (10,000 episodes). Raw overshoot rows are preserved.

`queue.log` tracks the detached sequential queue. `DONE` is written only after both certificates pass validation. `RESULTS.md` and per-policy results JSON report mean, median, p90, total and percentage of games with nonzero use for every counter. `manifest.json` stores model, binary, engine and config hashes. `columns.json` describes raw episode columns.

Instrumentation is confined to this source copy. It exports existing episode counters and adds verb-attempt counters to Stats, cleared by the existing episode reset. Policy inputs, rewards, masks and sampling are unchanged. Trainer source is unchanged. Whole episode output rows are protected by flockfile.

`attempt_*` counts dispatch to the action implementation. `counter_*` uses existing environment-specific semantics: some count commands, item verbs generally count a valid item selected at a prompt. Neither establishes that an effect succeeded. `reads_scroll` and `reads_book` separate those item classes. Wand engraving identification is counted separately from zapping. Item subtypes and tactical effectiveness are not measured here.

The initial 32-game smoke checks column shape, nonnegative counters and consistency of the read-class counters. It also compares the original outcome columns with the previous uninstrumented BALROG smoke run, logging whether they match exactly.
