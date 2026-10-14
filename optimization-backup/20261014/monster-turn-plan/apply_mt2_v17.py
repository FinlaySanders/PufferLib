"""v1.7: minliquid() is called for every monster every turn (movemon + mcalcdistress); its first test rejects 97% of calls. Replicate that
test inline at both call sites (exact: identical predicate, the function body is unchanged for the rest)."""
from pathlib import Path
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rep(p, old, new, count=1):
    t=(src/p).read_text(); assert t.count(old)==count, (p, t.count(old), old[:80]); (src/p).write_text(t.replace(old,new))
rep('include/hack.h', "static inline int\nnh_typ_special(schar typ)\n{", """/* the terrain minliquid() acts on (its own first test, inlined at the call sites) */
static inline int
nh_typ_liquidish(schar typ)
{
    return typ == POOL || typ == MOAT || typ == WATER || typ == DRAWBRIDGE_UP || typ == LAVAPOOL || typ == FOUNTAIN;
}
static inline int
nh_typ_special(schar typ)
{""")
t=(src/'src/mon.c').read_text()
n=t.count("if (minliquid(mtmp))"); assert n==2, n
t=t.replace("if (minliquid(mtmp))", "if ((mtmp->data->mlet == S_EEL || nh_typ_liquidish(TYP_AT(mtmp->mx, mtmp->my))) && minliquid(mtmp)) /* minliquid()'s first test, inlined */")
(src/'src/mon.c').write_text(t); print('v1.7 applied')
