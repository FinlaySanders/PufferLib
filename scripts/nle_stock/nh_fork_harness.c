// Validation harness for the C derivations inside the vec: the FORK engine drives every
// env (ground truth for all hooks), nh_derive.h derives each channel from the public
// observation on the same trajectory, and linker --wrap on the hooks compares the two.
// NH_DERIVE_MODE=0 (default): real values are used, mismatches counted per channel.
// NH_DERIVE_MODE=1: the derived values are used instead (score impact of the port alone).
// Probes (':' '+' '\') go to the real engine outside the env's key stream, as the python harness did.
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nletypes.h"
#include "nh_derive.h"
#include "nh_derive_rec.h"

extern nle_ctx_t* __real_nle_start(nle_obs*, FILE*, nle_settings*);
extern nle_ctx_t* __real_nle_step(nle_ctx_t*, nle_obs*);
extern nle_ctx_t* __real_nle_obs_refresh(nle_ctx_t*, nle_obs*);
extern void __real_nle_end(nle_ctx_t*);
extern void __real_nle_identity(nle_ctx_t*, int*, int*, int*, int*);
extern int __real_nle_terrain_underfoot(nle_ctx_t*);
extern int __real_nle_food_underfoot(nle_ctx_t*);
extern int __real_nle_container_at(nle_ctx_t*);
extern long __real_nle_shop_price(nle_ctx_t*);
extern int __real_nle_inside_shop(nle_ctx_t*);
extern int __real_nle_peaceful_at(nle_ctx_t*, int, int);
extern int __real_nle_spells(nle_ctx_t*, short*, signed char*, signed char*, int*, int);
extern int __real_nle_lnc_bits(nle_ctx_t*);
extern void __real_nle_weight(nle_ctx_t*, int*, int*);
extern int __real_nle_intrinsics(nle_ctx_t*);
extern int __real_nle_cast_blocked(nle_ctx_t*);
extern int __real_nle_path_drain(nle_ctx_t*, short*, int);

#define HMAX 4096
typedef struct {
    nle_ctx_t* ctx; nle_obs* obs; DObs d; DState S;
    unsigned char sdesc[21 * 79 * 80]; unsigned char tty[24 * 80]; signed char ttyc[24 * 80]; unsigned char cur[2];
    unsigned char chars[21 * 79]; unsigned char colors[21 * 79]; unsigned char invstrs[55 * 80];
    signed char inv_state[55 * 8]; short inv_true[55];
    short glyph_copy[21 * 79]; short inv_copy[55]; int have_copy;
    int in_probe; int used; FILE* keylog; unsigned long seed0; FILE* petlog; long steps;
    short mapprev[21 * 79]; char invprev[55 * 64]; char stprev[55 * 24]; void* rng;
    int pend, pend_key; // log-only: a stepped key whose boundary hash is still to be taken inside the env's own refresh
    long klog_n; long klog_marked; // keys written to the key log this episode; last key marked as an env boundary (R line)
    int idx; int ep; DRecW rec; // NH_DERIVE_REC=<dir>: derive-replay recording (mode 0, env slots < NH_DERIVE_REC_ENVS)
} HEnv;
static HEnv* g_envs[HMAX]; static int g_nenv; static int g_mode;
static int g_lock;
static void lock(void) { while (__sync_lock_test_and_set(&g_lock, 1)) {} }
static void unlock(void) { __sync_lock_release(&g_lock); }
static HEnv* find_env(nle_ctx_t* c) { for (int i = 0; i < g_nenv; i++) if (g_envs[i] && g_envs[i]->ctx == c) return g_envs[i]; return NULL; }
// derive-replay recording (nh_derive_rec.h): every engine interaction the derive sees plus the fork truth at every hook
static const char* g_rec_dir; static int g_rec_envs;
static void rec_obs(HEnv* e, int type, int key, int done) {
    if (!e->rec.on) return; DRecObs c; memset(&c, 0, sizeof c); const DObs* d = &e->d; const nle_obs* o = e->obs;
    if (d->glyphs) memcpy(c.glyphs, d->glyphs, sizeof c.glyphs); if (d->blstats) memcpy(c.blstats, d->blstats, sizeof c.blstats);
    if (d->message) memcpy(c.message, d->message, sizeof c.message); if (d->misc) memcpy(c.misc, d->misc, sizeof c.misc);
    if (d->tty_chars) memcpy(c.tty_chars, d->tty_chars, sizeof c.tty_chars); if (d->tty_colors) memcpy(c.tty_colors, d->tty_colors, sizeof c.tty_colors);
    if (d->tty_cursor) memcpy(c.tty_cursor, d->tty_cursor, sizeof c.tty_cursor);
    if (d->inv_glyphs) memcpy(c.inv_glyphs, d->inv_glyphs, sizeof c.inv_glyphs); if (d->inv_strs) memcpy(c.inv_strs, d->inv_strs, sizeof c.inv_strs);
    if (d->inv_letters) memcpy(c.inv_letters, d->inv_letters, sizeof c.inv_letters); if (d->inv_oclasses) memcpy(c.inv_oclasses, d->inv_oclasses, sizeof c.inv_oclasses);
    if (o && o->internal) memcpy(c.internal, o->internal, sizeof(int) * (NLE_INTERNAL_SIZE < 16 ? NLE_INTERNAL_SIZE : 16));
    if (o && o->inv_state) memcpy(c.inv_state, o->inv_state, sizeof c.inv_state); if (o && o->inv_true_glyphs) memcpy(c.inv_true, o->inv_true_glyphs, sizeof c.inv_true);
    drec_hdr(&e->rec, type, key, done); drec_snapshot(&e->rec, &c);
}
static void rec_hook(HEnv* e, int chan, int nargs, const long* a, int nvals, const long* v) { if (e && e->rec.on) drec_hook(&e->rec, chan, nargs, a, nvals, v); }
static void rec_start(HEnv* e, unsigned long seed) {
    if (!g_rec_dir || e->idx >= g_rec_envs) return; if (e->rec.on) drec_close(&e->rec);
    if (drec_open(&e->rec, g_rec_dir, seed, e->idx, e->ep++)) rec_obs(e, R_START, 0, 0);
}

