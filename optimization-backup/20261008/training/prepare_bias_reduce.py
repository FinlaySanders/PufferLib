from pathlib import Path
r=Path(__file__).parent;p=r/'source/ocean/nethack/nethack.cu';s=p.read_text()
i=s.index('__global__ void nh_relu_bias_bwd_kernel(');j=s.index('\n}\n',i)+3;fn=s[i:j]
needle='    extern __shared__ long long sdata[];'
code='''#ifdef PUF_BIAS_REDUCE
    if (dim<=BLOCK_SIZE && BLOCK_SIZE%dim==0) {
        __shared__ unsigned long long sums[BLOCK_SIZE];
        int64_t i0=(int64_t)blockIdx.x*blockDim.x+threadIdx.x;
        int64_t stride=(int64_t)gridDim.x*blockDim.x;
        float acc=0.0f;
        for(int64_t i=i0;i<total;i+=stride) {
            float g=to_float(out[i])>0.0f?to_float(grad[i]):0.0f;
            grad[i]=from_float(g);acc+=g;
        }
        sums[threadIdx.x]=(unsigned long long)__float2ll_rn(acc*NH_FXP);
        __syncthreads();
        if(threadIdx.x<dim) {
            unsigned long long sum=0;
            for(int k=threadIdx.x;k<BLOCK_SIZE;k+=dim)sum+=sums[k];
            if(sum)atomicAdd((unsigned long long*)&bias_acc[threadIdx.x],sum);
        }
        return;
    }
#endif
'''
assert needle in fn;fn=fn.replace(needle,code+needle,1);s=s[:i]+fn+s[j:];p.write_text(s)
