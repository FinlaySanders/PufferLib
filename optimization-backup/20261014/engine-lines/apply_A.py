"""Candidate A: branch-free candidate selection in m_move (+ position bit, should_displace min). Bit-exact by construction: same predicates, same RNG draws."""
import sys, shutil
from pathlib import Path
R=Path(__file__).resolve().parent; src=R/'engines'/sys.argv[1]/'source'
if not src.exists(): shutil.copytree(R/'engines/base_source', src)
def rep(path, old, new):
    t=path.read_text(); assert t.count(old)==1, (path, old[:60]); path.write_text(t.replace(old,new))
rep(src/'include/movement_masks.h',
"""    unsigned int dx = (unsigned int) (px - x + 1);
    unsigned int dy = (unsigned int) (py - y + 1);
    return dx < 3 && dy < 3 ? 1U << (3 * dx + dy) : 0U;""",
"""    unsigned int dx = (unsigned int) (px - x + 1);
    unsigned int dy = (unsigned int) (py - y + 1);
    unsigned int in = (dx < 3U) & (dy < 3U); /* branch-free: an out-of-range position yields 0 */
    return (1U << ((3U * dx + dy) & 31U)) & (0U - in);""")
rep(src/'src/monmove.c',
"""            nearer = ((ndist = dist2(nx, ny, gx, gy)) < nidist);

            if ((appr == 1 && nearer) || (appr == -1 && !nearer)
                || (!appr && !rn2(++chcnt)) || !mmoved) {
                nix = nx;
                niy = ny;
                nidist = ndist;
                chi = i;
                mmoved = 1;
            }""",
"""            ndist = dist2(nx, ny, gx, gy);
            nearer = (ndist < nidist);
            {
                /* The original predicate without its data-dependent branch: appr 1 takes a nearer cell, -1 a farther one,
                   0 draws rn2(++chcnt) for every candidate exactly as before, and the first candidate is always taken. */
                int take = appr ? ((nearer != (appr < 0)) | !mmoved) : (!rn2(++chcnt) | !mmoved);
                int m = -take;
                nix = (xchar) ((nx & m) | (nix & ~m));
                niy = (xchar) ((ny & m) | (niy & ~m));
                nidist = (ndist & m) | (nidist & ~m);
                chi = (i & m) | (chi & ~m);
                mmoved |= (schar) take;
            }""")
rep(src/'src/monmove.c',
"""        } else {
            if ((shortest_without_displacing == -1)
                || (ndist < shortest_without_displacing))
                shortest_without_displacing = ndist;
            count_without_displacing++;
        }""",
"""        } else {
            int upd = (shortest_without_displacing == -1) | (ndist < shortest_without_displacing);
            int m = -upd;
            shortest_without_displacing = (ndist & m) | (shortest_without_displacing & ~m);
            count_without_displacing++;
        }""")
print('A applied to', src)
