from pathlib import Path
import difflib,json,hashlib
r=Path(__file__).resolve().parent;p=r/'source/src/pufferl.cu';old=p.read_text();s=old
assert 'PUF_FINISH_SLEEP'not in s
s=s.replace('    bool collector_sleep;','    bool collector_sleep;\n    bool finish_sleep;',1)
s=s.replace('    vec->collector_sleep = vec->cohort_size || getenv("PUF_COLLECTOR_SLEEP");','    vec->collector_sleep = vec->cohort_size || getenv("PUF_COLLECTOR_SLEEP");\n    vec->finish_sleep = getenv("PUF_FINISH_SLEEP") != NULL;',1)
marker='''        vec->perf_completed[buf]=wall_clock();
        __atomic_store_n(state, BUF_WAITING, __ATOMIC_SEQ_CST);'''
new='''        vec->perf_completed[buf]=wall_clock();
        if (vec->finish_sleep) pthread_mutex_lock(&vec->cohort_mutex);
        __atomic_store_n(state, BUF_WAITING, __ATOMIC_SEQ_CST);
        if (vec->finish_sleep) {
            pthread_cond_broadcast(&vec->cohort_cond);
            pthread_mutex_unlock(&vec->cohort_mutex);
        }'''
assert s.count(marker)==1;s=s.replace(marker,new)
marker='''    for (int buf = 0; buf < p->vec->buffers; buf++) {
        int* state = &p->vec->worker_state[buf];
        while (__atomic_load_n(state, __ATOMIC_SEQ_CST) != BUF_WAITING) {}
    }
    float sec = (float)(wall_clock() - t0);'''
new='''    if (p->vec->finish_sleep) pthread_mutex_lock(&p->vec->cohort_mutex);
    for (int buf = 0; buf < p->vec->buffers; buf++) {
        int* state = &p->vec->worker_state[buf];
        while (__atomic_load_n(state, __ATOMIC_SEQ_CST) != BUF_WAITING) {
            if (p->vec->finish_sleep)
                pthread_cond_wait(&p->vec->cohort_cond, &p->vec->cohort_mutex);
        }
    }
    if (p->vec->finish_sleep) pthread_mutex_unlock(&p->vec->cohort_mutex);
    float sec = (float)(wall_clock() - t0);'''
assert s.count(marker)==1;s=s.replace(marker,new)
p.write_text(s)
(r/'FINISH_SLEEP.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='before/pufferl.cu',tofile='after/pufferl.cu')))
(r/'FINISH_SLEEP_SOURCE.json').write_text(json.dumps({'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'description':'Optional main-thread horizon wait uses existing mutex/cond; completion writes and notification under same mutex. Existing collector idle sleep controlled independently. No per-step new synchronization; default off.','hypothesis':'After cheaperGPUtraining, main and earlycompleted collectors may compete with simulation while waiting for remaining buffers. Prior pool-tail sleeping and CUDA waits do not cover this horizon-boundary spin.'},indent=2))
rows=[]
for label,env in [('base',{}),('both',{'PUF_FINISH_SLEEP':1,'PUF_COLLECTOR_SLEEP':1})]:
 rows.append({'kind':'full','label':'horizon_sleep_smoke_'+label,'binary':'finish_sleep_v21','env':{'PUF_CUDA_WAIT':'block',**env},'args':['--epochs=4','--start=1']})
(r/'FINISH_SLEEP_SMOKE.json').write_text(json.dumps(rows,indent=2))
print('Prepared optional horizon completion sleep, not built or run')
