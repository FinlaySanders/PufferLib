// env_sched.h — cache-affine rollout scheduler: per-game ownership, lazy active set, borrow-when-idle.
// Measured in the replay harness (experiments/nethack-scheduler-20261012): +11% env SPS over the shared pool at a 350 us inference
// round trip and +6% at 800 us with 2048 agents on 24 cores; no gain below ~40 agents per worker (the pool stays there).
// Every game has an owner worker. A worker steps its own ready games, activating a parked one only when none of its active games is
// ready (so the hot set grows just enough to cover the inference latency), and otherwise steps one tick of another worker's ready
// game (the owner keeps it). Workers never sleep. Inference slot threads pop ready observations from a global ring in windows.
#pragma once
#include <pthread.h>
#include <sched.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <immintrin.h>

typedef struct { int owner; int t; int active; double sent; } ESAgent;
typedef struct { int* items; double* times; int head, tail, cap, count; volatile int lock; } ESRing;

static inline void es_lock(volatile int* l) { while (__atomic_exchange_n(l, 1, __ATOMIC_ACQUIRE)) _mm_pause(); }
static inline void es_unlock(volatile int* l) { __atomic_store_n(l, 0, __ATOMIC_RELEASE); }
static inline double es_now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }

static void es_ring_init(ESRing* r, int cap, int timed) {
    r->items = (int*)calloc(cap, sizeof(int)); r->times = timed ? (double*)calloc(cap, sizeof(double)) : NULL;
    r->head = r->tail = r->count = 0; r->cap = cap; r->lock = 0;
}
static inline void es_push(ESRing* r, int x, double now) {
    es_lock(&r->lock);
    r->items[r->tail] = x; if (r->times) r->times[r->tail] = now;
    r->tail = (r->tail + 1) % r->cap; r->count++;
    es_unlock(&r->lock);
}
static inline int es_pop_front(ESRing* r, int* x) {
    if (!__atomic_load_n(&r->count, __ATOMIC_RELAXED)) return 0;
    es_lock(&r->lock);
    int ok = r->count > 0;
    if (ok) { *x = r->items[r->head]; r->head = (r->head + 1) % r->cap; r->count--; }
    es_unlock(&r->lock);
    return ok;
}
static inline int es_pop_back(ESRing* r, int* x) {
    if (!__atomic_load_n(&r->count, __ATOMIC_RELAXED)) return 0;
    es_lock(&r->lock);
    int ok = r->count > 0;
    if (ok) { r->tail = (r->tail + r->cap - 1) % r->cap; *x = r->items[r->tail]; r->count--; }
    es_unlock(&r->lock);
    return ok;
}

typedef struct EnvSched EnvSched;
typedef struct { EnvSched* s; int id; } ESWorker;
struct EnvSched {
    int workers, agents, horizon, pin;
    ESAgent* agent;
    ESRing* ready_active;   // per worker: own games whose actions are back and that are in the active set
    ESRing* ready_parked;   // per worker: own games whose actions are back but not yet active this segment
    int* active_count;
    ESRing infer;           // global: games whose observation is ready for inference (timed)
    pthread_mutex_t infer_mu; pthread_cond_t infer_cv; int infer_waiters;  // slot threads can sleep until the first push into an empty ring
    volatile long done_count;
    volatile int running, stop;
    void (*step)(void*, int); void* ctx;
    void (*before_step)(void*, int, int); // optional hook (recorded-action replay): (ctx, agent, t)
    pthread_t* threads; ESWorker* args;
    long *steps_own, *steps_borrow, *activations; double *busy, *idle; long *steps_own_w, *steps_borrow_w, *borrowed_from_w; double* busy_w;
    int* inrot; double* inrot_sum;  /* own games active and not yet done this segment; summed per step for the mean hot set */
    int* cluster; int cluster_pref;  /* L2 cluster of each worker's core (P-cores private, E-cores 4 per cluster) */
    double *rt_ewma, *step_ewma; int* cap; double hot_k; int hot_cap_fixed; long* parked_back;
};

