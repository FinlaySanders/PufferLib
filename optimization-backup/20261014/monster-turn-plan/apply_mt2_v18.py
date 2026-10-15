"""v1.8: six exact slices from the cycle/mispredict profile (each a pure transformation: same decisions, same draws, same display).
 E1 nle_fill_fixed_tm(): memoise the fake clock per thread (it re-seeded a 4 KB ISAAC64 state on nearly every turn: 1.5% of all Ir)
 E2 mt2_eligible(): the monster-status tests as masked 64-bit word compares, masks calibrated at first use by probing each field
 E3 lined_up(): decide throws_rocks()||m_carrying(WAN_STRIKING) only where linedup() consults it (after the clear-path test fails);
    m_move_fast(): skip lined_up() when appr != 1 and it could neither draw (Upolyd) nor reach the path tests (geometry), setting tbx/tby
 E4 engravings: per-column presence bitmap (level.move_columns[].engr) maintained by every list writer; engr_at() returns NULL without the walk
 E5 monster-list walks (movemon, mcalcdistress, mcalcmove loop, dmonsfree): prefetch the next monster (no semantic effect)
 E6 nh_track_near padded by one cell on each side: settrack()'s 3x3 update needs no clamps (hero positions are in range)"""
from pathlib import Path
src = Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rep(p, old, new, count=1):
    t = (src / p).read_text(); assert t.count(old) == count, (p, t.count(old), old[:90]); (src / p).write_text(t.replace(old, new))

# ---------------- E1: fixed-clock memo ----------------
rep('src/nlernd.c', """    isaac64_ctx time_rng;
    unsigned char seed_bytes[sizeof(seed)];

    memcpy(seed_bytes, &seed, sizeof(seed_bytes));
    isaac64_init(&time_rng, seed_bytes, sizeof(seed_bytes));

    tm->tm_year = 100 + (int) isaac64_next_uint(&time_rng, 50);
    tm->tm_mon = (int) isaac64_next_uint(&time_rng, 12);
    tm->tm_mday = 1 + (int) isaac64_next_uint(&time_rng, 28);
    tm->tm_hour = (int) isaac64_next_uint(&time_rng, 24);
    tm->tm_wday = (int) isaac64_next_uint(&time_rng, 7);
    tm->tm_yday = tm->tm_mon * 30 + tm->tm_mday;
""", """    isaac64_ctx time_rng;
    unsigned char seed_bytes[sizeof(seed)];
    /* v1.8: a pure function of the seed, asked for on nearly every turn (night()/midnight()/moon tests): memoise the six
       fields it writes per thread instead of re-seeding a 4 KB ISAAC64 state each time; only those six fields are copied */
    static __thread struct { int year, mon, mday, hour, wday, yday; unsigned long seed; int valid; } nh_tm_memo;

    if (nh_tm_memo.valid && nh_tm_memo.seed == seed) {
        tm->tm_year = nh_tm_memo.year; tm->tm_mon = nh_tm_memo.mon; tm->tm_mday = nh_tm_memo.mday;
        tm->tm_hour = nh_tm_memo.hour; tm->tm_wday = nh_tm_memo.wday; tm->tm_yday = nh_tm_memo.yday;
        return;
    }
    memcpy(seed_bytes, &seed, sizeof(seed_bytes));
    isaac64_init(&time_rng, seed_bytes, sizeof(seed_bytes));

    tm->tm_year = 100 + (int) isaac64_next_uint(&time_rng, 50);
    tm->tm_mon = (int) isaac64_next_uint(&time_rng, 12);
    tm->tm_mday = 1 + (int) isaac64_next_uint(&time_rng, 28);
    tm->tm_hour = (int) isaac64_next_uint(&time_rng, 24);
    tm->tm_wday = (int) isaac64_next_uint(&time_rng, 7);
    tm->tm_yday = tm->tm_mon * 30 + tm->tm_mday;
    nh_tm_memo.year = tm->tm_year; nh_tm_memo.mon = tm->tm_mon; nh_tm_memo.mday = tm->tm_mday;
    nh_tm_memo.hour = tm->tm_hour; nh_tm_memo.wday = tm->tm_wday; nh_tm_memo.yday = tm->tm_yday;
    nh_tm_memo.seed = seed; nh_tm_memo.valid = 1;
""")

