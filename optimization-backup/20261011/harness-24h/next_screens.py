from pathlib import Path
import json, os, subprocess, time
r=Path(__file__).resolve().parent
# An already-verified campaign must finish normally before any build or new timing.
campaign_pid=2896611
while Path(f'/proc/{campaign_pid}/cmdline').exists():
 cmd=Path(f'/proc/{campaign_pid}/cmdline').read_bytes()
 if b'campaign.py' not in cmd or b'COHORT_RECHECK2.json' not in cmd:
  raise RuntimeError('Expected campaign process identity changed')
 time.sleep(2)
rows=json.loads((r/'COHORT_RECHECK2.results.json').read_text())
assert len(rows)==7 and all(x['rc']==0 for x in rows)
print('Previous campaign finished; building new isolated candidates.',flush=True)
def run(cmd,log):
 print('START',log,flush=True)
 with (r/log).open('w') as f: subprocess.run(cmd,cwd=r,stdout=f,stderr=subprocess.STDOUT,check=True)
 print('DONE',log,flush=True)
run(['python','build.py','affinity_v12','-DPUF_MUON_OUTPLACE'],'affinity_v12.prepare.log')
run(['g++','-O2','-pthread','-DNVTX_DISABLE','-I/usr/local/cuda/include','bounded_pool_smoke.cpp','-o','bounded_pool_smoke'],'bounded_pool.build.log')
run([str(r/'bounded_pool_smoke')],'bounded_pool.smoke.log')
run(json.loads((r/'native_bounded/compile_command.json').read_text()),'native_bounded.build.log')
run(['python','run.py','full','scheduling_v12_smoke','--binary='+str(r/'binaries/affinity_v12'),'--epochs=4','--start=1','--env=PUF_CUDA_WAIT=block','--env=PUF_CPU_AFFINITY=1','--env=PUF_TIMING_STRIDE=16','--env=PUF_BUFFER_LEAD=4'],'scheduling_v12_smoke.launcher.log')
run(['python','native_bounded/snapshot_test.py','lead2048_screen', '2048', '0:512,6:512,7:512,8:512,9:512,0:512','--engine','/puffertank/experiments/nethack-compact-state-20261008/engines/movement_object_presence_pgo_followthrough/build'],'native_bounded.screen.log')
run(['python','campaign.py','AFFINITY_SCREEN.json'],'affinity_campaign.log')
print('ALL SCREENS COMPLETE',flush=True)
