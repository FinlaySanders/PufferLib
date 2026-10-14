"""Event-frequency counters for eligible moves (NH_MT2_CG build only): which fallbacks of the planned kernel would fire and how often."""
from pathlib import Path
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rep(path, old, new, count=1):
    t=path.read_text(); assert t.count(old)==count, (path, t.count(old), old[:70]); path.write_text(t.replace(old,new))
mon=src/'src/mon.c'
rep(mon, """int nh_mt2_on; /* mirrors""", """int nh_mt2_cur_elig; unsigned long long nh_mt2_c[64];
int nh_mt2_on; /* mirrors""")
rep(mon, """            if (elig && !nh_mt2_on) { CALLGRIND_TOGGLE_COLLECT; nh_mt2_on = 1; }
            rd = dochugw(mtmp);""", """            if (elig && !nh_mt2_on) { CALLGRIND_TOGGLE_COLLECT; nh_mt2_on = 1; }
            nh_mt2_cur_elig = elig;
            rd = dochugw(mtmp);
            nh_mt2_cur_elig = 0;""")
mm=src/'src/monmove.c'
rep(mm, """static NEARDATA const char practical[] = {""", """#ifdef NH_MT2_CG
extern int nh_mt2_cur_elig; extern unsigned long long nh_mt2_c[64];
enum { C_MOVES, C_PLAIN, C_DOORWIN, C_PILEWIN, C_TRAPWIN, C_LIQWIN, C_BARSWIN, C_GASWIN, C_ALTARWIN, C_ORIGDOOR, C_OCCWIN, C_TEMPLE, C_SOKO,
       C_BOXEMPTY, C_SEARCH, C_SEARCHOBJ, C_TARGET, C_MOVED, C_NOMOVE, C_TRACKHIT, C_DESTOBJ, C_DESTTRAP, C_DESTDOOR, C_DESTSEE, C_HIDES,
       C_RANGED, C_REFLECT, C_UPOLYD, C_ENGRHERE, C_ENGRANY, C_REGIONS, C_DISPLACES, C_INTEREST, C_USESITEMS, C_MINVENT, C_APPR0, C_ITEMSPECIES,
       C_SHOPROOM, C_CANOPEN, C_ORIGSEE, C_CNT0, C_CNT1, C_CNT2, C_CNT3, C_CNT4, C_CNT5, C_CNT6, C_CNT7, C_CNT8, C_NODIAG, C_INFRA_SENSE, C_MMOVED3 };
#define MT2C(k) do { if (nh_mt2_cur_elig) nh_mt2_c[k]++; } while (0)
static void mt2_window_stats(struct monst *m) {
    int x = m->mx, y = m->my, nx, ny, door = 0, pile = 0, trap = 0, liq = 0, bars = 0, gas = 0, altar = 0, occ = 0, see = 0;
    for (nx = x - 1; nx <= x + 1; nx++) for (ny = y - 1; ny <= y + 1; ny++) {
        int t; if (!isok(nx, ny) || (nx == x && ny == y)) continue; t = TYP_AT(nx, ny);
        if (IS_DOOR(t)) door = 1; if (t == IRONBARS) bars = 1; if (IS_ALTAR(t)) altar = 1;
        if (t == POOL || t == MOAT || t == WATER || t == LAVAPOOL || t == DRAWBRIDGE_UP || t == DRAWBRIDGE_DOWN) liq = 1;
        if (NH_SUMMARY(nx, ny).move_pile) pile = 1; if (NH_SUMMARY(nx, ny).move_trap_present) trap = 1; if (NH_SUMMARY(nx, ny).move_gas) gas = 1;
        if (MON_AT(nx, ny)) occ = 1; if (cansee(nx, ny)) see = 1;
    }
    MT2C(C_MOVES); if (door) MT2C(C_DOORWIN); if (pile) MT2C(C_PILEWIN); if (trap) MT2C(C_TRAPWIN); if (liq) MT2C(C_LIQWIN); if (bars) MT2C(C_BARSWIN);
    if (gas || NH_SUMMARY(x, y).move_gas) MT2C(C_GASWIN); if (altar) MT2C(C_ALTARWIN); if (IS_DOOR(TYP_AT(x, y))) MT2C(C_ORIGDOOR); if (occ) MT2C(C_OCCWIN);
    if (level.lflags.has_temple) MT2C(C_TEMPLE); if (Sokoban) MT2C(C_SOKO); if (see) MT2C(C_DESTSEE); if (couldsee(x, y)) MT2C(C_ORIGSEE);
    if (!door && !pile && !trap && !liq && !bars && !gas && !altar && !IS_DOOR(TYP_AT(x, y)) && !NH_SUMMARY(x, y).move_gas && !level.lflags.has_temple && !Sokoban) MT2C(C_PLAIN);
    if ((m->data->mflags3 & M3_DISPLACES) || m->data == &mons[PM_PURPLE_WORM]) MT2C(C_DISPLACES);
    if (NODIAG(monsndx(m->data))) MT2C(C_NODIAG);
    { int ex = 0, ox, oy; for (ox = max(1, x - 5); ox <= min(COLNO - 1, x + 5) && !ex; ox++) for (oy = max(0, y - 5); oy <= min(ROWNO - 1, y + 5); oy++) if (NH_SUMMARY(ox, oy).move_obj_present) { ex = 1; break; }
      if (!ex) MT2C(C_BOXEMPTY); }
    if (m->minvent) MT2C(C_MINVENT); if (ranged_attk(m->data)) MT2C(C_RANGED); if (Reflecting) MT2C(C_REFLECT); if (Upolyd) MT2C(C_UPOLYD);
    if (engr_at(x, y)) MT2C(C_ENGRHERE); if (head_engr) MT2C(C_ENGRANY); if (n_regions) MT2C(C_REGIONS); if (hides_under(m->data)) MT2C(C_HIDES);
    if (likes_gold(m->data) || likes_gems(m->data) || likes_objs(m->data) || likes_magic(m->data) || throws_rocks(m->data) || hides_under(m->data)) MT2C(C_ITEMSPECIES);
    if (!(nohands(m->data) || verysmall(m->data))) MT2C(C_CANOPEN);
    if (*in_rooms(x, y, SHOPBASE)) MT2C(C_SHOPROOM);
    if (nh_display_sense & ~NH_SENSE_VALID) MT2C(C_INFRA_SENSE);
}
#else
#define MT2C(k) do { } while (0)
#endif
static NEARDATA const char practical[] = {""")
rep(mm, """    set_apparxy(mtmp);
    /* where does mtmp think you are? */""", """#ifdef NH_MT2_CG
    if (nh_mt2_cur_elig) mt2_window_stats(mtmp);
#endif
    set_apparxy(mtmp);
    /* where does mtmp think you are? */""")
