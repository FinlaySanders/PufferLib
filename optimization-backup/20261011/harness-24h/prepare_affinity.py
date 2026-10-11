from pathlib import Path
import json
r=Path(__file__).resolve().parent
p=r/'source/src/env_pool.h';s=p.read_text()
needle='static void* ep_worker(void* arg) {'
helper='''/* Experimental placement for this 8P+16E host. Startup only. */
static void ep_pin_cpu(int cpu) {
    cpu_set_t allowed, selected;
    assert(pthread_getaffinity_np(pthread_self(), sizeof(allowed), &allowed) == 0);
    assert(CPU_ISSET(cpu, &allowed));
    CPU_ZERO(&selected); CPU_SET(cpu, &selected);
    assert(pthread_setaffinity_np(pthread_self(), sizeof(selected), &selected) == 0);
}

'''
assert s.count(needle)==1;s=s.replace(needle,helper+needle)
needle='    EnvPool* p = w->pool;\n'
assert s.count(needle)==1
s=s.replace(needle,needle+'''    const char* affinity = getenv("PUF_CPU_AFFINITY");
    if (affinity && atoi(affinity) == 1) {
        assert(p->workers == 24);
        ep_pin_cpu(w->id < 8 ? 2*w->id : 16+w->id-8);
    }
''')
p.write_text(s)
p=r/'source/src/pufferl.cu';s=p.read_text()
needle='    int buf = a->buf;\n'
assert s.count(needle)==1
s=s.replace(needle,needle+'''#ifdef PUF_ENV_POOL
    if (getenv("PUF_CPU_AFFINITY")) {
        assert(vec->buffers == 4);
        ep_pin_cpu(2*buf+1);
    }
#endif
''')
needle='''        while (__atomic_load_n(state, __ATOMIC_SEQ_CST) != BUF_WAITING) {}
    }
}

static void rollout_start(PuffeRL* p)'''
assert s.count(needle)==1
s=s.replace(needle,'''        while (__atomic_load_n(state, __ATOMIC_SEQ_CST) != BUF_WAITING) {}
    }
#ifdef PUF_ENV_POOL
    if (getenv("PUF_CPU_AFFINITY")) ep_pin_cpu(9);
#endif
}

static void rollout_start(PuffeRL* p)''')
p.write_text(s)
job=lambda label,env:dict(kind='full',label=label,binary='affinity_v12',env=dict(PUF_CUDA_WAIT='block',PUF_ROLLOUT_DETAIL=1,**env),args=['--epochs=80','--start=64'])
x=[job('affinity_base_a',{}),job('affinity_all',{'PUF_CPU_AFFINITY':1}),job('affinity_submit',{'PUF_CPU_AFFINITY':2}),job('affinity_all_reduce',{'PUF_CPU_AFFINITY':1,'NH_EMBED_REDUCE':7}),job('affinity_base_b',{})]
(r/'AFFINITY_SCREEN.json').write_text(json.dumps(x,indent=2))
with (r/'LEDGER.md').open('a') as f:
 f.write('\nGoal continuation: preceding prompt-only reply made no experimental progress. Re-read objective and verified campaign PID2896611 and benchmark2896874 live. Identity full result is neutral so far; cohort128 slower. Thread-local initial-exec is already enabled in the current engine, so no TLS candidate is warranted.\n\n16. CPU placement: native replay uses explicit24worker placement, but full pipeline currently lets all workers/submitters migrate. On this8P+16E host, prepare PUF_CPU_AFFINITY=1 to pin24workers to8P+16E, four submitters to P siblings1/3/5/7 and main to9. Mode2 pins main+submitters only. Hypothesis: more predictable CPU/GPU submission and game working-set residency, without fixed game ownership or changing parallelism. Configuration-specific scheduling experiment; no gain claim. Same2048envs/24workers/4buffers. Assertions check CPU availability; isolated source only. Do not compile until active timings finish.\n')
print('Prepared affinity candidate and serial timing spec; no build or run.')
