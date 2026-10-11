from pathlib import Path
import difflib

root = Path(__file__).resolve().parent
p = root/'source/src/pipeline_bench.cuh'
before = p.read_text()
helper = r'''
static void encoder_benchmark(PuffeRL* p, RolloutBuf src) {
    Policy* pol = &p->policies[0];
    int B = p->hypers.total_agents / p->hypers.num_buffers;
    Prec input = puf_slice(src.observations, 0, 0, B);
    cudaStream_t stream = p->train_stream;
    assert(cudaDeviceSynchronize() == cudaSuccess);
    cudaGraph_t graph;
    cudaGraphExec_t executable;
    assert(cudaStreamBeginCapture(stream,cudaStreamCaptureModeThreadLocal) == cudaSuccess);
    Prec output = pol->arch.encoder.forward(pol->weights.encoder,pol->buf_acts[0].encoder,input,stream);
    assert(cudaStreamEndCapture(stream,&graph) == cudaSuccess);
    assert(cudaGraphInstantiate(&executable,graph,0) == cudaSuccess);
    cudaGraphDestroy(graph);
    cudaEvent_t begin,end;
    cudaEventCreate(&begin);cudaEventCreate(&end);
    int repeats=256;
    int trials=getenv("NH_PIPELINE_TRIALS")?atoi(getenv("NH_PIPELINE_TRIALS")):10;
    fprintf(stderr,"ENCODER_BENCH B=%d repeats=%d output_elements=%ld\n",B,repeats,numel(output.shape));
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

'''
anchor='static void pipeline_benchmark(PuffeRL* p) {'
assert before.count(anchor)==1
s=before.replace(anchor,helper+anchor)
anchor='    assert(fgetc(file) == EOF); fclose(file);'
assert s.count(anchor)==1
s=s.replace(anchor,anchor+'\n    if(getenv("NH_ENCODER_BENCH")) encoder_benchmark(p,src);')
p.write_text(s)
(root/'encoder_bench.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/src/pipeline_bench.cuh',tofile='b/src/pipeline_bench.cuh')))
p=root/'run.py';s=p.read_text()
s=s.replace("['capture', 'proof', 'time', 'full']", "['capture', 'proof', 'time', 'full', 'encoder']")
s=s.replace("['proof', 'time']", "['proof', 'time', 'encoder']")
anchor="if args.kind == 'capture':"
assert s.count(anchor)==2
s=s.replace(anchor,"""if args.kind == 'encoder':
    environment.update(NH_ENCODER_BENCH='1',NH_ENCODER_OUTPUT=str(directory/'encoder.bin'))
if args.kind == 'capture':""",1)
p.write_text(s)
