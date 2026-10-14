import re,sys,collections
# Aggregate perf-annotate --stdio output by source line (the most recent source text before each instruction).
path=sys.argv[1]; top=int(sys.argv[2]) if len(sys.argv)>2 else 25
sections=re.split(r'^ Percent \|\tSource code & Disassembly of (\S+) for (\S+) \((\d+) samples.*$',open(path,errors='replace').read(),flags=re.M)
# re.split with groups yields [pre, dso, event, samples, body, dso, event, samples, body, ...]
for i in range(1,len(sections),4):
    dso,event,samples,body=sections[i],sections[i+1],sections[i+2],sections[i+3]
    agg=collections.Counter(); cur='<prologue>'; cur_file=''
    for ln in body.splitlines():
        m=re.match(r'^\s*([0-9.]+)\s*:\s+[0-9a-f]+:\s+(.*)$',ln)
        if m: agg[cur]+=float(m.group(1)); continue
        m2=re.match(r'^\s*:\s+(\d+)\s+(.*)$',ln)   # source line: "         :   1234    code"
        if m2: cur=f'{m2.group(1)}: {m2.group(2).strip()[:110]}'; continue
        m3=re.match(r'^\s*:\s*(\S+\.(c|h|cc)):?$',ln)
        if m3: cur_file=m3.group(1)
    print(f'== {event} ({samples} samples) {dso}  total={sum(agg.values()):.1f}%')
    for k,v in agg.most_common(top): print(f'{v:6.2f}  {k}')
