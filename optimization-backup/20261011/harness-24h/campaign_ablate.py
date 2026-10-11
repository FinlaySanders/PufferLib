# Serial ablation campaign; continues past failed runs and resumes by label.
from pathlib import Path
import json, subprocess, sys, time
root=Path(__file__).resolve().parent
spec=Path(sys.argv[1]); jobs=json.loads(spec.read_text())
out=spec.with_suffix('.results.json')
results=json.loads(out.read_text()) if out.exists() else []
done={r['label'] for r in results}
for job in jobs:
    label=job['label']
    if label in done: continue
    runner={'primary':'run_primary.py','model':'run_model.py','scale':'run_scale.py'}[job.get('runner','primary')]
    cmd=[sys.executable,str(root/runner),job.get('kind','full'),label,'--binary='+str(root/'binaries'/job.get('binary','attribution_v37'))]
    cmd+=['--env=%s=%s'%(k,v) for k,v in job.get('env',{}).items()]
    cmd+=job.get('args',[])
    t=time.time(); print('START',label,flush=True)
    with (root/(label+'.launcher.log')).open('w') as log:
        rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
    rf=root/'runs'/label/'result.json'
    r=json.loads(rf.read_text()) if rf.exists() else {'label':label,'rc':rc}
    r['launcher_rc']=rc; r['job']=job
    results.append(r); out.write_text(json.dumps(results,indent=2))
    print('DONE',label,'rc',rc,'sps',round(r.get('sps',0)),'wall',round(time.time()-t),flush=True)
