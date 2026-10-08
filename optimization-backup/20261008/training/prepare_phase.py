from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/pufferl.cu';s=p.read_text()
a='''    unsigned long long* stamps;  // device [2 * NUM_TE]; globaltimer ns''';assert a in s
s=s.replace(a,a+'''
#ifdef PUF_PHASE_PROFILE
    unsigned long long* phase_stamps;
#endif''',1)
a='''        2 * NUM_TE * sizeof(unsigned long long));''';assert a in s
s=s.replace(a,a+'''
#ifdef PUF_PHASE_PROFILE
    int nphase=(int)(hypers.replay_ratio*hypers.total_agents*hypers.horizon/hypers.minibatch_size);
    assert(cudaMalloc(&pufferl->profile.phase_stamps,2*nphase*5*sizeof(unsigned long long))==cudaSuccess);
#endif''',1)
a='''        Prec dec = arch_forward_train(''';assert a in s
s=s.replace(a,'''#ifdef PUF_PHASE_PROFILE
        auto* phase=pufferl->profile.phase_stamps+(slot*total_minibatches+mb)*5;
        puf_stamp<<<1,1,0,stream>>>(phase);
#endif
'''+a,1)
a='''        puff_advantage<<<adv_grid, ADV_THREADS, 0, stream>>>(''';assert a in s
s=s.replace(a,'''#ifdef PUF_PHASE_PROFILE
        puf_stamp<<<1,1,0,stream>>>(phase+1);
#endif
'''+a,1)
a='''        Float grad_logits = pufferl->ppo_bufs.grad_logits;''';assert a in s
s=s.replace(a,'''#ifdef PUF_PHASE_PROFILE
        puf_stamp<<<1,1,0,stream>>>(phase+2);
#endif
'''+a,1)
a='''        Float update_weights = pufferl->perf_frozen''';assert a in s
s=s.replace(a,'''#ifdef PUF_PHASE_PROFILE
        puf_stamp<<<1,1,0,stream>>>(phase+3);
#endif
'''+a,1)
a='''#endif
    }
    puf_stamp<<<1, 1, 0, stream>>>(st + TE_E);''';assert a in s
s=s.replace(a,'''#endif
#ifdef PUF_PHASE_PROFILE
        puf_stamp<<<1,1,0,stream>>>(phase+4);
#endif
    }
    puf_stamp<<<1, 1, 0, stream>>>(st + TE_E);''',1)
a='''    pufferl->epoch += 1;
}''';assert a in s
s=s.replace(a,'''#ifdef PUF_PHASE_PROFILE
    if(total_minibatches>0) {
        auto* h=(unsigned long long*)malloc(total_minibatches*5*sizeof(unsigned long long));
        assert(cudaMemcpy(h,pufferl->profile.phase_stamps+slot*total_minibatches*5,total_minibatches*5*sizeof(unsigned long long),cudaMemcpyDeviceToHost)==cudaSuccess);
        double ms[4]={};for(int i=0;i<total_minibatches;i++)for(int j=0;j<4;j++)ms[j]+=(h[i*5+j+1]-h[i*5+j])*1e-6;
        fprintf(stderr,"TRAIN_PHASE epoch=%d forward_ms=%.6f loss_ms=%.6f backward_ms=%.6f optimizer_ms=%.6f\\n",current_epoch,ms[0],ms[1],ms[2],ms[3]);free(h);
    }
#endif
'''+a,1);p.write_text(s)
