from pathlib import Path
import subprocess,os,json,hashlib,time
root=Path('/workspace/autoascend-benchmark');name='cert4032_attempts_1440';out=root/name
assert not out.exists()
assert subprocess.check_output(['git','-C',str(root/'autoascend'),'rev-parse','HEAD'],text=True).strip()=='8527910bd85c4d851c18ad912aae606c92cd516a'
subprocess.run(['git','-C',str(root/'autoascend'),'diff','--quiet','HEAD','--'],check=True)
engine=Path('/workspace/nle-stock/nle/libnethack.so');eh=hashlib.sha256(engine.read_bytes()).hexdigest();assert eh=='25e6ca0f3fe28cfd806f384146637deb56a8d6ac98fb834b89aff5ef033620e2'
runner=root/'run_attempts.py';assert hashlib.sha256(runner.read_bytes()).hexdigest()=='c5dbdbda3a3039476880b11b0bffb9de4282df119bf778959a710752dfea147e'
manifest=dict(batch=name,workers=96,attempts_per_worker=42,total_attempts=4032,timeout_seconds=1440,agent_commit='8527910bd85c4d851c18ad912aae606c92cd516a',engine_sha256=eh,runner_sha256=hashlib.sha256(runner.read_bytes()).hexdigest(),started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),clock='real',seeding='unseeded challenge resets',accounting='retain last live score on agent exceptions/timeouts; no retries or exclusions')
(root/(name+'.manifest.json')).write_text(json.dumps(manifest,indent=2)+'\n')
# This supervisor stays alive after SSH disconnect and summarizes after the runner exits.
supervisor=root/(name+'_supervisor.py')
supervisor.write_text('''from pathlib import Path
import subprocess,json,os
root=Path('/workspace/autoascend-benchmark');name='cert4032_attempts_1440'
e={k:v for k,v in os.environ.items() if not k.startswith('NH_') and k not in ('LD_PRELOAD','LD_LIBRARY_PATH','NETHACKOPTIONS','NLE_STOCK_LIB')}
e.update(PYTHONPATH='/workspace/nle-stock:/workspace/autoascend-benchmark/autoascend',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMBA_NUM_THREADS='1')
cmd=[str(root/'venv/bin/python'),str(root/'run_attempts.py'),'--workers','96','--episodes','42','--timeout','1440','--out',str(root/name)]
with (root/(name+'.log')).open('x') as log:
 p=subprocess.Popen(cmd,cwd=root,env=e,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
 (root/(name+'.pid')).write_text(str(p.pid)+'\\n')
 rc=p.wait()
(root/(name+'.exit.json')).write_text(json.dumps(dict(returncode=rc)))
result=subprocess.check_output([str(root/'venv/bin/python'),str(root/'summarize_attempts.py'),str(root/name)],cwd=root,text=True)
(root/(name+'.summary.json')).write_text(result)
assert rc==0 and json.loads(result)['attempt_set_complete'],result
(root/(name+'.DONE')).write_text('complete\\n')
print(result,flush=True)
''')
with (root/(name+'.supervisor.log')).open('x') as log:
 p=subprocess.Popen([str(root/'venv/bin/python'),str(supervisor)],cwd=root,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
(root/(name+'.supervisor.pid')).write_text(str(p.pid)+'\n')
print('STARTED',name,'supervisor',p.pid)
