from pathlib import Path
import ctypes, hashlib, json, statistics, subprocess
import torch

assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'], text=True).strip()
torch.cuda.set_device(0)
torch.manual_seed(641)
lib = ctypes.CDLL(str(Path('pool_bwd_micro.so').resolve()))
lib.pool_run.argtypes = [ctypes.c_int]*2 + [ctypes.c_void_p]*6 + [ctypes.c_int,ctypes.c_void_p]
lib.pool_run.restype = None
stream = torch.cuda.Stream()
smokes, timings = [], []
with torch.cuda.stream(stream):
    for branch, n, pad in [(0,55,5976),(1,16,-1),(2,16,-1),(3,8,-1)]:
        for batch in [1,17,512,4096]:
            gc = torch.randn(batch,1698,device='cuda',dtype=torch.bfloat16)
            gid = torch.randint(0,5000,(batch,n),device='cuda').float()
            gid[torch.rand_like(gid)>.7] = pad
            gid[0] = pad
            am = torch.randint(-1,n,(batch,64),device='cuda').float()
            out = torch.randn(batch,n,64,device='cuda',dtype=torch.bfloat16).clamp_min_(0)
            dv = torch.empty_like(out)
            bias = torch.empty(64,device='cuda',dtype=torch.int64)
            def run(mode):
                lib.pool_run(mode,branch,dv.data_ptr(),gc.data_ptr(),am.data_ptr(),gid.data_ptr(),out.data_ptr(),bias.data_ptr(),batch,stream.cuda_stream)
            run(0)
            ref, ref_bias = dv.clone(), bias.clone()
            for mode in [1,2]:
                run(mode)
                neq = (dv.view(torch.int16)!=ref.view(torch.int16)).sum().item()
                bneq = (bias!=ref_bias).sum().item()
                row = dict(branch=branch,batch=batch,mode=mode,elements=dv.numel(),different=neq,bias_different=bneq)
                smokes.append(row)
                assert neq==0 and bneq==0, row
            if batch != 4096:
                continue
            rows=[]
            for mode in [0,1,2,0]:
                graph = torch.cuda.CUDAGraph()
                with torch.cuda.graph(graph, stream=stream):
                    for _ in range(64): run(mode)
                for _ in range(100): graph.replay()
                stream.synchronize()
                trials=[]
                for _ in range(5):
                    a,b=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
                    a.record(stream);graph.replay();b.record(stream);b.synchronize()
                    trials.append(a.elapsed_time(b)*1000/64)
                row=dict(branch=branch,batch=batch,mode=mode,microseconds=statistics.mean(trials),trials=trials)
                rows.append(row); print(json.dumps(row),flush=True)
                del graph
            control=statistics.mean([rows[0]['microseconds'],rows[-1]['microseconds']])
            timings.append(dict(branch=branch,control_us=control,control_drift_percent=100*(rows[-1]['microseconds']/rows[0]['microseconds']-1),rows=rows))
            Path('POOL_BWD_SCREEN.partial.json').write_text(json.dumps(dict(smokes=smokes,timings=timings),indent=2))
result=dict(smokes=smokes,timings=timings,all_exact=True,
    scope='Synthetic BF16 pool routing, ReLU and fixed-point bias gradients. Same bias reduction grid, thread order, and pre-ReLU rounding. All-pad first game and random masks; no actual optimizer proof.',
    hashes={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['pool_bwd_micro.so','pool_bwd_candidate.cuh','pool_bwd_reference_parts.cu','pool_bwd_screen.py']})
Path('POOL_BWD_SCREEN.json').write_text(json.dumps(result,indent=2))
print('COMPLETE',len(smokes),sum(r['elements'] for r in smokes),flush=True)