static inline void es_step_agent(EnvSched* s, int w, int a, int borrowed) {
    ESAgent* g = &s->agent[a];
    double t0 = es_now();
    if (s->before_step) s->before_step(s->ctx, a, g->t);
    s->step(s->ctx, a);
    double dt = es_now() - t0; s->busy[w] += dt; s->busy_w[w] += dt; s->step_ewma[w] = s->step_ewma[w] > 0 ? 0.98 * s->step_ewma[w] + 0.02 * dt : dt;
    if (borrowed) { s->steps_borrow[w]++; s->steps_borrow_w[w]++; s->borrowed_from_w[g->owner]++; } else { s->steps_own[w]++; s->steps_own_w[w]++; }
    int t = ++g->t;
    s->inrot_sum[w] += s->inrot[g->owner];
    if (t >= s->horizon) { if (g->active) __atomic_fetch_sub(&s->inrot[g->owner], 1, __ATOMIC_RELAXED); __atomic_fetch_add(&s->done_count, 1, __ATOMIC_ACQ_REL); }
    else { double now = es_now(); g->sent = now; int was_empty = __atomic_load_n(&s->infer.count, __ATOMIC_RELAXED) == 0; es_push(&s->infer, a, now);
           if (was_empty && __atomic_load_n(&s->infer_waiters, __ATOMIC_RELAXED)) { pthread_mutex_lock(&s->infer_mu); pthread_cond_broadcast(&s->infer_cv); pthread_mutex_unlock(&s->infer_mu); } }
}

static void* es_worker(void* arg) {
    ESWorker* me = (ESWorker*)arg; EnvSched* s = me->s; int w = me->id;
    if (s->pin) {
        int cpu = -1;
        if (s->workers == 24) cpu = w < 8 ? 2 * w : 16 + w - 8;      /* one per physical core: P 0,2..14, E 16..31 */
        else if (s->workers == 32) cpu = w;
        if (cpu >= 0) { cpu_set_t cs; CPU_ZERO(&cs); CPU_SET(cpu, &cs); sched_setaffinity(0, sizeof cs, &cs); }
    }
    for (;;) {
        if (__atomic_load_n(&s->stop, __ATOMIC_ACQUIRE)) return NULL;
        if (!__atomic_load_n(&s->running, __ATOMIC_ACQUIRE)) { for (int i = 0; i < 64; i++) _mm_pause(); continue; }
        int a;
        if (es_pop_front(&s->ready_active[w], &a)) { es_step_agent(s, w, a, 0); continue; }
        if (__atomic_load_n(&s->inrot[w], __ATOMIC_RELAXED) < s->cap[w] && es_pop_front(&s->ready_parked[w], &a)) { s->agent[a].active = 1; s->active_count[w]++; s->activations[w]++; __atomic_fetch_add(&s->inrot[w], 1, __ATOMIC_RELAXED); es_step_agent(s, w, a, 0); continue; }
        /* borrow one tick of the busiest other worker's ready game; prefer a worker whose core shares my L2 (E-core clusters of 4) */
        int v = -1, most = 0;
        if (s->cluster_pref) for (int u = 0; u < s->workers; u++) {
            if (u == w || s->cluster[u] != s->cluster[w]) continue;
            int c = __atomic_load_n(&s->ready_parked[u].count, __ATOMIC_RELAXED) + __atomic_load_n(&s->ready_active[u].count, __ATOMIC_RELAXED);
            if (c > most) { most = c; v = u; }
        }
        if (v < 0) for (int u = 0; u < s->workers; u++) {
            if (u == w) continue;
            int c = __atomic_load_n(&s->ready_parked[u].count, __ATOMIC_RELAXED) + __atomic_load_n(&s->ready_active[u].count, __ATOMIC_RELAXED);
            if (c > most) { most = c; v = u; }
        }
        if (v >= 0 && (es_pop_back(&s->ready_parked[v], &a) || es_pop_back(&s->ready_active[v], &a))) { es_step_agent(s, w, a, 1); continue; }
        double t0 = es_now(); for (int i = 0; i < 32; i++) _mm_pause(); s->idle[w] += es_now() - t0;
    }
}

