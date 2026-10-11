from pathlib import Path
import ctypes,json,time,statistics,hashlib,subprocess,sys
import torch,triton
from entity_train_fused import entity_train_fused
def main():
    assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    torch.cuda.set_device(0);torch.manual_seed(345)
    name=sys.argv[1]
    n,off,pad,eps={"inventory":(55,1010,5976,.2),"monster":(16,1394,-1,.25),"item":(16,1538,-1,.25),"spell":(8,838,-1,.25)}[name]
    batch=4096
    x=torch.rand(batch,n,16,device='cuda',dtype=torch.bfloat16)
    w1=(torch.randn(64,16,device='cuda')*.1).to(torch.bfloat16)
    w2=(torch.randn(64,64,device='cuda')*.1).to(torch.bfloat16)
    b1=(torch.randn(64,device='cuda')*.1).to(torch.bfloat16)
    b2=(torch.randn(64,device='cuda')*.1).to(torch.bfloat16)
    gid=torch.randint(0,5976,(batch,n),device='cuda').float()
    gid[torch.rand_like(gid)>.5]=pad
    gid[0]=pad
    h=torch.empty(batch,n,64,device='cuda',dtype=torch.bfloat16);v=torch.empty_like(h)
    c=torch.full((batch,1698),-64,device='cuda',dtype=torch.bfloat16)
    amax=torch.empty(batch,64,device='cuda')
    lib=ctypes.CDLL(str(Path('entity_train_reference.so').resolve()))
    lib.inv_init.argtypes=[ctypes.c_void_p]*3+[ctypes.c_int]*4+[ctypes.c_float];lib.inv_init.restype=None
    lib.inv_run.argtypes=[ctypes.c_void_p]*8+[ctypes.c_int];lib.inv_run.restype=None
    stream=torch.cuda.Stream();torch.cuda.synchronize();rows=[]
    with torch.cuda.stream(stream):
        lib.inv_init(stream.cuda_stream,b1.data_ptr(),b2.data_ptr(),batch,n,off,pad,eps)
        baseline=lambda:lib.inv_run(x.data_ptr(),w1.data_ptr(),w2.data_ptr(),h.data_ptr(),v.data_ptr(),gid.data_ptr(),c.data_ptr(),amax.data_ptr(),batch)
        baseline();stream.synchronize()
        ref=c.clone();ref_amax=amax.clone();ref_h=h.clone();ref_v=v.clone();stream.synchronize()
        for index,config in enumerate([None,(4,1),(4,2),(8,1),None]):
            t=time.monotonic()
            if config:
                warps,stages=config
                fn=lambda:entity_train_fused[(batch,)](x,w1,b1,w2,b2,gid,c,amax,h,v,n,max(16,triton.next_power_of_2(n)),pad,off,eps,num_warps=warps,num_stages=stages)
            else:fn=baseline
            fn();stream.synchronize()
            prep=time.monotonic()-t
            ca=c[:,off:off+128].float();ra=ref[:,off:off+128].float();diff=ca-ra
            proof=dict(relative_l2=(diff.norm()/ra.norm()).item(),max_abs=diff.abs().max().item(),argmax_different=(amax!=ref_amax).sum().item(),finite=bool(torch.isfinite(c).all()),untouched=bool((c[:,:off]==-64).all() and (c[:,off+128:]==-64).all()))
            proof['h_relative_l2']=((h.float()-ref_h.float()).norm()/ref_h.float().norm()).item()
            proof['v_relative_l2']=((v.float()-ref_v.float()).norm()/ref_v.float().norm()).item()
            proof['h_different']=(h!=ref_h).sum().item()
            proof['v_different']=(v!=ref_v).sum().item()
            assert proof['h_relative_l2']<.03 and proof['v_relative_l2']<.03
            assert proof['finite'] and proof['untouched'] and proof['relative_l2']<.03,(config,proof)
            g=torch.cuda.CUDAGraph()
            with torch.cuda.graph(g,stream=stream):
                for _ in range(64):fn()
            for _ in range(100):g.replay()
            stream.synchronize();ts=[]
            for _ in range(5):
                a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True)
                a.record(stream);g.replay();b.record(stream);b.synchronize();ts.append(a.elapsed_time(b)*1000/64)
            row=dict(index=index,config=config,microseconds=statistics.mean(ts),trials=ts,proof=proof,prep_seconds=prep)
            rows.append(row);print(json.dumps(row),flush=True)
            Path('ENTITY_TRAIN_'+name+'.rows.json').write_text(json.dumps(rows,indent=2));del g
    control=statistics.mean([rows[0]['microseconds'],rows[-1]['microseconds']])
    for r in rows:r['gain_percent']=100*(control/r['microseconds']-1)
    result=dict(control_us=control,control_drift_percent=100*(rows[-1]['microseconds']/rows[0]['microseconds']-1),rows=rows,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),reference_sha256=hashlib.sha256(Path('entity_train_reference.so').read_bytes()).hexdigest(),scope='Training entity16->64->64 bias/ReLU and masked sum/max;4096games. Actual cuBLAS plus separate bias/ReLU baseline. BF16 pre-bias rounding retained and intermediate tensors saved. Synthetic inputs; no optimizer-state claim.',entity=name,entities_per_game=n,concat_offset=off,pad=pad,eps=eps)
    Path('ENTITY_TRAIN_'+name+'.json').write_text(json.dumps(result,indent=2));print('COMPLETE',control,flush=True)

if __name__=='__main__':main()
