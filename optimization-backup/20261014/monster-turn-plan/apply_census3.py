"""Coverage of the proposed v2 eligibility predicate: share of monster moves and of monster-move cycles it accepts."""
from pathlib import Path
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/census/source')
def rep(path, old, new, count=1):
    t=path.read_text(); assert t.count(old)==count, (path, t.count(old), old[:70]); path.write_text(t.replace(old,new))
mon=src/'src/mon.c'
rep(mon, """unsigned long long nh_elig[24]; /* far-unseen-hostile population: property counts (index = property) */""",
"""unsigned long long nh_elig[24]; /* far-unseen-hostile population: property counts (index = property) */
unsigned long long nh_cov[4]; /* eligible moves, eligible cycles, all moves, all cycles */
static int mt2_eligible(struct monst *m) {
    struct permonst *p = m->data;
    if (m->mtame || m->mpeaceful || m->isshk || m->ispriest || m->isgd || m->iswiz || m->wormno) return 0;
    if (m->mconf || m->mstun || m->mtrapped || m->meating || !m->mcanmove || m->mfrozen || m->msleeping) return 0;
    if (is_covetous(p) || tunnels(p) || passes_walls(p) || is_vampshifter(m) || p->mlet == S_EEL) return 0;
    if (u.uswallow || Conflict || Underwater || Warning) return 0;
    if (dist2(m->mx, m->my, u.ux, u.uy) <= BOLT_LIM * BOLT_LIM) return 0;
    if (canspotmon(m)) return 0;
    return 1;
}""")
rep(mon, """            nh_census[ck][cd][cv][0]++; nh_census[ck][cd][cv][1] += cdt;""",
"""            nh_census[ck][cd][cv][0]++; nh_census[ck][cd][cv][1] += cdt;
            nh_cov[2]++; nh_cov[3] += cdt; if (celig) { nh_cov[0]++; nh_cov[1] += cdt; }""")
rep(mon, """            int ck = nh_census_kind(mtmp); int dm = distmin(mtmp->mx, mtmp->my, u.ux, u.uy);""",
"""            int celig = mt2_eligible(mtmp); int ck = nh_census_kind(mtmp); int dm = distmin(mtmp->mx, mtmp->my, u.ux, u.uy);""")
nle=src/'src/nle.c'
rep(nle, """      fprintf(f, "far_unseen_hostile_props\\n");""",
"""      { extern unsigned long long nh_cov[4]; fprintf(f, "coverage eligible_moves %llu eligible_cycles %llu all_moves %llu all_cycles %llu\\n", nh_cov[0], nh_cov[1], nh_cov[2], nh_cov[3]); }
      fprintf(f, "far_unseen_hostile_props\\n");""")
print('coverage census added')
