from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/pufferl.cu';s=p.read_text();a=s.index('static void cpu_upload(');i=s.index('    cudaMemcpyAsync',a)
new='''#ifdef PUF_BATCH_UPLOAD
    if(stream != 0) {
        void* dsts[]={e->obs.data+(size_t)start*OBS_SIZE,e->rewards.data+start,e->terminals.data+start,e->action_mask.data+(size_t)start*mask};
        const void* srcs[]={v->observations+(size_t)start*OBS_SIZE,v->rewards+start,v->terminals+start,v->action_mask+(size_t)start*mask};
        size_t sizes[]={(size_t)n*OBS_SIZE*sizeof(obs_t),(size_t)n*sizeof(float),(size_t)n*sizeof(float),(size_t)n*mask};
        cudaMemcpyAttributes attrs={};attrs.srcAccessOrder=cudaMemcpySrcAccessOrderStream;
        size_t first=0;cudaError_t error=cudaMemcpyBatchAsync(dsts,srcs,sizes,4,&attrs,&first,1,stream);
        if(error!=cudaSuccess)fprintf(stderr,"BATCH_UPLOAD_ERROR %s\\n",cudaGetErrorString(error));
        assert(error==cudaSuccess);return;
    }
#endif
'''
s=s[:i]+new+s[i:];p.write_text(s)
