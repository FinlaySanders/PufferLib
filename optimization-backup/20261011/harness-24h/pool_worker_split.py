# aggregate POOL_WORKER lines (epochs >= first print) into per-worker wall split: python3 pool_worker_split.py <run.log> [batch_seconds]
import re,sys,collections
rows=[{k:float(v) for k,v in re.findall(r'(\w+)=([-\d.]+)',ln)} for ln in open(sys.argv[1]) if ln.startswith('POOL_WORKER')]
by=collections.defaultdict(lambda: collections.Counter()); eps=sorted({int(r['epoch']) for r in rows})
for r in rows:
    if int(r['epoch'])==eps[0]: continue  # first print accumulates the whole warm-up
    by[int(r['id'])].update(steps=r['steps'],cpu=r['busy_ms'],wbusy=r['wbusy_ms'],scan=r['scan_ms'],sleep=r['sleep_ms'])
n=len(eps)-1
tot=collections.Counter()
print('%-3s %8s %8s %8s %8s %8s %8s'%('id','us/step','cpu%','wbusy%','scan%','sleep%','offcpu%'))
for i in sorted(by):
    c=by[i]; wall=c['wbusy']+c['scan']+c['sleep']
    print('%-3d %8.1f %8.1f %8.1f %8.1f %8.1f %8.1f'%(i,1000*c['cpu']/max(c['steps'],1),100*c['cpu']/wall,100*c['wbusy']/wall,100*c['scan']/wall,100*c['sleep']/wall,100*(c['wbusy']-c['cpu'])/wall))
    tot.update(c); tot['wall']+=wall
w=tot['wall']; print('ALL: cpu-stepping %.1f%%  wall-in-claim %.1f%%  scan %.1f%%  sleep %.1f%%  off-cpu-while-claiming %.1f%%  (%d epochs, %d workers)'%(100*tot['cpu']/w,100*tot['wbusy']/w,100*tot['scan']/w,100*tot['sleep']/w,100*(tot['wbusy']-tot['cpu'])/w,n,len(by)))