# ---------------- E2: eligibility word masks ----------------
rep('src/monmove.c', '#include "nh_ctx_files/region_c.h"\n', '#include "nh_ctx_files/region_c.h"\n#include <pthread.h> /* v1.8: eligibility mask calibration */\n')
rep('src/monmove.c', """int
mt2_eligible(m)
struct monst *m;
{
    const struct permonst *p = m->data;

    if (m->mtame) return MT2WHY(0);""", """/* v1.8: the per-monster status part of the predicate as masked 64-bit word compares. The masks are calibrated once by
   probing each field on a zeroed struct monst (set the field, record the bytes it occupies), so no layout is assumed; a
   field that must be zero contributes its bits to the mask only, a field that must be all-ones (mcansee, mcanmove,
   cham == NON_PM) to the mask and the wanted value. Pure, so the test order is irrelevant. */
struct nh_mt2_ew { int n; unsigned off[8]; unsigned long long mask[8], want[8]; };
static struct nh_mt2_ew nh_mt2_ew;
static int nh_mt2_ew_ready;
static pthread_once_t nh_mt2_ew_once = PTHREAD_ONCE_INIT;
static void
nh_mt2_ew_probe(unsigned char *mb, unsigned char *wb, const struct monst *m, int want_ones)
{
    const unsigned char *b = (const unsigned char *) m;
    size_t i;
    for (i = 0; i < sizeof *m; i++)
        if (b[i]) { mb[i] |= b[i]; if (want_ones) wb[i] |= b[i]; }
}
#define NH_EW_ZERO(f) do { memset(&pm, 0, sizeof pm); pm.f = ~0; nh_mt2_ew_probe(mb, wb, &pm, 0); } while (0)
#define NH_EW_ONES(f) do { memset(&pm, 0, sizeof pm); pm.f = ~0; nh_mt2_ew_probe(mb, wb, &pm, 1); } while (0)
static void
nh_mt2_ew_init(void)
{
    struct monst pm;
    unsigned char mb[sizeof(struct monst)], wb[sizeof(struct monst)];
    size_t off;
    memset(mb, 0, sizeof mb); memset(wb, 0, sizeof wb);
    NH_EW_ZERO(mtame); NH_EW_ZERO(m_ap_type); NH_EW_ZERO(mundetected); NH_EW_ZERO(mflee); NH_EW_ZERO(msleeping);
    NH_EW_ZERO(mstun); NH_EW_ZERO(mconf); NH_EW_ZERO(mtrapped); NH_EW_ZERO(isshk); NH_EW_ZERO(isgd); NH_EW_ZERO(ispriest);
    NH_EW_ZERO(iswiz); NH_EW_ZERO(wormno); NH_EW_ZERO(mstrategy); NH_EW_ZERO(meating);
    NH_EW_ONES(mcansee); NH_EW_ONES(mcanmove); NH_EW_ONES(cham); /* NON_PM == -1: all ones */
    nh_mt2_ew.n = 0;
    for (off = 0; off + 8 <= sizeof(struct monst); off += 8) {
        unsigned long long mk = 0, wt = 0;
        int k;
        for (k = 7; k >= 0; k--) { mk = (mk << 8) | mb[off + k]; wt = (wt << 8) | wb[off + k]; }
        if (mk) {
            if (nh_mt2_ew.n == 8) panic("nh_mt2_ew_init: too many words");
            nh_mt2_ew.off[nh_mt2_ew.n] = (unsigned) off; nh_mt2_ew.mask[nh_mt2_ew.n] = mk; nh_mt2_ew.want[nh_mt2_ew.n] = wt;
            nh_mt2_ew.n++;
        }
    }
    __atomic_store_n(&nh_mt2_ew_ready, 1, __ATOMIC_RELEASE);
}
static inline int
mt2_status_ok(const struct monst *m)
{
    const unsigned char *b = (const unsigned char *) m;
    int i;
    if (!__atomic_load_n(&nh_mt2_ew_ready, __ATOMIC_ACQUIRE)) pthread_once(&nh_mt2_ew_once, nh_mt2_ew_init);
    for (i = 0; i < nh_mt2_ew.n; i++) {
        unsigned long long w;
        memcpy(&w, b + nh_mt2_ew.off[i], 8);
        if ((w & nh_mt2_ew.mask[i]) != nh_mt2_ew.want[i]) return 0;
    }
    return 1;
}
static int
mt2_eligible_fast(struct monst *m)
{
    if (!mt2_status_ok(m) || m == u.ustuck) return 0;
    if (nh_spw[m->data - mons] & SPW_MT2_NOFAST) return 0;
    if (mt2_hero_bad()) return 0;
    {
        int ddx = abs(m->mx - u.ux), ddy = abs(m->my - u.uy);
        if ((ddx > ddy ? ddx : ddy) <= 1) return 0;
    }
    return 1;
}
#ifdef NH_MT2_CG
static int mt2_eligible_slow(struct monst *m);
int
mt2_eligible(m)
struct monst *m;
{
    int slow = mt2_eligible_slow(m), fast = mt2_eligible_fast(m); /* census build: the original chain stays the authority */
    if (slow != fast) fprintf(stderr, "MT2_ELIG_MISMATCH id%u slow %d fast %d\\n", m->m_id, slow, fast);
    return slow;
}
static int
mt2_eligible_slow(struct monst *m)
#else
int
mt2_eligible(m)
struct monst *m;
{
    return mt2_eligible_fast(m);
}
static int
mt2_eligible_slow(struct monst *m) __attribute__((unused));
static int
mt2_eligible_slow(struct monst *m)
#endif
{
    const struct permonst *p = m->data;

    if (m->mtame) return MT2WHY(0);""")

