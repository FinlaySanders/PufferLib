"""Isolated dry-tile rejection before unchanged monster liquid handling."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import floor_empty_study as builder

R = Path(__file__).resolve().parent
D = R / 'liquid_fastpath'
S = D / 'source'
BASE = builder.BASE

def prepare():
    assert not D.exists()
    shutil.copytree(BASE, S)
    p = S / 'src/mon.c'
    t = p.read_text()
    needle = '''int minliquid(mtmp) register struct monst *mtmp;
{
    boolean inpool, inlava, infountain;
'''
    assert t.count(needle) == 1
    addition = '''
    /* Eels also have effects on dry land; keep their original path. */
    if (mtmp->data->mlet != S_EEL) {
        switch (TYP_AT(mtmp->mx, mtmp->my)) {
        case POOL: case MOAT: case WATER: case DRAWBRIDGE_UP:
        case LAVAPOOL: case FOUNTAIN:
            break;
        default:
            return 0;
        }
    }
'''
    p.write_text(t.replace(needle, needle + addition))
    (D / 'changes.patch').write_text(''.join(difflib.unified_diff(
        t.splitlines(True), p.read_text().splitlines(True),
        fromfile='base/src/mon.c', tofile='candidate/src/mon.c')))
    (D / 'source_manifest.json').write_text(json.dumps({
        str(p.relative_to(S)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in S.rglob('*') if p.is_file()}, indent=2))
    (D / 'HYPOTHESIS.md').write_text('''# Dry-tile monster liquid fast path

Current native profile attributes about 2% of samples to minliquid; this is
not a wall-clock fraction. Every moving monster enters the function. On a
dry ordinary tile with a non-eel species, all original effects are absent.
An early type switch may avoid the repeated terrain queries, Juiblex-level
test and monster/hero checks. This is a cheap bounded candidate, not an
expectation of a large gain. Golden/replay smoke checks precede timing;
broader special-terrain verification follows only if timing is useful.
No weight-cache change is included.

Water, lava, fountain, raised drawbridge and all eel species retain the
original code, including RNG calls, special levels and mounted behavior.
The guard uses the existing compact terrain type plane; its coherence
with the primary tile is already a baseline invariant, but must be checked
on replay before retention. Production files remain untouched.
''')

if __name__ == '__main__':
    import sys
    if sys.argv[1] == 'prepare':
        prepare()
    elif sys.argv[1] == 'build':
        builder.D, builder.S, builder.B = D, S, D / 'build'
        builder.build()
