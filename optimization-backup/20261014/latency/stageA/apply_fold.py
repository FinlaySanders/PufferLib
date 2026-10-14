"""Stage A part 1: fold the scheduler's 7 housekeeping kernels into 2 (PUF_SCHED_FOLD=1), identical element-wise semantics; graph node count print."""
from pathlib import Path
q=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/src/pufferl.cu'); t=q.read_text()
def rep(old,new):
    global t; assert t.count(old)==1, old[:80]; t=t.replace(old,new)
rep("""/* Mock forward (PUF_SCHED_MOCK_FORWARD=K)""",
"""/* Folded housekeeping (PUF_SCHED_FOLD=1): one kernel gathers state + RNG, zeroes terminal rows and snapshots segment starts; one kernel
 * scatters state + RNG and records the step. Same element-wise operations as the seven kernels above, in dependency order per element. */
__global__ void sched_pre_kernel(Prec st, Prec full_state, Prec init_states, Float terminals, curandStatePhilox4_32_10_t* rng_dst,
        const curandStatePhilox4_32_10_t* rng_src, const int* idx, const int* tt, int R, int start, int horizon) {
    int L = st.shape[0], H = st.shape[2], A = (int)full_state.shape[1]; long total = (long)L * R * H;
    int Af = init_states.data ? (int)init_states.shape[2] : 0; long stride = (long)L * Af * H;
    for (long i = blockIdx.x * (long)blockDim.x + threadIdx.x; i < total; i += (long)gridDim.x * blockDim.x) {
        int h = i % H, r = (i / H) % R, layer = i / ((long)R * H); int a = idx[r];
        precision_t v = full_state.data[state_elem_idx(layer, A, a < 0 ? 0 : a, h, H)];
        if (terminals.data[start + r] != 0.0f) v = from_float(0.0f);
        st.data[state_elem_idx(layer, R, r, h, H)] = v;
        if (init_states.data && a >= 0 && tt[r] % horizon == 0)
            init_states.data[(long)(tt[r] / horizon) * stride + state_elem_idx(layer, Af, a, h, H)] = v;
        if (i < R) { int ar = idx[i]; rng_dst[i] = rng_src[ar < 0 ? 0 : ar]; }
    }
}
__global__ void sched_post_kernel(Prec full_state, Prec st, curandStatePhilox4_32_10_t* rng_dst, const curandStatePhilox4_32_10_t* rng_src,
        StepRecord dst, StepRecord src, const int* idx, const int* tt, int R, int B, int Op, int Mp, int Ap) {
    int L = st.shape[0], H = st.shape[2], A = (int)full_state.shape[1]; long nstate = (long)L * R * H;
    int maxp = max(Op, max(Mp, Ap)); long nrec = (long)R * maxp; long total = nstate > nrec ? nstate : nrec;
    for (long i = blockIdx.x * (long)blockDim.x + threadIdx.x; i < total; i += (long)gridDim.x * blockDim.x) {
        if (i < nstate) { int h = i % H, r = (i / H) % R, layer = i / ((long)R * H); int a = idx[r];
            if (a >= 0) full_state.data[state_elem_idx(layer, A, a, h, H)] = st.data[state_elem_idx(layer, R, r, h, H)]; }
        if (i < nrec) { int r = i / maxp, e = i % maxp; int a = idx[r];
            if (a >= 0) { long row = (long)tt[r] * B + a;
                if (e < Op) dst.obs[row * Op + e] = src.obs[(long)r * Op + e];
                if (e < Mp) dst.mask[row * Mp + e] = src.mask[(long)r * Mp + e];
                if (e < Ap) dst.actions[row * Ap + e] = src.actions[(long)r * Ap + e];
                if (e == 0) { dst.lp[row] = src.lp[r]; dst.val[row] = src.val[r]; dst.rew[row] = src.rew[r]; dst.term[row] = src.term[r]; } } }
        if (i < R) { int a = idx[i]; if (a >= 0) rng_dst[a] = rng_src[i]; }
    }
}
static int g_sched_fold = -1;
/* Mock forward (PUF_SCHED_MOCK_FORWARD=K)""")
rep("""    sched_gather_state<<<grid_size(state_n), BLOCK_SIZE, 0, stream>>>(*st, p->sched_state, vec->d_idx[s], R, 0);
    sched_gather_rng<<<grid_size(R), BLOCK_SIZE, 0, stream>>>(p->rng_states[s], p->sched_rng, vec->d_idx[s], R, 0);
    zero_term_state<<<grid_size(state_n), BLOCK_SIZE, 0, stream>>>(*st, p->env.terminals, 0, start, R);
    if (p->rollouts.initial_states.data)
        sched_snapshot_state<<<grid_size(state_n), BLOCK_SIZE, 0, stream>>>(p->rollouts.initial_states, *st, vec->d_idx[s], vec->d_tt[s], R, H);
    pufferl_forward_step(p, s, 0, stream);
    sched_scatter_state<<<grid_size(state_n), BLOCK_SIZE, 0, stream>>>(p->sched_state, *st, vec->d_idx[s], R);
    sched_scatter_rng<<<grid_size(R), BLOCK_SIZE, 0, stream>>>(p->sched_rng, p->rng_states[s], vec->d_idx[s], R);
    RolloutBuf& ro = p->rollouts;
    StepRecord dst = {ro.observations.data, ro.action_mask.data, ro.logprobs.data, ro.values.data, ro.rewards.data, ro.terminals.data, ro.actions.data};
    StepRecord src = record_view(p->step_rollouts, 0, start, R);
    int Op = p->step_rollouts.observations.shape[2], Mp = p->step_rollouts.action_mask.shape[2], Ap = p->step_rollouts.actions.shape[2];
    sched_record_scatter<<<grid_size(R * max(Op, max(Mp, Ap))), BLOCK_SIZE, 0, stream>>>(dst, src, vec->d_idx[s], vec->d_tt[s], R, p->hypers.total_agents, Op, Mp, Ap);
}""",
"""    if (g_sched_fold < 0) g_sched_fold = getenv("PUF_SCHED_FOLD") ? atoi(getenv("PUF_SCHED_FOLD")) : 0;
    RolloutBuf& ro = p->rollouts;
    StepRecord dst = {ro.observations.data, ro.action_mask.data, ro.logprobs.data, ro.values.data, ro.rewards.data, ro.terminals.data, ro.actions.data};
    StepRecord src = record_view(p->step_rollouts, 0, start, R);
    int Op = p->step_rollouts.observations.shape[2], Mp = p->step_rollouts.action_mask.shape[2], Ap = p->step_rollouts.actions.shape[2];
    if (g_sched_fold) {
        sched_pre_kernel<<<grid_size(state_n), BLOCK_SIZE, 0, stream>>>(*st, p->sched_state, p->rollouts.initial_states, p->env.terminals,
            p->rng_states[s], p->sched_rng, vec->d_idx[s], vec->d_tt[s], R, start, H);
        pufferl_forward_step(p, s, 0, stream);
        long npost = max((long)state_n, (long)R * max(Op, max(Mp, Ap)));
        sched_post_kernel<<<grid_size(npost), BLOCK_SIZE, 0, stream>>>(p->sched_state, *st, p->sched_rng, p->rng_states[s], dst, src,
            vec->d_idx[s], vec->d_tt[s], R, p->hypers.total_agents, Op, Mp, Ap);
        return;
    }
    sched_gather_state<<<grid_size(state_n), BLOCK_SIZE, 0, stream>>>(*st, p->sched_state, vec->d_idx[s], R, 0);
    sched_gather_rng<<<grid_size(R), BLOCK_SIZE, 0, stream>>>(p->rng_states[s], p->sched_rng, vec->d_idx[s], R, 0);
    zero_term_state<<<grid_size(state_n), BLOCK_SIZE, 0, stream>>>(*st, p->env.terminals, 0, start, R);
    if (p->rollouts.initial_states.data)
        sched_snapshot_state<<<grid_size(state_n), BLOCK_SIZE, 0, stream>>>(p->rollouts.initial_states, *st, vec->d_idx[s], vec->d_tt[s], R, H);
    pufferl_forward_step(p, s, 0, stream);
    sched_scatter_state<<<grid_size(state_n), BLOCK_SIZE, 0, stream>>>(p->sched_state, *st, vec->d_idx[s], R);
    sched_scatter_rng<<<grid_size(R), BLOCK_SIZE, 0, stream>>>(p->sched_rng, p->rng_states[s], vec->d_idx[s], R);
    sched_record_scatter<<<grid_size(R * max(Op, max(Mp, Ap))), BLOCK_SIZE, 0, stream>>>(dst, src, vec->d_idx[s], vec->d_tt[s], R, p->hypers.total_agents, Op, Mp, Ap);
}""")
rep("""            assert(cudaGraphInstantiate(&graph, g, 0) == cudaSuccess); cudaGraphDestroy(g);""",
"""            if (getenv("PUF_SCHED_GRAPH_INFO")) { size_t nn = 0; cudaGraphGetNodes(g, NULL, &nn); fprintf(stderr, "SCHED_GRAPH slot=%d nodes=%zu\\n", s, nn); }
            assert(cudaGraphInstantiate(&graph, g, 0) == cudaSuccess); cudaGraphDestroy(g);""")
q.write_text(t); print('fold applied')
