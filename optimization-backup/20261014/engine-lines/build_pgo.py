"""PGO build of one engine source tree with the same profile workloads as tile_signed_pgo (score + depth replay_vec, P-cores).
usage: python3 build_pgo.py <name>   (expects engines/<name>/source; writes engines/<name>/{build,profiles,generate,*.log,manifest.json})"""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, time
R=Path(__file__).resolve().parent; OLD=Path('/puffertank/experiments/nethack-perf-20260917')
clean={k:v for k,v in os.environ.items() if not k.startswith(('NH_','NLE_','OMP_','GOMP_','CPU_','PUF_','PUFFER_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','NETHACKOPTIONS','CPUPROFILE')}
clean.update(NETHACKDIR=str(OLD/'dat'),NH_ZT_MASK='0',OMP_PROC_BIND='true',OMP_PLACES='cores')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
name=sys.argv[1]; d=R/'engines'/name; s=d/'source'; b=d/'build'; prof=d/'profiles'; assert s.exists(), s
if b.exists(): shutil.rmtree(b)
if prof.exists(): shutil.rmtree(prof)
prof.mkdir(); commands=[]
def invoke(label,cmd,extra=None):
    cmd=list(map(str,cmd)); t0=time.monotonic(); print('START',name,label,flush=True)
    with (d/(label+'.log')).open('w') as f: rc=subprocess.run(cmd,env=dict(clean,**(extra or {})),stdout=f,stderr=subprocess.STDOUT).returncode
    out=(d/(label+'.log')).read_text(errors='replace'); commands.append({'label':label,'command':cmd,'rc':rc,'seconds':time.monotonic()-t0})
    (d/'commands.json').write_text(json.dumps(commands,indent=2)); assert rc==0, out[-4000:]
    print('DONE',name,label,round(time.monotonic()-t0,1),flush=True); return out
def build(phase,flags):
    cmd=['cmake','-S',s,'-B',b,'-DCMAKE_BUILD_TYPE=Release','-DNLE_TLS_INITIAL_EXEC=ON','-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON','-DCMAKE_C_FLAGS=-fno-semantic-interposition '+flags,'-DCMAKE_CXX_FLAGS=-fno-semantic-interposition '+flags]
    for dep in ('bzip2','deboost_context','pybind11'): cmd+=['-DFETCHCONTENT_SOURCE_DIR_'+dep.upper()+'=/puffertank/pufferlib/vendor/fast-nle/build/_deps/'+dep+'-src']
    invoke(phase+'_configure',cmd); return invoke(phase+'_build',['cmake','--build',b,'--target','nethack','-j8'])
build('generate','-fprofile-generate='+str(prof)+' -fprofile-update=atomic')
(d/'generate').mkdir(exist_ok=True); shutil.copy2(b/'libnethack.so',d/'generate/libnethack.so')
for workload in ('score','depth'):
    corpus=OLD/('score-balanced-v2' if workload=='score' else 'depth-record-v2')
    selected=json.loads((OLD/(workload+'-timing-selected.json')).read_text())[::4]
    paths=[corpus/Path(x['path']).name for x in selected]; assert len(paths)==8
    invoke(workload+'_profile',['taskset','-c','0,2,4,6,8,10,12,14',OLD/'harness-v3'/workload/'replay_vec','time','8','20000','10000',*paths],dict(LD_LIBRARY_PATH=str(b),NH_DISC_SWAP=str(int(workload=='depth'))))
assert list(prof.rglob('*.gcda'))
out=build('use','-fprofile-use='+str(prof)+' -fprofile-correction -Werror=coverage-mismatch')
(d/'manifest.json').write_text(json.dumps({'library_sha256':sha(b/'libnethack.so'),'profile_files':len(list(prof.rglob('*.gcda'))),'missing_profile_warnings':[l for l in out.splitlines() if 'missing-profile' in l]},indent=2))
print('PGO READY',name,sha(b/'libnethack.so'),flush=True)
