"""Candidate D = A + cheap exact reorders found in the line map: itsstuck tests the (almost always false) u.ustuck identity before the
hero-form attack-table walk sticks(); pure predicates, identical result."""
import sys, shutil
from pathlib import Path
R=Path(__file__).resolve().parent; src=R/'engines'/sys.argv[1]/'source'
if not src.exists(): shutil.copytree(R/"engines/selA/source", src)
def rep(path, old, new):
    t=path.read_text(); assert t.count(old)==1, (path, old[:70]); path.write_text(t.replace(old,new))
rep(src/'src/monmove.c',
"""    if (sticks(youmonst.data) && mtmp == u.ustuck && !u.uswallow) {""",
"""    if (mtmp == u.ustuck && !u.uswallow && sticks(youmonst.data)) { /* same predicate; the identity test first skips the attack-table walk */""")
print('D applied to', src)
