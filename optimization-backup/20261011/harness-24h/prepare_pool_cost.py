from pathlib import Path
import difflib, hashlib, json
r=Path(__file__).resolve().parent
p=r/'source/src/env_pool.h'; old=p.read_text(); s=old
assert 'PUF_POOL_COST' not in s
s=s.replace('typedef struct {\n    pthread_mutex_t mu;', '''typedef struct {
    double cost;
    int offset;
} EPTaskCost;

static double ep_task_clock() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static int ep_cost_compare(const void* a, const void* b) {
    const EPTaskCost* x = (const EPTaskCost*)a;
    const EPTaskCost* y = (const EPTaskCost*)b;
    if (x->cost != y->cost) return x->cost > y->cost ? -1 : 1;
    return (x->offset > y->offset) - (x->offset < y->offset);
}

typedef struct {
    pthread_mutex_t mu;''',1)
s=s.replace('    int* next;\n} EPRegion;', '    int* next;\n    EPTaskCost* tasks;\n    int task_count;\n} EPRegion;',1)
s=s.replace('    int sleep_tail, check_claim, buffer_lead, batch_done;', '    int sleep_tail, check_claim, buffer_lead, batch_done, cost_order;',1)
needle='''            p->step(p->context, r->start + offset);
            worked++;'''
replacement='''            if (p->cost_order) {
                EPTaskCost* task = &r->tasks[offset];
                double begin = ep_task_clock();
                p->step(p->context, r->start + task->offset);
                double elapsed = ep_task_clock() - begin;
                task->cost = task->cost ? 0.875 * task->cost + 0.125 * elapsed : elapsed;
            } else {
                p->step(p->context, r->start + offset);
            }
            worked++;'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
needle='    p->batch_done = getenv("PUF_POOL_DONE_BATCH") != NULL;'
s=s.replace(needle,needle+'''\n    p->cost_order = getenv("PUF_POOL_COST") ? atoi(getenv("PUF_POOL_COST")) : 0;
    assert(p->cost_order >= 0 && p->cost_order <= 2);''',1)
needle='    assert(!r->active && !r->readers);\n    r->start = start;'
replacement='''    assert(!r->active && !r->readers);
    if (p->cost_order) {
        if (r->task_count != count) {
            free(r->tasks);
            r->tasks = (EPTaskCost*)calloc(count, sizeof(EPTaskCost));
            assert(r->tasks || !count);
            r->task_count = count;
            for (int i = 0; i < count; i++) r->tasks[i].offset = i;
        }
        if (p->cost_order == 2)
            qsort(r->tasks, count, sizeof(EPTaskCost), ep_cost_compare);
    }
    r->start = start;'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
s=s.replace('        free(p->region[b].next);','        free(p->region[b].tasks);\n        free(p->region[b].next);',1)
p.write_text(s)
(r/'POOL_COST.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='before/src/env_pool.h',tofile='after/src/env_pool.h')))
(r/'POOL_COST_SOURCE.json').write_text(json.dumps(dict(hypothesis='Unprofiled pool tail is 286.22ms/128 calls (2.24ms), ~30% of pool latency. Start historically expensive environments first to reduce final stragglers.',method='Per-task monotonic wall timing with 7/8 EMA, sorted descending before region publication; retain existing striped queues/work stealing. Mode1 times only; mode2 sorts. No engine changes or environment memory movement. Schedules are nondeterministic; observation equivalence must hold.',caveats=['Elapsed task time includes preemption; history is a noisy cost predictor.','Sorting disrupts worker affinity/cache locality; full pipeline must improve.','Pool tail is concurrent and not an additive estimate of total speed headroom.'],sha256=hashlib.sha256(s.encode()).hexdigest()),indent=2))
base=json.loads((r/'POOL_TIMING_FULL.json').read_text())[0]['env']
jobs=[]
for name,extra in [('base_a',{}),('measure',{'PUF_POOL_COST':1}),('sort',{'PUF_POOL_COST':2}),('base_b',{})]:
 jobs.append(dict(kind='full',label='pool_cost_'+name,binary='pool_cost_v24',env=dict(base,PUF_POOL_TIMING=1,**extra),args=['--epochs=80','--start=64']))
(r/'POOL_COST_FULL.json').write_text(json.dumps(jobs,indent=2))
smoke=[]
for j in jobs[:3]:
 j=dict(j,label=j['label']+'_smoke',args=['--epochs=4','--start=1']);smoke.append(j)
(r/'POOL_COST_SMOKE.json').write_text(json.dumps(smoke,indent=2))
with (r/'LEDGER.md').open('a') as f:
 f.write('\n## 2026-10-10 04:06 — pool tail confirmed and cost-order hypothesis\nPrevious prompt-only goal turn was no progress. Re-read objective and polled live session68352 to terminal. POOL_TIMING_FULL: controls209795.834SPS, drift−0.2243%; timing210437.122(+0.306%). All80obs/actor/counts exact. Pool claim655.912ms,tail286.222ms,drain0.614ms per128-step buffer; submitterCPU509.495/111.374/0.145ms. Large tail survives lightweight instrumentation. Per-buffer values overlap, not total wall attribution. Newcostorder experiment: measure prior per-env wall durations, sort expensive games first without changing environment order or striped stealing. Timer-only control separates overhead; sort may hurt locality. Source prepared, build/smoke/full next.\n')
print('prepared isolated cost-order scheduler')
