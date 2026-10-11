from pathlib import Path
import difflib
p=Path(__file__).parent/'source/src/algo.cu'
s=p.read_text(); before=s
for name, end in [('mingru_scan_forward_row','__global__ void mingru_scan_backward_row'),('mingru_scan_backward_row','__global__ void sum_rows_to_precision_kernel')]:
    start=s.index('__global__ void '+name)
    stop=s.index(end,start)
    chunk=s[start:stop]
    chunk='template<int TILE>\n'+chunk.replace('MINGRU_TILE','TILE')
    chunk=chunk.replace('blockIdx.y * TILE + hx','blockIdx.y * 32 + hx').replace('[TILE][TILE]','[TILE][32]')
    s=s[:start]+chunk+s[stop:]
for direction in ['forward','backward']:
    a=s.index('        if ((getenv("PUF_SCAN_ROW")',s.index('Prec mingru_'+('forward_train' if direction=='forward' else 'backward')+'('))
    b=s.index('\n        }',s.index('} else {',a))+len('\n        }')
    # First close is the full if/else block (all inner launches have no braces).
    old=s[a:b]
    tail='scan' if direction=='forward' else 'scan, grad.data, a->grad_next_state.data'
    bit=1 if direction=='forward' else 2
    new=f'''        if ((getenv("PUF_SCAN_ROW") && (atoi(getenv("PUF_SCAN_ROW")) & {bit}))
                || scan.T >= 256 && scan.B * scan.H <= 32768
                || scan.T >= 128 && scan.H <= 32) {{
            int tile=getenv("PUF_SCAN_TILE")?atoi(getenv("PUF_SCAN_TILE")):32;
            dim3 grid(scan.B, (scan.H + 31) / 32);
#define NH_SCAN_LAUNCH(T) mingru_scan_{direction}_row<T><<<grid, dim3(32,T), 0, stream>>>({tail})
            if(tile==4) {{ NH_SCAN_LAUNCH(4); }}
            else if(tile==8) {{ NH_SCAN_LAUNCH(8); }}
            else if(tile==16) {{ NH_SCAN_LAUNCH(16); }}
            else {{ NH_SCAN_LAUNCH(32); }}
#undef NH_SCAN_LAUNCH
        }} else {{
            int block=getenv("PUF_SCAN_BLOCK")?atoi(getenv("PUF_SCAN_BLOCK")):BLOCK_SIZE;
            mingru_scan_{direction}<<<(scan.B * scan.H + block - 1)/block, block, 0, stream>>>({tail});
        }}'''
    s=s[:a]+new+s[b:]
p.write_text(s)
(p.parents[2]/'scan_tiles.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='algo.before_tiles',tofile='algo.tiles')))
