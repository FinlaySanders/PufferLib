from pathlib import Path
import os,subprocess,json,hashlib,time
r=Path('/puffertank/experiments/inventory-supervised-20260914');repo=Path('/puffertank/pufferlib')
assert (r/'BUILD_DONE').exists()
model=repo/'resources/nethack/fixwt4b_s705.bin'
e={k:v for k,v in os.environ.items() if not k.startswith('NH_') and k not in ('LD_PRELOAD','LD_LIBRARY_PATH','NETHACKOPTIONS','NLE_STOCK_LIB')}
e.update(NETHACKDIR=str(repo/'vendor/fast-nle/build/dat'),OMP_NUM_THREADS='16',CUDA_VISIBLE_DEVICES='0')
manifest=dict(policy='fixwt4b_s705',checkpoint_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256((r/'puffer').read_bytes()).hexdigest(),columns=3718,slots=55,sfeat=24,slot_rep=16,inventory_rep=384,encoder_rep=1024,sample_stride=16,warmup_forward_calls=256,splits={})
# Distinct initial dungeon seeds and action seeds for every partition.
for split,frames,seed in [('train',65536,101000000),('validation',16384,201000000),('test',16384,301000000)]:
 out=r/(split+'.bin');assert not out.exists();env=dict(e,NH_INV_CAPTURE=str(out),NH_INV_FRAMES=str(frames),NH_DATA_SEED=str(seed))
 cmd=[str(r/'puffer'),'eval','--headless',f'--base.load_model_path={model}',f'--base.seed={seed}','--base.eval_agents=128','--vec.num_buffers=1','--vec.num_threads=16','--base.eval_episodes=100000','--base.cudagraphs=-1']
 with (r/(split+'.log')).open('x') as f:
  proc=subprocess.Popen(cmd,cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
  (r/'capture_active.json').write_text(json.dumps(dict(split=split,pid=proc.pid,command=cmd)))
  print('START',split,proc.pid,flush=True);rc=proc.wait()
 assert rc==0 and 'CAPTURE_DONE' in (r/(split+'.log')).read_text(),split
 assert out.stat().st_size==frames*3718*4,(split,out.stat().st_size)
 manifest['splits'][split]=dict(frames=frames,seed=seed,sha256=hashlib.sha256(out.read_bytes()).hexdigest())
 (r/'capture_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print('DONE',split,flush=True)
(r/'CAPTURE_DONE').write_text('ok\n')
