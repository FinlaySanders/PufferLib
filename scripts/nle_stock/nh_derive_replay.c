// Offline replay of the derivations (nh_derive.h) over recordings made by the fork harness (NH_DERIVE_REC=<dir>,
// nh_derive_rec.h). No engine: every key the derive saw, every probe reply and the fork's truth at every hook are in
// the file, so this re-runs the derive and reports per-channel mismatch rates plus examples in seconds.
// A probe the replayed derive sends that the recording does not have (or vice versa) is a divergence: the derive's
// probing changed, the rest of that episode cannot be replayed and is skipped (counted; validate such changes live).
//   nh_derive_replay [--examples N] [--all] [--baseline rates.txt] [--out rates.txt] <file.drec.gz | dir> ...
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <stdarg.h>
#include <sys/stat.h>
#include "nh_derive.h"
#include "nh_derive_rec.h"

enum { C_TERR, C_FOOD, C_CONT, C_PRICE, C_SHOP, C_PEACE, C_SPELLS, C_LNC, C_WT, C_CAP, C_INTR, C_CAST, C_PATH, C_ENGR, C_HERO, C_INVST, C_INVTRUE, C_IDENT, C_DISC, C_RANGE, C_MAPRANGE, C_N };
static const char* C_NAMES[C_N] = {"terrain", "food_underfoot", "container_at", "shop_price", "inside_shop", "peaceful_at", "spells", "lnc_bits", "weight", "capacity", "intrinsics", "cast_blocked", "path", "engraving_bits", "hero_tile", "inv_state", "inv_true_glyph", "identity", "discovered_set", "shuffle_range", "map_shuffle_range"};
static long M_q[C_N], M_bad[C_N];
static int g_examples = 5, g_all; static int E_n[C_N]; static int g_watch = -1;

typedef struct {
    DRecR r; DObs d; DState S; DRecObs work; DRecObs* o; signed char inv_state[55 * 8]; short inv_true[55]; // work = the buffers the derive reads and may write (dr_restore); r.cur stays the pristine recorded state the deltas apply to
    int diverged; int div_want, div_type, div_key; long probes, keys, bounds; unsigned long seed; long step;
    long watch_last; int watch_init; char mring[6][96]; long mring_t[6]; int mring_n; // --watch: last messages seen on env keys
} Rep;

static void note(int c, int bad) { M_q[c]++; if (bad) M_bad[c]++; }
static void example(Rep* R, int c, const char* fmt, ...) __attribute__((format(printf, 3, 4)));
static void example(Rep* R, int c, const char* fmt, ...) {
    if (!g_all && E_n[c] >= g_examples) return; E_n[c]++;
    char msg[256]; dr_msg(&R->d, msg, sizeof msg);
    printf("MIS %-15s seed=%lx step=%ld T=%ld hero=%ld,%ld ", C_NAMES[c], R->seed, R->step, R->o->blstats[20], R->o->blstats[1], R->o->blstats[0]);
    va_list ap; va_start(ap, fmt); vprintf(fmt, ap); va_end(ap);
    printf(" msg=\"%.70s\"\n", msg);
}
static int mock_send(void* ctx, int key) {
    Rep* R = (Rep*)ctx; DRecHdr h; if (R->diverged) return 0;
    if (!drec_next(&R->r, &h)) { R->diverged = 2; return 0; }
    if (h.type != R_PROBE || h.key != key) { drec_unread(&R->r, &h); R->diverged = 1; R->div_want = key; R->div_type = h.type; R->div_key = h.key; return 0; }
    if (!drec_read_obs(&R->r)) { R->diverged = 2; return 0; }
    R->work = R->r.cur; R->probes++; return h.done;
}
static void bind(Rep* R) {
    DRecObs* o = R->o; DObs* d = &R->d; memset(d, 0, sizeof *d);
    d->glyphs = o->glyphs; d->blstats = o->blstats; d->message = o->message; d->misc = o->misc; d->tty_chars = o->tty_chars; d->tty_colors = o->tty_colors; d->tty_cursor = o->tty_cursor;
    d->inv_glyphs = o->inv_glyphs; d->inv_strs = o->inv_strs; d->inv_letters = o->inv_letters; d->inv_oclasses = o->inv_oclasses;
    d->inv_state = R->inv_state; d->inv_true = R->inv_true;
}
static void identity_try(Rep* R) { if (R->S.ident_seen) return; dr_identity_from_text(&R->S, &R->d); if (R->S.role || R->S.race || R->S.gender || R->S.align != 1) R->S.ident_seen = 1; }
static void inv_text(const DRecObs* o, int i, char* t) { memcpy(t, o->inv_strs + i * 80, 80); t[80] = 0; }

