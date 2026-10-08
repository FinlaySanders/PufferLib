from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/algo.cu';s=p.read_text()
a='__global__ void ppo_loss_compute('
code='''#if defined(PUF_PPO_ZERO) && defined(PUFFER_NETHACK)
__global__ void nethack_zero_unused(float* logps,const float* actions,int A_total,int NT) {
    long i=(long)blockIdx.x*blockDim.x+threadIdx.x;if(i>=(long)NT*A_total)return;
    int sample=i/A_total,c=i%A_total;
    constexpr int widths[]=ACT_SIZES;
    int h=0,off=0;
    #pragma unroll
    for(int j=0;j<NUM_ATNS;j++) { if(c>=off)h=j;off+=widths[j]; }
    if(!nethack_head_used((int)actions[sample*NUM_ATNS],h))logps[i]=0.0f;
}
#endif
'''
assert a in s;s=s.replace(a,code+a,1)
a='''                    for (int j = 0; j < A; ++j) {
                        a.grad_logits[at_base + logits_offset + j] = 0.0f;
                    }''';assert a in s;s=s.replace(a,'#ifndef PUF_PPO_ZERO\n'+a+'\n#endif',1)
a='''    ppo_loss_compute<<<ppo_grid, PPO_THREADS, 0, stream>>>('''
b='''#if defined(PUF_PPO_ZERO) && defined(PUFFER_NETHACK)
    nethack_zero_unused<<<grid_size((long)N*T*A_total),BLOCK_SIZE,0,stream>>>(args.grad_logits,graph_args.actions,A_total,N*T);
#endif
'''+a
assert a in s;s=s.replace(a,b,1);p.write_text(s)