// mismatch ledger
enum { C_TERR, C_FOOD, C_CONT, C_PRICE, C_SHOP, C_PEACE, C_SPELLS, C_LNC, C_WT, C_CAP, C_INTR, C_CAST, C_PATH, C_ENGR, C_HERO, C_INVST, C_INVTRUE, C_IDENT, C_DISC, C_RANGE, C_MAPRANGE, C_N };
static const char* C_NAMES[C_N] = {"terrain", "food_underfoot", "container_at", "shop_price", "inside_shop", "peaceful_at", "spells", "lnc_bits", "weight", "capacity", "intrinsics", "cast_blocked", "path", "engraving_bits", "hero_tile", "inv_state", "inv_true_glyph", "identity", "known_but_undiscovered", "appearance_outside_range", "map_obj_outside_range"};
static long M_q[C_N], M_bad[C_N];
// NH_DERIVE_REAL=terrain,weight,... : in derived mode (NH_DERIVE_MODE=1) keep these channels REAL. Ablation rig:
// the score gap between all-derived and all-derived-but-X is the cost of reconstructing X.
static int g_real[C_N];
static int use_der(int c) { return g_mode > 0 && !g_real[c]; }
static void parse_real(const char* s) { if (!s) return; char b[512]; snprintf(b, sizeof b, "%s", s);
    for (char* t = strtok(b, ", "); t; t = strtok(NULL, ", ")) { int hit = 0; for (int c = 0; c < C_N; c++) if (!strcmp(t, C_NAMES[c])) { g_real[c] = 1; hit = 1; }
        if (!hit) fprintf(stderr, "NH_DERIVE_REAL: unknown channel '%s'\n", t); } }
static void note(int c, int bad) { __sync_fetch_and_add(&M_q[c], 1); if (bad) __sync_fetch_and_add(&M_bad[c], 1); }
static FILE* g_log;
static void logmis(HEnv* e, const char* what, long real, long der) { if (!g_log) return; lock(); fprintf(g_log, "MISMATCH %s T=%ld real=%ld derived=%ld\n", what, e && e->obs ? e->obs->blstats[20] : -1L, real, der); unlock(); }
static void report(void) {
    fprintf(stderr, "DERIVE_HARNESS mode=%d channel queries mismatches rate\n", g_mode);
    for (int c = 0; c < C_N; c++) if (g_real[c]) fprintf(stderr, "  (kept REAL in derived mode: %s)\n", C_NAMES[c]);
    for (int c = 0; c < C_N; c++) fprintf(stderr, "  %-16s %10ld %10ld %8.3f%%\n", C_NAMES[c], M_q[c], M_bad[c], 100.0 * (double)M_bad[c] / (double)(M_q[c] ? M_q[c] : 1));
    long probes = 0, skb = 0, ske = 0, skp = 0, keys = 0;
    for (int i = 0; i < g_nenv; i++) if (g_envs[i]) { probes += g_envs[i]->S.probes; skb += g_envs[i]->S.probe_skip_blind; ske += g_envs[i]->S.probe_skip_engulf; skp += g_envs[i]->S.probe_skip_prompt; keys += g_envs[i]->S.keys; }
    fprintf(stderr, "  keys=%ld probes=%ld skipped(blind=%ld engulfed=%ld prompt=%ld)\n", keys, probes, skb, ske, skp);
}

static int harness_send(void* ctx, int key) {
    HEnv* e = (HEnv*)ctx;
    e->in_probe = 1;
    e->obs->action = key;
    __real_nle_step(e->ctx, e->obs);
    if (!e->obs->done) __real_nle_obs_refresh(e->ctx, e->obs);
    rec_obs(e, R_PROBE, key, e->obs->done);
    e->in_probe = 0;
    return e->obs->done;
}
static void bind_public(HEnv* e, nle_obs* o) {
    if (g_mode < 0) { DObs* d = &e->d; d->glyphs = o->glyphs; d->blstats = o->blstats; d->message = o->message; d->misc = o->misc; d->tty_chars = o->tty_chars; d->tty_colors = o->tty_colors; d->tty_cursor = o->tty_cursor; d->sdesc = NULL; d->inv_glyphs = o->inv_glyphs; d->inv_strs = o->inv_strs; d->inv_letters = o->inv_letters; d->inv_oclasses = o->inv_oclasses; d->internal = NULL; d->inv_state = e->inv_state; d->inv_true = e->inv_true; return; } // log-only: the env's buffers only, nothing bound on its behalf
    // screen descriptions stay unbound in every mode: the engine builds them with mksobj (core RNG draws) and marks
    // adjacent objects dknown; the stock backend runs without them, so the training stream must too // log-only mode must not request descriptions: the engine builds them with mksobj, which draws from the core RNG, and the real env never binds them
    if (!o->tty_chars) o->tty_chars = e->tty;
    if (!o->tty_colors) o->tty_colors = e->ttyc;
    if (!o->tty_cursor) o->tty_cursor = e->cur;
    if (!o->chars) o->chars = e->chars;
    if (!o->colors) o->colors = e->colors;
    if (!o->inv_strs) o->inv_strs = e->invstrs;
    DObs* d = &e->d;
    d->glyphs = o->glyphs; d->blstats = o->blstats; d->message = o->message; d->misc = o->misc;
    d->tty_chars = o->tty_chars; d->tty_colors = o->tty_colors; d->tty_cursor = o->tty_cursor; d->sdesc = NULL;
    d->inv_glyphs = o->inv_glyphs; d->inv_strs = o->inv_strs; d->inv_letters = o->inv_letters; d->inv_oclasses = o->inv_oclasses;
    d->internal = NULL; d->inv_state = e->inv_state; d->inv_true = e->inv_true; // derived copies; the real ones stay in the env's buffers
}