static EnvSched* es_create(int workers, int agents, int horizon, void (*step)(void*, int), void* ctx, int pin) {
    EnvSched* s = (EnvSched*)calloc(1, sizeof(EnvSched));
    s->workers = workers; s->agents = agents; s->horizon = horizon; s->step = step; s->ctx = ctx; s->pin = pin;
    s->agent = (ESAgent*)calloc(agents, sizeof(ESAgent));
    { /* weighted ownership: P-core workers (0..7 when pinned 24) take PWEIGHT x the games of an E-core worker */
      double pw = getenv("PUF_SCHED_PWEIGHT") ? atof(getenv("PUF_SCHED_PWEIGHT")) : 1.0; double wt[256], sum = 0; int given[256];
      for (int w = 0; w < workers; w++) { wt[w] = (pin && workers == 24 && w < 8) ? pw : 1.0; sum += wt[w]; given[w] = 0; }
      for (int a = 0; a < agents; a++) { int best = 0; double br = 1e30; for (int w = 0; w < workers; w++) { double r = (given[w] + 1) / (wt[w] * agents / sum); if (r < br) { br = r; best = w; } } s->agent[a].owner = best; given[best]++; }
      if (pw != 1.0) fprintf(stderr, "SCHED ownership: P-core workers own %d games each, E-core workers %d\n", given[0], given[workers - 1]); }
    s->ready_active = (ESRing*)calloc(workers, sizeof(ESRing)); s->ready_parked = (ESRing*)calloc(workers, sizeof(ESRing));
    for (int w = 0; w < workers; w++) { es_ring_init(&s->ready_active[w], agents + 1, 0); es_ring_init(&s->ready_parked[w], agents + 1, 0); }
    es_ring_init(&s->infer, agents + 1, 1); pthread_mutex_init(&s->infer_mu, NULL); pthread_cond_init(&s->infer_cv, NULL); s->infer_waiters = 0;
    s->active_count = (int*)calloc(workers, sizeof(int));
    s->steps_own = (long*)calloc(workers, sizeof(long)); s->steps_borrow = (long*)calloc(workers, sizeof(long)); s->activations = (long*)calloc(workers, sizeof(long));
    s->busy = (double*)calloc(workers, sizeof(double)); s->idle = (double*)calloc(workers, sizeof(double));
    s->steps_own_w = (long*)calloc(workers, sizeof(long)); s->steps_borrow_w = (long*)calloc(workers, sizeof(long)); s->busy_w = (double*)calloc(workers, sizeof(double)); s->borrowed_from_w = (long*)calloc(workers, sizeof(long));
    s->inrot = (int*)calloc(workers, sizeof(int)); s->inrot_sum = (double*)calloc(workers, sizeof(double));
    s->cluster = (int*)calloc(workers, sizeof(int)); s->cluster_pref = getenv("PUF_SCHED_CLUSTER") ? atoi(getenv("PUF_SCHED_CLUSTER")) : 0;
    for (int w = 0; w < workers; w++) { int cpu = (pin && workers == 24) ? (w < 8 ? 2 * w : 16 + w - 8) : w; s->cluster[w] = cpu < 16 ? cpu : 100 + (cpu - 16) / 4; } /* i9-14900K: P-cores private L2, E-cores 16-19, 20-23, 24-27, 28-31 share one each */
    s->rt_ewma = (double*)calloc(workers, sizeof(double)); s->step_ewma = (double*)calloc(workers, sizeof(double)); s->cap = (int*)calloc(workers, sizeof(int)); s->parked_back = (long*)calloc(workers, sizeof(long));
    s->hot_k = getenv("PUF_SCHED_HOT_K") ? atof(getenv("PUF_SCHED_HOT_K")) : 1.25;
    s->hot_cap_fixed = getenv("PUF_SCHED_HOT_CAP") ? atoi(getenv("PUF_SCHED_HOT_CAP")) : 0;
    for (int w = 0; w < workers; w++) s->cap[w] = s->hot_cap_fixed ? s->hot_cap_fixed : 1 << 30; /* unknown until the first round trips are measured */
    s->done_count = agents; s->running = 0; s->stop = 0;
    s->threads = (pthread_t*)calloc(workers, sizeof(pthread_t)); s->args = (ESWorker*)calloc(workers, sizeof(ESWorker));
    for (int w = 0; w < workers; w++) { s->args[w].s = s; s->args[w].id = w; pthread_create(&s->threads[w], NULL, es_worker, &s->args[w]); }
    return s;
}

