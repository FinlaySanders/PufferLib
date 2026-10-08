from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/algo.cu';s=p.read_text()
a='''    cublasLtMatmulHeuristicResult_t result;int count=0;
    assert(cublasLtMatmulAlgoGetHeuristic(outplace_handle,p.desc,p.a,p.b,p.c,p.c,pref,1,&result,&count)==CUBLAS_STATUS_SUCCESS && count==1);
    p.algo=result.algo;cublasLtMatmulPreferenceDestroy(pref);outplace_plans.push_back(p);return outplace_plans.back();'''
b='''#ifdef PUF_LT_CHOICE
    cublasLtMatmulHeuristicResult_t results[4];int count=0;
    assert(cublasLtMatmulAlgoGetHeuristic(outplace_handle,p.desc,p.a,p.b,p.c,p.c,pref,4,results,&count)==CUBLAS_STATUS_SUCCESS && count>0);
    int rank=getenv("PUF_LT_RANK")?atoi(getenv("PUF_LT_RANK")):0;
    if(rank>=count)rank=0;assert(rank>=0);p.algo=results[rank].algo;
    fprintf(stderr,"LT_CHOICE M=%d N=%d K=%d rank=%d choices=%d\\n",M,N,K,rank,count);
#else
    cublasLtMatmulHeuristicResult_t result;int count=0;
    assert(cublasLtMatmulAlgoGetHeuristic(outplace_handle,p.desc,p.a,p.b,p.c,p.c,pref,1,&result,&count)==CUBLAS_STATUS_SUCCESS && count==1);
    p.algo=result.algo;
#endif
    cublasLtMatmulPreferenceDestroy(pref);outplace_plans.push_back(p);return outplace_plans.back();'''
assert a in s;s=s.replace(a,b,1);p.write_text(s)
