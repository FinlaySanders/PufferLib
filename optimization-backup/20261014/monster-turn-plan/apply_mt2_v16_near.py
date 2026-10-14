"""v1.6: near monsters (distmin 2..9, not adjacent) and could-see monsters join the fast path. Everything range-dependent is the original
code: distfleeck(), find_defensive()/find_misc() within dist2 36, the weapon-wield and castmu blocks (verbatim), lined_up() for in_line,
should_see for appr/track, hero/believed-position cells in the 3x3 → mfndpos fallback, the ALLOW_U / hero-cell / image-cell blocks after
selection (verbatim). Adjacent monsters (nearby) stay on the old path."""
from pathlib import Path
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rd(p): return (src/p).read_text()
def wr(p,t): (src/p).write_text(t)
def match_brace(text, j):
    assert text[j]=='{'; depth=0; k=j
    while True:
        c=text[k]
        if c=='{': depth+=1
        elif c=='}':
            depth-=1
            if depth==0: return k
        k+=1
mm=rd('src/monmove.c')
def rep(old,new,count=1):
    global mm; assert mm.count(old)==count,(mm.count(old),old[:90]); mm=mm.replace(old,new)
# ---- verbatim blocks from the ORIGINAL dochug / m_move (the first occurrences are the originals: dochug_fast/m_move_fast come later) ----
od=mm.index("dochug(mtmp)\nregister struct monst *mtmp;")
i=mm.index("    /* If monster is nearby you, and has to wield a weapon, do so.", od); j=mm.index("{", mm.index("if ((!mtmp->mpeaceful || Conflict) && inrange", i)); wield=mm[i:match_brace(mm,j)+1]
i=mm.index("        if (dist2(mtmp->mx, mtmp->my, u.ux, u.uy) <= 49", od); j=mm.index("{", i); castmu=mm[i:match_brace(mm,j)+1]
om=mm.index("\nm_move(mtmp, after)")
i=mm.index("        if (info[chi] & ALLOW_U) {", om); j=mm.index("        if (!m_in_out_region(mtmp, nix, niy))", i); postsel=mm[i:j]
assert "mattackm" in postsel and "ALLOW_MDISP" in postsel and "return 0;" in postsel and castmu.count("castmu(")==1 and "mon_wield_item" in wield
# ---- eligibility: not adjacent; could-see allowed ----
rep("""        if ((ddx > ddy ? ddx : ddy) <= 9) /* distmin */
            return MT2WHY(9);
    }
    if (viz_array[m->my][m->mx] & COULD_SEE)
        return MT2WHY(10);
    return 1;""", """        if ((ddx > ddy ? ddx : ddy) <= 1) /* adjacent (nearby): the melee path stays original */
            return MT2WHY(9);
    }
    return 1;""")
# ---- dochug_fast prelude ----
rep("""    set_apparxy(mtmp); /* believed hero position: exact for Invis/Displaced too; at distmin > 9 it stays >= 8 away */
    (void) rn2(5); /* distfleeck(): bravegremlin; nearby = scared = 0 beyond monnear; inrange only feeds blocks that need dist2 <= 8 */
    nh_muse_far_misc(); /* find_defensive() FALSE before any effect (dist2 > 25); find_misc() clears m.misc then FALSE (dist2 > 36) */
""", """    set_apparxy(mtmp); /* believed hero position (original function: exact for Invis/Displaced) */
    distfleeck(mtmp, &inrange, &nearby, &scared); /* not adjacent: nearby = scared = 0; inrange feeds the wield block */
    if (inrange)
        nh_mt2_hero_valid = 0; /* items, spells and attacks below may change hero properties */
    if (dist2(mtmp->mx, mtmp->my, mtmp->mux, mtmp->muy) <= 36) {
        if (find_defensive(mtmp)) {
            if (use_defensive(mtmp) != 0)
                return 1;
        } else if (find_misc(mtmp)) {
            if (use_misc(mtmp) != 0)
                return 1;
        }
    } else
        nh_muse_far_misc(); /* find_defensive() FALSE before any effect (dist2 > 25); find_misc() clears m.misc then FALSE (dist2 > 36) */

""" + wield + "\n\n    /* movement phase: !nearby holds, so the original condition is TRUE without its draws */\n    {\n    " + castmu.replace("\n", "\n") + "\n    }\n")
# ---- m_move_fast: should_see, appr chain, track, in_line ----
rep("""    gx = mtmp->mux;
    gy = mtmp->muy;
    appr = 1; /* !mflee; !mconf; should_see is FALSE beyond dist2 36; !mcansee, Invis and disguise are excluded */
    if (mtmp->mpeaceful) /* (mpeaceful && !isshk) precedes the stalker/bat/light draw in the original OR chain */
        appr = 0;
    else if ((spw & SPW_RANDAPPR) && !rn2(3))
        appr = 0;""", """    gx = mtmp->mux;
    gy = mtmp->muy;
    appr = 1; /* !mflee; !mconf */
    should_see = (couldsee(omx, omy)
                  && (NH_TILE(gx, gy).lit || !NH_TILE(omx, omy).lit)
                  && (dist2(omx, omy, gx, gy) <= 36));
    /* the original OR chain minus its excluded terms (!mcansee, disguise, uundetected), same evaluation order and draws */
    if ((should_see && Invis && !(spw & SPW_PERCEIVES) && rn2(11))
        || mtmp->mpeaceful
        || ((spw & SPW_RANDAPPR) && !rn2(3)))
        appr = 0;""")