rep(mm, """            setlikes = TRUE;
        }
    }

#define SQSRCHRADIUS 5""", """            setlikes = TRUE;
        }
    }
    if (appr == 0) MT2C(C_APPR0);
    if (likegold || likegems || likeobjs || likemagic || likerock || conceals) MT2C(C_INTEREST);
    if (uses_items) MT2C(C_USESITEMS);

#define SQSRCHRADIUS 5""")
rep(mm, """ look_for_obj:
            oomx = min(COLNO - 1, omx + minr);""", """ look_for_obj:
            MT2C(C_SEARCH);
            oomx = min(COLNO - 1, omx + minr);""")
rep(mm, """                if (otmp->otyp == ROCK)
                    continue;
                xx = otmp->ox;""", """                MT2C(C_SEARCHOBJ);
                if (otmp->otyp == ROCK)
                    continue;
                xx = otmp->ox;""")
rep(mm, """                            gx = otmp->ox;
                            gy = otmp->oy;
                            if (gx == omx && gy == omy) {""", """                            gx = otmp->ox;
                            gy = otmp->oy;
                            MT2C(C_TARGET);
                            if (gx == omx && gy == omy) {""")
rep(mm, """        cnt = mfndpos(mtmp, poss, info, flag);
        chcnt = 0;""", """        cnt = mfndpos(mtmp, poss, info, flag);
        MT2C(C_CNT0 + (cnt > 8 ? 8 : cnt));
        chcnt = 0;""")
rep(mm, """            if (appr != 0 && (trackmask & nh_move_position_bit(omx, omy, nx, ny))) {""", """            if (appr != 0 && (trackmask & nh_move_position_bit(omx, omy, nx, ny))) {
                MT2C(C_TRACKHIT);""")
rep(mm, """    if (mmoved) {
        register int j;

        if (mmoved == 1 && (u.ux != nix || u.uy != niy) && itsstuck(mtmp))""", """    if (mmoved) MT2C(C_MOVED); else MT2C(C_NOMOVE);
    if (mmoved) {
        register int j;

        if (mmoved == 1 && (u.ux != nix || u.uy != niy) && itsstuck(mtmp))""")
rep(mm, """            nh_newsym_moved(omx, omy); /* update the old position */
            if (mintrap(mtmp) >= 2) {""", """            if (NH_SUMMARY(mtmp->mx, mtmp->my).move_trap_present) MT2C(C_DESTTRAP);
            if (IS_DOOR(TYP_AT(mtmp->mx, mtmp->my))) MT2C(C_DESTDOOR);
            if (nh_move_obj_at(mtmp->mx, mtmp->my)) MT2C(C_DESTOBJ);
            nh_newsym_moved(omx, omy); /* update the old position */
            if (mintrap(mtmp) >= 2) {""")
rep(mm, """ postmov:
    if (mmoved == 1 || mmoved == 3) {""", """ postmov:
    if (mmoved == 3) MT2C(C_MMOVED3);
    if (mmoved == 1 || mmoved == 3) {""")
nle=src/'src/nle.c'
rep(nle, """    fprintf(f, "eligible_moves %llu all_moves %llu resyncs %llu\\n", nh_mt2_elig_moves, nh_mt2_all_moves, nh_mt2_resync); fclose(f);""",
"""    fprintf(f, "eligible_moves %llu all_moves %llu resyncs %llu\\n", nh_mt2_elig_moves, nh_mt2_all_moves, nh_mt2_resync);
    { extern unsigned long long nh_mt2_c[64]; static const char *names[] = {"moves","plain","doorwin","pilewin","trapwin","liqwin","barswin","gaswin","altarwin","origdoor","occwin","temple","soko",
        "boxempty","search","searchobj","target","moved","nomove","trackhit","destobj","desttrap","destdoor","winsee","hides","ranged","reflect","upolyd","engrhere","engrany","regions","displaces",
        "interest","usesitems","minvent","appr0","itemspecies","shoproom","canopen","origcouldsee","cnt0","cnt1","cnt2","cnt3","cnt4","cnt5","cnt6","cnt7","cnt8","nodiag","sensebits","mmoved3"};
      int k; for (k = 0; k < (int) (sizeof names / sizeof names[0]); k++) fprintf(f, "%s %llu\\n", names[k], nh_mt2_c[k]); }
    fclose(f);""")
print('stats applied')
