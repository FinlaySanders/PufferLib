"""Monster-turn v2 kernel (bit-exact): see PLAN.md KERNEL DECISIONS. Applies to engines/mt2/source."""
from pathlib import Path
import re
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rd(p): return (src/p).read_text()
def wr(p,t): (src/p).write_text(t)
def rep(p, old, new, count=1):
    t=rd(p); assert t.count(old)==count, (p, t.count(old), old[:80]); wr(p, t.replace(old,new))
def block_from(text, start_marker):
    i=text.index(start_marker); j=text.index('{', i); depth=0; k=j
    while True:
        c=text[k]
        if c=='{': depth+=1
        elif c=='}':
            depth-=1
            if depth==0: break
        k+=1
    return text[i:k+1]

# ---- A. column bitmaps -------------------------------------------------------------------------------------------
rep('include/movement_masks.h', "struct nh_move_column { unsigned int nonrock, occupied; };",
"""struct nh_move_column { unsigned int nonrock, occupied, special, pile, trap, gas, obj; };
/* special: terrain mfndpos() treats specially (door, bars, liquids, drawbridge, altar, air, cloud); pile/trap/gas/obj: NH_SUMMARY entity bits */
static inline void
nh_move_set_col_bit(unsigned int *field, int y, int on)
{
    unsigned int bit = 1U << y;
    if (on) *field |= bit;
    else *field &= ~bit;
}""")
rep('include/hack.h', """static inline void
nh_move_typ_set(int x, int y, schar typ)
{
    nh_typ_plane[x][y] = typ;
    nh_move_set_terrain(level.move_columns, x, y, !IS_ROCK(typ));
}""", """static inline int
nh_typ_special(schar typ)
{
    return typ == DOOR || typ == IRONBARS || typ == ALTAR || (typ >= POOL && typ <= LAVAPOOL)
           || typ == DRAWBRIDGE_DOWN || typ == AIR || typ == CLOUD;
}
static inline void
nh_move_typ_set(int x, int y, schar typ)
{
    nh_typ_plane[x][y] = typ;
    nh_move_set_terrain(level.move_columns, x, y, !IS_ROCK(typ));
    nh_move_set_col_bit(&level.move_columns[x + 1].special, y, nh_typ_special(typ));
}""")
rep('src/mon.c', """    for (o = level.objs[x][y]; o; o = o->nexthere) f |= nh_move_pile(o->otyp);
    NH_SUMMARY(x, y).move_pile = f >> 13;
    NH_SUMMARY(x, y).move_obj_present = OBJ_AT(x, y);
}""", """    for (o = level.objs[x][y]; o; o = o->nexthere) f |= nh_move_pile(o->otyp);
    NH_SUMMARY(x, y).move_pile = f >> 13;
    NH_SUMMARY(x, y).move_obj_present = OBJ_AT(x, y);
    nh_move_set_col_bit(&level.move_columns[x + 1].pile, y, f != 0);
    nh_move_set_col_bit(&level.move_columns[x + 1].obj, y, OBJ_AT(x, y));
}""")
rep('src/mon.c', """    NH_SUMMARY(x, y).move_trap = t ? t->ttyp : 0;
    NH_SUMMARY(x, y).move_trap_present = t != 0;
}""", """    NH_SUMMARY(x, y).move_trap = t ? t->ttyp : 0;
    NH_SUMMARY(x, y).move_trap_present = t != 0;
    nh_move_set_col_bit(&level.move_columns[x + 1].trap, y, t != 0);
}""")
rep('src/mon.c', """nh_tile_clear_entities(unsigned int domains)
{
    int x, y;""", """nh_tile_clear_entities(unsigned int domains)
{
    int x, y;
    for (x = 0; x < COLNO + 2; x++) {
        if (domains & NH_MOVE_PILES) level.move_columns[x].pile = level.move_columns[x].obj = 0;
        if (domains & NH_MOVE_TRAPS) level.move_columns[x].trap = 0;
        if (domains & NH_MOVE_GAS) level.move_columns[x].gas = 0;
    }""")