/* Segment start: every game's observation (from its last step) needs a forward at t=0; nothing is active yet. */
static void es_segment_start(EnvSched* s) {
    assert(__atomic_load_n(&s->done_count, __ATOMIC_ACQUIRE) == s->agents);
    for (int w = 0; w < s->workers; w++) { assert(s->ready_active[w].count == 0 && s->ready_parked[w].count == 0); s->active_count[w] = 0; s->inrot[w] = 0; }
    assert(s->infer.count == 0);
    __atomic_store_n(&s->done_count, 0, __ATOMIC_RELEASE);
    double now = es_now();
    for (int a = 0; a < s->agents; a++) { s->agent[a].t = 0; s->agent[a].active = 0; es_push(&s->infer, a, now); }
    __atomic_store_n(&s->running, 1, __ATOMIC_RELEASE);
}
static int es_segment_done(EnvSched* s) { return __atomic_load_n(&s->done_count, __ATOMIC_ACQUIRE) == s->agents; }
static void es_segment_finish(EnvSched* s) { while (!es_segment_done(s)) { struct timespec ts = {0, 50000}; nanosleep(&ts, NULL); } __atomic_store_n(&s->running, 0, __ATOMIC_RELEASE); }

/* Slot thread: sleep until something is pushed into the empty inference ring, or until timeout_ns elapses. */
static void es_infer_wait(EnvSched* s, long timeout_ns) {
    struct timespec ts; clock_gettime(CLOCK_REALTIME, &ts); ts.tv_nsec += timeout_ns; while (ts.tv_nsec >= 1000000000L) { ts.tv_nsec -= 1000000000L; ts.tv_sec++; }
    pthread_mutex_lock(&s->infer_mu); __atomic_fetch_add(&s->infer_waiters, 1, __ATOMIC_RELAXED);
    if (__atomic_load_n(&s->infer.count, __ATOMIC_RELAXED) == 0) pthread_cond_timedwait(&s->infer_cv, &s->infer_mu, &ts);
    __atomic_fetch_sub(&s->infer_waiters, 1, __ATOMIC_RELAXED); pthread_mutex_unlock(&s->infer_mu);
}
/* Age of the oldest pending observation in seconds (negative if the ring is empty). */
static double es_infer_oldest_age(EnvSched* s) { ESRing* r = &s->infer; if (!__atomic_load_n(&r->count, __ATOMIC_RELAXED)) return -1; return es_now() - r->times[r->head]; }
/* Inference side: take up to max ready observations; when fewer than max are ready, take them all once the oldest has waited window_s. */
static int es_infer_pop(EnvSched* s, int* ids, int max, double window_s) {
    ESRing* r = &s->infer;
    int c = __atomic_load_n(&r->count, __ATOMIC_RELAXED);
    if (!c) return 0;
    if (c < max && es_now() - r->times[r->head] < window_s) return 0;
    es_lock(&r->lock);
    int n = r->count < max ? r->count : max;
    if (n < max && es_now() - r->times[r->head] < window_s) n = 0;
    for (int i = 0; i < n; i++) { ids[i] = r->items[r->head]; r->head = (r->head + 1) % r->cap; }
    r->count -= n;
    es_unlock(&r->lock);
    return n;
}
/* Actions for these games are back in the host action array: hand them to their owners. */
static void es_actions_back(EnvSched* s, const int* ids, int n) {
    double now = es_now();
    for (int i = 0; i < n; i++) {
        int a = ids[i]; ESAgent* g = &s->agent[a]; int w = g->owner;
        if (g->sent > 0 && g->t > 0) { double rt = now - g->sent; s->rt_ewma[w] = s->rt_ewma[w] > 0 ? 0.95 * s->rt_ewma[w] + 0.05 * rt : rt; } /* t==0 returns are the segment-start burst, not a steady round trip */
        if (!s->hot_cap_fixed && s->step_ewma[w] > 0 && s->rt_ewma[w] > 0) { int c = (int)(s->hot_k * s->rt_ewma[w] / s->step_ewma[w]) + 1; s->cap[w] = c < 2 ? 2 : c; }
        if (g->active && __atomic_load_n(&s->inrot[w], __ATOMIC_RELAXED) > s->cap[w]) { g->active = 0; __atomic_fetch_sub(&s->inrot[w], 1, __ATOMIC_RELAXED); s->parked_back[w]++; }
        es_push(g->active ? &s->ready_active[w] : &s->ready_parked[w], a, now);
    }
}
static void es_destroy(EnvSched* s) {
    __atomic_store_n(&s->stop, 1, __ATOMIC_RELEASE);
    for (int w = 0; w < s->workers; w++) pthread_join(s->threads[w], NULL);
}
static void es_print_stats(EnvSched* s, FILE* f, const char* tag) {
    long own = 0, bor = 0, act = 0, pb = 0; double busy = 0, idle = 0, bmin = 1e30, bmax = 0, rot = 0, rt = 0, se = 0; long capsum = 0;
    for (int w = 0; w < s->workers; w++) { own += s->steps_own[w]; bor += s->steps_borrow[w]; act += s->activations[w]; busy += s->busy[w]; idle += s->idle[w]; rot += s->inrot_sum[w]; pb += s->parked_back[w]; s->parked_back[w] = 0; rt += s->rt_ewma[w]; se += s->step_ewma[w]; capsum += s->cap[w] > 100000 ? 0 : s->cap[w]; if (s->busy[w] < bmin) bmin = s->busy[w]; if (s->busy[w] > bmax) bmax = s->busy[w]; s->steps_own[w] = s->steps_borrow[w] = s->activations[w] = 0; s->busy[w] = s->idle[w] = 0; s->inrot_sum[w] = 0; }
    { char line[512]; int o = snprintf(line, sizeof line, "SCHED_PCORES %s", tag); for (int w = 0; w < s->workers && w < 8; w++) { long n = s->steps_own_w[w] + s->steps_borrow_w[w]; o += snprintf(line + o, sizeof line - o, " w%d=%.1f", w, n ? 1e6 * s->busy_w[w] / n : 0.0); } fprintf(f, "%s\n", line); }
    { double pb_=0,pe_=0; long pn=0,en=0,pbor=0,ebor=0,pfrom=0,efrom=0; for (int w = 0; w < s->workers; w++) { long n = s->steps_own_w[w] + s->steps_borrow_w[w]; int isP = s->pin && s->workers == 24 && w < 8; if (isP) { pb_ += s->busy_w[w]; pn += n; pbor += s->steps_borrow_w[w]; pfrom += s->borrowed_from_w[w]; } else { pe_ += s->busy_w[w]; en += n; ebor += s->steps_borrow_w[w]; efrom += s->borrowed_from_w[w]; } s->steps_own_w[w] = s->steps_borrow_w[w] = 0; s->busy_w[w] = 0; s->borrowed_from_w[w] = 0; }
      fprintf(f, "SCHED_CORES %s P_us_per_step=%.1f E_us_per_step=%.1f P_steps=%ld E_steps=%ld P_borrows=%ld E_borrows=%ld taken_from_P=%ld taken_from_E=%ld\n", tag, pn ? 1e6 * pb_ / pn : 0.0, en ? 1e6 * pe_ / en : 0.0, pn, en, pbor, ebor, pfrom, efrom); }
    fprintf(f, "SCHED_STATS %s steps_own=%ld steps_borrow=%ld borrow_pct=%.1f activations=%ld parked_back=%ld cap_mean=%.1f rt_us=%.0f step_us=%.1f hot_set_mean=%.1f us_per_step=%.1f busy_mean=%.3f busy_min=%.3f busy_max=%.3f idle_mean=%.3f\n",
        tag, own, bor, 100.0 * bor / (double)(own + bor ? own + bor : 1), act, pb, capsum / (double)s->workers, 1e6 * rt / s->workers, 1e6 * se / s->workers, rot / (double)(own + bor ? own + bor : 1), 1e6 * busy / (double)(own + bor ? own + bor : 1), busy / s->workers, bmin, bmax, idle / s->workers);
}