nle_ctx_t* __wrap_nle_start(nle_obs* obs, FILE* f, nle_settings* s) {
    static int init;
    if (!init) { init = 1; g_mode = getenv("NH_DERIVE_MODE") ? atoi(getenv("NH_DERIVE_MODE")) : 0; parse_real(getenv("NH_DERIVE_REAL")); if (g_mode == 0) { g_rec_dir = getenv("NH_DERIVE_REC"); g_rec_envs = getenv("NH_DERIVE_REC_ENVS") ? atoi(getenv("NH_DERIVE_REC_ENVS")) : 4; } const char* lp = getenv("NH_DERIVE_LOG"); if (lp) g_log = fopen(lp, "w"); atexit(report); }
    HEnv* e = NULL;
    lock();
    for (int i = 0; i < g_nenv; i++) if (g_envs[i] && !g_envs[i]->used) { e = g_envs[i]; break; }
    if (!e && g_nenv < HMAX) { e = (HEnv*)calloc(1, sizeof(HEnv)); e->idx = g_nenv; g_envs[g_nenv++] = e; }
    if (e) e->rng = NULL; // stale after the previous episode's context was torn down; set again on the first step
    if (e) e->used = 1;
    unlock();
    if (!e) { fprintf(stderr, "harness: too many envs\n"); exit(1); }
    bind_public(e, obs);
    e->ctx = __real_nle_start(obs, f, s); e->obs = obs;
    __real_nle_obs_refresh(e->ctx, obs);
    rec_start(e, s->initial_seeds.seeds[0]);
    dr_reset(&e->S, &e->d, (unsigned)s->initial_seeds.seeds[0]);
    if (g_mode >= 0) { dr_identity_from_text(&e->S, &e->d); if (e->S.role || e->S.race || e->S.gender || e->S.align != 1) e->S.ident_seen = 1; } // the welcome text is on screen right after the engine start; boundaries retry if it was missed
    { char msg[256]; dr_msg(&e->d, msg, sizeof msg); dr_update_memory(&e->S, &e->d, msg); dr_track_path(&e->S, &e->d, -1); }
    e->have_copy = 0; e->steps = 0;
    { const char* pd = getenv("NH_PETLOG"); if (pd) { char fn[512]; snprintf(fn, sizeof fn, "%s/%lx.pet", pd, s->initial_seeds.seeds[0]); if (e->petlog) fclose(e->petlog); e->petlog = fopen(fn, "w"); if (e->petlog) fprintf(e->petlog, "# role %d race %d\n", e->S.role, e->S.race); } }
    { const char* kd = getenv("NH_KEYLOG"); if (kd) { char fn[512]; snprintf(fn, sizeof fn, "%s/%lx.keys", kd, s->initial_seeds.seeds[0]); if (e->keylog) fclose(e->keylog); e->keylog = fopen(fn, "w"); e->seed0 = s->initial_seeds.seeds[0]; e->klog_n = 0; e->klog_marked = 0; e->invprev[0] = 0; e->stprev[0] = 0; e->rng = NULL; // the previous instance's RNG state is gone
        if (e->keylog) { DObs dr = e->d; dr.internal = obs->internal; dr.inv_state = obs->inv_state; dr.inv_true = obs->inv_true_glyphs; fprintf(e->keylog, "S %lx %lx %lx\n", s->initial_seeds.seeds[0], s->initial_seeds.seeds[1], dr_hash_sel(&dr));
            { unsigned long ph[9]; dr_obs_hash_parts(&dr, ph); fprintf(e->keylog, "P"); for (int g = 0; g < 9; g++) fprintf(e->keylog, " %lx", ph[g]); fprintf(e->keylog, "\n"); }
            { fprintf(e->keylog, "# internal="); if (obs->internal) for (int i = 0; i < 11; i++) fprintf(e->keylog, "%d ", obs->internal[i]); fprintf(e->keylog, "\n# inv="); for (int i = 0; i < 55 && e->d.inv_letters[i]; i++) fprintf(e->keylog, "%c:%d/%d ", e->d.inv_letters[i], e->d.inv_glyphs[i], e->d.inv_oclasses[i]); fprintf(e->keylog, "\n# inv_true="); if (obs->inv_true_glyphs) for (int i = 0; i < 55 && e->d.inv_letters[i]; i++) fprintf(e->keylog, "%c:%d ", e->d.inv_letters[i], obs->inv_true_glyphs[i]); fprintf(e->keylog, "\n# inv_state="); if (obs->inv_state) for (int i = 0; i < 55 && e->d.inv_letters[i]; i++) { fprintf(e->keylog, "%c:", e->d.inv_letters[i]); for (int f = 0; f < 8; f++) fprintf(e->keylog, "%d%s", obs->inv_state[i * 8 + f], f < 7 ? "," : " "); } fprintf(e->keylog, "\n# misc="); if (e->d.misc) for (int i = 0; i < 3; i++) fprintf(e->keylog, "%d ", e->d.misc[i]); fprintf(e->keylog, "\n# cursor=%d %d\n", e->d.tty_cursor ? e->d.tty_cursor[0] : -1, e->d.tty_cursor ? e->d.tty_cursor[1] : -1); }
            char m[256]; dr_msg(&e->d, m, sizeof m); fprintf(e->keylog, "# msg=%s\n# bl=", m); for (int i = 0; i < 27; i++) fprintf(e->keylog, "%ld ", e->d.blstats[i]); fprintf(e->keylog, "\n# map=");
            for (int k = 0; k < 21 * 79; k++) if (e->d.glyphs[k] != 2359 + 0 && e->d.glyphs[k] < 5976) fprintf(e->keylog, "%d:%d ", k, e->d.glyphs[k]); fprintf(e->keylog, "\n"); for (int r = 0; r < 24; r++) { char row[81]; dr_row(&e->d, r, row); fprintf(e->keylog, "# tty%02d=%s\n", r, row); } } } }
    return e->ctx;
}
// NH_KEYLOG_MAPAT=<file> with "seed key" lines: dump the map (and inventory strings) at those keys as well
static int mapat_wanted(unsigned long seed, long key) {
    static unsigned long ws[4096]; static long wk[4096]; static int wn = -1;
    if (wn < 0) { wn = 0; const char* f = getenv("NH_KEYLOG_MAPAT"); if (f) { FILE* fp = fopen(f, "r"); if (fp) { while (wn < 4096 && fscanf(fp, "%lx %ld", &ws[wn], &wk[wn]) == 2) wn++; fclose(fp); } } }
    for (int i = 0; i < wn; i++) if (ws[i] == seed && (wk[i] == key || wk[i] == key - 1)) return 1;
    return 0;
}
// core RNG state of the instance last stepped (nle_rng_state reads the current nh_cur); hashed per key and around hooks
#include "isaac64.h"
extern isaac64_ctx* nle_rng_state(int);
static unsigned long rng_hash(const void* p) { const unsigned char* b = (const unsigned char*)p; unsigned long h = 1469598103934665603UL; for (size_t i = 0; i < sizeof(isaac64_ctx); i++) h = (h ^ b[i]) * 1099511628211UL; return h; }
#define HOOK_RNG_CHECK(e, name, call) ({ unsigned long _h0 = ((e) && (e)->rng && (e)->keylog) ? rng_hash((e)->rng) : 0; __typeof__(call) _r = (call); if ((e) && (e)->rng && (e)->keylog && rng_hash((e)->rng) != _h0) fprintf((e)->keylog, "H %s %ld\n", name, (e)->klog_n); _r; })
static void klog_key(HEnv* e, nle_obs* obs, int key, int at_boundary, int done) { if (!e->keylog) return; { static long dbg = -2; if (dbg == -2) { const char* v = getenv("NH_INVDBG_KEY"); dbg = v ? atol(v) : -1; } if (dbg >= 0 && e->klog_n + 1 == dbg && obs->inv_letters && obs->inv_glyphs) { lock(); fprintf(stderr, "INVDBG k%ld", dbg); for (int i = 0; i < 55 && obs->inv_letters[i]; i++) fprintf(stderr, " %c[g=%d oc=%d]", obs->inv_letters[i], obs->inv_glyphs[i], obs->inv_oclasses ? obs->inv_oclasses[i] : -1); fprintf(stderr, "\n"); unlock(); } } DObs dr = e->d; dr.internal = obs->internal; dr.inv_state = obs->inv_state; dr.inv_true = obs->inv_true_glyphs; /* hash the engine's real values, not the harness copies */ if (g_mode < 0) { dr.glyphs = obs->glyphs; dr.blstats = obs->blstats; dr.message = obs->message; dr.misc = obs->misc; dr.inv_glyphs = obs->inv_glyphs; dr.inv_letters = obs->inv_letters; dr.inv_oclasses = obs->inv_oclasses; dr.tty_cursor = obs->tty_cursor; dr.tty_chars = obs->tty_chars; dr.inv_strs = obs->inv_strs; dr.sdesc = NULL; }
    fprintf(e->keylog, "K %d %lx %d", key, (done || !at_boundary) ? 0UL : dr_hash_sel(&dr), done); if (!done && at_boundary) { unsigned long ph[9]; dr_obs_hash_parts(&dr, ph); for (int g = 0; g < 9; g++) fprintf(e->keylog, " %lx", ph[g]); } fprintf(e->keylog, "\n"); e->klog_n++; if (!done) { fprintf(e->keylog, "# B%d", (int)e->klog_n); for (int i = 0; i < 27; i++) fprintf(e->keylog, " %ld", obs->blstats[i]); fprintf(e->keylog, " | I %d %d | %s | M %d%d%d\n", obs->internal ? obs->internal[6] : -1, obs->internal ? obs->internal[7] : -1, (const char*)obs->message, obs->misc ? obs->misc[0] : -1, obs->misc ? obs->misc[1] : -1, obs->misc ? obs->misc[2] : -1); }
 if (!done && obs->inv_strs) { char cur[55 * 64]; int p = 0; for (int i = 0; i < 55 && obs->inv_letters[i] && p < (int)sizeof cur - 70; i++) p += snprintf(cur + p, sizeof cur - p, "%c=\"%.60s\" ", obs->inv_letters[i], (const char*)obs->inv_strs + i * 80); cur[p] = 0; if (strcmp(cur, e->invprev)) { fprintf(e->keylog, "# V%d %s\n", (int)e->klog_n, cur); snprintf(e->invprev, sizeof e->invprev, "%s", cur); } }
 if (!done && obs->inv_state) { char cur[55 * 24]; int p = 0; for (int i = 0; i < 55 && obs->inv_letters[i] && p < (int)sizeof cur - 30; i++) { p += snprintf(cur + p, sizeof cur - p, "%c:", obs->inv_letters[i]); for (int f = 0; f < 8; f++) p += snprintf(cur + p, sizeof cur - p, "%d%s", obs->inv_state[i * 8 + f], f < 7 ? "," : " "); } cur[p] = 0; if (strcmp(cur, e->stprev)) { fprintf(e->keylog, "# W%d %s\n", (int)e->klog_n, cur); snprintf(e->stprev, sizeof e->stprev, "%s", cur); } }
 if (e->rng) fprintf(e->keylog, "KR %d %lx %u\n", (int)e->klog_n, rng_hash(e->rng), ((isaac64_ctx*)e->rng)->n);
 if (done) fprintf(e->keylog, "E score=%ld turn=%ld depth=%ld how=%d\n", obs->blstats[9], obs->blstats[20], obs->blstats[12], obs->how_done);
 if (!done && e->klog_n == 1) memcpy(e->mapprev, obs->glyphs, sizeof e->mapprev);
 else if (!done && e->klog_n > 1) { int first = 1; for (int k = 0; k < 21 * 79; k++) if (obs->glyphs[k] != e->mapprev[k]) { if (first) { fprintf(e->keylog, "# D%d ", (int)e->klog_n); first = 0; } fprintf(e->keylog, "%d:%d ", k, obs->glyphs[k]); e->mapprev[k] = obs->glyphs[k]; } if (!first) fprintf(e->keylog, "\n"); }
 if (!done && (e->klog_n <= 3 || mapat_wanted(e->seed0, e->klog_n))) { if (e->klog_n > 3 && obs->inv_strs) { fprintf(e->keylog, "# INV%d ", (int)e->klog_n); for (int i = 0; i < 55 && obs->inv_letters[i]; i++) fprintf(e->keylog, "%c=\"%.60s\"[g=%d] ", obs->inv_letters[i], (const char*)obs->inv_strs + i * 80, obs->inv_glyphs ? obs->inv_glyphs[i] : -1); fprintf(e->keylog, "\n"); } fprintf(e->keylog, "# M%d ", (int)e->klog_n); for (int k = 0; k < 21 * 79; k++) if (obs->glyphs[k] != 2359) fprintf(e->keylog, "%d:%d ", k, obs->glyphs[k]); fprintf(e->keylog, "\n"); } if (done) { fclose(e->keylog); e->keylog = NULL; } }
