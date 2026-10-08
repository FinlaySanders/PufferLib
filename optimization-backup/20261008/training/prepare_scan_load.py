from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/algo.cu';s=p.read_text()
s=s.replace('#define MINGRU_TILE 32','#define MINGRU_TILE 32\n#ifndef PUF_MINGRU_LOAD_ROWS\n#define PUF_MINGRU_LOAD_ROWS 32\n#endif',1)
for name in ('forward','backward'):
 start=s.index('__global__ void mingru_scan_'+name+'_row(');end=s.index('\n}\n',start)+3;fn=s[start:end]
 i=fn.index('        int t = c * MINGRU_TILE + t_local;');j=fn.index('        __syncthreads();',i)
 load=fn[i:j].replace('t_local','load_t')
 fn=fn[:i]+'        for(int load_t=t_local;load_t<MINGRU_TILE;load_t+=PUF_MINGRU_LOAD_ROWS) {\n'+load+'        }\n'+fn[j:]
 if name=='backward':
  needle='''        if (t_local == 0 && h_ok) {
            for (int i ='''
  repl='''        if (t_local == 0 && h_ok) {
            float z,s,gout,h_tilde,h_prev;
            for (int i ='''
  assert needle in fn;fn=fn.replace(needle,repl,1)
 s=s[:start]+fn+s[end:]
s=s.replace('dim3 block(MINGRU_TILE, MINGRU_TILE);','dim3 block(MINGRU_TILE, PUF_MINGRU_LOAD_ROWS);')
p.write_text(s)