# ---------------- E3: lined_up lazy boulder handling + m_move_fast skip ----------------
rep('src/mthrowu.c', """/* is mtmp in position to use ranged attack? */
boolean
lined_up(mtmp)
register struct monst *mtmp;
{
    boolean ignore_boulders;

    /* hero concealment usually trumps monst awareness of being lined up */
    if (Upolyd && rn2(25)
        && (u.uundetected || (U_AP_TYPE != M_AP_NOTHING
                              && U_AP_TYPE != M_AP_MONSTER)))
        return FALSE;

    ignore_boulders = (throws_rocks(mtmp->data)
                       || m_carrying(mtmp, WAN_STRIKING));
    return linedup(mtmp->mux, mtmp->muy, mtmp->mx, mtmp->my,
                   ignore_boulders ? 1 : 2);
}
""", """/* v1.8: linedup(mux, muy, mx, my, ignore_boulders ? 1 : 2) with the boulder decision taken where linedup() first consults it
   (after the clear-path test fails); throws_rocks() and m_carrying() are pure, so the result and the draws are identical */
STATIC_OVL boolean
nh_linedup_lazy(mtmp)
struct monst *mtmp;
{
    register xchar ax = mtmp->mux, ay = mtmp->muy, bx = mtmp->mx, by = mtmp->my;
    int dx, dy, boulderspots;

    /* These two values are set for use after successful return. */
    tbx = ax - bx;
    tby = ay - by;

    /* sometimes displacement makes a monster think that you're at its
       own location; prevent it from throwing and zapping in that case */
    if (!tbx && !tby)
        return FALSE;

    if ((!tbx || !tby || abs(tbx) == abs(tby)) /* straight line or diagonal */
        && distmin(tbx, tby, 0, 0) < BOLT_LIM) {
        boolean ignore_boulders;
        if ((ax == u.ux && ay == u.uy) ? (boolean) couldsee(bx, by)
                                       : clear_path(ax, ay, bx, by))
            return TRUE;
        /* don't have line of sight, but might still be lined up
           if that lack of sight is due solely to boulders */
        ignore_boulders = (throws_rocks(mtmp->data)
                           || m_carrying(mtmp, WAN_STRIKING)); /* boulderhandling 1 : 2, never 0 */
        dx = sgn(ax - bx), dy = sgn(ay - by);
        boulderspots = 0;
        do {
            /* <bx,by> is guaranteed to eventually converge with <ax,ay> */
            bx += dx, by += dy;
            if (IS_ROCK(NH_TILE(bx, by).typ) || closed_door(bx, by))
                return FALSE;
            if (sobj_at(BOULDER, bx, by))
                ++boulderspots;
        } while (bx != ax || by != ay);
        /* reached target position without encountering obstacle */
        if (ignore_boulders || rn2(2 + boulderspots) < 2)
            return TRUE;
    }
    return FALSE;
}

/* is mtmp in position to use ranged attack? */
boolean
lined_up(mtmp)
register struct monst *mtmp;
{
    /* hero concealment usually trumps monst awareness of being lined up */
    if (Upolyd && rn2(25)
        && (u.uundetected || (U_AP_TYPE != M_AP_NOTHING
                              && U_AP_TYPE != M_AP_MONSTER)))
        return FALSE;

    return nh_linedup_lazy(mtmp);
}
""")
rep('src/monmove.c', """    if ((!mtmp->mpeaceful || !rn2(10)) && !Is_rogue_level(&u.uz)) { /* the draw precedes the level test in the original */
        boolean in_line = (lined_up(mtmp)
               && (distmin(mtmp->mx, mtmp->my, mtmp->mux, mtmp->muy)
                   <= (throws_rocks(youmonst.data) ? 20 : ACURRSTR / 2 + 1)));
        if (appr != 1 || !in_line) {""", """    if ((!mtmp->mpeaceful || !rn2(10)) && !Is_rogue_level(&u.uz)) { /* the draw precedes the level test in the original */
        boolean in_line = FALSE;
        /* v1.8: in_line is only read when appr == 1. Otherwise lined_up() is still called when it could draw (Upolyd) or
           reach linedup()'s path tests (geometrically lined up within BOLT_LIM); in the remaining case its only effect is
           tbx/tby, set here exactly as linedup() sets them before returning FALSE. */
        if (appr == 1 || Upolyd || nh_lined_geom(mtmp)) {
            in_line = (lined_up(mtmp)
                   && (distmin(mtmp->mx, mtmp->my, mtmp->mux, mtmp->muy)
                       <= (throws_rocks(youmonst.data) ? 20 : ACURRSTR / 2 + 1)));
        } else {
            tbx = mtmp->mux - mtmp->mx;
            tby = mtmp->muy - mtmp->my;
        }
        if (appr != 1 || !in_line) {""")
