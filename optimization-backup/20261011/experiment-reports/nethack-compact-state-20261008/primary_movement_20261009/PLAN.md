# Primary movement storage experiment

Replace the authoritative terrain grid with eight-byte cells grouped into 64-byte 4x2 blocks. Remove the separate cached-type plane; preserve its distinct value and update timing inside each primary cell. Migrate every terrain reader and writer. Store pile/trap/gas summaries in the same cells, maintained at local mutation sites, with no query-triggered map rebuild or duplicate facts grid. Keep entity identity/attribute records and proven movement-column filters.

This increases primary terrain+type storage from 11760 to 14080 bytes, but replaces the previous failed 18484-byte terrain/type/facts combination. Spatial locality and fewer reads are the hypothesis, not reduced bytes versus baseline. Save format remains fieldwise legacy conversion.

Gates: original goldens/fuzz, summary/reference-query comparisons, saved score and depth trajectories, then matched A-B-B-A timings at 512 and 2048 with no concurrent workloads. Do not edit production or promote on a microbenchmark alone.
