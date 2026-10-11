"""Profile the unchanged engine on broader current-policy games, then screen it."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import time

r=Path(__file__).resolve().parent
base=Path('/puffertank/experiments/nethack-compact-state-20261008/engines/movement_object_presence_pgo_followthrough')
d=r/'current_workload_pgo'
s,b,prof=d/'source',d/'build',d/'profiles'
assert not d.exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
shutil.copytree(base/'source',s)
prof.mkdir()
rows=[]
env={k:v for k,v in os.environ.items() if not k.startswith(('NH_','NLE_','OMP_','GOMP_','CPU_','PUF_','PUFFER_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','NETHACKOPTIONS','CPUPROFILE')}
env.update(NETHACKDIR='/puffertank/experiments/nethack-perf-20260917/dat',NH_ZT_MASK='0')

def invoke(label,cmd,extra=None):
    cmd=list(map(str,cmd));start=time.time()
    print('START',label,flush=True)
    with (d/(label+'.log')).open('w') as f:
        p=subprocess.Popen(cmd,env=dict(env,**(extra or {})),stdout=f,stderr=subprocess.STDOUT,cwd=r)
        (r/'ACTIVE.json').write_text(json.dumps(dict(label='current_workload_pgo_'+label,pid=p.pid,started=start)))
        rc=p.wait(timeout=900)
    txt=(d/(label+'.log')).read_text(errors='replace')
    rows.append(dict(label=label,command=cmd,environment=extra or {},rc=rc,seconds=time.time()-start))
    (d/'commands.json').write_text(json.dumps(rows,indent=2))
    assert rc==0,txt[-5000:]
    print('DONE',label,round(time.time()-start,1),flush=True)
    return txt

def build(phase,flags):
    cmd=['cmake','-S',s,'-B',b,'-DCMAKE_BUILD_TYPE=Release',
        '-DNLE_TLS_INITIAL_EXEC=ON','-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON',
        '-DCMAKE_C_FLAGS=-fno-semantic-interposition '+flags,
        '-DCMAKE_CXX_FLAGS=-fno-semantic-interposition '+flags]
    for dep in ['bzip2','deboost_context','pybind11']:
        cmd.append('-DFETCHCONTENT_SOURCE_DIR_'+dep.upper()+'=/puffertank/pufferlib/vendor/fast-nle/build/_deps/'+dep+'-src')
    invoke(phase+'_configure',cmd)
    return invoke(phase+'_build',['cmake','--build',b,'--target','nethack','-j8'])

build('generate','-fprofile-generate='+str(prof)+' -fprofile-update=atomic')
(d/'generate').mkdir()
shutil.copy2(b/'libnethack.so',d/'generate/libnethack.so')
actions=Path('/puffertank/experiments/nethack-comprehensive-20261008/actions')
inputs={'current_actions':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(actions.glob('buf*.bin'))},
    'current_decisions_per_stream':'[0,8192); timed native screen begins at8192',
    'distinct_current_streams':512,'historical':{}}
# No snapshot/fork: normal exit flushes the profile. The first8192decisions
# train compiler feedback; subsequent decisions form the native timing window.
invoke('current_profile',[r/'native_pool/snapshot','512','24','8064','128',actions],
    dict(LD_LIBRARY_PATH=str(b),CPU_PIN='1',CPU_WARM_BURST='128',CPU_SETTLE='128'))
old=Path('/puffertank/experiments/nethack-perf-20260917')
for workload in ['score','depth']:
    corpus=old/('score-balanced-v2' if workload=='score' else 'depth-record-v2')
    selected=json.loads((old/(workload+'-timing-selected.json')).read_text())[::4]
    paths=[corpus/Path(x['path']).name for x in selected]
    assert len(paths)==8
    inputs['historical'][workload]={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    invoke(workload+'_profile',['taskset','-c','0,2,4,6,8,10,12,14',
        old/'harness-v3'/workload/'replay_vec','time','8','20000','10000',*paths],
        dict(LD_LIBRARY_PATH=str(b),NH_DISC_SWAP=str(int(workload=='depth'))))
(d/'profile-inputs.json').write_text(json.dumps(inputs,indent=2))
files=list(prof.rglob('*.gcda'));assert files
(d/'profile-manifest.json').write_text(json.dumps({str(p.relative_to(prof)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2))
txt=build('use','-fprofile-use='+str(prof)+' -fprofile-correction -Werror=coverage-mismatch')
assert 'coverage-mismatch' not in txt.lower(),txt[-5000:]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original={str(p.relative_to(base/'source')):sha(p) for p in (base/'source').rglob('*') if p.is_file()}
current={str(p.relative_to(s)):sha(p) for p in s.rglob('*') if p.is_file()}
assert original==current,'Source changed during profile/build'
(d/'manifest.json').write_text(json.dumps(dict(source_identical=True,source_hashes=current,
    library_sha256=sha(b/'libnethack.so'),baseline_library_sha256=sha(base/'build/libnethack.so'),
    missing_profile_warnings=[x for x in txt.splitlines() if 'missing-profile' in x]),indent=2))
# A cheap independent engine smoke before timings; full corpus checks are for wins.
prop=r/'floor_boxes/control/property'
invoke('property',[prop],dict(LD_LIBRARY_PATH=str(b)))
assert (d/'property.log').read_text()==(r/'floor_boxes/control/property.log').read_text()
native=[]
for name,engine in [('base_a',base/'build'),('candidate_a',b),('candidate_b',b),('base_b',base/'build')]:
    label='pgo_current2048_'+name
    invoke(label,['python',r/'native_pool/snapshot_test.py',label,'2048','0:512,0:512','--engine',engine])
    x=json.loads((r/'native_pool/runs'/label/'result.json').read_text())
    native.append(dict(label=label,sps=statistics.mean(float(z['result']['sps']) for z in x['cases']),
        endpoints=[{k:z['result'][k] for k in ['obs','turns','age']} for z in x['cases']]))
    print('NATIVE',native[-1],flush=True)
    if len(native)==2 and native[1]['sps']<native[0]['sps']*1.008:
        print('PARK: below0.8% firstpair screen gate',flush=True)
        break
assert all(x['endpoints']==native[0]['endpoints'] for x in native)
(d/'native.json').write_text(json.dumps(native,indent=2))
(r/'ACTIVE.json').write_text(json.dumps(dict(status='idle',last='current_workload_pgo_screen')))
print('CURRENT PGO SCREEN COMPLETE',flush=True)
