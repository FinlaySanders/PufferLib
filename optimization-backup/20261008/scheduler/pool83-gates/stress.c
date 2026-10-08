#include "env_pool.h"
#include <stdint.h>
#include <stdio.h>
#define BUFFERS 4
#define WIDTH 67
typedef struct { uint64_t value; int visits, busy; } Cell;
typedef struct { EnvPool* p; Cell* cells; int b, rounds; } Submit;
static uint64_t advance(uint64_t x) { return x * UINT64_C(6364136223846793005) + 1442695040888963407ULL; }
static void step(void* context, int i) {
    Cell* c = &((Cell*)context)[i];
    assert(__atomic_exchange_n(&c->busy, 1, __ATOMIC_SEQ_CST) == 0);
    if ((c->visits + i) % 13 == 0) sched_yield();
    c->value = advance(c->value); c->visits++;
    assert(__atomic_exchange_n(&c->busy, 0, __ATOMIC_SEQ_CST) == 1);
}
static void* submit(void* arg) {
    Submit* s = (Submit*)arg;
    int expected[WIDTH] = {0};
    uint64_t values[WIDTH] = {0};
    for (int round = 0; round < s->rounds; round++) {
        int n = (round * 17 + s->b) % (WIDTH + 1);
        ep_run(s->p, s->b, s->b * WIDTH, n);
        for (int i = 0; i < WIDTH; i++) {
            if (i < n) { expected[i]++; values[i] = advance(values[i]); }
            Cell* c = &s->cells[s->b * WIDTH + i];
            assert(c->visits == expected[i] && c->value == values[i]);
        }
    }
    return NULL;
}
int main(void) {
    for (int generation = 0; generation < 15; generation++) {
        Cell cells[BUFFERS * WIDTH] = {0};
        EnvPool* p = ep_create(generation < 12 ? 1 + generation % 8 : 20 + (generation-12)*4, BUFFERS, step, cells);
        pthread_t threads[BUFFERS]; Submit args[BUFFERS];
        for (int b = 0; b < BUFFERS; b++) {
            args[b] = (Submit){p, cells, b, 1000};
            assert(!pthread_create(&threads[b], NULL, submit, &args[b]));
        }
        for (int b = 0; b < BUFFERS; b++) pthread_join(threads[b], NULL);
        ep_destroy(p);
    }
    puts("PASS: 60000 concurrent regions; changing sizes, zero work, exact visits/state, destroy/recreate");
}
