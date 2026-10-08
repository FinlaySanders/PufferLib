from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/pufferl.cu';s=p.read_text();a='''        size_t memfree=0,memtotal=0;cudaMemGetInfo(&memfree,&memtotal);'''
b='''        if(epoch==15 && getenv("PUF_STATE_PROOF")) {
            assert(cudaDeviceSynchronize()==cudaSuccess);
            auto save_state=[&](const char* name,void* ptr,size_t bytes) {
                void* host=malloc(bytes);assert(host);
                assert(cudaMemcpy(host,ptr,bytes,cudaMemcpyDeviceToHost)==cudaSuccess);
                char path[4096];snprintf(path,sizeof(path),"%s/%s.bin",getenv("PUF_STATE_PROOF"),name);
                FILE* f=fopen(path,"wb");assert(f);assert(fwrite(host,1,bytes,f)==bytes);fclose(f);free(host);
            };
            save_state("master",pufferl->policies[0].master_weights.data,numel(pufferl->policies[0].master_weights.shape)*sizeof(float));
            save_state("momentum",pufferl->muon.mb.data,numel(pufferl->muon.mb.shape)*sizeof(float));
            save_state("updates",pufferl->grad.data,numel(pufferl->grad.shape)*sizeof(precision_t));
        }
'''+a
assert s.count(a)==1;s=s.replace(a,b);p.write_text(s)
