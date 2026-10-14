import re,sys,subprocess,collections
# perf script (-F event,dso,sym,symoff) -> per-source-line / per-inlined-function attribution for chosen symbols.
# usage: annot_script.py <script.txt> <sym>:<nm binary>:<debug binary>:<top> ...
samples=collections.Counter(); totals=collections.Counter()
for l in open(sys.argv[1],errors='replace'):
    m=re.match(r'\s*(\S+):\s+[0-9a-f]+\s+(\S+)\+0x([0-9a-f]+)\s+\((\S+)\)',l)
    if not m: continue
    ev=m.group(1); totals[ev]+=1; samples[(ev,m.group(2),int(m.group(3),16))]+=1
nmcache={}
def symaddr(binary,sym):
    if binary not in nmcache:
        nmcache[binary]={l.split()[2]:int(l.split()[0],16) for l in subprocess.run(['nm',binary],capture_output=True,text=True).stdout.splitlines() if len(l.split())==3}
    return nmcache[binary][sym]
for spec in sys.argv[2:]:
    sym,nmbin,dbg,top=spec.split(':'); top=int(top); base=symaddr(nmbin,sym)
    for ev in sorted(totals):
        offs={o:c for (e,s,o),c in samples.items() if e==ev and s==sym}
        n=sum(offs.values())
        if not n: continue
        out=subprocess.run(['addr2line','-e',dbg,'-f','-i','-a']+[hex(base+o) for o in sorted(offs)],capture_output=True,text=True).stdout.splitlines()
        info={}; cur=None; frames=[]; pend=None
        for ln in out+['0x']:
            if ln.startswith('0x'):
                if cur is not None: info[cur]=frames
                cur=int(ln,16) if len(ln)>2 else None; frames=[]; pend=None; continue
            if pend is None: pend=ln
            else: frames.append((pend,re.sub(r'^.*/(src|include|ocean/nethack|win/rl)/','',ln.split(' (')[0]))); pend=None
        byline=collections.Counter(); byfunc=collections.Counter()
        for o,c in offs.items():
            fr=info.get(base+o,[('?','?')]); inner=fr[0]; chain=' < '.join(f[0] for f in fr[1:3])
            byline[f'{inner[1]} [{inner[0]}{" < "+chain if chain else ""}]']+=c; byfunc[inner[0]]+=c
        print(f'\n== {sym} / {ev}: {n} samples = {100*n/totals[ev]:.1f}% of event — top source lines (% of this function)')
        for k,v in byline.most_common(top): print(f'{100*v/n:6.2f}  {k}')
        print('-- innermost function:', ', '.join(f'{k} {100*v/n:.1f}' for k,v in byfunc.most_common(12)))
