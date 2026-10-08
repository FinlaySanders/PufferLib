from pathlib import Path
import os,select,subprocess,json
r=Path(__file__).parent
# Wait for exactly the current comparison runner, not a name pattern.
pid=1429503
try:
 args=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
 if str(r/'train.py').encode() in args:
  fd=os.pidfd_open(pid);select.select([fd],[],[]);os.close(fd)
except (FileNotFoundError,ProcessLookupError):pass

def run(cmd,log,cwd=None,env=None):
 print('START',log,flush=True)
 with (r/log).open('w') as f:p=subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
 print('DONE',log,p.returncode,flush=True);assert p.returncode==0,log
run(['/usr/local/cuda/bin/nvcc','-O3','-arch=sm_89',str(r/'filter_lt.cu'),'-lcublas','-lcublasLt','-o',str(r/'filter_lt')],'build-filter.log')
run([str(r/'filter_lt'),str(r/'lt-config-rejected.bin'),str(r/'lt-config.bin')],'filter-lt.log')
run([str(r/'muon_check'),str(r/'lt-config.bin')],'muon-check.log')
run(['python',str(r/'patch_check.py')],'patch-check.log')
run(['python',str(r/'patch_lt.py')],'patch-lt.log')
for name,flags in [('workspace_check','-DPUF_GEMM_WORKSPACE -DPUF_GEMM_VALIDATE'),('both_check','-DPUF_GEMM_WORKSPACE -DPUF_SPLITK -DPUF_GEMM_VALIDATE'),('lt','-DPUF_GEMM_WORKSPACE -DPUF_LT_MUON -lcublasLt')]:
 run(['./build.sh','nethack','puffer_'+name],'build-'+name+'.log',r/'source',dict(os.environ,NVCC_EXTRA='-DPUF_ENV_WS -DPUF_PERF_LOAD -DPUF_HEAD_SAMPLER '+flags))
e={k:v for k,v in os.environ.items() if not k.startswith(('NH_','NLE_','OMP_','PUF_','PUFFER_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','NETHACKOPTIONS','NVCC_EXTRA')}
e.update(NETHACKDIR='/puffertank/experiments/nethack-perf-20260917/dat',NH_ZT_MASK='0',NH_DISC_SWAP='0',CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='32',LD_LIBRARY_PATH='/puffertank/experiments/nethack-perf-20260917/variants/candidate14-lto-local',PUF_PERF_START_WEIGHTS='/puffertank/pufferlib/resources/nethack/fixwt4b_s705.bin')
for name in ['workspace_check','both_check']:
 run([str(r/'source'/('puffer_'+name)),'train','--headless','--base.env_name=nethack','--base.cudagraphs=0','--train.total_timesteps=524288','--base.seed=901','--base.eval_episodes=8','--base.eval_agents=8','--base.run_id=check','--base.checkpoint_dir='+str(r/name/'checkpoints'),'--base.log_dir='+str(r/name/'logs')],name+'.log',r/'source',e)
p=r/'train_lt.py';s=p.read_text().replace("else label\n","else label.split('-')[0]\n");p.write_text(s)
run(['python',str(p),'workspace-c','lt','workspace-d'],'train-lt.log')
print('ALL_DONE',flush=True)
