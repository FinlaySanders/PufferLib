"""Candidate B = A + mfndpos prefilters from column masks: liquid (pool/lava, drawbridge excepted), diagonal rules (nodiag/origin door),
door-diagonal and worm-crossing diagonals keep the exact per-cell test. Masks maintained in nh_move_typ_set beside nonrock."""
import sys, shutil
from pathlib import Path
R=Path(__file__).resolve().parent; src=R/'engines'/sys.argv[1]/'source'
if not src.exists(): shutil.copytree(R/'engines/selA/source', src)
def rep(path, old, new):
    t=path.read_text(); assert t.count(old)==1, (path, old[:70]); path.write_text(t.replace(old,new))
rep(src/'include/movement_masks.h',
"""struct nh_move_column { unsigned int nonrock, occupied; };""",
"""struct nh_move_column { unsigned int nonrock, occupied, pool, lava, db, door; };
#define NH_MOVE_DIAG 0x145U /* neighbour bits 0, 2, 6, 8: the four diagonals */

static inline void
nh_move_set_bit(unsigned int *field, int y, int on)
{
    unsigned int bit = 1U << y;
    if (on) *field |= bit;
    else *field &= ~bit;
}""")
rep(src/'include/hack.h',
"""    nh_typ_plane[x][y] = typ;
    nh_move_set_terrain(level.move_columns, x, y, !IS_ROCK(typ));
}""",
"""    nh_typ_plane[x][y] = typ;
    nh_move_set_terrain(level.move_columns, x, y, !IS_ROCK(typ));
    {
        struct nh_move_column *c = &level.move_columns[x + 1];
        nh_move_set_bit(&c->pool, y, typ == POOL || typ == MOAT || typ == WATER);
        nh_move_set_bit(&c->lava, y, typ == LAVAPOOL);
        nh_move_set_bit(&c->db, y, typ == DRAWBRIDGE_UP);
        nh_move_set_bit(&c->door, y, typ == DOOR);
    }
}""")
m=src/'src/mon.c'
rep(m,
"""    unsigned int candidates, occupied;
    struct nh_move_column *cols;""",
"""    unsigned int candidates, occupied, occ_all, db_n, diag_exact;
    struct nh_move_column *cols;""")
rep(m,
"""        occupied = nh_move_neighbours(cols[0].occupied, cols[1].occupied,
                                      cols[2].occupied, y);
        /* Both hero positions stay on the original path. The old image may
           become obsolete during this loop, so keep the full checks below. */
        occupied &= ~(nh_move_position_bit(x, y, u.ux, u.uy)
                       | nh_move_position_bit(x, y, mon->mux, mon->muy));
        candidates &= ~occupied;
    }
    while (candidates) {""",
"""        /* Both hero positions stay on the original path. The old image may
           become obsolete during this loop, so keep the full checks below. */
        occupied = occ_all & ~(nh_move_position_bit(x, y, u.ux, u.uy)
                               | nh_move_position_bit(x, y, mon->mux, mon->muy));
        candidates &= ~occupied;
    }
    db_n = nh_move_neighbours(cols[0].db, cols[1].db, cols[2].db, y);
    {
        /* Liquid and diagonal rules decided from the column masks for every cell whose answer depends on terrain type alone.
           Drawbridge cells, door cells on a diagonal and diagonals with both orthogonal neighbours occupied (possible worm) keep
           the exact per-cell tests inside the loop. All removed tests are pure, so pruning the mask first is identical. */
        unsigned int pool_n = nh_move_neighbours(cols[0].pool, cols[1].pool, cols[2].pool, y);
        unsigned int lava_n = nh_move_neighbours(cols[0].lava, cols[1].lava, cols[2].lava, y);
        unsigned int door_n = nh_move_neighbours(cols[0].door, cols[1].door, cols[2].door, y);
        unsigned int bad = 0U;
        if (!poolok) bad |= wantpool ? ~pool_n : pool_n;
        if (!lavaok) bad |= lava_n;
        candidates &= ~(bad & ~db_n);
        if (nodiag || (IS_DOOR(origin_typ) && ((origin->rmflags & ~D_BROKEN) || mover.rogue)))
            candidates &= ~NH_MOVE_DIAG;
        diag_exact = (door_n
                      | ((occ_all >> 1) & (occ_all >> 3) & 1U)
                      | (((occ_all >> 1) & (occ_all >> 5) & 1U) << 2)
                      | (((occ_all >> 7) & (occ_all >> 3) & 1U) << 6)
                      | (((occ_all >> 7) & (occ_all >> 5) & 1U) << 8)) & NH_MOVE_DIAG;
    }
    while (candidates) {""")
rep(m,
"""    cols = &level.move_columns[x];
    if (!(flag & ALLOW_WALL) && !rockok && !treeok)""",
"""    cols = &level.move_columns[x];
    occ_all = nh_move_neighbours(cols[0].occupied, cols[1].occupied, cols[2].occupied, y);
    if (!(flag & ALLOW_WALL) && !rockok && !treeok)""")
rep(m,
"""            /* first diagonal checks (tight squeezes handled below) */
            if (nx != x && ny != y
                && (nodiag
                    || (IS_DOOR(origin_typ) && (origin->rmflags & ~D_BROKEN))
                    || (IS_DOOR(cell_typ) && (cell->rmflags & ~D_BROKEN))
                    || ((IS_DOOR(origin_typ) || IS_DOOR(cell_typ))
                        && mover.rogue)
                    /* mustn't pass between adjacent long worm segments,
                       but can attack that way */
                    || (m_at(x, ny) && m_at(nx, y) && worm_cross(x, y, nx, ny)
                        && !m_at(nx, ny) && (nx != u.ux || ny != u.uy))))
                continue;
            if (((nh_cell_pool(cell, nx, ny) != 0) == wantpool || poolok)
                && (lavaok || !nh_cell_lava(cell, nx, ny))) {""",
"""            /* first diagonal checks (tight squeezes handled below); nodiag and the origin-door rules already pruned the
               mask, so only door cells and possible worm crossings reach the exact test */
            if ((diag_exact & (1U << bit))
                && ((IS_DOOR(cell_typ) && ((cell->rmflags & ~D_BROKEN) || mover.rogue))
                    /* mustn't pass between adjacent long worm segments,
                       but can attack that way */
                    || (m_at(x, ny) && m_at(nx, y) && worm_cross(x, y, nx, ny)
                        && !m_at(nx, ny) && (nx != u.ux || ny != u.uy))))
                continue;
            if (!(db_n & (1U << bit)) /* liquid rules were applied to the mask; drawbridges keep the exact test */
                || (((nh_cell_pool(cell, nx, ny) != 0) == wantpool || poolok)
                    && (lavaok || !nh_cell_lava(cell, nx, ny)))) {""")
print('B applied to', src)
