---
name: nethack-results-ledger-2026-09-13
description: "AUTHORITATIVE results = resources/article/certificates/RESULTS.md; ALL headline certs complete 2026-09-13 21:05 (2B gym landed: 10,345 / 16,753, 8,064 games); independently verified 22/22 runs, 9/9 pools; quote numbers only from there"
metadata:
  type: project
---

Single source of truth for the fixed 1B/2B/4B results: `resources/article/certificates/` (RESULTS.md, results.csv/json,
manifest.json with SHA-256s, raw/ snapshots, ledger.py refresh|build). Built by another agent; I verified it with
`resources/article/independent_results.py` (no shared code; reads /tmp/reg/article/ep + /tmp/reg/article/gym) ->
`resources/article/RESULTS_INDEPENDENT.md`: all 20 completed runs match to 0.05, all 8 completed pooled rows match, raw
snapshots byte-identical. Their `gen_data.py` is now an adapter over the ledger and REFUSES to regenerate figures while
any headline pool is pending (2B/gym until r4_fixwt2b_s703_4k + s704_4k land, ~19:55 / ~20:50 on 09-13).

Certified pooled (median / mean+-se / games): 1B fork 9,098.5/13,783+-111/20,000; stock 8,687/13,103+-96/24,166; gym
8,919/13,362+-168/8,064. 2B fork 10,084.5/17,246+-161; stock 10,036/16,614+-137/24,109; gym PENDING. 4B fork
11,225.5/19,906+-188; stock 11,016/18,758+-218/12,071; gym 11,516/19,705+-281/8,064.

**Why:** two agents were producing tables; user wants one authoritative source. The ledger is stricter (hashes, no
one-seed pools, AutoAscend refs excluded until sourced) and correct, so it wins; my tables/draft cite it.
**How to apply:** quote numbers only from certificates/RESULTS.md; after 2B gym lands run `ledger.py refresh && build`,
then `render.sh` (figures) and re-stage /puffertank/docker/nethack_article. Constellation scaling render is parked:
data file resources/article/data/constellation_nethack_curves.ini (53K points, 3 tables) staged for the user; my
constellation.c export patch was NOT applied (anchor had a blank line; the unpatched dashboard hangs headless).
Related: [[nethack-article-figures]], [[nethack-cert-ledger]].

## Update 2026-09-13 21:05 — ledger COMPLETE
- 2B gym 4K certs landed (s703 20:04 median 10,213 / mean 17,034; s704 21:03 median 10,418 / mean 16,472). Pooled 2B gym: **10,345 · 16,752.8 ± 233.9 (8,064)**. `ledger.py refresh && build` run; RESULTS.md/results.csv/json updated.
- `independent_results.py` re-run: 22/22 runs, 9/9 pools MATCH, raw snapshots identical. No row is pending any more.
- Gym vs fork at 2B: median +2.6%, mean −2.9% — same "within seed noise" story as 1B/4B.
- Figures regenerated 21:05 (`render.sh`), draft table 2B gym row filled, everything re-staged to /puffertank/docker/nethack_article.
