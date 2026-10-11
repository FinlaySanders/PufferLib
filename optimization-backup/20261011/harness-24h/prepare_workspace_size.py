from pathlib import Path
import json
r=Path(__file__).resolve().parent;p=r/'source/src/algo.cu';s=p.read_text()
needle='    const size_t ws_bytes = 4 * 1024 * 1024;'
assert s.count(needle)==1
s=s.replace(needle,'''    const int ws_mib = getenv("PUF_CUBLAS_WS_MIB") ? atoi(getenv("PUF_CUBLAS_WS_MIB")) : 4;
    assert(ws_mib >= 4 && ws_mib <= 64);
    const size_t ws_bytes = (size_t)ws_mib << 20;
''')
needle='    cudaMalloc(&cs->workspace, getenv("NH_REC_LT")?nh_rec_workspace_bytes():ws_bytes);'
assert s.count(needle)==1
s=s.replace(needle,'''    size_t allocation_bytes = ws_bytes;
    if (getenv("NH_REC_LT") && nh_rec_workspace_bytes() > allocation_bytes)
        allocation_bytes = nh_rec_workspace_bytes();
    assert(cudaMalloc(&cs->workspace, allocation_bytes) == cudaSuccess);''')
p.write_text(s)
x=[]
for label,mib in [('ws_base_a',4),('ws8',8),('ws16',16),('ws32',32),('ws64',64),('ws_base_b',4)]:
 x.append(dict(kind='time',label=label,binary='completion_workspace_v13',env={'PUF_CUBLAS_WS_MIB':mib},args=['--trials=4']))
(r/'WORKSPACE_SCREEN.json').write_text(json.dumps(x,indent=2))
with (r/'LEDGER.md').open('a') as f:
 f.write('\n20. Explicit cuBLAS workspace capacity: retained handles own4MiB each. The existing test of32MiB applied only to one recurrent-inference Lt GEMM, not fulltraining/parallelMuon. Prepare PUF_CUBLAS_WS_MIB=8/16/32/64 to test heuristic access to larger scratch space across regular GEMMs while retaining stream ownership, operands, compute type and math mode. ExtraVRAM and numerical differences must be reported for anywinner; no implicit allocator or workspace sharing. Cheap saved-batch GPU timing gate first. Not built/tested; no existing binary modified.\n')
print('Prepared explicit workspace capacity screen; fixed default remains4MiB.')
