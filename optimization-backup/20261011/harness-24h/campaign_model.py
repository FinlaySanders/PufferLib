from pathlib import Path
import json
import subprocess
import sys

root=Path(__file__).resolve().parent
spec=Path(sys.argv[1])
jobs=json.loads(spec.read_text())
results=[]
for job in jobs:
    label=job['label']
    command=[sys.executable,str(root/'run_model.py'),job.get('kind','time'),label,
             '--binary='+str(root/'binaries'/job.get('binary','baseline'))]
    command+=['--env='+k+'='+str(v) for k,v in job.get('env',{}).items()]
    command+=job.get('args',[])
    print('START',label,flush=True)
    with (root/(label+'.launcher.log')).open('w') as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    result=json.loads((root/'runs'/label/'result.json').read_text())
    results.append(result)
    spec.with_suffix('.results.json').write_text(json.dumps(results,indent=2))
    print('DONE',label,{k:result[k] for k in ['mean_ms','sps','wall_seconds'] if k in result},flush=True)
