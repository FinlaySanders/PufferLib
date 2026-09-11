import re, sys, collections
S='/puffertank/pufferlib/scripts/nle_stock'
err = sys.argv[1]; keys = sys.argv[2] if len(sys.argv) > 2 else f'{S}/keys_l2w'
e = open(err, errors='ignore').read()
OBJ_OFF, CMAP_OFF, PET_OFF, INVIS = 1906, 2359, 381, 762
def cls(g):
    if g < PET_OFF: return 'mon'
    if g < INVIS: return 'pet'
    if g < OBJ_OFF: return 'inv/det/body/ridden'
    if g < CMAP_OFF: return 'obj'
    return 'cmap'
cnt = collections.Counter(); rows = []
for m in re.finditer(r'^replay ([0-9a-f]+): first divergence at key (\d+) turn (\d+): groups ([^\n]*)', e, re.M):
    seed, k, turn, groups = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4).split()
    tag = []
    t = open(f'{keys}/{seed}.keys', errors='ignore').read()
    if 'glyphs' in groups:
        fork = {}
        def apply(line):
            for c in line.split():
                i, g = c.split(':'); fork[int(i)] = int(g)
        m1 = re.search(r'^# M1 (.*)$', t, re.M)
        if m1: apply(m1.group(1))
        for d in re.finditer(r'^# D(\d+) (.*)$', t, re.M):
            if int(d.group(1)) <= k: apply(d.group(2))
        ms = re.search(rf'^replay {seed}: Mstock{k} (.*)$', e, re.M)
        stock = {}
        if ms:
            for c in ms.group(1).split():
                i, g = c.split(':'); stock[int(i)] = int(g)
        d = [(i, fork.get(i, 2359), stock.get(i, 2359)) for i in sorted(set(fork) | set(stock)) if fork.get(i, 2359) != stock.get(i, 2359)]
        kinds = collections.Counter(f'{cls(a)}->{cls(b)}' for i, a, b in d)
        tag.append(f'cells={len(d)} ' + ' '.join(f'{x}:{n}' for x, n in kinds.items()))
        ex = ' '.join(f'{i}:{a}/{b}' for i, a, b in d[:4])
    else:
        ex = ''
    bf = re.search(rf'^# B{k} ([^\n]*)', t, re.M); bs = re.search(rf'^replay {seed}: Bstock{k} ([^\n]*)', e, re.M)
    bl = ''
    if bf and bs:
        f = bf.group(1).split(' | '); s = bs.group(1).split(' | ')
        fv = f[0].split(); sv = s[0].split()
        diffs = [(j, fv[j], sv[j]) for j in range(min(len(fv), len(sv))) if fv[j] != sv[j]]
        bl = 'bl:' + ','.join(f'{j}={a}/{b}' for j, a, b in diffs[:6])
        if len(f) > 1 and len(s) > 1 and f[1] != s[1]: bl += f' I:{f[1]}/{s[1]}'
        if len(f) > 2 and len(s) > 2 and f[2].strip() != s[2].strip(): bl += f' msg:"{f[2].strip()[:50]}"/"{s[2].strip()[:50]}"'
    rows.append((turn, seed, k, ' '.join(groups), ' '.join(tag), bl, ex))
    for g in groups: cnt[g] += 1
rows.sort()
for r in rows: print(f'T{r[0]:>5} {r[1][:8]} k{r[2]:<6} [{r[3]}] {r[4]} {r[5]} {r[6]}')
print('groups', dict(cnt), 'n', len(rows))
