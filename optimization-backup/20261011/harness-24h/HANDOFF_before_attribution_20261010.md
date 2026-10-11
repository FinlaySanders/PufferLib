# Active original goal — 2026-10-10T06:47:49.148588+00:00

Read /root/.codex/attachments/45e8ae2b-9569-441d-b536-ceced1640e37/pasted-text-1.txt before continuing.
Start2026-10-09 22:30:39UTC, deadline2026-10-10 22:30:39UTC. Target277,778SPS with existing15.55M score architecture. Goal remains ACTIVE. User requested another goal prompt; prompt supplied, but current goal was not replaced. Previous prompt-only turn was no progress. This continuation made concrete progress: finished matched-PGO weight-cache full test; prepared/built/tested a new dry-tile candidate; launched2048screen.

No commits/pushes/PRs/default changes/subagents. Serialize heavy work. Chat updates roughly every minute. Verified PIDs only. Production files unchanged.

## Live job — POLL FIRST

Unified exec session **81622** runs `python screen_liquid_fastpath.py 2048`.
Observed 2026-10-10T06:47:49.148588+00:00: {"status": "running", "label": "liquid_fastpath_2048_candidate_a", "pid": 2974306, "started": 1791614848.0023184}; /proc/PID exists. Four native runs base_a/candidate_a/candidate_b/base_b,32 unpinnedworkers,8192warm and two restored512-decision windows per process. Expect about3minutes total. Results `liquid_fastpath/SCREEN_2048.json` and pending `_SUMMARY.json`.

All other heavy sessions terminal:24221 matched-PGO builds,6247 weight full campaign,60099 liquid build,95345 liquid512screen. Do not restart a job just because a status file or observation is stale; poll session or actual process.

## Current best — unchanged

COMBINED_DIRECT_SUMMARY:194071.687->210221.722SPS,+8.322%INCLUDING24->32workers. Fixed24workers +3.896%. Memory8840->8290MiB. All80observation/frozenactor/workcount proofs exact. GPU combination changes rounding, not established learning equivalence. Secondarydepth+3.861% repeated; shortlivefinite but trajectories diverge.

Fast stack and old numerical caveats are in HANDOFF_0626_ARCHIVE.md and HANDOFF_0624_ARCHIVE.md. Trainer source/binary remains env_pages_v36, SHA1d626672950bd3e3a4b9a4fe49c1c6d5fb06562b699271e347d7e3ba1b4f5149. No new CUDA source changes this turn. Weight-cache and liquid candidates are isolated engine replacements, NOT retained.

## Weight cache — full comparison finished, parked

Matched fresh PGO baseline/candidate successfully built. Identical16 profile inputs (8score+8depth); own counters, -Werror=coverage-mismatch. Only missing-profile warning is unused recover utility.
- base librarySHA1d1e35824834a93229b91368ff8a1cccbbe4e41ff4af8f0f6736afbca2499888
- candidateSHAfac9b084854dae7223f9371603247dd472bf50f33710bee234ff8acd7c1f2495
- source differences exactly five expected files; input list bytes identical.

WEIGHT_CACHE_FULL_SUMMARY.json:control210159.521SPS,candidate211830.893,+0.7953%;control drift-0.5858%. Candidate runs211702/211960;controls210777/209542. Both candidate runs beat both controls, so small positive signal, but below prior1%full continuation gate and drift exceeds0.5%. Park instead of spending long on incomplete mutation audit. It is NOT a retained win and should not be described as proven neutral. Full80obs hashes, frozenactor and113update/counts exact each. Tail~162.65->151.53ms,memory8290MiB unchanged.

Earlier native results:512+2.066%,2048+.977%; verifier93.421%hit eligibility with zero observed stale totals in one mature census. Existing quick suites passed, not comprehensive mutation proof. Details in weight_cache/DECISION.md and oldhandoff. Future reconsideration requires repeat/fullcorpus/specialmutationaudit before retention.

Harness correction: original run.py DID NOT accept --env=LD_LIBRARY_PATH despite the prior summary. First full launcher failed before starting engine; preserved weight_cache_full_base_a.launcher.log and empty run dir. Changed only experimental run.py argument whitelist to explicitly allow LD_LIBRARY_PATH; actual baseline/candidate /proc/maps verified. Retry labels end_v1. No production change.

## New candidate: dry-tile minliquid fast return

prepare_liquid_fastpath.py -> liquid_fastpath/source,build,changes.patch,HYPOTHESIS.md,CANDIDATE.json. Based on retainedengine source (same ordinaryLTO baseline as floor_empty_base), without weightcache. Only src/mon.c changed. Before original minliquid body:
- if species is not S_EEL, switch on existing TYP_AT.
- POOL/MOAT/WATER/DRAWBRIDGE_UP/LAVAPOOL/FOUNTAIN fall through to original body.
- other terrain returns0 immediately.
- All eels retain original path (dry-land HP loss and flee behavior).

Evidence: current CPU profile minliquid~2%samples (notwallshare); original disassembly shows drypath readingcompacttype,primarytile,dungeonstate,steed,monstertypes despite no effects. Newfastpath removes those coldreads/branches forordinarynon-eeldrycase. Disassemblies saved baseline_minliquid_disasm.txt,candidate_minliquid_disasm.txt.

screen_liquid_fastpath.py512 ran34goldens+26fuzz successfully, then4ABBAprocesses/twowindows each. SCREEN_512_SUMMARY:281547.54->285244.30SPS,+1.313%,controlsdrift+.785%. Allcandidatewindows284345–285830 exceedallcontrols280109–282697;all8endpoints/turncounts exact. Driftqualifiesclaim,notretained.2048screennowrunning.

If2048timinguseful: develop guard verification against actual original terrain predicates, run interleaved/shuffled/status fixtures and saveddecisioncorpus; buildmatchedPGOcandidate (can reuse already-builtweight_pgo_base as sameunchangedbase with identicalflags/profileinputs), then bounded fullpipelinegate. Avoid fullvalidation for timinglosers. minliquid fastpath relies on existing TYP_AT-primarytilecoherence; ensure specialterrain/eels unchanged. Nextpossible relatedlead is duplicated compact/primarytile reads in is_pool/nh_cell_pool, but no othercandidate implemented and don't repeat oldlayout guesses.

## Integrity and references

Latest integrity_064535.json:16protectedfiles unchanged. Actualchecktime2026-10-10T06:45:35UTC. Mainrepo unrelateddrone/depth/articlechangesuntouched.

ArchiveHANDOFF_0626_ARCHIVE.md contains oldweightdiagnostic/currentprofile/closedCPUcandidate details. Full historyLEDGER.md. Existing hugepage,emptyfloorquery,batchedGEMM,training/inferencefusion,Gram,padding and othernulls should not be repeated without new evidence.

run.py full80/start64 ~100sec, fixed2048env/4buffers/H128/batch262144/mb4096/113updates,512uniqueactionstreams repeated4x caveat. Native snapshot_test.run engineoverride32workers requirespinFalse. Allheavybuilds/profiles/timings serialized. No new retainedwinthisturn; actual progress is measured candidate decisions and nextscreen.