nle_ctx_t* __wrap_nle_step(nle_ctx_t* c, nle_obs* obs) {
    HEnv* e = find_env(c);
    int key = obs->action;
    unsigned long hpre = (e && e->rng) ? rng_hash(e->rng) : 0;
    if (e && g_mode < 0 && e->pend) { if (e->keylog) klog_key(e, obs, e->pend_key, 0, 0); e->pend = 0; } // a key with no refresh after it: not a boundary, hash 0
    __real_nle_step(c, obs);
    if (e) e->rng = (void*)nle_rng_state(0); // this instance was just stepped: nh_cur is its context
    if (e && e->keylog && key >= (int)'0' && key <= (int)'9' && hpre && rng_hash(e->rng) != hpre) fprintf(e->keylog, "H digit_step %ld\n", e->klog_n + 1);
    if (e && g_mode < 0) { // log-only: touch nothing the env does not touch; the boundary hash is taken inside the env's own refresh
        if (e->keylog) { if (obs->done) klog_key(e, obs, key, 1, 1); else { e->pend = 1; e->pend_key = key; } }
        return c;
    }
    { unsigned long h0 = (e && e->rng) ? rng_hash(e->rng) : 0; if (!obs->done) __real_nle_obs_refresh(c, obs); if (e && e->rng && e->keylog && rng_hash(e->rng) != h0) fprintf(e->keylog, "H obs_refresh %ld\n", e->klog_n + 1); }
    if (e) {
        bind_public(e, obs);
        rec_obs(e, R_KEY, key, obs->done);
        if (e->keylog) klog_key(e, obs, key, 1, obs->done);
        if (g_mode >= 0 && dr_after_key(&e->S, &e->d, e, harness_send, key, obs->done) && g_mode > 0) { obs->done = 1; obs->how_done = -1; }
        if (obs->done) drec_close(&e->rec);
    }
    return c;
}
nle_ctx_t* __wrap_nle_obs_refresh(nle_ctx_t* c, nle_obs* obs) {
    if (g_mode < 0) { HEnv* e = find_env(c); nle_ctx_t* rr = __real_nle_obs_refresh(c, obs);
        if (e && e->keylog && e->pend) { klog_key(e, obs, e->pend_key, 1, 0); e->pend = 0; if (e->keylog && e->klog_n > e->klog_marked) { fprintf(e->keylog, "R\n"); e->klog_marked = e->klog_n; } }
        return rr; }
    { HEnv* eb = find_env(c); if (eb && eb->keylog && eb->klog_n > eb->klog_marked) { fprintf(eb->keylog, "R\n"); eb->klog_marked = eb->klog_n; }
      if (eb && eb->rng && eb->keylog) { unsigned long h0 = rng_hash(eb->rng); nle_ctx_t* rr = __real_nle_obs_refresh(c, obs); if (rng_hash(eb->rng) != h0) fprintf(eb->keylog, "H env_refresh %ld\n", eb->klog_n); return rr; } } // env step boundary after the last key
    HEnv* e = find_env(c);
    __real_nle_obs_refresh(c, obs);
    if (!e || obs->done || e->in_probe) return c;
    bind_public(e, obs);
    rec_obs(e, R_BOUNDARY, 0, 0);
    if (e->petlog) { int hx = (int)obs->blstats[0], hy = (int)obs->blstats[1]; int best = -1, np = 0;
        for (int k = 0; k < 21 * 79; k++) { int g = obs->glyphs[k]; if (g >= NHT_GLYPH_PET_OFF && g < NHT_GLYPH_PET_OFF + NUMMONS) { np++; int d = abs(k % 79 - hx) > abs(k / 79 - hy) ? abs(k % 79 - hx) : abs(k / 79 - hy); if (best < 0 || d < best) best = d; } }
        e->steps++; fprintf(e->petlog, "%ld %ld %ld %d %d %d %d %ld %ld %ld %ld\n", e->steps, obs->blstats[20], obs->blstats[24], hx, hy, best, np, obs->blstats[10], obs->blstats[13], obs->blstats[18], obs->blstats[19]); }
    // the fork's glyphs are the truth (appearance ids, hero tile); keep a copy to compare the export against
    memcpy(e->glyph_copy, obs->glyphs, sizeof e->glyph_copy); memcpy(e->inv_copy, obs->inv_glyphs, sizeof e->inv_copy); e->have_copy = 1;
    if (g_mode >= 0 && !e->S.ident_seen) { dr_identity_from_text(&e->S, &e->d); if (e->S.role || e->S.race || e->S.gender || e->S.align != 1) e->S.ident_seen = 1; }
    if (g_mode >= 0) { static int dl = -1; if (dl < 0) dl = getenv("NH_STOCK_DISCLOG") != NULL || getenv("NH_STOCK_PILELOG") != NULL; dr_log_this = dl; dr_boundary(&e->S, &e->d, e, harness_send); }
    // hero tile: the fork draws the top object else terrain on the hero's square
    if (e->S.d_valid) { int k = e->S.d_r * 79 + e->S.d_c; int under = e->S.top >= 0 ? e->S.top : e->S.terrain; if (under < 0) under = CMAP_OFF + 19;
        int real = obs->glyphs[k]; int derm = dr_map_glyph(&e->S, (short)under); int bad = real != derm; note(C_HERO, bad); if (bad) logmis(e, "hero_tile", real, derm); // the fork maps the hero tile eagerly (maybe_true_glyph at every fill); compare the mapped value
        if (use_der(C_HERO)) obs->glyphs[k] = (short)dr_map_glyph(&e->S, (short)under); } // derived mode: the hero tile the stock derive would show
    // engraving bits
    { int eb = e->S.engr_bits; for (int k = 0; k < 21 * 79; k++) if (obs->glyphs[k] >= SWALLOW_OFF && obs->glyphs[k] < SWALLOW_HI) { eb |= 4; break; }
      int real = obs->internal ? obs->internal[6] : 0; note(C_ENGR, real != eb); if (real != eb) logmis(e, "engraving_bits", real, eb); if (use_der(C_ENGR) && obs->internal) { obs->internal[6] = eb; obs->internal[5] = (int)e->S.bless_est; } } // derived mode: engraving bits + prayer-cooldown estimate, never the engine's ublesscnt
    // identity structure: a type the fork prints by name must be in the derived discovered set (else stock would show an
    // appearance for a known item); an undiscovered item of a shuffled class must display an id inside the derived shuffle range
    if (obs->inv_true_glyphs) {
        for (int i = 0; i < 55 && obs->inv_letters[i]; i++) {
            int g = obs->inv_glyphs[i], tg = obs->inv_true_glyphs[i];
            if (tg != NO_GLYPH && tg >= OBJ_OFF && tg < CMAP_OFF) { int tidx = tg - OBJ_OFF; int bad = g_shuffled[tidx] && !e->S.discovered[tidx]; note(C_DISC, bad);
                if (bad && g_log) { static int shown; if (shown < 40) { shown++; char t[81]; memcpy(t, obs->inv_strs + i * 80, 80); t[80] = 0; lock(); fprintf(g_log, "DISCMIS T=%ld true=%s text=\"%s\"\n", obs->blstats[20], NHT_OBJ_NAME[tidx], t); unlock(); } } }
            if (tg == NO_GLYPH && g >= OBJ_OFF && g < CMAP_OFF) { int idx = g - OBJ_OFF; int c = NHT_OBJ_CLASS[idx]; int shuffled_class = c == 4 || c == 5 || c == 8 || c == 9 || c == 10 || c == 11;
                if (shuffled_class && g_in_range[idx]) { int bad = !g_app_slot[idx]; note(C_RANGE, bad); if (bad && g_log) { static int shown2; if (shown2 < 40) { shown2++; char t[81]; memcpy(t, obs->inv_strs + i * 80, 80); t[80] = 0; lock(); fprintf(g_log, "RANGEMIS T=%ld shown=%s class=%d text=\"%s\"\n", obs->blstats[20], NHT_OBJ_NAME[idx], c, t); unlock(); } } } }
        }
        // floor objects of shuffled classes shown by the fork: their displayed id must sit inside a derived shuffle range too
        for (int k = 0; k < 21 * 79; k++) { int g = obs->glyphs[k]; if (g < OBJ_OFF || g >= CMAP_OFF) continue; int idx = g - OBJ_OFF; int c = NHT_OBJ_CLASS[idx];
            if ((c == 4 || c == 5 || c == 8 || c == 9 || c == 10 || c == 11) && g_in_range[idx]) { int bad = !g_app_slot[idx]; note(C_MAPRANGE, bad); } }
    }
    // inventory state and true glyphs
    if (obs->inv_state && obs->inv_true_glyphs) {
        for (int i = 0; i < 55 && obs->inv_letters[i]; i++) {
            int bad = memcmp(obs->inv_state + i * 8, e->inv_state + i * 8, 8) != 0; note(C_INVST, bad);
            int badt = obs->inv_true_glyphs[i] != e->inv_true[i]; note(C_INVTRUE, badt);
            if ((bad || badt) && g_log) { static int shown; if (shown < 40000) { shown++; char t[81]; memcpy(t, obs->inv_strs + i * 80, 80); t[80] = 0; lock();
                fprintf(g_log, "INVMIS T=%ld slot=%d real_true=%d der_true=%d real_st=[%d %d %d %d %d %d %d %d] der_st=[%d %d %d %d %d %d %d %d] text=\"%s\"\n", obs->blstats[20], i, obs->inv_true_glyphs[i], e->inv_true[i],
                    obs->inv_state[i*8], obs->inv_state[i*8+1], obs->inv_state[i*8+2], obs->inv_state[i*8+3], obs->inv_state[i*8+4], obs->inv_state[i*8+5], obs->inv_state[i*8+6], obs->inv_state[i*8+7],
                    e->inv_state[i*8], e->inv_state[i*8+1], e->inv_state[i*8+2], e->inv_state[i*8+3], e->inv_state[i*8+4], e->inv_state[i*8+5], e->inv_state[i*8+6], e->inv_state[i*8+7], t); unlock(); } }
            if (use_der(C_INVST)) memcpy(obs->inv_state + i * 8, e->inv_state + i * 8, 8);
            if (use_der(C_INVTRUE)) obs->inv_true_glyphs[i] = e->inv_true[i];
        }
    }
    return c;
}
void __wrap_nle_end(nle_ctx_t* c) { HEnv* e = find_env(c); __real_nle_end(c); if (e) { drec_close(&e->rec); e->used = 0; e->ctx = NULL; e->rng = NULL; if (e->petlog) { fprintf(e->petlog, "# end how %d\n", e->obs ? e->obs->how_done : -9); fclose(e->petlog); e->petlog = NULL; } } }
void __wrap_nle_identity(nle_ctx_t* c, int* r, int* rc, int* g, int* a) {
    HEnv* e = find_env(c); __real_nle_identity(c, r, rc, g, a);
    if (e) { { long v[4] = { *r, *rc, *g, *a }; rec_hook(e, C_IDENT, 0, NULL, 4, v); } int bad = *r != e->S.role || *rc != e->S.race || *g != e->S.gender; note(C_IDENT, bad); if (bad) logmis(e, "identity", *r * 100 + *rc * 10 + *g, e->S.role * 100 + e->S.race * 10 + e->S.gender);
        if (use_der(C_IDENT)) { *r = e->S.role; *rc = e->S.race; *g = e->S.gender; *a = e->S.align; } }
}

