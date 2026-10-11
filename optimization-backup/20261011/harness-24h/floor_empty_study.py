"""Count repeat empty spatial floor queries; diagnostic timings are excluded."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import time

R = Path(__file__).resolve().parent
BASE = Path('/puffertank/experiments/nethack-compact-state-20261008/engines/movement_object_presence_pgo_followthrough/source')
D = R / 'floor_empty_study'
S = D / 'source'
B = D / 'build'

def prepare():
    assert not D.exists()
    shutil.copytree(BASE, S)
    p = S / 'include/nh_ctx_gen.h'
    t = p.read_text()
    needle = '    unsigned long g_nh_fobj_generation;'
    assert t.count(needle) == 1
    t = t.replace(needle, '    unsigned long empty_query_key[336], empty_query_generation[336];\n' + needle)
    p.write_text(t)
    p = S / 'src/monmove.c'
    t = p.read_text()
    old = 'struct obj *\nnh_fobj_next(struct nh_fobj_cursor *cursor, struct obj *prev,'
    assert t.count(old) == 1
    t = t.replace(old, 'static struct obj *\nnh_fobj_next_original(struct nh_fobj_cursor *cursor, struct obj *prev,')
    a = t.index('\nint\nm_move(')
    code = r'''
struct empty_query_row { unsigned long n[16]; };
static struct empty_query_row empty_query_rows[128];
static unsigned int empty_query_threads;
static int empty_query_enabled;
static __thread struct empty_query_row *empty_query_local;

void nh_diag_control(int enabled) {
    unsigned long n[16] = {0};
    if (enabled) memset(empty_query_rows, 0, sizeof empty_query_rows);
    else {
        for (unsigned int i = 0; i < empty_query_threads; i++)
            for (int j = 0; j < 16; j++) n[j] += empty_query_rows[i].n[j];
        fprintf(stderr, "EMPTY_QUERY starts=%lu eligible=%lu empty=%lu hit16=%lu hit64=%lu hit256=%lu objects=%lu empty_objects=%lu hit16_objects=%lu hit64_objects=%lu hit256_objects=%lu zero_objects=%lu\n",
                n[0],n[1],n[2],n[3],n[4],n[5],n[6],n[7],n[8],n[9],n[10],n[11]);
    }
    empty_query_enabled = enabled;
}

struct obj *
nh_fobj_next(struct nh_fobj_cursor *cursor, struct obj *prev,
             int lx, int hx, int ly, int hy)
{
    struct obj *o = nh_fobj_next_original(cursor, prev, lx, hx, ly, hy);
    if (empty_query_enabled && !prev) {
        if (!empty_query_local) {
            unsigned int i = __atomic_fetch_add(&empty_query_threads, 1, __ATOMIC_RELAXED);
            if (i >= 128) abort();
            empty_query_local = &empty_query_rows[i];
        }
        unsigned long *n = empty_query_local->n;
        n[0]++;
        if (lx >= 0 && lx <= 255 && hx >= 0 && hx <= 255
            && ly >= 0 && ly <= 255 && hy >= 0 && hy <= 255
            && nh_fobj_count >= 0) {
            unsigned long key = 1UL + (unsigned int) lx + ((unsigned int) hx << 8)
                + ((unsigned int) ly << 16) + ((unsigned int) hy << 24);
            unsigned long hash = key * 11400714819323198485UL;
            const int offsets[3] = {0, 16, 80};
            const int shifts[3] = {60, 58, 56};
            n[1]++;
            n[6] += nh_fobj_count;
            n[11] += nh_fobj_count == 0;
            if (!o) {n[2]++; n[7] += nh_fobj_count;}
            for (int k = 0; k < 3; k++) {
                int i = offsets[k] + (hash >> shifts[k]);
                int hit = nh_cur->empty_query_key[i] == key
                    && nh_cur->empty_query_generation[i] == nh_fobj_generation;
                if (hit && o) abort();
                n[3+k] += hit;
                if (hit) n[8+k] += nh_fobj_count;
                if (!o) {
                    nh_cur->empty_query_key[i] = key;
                    nh_cur->empty_query_generation[i] = nh_fobj_generation;
                }
            }
        }
    }
    return o;
}
'''
    p.write_text(t[:a] + code + t[a:])
    patch = ''
    for rel in ('include/nh_ctx_gen.h', 'src/monmove.c'):
        patch += ''.join(difflib.unified_diff((BASE/rel).read_text().splitlines(True), (S/rel).read_text().splitlines(True), fromfile='base/'+rel, tofile='diagnostic/'+rel))
    (D/'diagnostic.patch').write_text(patch)
    (D/'source_manifest.json').write_text(json.dumps({str(p.relative_to(S)):hashlib.sha256(p.read_bytes()).hexdigest() for p in S.rglob('*') if p.is_file()}, indent=2))

def build():
    flags = '-fno-semantic-interposition'
    cmd = ['cmake', '-S', str(S), '-B', str(B), '-DCMAKE_BUILD_TYPE=Release', '-DNLE_TLS_INITIAL_EXEC=ON', '-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON', '-DCMAKE_C_FLAGS='+flags, '-DCMAKE_CXX_FLAGS='+flags]
    for dep in ['bzip2', 'deboost_context', 'pybind11']:
        cmd += ['-DFETCHCONTENT_SOURCE_DIR_'+dep.upper()+'=/puffertank/pufferlib/vendor/fast-nle/build/_deps/'+dep+'-src']
    (D/'build_command.json').write_text(json.dumps(cmd, indent=2))
    t = time.monotonic()
    with (D/'build.log').open('w') as f:
        subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['cmake', '--build', str(B), '--target', 'nethack', '-j8'], stdout=f, stderr=subprocess.STDOUT, check=True)
    print('BUILT', time.monotonic()-t, flush=True)

if __name__ == '__main__':
    import sys
    if sys.argv[1] == 'prepare': prepare()
    elif sys.argv[1] == 'build': build()
