#ifndef ENV_POOL_H
#define ENV_POOL_H
#include <pthread.h>
#include <nvtx3/nvToolsExt.h>
#include <stdlib.h>
#include <assert.h>
#include <sched.h>
#include <time.h>
#include <string.h>

typedef struct {
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
    pthread_mutex_t mu;
    pthread_cond_t quiet;
    int active, readers, start, count, done;
    unsigned long generation;
    int* next;
    EPTaskCost* tasks;
    int task_count;
} EPRegion;
typedef struct {
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

typedef struct EnvPool EnvPool;
typedef struct { EnvPool* pool; int id; } EPWorker;
struct EnvPool {
    int workers, buffers, stop, buffer_focus, buffer_fair;
    int sleep_tail, check_claim, buffer_lead, batch_done, cost_order;
    unsigned long epoch;
    pthread_mutex_t mu;
    pthread_cond_t ready;
    EPRegion* region;
    EPTiming* timing;
    pthread_t* threads;
    EPWorker* args;
    void (*step)(void*, int);
    void* context;
};

static void ep_completed(EnvPool* p, EPRegion* r, int count) {
    int finished = __atomic_add_fetch(&r->done, count, __ATOMIC_RELEASE);
    if (p->sleep_tail && finished == r->count) {
        pthread_mutex_lock(&r->mu);
        pthread_cond_signal(&r->quiet);
        pthread_mutex_unlock(&r->mu);
    }
}

static int ep_claim(EnvPool* p, EPRegion* r, int id) {
    int worked = 0;
    for (int k = 0; k < p->workers; k++) {
        int home = (id + k) % p->workers;
        for (;;) {
            if (p->check_claim && home + __atomic_load_n(&r->next[home * 16],
                    __ATOMIC_RELAXED) * p->workers >= r->count) break;
            int n = __atomic_fetch_add(&r->next[home * 16], 1, __ATOMIC_RELAXED);
            int offset = home + n * p->workers;
            if (offset >= r->count) break;
            if (p->cost_order) {
                EPTaskCost* task = &r->tasks[offset];
                double begin = ep_task_clock();
                p->step(p->context, r->start + task->offset);
                double elapsed = ep_task_clock() - begin;
                task->cost = task->cost ? 0.875 * task->cost + 0.125 * elapsed : elapsed;
            } else {
                p->step(p->context, r->start + offset);
            }
            worked++;
            if (!p->batch_done) ep_completed(p, r, 1);
        }
    }
    if (p->batch_done && worked) ep_completed(p, r, worked);
    return worked;
}

/* Experimental placement for this 8P+16E host. Startup only. */
static void ep_pin_cpu(int cpu) {
    cpu_set_t allowed, selected;
    assert(pthread_getaffinity_np(pthread_self(), sizeof(allowed), &allowed) == 0);
    assert(CPU_ISSET(cpu, &allowed));
    CPU_ZERO(&selected); CPU_SET(cpu, &selected);
    assert(pthread_setaffinity_np(pthread_self(), sizeof(selected), &selected) == 0);
}

static void* ep_worker(void* arg) {
    EPWorker* w = (EPWorker*)arg;
    EnvPool* p = w->pool;
    const char* affinity = getenv("PUF_CPU_AFFINITY");
    if (affinity && atoi(affinity) == 1) {
        assert(p->workers == 24);
        ep_pin_cpu(w->id < 8 ? 2*w->id : 16+w->id-8);
    }
    for (;;) {
        pthread_mutex_lock(&p->mu);
        unsigned long epoch = p->epoch;
        int stop = p->stop;
        pthread_mutex_unlock(&p->mu);
        if (stop) return NULL;
        int order[64];
        if(p->buffer_fair || p->buffer_lead >= 0) {
            unsigned long generation[64], minimum = ~0UL;
            for(int i=0;i<p->buffers;i++) {
                EPRegion* r=&p->region[i];
                pthread_mutex_lock(&r->mu);
                unsigned long current = r->generation;
                generation[i]=r->active?current:~0UL;
                if (current < minimum) minimum = current;
                pthread_mutex_unlock(&r->mu);
                order[i]=i;
            }
            if (p->buffer_lead >= 0) {
                for (int i=0;i<p->buffers;i++) {
                    if (generation[i] != ~0UL)
                        generation[i] = (generation[i] > minimum + p->buffer_lead)
                            ? generation[i] + p->buffers : (unsigned long)i;
                }
            }
            for(int i=1;i<p->buffers;i++) {
                int key=order[i],j=i;
                while(j>0 && generation[order[j-1]]>generation[key]) {
                    order[j]=order[j-1];j--;
                }
                order[j]=key;
            }
        }
        int repeat_ready_scan = 0;
        for (int k = 0; k < p->buffers; k++) {
            EPRegion* r = &p->region[(p->buffer_fair || p->buffer_lead >= 0)?order[k]:(p->buffer_focus ? k : w->id + k) % p->buffers];
            pthread_mutex_lock(&r->mu);
            int active = r->active;
            if (active) r->readers++;
            pthread_mutex_unlock(&r->mu);
            if (!active) continue;
            nvtxRangePushA("pool.worker_work");
            int worked = ep_claim(p, r, w->id);
            nvtxRangePop();
            pthread_mutex_lock(&r->mu);
            if (--r->readers == 0) pthread_cond_signal(&r->quiet);
            pthread_mutex_unlock(&r->mu);
            if (p->buffer_focus && worked) {repeat_ready_scan = 1; break;}
        }
        if (repeat_ready_scan) continue;
        pthread_mutex_lock(&p->mu);
        while (!p->stop && epoch == p->epoch) pthread_cond_wait(&p->ready, &p->mu);
        pthread_mutex_unlock(&p->mu);
    }
}

static EnvPool* ep_create(int workers, int buffers, void (*step)(void*, int), void* context) {
    assert(workers > 0 && buffers > 0);
    EnvPool* p = (EnvPool*)calloc(1, sizeof(*p));
    assert(p);
    p->buffer_fair = getenv("PUF_BUFFER_FAIR") != NULL;
    p->buffer_lead = getenv("PUF_BUFFER_LEAD") ? atoi(getenv("PUF_BUFFER_LEAD")) : -1;
    if(p->buffer_fair || p->buffer_lead >= 0) assert(buffers<=64);
    p->buffer_focus = p->buffer_fair || p->buffer_lead >= 0 || getenv("PUF_BUFFER_FOCUS") != NULL;
    p->sleep_tail = getenv("PUF_POOL_SLEEP") != NULL;
    p->check_claim = getenv("PUF_POOL_CHECK_CLAIM") != NULL;
    p->batch_done = getenv("PUF_POOL_DONE_BATCH") != NULL;
    p->cost_order = getenv("PUF_POOL_COST") ? atoi(getenv("PUF_POOL_COST")) : 0;
    assert(p->cost_order >= 0 && p->cost_order <= 2);
    p->workers = workers; p->buffers = buffers; p->step = step; p->context = context;
    if (getenv("PUF_POOL_TIMING")) {
        assert(sizeof(EPTiming) == 64);
        assert(posix_memalign((void**)&p->timing, 64, buffers * sizeof(EPTiming)) == 0);
        memset(p->timing, 0, buffers * sizeof(EPTiming));
    }
    p->region = (EPRegion*)calloc(buffers, sizeof(*p->region));
    p->threads = (pthread_t*)calloc(workers, sizeof(*p->threads));
    p->args = (EPWorker*)calloc(workers, sizeof(*p->args));
    assert(p->region && p->threads && p->args);
    pthread_mutex_init(&p->mu, NULL); pthread_cond_init(&p->ready, NULL);
    for (int b = 0; b < buffers; b++) {
        pthread_mutex_init(&p->region[b].mu, NULL);
        pthread_cond_init(&p->region[b].quiet, NULL);
        p->region[b].next = (int*)calloc(workers * 16, sizeof(int));
        assert(p->region[b].next);
    }
    for (int w = 0; w < workers; w++) {
        p->args[w].pool = p; p->args[w].id = w;
        if (pthread_create(&p->threads[w], NULL, ep_worker, &p->args[w])) abort();
    }
    return p;
}

/* One submitting thread per region. Readers lease the region until all
 * accesses to its generation's counters have finished. */
static void ep_run(EnvPool* p, int buffer, int start, int count) {
    assert(buffer >= 0 && buffer < p->buffers && count >= 0);
    EPRegion* r = &p->region[buffer];
    double w0=0, w1=0, w2=0, w3=0, c0=0, c1=0, c2=0, c3=0;
    if (p->timing) ep_clocks(&w0, &c0);
    pthread_mutex_lock(&r->mu);
    assert(!r->active && !r->readers);
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
    r->start = start; r->count = count; r->generation++;
    __atomic_store_n(&r->done, 0, __ATOMIC_RELAXED);
    for (int w = 0; w < p->workers; w++) r->next[w * 16] = 0;
    r->active = 1;
    pthread_mutex_unlock(&r->mu);
    pthread_mutex_lock(&p->mu);
    p->epoch++; pthread_cond_broadcast(&p->ready);
    pthread_mutex_unlock(&p->mu);
    nvtxRangePushA("pool.submitter_work");
    ep_claim(p, r, buffer % p->workers);
    nvtxRangePop();
    if (p->timing) ep_clocks(&w1, &c1);
    nvtxRangePushA("pool.tail_wait");
    if (p->sleep_tail) {
        pthread_mutex_lock(&r->mu);
        while (__atomic_load_n(&r->done, __ATOMIC_ACQUIRE) < count)
            pthread_cond_wait(&r->quiet, &r->mu);
        pthread_mutex_unlock(&r->mu);
    } else {
        while (__atomic_load_n(&r->done, __ATOMIC_ACQUIRE) < count) sched_yield();
    }
    nvtxRangePop();
    if (p->timing) ep_clocks(&w2, &c2);
    pthread_mutex_lock(&r->mu);
    r->active = 0;
    nvtxRangePushA("pool.reader_drain");
    while (r->readers) pthread_cond_wait(&r->quiet, &r->mu);
    nvtxRangePop();
    pthread_mutex_unlock(&r->mu);
    if (p->timing) {
        ep_clocks(&w3, &c3);
        EPTiming* t = &p->timing[buffer];
        t->claim_wall += w1-w0; t->tail_wall += w2-w1; t->drain_wall += w3-w2;
        t->claim_cpu += c1-c0; t->tail_cpu += c2-c1; t->drain_cpu += c3-c2;
        t->samples++;
    }
}

/* Submitters must be joined before destroying the pool or its environments. */
static void ep_destroy(EnvPool* p) {
    pthread_mutex_lock(&p->mu);
    p->stop = 1; pthread_cond_broadcast(&p->ready);
    pthread_mutex_unlock(&p->mu);
    for (int w = 0; w < p->workers; w++) pthread_join(p->threads[w], NULL);
    for (int b = 0; b < p->buffers; b++) {
        assert(!p->region[b].active && !p->region[b].readers);
        pthread_mutex_destroy(&p->region[b].mu);
        pthread_cond_destroy(&p->region[b].quiet);
        free(p->region[b].tasks);
        free(p->region[b].next);
    }
    pthread_mutex_destroy(&p->mu); pthread_cond_destroy(&p->ready);
    free(p->timing); free(p->region); free(p->threads); free(p->args); free(p);
}
#endif