#define HOOK_INT(name, chan, field, cmp) \
int __wrap_##name(nle_ctx_t* c) { HEnv* e = find_env(c); int r = __real_##name(c); if (!e) return r; { long v = r; rec_hook(e, chan, 0, NULL, 1, &v); } int d = e->S.field; int bad = cmp; note(chan, bad); if (bad) logmis(e, #name, r, d); return use_der(chan) ? d : r; }
int __wrap_nle_terrain_underfoot(nle_ctx_t* c) { HEnv* e = find_env(c); int r = __real_nle_terrain_underfoot(c); if (!e) return r; { long v = r; rec_hook(e, C_TERR, 0, NULL, 1, &v); } int d = e->S.terrain; int bad = r != d; note(C_TERR, bad);
    if (bad) { logmis(e, "nle_terrain_underfoot", r, d);
        if (g_log && e->obs) { const nle_obs* o = e->obs; int hr = (int)o->blstats[1], hc = (int)o->blstats[0]; int k = hr * 79 + hc; DLevel* L = dr_level(&e->S, &e->d);
            lock(); fprintf(g_log, "TERRMIS T=%ld hero %d,%d real %d derived %d mem %d heroglyph %d probe_turn %ld cond %lx misc %d%d%d msg=\"%.50s\" top=\"%.40s\"\n", o->blstats[20], hr, hc, r, d, (k >= 0 && k < 21 * 79 && L) ? (int)L->terr[k] : -2, (k >= 0 && k < 21 * 79) ? (int)o->glyphs[k] : -2, e->S.probe_turn, (unsigned long)o->blstats[25], o->misc ? o->misc[0] : -1, o->misc ? o->misc[1] : -1, o->misc ? o->misc[2] : -1, o->message ? (const char*)o->message : "", o->tty_chars ? (const char*)o->tty_chars : ""); unlock(); } }
    return use_der(C_TERR) ? d : r; }
