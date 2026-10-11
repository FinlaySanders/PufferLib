from pathlib import Path
import difflib,hashlib,json
root=Path(__file__).resolve().parent
path=root/'source/src/pufferl.cu'
old=path.read_text();s=old
assert 'PUF_ACTOR_CACHE_MB' not in s
s=s.replace('    Prec actor_param;      // async flat actor params','    cudaAccessPolicyWindow actor_cache;\n    Prec actor_param;      // async flat actor params',1)
helper=r'''
// Startup/capture-only experiment; no changes to model arithmetic or graph ordering.
static int actor_cache_graph(cudaGraph_t graph, cudaAccessPolicyWindow window) {
    if (!window.num_bytes) return 0;
    size_t count = 0;
    assert(cudaGraphGetNodes(graph, NULL, &count) == cudaSuccess);
    cudaGraphNode_t* nodes = (cudaGraphNode_t*)malloc(count * sizeof(cudaGraphNode_t));
    assert(nodes || !count);
    assert(cudaGraphGetNodes(graph, nodes, &count) == cudaSuccess);
    int kernels = 0;
    for (size_t i = 0; i < count; i++) {
        cudaGraphNodeType type;
        assert(cudaGraphNodeGetType(nodes[i], &type) == cudaSuccess);
        if (type == cudaGraphNodeTypeKernel) {
            cudaKernelNodeAttrValue attr = {};
            attr.accessPolicyWindow = window;
            assert(cudaGraphKernelNodeSetAttribute(nodes[i],
                cudaKernelNodeAttributeAccessPolicyWindow, &attr) == cudaSuccess);
            cudaKernelNodeAttrValue got = {};
            assert(cudaGraphKernelNodeGetAttribute(nodes[i],
                cudaKernelNodeAttributeAccessPolicyWindow, &got) == cudaSuccess);
            assert(got.accessPolicyWindow.base_ptr == window.base_ptr);
            assert(got.accessPolicyWindow.num_bytes == window.num_bytes);
            assert(got.accessPolicyWindow.hitRatio == window.hitRatio);
            assert(got.accessPolicyWindow.hitProp == window.hitProp);
            assert(got.accessPolicyWindow.missProp == window.missProp);
            kernels++;
        } else if (type == cudaGraphNodeTypeGraph) {
            cudaGraph_t child;
            assert(cudaGraphChildGraphNodeGetGraph(nodes[i], &child) == cudaSuccess);
            kernels += actor_cache_graph(child, window);
        }
    }
    free(nodes);
    return kernels;
}

'''
marker='void pufferl_forward(PuffeRL* pufferl, int buf, int t, cudaStream_t stream) {'
assert s.count(marker)==1;s=s.replace(marker,helper+marker)
marker='''        assert(cudaGraphInstantiate(&pufferl->rollout_graphs[graph], _graph, 0)'''
assert s.count(marker)==1
s=s.replace(marker,'''        int cache_kernels = actor_cache_graph(_graph, pufferl->actor_cache);
        if (cache_kernels && t == 0 && graph_slot == 0)
            fprintf(stderr, "ACTOR_CACHE_GRAPH buffer=%d kernels=%d\\n", buf, cache_kernels);
'''+marker)
marker='''    pufferl->streams = (cudaStream_t*)calloc(1, num_buffers * sizeof(cudaStream_t));'''
setup=r'''    if (const char* value = getenv("PUF_ACTOR_CACHE_MB")) {
        int requested_mib = atoi(value);
        assert(requested_mib >= 0);
        if (requested_mib) {
            assert(hypers.async);
            int limit = 0, max_window = 0;
            assert(cudaDeviceGetAttribute(&limit, cudaDevAttrMaxPersistingL2CacheSize,
                hypers.gpu_id) == cudaSuccess);
            assert(cudaDeviceGetAttribute(&max_window, cudaDevAttrMaxAccessPolicyWindowSize,
                hypers.gpu_id) == cudaSuccess);
            size_t reserve = (size_t)requested_mib * 1024 * 1024;
            assert(reserve <= (size_t)limit);
            size_t bytes = numel(pufferl->actor_param.shape) * sizeof(precision_t);
            assert(bytes <= (size_t)max_window);
            assert(cudaDeviceSetLimit(cudaLimitPersistingL2CacheSize, reserve) == cudaSuccess);
            size_t actual = 0;
            assert(cudaDeviceGetLimit(&actual, cudaLimitPersistingL2CacheSize) == cudaSuccess);
            pufferl->actor_cache.base_ptr = pufferl->actor_param.data;
            pufferl->actor_cache.num_bytes = bytes;
            pufferl->actor_cache.hitRatio = reserve < bytes ? (float)reserve / bytes : 1.0f;
            pufferl->actor_cache.hitProp = cudaAccessPropertyPersisting;
            pufferl->actor_cache.missProp = cudaAccessPropertyNormal;
            fprintf(stderr, "ACTOR_CACHE requested=%zu actual=%zu bytes=%zu ratio=%.9f\n",
                reserve, actual, bytes, pufferl->actor_cache.hitRatio);
        }
    }
'''
assert s.count(marker)==1;s=s.replace(marker,setup+marker)
marker='''            assert(cudaStreamCreate(&pufferl->streams[i]) == cudaSuccess);
        }
    }

    if (PUF_BACKEND == PUF_GPU)'''
new='''            assert(cudaStreamCreate(&pufferl->streams[i]) == cudaSuccess);
        }
        if (pufferl->actor_cache.num_bytes) {
            cudaStreamAttrValue attr = {};
            attr.accessPolicyWindow = pufferl->actor_cache;
            assert(cudaStreamSetAttribute(pufferl->streams[i],
                cudaStreamAttributeAccessPolicyWindow, &attr) == cudaSuccess);
        }
    }

    if (PUF_BACKEND == PUF_GPU)'''
assert s.count(marker)==1;s=s.replace(marker,new)
path.write_text(s)
(root/'ACTOR_CACHE.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='before/src/pufferl.cu',tofile='after/src/pufferl.cu')))
(root/'ACTOR_CACHE_SOURCE.json').write_text(json.dumps({'sha256':hashlib.sha256(s.encode()).hexdigest(),'docs':'https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/l2-cache-control.html','scope':'Only actor streams/rollout graph kernel nodes; startup set-aside. Default off. Explicit graph-node properties read back.'},indent=2))
for name,jobs in [('ACTOR_CACHE_SMOKE',[(0,'base'),(32,'32')]),('ACTOR_CACHE_FULL',[(0,'base_a'),(16,'16'),(32,'32'),(0,'base_b')])]:
 rows=[]
 for mb,label in jobs:
  rows.append({'kind':'full','label':name.lower()+'_'+label,'binary':'actor_cache_v19','env':{'PUF_CUDA_WAIT':'block','PUF_ACTOR_CACHE_MB':mb},'args':['--epochs=4','--start=1'] if 'SMOKE' in name else ['--epochs=80','--start=64']})
 (root/(name+'.json')).write_text(json.dumps(rows,indent=2))
print('Prepared isolated cache experiment; not built or run')
