from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/pufferl.cu';s=p.read_text();(r/'pufferl.before-reuse.cu').write_text(s)
a='''    RolloutBuf rollouts;''';assert a in s;s=s.replace(a,a+'''
#ifdef PUF_REUSE_ROLLOUT
    RolloutBuf step_rollouts;
#endif''',1)
a='''    register_rollout_buffers(&pufferl->rollouts,
        acts, rollout_horizon, total_agents, input_size, num_action_heads, act_n);''';assert a in s
s=s.replace(a,a+'''
#ifdef PUF_REUSE_ROLLOUT
    assert(PUF_BACKEND==PUF_CPU);
    register_rollout_buffers(&pufferl->step_rollouts,acts,1,total_agents,input_size,num_action_heads,act_n);
#endif''',1)
start=s.index('void pufferl_forward_step(');end=s.index('\nvoid pufferl_forward(',start);part=s[start:end]
a='''    EnvBuf* env = &pufferl->env;''';assert a in part
part=part.replace(a,'''#ifdef PUF_REUSE_ROLLOUT
    int original_t=t;
    rollouts=pufferl->step_rollouts;t=0;
#endif
'''+a,1)
part=part.replace('        nh_refresh_tables=(t==0);','''#ifdef PUF_REUSE_ROLLOUT
        nh_refresh_tables=(original_t==0);
#else
        nh_refresh_tables=(t==0);
#endif''')
s=s[:start]+part+s[end:]
helper='''#ifdef PUF_REUSE_ROLLOUT
struct StepRecord { precision_t *obs,*mask,*lp,*val,*rew,*term;float* actions; };
__global__ void record_step(StepRecord dst,StepRecord src,int O,int M,int A,int B) {
    int i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<O)dst.obs[i]=src.obs[i];
    if(i<M)dst.mask[i]=src.mask[i];
    if(i<A)dst.actions[i]=src.actions[i];
    if(i<B){dst.lp[i]=src.lp[i];dst.val[i]=src.val[i];dst.rew[i]=src.rew[i];dst.term[i]=src.term[i];}
}
static StepRecord record_view(RolloutBuf& r,int t,int start,int n) {
    return {puf_slice(r.observations,t,start,n).data,puf_slice(r.action_mask,t,start,n).data,
        puf_slice(r.logprobs,t,start,n).data,puf_slice(r.values,t,start,n).data,
        puf_slice(r.rewards,t,start,n).data,puf_slice(r.terminals,t,start,n).data,
        puf_slice(r.actions,t,start,n).data};
}
static void record_rollout_step(PuffeRL* p,int buf,int t,cudaStream_t stream) {
    int B=p->hypers.total_agents/p->hypers.num_buffers,start=buf*B;
    int slot=p->hypers.async?p->write_slot:0;
    auto dst=record_view(p->rollouts,slot*p->hypers.horizon+t,start,B);
    auto src=record_view(p->step_rollouts,0,start,B);
    int O=B*p->step_rollouts.observations.shape[2],M=B*p->step_rollouts.action_mask.shape[2],A=B*p->step_rollouts.actions.shape[2];
    record_step<<<grid_size(max(O,max(M,A))),BLOCK_SIZE,0,stream>>>(dst,src,O,M,A,B);
}
static void snapshot_rollout_start(PuffeRL* p,int buf,cudaStream_t stream) {
    if(!p->rollouts.initial_states.data)return;
    int start=buf*(p->hypers.total_agents/p->hypers.num_buffers);
    int slot=p->hypers.async?p->write_slot:0;
    for(int b=0;b<p->num_policies;b++) {
        Policy* pol=&p->policies[b];if(pol->frozen)continue;
        int off=p->vec->policy_layout[b],n=p->vec->policy_layout[b+1]-off;if(!n)continue;
        Prec st=pol->buffer_states[buf];int count=st.shape[0]*n*st.shape[2];
        zero_term_state<<<grid_size(count),BLOCK_SIZE,0,stream>>>(st,p->env.terminals,0,start+off,n);
        snapshot_state<<<grid_size(count),BLOCK_SIZE,0,stream>>>(init_slot(p->rollouts.initial_states,slot),st,start+off,n);
    }
}
#endif

'''
a='void pufferl_forward(PuffeRL*';assert a in s;s=s.replace(a,helper+a,1)
a='''    int graph = (graph_slot * hypers->horizon + t) * hypers->num_buffers + buf;''';assert a in s
s=s.replace(a,'''#ifdef PUF_REUSE_ROLLOUT
    int graph=(t==0?0:1)*hypers->num_buffers+buf;
    if(t==0)snapshot_rollout_start(pufferl,buf,stream);
#else
'''+a+'\n#endif',1)
a='''            && "cudaGraphLaunch failed");
        profile_end(hypers->profile);
        return;''';assert a in s
s=s.replace(a,'''            && "cudaGraphLaunch failed");
#ifdef PUF_REUSE_ROLLOUT
        record_rollout_step(pufferl,buf,t,stream);
#endif
        profile_end(hypers->profile);
        return;''',1)
a='''    profile_end(hypers->profile);
}
''';start=s.index('void pufferl_forward(PuffeRL*');end=s.index(a,start)
s=s[:end]+'''#ifdef PUF_REUSE_ROLLOUT
    record_rollout_step(pufferl,buf,t,stream);
#endif
'''+s[end:];p.write_text(s)