static void boundary_checks(Rep* R) {
    DState* S = &R->S; DRecObs* o = R->o;
    if (S->d_valid) { int k = S->d_r * 79 + S->d_c; int under = S->top >= 0 ? S->top : S->terrain; if (under < 0) under = CMAP_OFF + 19;
        int real = o->glyphs[k], derm = dr_map_glyph(S, (short)under); note(C_HERO, real != derm); if (real != derm) example(R, C_HERO, "real=%d derived=%d top=%d terrain=%d", real, derm, S->top, S->terrain); }
    { int eb = S->engr_bits; for (int k = 0; k < DR_CELLS; k++) if (o->glyphs[k] >= SWALLOW_OFF && o->glyphs[k] < SWALLOW_HI) { eb |= 4; break; }
      int real = o->internal[6]; note(C_ENGR, real != eb); if (real != eb) example(R, C_ENGR, "real=%d derived=%d", real, eb); }
    for (int i = 0; i < 55 && o->inv_letters[i]; i++) {
        int g = o->inv_glyphs[i], tg = o->inv_true[i];
        if (tg != NO_GLYPH && tg >= OBJ_OFF && tg < CMAP_OFF) { int tidx = tg - OBJ_OFF; int bad = g_shuffled[tidx] && !S->discovered[tidx]; note(C_DISC, bad);
            if (bad) { char t[81]; inv_text(o, i, t); example(R, C_DISC, "true=%s text=\"%s\"", NHT_OBJ_NAME[tidx], t); } }
        if (tg == NO_GLYPH && g >= OBJ_OFF && g < CMAP_OFF) { int idx = g - OBJ_OFF; int c = NHT_OBJ_CLASS[idx]; int sc = c == 4 || c == 5 || c == 8 || c == 9 || c == 10 || c == 11;
            if (sc && g_in_range[idx]) { int bad = !g_app_slot[idx]; note(C_RANGE, bad); if (bad) { char t[81]; inv_text(o, i, t); example(R, C_RANGE, "glyph=%d text=\"%s\"", g, t); } } }
    }
    for (int k = 0; k < DR_CELLS; k++) { int g = o->glyphs[k]; if (g < OBJ_OFF || g >= CMAP_OFF) continue; int idx = g - OBJ_OFF; int c = NHT_OBJ_CLASS[idx];
        if ((c == 4 || c == 5 || c == 8 || c == 9 || c == 10 || c == 11) && g_in_range[idx]) note(C_MAPRANGE, !g_app_slot[idx]); }
    for (int i = 0; i < 55 && o->inv_letters[i]; i++) {
        int bad = memcmp(o->inv_state + i * 8, R->inv_state + i * 8, 8) != 0; note(C_INVST, bad);
        int badt = o->inv_true[i] != R->inv_true[i]; note(C_INVTRUE, badt);
        if (bad || badt) { char t[81]; inv_text(o, i, t); const signed char* a = o->inv_state + i * 8; const signed char* b = R->inv_state + i * 8;
            example(R, bad ? C_INVST : C_INVTRUE, "slot=%c real_true=%d der_true=%d real_st=[%d %d %d %d %d %d %d %d] der_st=[%d %d %d %d %d %d %d %d] text=\"%s\"", o->inv_letters[i], o->inv_true[i], R->inv_true[i],
                a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7], b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7], t); }
    }
}
static void watch(Rep* R, int chan, long real, long der) {
    if (chan != g_watch) return; if (R->watch_init && real == R->watch_last) return;
    printf("WATCH %-12s seed=%lx step=%ld T=%ld real %ld -> %ld (derived %ld) cond=%lx recent:", C_NAMES[chan], R->seed, R->step, R->o->blstats[20], R->watch_init ? R->watch_last : -1L, real, der, (unsigned long)R->o->blstats[25]);
    for (int i = 0; i < R->mring_n && i < 6; i++) { int j = (R->mring_n - 1 - i) % 6; printf(" [T%ld \"%s\"]", R->mring_t[j], R->mring[j]); } printf("\n");
    R->watch_last = real; R->watch_init = 1;
}
static void hook_check(Rep* R, int chan, int nargs, const long* a, int nvals, const long* v) {
    DState* S = &R->S; long r = nvals ? v[0] : 0; (void)nargs;
    if (g_watch >= 0) { if (chan == C_WT) { watch(R, C_WT, v[0], S->wt); watch(R, C_CAP, v[1], S->cap); } else if (chan == g_watch) watch(R, chan, r, chan == C_TERR ? S->terrain : chan == C_INTR ? S->intr : chan == C_LNC ? S->lnc : chan == C_PRICE ? S->price : -1); }
    switch (chan) {
    case C_TERR: note(C_TERR, r != S->terrain); if (r != S->terrain) example(R, C_TERR, "real=%ld derived=%d prev_terr=%d", r, S->terrain, S->prev_terr); break;
    case C_FOOD: { int bad = (r != 0) != (S->food != 0); note(C_FOOD, bad); if (bad) example(R, C_FOOD, "real=%ld derived=%d top=%d", r, S->food, S->top); } break;
    case C_CONT: { int bad = (r != 0) != (S->cont != 0); note(C_CONT, bad); if (bad) example(R, C_CONT, "real=%ld derived=%d top=%d", r, S->cont, S->top); } break;
    case C_SHOP: { int bad = (r != 0) != (S->inshop != 0); note(C_SHOP, bad); if (bad) example(R, C_SHOP, "real=%ld derived=%d", r, S->inshop); } break;
    case C_PRICE: note(C_PRICE, r != S->price); if (r != S->price) example(R, C_PRICE, "real=%ld derived=%ld inshop=%d top=%d", r, S->price, S->inshop, S->top); break;
    case C_LNC: note(C_LNC, r != S->lnc); if (r != S->lnc) example(R, C_LNC, "real=%ld derived=%d", r, S->lnc); break;
    case C_INTR: note(C_INTR, r != S->intr); if (r != S->intr) example(R, C_INTR, "real=%ld derived=%d form=%d form_dirty=%d gained=%d", r, S->intr, S->form, S->form_dirty, S->intr_gained); break;
    case C_CAST: { int bad = (r != 0) != (S->castblk != 0); note(C_CAST, bad); if (bad) example(R, C_CAST, "real=%ld derived=%d", r, S->castblk); } break;
    case C_IDENT: { int bad = v[0] != S->role || v[1] != S->race || v[2] != S->gender; note(C_IDENT, bad); if (bad) example(R, C_IDENT, "real=%ld/%ld/%ld derived=%d/%d/%d", v[0], v[1], v[2], S->role, S->race, S->gender); } break;
    case C_PEACE: { long x = a[0], y = a[1]; int d = (x >= 1 && x < 80 && y >= 0 && y < 21) ? S->peace[y * 79 + (x - 1)] : 0; note(C_PEACE, r != d);
        if (r != d) { int k = y * 79 + (x - 1); example(R, C_PEACE, "cell=%ld,%ld real=%ld derived=%d glyph=%d cached_g=%d cached_t=%ld", y, x - 1, r, d, (k >= 0 && k < DR_CELLS) ? R->o->glyphs[k] : -1, (k >= 0 && k < DR_CELLS) ? S->peace_g[k] : -1, (k >= 0 && k < DR_CELLS) ? S->peace_t[k] : -1L); } } break;
    case C_WT: { long rw = v[0], rc = v[1]; int bw = labs(rw - S->wt) > 10, bc = rc != S->cap; note(C_WT, bw); note(C_CAP, bc);
        if (bw) example(R, C_WT, "real=%ld derived=%d", rw, S->wt); if (bc) example(R, C_CAP, "real=%ld derived=%d weight_real=%ld weight_der=%d wlegs=%d", rc, S->cap, rw, S->wt, S->wlegs); } break;
    case C_SPELLS: { int rn = (int)v[0]; int bad = rn != S->nsp; for (int i = 0; i < rn && i < S->nsp && i < 8; i++) bad |= v[1 + i] != S->sp_ids[i] || v[9 + i] != S->sp_levs[i] || (v[25 + i] > 0) != (S->sp_knows[i] > 0);
        note(C_SPELLS, bad); if (bad) example(R, C_SPELLS, "real_n=%d derived_n=%d real0=%ld/%ld/%ld der0=%d/%d/%d", rn, S->nsp, v[1], v[9], v[25], S->sp_ids[0], S->sp_levs[0], S->sp_knows[0]); } break;
    case C_PATH: { int rn = (int)v[0]; const long* rp = v + 1; int bad = 0;
        for (int i = 0; i < rn && !bad; i++) { int f = 0; for (int j = 0; j < S->path_n; j++) if (S->path[2 * j] == rp[2 * i] && S->path[2 * j + 1] == rp[2 * i + 1]) { f = 1; break; } if (!f) bad = 1; }
        for (int j = 0; j < S->path_n && !bad; j++) { int f = 0; for (int i = 0; i < rn; i++) if (S->path[2 * j] == rp[2 * i] && S->path[2 * j + 1] == rp[2 * i + 1]) { f = 1; break; } if (!f) bad = 1; }
        note(C_PATH, bad); if (bad) { char rs[400] = "", ds[400] = ""; int p = 0; for (int i = 0; i < rn && p < 380; i++) p += snprintf(rs + p, sizeof rs - (size_t)p, "%ld,%ld ", rp[2 * i], rp[2 * i + 1]); p = 0; for (int j = 0; j < S->path_n && p < 380; j++) p += snprintf(ds + p, sizeof ds - (size_t)p, "%d,%d ", S->path[2 * j], S->path[2 * j + 1]);
            example(R, C_PATH, "real_n=%d derived_n=%d real=[%s] derived=[%s]", rn, S->path_n, rs, ds); } S->path_n = 0; } break;
    default: break;
    }
}

