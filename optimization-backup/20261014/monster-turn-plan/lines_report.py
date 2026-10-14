"""Per-line Ir report from callgrind_annotate --auto=yes output, normalised per eligible move."""
import re, sys
from collections import defaultdict
path, moves, thresh = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
text = open(path, errors='replace').read().splitlines()
# function self table
i = next(k for k, l in enumerate(text) if l.startswith('Ir') and 'file:function' in l)
rows = []
for l in text[i+2:]:
    if not l.strip(): break
    m = re.match(r'\s*([\d,]+)\s+\(\s*([\d.]+)%\)\s+(.*)', l)
    if m: rows.append((int(m.group(1).replace(',', '')), m.group(3)))
print('SELF Ir per eligible move (function, file:function; threshold %.0f/move):' % thresh)
for ir, name in rows:
    if ir / moves >= thresh: print('%8.1f  %s' % (ir / moves, name.split('[')[0].strip()))
# per-line
cur = None; perfile = defaultdict(list)
for l in text:
    m = re.match(r'-- Auto-annotated source: (.*)', l)
    if m: cur = m.group(1).strip(); continue
    if cur is None: continue
    m = re.match(r'\s*([\d,]+)\s+\(\s*[\d.]+%\)\s(.*)', l)
    if m:
        ir = int(m.group(1).replace(',', ''))
        if ir / moves >= thresh: perfile[cur].append((ir / moves, m.group(2).rstrip()))
print('\nLINES >= %.0f Ir per eligible move:' % thresh)
for f, lines in perfile.items():
    tot = sum(x for x, _ in lines)
    print('\n== %s  (listed lines total %.0f/move)' % (f.split('/source/')[-1], tot))
    for ir, src in lines: print('%7.1f | %s' % (ir, src[:150]))
