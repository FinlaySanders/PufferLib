# SPS from a run.log for any agent count: python3 sps_from_log.py <run.log> <agents> [horizon=128] [warm_steps=8388608]
import re,sys
log=open(sys.argv[1]).read(); agents=int(sys.argv[2]); horizon=int(sys.argv[3]) if len(sys.argv)>3 else 128
warm=int(sys.argv[4]) if len(sys.argv)>4 else 32*262144
batch=agents*horizon; clocks={int(e):float(t) for e,t in re.findall(r'BENCH_CLOCK epoch=(\d+) time=([\d.]+)',log)}
k1=warm//batch - 1; k2=max(clocks)-1
if k1 not in clocks or k2<=k1: sys.exit('window %d..%d not in clocks %s'%(k1,k2,sorted(clocks)[:3]))
sps=batch*(k2-k1)/(clocks[k2]-clocks[k1]); print('sps=%.0f batches=%d..%d (%d steps each) window=%.1fs'%(sps,k1,k2,batch,clocks[k2]-clocks[k1]))
