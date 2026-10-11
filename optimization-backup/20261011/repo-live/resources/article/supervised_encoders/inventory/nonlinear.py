"""Matched linear/MLP readouts of fixed inventory representations."""
from pathlib import Path
import json,time,hashlib,sys
import numpy as np
import torch
from torch import nn
import torch.nn.functional as F
import benchmark as base

R=base.ROOT;O=R/'nonlinear_results';O.mkdir(exist_ok=True)
torch.set_num_threads(8);torch.backends.cuda.matmul.allow_tf32=False
raw={s:base.inputs(s) for s in ['train','validation','test']}
ys={s:base.targets(d) for s,d in raw.items()}
proto=json.loads((R/'results/protocol.json').read_text());mu=np.array(proto['normalization_mean'],np.float32);sd=np.array(proto['normalization_sd'],np.float32)
data={}
for s,d in raw.items():
 d['selectors']=base.selectors(d['ids'],d['sf'])
 data[s]={k:torch.as_tensor(d[k],device='cuda') for k in ['ids','true','sf','selectors','frozen']}
 data[s]['y']=torch.as_tensor((ys[s][0]-mu)/sd,device='cuda');data[s]['mask']=torch.as_tensor(ys[s][1],device='cuda')
del raw
reg=torch.ones(len(base.TASKS),device='cuda',dtype=torch.bool);reg[base.BINARY]=False
protocol=dict(source='frozen representations; encoder never updated',sources=['rl_policy','supervised_encoder'],heads=['linear','mlp128_relu'],fit_seeds=[1,2,3],epochs=150,learning_rates=[.0003,.001],batch_size=1024,early_stopping='after 60 epochs, 30 epochs without validation improvement of 0.0001',data=proto['data'],tasks=base.TASKS)
(O/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')

def loss_fn(p,d,b):
 y=d['y'][b];m=d['mask'][b];l=(p-y).square();l[:,~reg]=F.binary_cross_entropy_with_logits(p[:,~reg],y[:,~reg],reduction='none')
 return ((l*m).sum(0)/m.sum(0).clamp_min(1)).mean()
@torch.no_grad()
def eval_head(head,z,split):
 ps=[];loss=0;d=data[split]
 for start in range(0,len(z),2048):
  b=torch.arange(start,min(start+2048,len(z)),device='cuda');p=head(z[b]);ps.append(p.cpu().numpy());loss+=loss_fn(p,d,b).item()*len(b)
 return loss/len(z),np.concatenate(ps)

for source in ['supervised_encoder','rl_policy']:
 for pool in ['max','sum','both']:
  for passed in [False,True]:
   for seed in [1,2,3]:
    z={};encoder_path=None
    if source=='supervised_encoder':
     encoder_path=R/'results'/f'supervised_{pool}_pass{int(passed)}_s{seed}.pt'
     model=base.Predictor('supervised',pool,passed).to('cuda');model.load_state_dict(torch.load(encoder_path,map_location='cuda',weights_only=True));model.eval();model.requires_grad_(False)
     with torch.no_grad():
      for split,d in data.items():
       parts=[]
       for start in range(0,len(d['ids']),2048):
        b=torch.arange(start,min(start+2048,len(d['ids'])),device='cuda');parts.append(model.encoder(d,b))
       z[split]=torch.cat(parts)
     del model
    else:
     for split,d in data.items():
      v=d['frozen'];parts=[v[:,:128]] if pool=='both' else [v[:,:64] if pool=='sum' else v[:,64:128]]
      if passed:parts.append(v[:,128:])
      z[split]=torch.cat(parts,1)
    mean=z['train'].mean(0);std=z['train'].std(0);supported=std>1e-6
    z={s:((v-mean)/std.clamp_min(1e-4))*supported for s,v in z.items()}
    for kind in ['linear','mlp128_relu']:
     name=f'{source}_{pool}_pass{int(passed)}_s{seed}_{kind}';out=O/(name+'.json')
     if out.exists():continue
     t=time.time();best=None;trials=[]
     for lr in [.0003,.001]:
      torch.manual_seed(seed)
      head=nn.Linear(z['train'].shape[1],len(base.TASKS)) if kind=='linear' else nn.Sequential(nn.Linear(z['train'].shape[1],128),nn.ReLU(),nn.Linear(128,len(base.TASKS)))
      final=head if kind=='linear' else head[-1];nn.init.zeros_(final.weight);nn.init.zeros_(final.bias);head=head.cuda()
      opt=torch.optim.Adam(head.parameters(),lr=lr);schedule=torch.optim.lr_scheduler.ReduceLROnPlateau(opt,factor=.5,patience=8,threshold=1e-3,min_lr=1e-5)
      bestloss=float('inf');state=None;stale=0;curve=[]
      for ep in range(150):
       order=torch.randperm(len(z['train']),device='cuda');tl=0
       for start in range(0,len(order),1024):
        b=order[start:start+1024];opt.zero_grad(set_to_none=True);loss=loss_fn(head(z['train'][b]),data['train'],b);assert torch.isfinite(loss)
        loss.backward();opt.step();tl+=loss.item()*len(b)
       vl,_=eval_head(head,z['validation'],'validation');curve.append(dict(epoch=ep+1,train_loss=tl/len(order),val_loss=vl));stale=0 if vl<bestloss-1e-4 else stale+1
       if vl<bestloss:bestloss=vl;state={k:v.detach().cpu().clone() for k,v in head.state_dict().items()}
       schedule.step(vl)
       if ep>=59 and stale>=30:break
      trials.append(dict(lr=lr,best_validation_loss=bestloss,curve=curve))
      if best is None or bestloss<best['loss']:best=dict(loss=bestloss,lr=lr,state=state)
     head.load_state_dict(best['state']);_,pred=eval_head(head,z['test'],'test')
     rec=dict(name=name,source=source,pool=pool,passthrough=passed,seed=seed,head=kind,selected_lr=best['lr'],validation_loss=best['loss'],seconds=time.time()-t,parameters=sum(p.numel() for p in head.parameters()),excluded_constant_coordinates=int((~supported).sum()),tasks=base.metrics(*ys['test'],pred*sd+mu),trials=trials)
     if encoder_path:rec['encoder_sha256']=hashlib.sha256(encoder_path.read_bytes()).hexdigest()
     out.write_text(json.dumps(rec,indent=2)+'\n');torch.save(best['state'],O/(name+'.pt'));print('DONE',name,round(time.time()-t,1),flush=True)
print('NONLINEAR_DONE',flush=True)