rep('src/monmove.c', """/* *in_rooms(x, y, SHOPBASE) != '\\0' */
static inline int
mt2_in_shop(int x, int y)""", """/* linedup()'s pure geometric pre-tests: FALSE means lined_up() sets tbx/tby and returns FALSE without any draw */
static inline int
nh_lined_geom(const struct monst *m)
{
    int dx = m->mux - m->mx, dy = m->muy - m->my, ax = abs(dx), ay = abs(dy);
    return (dx || dy) && (!dx || !dy || ax == ay) && (ax > ay ? ax : ay) < BOLT_LIM;
}

/* *in_rooms(x, y, SHOPBASE) != '\\0' */
static inline int
mt2_in_shop(int x, int y)""")

# ---------------- E4: engraving presence bitmap ----------------
rep('include/movement_masks.h', "struct nh_move_column { unsigned int nonrock, occupied, special, pile, trap, gas, obj, door; };",
    "struct nh_move_column { unsigned int nonrock, occupied, special, pile, trap, gas, obj, door, engr; };")
rep('include/movement_facts.h', "#define NH_MOVE_GAS     8U\n#define NH_MOVE_ALL     15U", "#define NH_MOVE_GAS     8U\n#define NH_MOVE_ENGR    16U\n#define NH_MOVE_ALL     31U")
rep('src/mon.c', "        if (domains & NH_MOVE_GAS) level.move_columns[x].gas = 0;\n", "        if (domains & NH_MOVE_GAS) level.move_columns[x].gas = 0;\n        if (domains & NH_MOVE_ENGR) level.move_columns[x].engr = 0;\n")
rep('src/mklev.c', "nh_tile_clear_entities(NH_MOVE_PILES | NH_MOVE_TRAPS | NH_MOVE_GAS);", "nh_tile_clear_entities(NH_MOVE_PILES | NH_MOVE_TRAPS | NH_MOVE_GAS | NH_MOVE_ENGR);")
rep('src/engrave.c', """engr_at(x, y)
xchar x, y;
{
    register struct engr *ep = head_engr;

    while (ep) {
        if (x == ep->engr_x && y == ep->engr_y)
            return ep;
        ep = ep->nxt_engr;
    }
    return (struct engr *) 0;
}
""", """nh_engr_walk(x, y)
xchar x, y;
{
    register struct engr *ep = head_engr;

    while (ep) {
        if (x == ep->engr_x && y == ep->engr_y)
            return ep;
        ep = ep->nxt_engr;
    }
    return (struct engr *) 0;
}

/* v1.8: per-column presence bits, maintained by every writer of the engraving list (make_engr_at, del_engr, rloc_engr,
   rest_engravings, save_engravings release, level creation); a set bit only says "walk the list". */
static void
nh_engr_bit_update(int x, int y)
{
    if ((unsigned) x < COLNO && (unsigned) y < ROWNO)
        nh_move_set_col_bit(&level.move_columns[x + 1].engr, y, nh_engr_walk((xchar) x, (xchar) y) != 0);
}

struct engr *
engr_at(x, y)
xchar x, y;
{
    if ((unsigned) x < COLNO && (unsigned) y < ROWNO && !((level.move_columns[x + 1].engr >> y) & 1U)) {
#ifdef NH_MT2_CG
        if (nh_engr_walk(x, y)) fprintf(stderr, "ENGR_BITMAP_MISMATCH %d,%d\\n", x, y);
#endif
        return (struct engr *) 0;
    }
    return nh_engr_walk(x, y);
}
""")
rep('src/engrave.c', "struct engr *\nnh_engr_walk(x, y)", "STATIC_OVL struct engr *\nnh_engr_walk(x, y)")
rep('src/engrave.c', """    ep->nxt_engr = head_engr;
    head_engr = ep;
    ep->engr_x = x;
    ep->engr_y = y;
    ep->engr_txt = (char *) (ep + 1);
    Strcpy(ep->engr_txt, s);""", """    ep->nxt_engr = head_engr;
    head_engr = ep;
    ep->engr_x = x;
    ep->engr_y = y;
    nh_engr_bit_update(x, y);
    ep->engr_txt = (char *) (ep + 1);
    Strcpy(ep->engr_txt, s);""")
