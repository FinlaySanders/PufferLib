from pathlib import Path
import json, subprocess, time
r=Path(__file__).resolve().parent
pid=2898888
while Path(f'/proc/{pid}/cmdline').exists():
 try:cmd=Path(f'/proc/{pid}/cmdline').read_bytes()
 except FileNotFoundError:break
 assert b'campaign.py' in cmd and b'AFFINITY_SCREEN.json' in cmd
 time.sleep(2)
rows=json.loads((r/'AFFINITY_SCREEN.results.json').read_text())
assert len(rows)==6 and all(x['rc']==0 for x in rows)
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
def run(cmd,log):
 print('START',log,flush=True)
 with (r/log).open('w') as f:subprocess.run(cmd,cwd=r,stdout=f,stderr=subprocess.STDOUT,check=True)
 print('DONE',log,flush=True)
run(['python','build.py','completion_workspace_v13','-DPUF_MUON_OUTPLACE'],'completion_workspace_v13.prepare.log')
run(['g++','-O2','-pthread','-DNVTX_DISABLE','-I/usr/local/cuda/include','completion_pool_smoke.cpp','-o','completion_pool_smoke'],'completion_pool.build.log')
run([str(r/'completion_pool_smoke')],'completion_pool.smoke.log')
run(json.loads((r/'native_completion/compile_command.json').read_text()),'native_completion.build.log')
run(['python','native_completion/snapshot_test.py','completion2048_screen','2048','0:512,10:512,11:512,12:512,12:512,11:512,10:512,0:512','--engine','/puffertank/experiments/nethack-compact-state-20261008/engines/movement_object_presence_pgo_followthrough/build'],'native_completion.screen.log')
run(['python','campaign.py','WORKSPACE_SCREEN.json'],'workspace_campaign.log')
print('ALL SECOND SCREENS COMPLETE',flush=True)
