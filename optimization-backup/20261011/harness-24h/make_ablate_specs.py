import json
from pathlib import Path
root=Path(__file__).resolve().parent
RETAINED='/puffertank/experiments/nethack-compact-state-20261008/engines/movement_object_presence_pgo_followthrough/build'
ENGINES={
 'eng_stock':'/puffertank/pufferlib/vendor/fast-nle/build',
 'eng_sept14':'/puffertank/experiments/nethack-perf-20260917/tight-loop/campaign2h/final',
 'eng_precompact':'/puffertank/experiments/nethack-locality-target-20261008/engines/persist/build',
}
GPUFAST={'PUF_OUTPLACE':1,'PUF_OUTPLACE_RANK':1,'PUF_SCAN_ROW':3,'PUF_SCAN_TILE':4,'NH_EMBED_REDUCE':7,
         'NH_IDENTITY_WARP':1,'NH_FUSED_BR':1,'NH_PASS_FAST':3,'NH_SFEAT_FAST':1}
ENTITY={'NH_ENTITY_FUSED':15,'NH_ENTITY_TRAIN_FUSED':15}
WAIT={'PUF_CUDA_WAIT':'block','PUF_FINISH_SLEEP':1}
BASE={'PUF_POOL_WORKERS':32,'PUF_INFER_PRIORITY':1,'PUF_ROLLOUT_DETAIL':1,'PUF_POOL_TIMING':1,'LD_LIBRARY_PATH':RETAINED}
FULL={**BASE,**GPUFAST,**ENTITY,**WAIT}
def arms():
    yield 'full_a',FULL,[]
    off={**BASE,'LD_LIBRARY_PATH':ENGINES['eng_stock'],'PUF_INFER_PRIORITY':0,'NH_GRAD_PIPELINE':0,'CUDA_DEVICE_MAX_CONNECTIONS':8}
    yield 'all_off',off,['--lanes=1']
    for name,path in ENGINES.items(): yield name,{**FULL,'LD_LIBRARY_PATH':path},[]
    yield 'gpufast_off',{**BASE,**ENTITY,**WAIT},[]
    yield 'entity_off',{**FULL,'NH_ENTITY_FUSED':0,'NH_ENTITY_TRAIN_FUSED':0},[]
    yield 'lanes1',FULL,['--lanes=1']
    yield 'gradpipe_off',{**FULL,'NH_GRAD_PIPELINE':0,'CUDA_DEVICE_MAX_CONNECTIONS':8},[]
    yield 'prio_off',{**FULL,'PUF_INFER_PRIORITY':0},[]
    yield 'wait_off',{**BASE,**GPUFAST,**ENTITY},[]
    yield 'workers16',{**FULL,'PUF_POOL_WORKERS':16},[]
    yield 'full_b',FULL,[]
def write(prefix,regimes):
    for tag,runner,width,base_args in regimes:
        jobs=[{'label':f'abl{prefix}{tag}_{name}','runner':runner,'kind':'full','binary':'attribution_v37',
               'env':env,'args':base_args+[f'--width={width}']+extra} for name,env,extra in arms()]
        (root/f'ablate_{prefix}{tag}.json').write_text(json.dumps(jobs,indent=1)); print(prefix+tag,len(jobs),'jobs')
if __name__=='__main__':
    write('',[('15m512','primary',1024,['--epochs=64','--start=24']),('5m512','primary',512,['--epochs=64','--start=24']),
              ('15m2048','model',1024,['--epochs=80','--start=64']),('5m2048','model',512,['--epochs=80','--start=64'])])
