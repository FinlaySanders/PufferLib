"""Inventory capacity and frozen-policy probes on the same held-out observations."""
from pathlib import Path
import argparse,json,hashlib,time,copy
import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

ROOT=Path('/puffertank/experiments/inventory-concrete-20260914')
PAD=5976;SLOTS=55;VOCAB=5977
TASKS=['arrow_quantity','best_armor_enchant','wielding_bow']
BINARY=[2]

def inputs(split):
 a=np.memmap(ROOT/(split+'.bin'),dtype=np.float32,mode='r').reshape(-1,3718)
 assert np.isfinite(a).all()
 return dict(ids=np.array(a[:,:55],dtype=np.int64),true=np.array(a[:,55:110],dtype=np.int64),sf=np.array(a[:,110:1430]).reshape(-1,55,24),r=np.array(a[:,1430:2310]).reshape(-1,55,16),frozen=np.array(a[:,2310:2694]),global_rep=np.array(a[:,2694:]))

def targets(d):
 ids,sf=d['ids'],d['sf'];occ=ids!=PAD;obj=ids-1906
 arrows=np.isin(obj,[1,2,3,4,5])&occ
 armor=(sf[:,:,17:].sum(-1)>.5)&occ;known=(sf[:,:,4]>.5)&occ
 enchant=np.rint(sf[:,:,5]*7);quantity=np.rint(sf[:,:,6]*30)
 wield=(sf[:,:,10]>.5)&occ;bow=np.isin(obj,[65,66,67,68])&occ
 y=np.zeros((len(ids),3),np.float32);m=np.ones_like(y)
 y[:,0]=(quantity*arrows).sum(1)
 valid=armor&known;m[:,1]=valid.any(1)
 y[:,1]=np.where(valid,enchant,-999).max(1);y[m[:,1]==0,1]=0
 y[:,2]=(wield&bow).any(1)
 return y,m

def selectors(ids,sf):
 occ=ids!=PAD;worn=(sf[:,:,9]>.5)&occ;wield=(sf[:,:,10]>.5)&occ;quiver=(sf[:,:,12]>.5)&occ
 obj=ids-1906
 masks=[wield,quiver,worn]
 am=worn&(obj>=178)&(obj<=188);ring=worn&(obj>=150)&(obj<=177);eye=worn&(obj>=207)&(obj<=209)
 for mask,rank in [(am,1),(ring,1),(ring,2),(eye,1)]:masks.append(mask&(mask.cumsum(1)==rank))
 return np.stack(masks,1).astype(np.float32)

def passthrough(r,sf,sel):
 payload=torch.cat([r,sf],-1)
 wq=torch.bmm(sel[:,:2],payload).flatten(1)
 worn=torch.bmm(sel[:,2:3],r).squeeze(1)/sel[:,2].sum(1,keepdim=True).clamp_min(1)
 acc=torch.bmm(sel[:,3:],payload).flatten(1)
 return torch.cat([wq,worn,acc],1)

class Encoder(nn.Module):
 def __init__(self,pool,passed):
  super().__init__();self.pool=pool;self.passed=passed
  lut=json.loads((Path(__file__).parent/'glyph_map.json').read_text())
  self.register_buffer('kinds',torch.tensor(lut['kind']));self.register_buffer('subs',torch.tensor(lut['sub']))
  self.kind=nn.Embedding(14,32);self.sub=nn.Embedding(944,32);nn.init.zeros_(self.kind.weight);nn.init.zeros_(self.sub.weight)
  self.emb=nn.Embedding(VOCAB,32);self.glyph=nn.Linear(32,16,bias=False);self.true=nn.Linear(32,16,bias=False);self.state=nn.Linear(24,16)
  self.value=nn.Sequential(nn.Linear(16,64),nn.ReLU(),nn.Linear(64,64),nn.ReLU())
  self.dim=(128 if pool=='both' else 64)+(256 if passed else 0)
 def embed(self,ids):return self.emb(ids)+self.kind(self.kinds[ids])+self.sub(self.subs[ids])
 def forward(self,d,b):
  ids=d['ids'][b];sf=d['sf'][b];occ=(ids!=PAD).unsqueeze(-1)
  r=F.relu(self.glyph(self.embed(ids))+self.true(self.embed(d['true'][b]))*(d['true'][b]!=PAD).unsqueeze(-1)+self.state(sf))*occ
  v=self.value(r)
  sm=(v*occ).sum(1)*.2;mx=v.masked_fill(~occ,-1e9).max(1).values;mx=torch.where(occ.any(1),mx,0)
  parts=[sm,mx] if self.pool=='both' else [sm if self.pool=='sum' else mx]
  if self.passed:parts.append(passthrough(r,sf,d['selectors'][b]))
  return torch.cat(parts,1)

