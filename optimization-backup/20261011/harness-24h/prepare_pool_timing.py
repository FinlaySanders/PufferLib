from pathlib import Path
import difflib,hashlib,json
r=Path(__file__).resolve().parent
patches=[]
p=r/'source/src/env_pool.h';old=p.read_text();s=old
s=s.replace('#include <sched.h>','#include <sched.h>\n#include <time.h>\n#include <string.h>',1)
needle='typedef struct EnvPool EnvPool;'
replacement='''typedef struct {
    double claim_wall, tail_wall, drain_wall;
    double claim_cpu, tail_cpu, drain_cpu;
    unsigned long samples;
    char padding[8];
} EPTiming;

static void ep_clocks(double* wall, double* cpu) {
    struct timespec w, c;
    clock_gettime(CLOCK_MONOTONIC, &w);
    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &c);
    *wall = w.tv_sec + w.tv_nsec * 1e-9;
    *cpu = c.tv_sec + c.tv_nsec * 1e-9;
}

typedef struct EnvPool EnvPool;'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
s=s.replace('    EPRegion* region;','    EPRegion* region;\n    EPTiming* timing;',1)
needle='    p->workers = workers; p->buffers = buffers; p->step = step; p->context = context;'
replacement=needle+'''
    if (getenv("PUF_POOL_TIMING")) {
        assert(sizeof(EPTiming) == 64);
        assert(posix_memalign((void**)&p->timing, 64, buffers * sizeof(EPTiming)) == 0);
        memset(p->timing, 0, buffers * sizeof(EPTiming));
    }'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
needle='''    EPRegion* r = &p->region[buffer];
    pthread_mutex_lock(&r->mu);'''
replacement='''    EPRegion* r = &p->region[buffer];
    double w0=0, w1=0, w2=0, w3=0, c0=0, c1=0, c2=0, c3=0;
    if (p->timing) ep_clocks(&w0, &c0);
    pthread_mutex_lock(&r->mu);'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
needle='''    ep_claim(p, r, buffer % p->workers);
    nvtxRangePop();'''
assert s.count(needle)==1;s=s.replace(needle,needle+'\n    if (p->timing) ep_clocks(&w1, &c1);')
needle='''    nvtxRangePop();
    pthread_mutex_lock(&r->mu);
    r->active = 0;'''
replacement='''    nvtxRangePop();
    if (p->timing) ep_clocks(&w2, &c2);
    pthread_mutex_lock(&r->mu);
    r->active = 0;'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
needle='''    pthread_mutex_unlock(&r->mu);
}

/* Submitters must be joined'''
replacement='''    pthread_mutex_unlock(&r->mu);
    if (p->timing) {
        ep_clocks(&w3, &c3);
        EPTiming* t = &p->timing[buffer];
        t->claim_wall += w1-w0; t->tail_wall += w2-w1; t->drain_wall += w3-w2;
        t->claim_cpu += c1-c0; t->tail_cpu += c2-c1; t->drain_cpu += c3-c2;
        t->samples++;
    }
}

/* Submitters must be joined'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
s=s.replace('free(p->region); free(p->threads); free(p->args); free(p);','free(p->timing); free(p->region); free(p->threads); free(p->args); free(p);',1)
p.write_text(s)
patches.extend(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='before/src/env_pool.h',tofile='after/src/env_pool.h'))
p=r/'source/src/pufferl.cu';old=p.read_text();s=old
needle='''        memset(src, 0, NUM_PROF * sizeof(float));
    }
    p->profile.accum[PROF_MODEL]'''
replacement='''        memset(src, 0, NUM_PROF * sizeof(float));
#ifdef PUF_ENV_POOL
        if (p->vec->env_pool->timing) {
            EPTiming* timing = &p->vec->env_pool->timing[buf];
            if (p->epoch >= 64)
                fprintf(stderr, "POOL_TIMING epoch=%ld buffer=%d samples=%lu claim_wall_ms=%.6f tail_wall_ms=%.6f drain_wall_ms=%.6f claim_cpu_ms=%.6f tail_cpu_ms=%.6f drain_cpu_ms=%.6f\\n",
                    p->epoch, buf, timing->samples, 1000*timing->claim_wall,
                    1000*timing->tail_wall, 1000*timing->drain_wall,
                    1000*timing->claim_cpu, 1000*timing->tail_cpu, 1000*timing->drain_cpu);
            memset(timing, 0, sizeof(*timing));
        }
#endif
    }
    p->profile.accum[PROF_MODEL]'''
assert s.count(needle)==1;s=s.replace(needle,replacement);p.write_text(s)
patches.extend(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='before/src/pufferl.cu',tofile='after/src/pufferl.cu'))
(r/'POOL_TIMING.patch').write_text(''.join(patches))
(r/'POOL_TIMING_SOURCE.json').write_text(json.dumps(dict(
    hypothesis='Node-traced32workerpooltail1.93ms vsolder24worker0.376ms may be tracing/schedulingartifact. Measure unprofiled poolpublication+claim/tail/readers-drain walland submitterCPU durations before a cost-ordering candidate.',
    method='Four clock pairs per512-game ep_run, eachbuffer hascache-linealigned64B counters andonewriter. Reset/read onlyafterallcollectorswaiting. Noengine, action, batching, synchronizationsemanticschanges. Defaultoff; benchmark pertubationwithmatchedtimingoffcontrols.',
    source_hashes={name:hashlib.sha256((r/'source'/name).read_bytes()).hexdigest() for name in ['src/pufferl.cu','src/env_pool.h']}),indent=2))
base=json.loads((r/'FOCUS_FAST32.json').read_text())[0]['env'];base['PUF_ROLLOUT_DETAIL']='1'
jobs=[]
for name,extra in [('base_a',{}),('timing',{'PUF_POOL_TIMING':1}),('base_b',{})]:
 jobs.append(dict(kind='full',label='pool_timing_'+name,binary='pool_timing_v23',env=dict(base,**extra),args=['--epochs=80','--start=64']))
(r/'POOL_TIMING_FULL.json').write_text(json.dumps(jobs,indent=2))
print('pool timing diagnostic prepared, not built')
