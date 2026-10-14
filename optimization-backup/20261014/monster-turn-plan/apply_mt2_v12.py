"""mt2 v1.2: S3 object search by box-cell enumeration in fobj order (per-object fobj index), S7 door-aware plain window."""
from pathlib import Path
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rd(p): return (src/p).read_text()
def wr(p,t): (src/p).write_text(t)
def rep(p, old, new, count=1):
    t=rd(p); assert t.count(old)==count, (p, t.count(old), old[:80]); wr(p, t.replace(old,new))
def match_brace(text, j):
    assert text[j]=='{'; depth=0; k=j
    while True:
        c=text[k]
        if c=='{': depth+=1
        elif c=='}':
            depth-=1
            if depth==0: return k
        k+=1
# ---- S3: per-object fobj index ------------------------------------------------------------------------------------
_o=rd('include/obj.h'); _a="    struct oextra *oextra; /* pointer to oextra struct */\n};"; assert _o.count(_a)==2 and _o.index(_a) < _o.index("struct obj_legacy")
wr('include/obj.h', _o.replace(_a, "    struct oextra *oextra; /* pointer to oextra struct */\n    int nh_fidx; /* position in the floor-object index (monmove.c nh_fobj_*), valid while nh_fobj_valid */\n};", 1)) # struct obj only; obj_legacy keeps its layout
for f,old in (('include/obj_save.h','_Static_assert(sizeof(struct obj)==88,"compact object size");'),
              ('src/save.c','_Static_assert(sizeof(struct obj)   ==   88, "save.c: sizeof(struct obj) drifted");'),
              ('src/restore.c','_Static_assert(sizeof(struct obj)   ==   88, "restore.c: sizeof(struct obj) drifted");')):
    rep(f, old, old.replace('88','96'))
rep('src/monmove.c', """    nh_fobj_lo = 2048 - n; nh_fobj_count = n; nh_fobj_valid = 1;
}""", """    nh_fobj_lo = 2048 - n; nh_fobj_count = n; nh_fobj_valid = 1;
    for (n = nh_fobj_lo; n < 2048; n++) nh_fobj_ptr[n]->nh_fidx = n;
}""")
rep('src/monmove.c', """    nh_fobj_ptr[nh_fobj_lo] = o;
    nh_fobj_x[nh_fobj_lo] = o->ox; nh_fobj_y[nh_fobj_lo] = o->oy;""", """    nh_fobj_ptr[nh_fobj_lo] = o;
    o->nh_fidx = nh_fobj_lo;
    nh_fobj_x[nh_fobj_lo] = o->ox; nh_fobj_y[nh_fobj_lo] = o->oy;""")
rep('src/monmove.c', """    memmove(nh_fobj_y + lo + 1, nh_fobj_y + lo, (i - lo) * sizeof nh_fobj_y[0]);
    nh_fobj_lo++; nh_fobj_count--;""", """    memmove(nh_fobj_y + lo + 1, nh_fobj_y + lo, (i - lo) * sizeof nh_fobj_y[0]);
    for (hi = lo + 1; hi <= i; hi++) nh_fobj_ptr[hi]->nh_fidx = hi;
    nh_fobj_lo++; nh_fobj_count--;""")
