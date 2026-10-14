"""Streaming gather (PUF_SCHED_STREAM=1, requires PUF_SCHED_ZERO_COPY=2): the slot thread pops games as they arrive during the window and issues
their observation/mask copies immediately (coalesced to PUF_SCHED_STREAM_ROWS rows or PUF_SCHED_STREAM_US), so the DMA overlaps the window
wait instead of running serially at window close. Same rows, same bytes, same launch rule (oldest row's age >= window, or R rows): exact."""
from pathlib import Path
def rep(t,old,new,count=1):
    assert t.count(old)==count, (t.count(old), old[:90]); return t.replace(old,new)
E=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/src/env_sched.h'); t=E.read_text()
t=rep(t,"""/* Actions for these games are back in the host action array: hand them to their owners. */""",
"""/* Pop whatever is in the inference ring now (up to max), ignoring the window; *first_time = push time of the first popped item. */
static int es_infer_pop_any(EnvSched* s, int* ids, int max, double* first_time) {
    ESRing* r = &s->infer;
    if (!__atomic_load_n(&r->count, __ATOMIC_RELAXED) || max <= 0) return 0;
    es_lock(&r->lock);
    int n = r->count < max ? r->count : max;
    if (n > 0) *first_time = r->times[r->head];
    for (int i = 0; i < n; i++) { ids[i] = r->items[r->head]; r->head = (r->head + 1) % r->cap; }
    r->count -= n;
    es_unlock(&r->lock);
    return n;
}
/* Actions for these games are back in the host action array: hand them to their owners. */""")
E.write_text(t)
P=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/src/pufferl.cu'); t=P.read_text()
t=rep(t,"""    int tables_ext = getenv("PUF_SCHED_TABLES") ? atoi(getenv("PUF_SCHED_TABLES")) : 0; long table_epoch = -1;""",
"""    int tables_ext = getenv("PUF_SCHED_TABLES") ? atoi(getenv("PUF_SCHED_TABLES")) : 0; long table_epoch = -1;
    int stream_mode = getenv("PUF_SCHED_STREAM") ? atoi(getenv("PUF_SCHED_STREAM")) : 0;
    int stream_rows = getenv("PUF_SCHED_STREAM_ROWS") ? atoi(getenv("PUF_SCHED_STREAM_ROWS")) : 8;
    double stream_us = (getenv("PUF_SCHED_STREAM_US") ? atof(getenv("PUF_SCHED_STREAM_US")) : 25.0) * 1e-6;
    if (stream_mode) assert(vec->sched_zero_copy == 2 && "PUF_SCHED_STREAM needs the batched DMA gather (PUF_SCHED_ZERO_COPY=2)");
    int n_acc = 0, pend_from = 0, wslot_b = 0; double batch_t0 = 0, last_issue = 0;""")
t=rep(t,"""        double window = vec->sched_window > 0 ? vec->sched_window : fwd_ewma;
        int n = es_infer_pop(es, idx, R, window);
        if (!n) {""",
"""        int n, wslot;
        if (stream_mode) {
            double window = vec->sched_window > 0 ? vec->sched_window : fwd_ewma; double first_t = 0;
            int k = es_infer_pop_any(es, idx + n_acc, R - n_acc, &first_t);
            if (k > 0) {
                if (n_acc == 0) { batch_t0 = first_t; wslot_b = vec->sched_write_slot; last_issue = es_now(); }
                for (int r = n_acc; r < n_acc + k; r++) { int g = idx[r]; tt[r] = wslot_b * H + es->agent[g].t; srew[r] = vec->rewards[g]; sterm[r] = vec->terminals[g];
                    bdst[2 * r] = e->obs.data + (size_t)(start + r) * OBS_SIZE; bsrc[2 * r] = vec->observations + (size_t)g * OBS_SIZE; bsz[2 * r] = (size_t)OBS_SIZE * sizeof(obs_t);
                    bdst[2 * r + 1] = e->action_mask.data + (size_t)(start + r) * mask; bsrc[2 * r + 1] = vec->action_mask + (size_t)g * mask; bsz[2 * r + 1] = (size_t)mask; }
                n_acc += k;
            }
            if (n_acc == 0) { for (int i = 0; i < 16; i++) _mm_pause(); continue; }
            double now = es_now(); int pend = n_acc - pend_from; int closing = (n_acc == R) || (now - batch_t0 >= window);
            if (pend > 0 && (pend >= stream_rows || now - last_issue >= stream_us || closing)) {
                size_t aidx = 0;
                assert(cudaMemcpyBatchAsync(bdst + 2 * pend_from, bsrc + 2 * pend_from, bsz + 2 * pend_from, (size_t)2 * pend, &battr, &aidx, 1, stream) == cudaSuccess && "cudaMemcpyBatchAsync failed");
                pend_from = n_acc; last_issue = now;
            }
            if (!closing) { for (int i = 0; i < 16; i++) _mm_pause(); continue; }
            n = n_acc; n_acc = 0; pend_from = 0; wslot = wslot_b;
            for (int r = n; r < R; r++) { idx[r] = -1; tt[r] = wslot * H; srew[r] = 0; sterm[r] = 0; }
            cudaMemcpyAsync(e->rewards.data + start, srew, R * sizeof(float), cudaMemcpyHostToDevice, stream);
            cudaMemcpyAsync(e->terminals.data + start, sterm, R * sizeof(float), cudaMemcpyHostToDevice, stream);
        } else {
        double window = vec->sched_window > 0 ? vec->sched_window : fwd_ewma;
        n = es_infer_pop(es, idx, R, window);
        if (!n) {""")
t=rep(t,"""        int wslot = vec->sched_write_slot;
        if (vec->sched_zero_copy == 2) {""",
"""        wslot = vec->sched_write_slot;
        if (vec->sched_zero_copy == 2) {""")
t=rep(t,"""        cudaMemcpyAsync(e->action_mask.data + (size_t)start * mask, smask, (size_t)R * mask, cudaMemcpyHostToDevice, stream);
        }
        cudaMemcpyAsync(vec->d_idx[s], idx, R * sizeof(int), cudaMemcpyHostToDevice, stream);""",
"""        cudaMemcpyAsync(e->action_mask.data + (size_t)start * mask, smask, (size_t)R * mask, cudaMemcpyHostToDevice, stream);
        }
        }
        cudaMemcpyAsync(vec->d_idx[s], idx, R * sizeof(int), cudaMemcpyHostToDevice, stream);""")
P.write_text(t); print('stream gather applied')