rep('src/engrave.c', """        if (!ept) {
            impossible("Error in del_engr?");
            return;
        }
    }
    dealloc_engr(ep);
}""", """        if (!ept) {
            impossible("Error in del_engr?");
            return;
        }
    }
    nh_engr_bit_update(ep->engr_x, ep->engr_y);
    dealloc_engr(ep);
}""")
rep('src/engrave.c', """    } while (engr_at(tx, ty) || !goodpos(tx, ty, (struct monst *) 0, 0));

    ep->engr_x = tx;
    ep->engr_y = ty;
}""", """    } while (engr_at(tx, ty) || !goodpos(tx, ty, (struct monst *) 0, 0));

    {
        int ox = ep->engr_x, oy = ep->engr_y;
        ep->engr_x = tx;
        ep->engr_y = ty;
        nh_engr_bit_update(ox, oy);
        nh_engr_bit_update(tx, ty);
    }
}""")
rep('src/engrave.c', """    if (release_data(mode))
        head_engr = 0;
}""", """    if (release_data(mode)) {
        head_engr = 0;
        nh_tile_clear_entities(NH_MOVE_ENGR);
    }
}""")
rep('src/engrave.c', """    head_engr = 0;
    while (1) {
        mread(fd, (genericptr_t) &lth, sizeof lth);
        if (lth == 0)
            return;
        ep = newengr(lth);
        mread(fd, (genericptr_t) ep, sizeof (struct engr) + lth);
        ep->nxt_engr = head_engr;
        head_engr = ep;""", """    head_engr = 0;
    nh_tile_clear_entities(NH_MOVE_ENGR);
    while (1) {
        mread(fd, (genericptr_t) &lth, sizeof lth);
        if (lth == 0)
            return;
        ep = newengr(lth);
        mread(fd, (genericptr_t) ep, sizeof (struct engr) + lth);
        ep->nxt_engr = head_engr;
        head_engr = ep;
        nh_engr_bit_update(ep->engr_x, ep->engr_y);""")

