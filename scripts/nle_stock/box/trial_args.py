# print --section.key=value args reproducing a sweep trial's config (drops metrics/sweep/run bookkeeping)
import sys,configparser
c=configparser.ConfigParser(inline_comment_prefixes=("#",";"),strict=False,interpolation=None); c.read(sys.argv[1])
skip_keys={("base","run_id"),("base","result_fd"),("base","gpu_offset"),("base","seed")}
out=[]
for sec in c.sections():
    if sec=="metrics" or sec.startswith("sweep"): continue
    for k,v in c.items(sec):
        if (sec,k) in skip_keys: continue
        v=v.strip()
        if not v or " " in v: continue
        out.append(f"--{sec}.{k}={v}")
print(" ".join(out))
