# Agent-count scaling at constant batch 262144 and matched game age (4096 recorded steps per env, 12 measured epochs).
import json
from pathlib import Path
import make_ablate_specs as m
root=Path(__file__).resolve().parent
REG=[(512,512,8,20),(1024,256,16,28),(4096,64,64,76)]
jobs=[]
for width in (1024,512):
    for agents,horizon,start,epochs in REG:
        for rep in 'ab':
            jobs.append({'label':f'ablscale_w{width}_a{agents}_{rep}','runner':'scale','kind':'full','binary':'attribution_v37','env':m.FULL,
                         'args':[f'--epochs={epochs}',f'--start={start}',f'--width={width}',f'--agents={agents}',f'--horizon={horizon}']})
(root/'ablate_scale.json').write_text(json.dumps(jobs,indent=1)); print(len(jobs),'scale jobs')
