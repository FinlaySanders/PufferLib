from pathlib import Path
import json
import os
import shlex
import subprocess
import time

R=Path(__file__).resolve().parent
OLD=Path('/puffertank/experiments/nethack-compact-state-20261008')
D=R/'floor_empty_study'
t=(OLD/'fobj_bytes_property.c').read_text()
needle='    fobj=NULL;\n    free(items);'
assert t.count(needle)==1
t=t.replace(needle,r'''
    for (int i=0;i<32;i++) {
        items[i].nobj=i+1<32 ? items+i+1 : NULL;
        items[i].ox=i%80; items[i].oy=i%21;
    }
    fobj=items;
    nh_fobj_invalidate();
    for (int trial=0;trial<20000;trial++) {
        int lx=draw()%80,hx=lx+(draw()%6),ly=draw()%21,hy=ly+(draw()%6);
        for (int rep=0;rep<5;rep++) {
            struct nh_fobj_cursor cursor;
            struct obj *got=nh_fobj_next(&cursor,NULL,lx,hx,ly,hy);
            struct obj *want=reference(NULL,lx,hx,ly,hy);
            assert(got==want);
            queries++;
            hash^=got ? (uint64_t)(got-items+1) : 0;
            hash*=1099511628211ULL;
            if (rep==2 && trial%3==0) {
                items[trial%32].ox=lx; items[trial%32].oy=ly;
                if (trial%9==0) nh_fobj_generation=ULONG_MAX;
                nh_fobj_invalidate();
            }
        }
    }
    fobj=NULL;
    free(items);''')
(D/'property.c').write_text(t)
rows=[]
for name in ['floor_empty_base','floor_empty_candidate']:
    e=R/name
    flags=[]
    lines=(e/'build/CMakeFiles/nethack.dir/flags.make').read_text().splitlines()
    for prefix in ['C_DEFINES = ','C_INCLUDES = ']:
        flags+=shlex.split(next(x[len(prefix):] for x in lines if x.startswith(prefix)))
    cmd=['cc','-O2','-g',*flags,str(D/'property.c'),'-L'+str(e/'build'),'-Wl,-rpath,'+str(e/'build'),'-lnethack','-o',str(e/'property')]
    subprocess.run(cmd,check=True)
    p=subprocess.run([str(e/'property')],capture_output=True,text=True)
    rows.append({'name':name,'command':cmd,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    (D/'PROPERTY.json').write_text(json.dumps(rows,indent=2))
    print(name,p.stdout+p.stderr,flush=True)
    assert p.returncode==0
assert rows[0]['stdout']==rows[1]['stdout']

clean={k:v for k,v in os.environ.items() if not k.startswith(('NH_','NLE_','OMP_','PUF_','PUFFER_','CPU_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','NETHACKOPTIONS')}
clean.update(NETHACKDIR='/puffertank/experiments/nethack-perf-20260917/dat',NH_ZT_MASK='0')
gold=sorted(map(str,(OLD/'checks/goldens').glob('*.golden')))
fuzz=sorted(map(str,(OLD/'checks/fuzz').glob('*.golden')))
assert len(gold)==34 and len(fuzz)==26
rows=[]
for label,exe,args,extra in [('golden','replay_golden',gold,{}),('fuzz','replay_golden',fuzz,{}),('status','replay_golden',gold,{'NLE_REPLAY_OPTIONS_APPEND':',!status_updates'}),('interleaved','replay_multi',gold,{}),('shuffled','replay_multi',gold,{})]:
    cmd=['/puffertank/experiments/nethack-perf-20260917/gates/'+exe]+(['--'+label] if exe=='replay_multi' else [])+[str(R/'floor_empty_candidate/build/libnethack.so'),clean['NETHACKDIR'],*args]
    start=time.monotonic()
    with (D/(label+'.log')).open('w') as f:
        p=subprocess.run(cmd,env=dict(clean,**extra),stdout=f,stderr=subprocess.STDOUT)
    rows.append({'label':label,'rc':p.returncode,'seconds':time.monotonic()-start,'command':cmd})
    (D/'QUICK_GATES.json').write_text(json.dumps(rows,indent=2))
    assert p.returncode==0, (D/(label+'.log')).read_text()[-3000:]
    print('PASS',label,round(time.monotonic()-start,2),flush=True)
