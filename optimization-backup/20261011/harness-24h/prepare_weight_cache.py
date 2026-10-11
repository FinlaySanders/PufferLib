from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import floor_empty_study as builder

R=Path(__file__).resolve().parent
D=R/'weight_cache'
S=D/'source'
BASE=builder.BASE
assert not D.exists()
shutil.copytree(BASE,S)
p=S/'include/nh_ctx_gen.h';t=p.read_text()
needle='    void *nh_lazy[NH_LAZY_SLOTS];\n};';assert t.count(needle)==1
p.write_text(t.replace(needle,'''    void *nh_lazy[NH_LAZY_SLOTS];
    struct obj *weight_cache_head;
    int weight_cache_valid, weight_cache_sum, weight_cache_rocks;
};'''))
p=S/'src/invent.c';t=p.read_text();needle='void\nupdate_inventory()\n{';assert t.count(needle)==1
p.write_text(t.replace(needle,needle+'\n    nh_cur->weight_cache_valid = 0;'))
p=S/'src/eat.c';t=p.read_text();needle='    piece->owt = weight(piece);';assert t.count(needle)==1
p.write_text(t.replace(needle,needle+'\n    nh_cur->weight_cache_valid = 0;'))
p=S/'src/nle.c';t=p.read_text();a=t.index('nle_step(nle_ctx_t *nle, nle_obs *obs)');needle='    nh_cur = (struct nh_ctx *) nle->nh;';assert needle in t[a:]
p.write_text(t[:a]+t[a:].replace(needle,needle+'\n    nh_cur->weight_cache_valid = 0;',1))
p=S/'src/hack.c';t=p.read_text();a=t.index('int\ninv_weight()\n{');b=t.index('\n/*',a)
fn=t[a:b]
needle='    register int wt = 0;';assert fn.count(needle)==1
fn=fn.replace(needle,needle+'''
    int rocks = throws_rocks(youmonst.data) != 0;
    int hit = nh_cur->weight_cache_valid && nh_cur->weight_cache_head == invent
        && nh_cur->weight_cache_rocks == rocks;
#ifndef NLE_WEIGHT_VERIFY
    if (hit) wt = nh_cur->weight_cache_sum;
    else
#endif
    {
''')
needle='    wc = weight_cap();';assert fn.count(needle)==1
fn=fn.replace(needle,'''#ifdef NLE_WEIGHT_VERIFY
        if (hit && wt != nh_cur->weight_cache_sum)
            panic("weight cache stale: cached %d actual %d", nh_cur->weight_cache_sum, wt);
#endif
        nh_cur->weight_cache_head = invent;
        nh_cur->weight_cache_sum = wt;
        nh_cur->weight_cache_rocks = rocks;
        nh_cur->weight_cache_valid = 1;
    }
'''+needle)
p.write_text(t[:a]+fn+t[b:])
patch=''
for rel in ('include/nh_ctx_gen.h','src/hack.c','src/invent.c','src/eat.c','src/nle.c'):
    patch+=''.join(difflib.unified_diff((BASE/rel).read_text().splitlines(True),(S/rel).read_text().splitlines(True),fromfile='base/'+rel,tofile='candidate/'+rel))
(D/'changes.patch').write_text(patch)
(D/'source_manifest.json').write_text(json.dumps({str(p.relative_to(S)):hashlib.sha256(p.read_bytes()).hexdigest() for p in S.rglob('*') if p.is_file()},indent=2))
builder.D=D;builder.S=S;builder.B=D/'build';builder.build()
cmd=json.loads((D/'build_command.json').read_text());cmd[cmd.index('-B')+1]=str(D/'verify')
cmd=[x+' -DNLE_WEIGHT_VERIFY' if x.startswith(('-DCMAKE_C_FLAGS=','-DCMAKE_CXX_FLAGS=')) else x for x in cmd]
(D/'verify_command.json').write_text(json.dumps(cmd,indent=2))
with (D/'verify_build.log').open('w') as f:
    subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
    subprocess.run(['cmake','--build',str(D/'verify'),'--target','nethack','-j8'],stdout=f,stderr=subprocess.STDOUT,check=True)
print('BUILT fast and verification variants',flush=True)