HOOK_INT(nle_food_underfoot, C_FOOD, food, (r != 0) != (d != 0))
HOOK_INT(nle_container_at, C_CONT, cont, (r != 0) != (d != 0))
int __wrap_nle_inside_shop(nle_ctx_t* c) { HEnv* e = find_env(c); int r = __real_nle_inside_shop(c); if (!e) return r; { long v = r; rec_hook(e, C_SHOP, 0, NULL, 1, &v); } int d = e->S.inshop; int bad = (r != 0) != (d != 0); note(C_SHOP, bad);
    if (bad) { logmis(e, "nle_inside_shop", r, d); if (g_log && e->obs) { const nle_obs* o = e->obs; DLevel* L = dr_level(&e->S, &e->d); int k = (int)o->blstats[1] * 79 + (int)o->blstats[0];
        lock(); fprintf(g_log, "SHOPMIS T=%ld hero %ld,%ld real %d derived %d shop_set %d shopcell %d terrain %d msg=\"%.60s\"\n", o->blstats[20], o->blstats[1], o->blstats[0], r, d, L ? L->shop_set : -1, (L && k >= 0 && k < 21 * 79) ? L->shop[k] : -1, e->S.terrain, o->message ? (const char*)o->message : ""); unlock(); } }
    return use_der(C_SHOP) ? d : r; }