class Predictor(nn.Module):
 def __init__(self,mode,pool,passed):
  super().__init__();self.mode=mode;self.pool=pool;self.passed=passed
  self.encoder=Encoder(pool,passed) if mode=='supervised' else None
  dim=self.encoder.dim if self.encoder else (128 if pool=='both' else 64)+(256 if passed else 0)
  self.head=nn.Linear(dim,len(TASKS))
  if mode=='frozen':nn.init.zeros_(self.head.weight);nn.init.zeros_(self.head.bias)
 def forward(self,d,b):
  if self.encoder:z=self.encoder(d,b)
  else:
   z=d['frozen'][b];parts=[z[:,:128]] if self.pool=='both' else [z[:,:64] if self.pool=='sum' else z[:,64:128]]
   if self.passed:parts.append(z[:,128:])
   z=torch.cat(parts,1)
  return self.head(z)

def auc(y,p):
 n1=int(y.sum());n0=len(y)-n1
 if not n1 or not n0:return None
 order=np.argsort(p,kind='stable');ranks=np.empty(len(p),float);v=p[order]
 starts=np.r_[0,np.flatnonzero(v[1:]!=v[:-1])+1];ends=np.r_[starts[1:],len(v)]
 for a,b in zip(starts,ends):ranks[order[a:b]]=(a+1+b)/2
 return float((ranks[y==1].sum()-n1*(n1+1)/2)/(n1*n0))

