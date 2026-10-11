import json,os,subprocess
from pathlib import Path
root=Path('/workspace/autoascend-benchmark')
rows=[json.loads(p.read_text()) for p in (root/'smoke2').glob('w*.jsonl')]
assert len(rows)==4 and all(r['completed'] and 'error' not in r for r in rows)
assert not (root/'cert4032').exists()
env=dict(os.environ,PYTHONPATH='/workspace/nle-stock:/workspace/autoascend-benchmark/autoascend',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMBA_NUM_THREADS='1')
with (root/'cert4032.log').open('x') as log:
    p=subprocess.Popen([str(root/'venv/bin/python'),str(root/'run.py'),'--workers','96','--episodes','42','--out',str(root/'cert4032')],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,stdin=subprocess.DEVNULL)
(root/'cert4032.pid').write_text(str(p.pid)+'\n')
print('STARTED',p.pid)
