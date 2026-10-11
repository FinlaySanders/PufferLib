"""Avoid full tile/dungeon reads on ordinary non-water terrain."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import floor_empty_study as builder

R = Path(__file__).resolve().parent
D = R / 'terrain_queries'
S = D / 'source'
BASE = builder.BASE

def prepare():
    assert not D.exists()
    shutil.copytree(BASE, S)
    p = S / 'include/hack.h'
    t = p.read_text()
    before = '    if (ltyp == POOL || ltyp == MOAT || ltyp == WATER || is_moat(x, y))'
    after = '''    if (ltyp == POOL || ltyp == MOAT || ltyp == WATER
        || (ltyp == DRAWBRIDGE_UP && is_moat(x, y)))'''
    assert t.count(before) == 1
    p.write_text(t.replace(before, after))
    p = S / 'src/mon.c'
    t = p.read_text()
    before = '''        || (!Is_juiblex_level(&u.uz) && (c->typ == MOAT
            || (c->typ == DRAWBRIDGE_UP && (c->rmflags & DB_UNDER) == DB_MOAT))));'''
    after = '''        || (TYP_AT(x, y) == DRAWBRIDGE_UP && !Is_juiblex_level(&u.uz)
            && (c->rmflags & DB_UNDER) == DB_MOAT));'''
    assert t.count(before) == 1
    p.write_text(t.replace(before, after))
    patch = ''
    for rel in ('include/hack.h', 'src/mon.c'):
        patch += ''.join(difflib.unified_diff(
            (BASE / rel).read_text().splitlines(True),
            (S / rel).read_text().splitlines(True),
            fromfile='base/' + rel, tofile='candidate/' + rel))
    (D / 'changes.patch').write_text(patch)
    (D / 'source_manifest.json').write_text(json.dumps({
        str(p.relative_to(S)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in S.rglob('*') if p.is_file()}, indent=2))
    (D / 'HYPOTHESIS.md').write_text('''# Water predicates from existing terrain type

The current engine maintains a compact terrain type plane. is_pool and
nh_cell_pool nevertheless read a full tile's type and Juiblex-level state
for ordinary dry tiles. Their only additional water case is a raised
drawbridge over a moat. Gate this case with the already-read compact type.
No new cache or invalidation rules are introduced. The original is_moat
function is unchanged. The standalone minliquid early-return candidate is
not included; the mechanisms overlap and their gains must not be added.

Check ordinary-LTO golden/fuzz replay, then a short native timing screen.
If timing is useful, exhaustively compare original and candidate water
predicates across all terrain types, drawbridge masks, valid coordinates
and Juiblex-level flags using actual engine headers. Verify compact/primary
terrain coherence and replay the larger corpus before retention. Report
whole-pipeline timing separately from CPU-only timing.
''')

if __name__ == '__main__':
    import sys
    if sys.argv[1] == 'prepare':
        prepare()
    elif sys.argv[1] == 'build':
        builder.D, builder.S, builder.B = D, S, D / 'build'
        builder.build()