rep('src/region.c', """        NH_SUMMARY(x, y).move_gas = reg && reg->glyph == cmap_to_glyph(S_poisoncloud);
    }
}""", """        NH_SUMMARY(x, y).move_gas = reg && reg->glyph == cmap_to_glyph(S_poisoncloud);
        nh_move_set_col_bit(&level.move_columns[x + 1].gas, y, NH_SUMMARY(x, y).move_gas);
    }
}""")
t=rd('src/mklev.c'); i=t.index("            NH_SUMMARY(x, y).move_obj_present = 0;"); j=t.index("    xdnladder = ydnladder = xupladder = yupladder = 0;", i)
assert "nh_tile_clear_entities" not in t[i:j]
wr('src/mklev.c', t[:j]+"    nh_tile_clear_entities(NH_MOVE_PILES | NH_MOVE_TRAPS | NH_MOVE_GAS); /* column bits of the per-cell entity summaries cleared above */\n"+t[j:])

# ---- F. species bits + load table ---------------------------------------------------------------------------------
rep('include/hack.h', "#define SPW_RANGED (1ULL << 45)\nextern unsigned long long nh_spw[NUMMONS];",
"""#define SPW_RANGED (1ULL << 45)
#define SPW_NODIAG (1ULL << 46)
#define SPW_HASEYES (1ULL << 47)
#define SPW_RANDAPPR (1ULL << 48)   /* stalker, bats, lights: random approach draw in m_move() */
#define SPW_LEPRECHAUN (1ULL << 49)
#define SPW_MT2_NOFAST (1ULL << 50) /* species the monster-turn fast path leaves on the original code */
extern unsigned long long nh_spw[NUMMONS];
extern short nh_spw_maxload[NUMMONS]; /* max_mon_load() per species */""")
rep('src/mondata.c', """unsigned long long nh_spw[NUMMONS];
static void __attribute__((constructor))
nh_spw_init(void)
{
    int i;
    for (i = 0; i < NUMMONS; i++) {
        const struct permonst *p = &mons[i];
        unsigned long long w = 0;""", """unsigned long long nh_spw[NUMMONS];
short nh_spw_maxload[NUMMONS];
static void __attribute__((constructor))
nh_spw_init(void)
{
    int i;
    for (i = 0; i < NUMMONS; i++) {
        const struct permonst *p = &mons[i];
        unsigned long long w = 0;
        struct monst fake;
        (void) memset((genericptr_t) &fake, 0, sizeof fake);
        fake.data = (struct permonst *) p;
        nh_spw_maxload[i] = (short) max_mon_load(&fake); /* reads only mtmp->data */
        if (NODIAG(i)) w |= SPW_NODIAG;
        if (haseyes(p)) w |= SPW_HASEYES;
        if (i == PM_STALKER || p->mlet == S_BAT || p->mlet == S_LIGHT) w |= SPW_RANDAPPR;
        if (i == PM_LEPRECHAUN) w |= SPW_LEPRECHAUN;
        if (is_covetous(p) || tunnels(p) || passes_walls(p) || is_watch(p) || is_mind_flayer(p) || p->mlet == S_EEL
            || is_hider(p) || p->msound == MS_SHRIEK || p->msound == MS_NEMESIS || i == PM_MEDUSA || i == PM_TENGU
            || (p->mflags3 & M3_DISPLACES) || i == PM_PURPLE_WORM || is_unicorn(p) || is_rider(p) || p->mlet == S_GHOST
#ifdef MAIL
            || i == PM_MAIL_DAEMON
#endif
            )
            w |= SPW_MT2_NOFAST;""")

# ---- G. muse replicas ---------------------------------------------------------------------------------------------
rep('src/muse.c', """#define m     (*nle_musable())""", """#define m     (*nle_musable())

/* monster-turn fast path (monmove.c): the observable side effects of find_misc()/find_offensive() for a monster that returns
   FALSE by distance. find_misc() clears m.misc before its early return; find_defensive() returns before touching m. */
void
nh_muse_far_misc()
{
    m.misc = (struct obj *) 0;
    m.has_misc = 0;
}

/* find_offensive() for a monster at distmin >= BOLT_LIM while !Reflecting && !Upolyd: no RNG draw, lined_up() can only
   store tbx/tby and fail the range test, so the result is always FALSE. */
boolean
find_offensive_far(mtmp)
struct monst *mtmp;
{
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
    tbx = mtmp->mux - mtmp->mx;
    tby = mtmp->muy - mtmp->my;
    return FALSE;
}""")

