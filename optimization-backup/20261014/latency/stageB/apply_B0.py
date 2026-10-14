"""Stage B0 (exact): (1) PUF_SCHED_TABLES=1 — the three vocabulary table kernels run once per epoch outside the captured graph instead of
inside every forward; (2) PUF_SCHED_SKIPDUP=1 — the forward step's own zero_term_state is skipped in the scheduler path (the pre-kernel already
zeroed the same rows; idempotent)."""
from pathlib import Path
f=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/ocean/nethack/nethack.cu'); t=f.read_text()
def rep(old,new,count=1):
    global t; assert t.count(old)==count, (t.count(old), old[:80]); t=t.replace(old,new)
rep("""thread_local bool nh_refresh_tables = true;""",
"""thread_local bool nh_refresh_tables = true;
thread_local bool nh_tables_external = false; /* scheduler slot threads refresh the vocabulary tables per epoch, outside the graph */""")
rep("""static Prec nethack_encoder_forward(void* w, void* activations, Prec input, cudaStream_t stream) {
    NethackEncoderWeights* ew = (NethackEncoderWeights*)w;
    NethackEncoderActivations* a = (NethackEncoderActivations*)activations;
    nh_fused_br_active = (nh_fused_br_mode & (a->training ? 2 : 1)) != 0;
    int B = input.shape[0];

    if (nh_refresh_tables) {""",
"""void nethack_encoder_refresh_tables(void* w, void* activations, cudaStream_t stream) {
    NethackEncoderWeights* ew = (NethackEncoderWeights*)w;
    NethackEncoderActivations* a = (NethackEncoderActivations*)activations;
    nh_eff_embed_kernel<<<nh_narrow_grid(grid_size(NH_GLYPH_VOCAB * NH_EMBED_DIM), a->training), BLOCK_SIZE, 0, stream>>>(
        a->e_eff.data, ew->embed_w.data, ew->ekind_w.data, ew->esub_w.data);
    nh_inv_table_kernel<<<nh_narrow_grid(grid_size(NH_GLYPH_VOCAB * NH_INV_HID), a->training), BLOCK_SIZE, 0, stream>>>(
        a->inv_T.data, a->e_eff.data, ew->inv1_w.data);
    nh_inv_table_kernel<<<nh_narrow_grid(grid_size(NH_GLYPH_VOCAB * NH_INV_HID), a->training), BLOCK_SIZE, 0, stream>>>(
        a->invt_T.data, a->e_eff.data, ew->invt_w.data);
}
static Prec nethack_encoder_forward(void* w, void* activations, Prec input, cudaStream_t stream) {
    NethackEncoderWeights* ew = (NethackEncoderWeights*)w;
    NethackEncoderActivations* a = (NethackEncoderActivations*)activations;
    nh_fused_br_active = (nh_fused_br_mode & (a->training ? 2 : 1)) != 0;
    int B = input.shape[0];
    if (nh_tables_external) nh_refresh_tables = false;

    if (nh_refresh_tables) {""")
f.write_text(t)
p=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/src/pufferl.cu'); t=p.read_text()
rep("""static int g_sched_fold = -1; static const char* g_sched_dump = getenv("PUF_SCHED_DUMP");""",
"""static int g_sched_fold = -1; static const char* g_sched_dump = getenv("PUF_SCHED_DUMP");
static thread_local int g_sched_skipdup = 0; /* scheduler path: the pre-kernel already zeroed terminal rows */""")
rep("""        int state_n = (int)st->shape[0] * n * (int)st->shape[2];
        zero_term_state<<<nh_narrow_grid(grid_size(state_n), false), BLOCK_SIZE, 0, stream>>>(
            *st, env->terminals, 0, sub, n);""",
"""        int state_n = (int)st->shape[0] * n * (int)st->shape[2];
        if (!g_sched_skipdup) zero_term_state<<<nh_narrow_grid(grid_size(state_n), false), BLOCK_SIZE, 0, stream>>>(
            *st, env->terminals, 0, sub, n);""")
rep("""    int R = vec->agents_per_buf, H = p->hypers.horizon; long mask = vec->mask_size; EnvSched* es = vec->sched;
    if (getenv("PUF_SCHED_MOCK_FORWARD")) {""",
"""    int R = vec->agents_per_buf, H = p->hypers.horizon; long mask = vec->mask_size; EnvSched* es = vec->sched;
    int tables_ext = getenv("PUF_SCHED_TABLES") ? atoi(getenv("PUF_SCHED_TABLES")) : 0; long table_epoch = -1;
    g_sched_skipdup = getenv("PUF_SCHED_SKIPDUP") ? atoi(getenv("PUF_SCHED_SKIPDUP")) : 0;
#ifdef PUFFER_NETHACK
    nh_tables_external = tables_ext != 0;
#endif
    if (getenv("PUF_SCHED_MOCK_FORWARD")) {""")
rep("""        double f0 = es_now();
        if (!graph) {""",
"""        double f0 = es_now();
#ifdef PUFFER_NETHACK
        if (tables_ext && table_epoch != (long)p->epoch) { /* vocabulary tables depend only on the weights: once per epoch, outside the graph */
            Policy* pol = &p->policies[0]; Weights* w = (!pol->frozen && p->hypers.async) ? &p->actor_weights : &pol->weights;
            nethack_encoder_refresh_tables(w->encoder, pol->buf_acts[s].encoder, stream); table_epoch = (long)p->epoch;
        }
#endif
        if (!graph) {""")
p.write_text(t); print('B0 applied')
