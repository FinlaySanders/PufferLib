from pathlib import Path
import json,re,hashlib,time,os,copy
import numpy as np
import torch
from torch import nn
from sklearn.metrics import roc_auc_score
from collections import Counter
ROOT=Path('/puffertank/experiments/message-frozen-20260914');ROOT.mkdir(exist_ok=True)
torch.set_num_threads(4)
source=Path('/tmp/msg_s701.bin')
raw=np.fromfile(source,dtype=np.uint8).reshape(-1,4312)[:,4184:]
messages=sorted(set(bytes(t).split(b'\0',1)[0].lower().decode('latin1') for t in raw)-{''})
n=len(messages);perm=np.random.default_rng(1409).permutation(n)
splits=[perm[:int(n*.8)],perm[int(n*.8):int(n*.9)],perm[int(n*.9):]]
patterns=[('you_kill',r'you (kill|destroy)'),('you_hit',r'you (hit|smite|bash)|your .* hits'),('enemy_hits',r'(hits!|hits you|bites!|bites you|touches you|stings)'),('enemy_miss',r'(misses|just misses|swings wildly)'),('item_found',r'you (see here|find|pick up)|^[a-z] - '),('hunger',r'(hungry|weak from|fainting|starving)'),('feel_message',r'you feel'),('door_stairs',r'(door|the stairs|staircase)'),('shop',r'(costs|zorkmid|for sale|welcome to|pay)'),('prayer',r'(pray|voice|pleased)'),('experience',r'(welcome to experience|feel more confident)'),('status',r'(poison|sick|confus|stun|blind|paraly)')]
y=np.array([[bool(re.search(p,m)) for _,p in patterns] for m in messages],dtype=np.float32)
chars=np.zeros((n,128),dtype=np.int64)
for i,m in enumerate(messages):chars[i,:len(m)]=list(m.encode('latin1'))
tri=(chars[:,:-2]<<16)|(chars[:,1:-1]<<8)|chars[:,2:]
valid=(chars[:,:-2]>0)&(chars[:,1:-1]>0)&(chars[:,2:]>0)
hashed=(tri*2654435761)&0xffffffff
species=[]
for name,pat in [('killed_species',r'you kill the (?:poor |invisible )?([a-z][a-z -]+?)[!.]'),('attacker_species',r'the ([a-z][a-z -]+?) (?:bites|hits|stings|touches|kicks|butts)')]:
 labels=[(q.group(1).strip() if (q:=re.search(pat,m)) else None) for m in messages]
 counts=Counter(labels[i] for i in splits[0] if labels[i]);classes=[k for k,c in counts.most_common(14) if c>=10]
 if len(classes)>=2:species.append((name,classes,np.array([classes.index(l) if l in classes else -1 for l in labels])))
protocol=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),frames=len(raw),unique_nonempty=n,split='80/10/10 distinct lowercased message strings, uniformly weighted; no episode IDs available',seed=1409,patterns=patterns,species=[dict(name=a,classes=b) for a,b,_ in species],buckets=[256,1024,4096],widths=[32,128,256],fit_seeds=[1,2,3],learning_rates=[.001,.003,.01],epochs=200,batch=256,selection='validation equal-task loss, early stop patience 25 after epoch 60; test only chosen LR/checkpoint',normalization='sum / sqrt(trigram_count+1)',cnn='byte embedding16; Conv1d(16,64,k5,pad2), ReLU; Conv1d(64,D,k5,pad2), ReLU; masked global max',note='frozen random encoders; train-only standardized features; linear heads trained; not a zero-training policy test')
protocol['coverage']={name:[int(y[s,j].sum()) for s in splits] for j,(name,_) in enumerate(patterns)}
protocol['species_coverage']={name:[int((v[s]>=0).sum()) for s in splits] for name,_,v in species}
(ROOT/'protocol.json').write_text(json.dumps(protocol,indent=2))
(ROOT/'splits.json').write_text(json.dumps({name:[messages[i] for i in s] for name,s in zip(['train','validation','test'],splits)}))
print('DATA',n,protocol['coverage'],protocol['species_coverage'],flush=True)
X=torch.tensor(chars,device='cuda');Y=torch.tensor(y,device='cuda');S=[torch.tensor(s,device='cuda') for s in splits];SY=[torch.tensor(v,device='cuda') for _,_,v in species]
IDS={v:torch.tensor(np.where(valid,hashed>>(32-int(np.log2(v))),v),device='cuda') for v in [256,1024,4096]}
class Model(nn.Module):
 def __init__(self,kind,v,d):
  super().__init__();self.kind=kind;self.v=v
  if kind=='trigram':self.emb=nn.Embedding(v+1,d,padding_idx=v)
  else:self.emb=nn.Embedding(256,16,padding_idx=0);self.conv=nn.Sequential(nn.Conv1d(16,64,5,padding=2),nn.ReLU(),nn.Conv1d(64,d,5,padding=2),nn.ReLU())
  self.head=nn.Linear(d,len(patterns));self.spec=nn.ModuleList([nn.Linear(d,len(c)) for _,c,_ in species])
 def encode(self,b):
  if self.kind=='trigram':
   ids=IDS[self.v][b];z=self.emb(ids).sum(1)/torch.sqrt((ids!=self.v).sum(1,keepdim=True)+1.)
  else:
   ch=X[b];z=self.conv(self.emb(ch).transpose(1,2)).masked_fill((ch==0)[:,None,:],-1e9).amax(-1)
  return z
 def forward(self,b):
  z=self.features[b] if hasattr(self,'features') else self.encode(b)
  return self.head(z),[h(z) for h in self.spec]
