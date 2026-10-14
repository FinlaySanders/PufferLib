#ifndef NH_ENV_TURN
#ifdef PUFFER_NETHACK
#define NH_ENV_TURN(e) ((long)(e)->blstats[NLE_BL_TIME])
#define NH_ENV_DEPTH(e) ((long)(e)->blstats[NLE_BL_DEPTH])
#else
#define NH_ENV_TURN(e) 0L
#define NH_ENV_DEPTH(e) 0L
#endif
#endif

// Isolated benchmark: one genuine saved rollout, full PPO graph, no environment work.
struct PipelineBlock {
    const char* name;
    void* device;
    size_t bytes;
    bool restore;
};

static int pipeline_blocks(PuffeRL* p, RolloutBuf& src, PipelineBlock* blocks) {
    int n = 0;
#define PIPE_FIELD(field) blocks[n++] = {#field, src.field.data, \
    (size_t)numel(src.field.shape) * sizeof(*src.field.data), false}
    PIPE_FIELD(observations); PIPE_FIELD(actions); PIPE_FIELD(values);
    PIPE_FIELD(logprobs); PIPE_FIELD(rewards); PIPE_FIELD(terminals);
    PIPE_FIELD(action_mask); PIPE_FIELD(initial_states);
#undef PIPE_FIELD
    Policy* policy = &p->policies[0];
    blocks[n++] = {"params", policy->param.data, (size_t)numel(policy->param.shape) * sizeof(precision_t), true};
    blocks[n++] = {"master", policy->master_weights.data, (size_t)numel(policy->master_weights.shape) * sizeof(float), true};
    blocks[n++] = {"momentum", p->muon.mb.data, (size_t)numel(p->muon.mb.shape) * sizeof(float), true};
    blocks[n++] = {"updates", p->grad.data, (size_t)numel(p->grad.shape) * sizeof(precision_t), true};
    return n;
}

static void pipeline_file(FILE* file, void* device, size_t bytes, bool write) {
    void* host = malloc(bytes); assert(host);
    if (write) {
        assert(cudaMemcpy(host, device, bytes, cudaMemcpyDeviceToHost) == cudaSuccess);
        assert(fwrite(host, 1, bytes, file) == bytes);
    } else {
        assert(fread(host, 1, bytes, file) == bytes);
        assert(cudaMemcpy(device, host, bytes, cudaMemcpyHostToDevice) == cudaSuccess);
    }
    free(host);
}

static void pipeline_dump(PuffeRL* p, RolloutBuf src, int slot, long epoch) {
    assert(cudaDeviceSynchronize() == cudaSuccess);
    PipelineBlock blocks[16]; int n = pipeline_blocks(p, src, blocks);
    FILE* file = fopen(getenv("NH_PIPELINE_DUMP"), "wb"); assert(file);
    uint64_t header[] = {0x4e48504950453031ULL, (uint64_t)p->hypers.total_agents,
        (uint64_t)p->hypers.horizon, (uint64_t)slot, (uint64_t)epoch, (uint64_t)n};
    assert(fwrite(header, sizeof(header), 1, file) == 1);
    for (int i = 0; i < n; i++) {
        uint64_t bytes = blocks[i].bytes;
        assert(fwrite(&bytes, sizeof(bytes), 1, file) == 1);
        pipeline_file(file, blocks[i].device, bytes, true);
    }
    fclose(file);
    long sum = 0, over = 0;
    for (int i = 0; i < p->vec->size; i++) {
        long turn = NH_ENV_TURN(&p->vec->envs[i]); sum += turn; over += turn >= 10000;
    }
    fprintf(stderr, "PIPELINE_SAVED epoch=%ld mean_turn=%.3f over10k=%ld agents=%d slot=%d\n",
        epoch, (double)sum / p->vec->size, over, p->vec->size, slot);
}


static void encoder_benchmark(PuffeRL* p, RolloutBuf src) {
    Policy* pol = &p->policies[0];
    int B = p->hypers.total_agents / p->hypers.num_buffers;
    Prec input = puf_slice(src.observations, 0, 0, B);
    cudaStream_t stream = p->train_stream;
    assert(cudaDeviceSynchronize() == cudaSuccess);
    cudaGraph_t graph;
    cudaGraphExec_t executable;
    assert(cudaStreamBeginCapture(stream,cudaStreamCaptureModeThreadLocal) == cudaSuccess);
    Prec output;
    bool inference = getenv("NH_INFERENCE_BENCH") != NULL;
    if(inference) {
        Prec st=pol->buffer_states[0];
        Prec saved=init_slot(src.initial_states,p->async_ready_slot);
        int H=st.shape[2];
        for(int l=0;l<st.shape[0];l++)
            assert(cudaMemcpyAsync(st.data+(long)l*B*H,saved.data+(long)l*saved.shape[1]*H,
                (size_t)B*H*sizeof(precision_t),cudaMemcpyDeviceToDevice,stream)==cudaSuccess);
        output=arch_forward(&pol->arch,pol->weights,pol->buf_acts[0],input,st,stream);
    } else {
        output=pol->arch.encoder.forward(pol->weights.encoder,pol->buf_acts[0].encoder,input,stream);
    }
    assert(cudaStreamEndCapture(stream,&graph) == cudaSuccess);
    assert(cudaGraphInstantiate(&executable,graph,0) == cudaSuccess);
    cudaGraphDestroy(graph);
    cudaEvent_t begin,end;
    cudaEventCreate(&begin);cudaEventCreate(&end);
    int repeats=256;
    int trials=getenv("NH_PIPELINE_TRIALS")?atoi(getenv("NH_PIPELINE_TRIALS")):10;
    fprintf(stderr,"ENCODER_BENCH B=%d repeats=%d output_elements=%ld full_inference=%d\n",B,repeats,numel(output.shape),inference);
    for(int trial=-2;trial<trials;trial++) {
        assert(cudaEventRecord(begin,stream) == cudaSuccess);
        for(int i=0;i<repeats;i++) assert(cudaGraphLaunch(executable,stream) == cudaSuccess);
        assert(cudaEventRecord(end,stream) == cudaSuccess);
        assert(cudaEventSynchronize(end) == cudaSuccess);
        float ms;
        assert(cudaEventElapsedTime(&ms,begin,end) == cudaSuccess);
        fprintf(stderr,"PIPELINE_TRIAL trial=%d milliseconds=%.9f model_ms=%.9f\n",trial,ms/repeats,ms/repeats);
    }
    if(const char* path=getenv("NH_ENCODER_OUTPUT")) {
        FILE* f=fopen(path,"wb");assert(f);
        pipeline_file(f,output.data,numel(output.shape)*sizeof(precision_t),true);
        fclose(f);
    }
    fprintf(stderr,"PIPELINE_COMPLETE mode=encoder_only inference=1 updating=0\n");
    exit(0);
}