static long g_files, g_eps, g_eps_div, g_eps_trunc; static long g_div_by_type[8];
static void skip_to_end(Rep* R) { DRecHdr h; while (drec_next(&R->r, &h)) { if (h.type == R_END) return; if (h.type == R_HOOK) { int na, nv; long a[8], v[DREC_MAXVALS]; if (!drec_read_hook(&R->r, &na, a, &nv, v)) return; } else if (!drec_read_obs(&R->r)) return; } }
static void replay_file(const char* path) {
    Rep* R = (Rep*)calloc(1, sizeof(Rep)); if (!drec_ropen(&R->r, path)) { fprintf(stderr, "skip (not a recording): %s\n", path); free(R); return; }
    g_files++; R->o = &R->work; R->seed = R->r.seed; bind(R);
    { static int env_done; if (!env_done) { env_done = 1; drec_apply_env(&R->r); if (getenv("DREC_SHOW_ENV")) fputs(R->r.env, stderr); } } // the derive caches its switches on first use: apply the recording's environment once, before any dr_ call
    DRecHdr h; int started = 0, ended = 0;
    while (!R->diverged && drec_next(&R->r, &h)) {
        if (h.type == R_END) { ended = 1; break; }
        if (h.type == R_HOOK) { int na, nv; long a[8], v[DREC_MAXVALS]; if (!drec_read_hook(&R->r, &na, a, &nv, v)) { R->diverged = 2; break; } if (started) hook_check(R, h.key, na, a, nv, v); continue; }
        if (!drec_read_obs(&R->r)) { R->diverged = 2; break; }
        R->work = R->r.cur;
        if (h.type == R_START) { dr_reset(&R->S, &R->d, (unsigned)R->seed); identity_try(R); { char msg[256]; dr_msg(&R->d, msg, sizeof msg); dr_update_memory(&R->S, &R->d, msg); dr_track_path(&R->S, &R->d, -1); } started = 1; g_eps++; continue; }
        if (h.type == R_PROBE) { R->diverged = 1; R->div_want = -1; R->div_type = R_PROBE; R->div_key = h.key; break; } // the recorded derive probed here, the replayed one did not
        if (h.type == R_KEY) { R->keys++; R->step++;
            if (g_watch >= 0 && R->o->message[0]) { int j = R->mring_n % 6; snprintf(R->mring[j], sizeof R->mring[j], "%.90s", (const char*)R->o->message); R->mring_t[j] = R->o->blstats[20]; R->mring_n++; }
            dr_after_key(&R->S, &R->d, R, mock_send, h.key, h.done); continue; }
        if (h.type == R_BOUNDARY) { R->bounds++; identity_try(R); dr_boundary(&R->S, &R->d, R, mock_send); if (!R->diverged) boundary_checks(R); continue; }
    }
    if (R->diverged == 1) { g_eps_div++; g_div_by_type[R->div_type & 7]++; if (g_eps_div <= 5) fprintf(stderr, "DIVERGED seed=%lx step=%ld T=%ld: replayed derive wanted probe key %d, recording has type %d key %d\n", R->seed, R->step, R->o->blstats[20], R->div_want, R->div_type, R->div_key); skip_to_end(R); }
    else if (R->diverged == 2 || !ended) g_eps_trunc++;
    drec_rclose(&R->r); free(R);
}
static int has_suffix(const char* s, const char* suf) { size_t a = strlen(s), b = strlen(suf); return a >= b && !strcmp(s + a - b, suf); }
static void replay_path(const char* p) {
    struct stat st; if (stat(p, &st)) { fprintf(stderr, "missing: %s\n", p); return; }
    if (S_ISDIR(st.st_mode)) { DIR* d = opendir(p); struct dirent* e; char* names[65536]; int n = 0;
        while ((e = readdir(d)) && n < 65536) if (has_suffix(e->d_name, ".drec.gz")) names[n++] = strdup(e->d_name); closedir(d);
        for (int i = 0; i < n; i++) for (int j = i + 1; j < n; j++) if (strcmp(names[i], names[j]) > 0) { char* t = names[i]; names[i] = names[j]; names[j] = t; }
        for (int i = 0; i < n; i++) { char f[2048]; snprintf(f, sizeof f, "%s/%s", p, names[i]); replay_file(f); free(names[i]); } }
    else replay_file(p);
}
int main(int argc, char** argv) {
    const char* baseline = NULL; const char* out = NULL; int first = 1;
    for (int i = 1; i < argc; i++) { if (!strcmp(argv[i], "--examples") && i + 1 < argc) g_examples = atoi(argv[++i]); else if (!strcmp(argv[i], "--all")) g_all = 1;
        else if (!strcmp(argv[i], "--watch") && i + 1 < argc) { const char* w = argv[++i]; for (int c = 0; c < C_N; c++) if (!strcmp(w, C_NAMES[c])) g_watch = c; if (g_watch < 0) { fprintf(stderr, "unknown channel %s\n", w); return 2; } }
        else if (!strcmp(argv[i], "--baseline") && i + 1 < argc) baseline = argv[++i]; else if (!strcmp(argv[i], "--out") && i + 1 < argc) out = argv[++i]; else { replay_path(argv[i]); first = 0; } }
    if (first) { fprintf(stderr, "usage: nh_derive_replay [--examples N] [--all] [--watch channel] [--baseline rates.txt] [--out rates.txt] <file.drec.gz | dir> ...\n"); return 2; }
    printf("DERIVE_REPLAY files=%ld episodes=%ld diverged=%ld truncated=%ld\n", g_files, g_eps, g_eps_div, g_eps_trunc);
    printf("  %-18s %10s %10s %9s\n", "channel", "queries", "mismatch", "rate");
    for (int c = 0; c < C_N; c++) printf("  %-18s %10ld %10ld %8.3f%%\n", C_NAMES[c], M_q[c], M_bad[c], 100.0 * (double)M_bad[c] / (double)(M_q[c] ? M_q[c] : 1));
    if (out) { FILE* f = fopen(out, "w"); if (f) { for (int c = 0; c < C_N; c++) fprintf(f, "%s %ld %ld\n", C_NAMES[c], M_bad[c], M_q[c]); fclose(f); } }
    int rc = 0;
    if (baseline) { FILE* f = fopen(baseline, "r"); if (!f) { fprintf(stderr, "no baseline %s\n", baseline); return 2; } char name[64]; long bb, bq;
        while (fscanf(f, "%63s %ld %ld", name, &bb, &bq) == 3) for (int c = 0; c < C_N; c++) if (!strcmp(name, C_NAMES[c])) {
            double was = bq ? (double)bb / (double)bq : 0, now = M_q[c] ? (double)M_bad[c] / (double)M_q[c] : 0;
            if (now > was + 1e-4 && M_bad[c] > bb) { printf("WORSE %-18s %.3f%% -> %.3f%%\n", C_NAMES[c], 100 * was, 100 * now); rc = 1; }
            else if (now + 1e-4 < was) printf("BETTER %-17s %.3f%% -> %.3f%%\n", C_NAMES[c], 100 * was, 100 * now); }
        fclose(f); printf(rc ? "REPLAY_REGRESSION\n" : "REPLAY_OK\n"); }
    return rc;
}
