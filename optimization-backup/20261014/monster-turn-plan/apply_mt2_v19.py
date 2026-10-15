"""v1.9: three more exact slices.
 E7  t_at(): per-column trap presence bits (already maintained for the movement kernel) decide "no trap here" without the list walk;
     nh_trap_update() keeps using the raw walk (it runs between the list change and the bit update)
 E11 find_offensive(): which_armor(W_ARMH) is pure and only read after the lined_up() test; evaluate it there
 E12 m_move_fast(): the two *in_rooms(SHOPBASE) tests use mt2_in_shop() (same predicate from the cell's roomno; shared cells still walk)"""
from pathlib import Path
src = Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rep(p, old, new, count=1):
    t = (src / p).read_text()
    if old not in t or new in t: print('  already:', p, old[:50].strip()); return
    assert t.count(old) == count, (p, t.count(old), old[:90]); (src / p).write_text(t.replace(old, new))

# ---------------- E7: trap lookup gate ----------------
rep('src/trap.c', """struct trap *
t_at(x, y)
register int x, y;
{
    register struct trap *trap = ftrap;

    while (trap) {
        if (trap->tx == x && trap->ty == y)
            return trap;
        trap = trap->ntrap;
    }
    return (struct trap *) 0;
}
""", """STATIC_OVL struct trap *
nh_trap_walk(x, y)
register int x, y;
{
    register struct trap *trap = ftrap;

    while (trap) {
        if (trap->tx == x && trap->ty == y)
            return trap;
        trap = trap->ntrap;
    }
    return (struct trap *) 0;
}

/* v1.9: the per-column trap presence bits (maketrap/deltrap/restore/bubble moves keep them via nh_trap_update(), which walks)
   answer "no trap here" without the walk; a set bit only says "walk the list" */
struct trap *
t_at(x, y)
register int x, y;
{
    if ((unsigned) x < COLNO && (unsigned) y < ROWNO && !((level.move_columns[x + 1].trap >> y) & 1U)) {
#ifdef NH_MT2_CG
        if (nh_trap_walk(x, y)) fprintf(stderr, "TRAP_BITMAP_MISMATCH %d,%d\\n", x, y);
#endif
        return (struct trap *) 0;
    }
    return nh_trap_walk(x, y);
}
""")
rep('src/mon.c', """nh_trap_update(int x, int y)
{
    struct trap *t;
    if ((unsigned) x >= COLNO || (unsigned) y >= ROWNO) return;
    t = t_at(x, y);""", """nh_trap_update(int x, int y)
{
    struct trap *t;
    extern struct trap *nh_trap_walk_ext(int, int);
    if ((unsigned) x >= COLNO || (unsigned) y >= ROWNO) return;
    t = nh_trap_walk_ext(x, y); /* v1.9: the raw walk; the bit is being (re)computed here */""")
rep('src/trap.c', """/* v1.9: the per-column trap presence bits""", """struct trap *
nh_trap_walk_ext(int x, int y)
{
    return nh_trap_walk(x, y);
}

/* v1.9: the per-column trap presence bits""")

# ---------------- E11: find_offensive helmet after the lined_up test ----------------
rep('src/muse.c', """    register struct obj *obj;
    boolean reflection_skip = (Reflecting && rn2(2));
    struct obj *helmet = which_armor(mtmp, W_ARMH);

    m.offensive = (struct obj *) 0;
    m.has_offense = 0;
    if (mtmp->mpeaceful || is_animal(mtmp->data) || mindless(mtmp->data)
        || nohands(mtmp->data))
        return FALSE;
    if (u.uswallow)
        return FALSE;
    if (in_your_sanctuary(mtmp, 0, 0))
        return FALSE;
    if (dmgtype(mtmp->data, AD_HEAL)
        && !uwep && !uarmu && !uarm && !uarmh
        && !uarms && !uarmg && !uarmc && !uarmf)
        return FALSE;
    /* all offensive items require orthogonal or diagonal targetting */
    if (!lined_up(mtmp))
        return FALSE;
""", """    register struct obj *obj;
    boolean reflection_skip = (Reflecting && rn2(2));
    struct obj *helmet;

    m.offensive = (struct obj *) 0;
    m.has_offense = 0;
    if (mtmp->mpeaceful || is_animal(mtmp->data) || mindless(mtmp->data)
        || nohands(mtmp->data))
        return FALSE;
    if (u.uswallow)
        return FALSE;
    if (in_your_sanctuary(mtmp, 0, 0))
        return FALSE;
    if (dmgtype(mtmp->data, AD_HEAL)
        && !uwep && !uarmu && !uarm && !uarmh
        && !uarms && !uarmg && !uarmc && !uarmf)
        return FALSE;
    /* all offensive items require orthogonal or diagonal targetting */
    if (!lined_up(mtmp))
        return FALSE;
    helmet = which_armor(mtmp, W_ARMH); /* v1.9: pure, first read below */
""")

# ---------------- E12: shop test from the cell's roomno in the fast move ----------------
t = (src / 'src/monmove.c').read_text()
a = t.index('\nm_move_fast(mtmp)\n'); b = t.index('\ndochug_fast(mtmp)\n')
seg = t[a:b]
assert a < b
assert seg.count("if (*in_rooms(mtmp->mx, mtmp->my, SHOPBASE))") == 1 and seg.count("if (!*in_rooms(mtmp->mx, mtmp->my, SHOPBASE) || !rn2(25)) {") == 1
seg = seg.replace("if (*in_rooms(mtmp->mx, mtmp->my, SHOPBASE))", "if (mt2_in_shop(mtmp->mx, mtmp->my)) /* v1.9: same predicate */")
seg = seg.replace("if (!*in_rooms(mtmp->mx, mtmp->my, SHOPBASE) || !rn2(25)) {", "if (!mt2_in_shop(mtmp->mx, mtmp->my) || !rn2(25)) { /* v1.9: same predicate */")
(src / 'src/monmove.c').write_text(t[:a] + seg + t[b:])
print('v1.9 applied')
