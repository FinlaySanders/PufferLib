"""Candidate F = E + three exact micro-items from the line map: (1) rn2/rn2_on_display_rng read the per-env RNG state through the thread
context directly instead of calling the exported accessor; (2) nh_mover_scary tests the (loop-invariant, cheap) vampire predicate before the
altar terrain load; (3) mfndpos hoists Displaced && monseeu out of the candidate loop. Pure reorders; same results."""
import sys, shutil, re
from pathlib import Path
R=Path(__file__).resolve().parent; src=R/'engines'/sys.argv[1]/'source'
if not src.exists(): shutil.copytree(R/'engines/selE/source', src)
def rep(path, old, new, count=1):
    t=path.read_text(); assert t.count(old)==count, (path, t.count(old), old[:70]); path.write_text(t.replace(old,new))
rnd=src/'src/rnd.c'; t=rnd.read_text(); n=t.count('isaac64_next_uint64(nle_rng_state(')
assert n>=2, n
t=t.replace('isaac64_next_uint64(nle_rng_state(CORE))','isaac64_next_uint64(&nh_cur->g_rnd_c_rng_state[CORE])')
t=t.replace('isaac64_next_uint64(nle_rng_state(DISP))','isaac64_next_uint64(&nh_cur->g_rnd_c_rng_state[DISP])')
assert t.count('isaac64_next_uint64(nle_rng_state(')==0; rnd.write_text(t)
rep(src/'src/mon.c',
"""    if (IS_ALTAR(TYP_AT(x, y)) && (m->data->mlet == S_VAMPIRE || is_vampshifter(mon))) return TRUE;""",
"""    if ((m->data->mlet == S_VAMPIRE || is_vampshifter(mon)) && IS_ALTAR(TYP_AT(x, y))) return TRUE; /* monster test first: the terrain load is rarely needed */""")
rep(src/'src/mon.c',
"""    mover.monseeu = mon->mcansee && (!Invis || SPWQ(mdat, SPW_PERCEIVES, perceives(mdat)));""",
"""    mover.monseeu = mon->mcansee && (!Invis || SPWQ(mdat, SPW_PERCEIVES, perceives(mdat)));
    disp_see = Displaced && mover.monseeu; /* loop-invariant part of the displaced-image test */""")
rep(src/'src/mon.c',
"""    unsigned int candidates, occupied, nonrock_n, squeeze_n;
    boolean simple_rock;""",
"""    unsigned int candidates, occupied, nonrock_n, squeeze_n;
    boolean simple_rock, disp_see;""")
rep(src/'src/mon.c',
"""                if (Displaced && monseeu && mon->mux == nx
                    && mon->muy == ny) {""",
"""                if (disp_see && mon->mux == nx
                    && mon->muy == ny) {""")
print('F applied to', src)
