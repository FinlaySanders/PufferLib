from pathlib import Path
import subprocess,os,json,time
r=Path(__file__).resolve().parent;rows=[]
for tree,name,flags in [('source','puffer_baseline',''),('source','puffer_heads','-DPUF_HEAD_SAMPLER'),('depth-source','puffer_baseline',''),('depth-source','puffer_heads','-DPUF_HEAD_SAMPLER')]:
 cmd=['bash','build.sh','nethack',name];t=time.time()
 with (r/(tree+'-'+name+'-build.log')).open('w') as f:p=subprocess.run(cmd,cwd=r/tree,env=dict(os.environ,NVCC_EXTRA='-DPUF_ENV_WS -DPUF_PERF_LOAD '+flags),stdout=f,stderr=subprocess.STDOUT)
 rows.append(dict(tree=tree,name=name,flags=flags,command=cmd,rc=p.returncode,seconds=time.time()-t));(r/'build-results.json').write_text(json.dumps(rows,indent=2));print(tree,name,p.returncode,flush=True);assert p.returncode==0