# ---- H. display replica -------------------------------------------------------------------------------------------
rep('src/display.c', """/* FIXME: This is a dirty hack, because newsym() doesn't distinguish""", """/* nh_newsym_moved() for the monster-turn fast path: the caller guarantees !u.uswallow, !Underwater and <x,y> != hero. */
void
nh_newsym_moved_far(x, y)
int x, y;
{
    register struct rm *lev;
    struct monst *mon;
    int s = nh_display_sense;
    gbuf_state *gb;

    if (!(s & NH_SENSE_VALID) || (s & NH_SENSE_SPECIAL) || cansee(x, y))
        goto full;
    if ((s & ~NH_SENSE_VALID) && (mon = m_at(x, y)) != 0) {
        if ((s & NH_SENSE_DETECT)
            || ((s & NH_SENSE_TPBLIND) && !mindless(mon->data))
            || ((s & NH_SENSE_TP) && !mindless(mon->data) && distu(mon->mx, mon->my) <= (BOLT_LIM * BOLT_LIM))
            || ((s & NH_SENSE_WARNMON) && MATCH_WARN_OF_MON(mon))
            || ((s & NH_SENSE_INFRA) && infravisible(mon->data) && couldsee(mon->mx, mon->my))
            || ((s & NH_SENSE_WARNING) && mon_warning(mon)))
            goto full;
    }
    lev = &(NH_TILE(x, y));
    if ((!lev->waslit || (flags.dark_room && iflags.use_color))
        && ((lev->glyph == cmap_to_glyph(S_litcorr) && lev->typ == CORR)
            || (lev->glyph == cmap_to_glyph(S_room) && lev->typ == ROOM)))
        goto full;
    gb = (gbuf_state *) nh_cur->nh_lazy[15];
    if (!gb || gb->glyph[y][x] != lev->glyph)
        goto full;
    return;
 full:
    newsym(x, y);
}

/* FIXME: This is a dirty hack, because newsym() doesn't distinguish""")

# ---- declarations -------------------------------------------------------------------------------------------------
rep('include/extern.h', "E int FDECL(dochugw, (struct monst *));", """E int FDECL(dochugw, (struct monst *));
E int FDECL(mt2_eligible, (struct monst *));
E void NDECL(nh_muse_far_misc);
E boolean FDECL(find_offensive_far, (struct monst *));
E void FDECL(nh_newsym_moved_far, (int, int));""")

# ---- I. monmove.c -------------------------------------------------------------------------------------------------
mm=rd('src/monmove.c')
door_block=mm[mm.index("            /* open a door, or crash through it, if 'mtmp' can */"):mm.index("            /* possibly dig */")]
pickup_block=block_from(mm, "        if (nh_move_obj_at(mtmp->mx, mtmp->my) && mtmp->mcanmove) {")
hides_block=block_from(mm, "        if (SPWQ(ptr, SPW_HIDESUNDER, hides_under(ptr)) || ptr->mlet == S_EEL) {")
search_block=block_from(mm, "    {\n        register int minr = SQSRCHRADIUS; /* not too far away */")
assert door_block.count('\n')>60 and pickup_block.count('\n')>30 and hides_block.count('\n')>5 and search_block.count('\n')>80
s2=search_block.replace("(!*in_rooms(omx, omy, SHOPBASE)", "(!mt2_in_shop(omx, omy)")
s2=s2.replace("for (otmp = nh_fobj_next(&cursor, (struct obj *) 0, lmx, oomx, lmy, oomy);",
              "for (otmp = mt2_box_has_objects(lmx, oomx, lmy, oomy) ? nh_fobj_next(&cursor, (struct obj *) 0, lmx, oomx, lmy, oomy) : (struct obj *) 0;")
assert s2!=search_block and s2.count("mt2_box_has_objects")==1 and s2.count("mt2_in_shop")==1

# dochugw: canspotmon only when its result can be read
rep('src/monmove.c', "    boolean already_saw_mon = !occupation ? 0 : canspotmon(mtmp);",
    "    boolean already_saw_mon = (!occupation || distu(x, y) > (BOLT_LIM + 1) * (BOLT_LIM + 1)) ? 0 : canspotmon(mtmp); /* unread beyond that range */")

