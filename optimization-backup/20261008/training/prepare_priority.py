from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/pufferl.cu';s=p.read_text()
s=s.replace('''        assert(cudaStreamCreateWithFlags(
            &pufferl->train_stream, cudaStreamNonBlocking) == cudaSuccess);''','''#ifdef PUF_STREAM_PRIORITY
        int least=0,greatest=0;cudaDeviceGetStreamPriorityRange(&least,&greatest);
        const char* pr=getenv("PUF_LOOP_PRIORITY");
        assert(cudaStreamCreateWithPriority(&pufferl->train_stream,cudaStreamNonBlocking,
            pr && !strcmp(pr,"train") ? greatest : least)==cudaSuccess);
#else
        assert(cudaStreamCreateWithFlags(
            &pufferl->train_stream, cudaStreamNonBlocking) == cudaSuccess);
#endif''')
s=s.replace('''            assert(cudaStreamCreateWithFlags(
                &pufferl->streams[i], cudaStreamNonBlocking) == cudaSuccess);''','''#ifdef PUF_STREAM_PRIORITY
            int least=0,greatest=0;cudaDeviceGetStreamPriorityRange(&least,&greatest);
            const char* pr=getenv("PUF_LOOP_PRIORITY");
            assert(cudaStreamCreateWithPriority(&pufferl->streams[i],cudaStreamNonBlocking,
                pr && !strcmp(pr,"rollout") ? greatest : least)==cudaSuccess);
#else
            assert(cudaStreamCreateWithFlags(
                &pufferl->streams[i], cudaStreamNonBlocking) == cudaSuccess);
#endif''');p.write_text(s)
p=r/'source/src/algo.cu';s=p.read_text();a='    cudaStreamCreateWithFlags(&g_dw_stream, cudaStreamNonBlocking);';b='''#ifdef PUF_STREAM_PRIORITY
    int least=0,greatest=0;cudaDeviceGetStreamPriorityRange(&least,&greatest);
    const char* pr=getenv("PUF_LOOP_PRIORITY");
    assert(cudaStreamCreateWithPriority(&g_dw_stream,cudaStreamNonBlocking,
        pr && !strcmp(pr,"train") ? greatest : least)==cudaSuccess);
#else
'''+a+'''
#endif''';assert a in s;s=s.replace(a,b);p.write_text(s)
p=r/'bench.py';s=p.read_text();s=s.replace("if not update:base['PUF_PERF_FREEZE']='1'","base.update(dict(x[6:].split('=',1) for x in sys.argv if x.startswith('--env=')))\nif not update:base['PUF_PERF_FREEZE']='1'");(r/'bench_extra.py').write_text(s)
