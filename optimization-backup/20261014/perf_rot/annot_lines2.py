import re,sys,subprocess,collections
# perf annotate --stdio output -> per-source-line and per-inlined-function aggregation via addr2line on a debug binary.
# usage: annot_lines2.py <annot.txt> <debug binary> <top> [base]   (base = load bias to subtract from annotate addresses; default 0)
path,binary,top=sys.argv[1],sys.argv[2],int(sys.argv[3]); base=int(sys.argv[4],16) if len(sys.argv)>4 else 0
text=open(path,errors='replace').read()
parts=re.split(r'^ Percent \|\tSource code & Disassembly of (\S+) for (\S+) \((\d+) samples.*$',text,flags=re.M)
for i in range(1,len(parts),4):
    dso,event,samples,body=parts[i],parts[i+1],parts[i+2],parts[i+3]
    hits=[]
    for ln in body.splitlines():
        m=re.match(r'^\s*([0-9.]+)\s*:\s+([0-9a-f]+):\s+(.*)$',ln)
        if m and float(m.group(1))>0: hits.append((float(m.group(1)),int(m.group(2),16)-base,m.group(3).strip()))
    addrs=sorted(set(a for _,a,_ in hits))
    out=subprocess.run(['addr2line','-e',binary,'-f','-i','-a']+[hex(a) for a in addrs],capture_output=True,text=True).stdout.splitlines()
    info={}; cur=None; frames=[]
    for ln in out+['0x']:
        if ln.startswith('0x'):
            if cur is not None: info[cur]=frames
            cur=int(ln,16) if len(ln)>2 else None; frames=[]; pend=None; continue
        if pend is None: pend=ln
        else:
            loc=re.sub(r'^.*/(src|include|ocean/nethack|win/rl)/','',ln.split(' (')[0]); frames.append((pend,loc)); pend=None
    byline=collections.Counter(); byfunc=collections.Counter(); byinsn=collections.Counter()
    for pct,a,insn in hits:
        fr=info.get(a,[('?','?')])
        inner=fr[0]; chain=' < '.join(f[0] for f in fr[1:3])
        byline[f'{inner[1]} [{inner[0]}{" < "+chain if chain else ""}]']+=pct
        byfunc[inner[0]]+=pct
        byinsn[insn.split()[0]]+=pct
    print(f'\n== {event} {samples} samples ({dso}) — top lines')
    for k,v in byline.most_common(top): print(f'{v:6.2f}  {k}')
    print('-- by innermost (inlined) function:', ', '.join(f'{k} {v:.1f}' for k,v in byfunc.most_common(14)))
    print('-- by mnemonic:', ', '.join(f'{k} {v:.1f}' for k,v in byinsn.most_common(10)))
