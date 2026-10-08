#ifndef ENV_POOL_H
#define ENV_POOL_H
#include <pthread.h>
#include <stdlib.h>
#include <assert.h>
#include <sched.h>

typedef struct {
    pthread_mutex_t mu;
    pthread_cond_t quiet;
    int active, readers, start, count, done;
    int* next;
} EPRegion;
typedef struct EnvPool EnvPool;
typedef struct { EnvPool* pool; int id; } EPWorker;
struct EnvPool {
    int workers, buffers, stop;
    unsigned long epoch;
    pthread_mutex_t mu;
    pthread_cond_t ready;
    EPRegion* region;
    pthread_t* threads;
    EPWorker* args;
    void (*step)(void*, int);
    void* context;
};

static void ep_claim(EnvPool* p, EPRegion* r, int id) {
    for (int k = 0; k < p->workers; k++) {
        int home = (id + k) % p->workers;
        for (;;) {
            int n = __atomic_fetch_add(&r->next[home * 16], 1, __ATOMIC_RELAXED);
            int offset = home + n * p->workers;
            if (offset >= r->count) break;
            p->step(p->context, r->start + offset);
            __atomic_fetch_add(&r->done, 1, __ATOMIC_RELEASE);
        }
    }
}

static void* ep_worker(void* arg) {
    EPWorker* w = (EPWorker*)arg;
    EnvPool* p = w->pool;
    for (;;) {
        pthread_mutex_lock(&p->mu);
        unsigned long epoch = p->epoch;
        int stop = p->stop;
        pthread_mutex_unlock(&p->mu);
        if (stop) return NULL;
        for (int k = 0; k < p->buffers; k++) {
            EPRegion* r = &p->region[(w->id + k) % p->buffers];
            pthread_mutex_lock(&r->mu);
            int active = r->active;
            if (active) r->readers++;
            pthread_mutex_unlock(&r->mu);
            if (!active) continue;
            ep_claim(p, r, w->id);
            pthread_mutex_lock(&r->mu);
            if (--r->readers == 0) pthread_cond_signal(&r->quiet);
            pthread_mutex_unlock(&r->mu);
        }
        pthread_mutex_lock(&p->mu);
        while (!p->stop && epoch == p->epoch) pthread_cond_wait(&p->ready, &p->mu);
        pthread_mutex_unlock(&p->mu);
    }
}

static EnvPool* ep_create(int workers, int buffers, void (*step)(void*, int), void* context) {
    assert(workers > 0 && buffers > 0);
    EnvPool* p = (EnvPool*)calloc(1, sizeof(*p));
    assert(p);
    p->workers = workers; p->buffers = buffers; p->step = step; p->context = context;
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
    pthread_mutex_lock(&r->mu);
    assert(!r->active && !r->readers);
    r->start = start; r->count = count;
    __atomic_store_n(&r->done, 0, __ATOMIC_RELAXED);
    for (int w = 0; w < p->workers; w++) r->next[w * 16] = 0;
    r->active = 1;
    pthread_mutex_unlock(&r->mu);
    pthread_mutex_lock(&p->mu);
    p->epoch++; pthread_cond_broadcast(&p->ready);
    pthread_mutex_unlock(&p->mu);
    ep_claim(p, r, buffer % p->workers);
    while (__atomic_load_n(&r->done, __ATOMIC_ACQUIRE) < count) sched_yield();
    pthread_mutex_lock(&r->mu);
    r->active = 0;
    while (r->readers) pthread_cond_wait(&r->quiet, &r->mu);
    pthread_mutex_unlock(&r->mu);
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
        free(p->region[b].next);
    }
    pthread_mutex_destroy(&p->mu); pthread_cond_destroy(&p->ready);
    free(p->region); free(p->threads); free(p->args); free(p);
}
#endif
