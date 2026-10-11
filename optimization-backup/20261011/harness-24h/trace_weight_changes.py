from pathlib import Path
import difflib
import hashlib
import json
import shutil
import sys
import floor_empty_study as builder

R=Path(__file__).resolve().parent
D=R/'weight_change_trace'
S=D/'source'
assert not D.exists()
shutil.copytree(R/'weight_repeat_study/source',S)
p=S/'src/hack.c'
t=p.read_text()
# System declarations before NetHack's macro-heavy headers.
t='#define _GNU_SOURCE\n#include <execinfo.h>\n#include <dlfcn.h>\n'+t
needle='struct weight_diag_row { unsigned long n[16]; };'
assert t.count(needle)==1
t=t.replace(needle,'''struct weight_trace_sample { void *pc[16]; int depth, before, after; long turn; };
struct weight_diag_row { unsigned long n[16]; struct weight_trace_sample samples[16]; };''')
needle='    weight_diag_enabled=enabled;'
assert t.count(needle)==1
t=t.replace(needle,'''    if (!enabled) {
        for (unsigned int i=0;i<weight_diag_threads;i++) {
            for (int j=0;j<16;j++) {
                struct weight_trace_sample *s=&weight_diag_rows[i].samples[j];
                if (!s->depth) continue;
                fprintf(stderr,"WEIGHT_TRACE thread=%u sample=%d old=%d new=%d turn=%ld",i,j,s->before,s->after,s->turn);
                for (int k=0;k<s->depth;k++) {
                    Dl_info info;
                    if (dladdr(s->pc[k],&info))
                        fprintf(stderr," %s+0x%lx", info.dli_fname,(unsigned long)s->pc[k]-(unsigned long)info.dli_fbase);
                }
                fprintf(stderr,"\\n");
            }
        }
    }
'''+needle)
needle='            n[6]++;n[7]+=!same_sum;n[8]+=visited;'
assert t.count(needle)==1
t=t.replace(needle,'''            n[6]++;n[7]+=!same_sum;n[8]+=visited;
            if (!same_sum && n[7]<=16) {
                struct weight_trace_sample *s=&weight_diag_local->samples[n[7]-1];
                s->before=nh_cur->weight_last_sum;s->after=wt;s->turn=moves;
                s->depth=backtrace(s->pc,16);
            }''')
p.write_text(t)
(D/'trace.patch').write_text(''.join(difflib.unified_diff((R/'weight_repeat_study/source/src/hack.c').read_text().splitlines(True),t.splitlines(True),fromfile='diagnostic/src/hack.c',tofile='trace/src/hack.c')))
builder.D=D;builder.S=S;builder.B=D/'build';builder.build()
sys.path.insert(0,str(R/'native_pool'))
from snapshot_test import run
result=run('weight_change_trace',512,'0:2048',engine=D/'build',workers=32,pin=False,binary_override=R/'floor_empty_study/snapshot_diag')
log=(R/'native_pool/runs/weight_change_trace/run.log').read_text()
lines=[s for s in log.splitlines() if s.startswith('WEIGHT_TRACE ')]
assert lines
(D/'traces.txt').write_text('\n'.join(lines)+'\n')
(D/'RESULT.json').write_text(json.dumps({'samples':len(lines),'endpoints_ok':result['endpoints_ok'],'engine_sha256':hashlib.sha256((D/'build/libnethack.so').read_bytes()).hexdigest(),'timing_excluded':True},indent=2))
print('TRACE SAMPLES',len(lines),flush=True)
