from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/algo.cu';s=p.read_text()
for name in ('forward','backward'):
 start=s.index('__global__ void mingru_scan_'+name+'_row(');end=s.index('\n}\n',start)+3;fn=s[start:end]
 fn=fn.replace('    __shared__ float sm_term[MINGRU_TILE][MINGRU_TILE];','''#ifdef PUF_SCAN_PACK
    __shared__ unsigned char sm_term[MINGRU_TILE];
#else
    __shared__ float sm_term[MINGRU_TILE][MINGRU_TILE];
#endif''')
 fn=fn.replace('        sm_term[load_t][hx] = term;','''#ifdef PUF_SCAN_PACK
        if(hx==0)sm_term[load_t]=(unsigned char)term;
#else
        sm_term[load_t][hx] = term;
#endif''')
 fn=fn.replace('sm_term[i][hx]','''
#ifdef PUF_SCAN_PACK
                    sm_term[i]
#else
                    sm_term[i][hx]
#endif
''')
 if name=='backward':
  fn=fn.replace('    __shared__ float sm_hid[MINGRU_TILE][MINGRU_TILE];','''#ifdef PUF_SCAN_PACK
    __shared__ unsigned char sm_negative[MINGRU_TILE][MINGRU_TILE];
#else
    __shared__ float sm_hid[MINGRU_TILE][MINGRU_TILE];
#endif''')
  fn=fn.replace('        sm_hid[load_t][hx] = hidden;','''#ifdef PUF_SCAN_PACK
        sm_negative[load_t][hx]=(hidden<0.0f);
#else
        sm_hid[load_t][hx] = hidden;
#endif''')
  fn=fn.replace('sm_hid[i][hx] >= 0.0f','''
#ifdef PUF_SCAN_PACK
                    !sm_negative[i][hx]
#else
                    sm_hid[i][hx] >= 0.0f
#endif
''')
 s=s[:start]+fn+s[end:]
p.write_text(s)
