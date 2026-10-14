"""mt2 baseline profile build: callgrind collection toggled ON only around dochugw() calls for monsters the v2 eligibility predicate accepts,
so the line-level annotation shows where an ELIGIBLE move's instructions go. No behaviour change (client requests are no-ops outside valgrind)."""
from pathlib import Path
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rep(path, old, new, count=1):
    t=path.read_text(); assert t.count(old)==count, (path, t.count(old), old[:70]); path.write_text(t.replace(old,new))
mon=src/'src/mon.c'
rep(mon, """movemon()
{""", """#ifdef NH_MT2_CG
#include <valgrind/callgrind.h>
unsigned long long nh_mt2_elig_moves, nh_mt2_all_moves;
/* v2 eligibility (ordinary hostile, far, unseen); the kernel's one mask test. Mirrors apply_census3.py plus mstrategy/ustuck/hero-state terms. */
int mt2_eligible(struct monst *m) {
    struct permonst *p = m->data;
    if (m->mtame || m->mpeaceful || m->isshk || m->ispriest || m->isgd || m->iswiz || m->wormno || m->mstrategy) return 0;
    if (m->mconf || m->mstun || m->mtrapped || m->meating || !m->mcanmove || m->mfrozen || m->msleeping || !m->mcansee || m->mflee) return 0;
    if (m == u.ustuck || m->mundetected || M_AP_TYPE(m) != M_AP_NOTHING) return 0;
    if (is_covetous(p) || tunnels(p) || passes_walls(p) || is_vampshifter(m) || p->mlet == S_EEL || is_watch(p) || is_mind_flayer(p)
        || p->msound == MS_NEMESIS || p->msound == MS_SHRIEK || p == &mons[PM_MEDUSA] || p == &mons[PM_TENGU] || is_hider(p)) return 0;
    if (u.uswallow || Conflict || Underwater || Invis || Displaced || Hallucination || u.uundetected || U_AP_TYPE != M_AP_NOTHING) return 0;
    if (distmin(m->mx, m->my, u.ux, u.uy) <= 9) return 0;
    if (canspotmon(m)) return 0;
    return 1;
}
#endif
movemon()
{""")
rep(mon, """        if (dochugw(mtmp)) /* otherwise just move the monster */
            continue;""",
"""#ifdef NH_MT2_CG
        {
            int elig = mt2_eligible(mtmp), rd;
            nh_mt2_all_moves++; nh_mt2_elig_moves += elig;
            if (elig) CALLGRIND_TOGGLE_COLLECT;
            rd = dochugw(mtmp);
            if (elig) CALLGRIND_TOGGLE_COLLECT;
            if (rd) continue;
        }
#else
        if (dochugw(mtmp)) /* otherwise just move the monster */
            continue;
#endif""")
nle=src/'src/nle.c'
rep(nle, """nle_ctx_t *
nle_step(nle_ctx_t *nle, nle_obs *obs)
{""", """#ifdef NH_MT2_CG
extern unsigned long long nh_mt2_elig_moves, nh_mt2_all_moves;
__attribute__((destructor)) static void nh_mt2_dump(void) {
    const char *p = getenv("NH_MT2_STATS"); if (!p) return; FILE *f = fopen(p, "w"); if (!f) return;
    fprintf(f, "eligible_moves %llu all_moves %llu\\n", nh_mt2_elig_moves, nh_mt2_all_moves); fclose(f);
}
#endif
nle_ctx_t *
nle_step(nle_ctx_t *nle, nle_obs *obs)
{""")
print('mt2 profile toggle applied')