# ---------------- E5: prefetch the next monster in the list walks ----------------
rep('src/mon.c', "        nmtmp = mtmp->nmon;\n", "        nmtmp = mtmp->nmon;\n        if (nmtmp) { __builtin_prefetch(nmtmp); __builtin_prefetch((const char *) nmtmp + 64); } /* v1.8: next monster, no semantic effect */\n")
rep('src/mon.c', """    for (mtmp = fmon; mtmp; mtmp = mtmp->nmon) {
        if (DEADMONSTER(mtmp))
            continue;

        /* must check non-moving monsters once/turn in case they managed""", """    for (mtmp = fmon; mtmp; mtmp = mtmp->nmon) {
        __builtin_prefetch(mtmp->nmon); /* v1.8 */
        if (DEADMONSTER(mtmp))
            continue;

        /* must check non-moving monsters once/turn in case they managed""")
rep('src/mon.c', """    for (mtmp = &fmon; *mtmp;) {
        freetmp = *mtmp;
""", """    for (mtmp = &fmon; *mtmp;) {
        freetmp = *mtmp;
        __builtin_prefetch(freetmp->nmon); /* v1.8 */
""")
rep('src/allmain.c', """                    for (mtmp = fmon; mtmp; mtmp = mtmp->nmon)
                        mtmp->movement += mcalcmove(mtmp);""", """                    for (mtmp = fmon; mtmp; mtmp = mtmp->nmon) {
                        __builtin_prefetch(mtmp->nmon); /* v1.8 */
                        mtmp->movement += mcalcmove(mtmp);
                    }""")

# ---------------- E6: padded hero-track neighbourhood ----------------
rep('include/nh_ctx_gen.h', "    unsigned char g_nh_track_near[COLNO][ROWNO]; /* global: nh_track_near */",
    "    unsigned char g_nh_track_near[COLNO + 2][ROWNO + 2]; /* global: nh_track_near; v1.8: padded, indexed [x + 1][y + 1] */")
rep('src/track.c', """    int x, y;
    for (x = max(0, position->x - 1); x <= min(COLNO - 1, position->x + 1); x++)
        for (y = max(0, position->y - 1); y <= min(ROWNO - 1, position->y + 1); y++)
            nh_track_near[x][y] += delta;""", """    int x, y;
    /* v1.8: padded array, so the 3x3 window needs no clamps (track positions are hero positions: 0..COLNO-1, 0..ROWNO-1) */
    for (x = position->x; x <= position->x + 2; x++)
        for (y = position->y; y <= position->y + 2; y++)
            nh_track_near[x][y] += delta;""")
rep('src/track.c', "    if (x >= 0 && x < COLNO && y >= 0 && y < ROWNO && !nh_track_near[x][y])", "    if (x >= 0 && x < COLNO && y >= 0 && y < ROWNO && !nh_track_near[x + 1][y + 1])")
rep('src/monmove.c', "&& nh_track_near[omx][omy]) {", "&& nh_track_near[omx + 1][omy + 1]) {")
print('v1.8 applied')
