"""v1.6b: dochug_fast uses the ORIGINAL movement-phase condition and body (verbatim, m_move -> m_move_fast) and the demonic-blackmail block,
so a believed hero position adjacent to the monster (Invis/Displaced guesses) takes the original no-move/attack path."""
from pathlib import Path
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
mm=(src/'src/monmove.c').read_text()
def match_brace(text, j):
    assert text[j]=='{'; depth=0; k=j
    while True:
        c=text[k]
        if c=='{': depth+=1
        elif c=='}':
            depth-=1
            if depth==0: return k
        k+=1
od=mm.index("dochug(mtmp)\nregister struct monst *mtmp;")
i=mm.index("    /* Demonic Blackmail! */", od); j=mm.index("{", mm.index("if (nearby && mdat->msound == MS_BRIBE", i)); bribe=mm[i:match_brace(mm,j)+1]
i=mm.index("    /*  Now the actual movement phase", od); j=mm.index("{", mm.index("if (!nearby || mtmp->mflee || scared", i)); move=mm[i:match_brace(mm,j)+1]
assert "tmp = m_move(mtmp, 0);" in move and "switch (tmp)" in move and "demon_talk" in bribe
move_fast = move.replace("        tmp = m_move(mtmp, 0);\n        if (tmp != 2)\n            distfleeck(mtmp, &inrange, &nearby, &scared); /* recalc */",
"""        tmp = m_move_fast(mtmp);
        if (tmp != 2) {
            if (dist2(mtmp->mx, mtmp->my, mtmp->mux, mtmp->muy) > (BOLT_LIM * BOLT_LIM))
                (void) rn2(5); /* distfleeck() recalc out of range: inrange = nearby = scared = 0, only its draw */
            else {
                nh_mt2_hero_valid = 0; /* the near tail (attacks) may change hero properties */
                distfleeck(mtmp, &inrange, &nearby, &scared); /* recalc */
            }
        }""")
assert move_fast != move
# dochug_fast: replace from the movement comment through the end of its switch with the verbatim blocks
df=mm.index("dochug_fast(mtmp)\nregister struct monst *mtmp;")
s=mm.index("    /* movement phase: !nearby holds, so the original condition is TRUE without its draws */", df)
e=mm.index("    if (!mtmp->mpeaceful || (Conflict && !resist(mtmp, RING_CLASS, 0, 0))) {", df)
new_mid = "\n" + bribe + "\n\n" + move_fast + "\n\n"
mm = mm[:s] + new_mid + mm[e:]
# the inrange-based hero invalidation stays; `nearby` is now real: no assumption comment needed
(src/'src/monmove.c').write_text(mm); print('v1.6b applied; bribe', bribe.count('\n'), 'move block', move_fast.count('\n'))