def loss(pred,b):
 p,sp=pred;losses=[nn.functional.binary_cross_entropy_with_logits(p,Y[b])]
 for q,target in zip(sp,SY):
  mask=target[b]>=0
  if mask.any():losses.append(nn.functional.cross_entropy(q[mask],target[b][mask]))
 return torch.stack(losses).mean()
def evaluate(net,idx,metrics=False):
 net.eval()
 with torch.no_grad():
  out=[net(b) for b in idx.split(512)];pred=(torch.cat([a for a,_ in out]),[torch.cat([b[j] for _,b in out]) for j in range(len(species))]);value=float(loss(pred,idx))
  if not metrics:return value
  p=pred[0].cpu().numpy();yy=Y[idx].cpu().numpy();res={}
  for j,(name,_) in enumerate(patterns):res[name]=dict(auc=float(roc_auc_score(yy[:,j],p[:,j])) if len(set(yy[:,j]))==2 else None,positives=int(yy[:,j].sum()),n=len(idx))
  for (name,classes,_),q,target in zip(species,pred[1],SY):
   t=target[idx];mask=t>=0;counts=torch.bincount(t[mask],minlength=len(classes));res[name]=dict(accuracy=float((q.argmax(-1)[mask]==t[mask]).float().mean()) if mask.any() else None,n=int(mask.sum()),majority=float(counts.max()/mask.sum()) if mask.any() else None)
 return value,res
configs=[('trigram',v,d) for v in [256,1024,4096] for d in [32,128,256]]+[('cnn',0,d) for d in [32,128,256]]
for kind,v,d in configs:
 for seed in [1,2,3]:
  name=f'{kind}_v{v}_d{d}_s{seed}';start=time.time();best=None;trials=[]
  for lr in [.001,.003,.01]:
   torch.manual_seed(seed);net=Model(kind,v,d).cuda()
   frozen={k:t.detach().clone() for k,t in net.state_dict().items() if not k.startswith(('head.','spec.'))}
   for k,t in net.named_parameters():t.requires_grad_(k.startswith(('head.','spec.')))
   with torch.no_grad():
    z=torch.cat([net.encode(b) for b in torch.arange(n,device='cuda').split(512)])
    mean=z[S[0]].mean(0);std=z[S[0]].std(0);keep=std>1e-6
    net.features=torch.where(keep,(z-mean)/std.clamp_min(1e-6),0)
    for head in [net.head,*net.spec]:head.weight.zero_();head.bias.zero_()
   opt=torch.optim.Adam([p for p in net.parameters() if p.requires_grad],lr=lr);scheduler=torch.optim.lr_scheduler.ReduceLROnPlateau(opt,patience=8,factor=.5)
   bv=float('inf');state=None;be=0
   for ep in range(200):
    net.train();order=S[0][torch.randperm(len(S[0]),device='cuda')]
    for b in order.split(256):
     opt.zero_grad();l=loss(net(b),b);l.backward();opt.step()
    vl=evaluate(net,S[1]);scheduler.step(vl)
    if vl<bv-1e-5:bv=vl;be=ep;state={k:t.detach().cpu().clone() for k,t in net.state_dict().items()}
    if ep>=60 and ep-be>=25:break
   assert all(torch.equal(net.state_dict()[k],t) for k,t in frozen.items()),'Encoder changed'
   trials.append(dict(lr=lr,validation_loss=bv,best_epoch=be+1,epochs=ep+1))
   if best is None or bv<best[0]:best=(bv,state,lr,be+1)
  net.load_state_dict(best[1]);tl,metrics=evaluate(net,S[2],True)
  result=dict(name=name,kind=kind,buckets=v,width=d,seed=seed,parameters=sum(p.numel() for p in net.parameters()),trainable_parameters=sum(p.numel() for p in net.parameters() if p.requires_grad),encoder_frozen_verified=True,validation_loss=best[0],lr=best[2],best_epoch=best[3],test_loss=tl,tasks=metrics,trials=trials,seconds=time.time()-start)
  (ROOT/(name+'.json')).write_text(json.dumps(result,indent=2));torch.save(best[1],ROOT/(name+'.pt'));print('DONE',name,round(result['seconds'],1),flush=True)
(ROOT/'DONE').write_text('All 36 fits completed\n')