kernel = r'''
/* ===================================================================================================================
 * Monster-turn v2 (mt2): exact fast path for an ordinary hostile monster far from (distmin > 9) and unseen by the hero.
 * mt2_eligible() excludes every monster, species, hero and level state under which any skipped original statement could
 * have an effect; what remains is evaluated in the original order with the original RNG draws. Runtime switch: NH_MT2=0.
 * =================================================================================================================== */
#include <stdlib.h>
int nh_mt2_fast = 1;
static void __attribute__((constructor))
nh_mt2_init(void)
{
    const char *e = getenv("NH_MT2");
    if (e && *e == '0')
        nh_mt2_fast = 0;
}
#ifdef NH_MT2_TRACE
#include <stdio.h>
#include "isaac64.h"
extern isaac64_ctx *FDECL(nle_rng_state, (int));
FILE *nh_mt2_trace_fp;
int nh_mt2_trace_elig;
static void
mt2_trace(struct monst *m, int omx, int omy, int gx, int gy, int appr, int cnt, coord *poss, long *info, int chi, int nix, int niy, int mmoved)
{
    int i;
    if (!nh_mt2_trace_fp) {
        const char *p = getenv("NH_MT2_TRACE");
        if (!p || !(nh_mt2_trace_fp = fopen(p, "w"))) return;
    }
    fprintf(nh_mt2_trace_fp, "%ld id%u pm%d %d,%d g%d,%d a%d c%d", moves, m->m_id, monsndx(m->data), omx, omy, gx, gy, appr, cnt);
    for (i = 0; i < cnt; i++) fprintf(nh_mt2_trace_fp, " %d,%d/%lx", poss[i].x, poss[i].y, info[i]);
    fprintf(nh_mt2_trace_fp, " -> %d %d,%d m%d rng%d\n", chi, nix, niy, mmoved, nle_rng_state(0)->n);
}
#define MT2_TRACE(...) do { if (nh_mt2_trace_elig) mt2_trace(__VA_ARGS__); } while (0)
#else
#define MT2_TRACE(...) do { } while (0)
#endif

int
mt2_eligible(m)
struct monst *m;
{
    const struct permonst *p = m->data;

    if (m->mtame || m->mpeaceful || m->isshk || m->ispriest || m->isgd || m->iswiz || m->wormno || m->mstrategy)
        return 0;
    if (m->mconf || m->mstun || m->mtrapped || m->meating || !m->mcanmove || m->msleeping || !m->mcansee || m->mflee
        || m->mundetected || M_AP_TYPE(m) != M_AP_NOTHING || m->cham != NON_PM || m == u.ustuck)
        return 0;
    if (nh_spw[p - mons] & SPW_MT2_NOFAST)
        return 0;
    if (u.uswallow || Underwater || Invis || Displaced || Hallucination || Conflict || Upolyd || Reflecting
        || u.uundetected || U_AP_TYPE != M_AP_NOTHING)
        return 0;
    if (distmin(m->mx, m->my, u.ux, u.uy) <= 9)
        return 0;
    if (viz_array[m->my][m->mx] & COULD_SEE)
        return 0;
    return 1;
}

/* *in_rooms(x, y, SHOPBASE) != '\0' */
static inline int
mt2_in_shop(int x, int y)
{
    int rno = NH_TILE(x, y).roomno;
    if (rno == NO_ROOM) return 0;
    if (rno >= ROOMOFFSET) return rooms[rno - ROOMOFFSET].rtype >= SHOPBASE;
    return *in_rooms(x, y, SHOPBASE) != '\0';
}

/* any floor object inside the search box: the search loop body has no effect when it never runs */
static inline int
mt2_box_has_objects(int lx, int hx, int ly, int hy)
{
    unsigned int rows = (2U << hy) - (1U << ly), acc = 0;
    int x;
    for (x = lx; x <= hx; x++) acc |= level.move_columns[x + 1].obj;
    return (acc & rows) != 0;
}

static int
m_move_fast(mtmp)
register struct monst *mtmp;
{
    struct permonst *ptr = mtmp->data;
    unsigned long long spw = nh_spw[ptr - mons];
    register int appr;
    xchar gx, gy, nix, niy, chcnt = 0;
    int chi, cnt;
    boolean likegold = 0, likegems = 0, likeobjs = 0, likemagic = 0, conceals = 0;
    boolean likerock = 0, can_tunnel = 0;
    boolean can_open = 0, can_unlock = 0, doorbuster = 0;
    boolean uses_items = 0, setlikes = 0;
    boolean plain;
    struct monst *mtoo;
    schar mmoved = 0;
    long info[9];
    long flag;
    int omx = mtmp->mx, omy = mtmp->my;
    struct nh_move_column *cols = &level.move_columns[omx];
    coord poss[9];

    /* mtrapped and meating are excluded; sawmon (vampshifter) is excluded */
    if ((spw & SPW_HIDESUNDER) && NH_SUMMARY(omx, omy).move_obj_present && rn2(10))
        return 0; /* do not leave hiding place */

    mtmp->mux = u.ux; /* set_apparxy(): found_you */
    mtmp->muy = u.uy;
    can_open = !(spw & (SPW_NOHANDS | SPW_VERYSMALL));
    doorbuster = (spw & SPW_GIANT) != 0;
    /* can_unlock (three inventory walks) is only read with a door in reach: computed on the fallback path */

    gx = mtmp->mux;
    gy = mtmp->muy;
    appr = 1; /* !mflee; !mconf; should_see is FALSE beyond dist2 36; !mcansee, Invis, disguise, peaceful are excluded */
    if ((spw & SPW_RANDAPPR) && !rn2(3))
        appr = 0;
    if ((spw & SPW_LEPRECHAUN) && (appr == 1)) {
        struct obj *lepgold, *ygold;
        if ((lepgold = findgold(mtmp->minvent))
            && (lepgold->quan > ((ygold = findgold(invent)) ? ygold->quan : 0L)))
            appr = -1;
    }
    if (((uwep && uwep->oartifact == ART_EXCALIBUR) || (spw & SPW_HASEYES)) && nh_track_near[omx][omy]) {
        register coord *cp = gettrack(omx, omy);
        if (cp) {
            gx = cp->x;
            gy = cp->y;
        }
    }

    if (!Is_rogue_level(&u.uz)) { /* hostile: no rn2(10) draw */
        /* in_line is FALSE at distmin >= 9: lined_up() draws nothing (!Upolyd) and linedup() only stores tbx/tby */
        register int pctload = 0;
        tbx = mtmp->mux - omx;
        tby = mtmp->muy - omy;
        if ((spw & (SPW_LIKEGOLD | SPW_LIKEGEMS | SPW_LIKEOBJS | SPW_LIKEMAGIC | SPW_THROWSROCKS))
            || !(spw & (SPW_MINDLESS | SPW_ANIMAL)))
            pctload = (curr_mon_load(mtmp) * 100) / nh_spw_maxload[ptr - mons];
        likegold = ((spw & SPW_LIKEGOLD) && pctload < 95);
        likegems = ((spw & SPW_LIKEGEMS) && pctload < 85);
        uses_items = (!(spw & (SPW_MINDLESS | SPW_ANIMAL)) && pctload < 75);
        likeobjs = ((spw & SPW_LIKEOBJS) && pctload < 75);
        likemagic = ((spw & SPW_LIKEMAGIC) && pctload < 85);
        likerock = ((spw & SPW_THROWSROCKS) && pctload < 50 && !Sokoban);
        conceals = (spw & SPW_HIDESUNDER) != 0;
        setlikes = TRUE;
    }

''' + s2 + r'''

    /* can_tunnel: excluded */
    nix = omx;
    niy = omy;
    {
        unsigned int bad = nh_move_neighbours(cols[0].special | cols[0].pile | cols[0].trap | cols[0].gas,
                                              cols[1].special | cols[1].pile | cols[1].trap | cols[1].gas,
                                              cols[2].special | cols[2].pile | cols[2].trap | cols[2].gas, omy);
        plain = !bad && !(((cols[1].special | cols[1].gas) >> omy) & 1U) && !level.lflags.has_temple && !Sokoban;
    }
    if (plain) {
        /* mfndpos() for a window of plain floor: every per-cell test of the original is decided by the masks */
        unsigned int nonrock_n = nh_move_neighbours(cols[0].nonrock, cols[1].nonrock, cols[2].nonrock, omy);
        unsigned int occ = nh_move_neighbours(cols[0].occupied, cols[1].occupied, cols[2].occupied, omy);
        unsigned int cand = nonrock_n & ~occ;
        if (spw & SPW_NODIAG) {
            cand &= 0x0aaU;
        } else if (cand & 0x145U) {
            unsigned int r1 = !((nonrock_n >> 1) & 1U), r3 = !((nonrock_n >> 3) & 1U), r5 = !((nonrock_n >> 5) & 1U), r7 = !((nonrock_n >> 7) & 1U);
            unsigned int squeeze_n = (r1 & r3) | ((r1 & r5) << 2) | ((r7 & r3) << 6) | ((r7 & r5) << 8);
            unsigned int o1 = (occ >> 1) & 1U, o3 = (occ >> 3) & 1U, o5 = (occ >> 5) & 1U, o7 = (occ >> 7) & 1U;
            unsigned int worm_n = (o1 & o3) | ((o1 & o5) << 2) | ((o7 & o3) << 6) | ((o7 & o5) << 8);
            if ((cand & squeeze_n) && cant_squeeze_thru(mtmp))
                cand &= ~squeeze_n;
            worm_n &= cand;
            while (worm_n) {
                int b = __builtin_ctz(worm_n);
                worm_n &= worm_n - 1;
                if (worm_cross(omx, omy, omx - 1 + b / 3, omy - 1 + b % 3))
                    cand &= ~(1U << b);
            }
        }
        cnt = 0;
        while (cand) {
            int b = __builtin_ctz(cand), nx, ny, dx, dy;
            cand &= cand - 1;
            nx = omx - 1 + b / 3;
            ny = omy - 1 + b % 3;
            dx = nx - u.ux;
            dy = ny - u.uy;
            info[cnt] = (!dx || !dy || dx == dy || dx == -dy) ? NOTONL : 0L; /* monseeu && onlineu() */
            poss[cnt].x = nx;
            poss[cnt].y = ny;
            cnt++;
        }
        flag = ALLOW_U;
    } else {
        can_unlock = (can_open && monhaskey(mtmp, TRUE));
        flag = ALLOW_U;
        if (spw & SPW_MINION)
            flag |= ALLOW_SANCT;
        if (spw & SPW_PASSBARS)
            flag |= ALLOW_BARS;
        if ((spw & SPW_HUMAN) || ptr == &mons[PM_MINOTAUR])
            flag |= ALLOW_SSM;
        if ((spw & SPW_UNDEAD) && ptr->mlet != S_GHOST)
            flag |= NOGARLIC;
        if (spw & SPW_THROWSROCKS)
            flag |= ALLOW_ROCK;
        if (can_open)
            flag |= OPENDOOR;
        if (can_unlock)
            flag |= UNLOCKDOOR;
        if (doorbuster)
            flag |= BUSTDOOR;
        cnt = mfndpos(mtmp, poss, info, flag);
    }
    {
        register int i, j, nx, ny, nearer;
        unsigned int trackmask;
        int jcnt;
        int ndist, nidist;
        register coord *mtrk;

        chcnt = 0;
        jcnt = min(MTSZ, cnt - 1);
        trackmask = 0;
        for (j = 0; j < jcnt; j++)
            trackmask |= nh_move_position_bit(omx, omy, mtmp->mtrack[j].x, mtmp->mtrack[j].y);
        chi = -1;
        nidist = dist2(nix, niy, gx, gy);
        if (level.lflags.shortsighted
            && nidist > (couldsee(nix, niy) ? 144 : 36) && appr == 1)
            appr = 0;
        /* avoid (unicorn) and should_displace (ALLOW_MDISP) cannot apply to this population */
        for (i = 0; i < cnt; i++) {
            nx = poss[i].x;
            ny = poss[i].y;
            if (appr != 0 && (trackmask & nh_move_position_bit(omx, omy, nx, ny))) {
                unsigned int hits = 0;
                mtrk = &mtmp->mtrack[0];
                for (j = 0; j < MTSZ; j++)
                    hits |= (unsigned int) ((j < jcnt) & (nx == mtrk[j].x) & (ny == mtrk[j].y)) << j;
                while (hits) {
                    j = __builtin_ctz(hits);
                    hits &= hits - 1;
                    if (rn2(4 * (cnt - j)))
                        goto nxti;
                }
            }
            ndist = dist2(nx, ny, gx, gy);
            nearer = (ndist < nidist);
            {
                int take = appr ? ((nearer != (appr < 0)) | !mmoved) : (!rn2(++chcnt) | !mmoved);
                int m = -take;
                nix = (xchar) ((nx & m) | (nix & ~m));
                niy = (xchar) ((ny & m) | (niy & ~m));
                nidist = (ndist & m) | (nidist & ~m);
                chi = (i & m) | (chi & ~m);
                mmoved |= (schar) take;
            }
 nxti:
            ;
        }
    }
    MT2_TRACE(mtmp, omx, omy, gx, gy, appr, cnt, poss, info, chi, nix, niy, mmoved);

    if (mmoved) {
        register int j;
        /* itsstuck(): not u.ustuck; m_digweapon_check(): no tunneller; ALLOW_U/ALLOW_M/ALLOW_MDISP cannot be set here */
        if (n_regions && !m_in_out_region(mtmp, nix, niy))
            return 3;
        remove_monster(omx, omy);
        mtmp->mx = nix, mtmp->my = niy; /* place_monster() without its consistency diagnostics */
        NH_SET_MON(nix, niy, mtmp);
        mtmp->mstate &= ~(MON_OFFMAP | MON_MIGRATING | MON_LIMBO | MON_BUBBLEMOVE | MON_ENDGAME_FREE | MON_ENDGAME_MIGR);
        for (j = MTSZ - 1; j > 0; j--)
            mtmp->mtrack[j] = mtmp->mtrack[j - 1];
        mtmp->mtrack[0].x = omx;
        mtmp->mtrack[0].y = omy;
    }
    /* !mmoved: unicorn teleport and worms are excluded */
 postmov:
    if (mmoved == 1 || mmoved == 3) {
        boolean canseeit = cansee(mtmp->mx, mtmp->my);

        if (mmoved == 1) {
            nix = mtmp->mx, niy = mtmp->my;
            /* vampshifter door shift: excluded */
            nh_newsym_moved_far(omx, omy); /* update the old position */
            if (NH_SUMMARY(mtmp->mx, mtmp->my).move_trap_present) { /* mintrap() without a trap only clears mtrapped (already 0) */
                if (mintrap(mtmp) >= 2) {
                    if (mtmp->mx)
                        newsym(mtmp->mx, mtmp->my);
                    return 2; /* it died */
                }
                ptr = mtmp->data; /* in case mintrap() caused polymorph */
            }

''' + door_block + r'''
            /* can_tunnel and u.uswallow: excluded */
            nh_newsym_moved_far(mtmp->mx, mtmp->my);
        }
''' + pickup_block + '\n' + hides_block + r'''
        /* isshk: excluded */
    }
    return mmoved;
}

/* dochug() for an eligible monster: the pre-move chain is inert at this distance (PLAN.md KERNEL DECISIONS 2) */
static int
dochug_fast(mtmp)
register struct monst *mtmp;
{
    register struct permonst *mdat = mtmp->data;
    register int tmp = 0;
    int inrange = 0, nearby = 0, scared = 0;

    if (head_engr) /* wipe_engr_at() is a no-op without an engraving on the level */
        wipe_engr_at(mtmp->mx, mtmp->my, 1, FALSE);
    mtmp->mux = u.ux; /* set_apparxy(): found_you */
    mtmp->muy = u.uy;
    (void) rn2(5); /* distfleeck(): bravegremlin; inrange = nearby = scared = 0 beyond BOLT_LIM */
    nh_muse_far_misc(); /* find_defensive() FALSE before any effect (dist2 > 25); find_misc() clears m.misc then FALSE (dist2 > 36) */

    tmp = m_move_fast(mtmp);
    if (tmp != 2) {
        if (dist2(mtmp->mx, mtmp->my, mtmp->mux, mtmp->muy) > (BOLT_LIM * BOLT_LIM))
            (void) rn2(5); /* distfleeck() recalc out of range */
        else
            distfleeck(mtmp, &inrange, &nearby, &scared); /* recalc (teleport trap etc.) */
    }

    switch (tmp) {
    case 0:
    case 3:
        /* isgd and Hallucination are excluded */
        break;
    case 1:
        if (mtmp->msleeping || !mtmp->mcanmove)
            return 0;
        if (!nearby && (SPWQ(mdat, SPW_RANGED, ranged_attk(mdat))
                        || (distmin(mtmp->mx, mtmp->my, mtmp->mux, mtmp->muy) >= BOLT_LIM
                            ? find_offensive_far(mtmp) : find_offensive(mtmp))))
            break;
        if (mtmp == u.ustuck) {
            if (u.uswallow)
                return mattacku(mtmp);
            if (distu(mtmp->mx, mtmp->my) > 2)
                unstuck(mtmp);
        }
        return 0;
    case 2:
        return 1;
    }

    if (!mtmp->mpeaceful || (Conflict && !resist(mtmp, RING_CLASS, 0, 0))) {
        if (inrange && !SPWQ(mdat, SPW_NOATTACKS, noattacks(mdat))
            && (Upolyd ? u.mh : u.uhp) > 0 && !scared && tmp != 3)
            if (mattacku(mtmp))
                return 1;
        if (mtmp->wormno)
            wormhitu(mtmp);
    }
    if (!mtmp->msleeping && mtmp->mcanmove && nearby)
        quest_talk(mtmp);
    if (inrange && mtmp->data->msound == MS_CUSS && !mtmp->mpeaceful
        && couldsee(mtmp->mx, mtmp->my) && !mtmp->minvis && !rn2(5))
        cuss(mtmp);

    return (tmp == 2);
}
'''
# the kernel needs the search block's labels/constants: place it right before dochug() — but the extracted blocks reference
# SQSRCHRADIUS and the class strings (practical[] etc.) defined after dochug(); insert instead right before "boolean\nm_digweapon_check"
anchor = "boolean\nm_digweapon_check(mtmp, nix, niy)"
assert mm.count(anchor)==1
mm = mm.replace(anchor, kernel + "\n" + anchor)
# dispatch at the top of dochug (after its declarations)
old_head = """    /*  Pre-movement adjustments
     */

    mdat = mtmp->data;

    if (mtmp->mstrategy & STRAT_ARRIVE) {"""
