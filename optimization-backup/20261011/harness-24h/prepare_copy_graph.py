from pathlib import Path
import difflib, hashlib, json
r=Path(__file__).resolve().parent
p=r/'source/src/pufferl.cu';old=p.read_text();s=old
assert 'PUF_COPY_GRAPH' not in s
needle='''void pufferl_forward(PuffeRL* pufferl, int buf, int t, cudaStream_t stream) {
    Hypers* hypers = &pufferl->hypers;'''
replacement=needle+'''
    static thread_local int copy_graph = -1;
    if (copy_graph < 0)
        copy_graph = getenv("PUF_COPY_GRAPH") ? atoi(getenv("PUF_COPY_GRAPH")) : 0;
    assert(copy_graph >= 0 && copy_graph <= 2);
    bool graph_download = copy_graph == 2 && PUF_BACKEND == PUF_CPU;'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
needle='    bool step_graph = hypers->cudagraphs && pufferl->rollout_graphs != NULL;'
s=s.replace(needle,needle+'\n    assert(!graph_download || step_graph);',1)
needle='''    pufferl_forward_step(pufferl, buf, t, stream);
    if (step_graph) {'''
replacement='''    pufferl_forward_step(pufferl, buf, t, stream);
    if (graph_download) {
        int n = pufferl->vec->agents_per_buf;
        int start = buf * n;
        assert(cudaMemcpyAsync(pufferl->vec->actions + (size_t)start * NUM_ATNS,
            pufferl->env.actions.data + (size_t)start * NUM_ATNS,
            (size_t)n * NUM_ATNS * sizeof(float), cudaMemcpyDeviceToHost, stream)
            == cudaSuccess);
    }
    if (step_graph) {'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
needle='''    int timing_round=0;
    __atomic_store_n(state, BUF_WAITING, __ATOMIC_SEQ_CST);'''
replacement='''    int copy_graph = getenv("PUF_COPY_GRAPH") ? atoi(getenv("PUF_COPY_GRAPH")) : 0;
    assert(copy_graph >= 0 && copy_graph <= 2);
    cudaGraphExec_t upload_graph = NULL;
    int timing_round=0;
    __atomic_store_n(state, BUF_WAITING, __ATOMIC_SEQ_CST);'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
needle='''                if(perf_record) fclose(perf_record);
                return NULL;'''
s=s.replace(needle,'''                if (upload_graph) cudaGraphExecDestroy(upload_graph);
'''+needle,1)
needle='''        if (__atomic_load_n(&vec->shutdown, __ATOMIC_SEQ_CST)) {
            for (int i = 0; i < NUM_EV; i++) {'''
s=s.replace(needle,'''        if (__atomic_load_n(&vec->shutdown, __ATOMIC_SEQ_CST)) {
            if (upload_graph) cudaGraphExecDestroy(upload_graph);
            for (int i = 0; i < NUM_EV; i++) {''',1)
needle='''            cudaMemcpyAsync(
                &vec->actions[agent_start * NUM_ATNS],'''
s=s.replace(needle,'''            if (copy_graph != 2) cudaMemcpyAsync(
                &vec->actions[agent_start * NUM_ATNS],''',1)
needle='''            cpu_upload(pufferl, agent_start, apb, stream);
            if(timing_sample) cudaEventRecord(ev[H2D_END], stream);'''
replacement='''            if (copy_graph) {
                if (!upload_graph) {
                    assert(cudaStreamBeginCapture(stream, cudaStreamCaptureModeThreadLocal)
                        == cudaSuccess);
                    cpu_upload(pufferl, agent_start, apb, stream);
                    cudaGraph_t graph;
                    assert(cudaStreamEndCapture(stream, &graph) == cudaSuccess);
                    assert(cudaGraphInstantiate(&upload_graph, graph, 0) == cudaSuccess);
                    assert(cudaGraphDestroy(graph) == cudaSuccess);
                }
                assert(cudaGraphLaunch(upload_graph, stream) == cudaSuccess);
            } else {
                cpu_upload(pufferl, agent_start, apb, stream);
            }
            if(timing_sample) cudaEventRecord(ev[H2D_END], stream);'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
p.write_text(s)
(r/'COPY_GRAPH.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='before/src/pufferl.cu',tofile='after/src/pufferl.cu')))
(r/'COPY_GRAPH_SOURCE.json').write_text(json.dumps(dict(hypothesis='Four per-step H2D calls and one D2H call remain outside inference graphs. Capture fixed-address uploads as one reusable graph; optionally include action D2H in inference graph to reduce host submissions.',method='Mode1 captures four uploads at original position; mode2 additionally moves action download inside inference graph before archive kernel. Sync remains after both. Initial env_restart upload and final-horizon uploads remain unchanged. No math or buffer layout changes.',evidence='Current full per-buffer completion~1230ms vs env~948,model~109,copy~69 leaves~104ms not covered by those stage timers. Includes host submission/wakeup/bookkeeping, so only a ceiling, not attribution. Node trace shows substantial CPU API submission but is perturbed; timing-stride reduction was previously null.',caveats=['Mode2 model timing includes action D2H; model/copy phase labels cannot be compared directly to control.','Archive and D2H order reverses, but sources independent and same final stream synchronization protects both before CPU action consumption.','Full sampling/live-update proof required if retained.'],sha256=hashlib.sha256(s.encode()).hexdigest()),indent=2))
base=json.loads((r/'POOL_TIMING_FULL.json').read_text())[0]['env']
jobs=[]
for name,extra in [('base_a',{}),('upload',{'PUF_COPY_GRAPH':1}),('both',{'PUF_COPY_GRAPH':2}),('base_b',{})]:
 jobs.append(dict(kind='full',label='copy_graph_'+name,binary='copy_graph_v25',env=dict(base,**extra),args=['--epochs=80','--start=64']))
(r/'COPY_GRAPH_FULL.json').write_text(json.dumps(jobs,indent=2))
(r/'COPY_GRAPH_SMOKE.json').write_text(json.dumps([dict(j,label=j['label']+'_smoke',args=['--epochs=4','--start=1']) for j in jobs[:3]],indent=2))
print('copy graph prepared, not built')
