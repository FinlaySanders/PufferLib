from pathlib import Path
import re
root=Path(__file__).parent
palette=[(120,130,130),(225,90,90),(90,210,135),(230,205,115),(100,155,235),(195,130,225),(70,205,205),(225,232,230)]
rows=[]
for y,line in enumerate((root/'frame.ansi').read_text().splitlines()[:47]):
    color=7;x=0
    for part in re.split(r'(\x1b\[[0-9;]*[A-Za-z])',line):
        if part.startswith('\x1b'):
            if part.endswith('m'):
                for n in (int(v or 0) for v in part[2:-1].split(';')):
                    if n==0: color=7
                    elif 30<=n<=37:color=n-30
            continue
        for ch in part:
            if ch!=' ': rows.append((x,y,ord(ch),*palette[color]))
            x+=1
(root/'frame.h').write_text('static const int cells[][6]={\n'+''.join('{'+','.join(map(str,r))+'},\n' for r in rows)+'};\n')
