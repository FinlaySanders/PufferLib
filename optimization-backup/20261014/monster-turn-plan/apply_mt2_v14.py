"""mt2 v1.4: hero states Displaced and Invis join the fast path (the believed hero position comes from set_apparxy(), exactly as the
original, twice per move); Upolyd joins with the two lined_up() rn2(25) draw replicas."""
from pathlib import Path
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rd(p): return (src/p).read_text()
def wr(p,t): (src/p).write_text(t)
def rep(p, old, new, count=1):
    t=rd(p); assert t.count(old)==count, (p, t.count(old), old[:80]); wr(p, t.replace(old,new))
rep('src/monmove.c', """        nh_mt2_hero_bad = (u.uswallow || Underwater || Invis || Displaced || Hallucination || Conflict || Upolyd || Reflecting
                           || u.uundetected || U_AP_TYPE != M_AP_NOTHING);""",
"""        nh_mt2_hero_bad = (u.uswallow || Underwater || Hallucination || Conflict || Reflecting
                           || u.uundetected || U_AP_TYPE != M_AP_NOTHING); /* Invis/Displaced: set_apparxy(); Upolyd: lined_up() draws */""")
# dochug_fast: believed position by the original function (found_you for the plain case; the guess loop for Invis/Displaced)
rep('src/monmove.c', """    mtmp->mux = u.ux; /* set_apparxy(): found_you */
    mtmp->muy = u.uy;
    (void) rn2(5); /* distfleeck(): bravegremlin; inrange = nearby = scared = 0 beyond BOLT_LIM */""",
"""    set_apparxy(mtmp); /* believed hero position: exact for Invis/Displaced too; at distmin > 9 it stays >= 8 away */
    (void) rn2(5); /* distfleeck(): bravegremlin; nearby = scared = 0 beyond monnear; inrange only feeds blocks that need dist2 <= 8 */""")
rep('src/monmove.c', """    mtmp->mux = u.ux; /* set_apparxy(): found_you */
    mtmp->muy = u.uy;
    can_open = !(spw & (SPW_NOHANDS | SPW_VERYSMALL));""",
"""    set_apparxy(mtmp); /* second call of the original: re-guesses for Invis/Displaced */
    can_open = !(spw & (SPW_NOHANDS | SPW_VERYSMALL));""")
# in_line replica: lined_up() draws rn2(25) when Upolyd (the result stays FALSE: uundetected/U_AP excluded, range >= BOLT_LIM)
rep('src/monmove.c', """        /* in_line is FALSE at distmin >= 9: lined_up() draws nothing (!Upolyd) and linedup() only stores tbx/tby */
        register int pctload = 0;
        tbx = mtmp->mux - omx;
        tby = mtmp->muy - omy;""",
"""        /* in_line is FALSE at this range: lined_up() draws rn2(25) when Upolyd and linedup() only stores tbx/tby */
        register int pctload = 0;
        if (Upolyd)
            (void) rn2(25);
        tbx = mtmp->mux - omx;
        tby = mtmp->muy - omy;""")
rep('src/muse.c', """    tbx = mtmp->mux - mtmp->mx;
    tby = mtmp->muy - mtmp->my;
    return FALSE;
}""", """    if (Upolyd)
        (void) rn2(25); /* lined_up(): hero concealment draw; cannot return early since uundetected/U_AP are excluded */
    tbx = mtmp->mux - mtmp->mx;
    tby = mtmp->muy - mtmp->my;
    return FALSE;
}""")
rep('src/muse.c', "/* find_offensive() for a monster at distmin >= BOLT_LIM while !Reflecting && !Upolyd: no RNG draw, lined_up() can only",
                 "/* find_offensive() for a monster at distmin >= BOLT_LIM while !Reflecting: lined_up() draws only the Upolyd roll and can only")
print('v1.4 applied')