assert mm.count(old_head)==1
mm = mm.replace(old_head, """    /*  Pre-movement adjustments
     */

    mdat = mtmp->data;

#ifdef NH_MT2_TRACE
    nh_mt2_trace_elig = mt2_eligible(mtmp);
    if (nh_mt2_fast && nh_mt2_trace_elig)
        return dochug_fast(mtmp);
#else
    if (nh_mt2_fast && mt2_eligible(mtmp))
        return dochug_fast(mtmp);
#endif

    if (mtmp->mstrategy & STRAT_ARRIVE) {""")
# trace hook in the original m_move at the same point (after the selection loop)
old_sel_end = """ nxti:
            ;
        }
    }

    if (mmoved) MT2C(C_MOVED); else MT2C(C_NOMOVE);"""
assert mm.count(old_sel_end)==1
mm = mm.replace(old_sel_end, """ nxti:
            ;
        }
    }
    MT2_TRACE(mtmp, omx, omy, gx, gy, appr, cnt, poss, info, chi, nix, niy, mmoved);

    if (mmoved) MT2C(C_MOVED); else MT2C(C_NOMOVE);""")
# the kernel code is inserted BEFORE m_digweapon_check, i.e. before dochug's forward uses: dochug_fast is static and defined earlier: fine.
# SQSRCHRADIUS is #defined inside m_move (after our insertion point): define it for the kernel too
mm = mm.replace(kernel, kernel.replace("static int\nm_move_fast(mtmp)", "#ifndef SQSRCHRADIUS\n#define SQSRCHRADIUS 5\n#endif\nstatic int\nm_move_fast(mtmp)", 1), 1)
wr('src/monmove.c', mm)

# the MT2C counters and the eligibility copy in mon.c: use the real predicate
rep('src/mon.c', """/* v2 eligibility (ordinary hostile, far, unseen); the kernel's one mask test. Mirrors apply_census3.py plus mstrategy/ustuck/hero-state terms. */
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
""", "")
print('kernel applied')
