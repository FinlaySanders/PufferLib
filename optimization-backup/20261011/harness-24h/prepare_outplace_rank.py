from pathlib import Path
import difflib,json,hashlib
r=Path(__file__).resolve().parent;p=r/'source/src/algo.cu';old=p.read_text()
a='''    cublasLtMatmulHeuristicResult_t result;int count=0;
    assert(cublasLtMatmulAlgoGetHeuristic(outplace_handle,p.desc,p.a,p.b,p.c,p.c,pref,1,&result,&count)==CUBLAS_STATUS_SUCCESS && count==1);
    p.algo=result.algo;cublasLtMatmulPreferenceDestroy(pref);outplace_plans.push_back(p);return outplace_plans.back();'''
b='''    const char* rank_env = getenv("PUF_OUTPLACE_RANK");
    cublasLtMatmulHeuristicResult_t results[4]; int count = 0;
    int requested = rank_env ? 4 : 1;
    assert(cublasLtMatmulAlgoGetHeuristic(outplace_handle,p.desc,p.a,p.b,p.c,p.c,pref,requested,results,&count)==CUBLAS_STATUS_SUCCESS && count>0);
    int rank = rank_env ? atoi(rank_env) : 0;
    assert(rank >= 0 && rank < 4);
    if (rank >= count) rank = 0;
    assert(results[rank].state == CUBLAS_STATUS_SUCCESS);
    p.algo = results[rank].algo;
    if (rank_env) fprintf(stderr,"OUTPLACE_RANK M=%d N=%d K=%d requested=%s selected=%d choices=%d workspace=%zu\\n",M,N,K,rank_env,rank,count,results[rank].workspaceSize);
    cublasLtMatmulPreferenceDestroy(pref);outplace_plans.push_back(p);return outplace_plans.back();'''
assert old.count(a)==1;s=old.replace(a,b)
p.write_text(s)
(r/'OUTPLACE_RANK.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='before/algo.cu',tofile='after/algo.cu')))
(r/'OUTPLACE_RANK_SOURCE.json').write_text(json.dumps(dict(before=hashlib.sha256(old.encode()).hexdigest(),after=hashlib.sha256(s.encode()).hexdigest(),hypothesis='Alternate heuristics previously showed speed but failed old exactness gate; current goal permits quantified equivalent rounding; test current4MiB4stream setup',same_precision_and_compute_type=True,default_path_unchanged=True,status='Prepared not compiled'),indent=2))
jobs=[]
for label,env in [('base_a',{}),('rank0',{'PUF_OUTPLACE':1,'PUF_OUTPLACE_RANK':0}),('rank1',{'PUF_OUTPLACE':1,'PUF_OUTPLACE_RANK':1}),('rank2',{'PUF_OUTPLACE':1,'PUF_OUTPLACE_RANK':2}),('rank3',{'PUF_OUTPLACE':1,'PUF_OUTPLACE_RANK':3}),('base_b',{})]:
 jobs.append(dict(kind='time',label='outplace_rank_'+label,binary='outplace_rank_v18',env=dict(PUF_CUDA_WAIT='block',**env),args=['--trials=4']))
(r/'OUTPLACE_RANK_SCREEN.json').write_text(json.dumps(jobs,indent=2))
print('Prepared alternate rank screen; no build or timing yet.')
