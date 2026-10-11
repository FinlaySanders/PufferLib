from pathlib import Path
import json
import subprocess
import sys

root = Path(__file__).resolve().parent
stage = sys.argv[1]
candidate = root/'binaries/fused_br_v2'
baseline = root/'binaries/baseline'
if stage == 'gpu':
    jobs = [('br_gpu_base_a', baseline, 0), ('br_gpu_disabled', candidate, 0),
            ('br_gpu_train_a', candidate, 2), ('br_gpu_train_b', candidate, 2),
            ('br_gpu_base_b', baseline, 0)]
    kind, extra = 'time', ['--trials=10']
elif stage == 'full':
    jobs = [('br_full_base_a', baseline, 0), ('br_full_inference_a', candidate, 1),
            ('br_full_base_b', baseline, 0)]
    kind, extra = 'full', ['--epochs=80','--start=64']
else: raise ValueError(stage)
results=[]
for label,binary,mode in jobs:
    command=[sys.executable,str(root/'run.py'),kind,label,'--binary='+str(binary),
        '--env=NH_FUSED_BR='+str(mode),*extra]
    print('START',label,flush=True)
    with (root/(label+'.launcher.log')).open('w') as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    result=json.loads((root/'runs'/label/'result.json').read_text())
    result['mode']=mode
    results.append(result)
    (root/('FUSED_BR_'+stage.upper()+'.json')).write_text(json.dumps(results,indent=2))
    print('DONE',label,{k:result[k] for k in ['mean_ms','sps','wall_seconds'] if k in result},flush=True)
