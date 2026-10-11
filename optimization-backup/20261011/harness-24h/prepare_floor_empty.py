from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
import floor_empty_study as study

R = Path(__file__).resolve().parent
OLD = Path('/puffertank/experiments/nethack-compact-state-20261008')
BASE = study.BASE

def prepare(name, candidate):
    d = R/name
    s = d/'source'
    assert not d.exists()
    shutil.copytree(BASE, s)
    if candidate:
        p = s/'include/nh_ctx_gen.h'
        t = p.read_text()
        old = '    void *nh_lazy[NH_LAZY_SLOTS];\n};'
        assert t.count(old) == 1
        p.write_text(t.replace(old, '    void *nh_lazy[NH_LAZY_SLOTS];\n    unsigned long empty_query[64][2];\n};'))
        p = s/'src/monmove.c'
        t = p.read_text()
        old = '    nh_fobj_generation++;'
        assert t.count(old) == 1
        t = t.replace(old, '    if (++nh_fobj_generation == 0)\n        memset(nh_cur->empty_query, 0, sizeof nh_cur->empty_query);')
        a = t.index('struct obj *\nnh_fobj_next(')
        b = t.index('\nint\nm_move(', a)
        fn = t[a:b]
        old = '    struct obj *o;\n    if (!prev) {'
        assert fn.count(old) == 1
        fn = fn.replace(old, '    struct obj *o;\n    unsigned long empty_key = 0;\n    unsigned int empty_slot = 0;\n    if (!prev) {')
        old = '        cursor->fallback = nh_fobj_count < 0;'
        assert fn.count(old) == 1
        fn = fn.replace(old, old + r'''
        if (nh_fobj_count > 0 && lx >= 0 && lx <= 255 && hx >= 0 && hx <= 255
            && ly >= 0 && ly <= 255 && hy >= 0 && hy <= 255) {
            empty_key = 1UL + (unsigned int) lx + ((unsigned int) hx << 8)
                + ((unsigned int) ly << 16) + ((unsigned int) hy << 24);
            empty_slot = (empty_key * 11400714819323198485UL) >> 58;
            if (nh_cur->empty_query[empty_slot][0] == empty_key
                && nh_cur->empty_query[empty_slot][1] == nh_fobj_generation) {
#ifdef NLE_FOBJ_VERIFY
                for (o = fobj; o; o = o->nobj)
                    if (o->ox >= lx && o->ox <= hx && o->oy >= ly && o->oy <= hy)
                        panic("empty floor query cache mismatch");
#endif
                cursor->index = nh_fobj_count;
                return (struct obj *) 0;
            }
        }''')
        old = '    return (struct obj *) 0;\n}\n'
        assert fn.count(old) == 1
        fn = fn.replace(old, '''    if (empty_key) {
        nh_cur->empty_query[empty_slot][0] = empty_key;
        nh_cur->empty_query[empty_slot][1] = nh_fobj_generation;
    }
    return (struct obj *) 0;
}
''')
        p.write_text(t[:a]+fn+t[b:])
    patch = ''
    for rel in ('include/nh_ctx_gen.h','src/monmove.c'):
        patch += ''.join(difflib.unified_diff((BASE/rel).read_text().splitlines(True), (s/rel).read_text().splitlines(True), fromfile='base/'+rel, tofile=name+'/'+rel))
    (d/'changes.patch').write_text(patch)
    (d/'manifest.json').write_text(json.dumps({str(p.relative_to(s)):hashlib.sha256(p.read_bytes()).hexdigest() for p in s.rglob('*') if p.is_file()},indent=2))
    return d

if __name__ == '__main__':
    for name,candidate in [('floor_empty_base',False),('floor_empty_candidate',True)]:
        d=prepare(name,candidate)
        study.D=d;study.S=d/'source';study.B=d/'build'
        study.build()
    print('PREPARED AND BUILT',flush=True)
