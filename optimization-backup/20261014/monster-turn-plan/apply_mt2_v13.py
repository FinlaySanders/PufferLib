"""mt2 v1.3: peaceful far-unseen monsters join the fast path (wander intent, rn2(10) before the likes test, SANCT|SSM flag);
hero-state word cached per movemon pass and marked stale after any move that is not a pure fast move."""
from pathlib import Path
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rd(p): return (src/p).read_text()
def wr(p,t): (src/p).write_text(t)
def rep(p, old, new, count=1):
    t=rd(p); assert t.count(old)==count, (p, t.count(old), old[:80]); wr(p, t.replace(old,new))
# ---- eligibility: peaceful allowed; hero word cached -------------------------------------------------------------------
rep('src/monmove.c', """int
mt2_eligible(m)
struct monst *m;
{
    const struct permonst *p = m->data;

    if (m->mtame || m->mpeaceful || m->isshk || m->ispriest || m->isgd || m->iswiz || m->wormno || m->mstrategy)
        return 0;""", """/* hero-state half of the predicate: recomputed at each movemon() pass and after any monster move that was not a pure fast move
   (only hero actions, old-path monster moves and the fast path's near tail can change these properties) */
int nh_mt2_hero_stale = 1, nh_mt2_hero_bad;
static int
mt2_hero_bad(void)
{
    if (nh_mt2_hero_stale) {
        nh_mt2_hero_bad = (u.uswallow || Underwater || Invis || Displaced || Hallucination || Conflict || Upolyd || Reflecting
                           || u.uundetected || U_AP_TYPE != M_AP_NOTHING);
        nh_mt2_hero_stale = 0;
    }
    return nh_mt2_hero_bad;
}

int
mt2_eligible(m)
struct monst *m;
{
    const struct permonst *p = m->data;

    if (m->mtame || m->isshk || m->ispriest || m->isgd || m->iswiz || m->wormno || m->mstrategy)
        return 0;""")
rep('src/monmove.c', """    if (u.uswallow || Underwater || Invis || Displaced || Hallucination || Conflict || Upolyd || Reflecting
        || u.uundetected || U_AP_TYPE != M_AP_NOTHING)
        return 0;
    {
        int ddx""", """    if (mt2_hero_bad())
        return 0;
    {
        int ddx""")
# dispatch: record purity; dochugw marks the word stale after any non-pure move
rep('src/monmove.c', """#ifdef NH_MT2_TRACE
    nh_mt2_trace_elig = mt2_eligible(mtmp);
    if (nh_mt2_fast && nh_mt2_trace_elig)
        return dochug_fast(mtmp);
#else
    if (nh_mt2_fast && mt2_eligible(mtmp))
        return dochug_fast(mtmp);
#endif""", """#ifdef NH_MT2_TRACE
    nh_mt2_trace_elig = mt2_eligible(mtmp);
    if (nh_mt2_fast && nh_mt2_trace_elig)
        return dochug_fast(mtmp);
#else
    if (nh_mt2_fast && mt2_eligible(mtmp))
        return dochug_fast(mtmp);
#endif
    nh_mt2_hero_stale = 1; /* the original path may change hero properties (attacks, theft, engulfing): recompute before the next fast move */""")
rep('src/mon.c', """    nh_display_sense_recalc();
""", """    nh_display_sense_recalc();
    { extern int nh_mt2_hero_stale; nh_mt2_hero_stale = 1; }
""")
# dochug_fast: purity flag (set when the tail stayed out of range), peaceful tail unchanged (verbatim attack block already tests mpeaceful)
rep('src/monmove.c', """    tmp = m_move_fast(mtmp);
    if (tmp != 2) {
        if (dist2(mtmp->mx, mtmp->my, mtmp->mux, mtmp->muy) > (BOLT_LIM * BOLT_LIM))
            (void) rn2(5); /* distfleeck() recalc out of range */
        else
            distfleeck(mtmp, &inrange, &nearby, &scared); /* recalc (teleport trap etc.) */
    }""", """    tmp = m_move_fast(mtmp);
    if (tmp != 2) {
        if (dist2(mtmp->mx, mtmp->my, mtmp->mux, mtmp->muy) > (BOLT_LIM * BOLT_LIM))
            (void) rn2(5); /* distfleeck() recalc out of range: nothing below can touch the hero */
        else {
            nh_mt2_hero_stale = 1; /* the near tail (attacks) may change hero properties */
            distfleeck(mtmp, &inrange, &nearby, &scared); /* recalc (teleport trap etc.) */
        }
    }""")
# m_move_fast: intent and likes for peaceful monsters
rep('src/monmove.c', """    appr = 1; /* !mflee; !mconf; should_see is FALSE beyond dist2 36; !mcansee, Invis, disguise, peaceful are excluded */
    if ((spw & SPW_RANDAPPR) && !rn2(3))
        appr = 0;""", """    appr = 1; /* !mflee; !mconf; should_see is FALSE beyond dist2 36; !mcansee, Invis and disguise are excluded */
    if (mtmp->mpeaceful) /* (mpeaceful && !isshk) precedes the stalker/bat/light draw in the original OR chain */
        appr = 0;
    else if ((spw & SPW_RANDAPPR) && !rn2(3))
        appr = 0;""")
rep('src/monmove.c', """    if (!Is_rogue_level(&u.uz)) { /* hostile: no rn2(10) draw */
        /* in_line is FALSE at distmin >= 9: lined_up() draws nothing (!Upolyd) and linedup() only stores tbx/tby */
        register int pctload = 0;""", """    if ((!mtmp->mpeaceful || !rn2(10)) && !Is_rogue_level(&u.uz)) { /* the draw precedes the level test in the original */
        /* in_line is FALSE at distmin >= 9: lined_up() draws nothing (!Upolyd) and linedup() only stores tbx/tby */
        register int pctload = 0;""")
rep('src/monmove.c', """        can_unlock = (can_open && monhaskey(mtmp, TRUE));
        unlock_known = 1;
        flag = ALLOW_U;""", """        can_unlock = (can_open && monhaskey(mtmp, TRUE));
        unlock_known = 1;
        flag = mtmp->mpeaceful ? (ALLOW_SANCT | ALLOW_SSM) : ALLOW_U; /* Conflict is excluded */""")
rep('src/monmove.c', """        if (level.lflags.shortsighted
            && nidist > (couldsee(nix, niy) ? 144 : 36) && appr == 1)
            appr = 0;
        /* avoid (unicorn) and should_displace (ALLOW_MDISP) cannot apply to this population */""", """        if (!mtmp->mpeaceful && level.lflags.shortsighted
            && nidist > (couldsee(nix, niy) ? 144 : 36) && appr == 1)
            appr = 0;
        /* avoid (unicorn) and should_displace (ALLOW_MDISP) cannot apply to this population */""")
print('v1.3 applied')