def metrics(y,m,p):
 out={}
 for k,name in enumerate(TASKS):
  valid=m[:,k]>.5;a=y[valid,k];pred=p[valid,k]
  val=None
  if len(a)>1:
   if k in BINARY:val=auc(a,pred)
   elif np.var(a)>1e-10:val=float(1-np.mean((a-pred)**2)/np.var(a))
  out[name]=dict(metric='auc' if k in BINARY else 'r2',value=val,n=len(a),positives=int(a.sum()) if k in BINARY else None)
 return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--epochs',type=int,default=30);ap.add_argument('--seeds',type=int,nargs='+',default=[1,2,3]);ap.add_argument('--smoke',action='store_true');args=ap.parse_args()
 torch.set_num_threads(8);torch.set_float32_matmul_precision('highest');dev='cuda';torch.backends.cuda.matmul.allow_tf32=False
 assert (ROOT/'CAPTURE_DONE').exists()
 data={s:inputs(s) for s in ['train','validation','test']};raw_targets={s:targets(d) for s,d in data.items()}
 mu=np.zeros(len(TASKS),np.float32);sd=np.ones_like(mu)
 for k in range(len(TASKS)):
  if k not in BINARY:
   a=raw_targets['train'][0][:,k][raw_targets['train'][1][:,k]>.5];mu[k]=a.mean();sd[k]=max(a.std(),1e-4)
 coverage={s:{name:dict(n=int(m[:,k].sum()),positive=int(y[m[:,k]>.5,k].sum()) if k in BINARY else None,unique=int(len(np.unique(y[m[:,k]>.5,k])))) for k,name in enumerate(TASKS)} for s,(y,m) in raw_targets.items()}
 (ROOT/'target_coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
 for split,d in data.items():
  d['selectors']=selectors(d['ids'],d['sf'])
  # Verify the passthrough replica against the actual CUDA branch on real data.
  rp=torch.from_numpy(d['r'][:512]);sf=torch.from_numpy(d['sf'][:512]);sel=torch.from_numpy(d['selectors'][:512])
  predicted=passthrough(rp,sf,sel).numpy();actual=d['frozen'][:512,128:]
  assert np.allclose(predicted,actual,rtol=.035,atol=.035),(split,float(abs(predicted-actual).max()))
  del d['r'];del d['global_rep']
  y,m=raw_targets[split];d['y']=(y-mu)/sd;d['mask']=m
  for key in d:d[key]=torch.as_tensor(d[key],device=dev)
 # Standardize frozen probe coordinates using train data only. Different
 # feature amplitudes should not make a linear probe artificially weak.
 zm=data['train']['frozen'].mean(0);raw_std=data['train']['frozen'].std(0);zs=raw_std.clamp_min(1e-4)
 # A constant training coordinate has no identifiable coefficient. Fix that
 # null-space coefficient to zero, including when it varies on held-out games.
 supported=raw_std>1e-6
 for d in data.values():d['frozen']=((d['frozen']-zm)/zs)*supported
 (ROOT/'probe_constant_coordinates.json').write_text(json.dumps(dict(excluded=torch.where(~supported)[0].cpu().tolist(),reason='constant on training observations; coefficient unidentifiable'),indent=2))
 reg=torch.ones(len(TASKS),device=dev,dtype=torch.bool);reg[BINARY]=False
 def loss_fn(pred,d,b):
  target=d['y'][b];mask=d['mask'][b];loss=(pred-target).square()
  loss[:,~reg]=F.binary_cross_entropy_with_logits(pred[:,~reg],target[:,~reg],reduction='none')
  return ((loss*mask).sum(0)/mask.sum(0).clamp_min(1)).mean()
 @torch.no_grad()
 def evaluate(model,split):
  d=data[split];ps=[];total=0
  for start in range(0,len(d['ids']),2048):
   b=torch.arange(start,min(start+2048,len(d['ids'])),device=dev);p=model(d,b);ps.append(p.cpu().numpy());total+=loss_fn(p,d,b).item()*len(b)
  return total/len(d['ids']),np.concatenate(ps)
 modes=['supervised','frozen'];pools=['sum','max','both'];passes=[False,True]
 if args.smoke:modes=['supervised','frozen'];pools=['both'];passes=[True];args.seeds=[0];args.epochs=1
 resdir=ROOT/('smoke_results' if args.smoke else 'results');resdir.mkdir(exist_ok=True)
 (resdir/'protocol.json').write_text(json.dumps(dict(epochs=args.epochs,seeds=args.seeds,learning_rates=[.0003,.001],batch_size=1024,tasks=TASKS,binary=BINARY,normalization_mean=mu.tolist(),normalization_sd=sd.tolist(),torch=torch.__version__,data=json.loads((ROOT/'capture_manifest.json').read_text())),indent=2)+'\n')
 for mode in modes:
  for pool in pools:
   for passed in passes:
    for seed in args.seeds:
     name=f'{mode}_{pool}_pass{int(passed)}_s{seed}';out=resdir/(name+'.json')
     if out.exists():continue
     t=time.time();best=None;trials=[]
     for lr in [.0003,.001]:
      torch.manual_seed(seed);np.random.seed(seed)
      model=Predictor(mode,pool,passed).to(dev);opt=torch.optim.Adam(model.parameters(),lr=lr);bestloss=float('inf');state=None;curve=[];stale=0
      scheduler=torch.optim.lr_scheduler.ReduceLROnPlateau(opt,factor=.5,patience=8,threshold=1e-3,min_lr=1e-5)
      for epoch in range(args.epochs):
       model.train();order=torch.randperm(len(data['train']['ids']),device=dev);ls=0
       for start in range(0,len(order),1024):
        b=order[start:start+1024];opt.zero_grad(set_to_none=True);p=model(data['train'],b);loss=loss_fn(p,data['train'],b);assert torch.isfinite(loss)
        loss.backward();opt.step();ls+=loss.item()*len(b)
       model.eval();vl,_=evaluate(model,'validation');curve.append(dict(epoch=epoch+1,train_loss=ls/len(order),val_loss=vl))
       stale=0 if vl<bestloss-1e-4 else stale+1
       if vl<bestloss:bestloss=vl;state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
       scheduler.step(vl)
       if epoch>=59 and stale>=30:break
      trials.append(dict(lr=lr,best_validation_loss=bestloss,curve=curve))
      if best is None or bestloss<best['loss']:best=dict(loss=bestloss,state=state,lr=lr)
     model.load_state_dict(best['state']);model.eval();_,p=evaluate(model,'test');p=p*sd+mu
     result=dict(name=name,mode=mode,pool=pool,passthrough=passed,seed=seed,selected_lr=best['lr'],validation_loss=best['loss'],parameters=sum(x.numel() for x in model.parameters()),seconds=time.time()-t,tasks=metrics(*raw_targets['test'],p),trials=trials)
     out.write_text(json.dumps(result,indent=2)+'\n');torch.save(best['state'],resdir/(name+'.pt'));print('DONE',name,round(time.time()-t,1),flush=True)
 print('BENCHMARK_DONE',flush=True)
