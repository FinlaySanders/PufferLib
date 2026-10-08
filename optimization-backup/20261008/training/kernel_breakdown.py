from pathlib import Path
import sqlite3,json,collections,sys,bisect
r=Path(__file__).parent
for label in sys.argv[1:]:
 d=r/label; db=sqlite3.connect(d/'timeline.sqlite');db.row_factory=sqlite3.Row
 hi=db.execute('select max(end) from CUPTI_ACTIVITY_KIND_RUNTIME').fetchone()[0]-250_000_000;lo=250_000_000
 names=dict(db.execute('select id,value from StringIds'))
 ranges=collections.defaultdict(list)
 for x in db.execute('select start,end,globalTid,text,textId from NVTX_EVENTS order by start'):
  name=x['text'] or names.get(x['textId'])
  if name in ('train_forward_backward','rollout.gpu_submit') and x['end'] is not None:ranges[x['globalTid']].append((x['start'],x['end'],name))
 starts={k:[a[0] for a in v] for k,v in ranges.items()};tags={}
 for x in db.execute('select start,globalTid,correlationId from CUPTI_ACTIVITY_KIND_RUNTIME'):
  a=ranges[x['globalTid']];i=bisect.bisect_right(starts.get(x['globalTid'],[]),x['start'])-1
  tags[x['correlationId']]=('ppo' if a[i][2]=='train_forward_backward' else 'inference') if i>=0 and a[i][1]>=x['start'] else 'other'
 sums=collections.Counter();top=collections.defaultdict(collections.Counter);inopt=collections.defaultdict(bool);afterupdate=collections.defaultdict(bool);count=collections.Counter()
 for x in db.execute('select * from CUPTI_ACTIVITY_KIND_KERNEL order by start'):
  tag=tags.get(x['correlationId'],'other');name=names[x['demangledName']];stream=x['streamId'];group=tag
  if tag=='ppo':
   if 'muon_sum_sq_partials' in name:inopt[stream]=True
   group='optimizer' if inopt[stream] or (afterupdate[stream] and name.startswith('void cast<')) else 'forward_loss_backward'
   afterupdate[stream]=False
   if 'muon_weight_update' in name:inopt[stream]=False;afterupdate[stream]=True
  dt=max(0,min(x['end'],hi)-max(x['start'],lo))
  if dt:sums[group]+=dt;top[group][name]+=dt;count[group]+=1
 out={'kernel_seconds':{k:v/1e9 for k,v in sums.items()},'summed_kernel_percent':{k:100*v/sum(sums.values()) for k,v in sums.items()},'kernel_counts':dict(count),'top_by_group':{k:[{'name':n,'seconds':v/1e9} for n,v in c.most_common(10)] for k,c in top.items()},'method':'Optimizer kernels identified in training stream from muon_sum_sq_partials through muon_weight_update and following cast. Includes Newton-Schulz GEMMs. Summed kernel duration is not additive wall time.'}
 (d/'kernel_breakdown.json').write_text(json.dumps(out,indent=2));print(label,json.dumps({k:v for k,v in out.items() if k not in ('top_by_group','method')}),flush=True)
