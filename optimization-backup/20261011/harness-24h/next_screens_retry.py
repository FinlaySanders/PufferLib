from pathlib import Path
import json,subprocess
r=Path(__file__).resolve().parent
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
def run(cmd,log):
 print('START',log,flush=True)
 with (r/log).open('w') as f:subprocess.run(cmd,cwd=r,stdout=f,stderr=subprocess.STDOUT,check=True)
 print('DONE',log,flush=True)
run(json.loads((r/'native_bounded/compile_command.json').read_text()),'native_bounded.build_v2.log')
run(['python','native_bounded/snapshot_test.py','lead2048_screen_v2','2048','0:512,6:512,7:512,8:512,9:512,0:512','--engine','/puffertank/experiments/nethack-compact-state-20261008/engines/movement_object_presence_pgo_followthrough/build'],'native_bounded.screen_v2.log')
run(['python','campaign.py','AFFINITY_SCREEN.json'],'affinity_campaign.log')
print('ALL SCREENS COMPLETE',flush=True)
