# All training optimization screens

| Case | SPS | GPU MiB | Weight updates | Checkpoint |
|---|---:|---:|---|---|
| norm-update | 172,407 | 15,435 | True | exact checkpoint |
| baseline-update | 170,387 | 15,597 | True | exact checkpoint |
| norm-frozen | 172,814 | 15,525 | False | exact checkpoint |
| baseline-profile | 161,884 | 15,707 | False | exact checkpoint; diagnostic timing |
| fuse-update | 170,858 | 15,597 | True | exact checkpoint |
| nocopy-update | 171,791 | 15,417 | True | exact checkpoint |
| bias-update | 171,020 | 15,597 | True | exact checkpoint |
| skip-update | 174,522 | 15,597 | True | exact checkpoint |
| combo1-update | 177,522 | 15,255 | True | exact checkpoint |
| baseline-frozen-repeat | 170,995 | 15,687 | False | exact checkpoint |
| combo1-frozen | 177,176 | 15,345 | False | exact checkpoint |
| cache-update | 171,899 | 15,297 | True | exact checkpoint |
| poolfuse-update | 171,335 | 15,417 | True | exact checkpoint |
| priority-train | 170,394 | 15,687 | False | exact checkpoint |
| priority-rollout | 168,603 | 15,687 | False | exact checkpoint |
| sample-update | 170,517 | 15,597 | True | exact checkpoint |
| upload-update | 170,958 | 15,597 | True | exact checkpoint |
| outplace-update | 176,021 | 15,041 | True | exact checkpoint |
| combo2-update | 183,577 | 14,699 | True | exact checkpoint |
| sampler-shared-update | 171,801 | 15,597 | True | exact checkpoint |
| combo2-frozen | 183,589 | 14,789 | False | exact checkpoint |
| early-baseline | 175,447 | 15,687 | False | exact checkpoint |
| early-combo2 | 187,168 | 14,789 | False | exact checkpoint |
| parallel2-update | 182,922 | 14,747 | True | exact checkpoint |
| parallel4-update | 181,569 | 14,843 | True | exact checkpoint |
| idrows-update | 163,119 | 15,601 | True | exact checkpoint |
| state-base | 170,059 | 15,597 | True | exact checkpoint |
| state-combo2 | 183,023 | 14,697 | True | exact checkpoint |
| group-update | 169,370 | 15,423 | True | exact checkpoint |
| compact-update | 183,540 | 14,699 | True | exact checkpoint |
| combo3-update | 184,088 | 14,329 | True | exact checkpoint |
| ppo-zero-update | 173,811 | 15,601 | True | exact checkpoint |
| combo2-profile | 0 | 0 | False | not completed; diagnostic timing |
| scan8-update | 171,624 | 15,597 | True | exact checkpoint |
| scan4-update | 169,021 | 15,597 | True | exact checkpoint |
| scanpack-update | 171,905 | 15,597 | True | exact checkpoint |
| combo4-update | 185,650 | 14,697 | True | exact checkpoint |
| combo4-profile | 0 | 0 | False | not completed; diagnostic timing |
| bytes-update | 171,454 | 12,011 | True | exact checkpoint |
| combo4-phases | 186,411 | 14,799 | False | exact checkpoint; diagnostic timing |
| finish-update | 173,797 | 14,675 | True | exact checkpoint |
| combo5-update | 187,031 | 11,111 | True | exact checkpoint |
| baseline-phases | 170,576 | 15,695 | False | exact checkpoint; diagnostic timing |
| reuse-update | 169,808 | 12,407 | True | exact checkpoint |
| msgpair-update | 170,454 | 15,597 | True | exact checkpoint |
| small-baseline | 246,289 | 14,983 | False | exact checkpoint |
| small-combo5 | 248,194 | 10,567 | False | exact checkpoint |
| wmma-update | 171,683 | 15,005 | True | exact checkpoint |
| sm64-update | 183,992 | 14,505 | True | different checkpoint |
| sm96-update | 184,095 | 14,505 | True | different checkpoint |
| memory-update | 187,291 | 8,095 | True | exact checkpoint |
| small-combo3 | 242,788 | 13,781 | False | exact checkpoint |
| memory-repeat1 | 187,839 | 8,185 | False | exact checkpoint |
| baseline-final1 | 170,648 | 15,687 | False | exact checkpoint |
| memory-state | 186,815 | 8,095 | True | exact checkpoint |
| dw-serial | 185,665 | 8,091 | True | exact checkpoint |
| dw-defer | 186,181 | 8,091 | True | exact checkpoint |
| memory-repeat2 | 186,779 | 8,185 | False | exact checkpoint |
| retained-state | 187,308 | 8,095 | True | exact checkpoint |
| early-memory | 191,753 | 8,185 | False | exact checkpoint |
| early-base-update | 175,051 | 15,597 | True | exact checkpoint |
| early-memory-update | 190,659 | 8,095 | True | exact checkpoint |
| bias-reduce | 186,467 | 8,095 | True | exact checkpoint |
| mature-live-base | 170,930 | 15,687 | False | exact checkpoint |
| mature-live-retained | 185,945 | 8,185 | False | exact checkpoint |
| retained-phases | 187,283 | 8,193 | False | exact checkpoint; diagnostic timing |
| small-live-base | 348,802 | 14,971 | True | exact checkpoint |
| small-live-retained | 390,413 | 7,641 | True | exact checkpoint |
| baseline-final2 | 170,600 | 15,687 | False | exact checkpoint |
| retained-final1 | 187,167 | 8,185 | False | exact checkpoint |
| retained-profile | 0 | 0 | False | not completed; diagnostic timing |
| lt-rank1 | 192,656 | 8,103 | True | different checkpoint |
| lt-rank2 | 190,273 | 8,111 | True | different checkpoint |
| lt-rank3 | 182,209 | 8,061 | True | different checkpoint |
| small-retained | 242,854 | 7,653 | False | exact checkpoint |
| reset-base | 174,246 | 15,589 | True | exact checkpoint |
| reset-retained | 190,672 | 8,087 | True | exact checkpoint |
| lt-large | 192,752 | 8,095 | True | different checkpoint |
| lt-small | 186,633 | 8,103 | True | different checkpoint |
| small-base-repeat | 236,495 | 14,983 | False | exact checkpoint |
| small-retained-repeat | 246,897 | 7,653 | False | exact checkpoint |
| sync-base | 140,174 | 10,077 | True | exact checkpoint |
| sync-retained | 150,434 | 5,733 | True | exact checkpoint |
| minimal-update | 186,966 | 8,095 | True | exact checkpoint |
| small-base-repeat2 | 240,435 | 14,983 | False | exact checkpoint |
| small-retained-repeat2 | 247,343 | 7,653 | False | exact checkpoint |

Replay cases verify three observation hashes. Frozen cases verify unchanged policy weights; that alone does not prove identical gradients. Full state and live trajectory comparisons are in final-state-proof.json. Failed Nsight finalization is a profiler issue, not a training crash.
