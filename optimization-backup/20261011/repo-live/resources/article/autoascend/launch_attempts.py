import json,os,subprocess
from pathlib import Path
root=Path('/workspace/autoascend-benchmark')
rows=[json.loads(line) for p in (root/'smoke_attempts_timeout').glob('w*.jsonl') for line in p.read_text().splitlines()]
assert len(rows)==8 and {(r['worker'],r['episode']) for r in rows}=={(w,e) for w in range(4) for e in (1,2)}
assert all(r['outcome']=='timeout' for r in rows)
assert not (root/'cert4032_attempts').exists()
env=dict(os.environ,PYTHONPATH='/workspace/nle-stock:/workspace/autoascend-benchmark/autoascend',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMBA_NUM_THREADS='1')
with (root/'cert4032_attempts.log').open('x') as log:
    p=subprocess.Popen([str(root/'venv/bin/python'),str(root/'run_attempts.py'),'--workers','96','--episodes','42','--timeout','720','--out',str(root/'cert4032_attempts')],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,stdin=subprocess.DEVNULL)
(root/'cert4032_attempts.pid').write_text(str(p.pid)+'\n')
print('STARTED',p.pid)
