"""Matched compiler feedback for the weight-cache candidate and its control."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import time

R=Path(__file__).resolve().parent
OLD=Path('/puffertank/experiments/nethack-perf-20260917')
clean={k:v for k,v in os.environ.items() if not k.startswith(('NH_','NLE_','OMP_','GOMP_','CPU_','PUF_','PUFFER_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','NETHACKOPTIONS','CPUPROFILE')}
clean.update(NETHACKDIR=str(OLD/'dat'),NH_ZT_MASK='0',OMP_PROC_BIND='true',OMP_PLACES='cores')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

for label,original in [('base',R/'floor_empty_base/source'),('candidate',R/'weight_cache/source')]:
    d=R/('weight_pgo_'+label);s=d/'source';b=d/'build';prof=d/'profiles'
    assert not d.exists()
    shutil.copytree(original,s);prof.mkdir();commands=[]
    def invoke(name,cmd,extra=None):
        cmd=list(map(str,cmd));start=time.monotonic();print('START',label,name,flush=True)
        with (d/(name+'.log')).open('w') as f:
            p=subprocess.Popen(cmd,env=dict(clean,**(extra or {})),stdout=f,stderr=subprocess.STDOUT)
            (d/'ACTIVE.json').write_text(json.dumps({'label':name,'pid':p.pid,'started':time.time()}))
            rc=p.wait(timeout=900)
        out=(d/(name+'.log')).read_text(errors='replace')
        commands.append({'label':name,'command':cmd,'environment':extra or {},'rc':rc,'seconds':time.monotonic()-start})
        (d/'commands.json').write_text(json.dumps(commands,indent=2));assert rc==0,out[-5000:]
        print('DONE',label,name,round(time.monotonic()-start,2),flush=True);return out
    def build(phase,flags):
        cmd=['cmake','-S',s,'-B',b,'-DCMAKE_BUILD_TYPE=Release','-DNLE_TLS_INITIAL_EXEC=ON','-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON','-DCMAKE_C_FLAGS=-fno-semantic-interposition '+flags,'-DCMAKE_CXX_FLAGS=-fno-semantic-interposition '+flags]
        for dep in ('bzip2','deboost_context','pybind11'):
            cmd+=['-DFETCHCONTENT_SOURCE_DIR_'+dep.upper()+'=/puffertank/pufferlib/vendor/fast-nle/build/_deps/'+dep+'-src']
        invoke(phase+'_configure',cmd)
        return invoke(phase+'_build',['cmake','--build',b,'--target','nethack','-j8'])
    build('generate','-fprofile-generate='+str(prof)+' -fprofile-update=atomic')
    (d/'generate').mkdir();shutil.copy2(b/'libnethack.so',d/'generate/libnethack.so')
    inputs={}
    for workload in ('score','depth'):
        corpus=OLD/('score-balanced-v2' if workload=='score' else 'depth-record-v2')
        selected=json.loads((OLD/(workload+'-timing-selected.json')).read_text())[::4]
        paths=[corpus/Path(x['path']).name for x in selected];assert len(paths)==8
        inputs[workload]={str(p):sha(p) for p in paths}
        invoke(workload+'_profile',['taskset','-c','0,2,4,6,8,10,12,14',OLD/'harness-v3'/workload/'replay_vec','time','8','20000','10000',*paths],dict(LD_LIBRARY_PATH=str(b),NH_DISC_SWAP=str(int(workload=='depth'))))
    (d/'profile-inputs.json').write_text(json.dumps(inputs,indent=2))
    profiles=list(prof.rglob('*.gcda'));assert profiles
    (d/'profile-manifest.json').write_text(json.dumps({str(p.relative_to(prof)):sha(p) for p in profiles},indent=2))
    out=build('use','-fprofile-use='+str(prof)+' -fprofile-correction -Werror=coverage-mismatch')
    assert 'coverage-mismatch' not in out.lower(),out[-5000:]
    source_hashes={str(p.relative_to(s)):sha(p) for p in s.rglob('*') if p.is_file()}
    assert source_hashes=={str(p.relative_to(original)):sha(p) for p in original.rglob('*') if p.is_file()}
    (d/'manifest.json').write_text(json.dumps({'source_hashes':source_hashes,'library_sha256':sha(b/'libnethack.so'),'missing_profile_warnings':[line for line in out.splitlines() if 'missing-profile' in line]},indent=2))
    (d/'ACTIVE.json').write_text(json.dumps({'status':'complete'}))
assert json.loads((R/'weight_pgo_base/profile-inputs.json').read_text())==json.loads((R/'weight_pgo_candidate/profile-inputs.json').read_text())
print('MATCHED PGO BUILDS COMPLETE',flush=True)