# the enumerator (defined after nh_fobj_build so the statics are visible) + the two-loop search in m_move_fast
rep('src/monmove.c', """void
nh_fobj_placed(struct obj *o)
{""", """#define MT2_MAXOBJ 16
/* Floor objects inside the box, in fobj order (ascending index): the search loop can then run its original body over them.
   Returns -1 when the index is unavailable (too many objects) or the box holds more than MT2_MAXOBJ objects: use the cursor. */
static int
mt2_box_objects(int lx, int hx, int ly, int hy, struct obj **list)
{
    unsigned int rows = (2U << hy) - (1U << ly);
    int x, n = 0, i, j;
    struct obj *o, *t;
    if (!nh_fobj_valid) nh_fobj_build();
    if (nh_fobj_count < 0) return -1;
    for (x = lx; x <= hx; x++) {
        unsigned int bits = level.move_columns[x + 1].obj & rows;
        while (bits) {
            int y = __builtin_ctz(bits);
            bits &= bits - 1;
            for (o = level.objs[x][y]; o; o = o->nexthere) {
                if (n == MT2_MAXOBJ) return -1;
                list[n++] = o;
            }
        }
    }
    for (i = 1; i < n; i++) { /* insertion sort by fobj position */
        t = list[i];
        for (j = i; j > 0 && list[j - 1]->nh_fidx > t->nh_fidx; j--) list[j] = list[j - 1];
        list[j] = t;
    }
    return n;
}

void
nh_fobj_placed(struct obj *o)
{""")
mm=rd('src/monmove.c')
fs=mm.index("m_move_fast(mtmp)")
hdr_start=mm.index("for (otmp = mt2_box_has_objects(lmx, oomx, lmy, oomy) ? nh_fobj_next", fs)
hdr_end=mm.index("{", mm.index("otmp = nh_fobj_next(&cursor, otmp, lmx, oomx, lmy, oomy))", hdr_start))
body_end=match_brace(mm, hdr_end)
header=mm[hdr_start:hdr_end]; body=mm[hdr_end:body_end+1]
assert "goto postmov" in body and body.count("continue")>=3
cursor_header="for (otmp = nh_fobj_next(&cursor, (struct obj *) 0, lmx, oomx, lmy, oomy);\n                 otmp;\n                 otmp = nh_fobj_next(&cursor, otmp, lmx, oomx, lmy, oomy)) "
new = ("{\n            struct obj *mt2_list[MT2_MAXOBJ];\n            int mt2_n = mt2_box_objects(lmx, oomx, lmy, oomy, mt2_list), mt2_i;\n"
       "            if (mt2_n < 0) {\n            " + cursor_header + body + "\n            } else for (mt2_i = 0; mt2_i < mt2_n; mt2_i++) {\n                otmp = mt2_list[mt2_i];\n            " + body + "\n            }\n            }")
mm = mm[:hdr_start] + new + mm[body_end+1:]
# the body is a for-body with 'continue': inside the else-for it continues that for: same semantics. Done.
# ---- S7: door-aware plain window ------------------------------------------------------------------------------------
old_bad = """        unsigned int bad = nh_move_neighbours(cols[0].special | cols[0].pile | cols[0].trap | cols[0].gas,
                                              cols[1].special | cols[1].pile | cols[1].trap | cols[1].gas,
                                              cols[2].special | cols[2].pile | cols[2].trap | cols[2].gas, omy);
        plain = !bad && !(((cols[1].special | cols[1].gas) >> omy) & 1U) && !level.lflags.has_temple && !Sokoban;
    }"""
assert mm.count(old_bad)==1
mm = mm.replace(old_bad, """        unsigned int bad = nh_move_neighbours(cols[0].special | cols[0].pile | cols[0].trap | cols[0].gas,
                                              cols[1].special | cols[1].pile | cols[1].trap | cols[1].gas,
                                              cols[2].special | cols[2].pile | cols[2].trap | cols[2].gas, omy);
        door_n = nh_move_neighbours(cols[0].door, cols[1].door, cols[2].door, omy);
        origin_door = (cols[1].door >> omy) & 1U;
        /* doors are the one special terrain handled here (their rules below); any other special cell, origin gas or temple → fallback */
        plain = !(bad & ~door_n) && !((((cols[1].special | cols[1].gas) >> omy) & 1U) & ~origin_door) && !level.lflags.has_temple && !Sokoban;
    }""")
old_cand = """        unsigned int cand = nonrock_n & ~occ;
        if (spw & SPW_NODIAG) {
            cand &= 0x0aaU;
        } else if (cand & 0x145U) {"""
