# Per-line self cost from a callgrind dump (positions=line, subposition compression, calls= inclusive lines skipped).
import sys, re, collections
path=sys.argv[1]; want=sys.argv[2] if len(sys.argv)>2 else 'Ir'
events=None; names={}; cur_file=None; fn_file=None; last=0; skip=False
cost=collections.Counter()
def name(tok):
    m=re.match(r'\((\d+)\)\s*(.*)',tok)
    if not m: return tok
    i,n=m.group(1),m.group(2).strip()
    if n: names[i]=n
    return names.get(i,i)
for line in open(path,errors='replace'):
    if line.startswith('events:'): events=line.split()[1:]; idx=events.index(want); continue
    if line.startswith(('fl=','fi=','fe=')): cur_file=name(line[3:].strip()); continue
    if line.startswith('fn='): fn_file=cur_file; continue
    if line.startswith(('cfn=','cfl=','cfi=','cob=','ob=')): continue
    if line.startswith('calls='): skip=True; continue
    if not line or not (line[0].isdigit() or line[0] in '+-*'): continue
    parts=line.split(); pos=parts[0]
    if pos=='*': ln=last
    elif pos[0] in '+-': ln=last+int(pos)
    else: ln=int(pos)
    last=ln
    if skip: skip=False; continue
    if len(parts)>1+idx: cost[(cur_file,ln)]+=int(parts[1+idx])
tot=sum(cost.values()); print(f"{want} total {tot:,} over {len(cost)} lines")
import pickle; pickle.dump(dict(cost),open(path+'.'+want+'.pkl','wb'))