static void pipeline_benchmark(PuffeRL* p) {
    FILE* file = fopen(getenv("NH_PIPELINE_LOAD"), "rb"); assert(file);
    uint64_t header[6]; assert(fread(header, sizeof(header), 1, file) == 1);
    assert(header[0] == 0x4e48504950453031ULL);
    assert(header[1] == p->hypers.total_agents && header[2] == p->hypers.horizon);
    int slot = (int)header[3]; long epoch = (long)header[4];
    p->async_ready_slot = slot; p->epoch = epoch;
    RolloutBuf src = rollout_time_view(&p->rollouts, slot * p->hypers.horizon, p->hypers.horizon);
    PipelineBlock blocks[16]; int n = pipeline_blocks(p, src, blocks);
    assert(header[5] == n);
    void* saved[16] = {};
    for (int i = 0; i < n; i++) {
        uint64_t bytes; assert(fread(&bytes, sizeof(bytes), 1, file) == 1);
        assert(bytes == blocks[i].bytes);
        pipeline_file(file, blocks[i].device, bytes, false);
        if (blocks[i].restore) {
            assert(cudaMalloc(&saved[i], bytes) == cudaSuccess);
            assert(cudaMemcpy(saved[i], blocks[i].device, bytes, cudaMemcpyDeviceToDevice) == cudaSuccess);
        }
    }
    assert(fgetc(file) == EOF); fclose(file);
    if(getenv("NH_ENCODER_BENCH")) encoder_benchmark(p,src);
    bool proof = getenv("NH_PIPELINE_PROOF") != NULL;
    if (proof) assert(cudaMalloc(&pipeline_raw_grads, 2 * numel(p->grad.shape) * sizeof(precision_t)) == cudaSuccess);
    int trials = getenv("NH_PIPELINE_TRIALS") ? atoi(getenv("NH_PIPELINE_TRIALS")) : 10;
    int warm = proof ? 0 : 2;
    if (proof) trials = 1;
    for (int trial = -warm; trial < trials; trial++) {
        for (int i = 0; i < n; i++) if (saved[i])
            assert(cudaMemcpyAsync(blocks[i].device, saved[i], blocks[i].bytes,
                cudaMemcpyDeviceToDevice, p->train_stream) == cudaSuccess);
        if (p->perf_frozen) {
            assert(cudaMemcpyAsync(p->perf_shadow_master.data, p->policies[0].master_weights.data,
                numel(p->policies[0].master_weights.shape) * sizeof(float), cudaMemcpyDeviceToDevice, p->train_stream) == cudaSuccess);
            assert(cudaMemcpyAsync(p->perf_shadow_param.data, p->policies[0].param.data,
                numel(p->policies[0].param.shape) * sizeof(precision_t), cudaMemcpyDeviceToDevice, p->train_stream) == cudaSuccess);
        }
        p->epoch = epoch;
        train_impl(p, &src);
        muon_profile_report(&p->muon, trial);
        unsigned long long stamps[NUM_TE];
        assert(cudaMemcpy(stamps, p->profile.stamps + slot * NUM_TE, sizeof(stamps), cudaMemcpyDeviceToHost) == cudaSuccess);
        assert(cudaGetLastError() == cudaSuccess);
        fprintf(stderr, "PIPELINE_TRIAL trial=%d milliseconds=%.6f model_ms=%.6f\n",
            trial, (stamps[TE_E]-stamps[TE_S])*1e-6, (stamps[TE_E]-stamps[TE_MID])*1e-6);
    }
    if (proof) {
        for (int i = 0; i < n; i++) if (blocks[i].restore) {
            char path[4096]; snprintf(path, sizeof(path), "%s/%s.bin", getenv("NH_PIPELINE_PROOF"), blocks[i].name);
            FILE* out = fopen(path, "wb"); assert(out);
            pipeline_file(out, blocks[i].device, blocks[i].bytes, true); fclose(out);
        }
        char path[4096]; snprintf(path, sizeof(path), "%s/raw_gradients.bin", getenv("NH_PIPELINE_PROOF"));
        FILE* out = fopen(path, "wb"); assert(out);
        pipeline_file(out, pipeline_raw_grads, 2 * numel(p->grad.shape) * sizeof(precision_t), true); fclose(out);
    }
    fprintf(stderr, "PIPELINE_COMPLETE mode=%s proof=%d frozen=%d\n", getenv("NH_GRAD_PIPELINE"), proof, p->perf_frozen);
    exit(0);
}
