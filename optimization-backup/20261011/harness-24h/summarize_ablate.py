import json,sys,statistics
from pathlib import Path
root=Path(__file__).resolve().parent
for tag in sys.argv[1:] or ['15m512','5m512','15m2048','5m2048']:
    f=root/f'ablate_{tag}.results.json'
    if not f.exists(): print(f'\n== {tag}: no results yet'); continue
    rs=json.load(open(f)); by={r['label'].split('_',1)[1]:r for r in rs}
    full=[by[k]['sps'] for k in ('full_a','full_b') if k in by and 'sps' in by[k]]
    ref=statistics.mean(full) if full else None
    refp=[p[1] for p in by.get('full_a',{}).get('proofs',[])]
    print(f'\n== {tag}: full mean {ref and round(ref)}  (controls {[round(x) for x in full]}, drift {len(full)==2 and round((full[1]/full[0]-1)*100,2)}%)')
    print(f"{'arm':16}{'sps':>9}{'vs full':>9}{'epoch_ms':>9}{'ppo_est':>8}{'rtail':>7}{'ptail':>7}{'obs match':>11}{'wall':>6}")
    for r in rs:
        arm=r['label'].split('_',1)[1]
        if 'sps' not in r: print(f"{arm:16}{'FAILED rc='+str(r.get('launcher_rc')):>9}"); continue
        d=(r['sps']/ref-1)*100 if ref else 0
        ep=r.get('epochs',[]); meas=[e for e in ep if e.get('epoch',0)>=int([a for a in r['job']['args'] if a.startswith('--start=')][0].split('=')[1])]
        def avg(k):
            v=[e[k] for e in meas if k in e]; return statistics.mean(v)*1000 if v else float('nan')
        pm=sum(1 for a,b in zip(refp,[p[1] for p in r.get('proofs',[])]) if a==b)
        print(f"{arm:16}{round(r['sps']):>9}{d:>+8.2f}%{avg('seconds'):>9.0f}{avg('seconds')-avg('rollout_tail'):>8.0f}{avg('rollout_tail'):>7.0f}{avg('ppo_tail'):>7.0f}{str(pm)+'/'+str(len(refp)):>11}{round(r['wall_seconds']):>6}")
