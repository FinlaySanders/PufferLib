from pathlib import Path
import json, os, re, subprocess, sys, time

r = Path(__file__).resolve().parent
spec = r/'ENV_PAGES_FULL.json'
labels = {v['label'] for v in json.loads(spec.read_text())}
rows=[]
seen=set()
job=subprocess.Popen([sys.executable,str(r/'campaign.py'),str(spec)])
while job.poll() is None:
    try:
        a=json.loads((r/'ACTIVE.json').read_text())
        label=a.get('label')
        if label not in labels or label in seen or time.time()-a.get('started',time.time())<25:
            time.sleep(.2);continue
        pid=a['pid']
        executable=os.readlink('/proc/'+str(pid)+'/exe')
        assert executable==str(r/'binaries/env_pages_v36'),executable
        log=(r/'runs'/label/'run.log').read_text(errors='replace')
        m=re.search(r'ENV_PAGES mode=(\d+) address=(0x[0-9a-f]+) bytes=(\d+) logical=(\d+)',log)
        if not m:
            seen.add(label);continue
        mode=int(m[1]);address=int(m[2],16);size=int(m[3]);logical=int(m[4])
        maps=[];entry=None
        for line in Path('/proc',str(pid),'smaps').read_text().splitlines():
            z=re.match(r'^([0-9a-f]+)-([0-9a-f]+) ',line)
            if z:
                low,high=int(z[1],16),int(z[2],16)
                entry=dict(start=low,end=high,header=line) if low<address+size and high>address else None
                if entry is not None:maps.append(entry)
            elif entry is not None and ':' in line:
                key,val=line.split(':',1);entry[key]=val.strip()
        row=dict(label=label,pid=pid,executable=executable,mode=mode,address=address,bytes=size,logical_bytes=logical,
            seconds_since_start=time.time()-a['started'],mappings=maps,
            anon_huge_kib=sum(int(x.get('AnonHugePages','0 kB').split()[0]) for x in maps),
            rss_kib=sum(int(x.get('Rss','0 kB').split()[0]) for x in maps))
        assert maps and maps[0]['start']==address and maps[-1]['end']==address+size,row
        rows.append(row);seen.add(label)
        (r/'ENV_PAGES_MAPPING.json').write_text(json.dumps(rows,indent=2))
        print('MAPPING',label,'huge KiB',row['anon_huge_kib'],'rss KiB',row['rss_kib'],flush=True)
    except (FileNotFoundError,ProcessLookupError,json.JSONDecodeError):
        pass
    time.sleep(.2)
rc=job.wait()
assert rc==0,rc
assert {x['mode'] for x in rows}=={1,2},rows
subprocess.run([sys.executable,str(r/'full_summary.py'),str(spec.with_suffix('.results.json'))],check=True)
