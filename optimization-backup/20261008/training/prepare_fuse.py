from pathlib import Path
r=Path(__file__).parent;a=r/'source/src/algo.cu';s=a.read_text()
pos=s.index('constexpr double ns_coeffs')
k='''#ifdef PUF_MUON_FUSE_CAST
__global__ void muon_weight_update_cast(float* __restrict__ wb, precision_t* __restrict__ low,
        const precision_t* __restrict__ update, const float* __restrict__ lr_ptr, float wd, int n) {
    float lr=*lr_ptr;float wd_scale=1.0f-lr*wd;
    int idx=blockIdx.x*blockDim.x+threadIdx.x;
    if(idx<n) { float v=wb[idx]*wd_scale-lr*to_float(update[idx]);wb[idx]=v;low[idx]=from_float(v); }
}
#endif

'''
s=s[:pos]+k+s[pos:]
s=s.replace('float max_grad_norm, cudaStream_t stream = 0) {','float max_grad_norm, cudaStream_t stream = 0, precision_t* low = nullptr) {')
old='''    muon_weight_update<<<grid_size(n_grad), BLOCK_SIZE, 0, stream>>>(
        weights.data, grads.data, m->lr, 0.0f, n_grad);'''
new='''#ifdef PUF_MUON_FUSE_CAST
    if(low) muon_weight_update_cast<<<grid_size(n_grad),BLOCK_SIZE,0,stream>>>(weights.data,low,grads.data,m->lr,0.0f,n_grad);
    else
#endif
    muon_weight_update<<<grid_size(n_grad), BLOCK_SIZE, 0, stream>>>(
        weights.data, grads.data, m->lr, 0.0f, n_grad);'''
assert old in s;s=s.replace(old,new);a.write_text(s)
p=r/'source/src/pufferl.cu';t=p.read_text();(r/'pufferl.before-fuse.cu').write_text(t)
old='''        muon_step(&pufferl->muon, update_weights,
            pufferl->grad, hypers->max_grad_norm, stream);
        if (USE_BF16) {'''
new='''#ifdef PUF_MUON_FUSE_CAST
        muon_step(&pufferl->muon,update_weights,pufferl->grad,hypers->max_grad_norm,stream,
            USE_BF16 ? (pufferl->perf_frozen ? pufferl->perf_shadow_param.data : primary->param.data) : nullptr);
#else
        muon_step(&pufferl->muon, update_weights,
            pufferl->grad, hypers->max_grad_norm, stream);
#endif
#ifndef PUF_MUON_FUSE_CAST
        if (USE_BF16) {'''
assert old in t;t=t.replace(old,new)
old='''                update_weights.data, n);
        }
    }
    puf_stamp'''
new='''                update_weights.data, n);
        }
#endif
    }
    puf_stamp'''
assert old in t;t=t.replace(old,new);p.write_text(t)
