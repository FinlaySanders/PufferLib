"""Stage B1: fused minGRU layer (inference) + per-slot logprob/value dump for numerics validation (PUF_SCHED_DUMP=path)."""
from pathlib import Path
a=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/src/algo.cu'); t=a.read_text()
kern=Path('/puffertank/experiments/nethack-latency-20261014/stageB/mingru_fused.cu').read_text()
def rep(old,new,count=1):
    global t; assert t.count(old)==count, (t.count(old), old[:80]); t=t.replace(old,new)
anchor="Prec mingru_forward(void* w, Prec x, Prec state,\n        void* activations, cudaStream_t stream) {"
rep(anchor, kern+"\n"+anchor)
rep("""        Prec fused_out = x.data == a->out.data ? a->next_state : a->out;
        if (rec_fused_try(x.data, m->weights[i].data, state_i.data,""",
"""        Prec fused_out = x.data == a->out.data ? a->next_state : a->out;
        if (mingru_fused_try(x.data, m->weights[i].data, state_i.data, fused_out.data, B, H, stream)) { x = fused_out; continue; }
        if (rec_fused_try(x.data, m->weights[i].data, state_i.data,""")
a.write_text(t)
p=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/src/pufferl.cu'); t=p.read_text()
rep("""        assert(cudaStreamSynchronize(stream) == cudaSuccess);
        double dt = es_now() - f0; fwd_ewma = 0.9 * fwd_ewma + 0.1 * dt; vec->sched_fwd_sum[s] += dt;""",
"""        assert(cudaStreamSynchronize(stream) == cudaSuccess);
        if (g_sched_dump && vec->sched_forwards[s] < 64) { /* numerics probe: logprob/value of the first 64 forwards per slot */
            StepRecord sv = record_view(p->step_rollouts, 0, start, R);
            precision_t* hl = (precision_t*)malloc(2 * R * sizeof(precision_t));
            cudaMemcpy(hl, sv.lp, R * sizeof(precision_t), cudaMemcpyDeviceToHost); cudaMemcpy(hl + R, sv.val, R * sizeof(precision_t), cudaMemcpyDeviceToHost);
            char path[512]; snprintf(path, sizeof path, "%s.slot%d", g_sched_dump, s); FILE* df = fopen(path, "a");
            for (int r = 0; r < n; r++) fprintf(df, "%ld %d %d %.6g %.6g\\n", vec->sched_forwards[s], r, idx[r], (double)to_float(hl[r]), (double)to_float(hl[R + r]));
            fclose(df); free(hl);
        }
        double dt = es_now() - f0; fwd_ewma = 0.9 * fwd_ewma + 0.1 * dt; vec->sched_fwd_sum[s] += dt;""")
rep("""static int g_sched_fold = -1;""", """static int g_sched_fold = -1; static const char* g_sched_dump = getenv("PUF_SCHED_DUMP");""")
p.write_text(t); print('B1 applied')
