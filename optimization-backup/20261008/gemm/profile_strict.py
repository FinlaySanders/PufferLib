from pathlib import Path
import os,subprocess,json,select
r=Path(__file__).parent;d=r/'profile-strict';d.mkdir();s=r/'source'
e={k:v for k,v in os.environ.items() if not k.startswith(('NH_','NLE_','OMP_','PUF_','PUFFER_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','NETHACKOPTIONS','NVCC_EXTRA')};e.update(NETHACKDIR='/puffertank/experiments/nethack-perf-20260917/dat',NH_ZT_MASK='0',NH_DISC_SWAP='0',CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='32',LD_LIBRARY_PATH='/puffertank/experiments/nethack-perf-20260917/variants/candidate14-lto-local',PUF_PERF_START_WEIGHTS='/puffertank/pufferlib/resources/nethack/fixwt4b_s705.bin',PUF_PERF_LOADED_PROOF=str(d/'loaded.bin'))
cmd=[str(s/'puffer_strict'),'train','--headless','--base.env_name=nethack','--train.total_timesteps=16777216','--base.profile=1','--base.seed=901','--base.run_id=profile','--base.eval_episodes=8','--base.eval_agents=8','--base.checkpoint_dir='+str(d/'checkpoints'),'--base.log_dir='+str(d/'logs')]
ns=['nsys','profile','--trace=cuda,nvtx','--sample=none','--cpuctxsw=none','--cuda-graph-trace=node','--delay=60','--duration=10','--kill=none','--wait=all','--output='+str(d/'timeline'),*cmd];(d/'command.json').write_text(json.dumps(dict(command=ns,environment=e),indent=2))
with (d/'run.log').open('w') as f:p=subprocess.run(ns,cwd=s,env=e,stdout=f,stderr=subprocess.STDOUT)
assert p.returncode==0;print('CAPTURE_DONE',flush=True)
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  args=(proc/'cmdline').read_bytes().split(b'\0')
  if args and args[0]==cmd[0].encode() and cmd[-2].encode() in args:
   fd=os.pidfd_open(int(proc.name));select.select([fd],[],[]);os.close(fd)
 except (FileNotFoundError,ProcessLookupError,PermissionError):pass
assert (d/'checkpoints/nethack/profile/0000000016777216.bin').exists()
with (d/'export.log').open('w') as f:p=subprocess.run(['nsys','export','--type=sqlite','--output='+str(d/'timeline.sqlite'),str(d/'timeline.nsys-rep')],stdout=f,stderr=subprocess.STDOUT)
assert p.returncode==0;print('PROFILE_DONE',flush=True)