assert mm.count(old_cand)==1
mm = mm.replace(old_cand, """        unsigned int cand = nonrock_n & ~occ;
        if (cand & door_n) {
            /* mfndpos(): a closed door needs OPENDOOR, a locked one UNLOCKDOOR, unless amorphous (can_fog excluded) or a doorbuster */
            unsigned int dbits = cand & door_n;
            if (!(spw & SPW_AMORPHOUS) && !doorbuster) {
                while (dbits) {
                    int b = __builtin_ctz(dbits), dm;
                    dbits &= dbits - 1;
                    dm = NH_TILE(omx - 1 + b / 3, omy - 1 + b % 3).rmflags;
                    if (dm & D_LOCKED) {
                        if (!unlock_known) { can_unlock = (can_open && monhaskey(mtmp, TRUE)); unlock_known = 1; }
                        if (!can_unlock) { cand &= ~(1U << b); continue; }
                    }
                    if ((dm & D_CLOSED) && !can_open)
                        cand &= ~(1U << b);
                }
            }
        }
        if (spw & SPW_NODIAG) {
            cand &= 0x0aaU;
        } else if ((cand & 0x145U) && (origin_door || (cand & door_n & 0x145U))) {
            /* mfndpos(): no diagonal move out of or into a door that is not broken away (or any door on the Rogue level) */
            unsigned int dbits = cand & 0x145U;
            boolean rogue = Is_rogue_level(&u.uz);
            int odm = origin_door ? (NH_TILE(omx, omy).rmflags & ~D_BROKEN) : 0;
            while (dbits) {
                int b = __builtin_ctz(dbits), isdoor = (door_n >> b) & 1U;
                dbits &= dbits - 1;
                if (odm || (isdoor && (NH_TILE(omx - 1 + b / 3, omy - 1 + b % 3).rmflags & ~D_BROKEN)) || ((origin_door || isdoor) && rogue))
                    cand &= ~(1U << b);
            }
        }
        if (spw & SPW_NODIAG) {
            ;
        } else if (cand & 0x145U) {""")
# fallback path: can_unlock computed there; mark known
old_fb = "        can_unlock = (can_open && monhaskey(mtmp, TRUE));\n        flag = ALLOW_U;"
assert mm.count(old_fb)==1
mm = mm.replace(old_fb, "        can_unlock = (can_open && monhaskey(mtmp, TRUE));\n        unlock_known = 1;\n        flag = ALLOW_U;")
# the verbatim door block reads can_unlock: make sure it is computed when the destination is a door
old_db = "            /* open a door, or crash through it, if 'mtmp' can */"
i = mm.index(old_db, fs)
mm = mm[:i] + "            if (!unlock_known && IS_DOOR(TYP_AT(mtmp->mx, mtmp->my))) { can_unlock = (can_open && monhaskey(mtmp, TRUE)); unlock_known = 1; }\n" + mm[i:]
# declarations
old_decl = "    unsigned char cbit[9]; /* neighbourhood bit of each candidate: the track test needs no coordinate arithmetic */\n"
assert mm.count(old_decl)==1
mm = mm.replace(old_decl, old_decl + "    unsigned int door_n, origin_door;\n    boolean unlock_known = 0; /* can_unlock is three inventory walks: computed only when a locked door is in reach */\n")
wr('src/monmove.c', mm)
# door column bitmap
rep('include/movement_masks.h', "struct nh_move_column { unsigned int nonrock, occupied, special, pile, trap, gas, obj; };",
    "struct nh_move_column { unsigned int nonrock, occupied, special, pile, trap, gas, obj, door; };")
rep('include/hack.h', "    nh_move_set_col_bit(&level.move_columns[x + 1].special, y, nh_typ_special(typ));\n}",
    "    nh_move_set_col_bit(&level.move_columns[x + 1].special, y, nh_typ_special(typ));\n    nh_move_set_col_bit(&level.move_columns[x + 1].door, y, typ == DOOR);\n}")
print('v1.2 applied')
