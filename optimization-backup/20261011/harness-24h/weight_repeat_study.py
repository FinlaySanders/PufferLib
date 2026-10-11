"""Measure repeated player-weight walks and audit inventory notifications."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess
import shutil
import sys
import floor_empty_study as builder

R=Path(__file__).resolve().parent
D=R/'weight_repeat_study'
S=D/'source'
BASE=builder.BASE

def prepare():
    assert not D.exists()
    shutil.copytree(BASE,S)
    p=S/'include/nh_ctx_gen.h'
    t=p.read_text()
    needle='    void *nh_lazy[NH_LAZY_SLOTS];\n};'
    assert t.count(needle)==1
    p.write_text(t.replace(needle,'''    void *nh_lazy[NH_LAZY_SLOTS];
    unsigned long weight_notify, weight_last_notify;
    struct obj *weight_last_head;
    int weight_last_sum, weight_last_cap, weight_last_rocks, weight_last_valid;
};'''))
    p=S/'src/invent.c';t=p.read_text()
    needle='void\nupdate_inventory()\n{'
    assert t.count(needle)==1
    p.write_text(t.replace(needle,needle+'\n    nh_cur->weight_notify++;'))
    p=S/'src/hack.c';t=p.read_text()
    a=t.index('int\ninv_weight()\n{');b=t.index('\n/*',a)
    fn=t[a:b]
    assert fn.count('register int wt = 0;')==1
    fn=fn.replace('register int wt = 0;','register int wt = 0;\n    int visited = 0;')
    assert fn.count('    while (otmp) {')==1
    fn=fn.replace('    while (otmp) {','    while (otmp) {\n        visited++;')
    assert fn.count('    wc = weight_cap();')==1
    fn=fn.replace('    wc = weight_cap();','    wc = weight_cap();\n    nh_weight_observe(wt, visited, wc);')
    code=r'''
struct weight_diag_row { unsigned long n[16]; };
static struct weight_diag_row weight_diag_rows[128];
static unsigned int weight_diag_threads;
static int weight_diag_enabled;
static __thread struct weight_diag_row *weight_diag_local;

void nh_diag_control(int enabled) {
    unsigned long n[16] = {0};
    if (enabled) memset(weight_diag_rows, 0, sizeof weight_diag_rows);
    else {
        for (unsigned int i=0;i<weight_diag_threads;i++)
            for (int j=0;j<16;j++) n[j]+=weight_diag_rows[i].n[j];
        fprintf(stderr,"WEIGHT_REPEAT calls=%lu entries=%lu previous=%lu same_sum=%lu same_capacity=%lu same_both=%lu notification_hit=%lu wrong_sum=%lu notification_hit_entries=%lu notification_changed=%lu head_changed=%lu rocks_changed=%lu\n",
                n[0],n[1],n[2],n[3],n[4],n[5],n[6],n[7],n[8],n[9],n[10],n[11]);
    }
    weight_diag_enabled=enabled;
}

static void nh_weight_observe(int wt, int visited, int cap) {
    if (!weight_diag_enabled) return;
    if (!weight_diag_local) {
        unsigned int i=__atomic_fetch_add(&weight_diag_threads,1,__ATOMIC_RELAXED);
        if (i>=128) abort();
        weight_diag_local=&weight_diag_rows[i];
    }
    unsigned long *n=weight_diag_local->n;
    int rocks=throws_rocks(youmonst.data)!=0;
    n[0]++;n[1]+=visited;
    if (nh_cur->weight_last_valid) {
        int same_sum=nh_cur->weight_last_sum==wt;
        int same_cap=nh_cur->weight_last_cap==cap;
        int notification_same=nh_cur->weight_last_notify==nh_cur->weight_notify;
        int head_same=nh_cur->weight_last_head==invent;
        int rocks_same=nh_cur->weight_last_rocks==rocks;
        n[2]++; n[3]+=same_sum; n[4]+=same_cap; n[5]+=same_sum&&same_cap;
        n[9]+=!notification_same;n[10]+=!head_same;n[11]+=!rocks_same;
        if (notification_same && head_same && rocks_same) {
            n[6]++;n[7]+=!same_sum;n[8]+=visited;
        }
    }
    nh_cur->weight_last_valid=1;
    nh_cur->weight_last_notify=nh_cur->weight_notify;
    nh_cur->weight_last_head=invent;
    nh_cur->weight_last_rocks=rocks;
    nh_cur->weight_last_sum=wt;
    nh_cur->weight_last_cap=cap;
}

'''
    p.write_text(t[:a]+code+fn+t[b:])
    patch=''
    for rel in ('include/nh_ctx_gen.h','src/hack.c','src/invent.c'):
        patch+=''.join(difflib.unified_diff((BASE/rel).read_text().splitlines(True),(S/rel).read_text().splitlines(True),fromfile='base/'+rel,tofile='diagnostic/'+rel))
    (D/'diagnostic.patch').write_text(patch)
    (D/'source_manifest.json').write_text(json.dumps({str(p.relative_to(S)):hashlib.sha256(p.read_bytes()).hexdigest() for p in S.rglob('*') if p.is_file()},indent=2))

def execute():
    builder.D=D;builder.S=S;builder.B=D/'build';builder.build()
    sys.path.insert(0,str(R/'native_pool'))
    from snapshot_test import run
    result=run('weight_repeat_census',512,'0:2048',engine=D/'build',workers=32,pin=False,binary_override=R/'floor_empty_study/snapshot_diag')
    lines=[s for s in (R/'native_pool/runs/weight_repeat_census/run.log').read_text().splitlines() if s.startswith('WEIGHT_REPEAT ')]
    assert len(lines)==1,lines
    counts={k:int(v) for k,v in (s.split('=') for s in lines[0].split()[1:])}
    out={'counts':counts,'endpoints_ok':result['endpoints_ok'],'diagnostic_timings_excluded':True,'note':'All original weight computations execute. Consecutive output equality is an opportunity bound, not a safe cache-validity rule. Notification check compares consecutive observations, so it can underestimate persistent stale-cache errors.'}
    (D/'COUNTS.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2),flush=True)

if __name__=='__main__':
    prepare();execute()
