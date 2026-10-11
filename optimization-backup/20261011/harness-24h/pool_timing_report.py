# Per-buffer rollout anatomy from POOL_TIMING + ROLLOUT_DETAIL + BATCH_PERF lines: python3 pool_timing_report.py <run.log> [epoch_min]
import re, sys, collections
log=open(sys.argv[1]).read().splitlines(); emin=int(sys.argv[2]) if len(sys.argv)>2 else 64
def rows(tag): return [{k:float(v) for k,v in re.findall(r'(\w+)=([-\d.]+)',ln)} for ln in log if ln.startswith(tag)]
bp={int(r['epoch']):r for r in rows('BATCH_PERF')}
pt=collections.defaultdict(list); rd=collections.defaultdict(list)
for r in rows('POOL_TIMING'):
    if r['epoch']>=emin and r['epoch'] in bp and bp[r['epoch']]['rollout_tail']>=0: pt[int(r['buffer'])].append(r)
for r in rows('ROLLOUT_DETAIL'):
    if r['epoch']>=emin: rd[int(r['buffer'])].append(r)
eps=sorted(e for e in bp if e>=emin and e<max(bp)); 
if not eps: sys.exit('no epochs >= %d'%emin)
batch=sum(bp[e]['seconds'] for e in eps)/len(eps)*1000
print('epochs %d..%d  mean batch %.1f ms  rollout_tail %.1f ms  ppo_tail %.1f ms'%(eps[0],eps[-1],batch,
      sum(bp[e]['rollout_tail'] for e in eps)/len(eps)*1000, sum(bp[e]['ppo_tail'] for e in eps)/len(eps)*1000))
print('%-4s %8s %8s %8s %8s | %8s %8s %8s %8s %8s'%('buf','claim','tail','drain','claimcpu','complete','model','env','copy','steps'))
tot=collections.Counter()
for b in sorted(set(pt)|set(rd)):
    p=pt.get(b,[]); d=rd.get(b,[]); n=max(len(p),1); m=max(len(d),1)
    c=sum(x['claim_wall_ms'] for x in p)/n; t=sum(x['tail_wall_ms'] for x in p)/n; dr=sum(x['drain_wall_ms'] for x in p)/n; cc=sum(x['claim_cpu_ms'] for x in p)/n
    comp=sum(x['complete_ms'] for x in d)/m; mo=sum(x['model_ms'] for x in d)/m; en=sum(x['env_ms'] for x in d)/m; co=sum(x['copy_ms'] for x in d)/m
    st=sum(x['samples'] for x in p)/n
    print('%-4d %8.1f %8.1f %8.1f %8.1f | %8.1f %8.1f %8.1f %8.1f %8.0f'%(b,c,t,dr,cc,comp,mo,en,co,st))
    tot.update(claim=c,tail=t,drain=dr,model=mo,env=en,copy=co,comp=comp)
nb=len(set(pt)|set(rd))
print('sum over buffers (ms per batch): claim %.0f tail %.0f drain %.0f | model %.0f env %.0f copy %.0f ; mean complete %.0f'%(tot['claim'],tot['tail'],tot['drain'],tot['model'],tot['env'],tot['copy'],tot['comp']/max(nb,1)))
print('submitter busy share of env wall: %.1f%%  tail share: %.1f%%'%(100*tot['claim']/max(tot['env'],1e-9),100*tot['tail']/max(tot['env'],1e-9)))