HOOK_INT(nle_lnc_bits, C_LNC, lnc, r != d)
HOOK_INT(nle_intrinsics, C_INTR, intr, r != d)
HOOK_INT(nle_cast_blocked, C_CAST, castblk, (r != 0) != (d != 0))
long __wrap_nle_shop_price(nle_ctx_t* c) { HEnv* e = find_env(c); long r = HOOK_RNG_CHECK(e, "shop_price", __real_nle_shop_price(c)); if (!e) return r; rec_hook(e, C_PRICE, 0, NULL, 1, &r); long d = e->S.price; note(C_PRICE, r != d); if (r != d) logmis(e, "shop_price", r, d); return use_der(C_PRICE) ? d : r; }
int __wrap_nle_peaceful_at(nle_ctx_t* c, int x, int y) {
    HEnv* e = find_env(c); int r = HOOK_RNG_CHECK(e, "peaceful_at", __real_nle_peaceful_at(c, x, y)); if (!e) return r;
    { long a[2] = { x, y }, v = r; rec_hook(e, C_PEACE, 2, a, 1, &v); }
    int d = (x >= 1 && x < 80 && y >= 0 && y < 21) ? e->S.peace[y * 79 + (x - 1)] : 0;
    note(C_PEACE, r != d); if (r != d) { logmis(e, "peaceful_at", r, d);
        if (g_log && x >= 1 && x < 80 && y >= 0 && y < 21) { int k = y * 79 + (x - 1); const nle_obs* o = e->obs; lock();
            fprintf(g_log, "PEACEMIS T=%ld cell %d,%d glyph %d cached_g %d cached_t %ld hero %ld,%ld cond %lx misc %d%d%d deferred %d text=\"%.60s\"\n", o ? o->blstats[20] : -1L, y, x - 1, o ? (int)o->glyphs[k] : -1, (int)e->S.peace_g[k], e->S.peace_t[k], o ? o->blstats[1] : -1L, o ? o->blstats[0] : -1L, o ? (unsigned long)o->blstats[25] : 0UL, o && o->misc ? o->misc[0] : -1, o && o->misc ? o->misc[1] : -1, o && o->misc ? o->misc[2] : -1, e->S.probes_deferred, o && o->message ? (const char*)o->message : "");
            unlock(); } }
    return use_der(C_PEACE) ? d : r;
}
void __wrap_nle_weight(nle_ctx_t* c, int* wt, int* cap) {
    HEnv* e = find_env(c); int rw, rc; { unsigned long _h0 = (e && e->rng) ? rng_hash(e->rng) : 0; __real_nle_weight(c, &rw, &rc); if (e && e->rng && e->keylog && rng_hash(e->rng) != _h0) fprintf(e->keylog, "H weight %ld\n", e->klog_n); } if (!e) { *wt = rw; *cap = rc; return; }
    { long v[2] = { rw, rc }; rec_hook(e, C_WT, 0, NULL, 2, v); }
    note(C_WT, abs(rw - e->S.wt) > 10);
    if (abs(rw - e->S.wt) > 10 && g_log) { static int shown; if (shown < 30) { shown++; lock(); fprintf(g_log, "WTMIS T=%ld real=%d derived=%d items:", e->obs->blstats[20], rw, e->S.wt);
        for (int i = 0; i < 55 && e->obs->inv_letters[i]; i++) { char t[81]; memcpy(t, e->obs->inv_strs + i * 80, 80); t[80] = 0; fprintf(g_log, " [%d:%s]", e->obs->inv_glyphs[i], t); } fprintf(g_log, "\n"); unlock(); } }
    note(C_CAP, rc != e->S.cap); if (rc != e->S.cap) logmis(e, "capacity", rc, e->S.cap);
    *wt = use_der(C_WT) ? e->S.wt : rw; *cap = use_der(C_CAP) ? e->S.cap : rc;
}
int __wrap_nle_spells(nle_ctx_t* c, short* a, signed char* b, signed char* d, int* ee, int n) {
    HEnv* e = find_env(c); short ra[8]; signed char rb[8], rd[8]; int re[8];
    int rn = HOOK_RNG_CHECK(e, "spells", __real_nle_spells(c, ra, rb, rd, re, n < 8 ? n : 8));
    if (!e) { int m = n < 8 ? n : 8; m = m < rn ? m : rn; for (int i = 0; i < m; i++) { a[i] = ra[i]; b[i] = rb[i]; d[i] = rd[i]; ee[i] = re[i]; } return m; }
    { long v[33]; v[0] = rn; for (int i = 0; i < 8; i++) { v[1 + i] = i < rn ? ra[i] : 0; v[9 + i] = i < rn ? rb[i] : 0; v[17 + i] = i < rn ? rd[i] : 0; v[25 + i] = i < rn ? re[i] : 0; } rec_hook(e, C_SPELLS, 0, NULL, 33, v); }
    int bad = rn != e->S.nsp;
    for (int i = 0; i < rn && i < e->S.nsp; i++) bad |= ra[i] != e->S.sp_ids[i] || rb[i] != e->S.sp_levs[i] || (re[i] > 0) != (e->S.sp_knows[i] > 0);
    note(C_SPELLS, bad); if (bad) logmis(e, "spells", rn, e->S.nsp);
    int m = n < 8 ? n : 8;
    if (use_der(C_SPELLS)) { m = m < e->S.nsp ? m : e->S.nsp; for (int i = 0; i < m; i++) { a[i] = e->S.sp_ids[i]; b[i] = e->S.sp_levs[i]; d[i] = e->S.sp_fails[i]; ee[i] = e->S.sp_knows[i]; } return m; }
    m = m < rn ? m : rn; for (int i = 0; i < m; i++) { a[i] = ra[i]; b[i] = rb[i]; d[i] = rd[i]; ee[i] = re[i]; } return m;
}
int __wrap_nle_path_drain(nle_ctx_t* c, short* p, int n) {
    HEnv* e = find_env(c); short rp[2 * 512]; int rn = HOOK_RNG_CHECK(e, "path_drain", __real_nle_path_drain(c, rp, n < 512 ? n : 512));
    if (!e) { int m = n < rn ? n : rn; memcpy(p, rp, 2 * m * sizeof(short)); return m; }
    { long v[1 + 2 * 512]; v[0] = rn; for (int i = 0; i < 2 * rn && i < 2 * 512; i++) v[1 + i] = rp[i]; rec_hook(e, C_PATH, 0, NULL, 1 + 2 * (rn < 512 ? rn : 512), v); }
    int bad = 0; // tile sets, order-insensitive
    for (int i = 0; i < rn && !bad; i++) { int f = 0; for (int j = 0; j < e->S.path_n; j++) if (e->S.path[2 * j] == rp[2 * i] && e->S.path[2 * j + 1] == rp[2 * i + 1]) { f = 1; break; } if (!f) bad = 1; }
    for (int j = 0; j < e->S.path_n && !bad; j++) { int f = 0; for (int i = 0; i < rn; i++) if (e->S.path[2 * j] == rp[2 * i] && e->S.path[2 * j + 1] == rp[2 * i + 1]) { f = 1; break; } if (!f) bad = 1; }
    note(C_PATH, bad); if (bad) logmis(e, "path", rn, e->S.path_n);
    int m;
    if (use_der(C_PATH)) { m = n < e->S.path_n ? n : e->S.path_n; memcpy(p, e->S.path, 2 * m * sizeof(short)); e->S.path_n = 0; return m; }
    m = n < rn ? n : rn; memcpy(p, rp, 2 * m * sizeof(short)); e->S.path_n = 0; return m;
}

extern int __real_nle_discoveries(nle_ctx_t*);
int __wrap_nle_discoveries(nle_ctx_t* c) { HEnv* e = find_env(c); return HOOK_RNG_CHECK(e, "discoveries", __real_nle_discoveries(c)); }
