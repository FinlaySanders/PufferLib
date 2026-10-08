from pathlib import Path
import os,subprocess,json
r=Path(__file__).parent

def run(cmd,log,cwd=None,env=None):
 print('START',log,flush=True)
 with (r/log).open('w') as f:p=subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
 print('DONE',log,p.returncode,flush=True);assert p.returncode==0,log
for name,flags in [('strict_check','-DPUF_GEMM_WORKSPACE -DPUF_GEMM_STRICT -DPUF_GEMM_VALIDATE'),('both_check2','-DPUF_GEMM_WORKSPACE -DPUF_SPLITK -DPUF_GEMM_VALIDATE'),('strict','-DPUF_GEMM_WORKSPACE -DPUF_GEMM_STRICT')]:
 run(['./build.sh','nethack','puffer_'+name],'build-'+name+'.log',r/'source',dict(os.environ,NVCC_EXTRA='-DPUF_ENV_WS -DPUF_PERF_LOAD -DPUF_HEAD_SAMPLER '+flags))
e={k:v for k,v in os.environ.items() if not k.startswith(('NH_','NLE_','OMP_','PUF_','PUFFER_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','NETHACKOPTIONS','NVCC_EXTRA')};e.update(NETHACKDIR='/puffertank/experiments/nethack-perf-20260917/dat',NH_ZT_MASK='0',NH_DISC_SWAP='0',CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='32',LD_LIBRARY_PATH='/puffertank/experiments/nethack-perf-20260917/variants/candidate14-lto-local',PUF_PERF_START_WEIGHTS='/puffertank/pufferlib/resources/nethack/fixwt4b_s705.bin')
for name in ['strict_check','both_check2']:
 (r/name).mkdir(exist_ok=True);e['PUF_PERF_LOADED_PROOF']=str(r/name/'loaded.bin')
 run([str(r/'source'/('puffer_'+name)),'train','--headless','--base.env_name=nethack','--base.cudagraphs=-1','--train.total_timesteps=524288','--base.seed=901','--base.eval_episodes=8','--base.eval_agents=8','--base.run_id=check','--base.checkpoint_dir='+str(r/name/'checkpoints'),'--base.log_dir='+str(r/name/'logs')],name+'.log',r/'source',e)
p=r/'train_lt.py';s=p.read_text().replace("else label\n","else label.split('-')[0]\n");p.write_text(s)
run(['python',str(p),'strict','lt','workspace-d'],'train-lt.log')