rep("""    if (((uwep && uwep->oartifact == ART_EXCALIBUR) || (spw & SPW_HASEYES)) && nh_track_near[omx][omy]) {""",
    """    if (!should_see && ((uwep && uwep->oartifact == ART_EXCALIBUR) || (spw & SPW_HASEYES)) && nh_track_near[omx][omy]) {""")
rep("""    if ((!mtmp->mpeaceful || !rn2(10)) && !Is_rogue_level(&u.uz)) { /* the draw precedes the level test in the original */
        /* in_line is FALSE at this range: lined_up() draws rn2(25) when Upolyd and linedup() only stores tbx/tby */
        register int pctload = 0;
        if (Upolyd)
            (void) rn2(25);
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
    }""", """    if ((!mtmp->mpeaceful || !rn2(10)) && !Is_rogue_level(&u.uz)) { /* the draw precedes the level test in the original */
        boolean in_line = (lined_up(mtmp)
               && (distmin(mtmp->mx, mtmp->my, mtmp->mux, mtmp->muy)
                   <= (throws_rocks(youmonst.data) ? 20 : ACURRSTR / 2 + 1)));
        if (appr != 1 || !in_line) {
            register int pctload = 0;
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
    }""")
# declarations
rep("    boolean unlock_known = 0; /* can_unlock is three inventory walks: computed only when a locked door is in reach */\n",
    "    boolean unlock_known = 0; /* can_unlock is three inventory walks: computed only when a locked door is in reach */\n    boolean should_see;\n")
# plain window: the hero cell and the believed-position cell carry their own rules (ALLOW_U, mux update, Elbereth, displacement) → fallback
rep("        plain = !bad && !((((cols[1].special & ~(cols[1].door & dmask)) | cols[1].gas) >> omy) & 1U) && !level.lflags.has_temple && !Sokoban;",
    "        plain = !bad && !((((cols[1].special & ~(cols[1].door & dmask)) | cols[1].gas) >> omy) & 1U) && !level.lflags.has_temple && !Sokoban\n                && distmin(omx, omy, u.ux, u.uy) > 1 && distmin(omx, omy, mtmp->mux, mtmp->muy) > 1;")
# plain loop: info must be defined (read by the post-selection blocks)
rep("""            cbit[cnt] = b;
#ifdef NH_MT2_TRACE
            { int dx = poss[cnt].x - u.ux, dy = poss[cnt].y - u.uy; info[cnt] = (!dx || !dy || dx == dy || dx == -dy) ? NOTONL : 0L; }
#endif
            cnt++;""", """            cbit[cnt] = b;
            info[cnt] = 0L; /* no hero/image/monster cell in a plain window: only NOTONL could be set, and it is read by unicorns alone */
#ifdef NH_MT2_TRACE
            { int dx = poss[cnt].x - u.ux, dy = poss[cnt].y - u.uy; info[cnt] = (!dx || !dy || dx == dy || dx == -dy) ? NOTONL : 0L; }
#endif
            cnt++;""")
# post-selection blocks (verbatim) before the region test
rep("""        /* itsstuck(): not u.ustuck; m_digweapon_check(): no tunneller; ALLOW_U/ALLOW_M/ALLOW_MDISP cannot be set here */
        if (n_regions && !m_in_out_region(mtmp, nix, niy))
            return 3;""", """        /* itsstuck(): not u.ustuck; m_digweapon_check(): no tunneller */
""" + postsel + """        if (n_regions && !m_in_out_region(mtmp, nix, niy))
            return 3;""")
wr('src/monmove.c', mm)
print('v1.6 applied; wield block lines', wield.count('\n'), 'castmu', castmu.count('\n'), 'postsel', postsel.count('\n'))
