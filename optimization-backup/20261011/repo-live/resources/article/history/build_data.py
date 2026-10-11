from pathlib import Path
import subprocess, re, json, csv, shutil, statistics, hashlib
from datetime import date
root=Path(__file__).resolve().parent
ev=root/'evidence'
ev.mkdir(exist_ok=True)
points=[]
def add(day,score,stage,label,source,kind,budget):
    points.append(dict(date=day,score=score,stage=stage,label=label,source=source,measurement=kind,training_steps=budget))
notes=Path('/root/.claude/projects/-puffertank-pufferlib/memory/nethack-env-setup.md')
shutil.copy2(notes,ev/notes.name)
for sha in ['1cbd975d','9ceeab2a']:
    (ev/(sha+'.txt')).write_text(subprocess.check_output(['git','show','-s','--format=fuller',sha],text=True))
(ev/'project_start.txt').write_text('User confirmed 3 July 2026 as the first project day. Zero is a chart origin, not a measured evaluation.\n')
add('2026-07-03',0,'monk','Project start','evidence/project_start.txt','User-confirmed start date; illustrative zero baseline',0)
add('2026-07-06',406.9,'monk','Early sweep','evidence/nethack-env-setup.md','Historical campaign note reports score after 259M training; not re-certified',259000000)
add('2026-07-08',1100,'monk','1100 score commit','evidence/9ceeab2a.txt','Approximate score in commit title; aggregation and evaluation protocol unspecified',None)
add('2026-07-14',statistics.mean([3287,3392,3807,3816,3873.6]),'monk','340M seed panel','evidence/nethack-env-setup.md','Average of five historical reported means; completed rerun replaces crashed seed; mostly rounded source values',340000000)
commit=subprocess.check_output(['git','show','-s','--format=fuller','7919bbda'],text=True)
(ev/'7919bbda.txt').write_text(commit)
add('2026-07-31',3604.8,'monk','5c port','evidence/7919bbda.txt','10K-game evaluation mean documented in commit',250000000)
old=Path('/tmp/claude-0/-puffertank-pufferlib/b5a6399e-3c2b-4b96-af84-b52fb0424b97/scratchpad/certify_all.log')
shutil.copy2(old,ev/old.name)
s=old.read_text()
vals={m[0]:float(m[1]) for m in re.findall(r'EVALRESULT (sc1b_s40[1-7]) score ([\d.]+)',s)}
assert len(vals)==7
add('2026-08-04',statistics.mean(vals.values()),'monk','1B seed panel','evidence/certify_all.log','Unweighted average of seven reported evaluation means',1000000000)
for name,day,stage,label in [('new1b_s305','2026-08-13','monk','Monk 1B'),('multi1b_s305','2026-08-14','challenge','Random characters'),('idemb1b_s311','2026-08-15','challenge','Identity embeddings')]:
    p=Path('/tmp')/(name+'.log')
    shutil.copy2(p,ev/p.name)
    s=re.sub(r'\x1b\[[0-9;?]*[A-Za-z]','',p.read_text(errors='replace'))
    vals=re.findall(r'\bscore\s+([\d.]+)',s)
    add(day,float(vals[-1]),stage,label,'evidence/'+p.name,'Final reported panel mean; not a modern burn-in certificate',1000000000)
s=(ev/'drone_long.log').read_text()
for size,day,n in [('1B','2026-09-07',3),('2B','2026-09-08',3),('4B','2026-09-09',4)]:
    vals={}
    for run,val in re.findall(r'(rt_'+size+r'_1122_s20[1-4]) rc=0 score=([\d.]+)',s):
        if int(run[-1])<=n: vals[run]=float(val)
    assert len(vals)==n, vals
    add(day,statistics.mean(vals.values()),'challenge',size+' seed panel','evidence/drone_long.log','Average of '+str(n)+' reported inline final evaluation means',int(size[0])*1000000000)
ledger=json.loads((root.parent/'certificates/results.json').read_text())
runs=[r for r in ledger['runs'] if r['size']=='4B' and r['interface']=='gym' and r['cohort']=='headline']
assert len(runs)==2 and sum(r['stats']['n'] for r in runs)==8064
score=sum(r['stats']['mean']*r['stats']['n'] for r in runs)/8064
add('2026-09-13',score,'python','Fixed 4B Python','../certificates/results.json','Pooled 8,064-game Python certificate',4000000000)
for point in points:
    point['plot'] = point['label'] != '5c port'
    point['exclusion_reason'] = '250M trainer-port validation, not a champion milestone' if not point['plot'] else ''
(root/'milestones.json').write_text(json.dumps(points,indent=2)+'\n')
with (root/'milestones.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=points[0].keys());w.writeheader();w.writerows(points)
start=date.fromisoformat(points[0]['date'])
with (root/'data.h').open('w') as f:
    f.write('static const int N_HISTORY = '+str(len(points))+';\n')
    f.write('static const float HISTORY_DAY[] = {'+','.join(str((date.fromisoformat(p['date'])-start).days) for p in points)+'};\n')
    f.write('static const int HISTORY_PLOT[] = {'+','.join(str(int(p['plot'])) for p in points)+'};\n')
    f.write('static const int HISTORY_STAGE[] = {'+','.join(str({'monk':0,'challenge':1,'python':2}[p['stage']]) for p in points)+'};\n')
    f.write('static const float HISTORY_SCORE[] = {'+','.join(str(p['score']) for p in points)+'};\n')
(root/'evidence_hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ev.iterdir() if p.is_file()},indent=2))
print(json.dumps(points,indent=2))
