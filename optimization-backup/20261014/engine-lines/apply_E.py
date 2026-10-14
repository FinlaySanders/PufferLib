"""Candidate E = D + two more exact rewrites from candidate B's line map:
 (1) m_move track avoidance: the matching track entries are found with a fixed 4-wide compare and visited in ascending order, so the rn2
     draws are the same as the original scan, without the variable-trip inner loop (10% + 4% of m_move's remaining mispredicts).
 (2) mfndpos tight-squeeze test: for movers without tunnelling, wall-passing or Sokoban rules, bad_rock is exactly 'rock terrain', so the
     two orthogonal cells are read from the nonrock neighbour mask; other movers keep the exact calls."""
import sys, shutil
from pathlib import Path
R=Path(__file__).resolve().parent; src=R/'engines'/sys.argv[1]/'source'
if not src.exists(): shutil.copytree(R/'engines/selD/source', src)
def rep(path, old, new):
    t=path.read_text(); assert t.count(old)==1, (path, old[:70]); path.write_text(t.replace(old,new))
rep(src/'src/monmove.c',
"""            if (appr != 0 && (trackmask & nh_move_position_bit(omx, omy, nx, ny))) {
                mtrk = &mtmp->mtrack[0];
                for (j = 0; j < jcnt; mtrk++, j++)
                    if (nx == mtrk->x && ny == mtrk->y)
                        if (rn2(4 * (cnt - j)))
                            goto nxti;
            }""",
"""            if (appr != 0 && (trackmask & nh_move_position_bit(omx, omy, nx, ny))) {
                /* same draws in the same order: one rn2 per matching track entry, ascending, until the first nonzero */
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
            }""")
m=src/'src/mon.c'
rep(m,
"""    unsigned int candidates, occupied;
    struct nh_move_column *cols;""",
"""    unsigned int candidates, occupied, nonrock_n, squeeze_n;
    boolean simple_rock;
    struct nh_move_column *cols;""")
rep(m,
"""    cols = &level.move_columns[x];
    if (!(flag & ALLOW_WALL) && !rockok && !treeok)""",
"""    cols = &level.move_columns[x];
    nonrock_n = nh_move_neighbours(cols[0].nonrock, cols[1].nonrock, cols[2].nonrock, y);
    /* tight squeeze: for movers without tunnelling, wall-passing or Sokoban rules bad_rock is exactly rock terrain, so the diagonals
       whose two orthogonal cells are both rock come straight from the nonrock mask; other movers test every diagonal exactly */
    simple_rock = !mover.sokoban && !SPWQ(mdat, SPW_TUNNELS, tunnels(mdat)) && !SPWQ(mdat, SPW_PASSWALL, passes_walls(mdat));
    {
        unsigned int r1 = !((nonrock_n >> 1) & 1U), r3 = !((nonrock_n >> 3) & 1U), r5 = !((nonrock_n >> 5) & 1U), r7 = !((nonrock_n >> 7) & 1U);
        squeeze_n = simple_rock ? ((r1 & r3) | ((r1 & r5) << 2) | ((r7 & r3) << 6) | ((r7 & r5) << 8)) : 0x145U;
    }
    if (!(flag & ALLOW_WALL) && !rockok && !treeok)""")
rep(m,
"""                /* check for diagonal tight squeeze */
                if (nx != x && ny != y && nh_mover_bad_rock(&mover, x, ny)
                    && nh_mover_bad_rock(&mover, nx, y) && nh_mover_squeeze(&mover))
                    continue;""",
"""                /* check for diagonal tight squeeze (squeeze_n: see above) */
                if ((squeeze_n & (1U << bit))
                    && (simple_rock || (nh_mover_bad_rock(&mover, x, ny) && nh_mover_bad_rock(&mover, nx, y)))
                    && nh_mover_squeeze(&mover))
                    continue;""")
print('E applied to', src)
