from pathlib import Path
import sqlite3,json,collections,bisect,statistics
r=Path(__file__).parent;d=r/'profile-strict';c=sqlite3.connect(d/'timeline.sqlite');c.row_factory=sqlite3.Row;names=dict(c.execute('select id,value from StringIds'));ranges=collections.defaultdict(list)
for x in c.execute('select start,end,globalTid,text from NVTX_EVENTS where end is not null order by start'):ranges[x['globalTid']].append((x['start'],x['end'],x['text']))
starts={k:[x[0] for x in v] for k,v in ranges.items()};tags={}
for x in c.execute('select start,end,globalTid,correlationId from CUPTI_ACTIVITY_KIND_RUNTIME'):
 a=ranges[x['globalTid']];i=bisect.bisect_right(starts.get(x['globalTid'],[]),x['start'])-1;tags[x['correlationId']]=a[i][2] if i>=0 and a[i][0]<=x['start']<=a[i][1] else 'unattributed'
intervals=collections.defaultdict(list);sumtime=collections.Counter();top=collections.Counter();graphs=collections.defaultdict(list)
for x in c.execute('select start,end,correlationId,demangledName,gridX,gridY,gridZ,blockX,blockY,blockZ from CUPTI_ACTIVITY_KIND_KERNEL order by start'):
 tag=tags.get(x['correlationId'],'unattributed');a=max(0,x['start']);b=min(10_000_000_000,x['end'])
 if b<=a:continue
 intervals['all'].append((a,b));intervals[tag].append((a,b));sumtime[tag]+=b-a
 if tag=='train_forward_backward':
  graphs[x['correlationId']].append((a,b));top[names[x['demangledName']]]+=b-a

def union(a):
 out=[]
 for s,e in sorted(a):
  if out and s<=out[-1][1]:out[-1][1]=max(e,out[-1][1])
  else:out.append([s,e])
 return sum(e-s for s,e in out)
spans=[dict(corr=k,start=min(s for s,e in v),end=max(e for s,e in v),kernels=len(v)) for k,v in graphs.items()];spans.sort(key=lambda x:x['start']);mx=max(x['kernels'] for x in spans);complete=[x for x in spans if x['kernels']==mx and x['end']<10_000_000_000];mean=statistics.mean((x['end']-x['start'])/1e9 for x in complete)
res=dict(capture_seconds=10,kernel_union_seconds={k:union(v)/1e9 for k,v in intervals.items()},kernel_sums_seconds={k:v/1e9 for k,v in sumtime.items()},ppo_graphs=spans,complete_ppo_graph_count=len(complete),mean_complete_ppo_graph_seconds=mean,ppo_gap_ms=[(b['start']-a['end'])/1e6 for a,b in zip(spans,spans[1:])],top_ppo_kernel_sums_seconds=[dict(name=k,seconds=v/1e9) for k,v in top.most_common(12)])
a=union(intervals['train_forward_backward']);b=union(intervals['fused_rollout']);both=union(intervals['train_forward_backward']+intervals['fused_rollout']);res['inference_training_overlap_seconds']=(a+b-both)/1e9
(d/'summary.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
