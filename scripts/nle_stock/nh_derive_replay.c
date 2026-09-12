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
static int g_examples = 5, g_all, g_msgs; static int E_n[C_N]; static int g_watch = -1; static long g_min_turn = 0; // --min-turn N: count only hooks/boundaries at game turn >= N (late-game error rates)

typedef struct {
    DRecR r; DObs d; DState S; DRecObs work; DRecObs* o; signed char inv_state[55 * 8]; short inv_true[55]; // work = the buffers the derive reads and may write (dr_restore); r.cur stays the pristine recorded state the deltas apply to
    int diverged; int div_want, div_type, div_key; long probes, keys, bounds; unsigned long seed; long step;
    long watch_last[C_N]; int watch_init[C_N]; char mring[6][96]; long mring_t[6]; int mring_n; // --watch: last messages seen on env keys
    int che, chs, che_truth, poly, tform, fp_e_seen, fp_s_seen; long che_t, fpT_e, fpT_s; // --canthold audit state (expiry variant, sticky variant, truth form)
} Rep;

static long g_cur_turn; static void note(int c, int bad) { if (g_cur_turn < g_min_turn) return; M_q[c]++; if (bad) M_bad[c]++; }

// --canthold: audit the env's form mask (ocean/nethack/nethack.h nethack_track_cant_hold) against the hero's actual form, key by key.
// Truth = the polymorph messages ("You turn into <mon>!", "You feel like a new <mon>!" re-poly, "You return to <race> form!"), the form
// looked up in the monster tables: cantwield = M1_NOHANDS (0x2000) || msize == MZ_TINY (0). A key with HD > 0 in blstats and no polymorph
// message seen counts as an unknown form (skipped). Both the shipped 100-turn expiry and the never-expiring belief (leaky 4B lanes) run side by side.
static int g_canthold; static long CH_keys, CH_polykeys, CH_unknown, CH_truth, CH_miss_hd, CH_sets, CH_sets_true, CH_sets_false, CH_sets_unknown, CH_clears, CH_expiries;
static long CH_on_e, CH_fp_e, CH_fpstale_e, CH_fn_e, CH_fpT_e, CH_fpeps_e, CH_on_s, CH_fp_s, CH_fn_s, CH_fpT_s, CH_fpeps_s, CH_eps, CH_poly_eps; static int CH_ex;
static int ch_mon_lookup(const char* p) {
    if (!strncmp(p, "an ", 3)) p += 3; else if (!strncmp(p, "a ", 2)) p += 2; else if (!strncmp(p, "the ", 4)) p += 4;
    char name[64]; int n = 0; while (p[n] && p[n] != '!' && p[n] != '.' && n < 63) { name[n] = p[n]; n++; } name[n] = 0;
    for (int i = 0; i < NHT_NUMMONS; i++) if (!strcmp(name, NHT_MON_NAME[i])) return i; return -1;
}
static long CH_rev_probe, CH_silent_revert, CH_ambig; // polymorph entries/reverts whose message reached the recording only in a probe reply (a --More-- page the derive dismissed): in training there are no probes and the env sees them
static void canthold_msg(Rep* R, const char* m, long T, int from_probe) { // every message the game printed, env key or probe reply = what the training env sees
    const char* p; int before = R->poly;
    if (m[0]) {
        if ((p = strstr(m, "You turn into "))) { R->poly = 1; R->tform = ch_mon_lookup(p + 14); }
        else if (strstr(m, "You feel like a new ")) { R->poly = 0; R->tform = -1; } // newman(): natural form again; the same-form re-poly says "You feel like a <mon>!" and changes nothing
        if ((p = strstr(m, "You return to ")) && strstr(p, " form")) { R->poly = 0; R->tform = -1; }
        if (from_probe && R->poly != before) CH_rev_probe++;
    }
    if (R->che && T - R->che_t > 100) { R->che = 0; CH_expiries++; }
    int set = m[0] && (strstr(m, "can't even hold anything") || strstr(m, "Don't be ridiculous") || strstr(m, "can't throw or shoot without hands") || strstr(m, "Don't even bother") || strstr(m, "can't wear any armor in your current form"));
    int clr = m[0] && (strstr(m, "You return to ") || strstr(m, "You turn into ") || strstr(m, "You break out of your cocoon"));
    if (set) {
        if (!R->che) { int truth = !R->poly ? 0 : (R->tform >= 0 ? (((NHT_MON_M1[R->tform] & 0x2000u) != 0) || NHT_MON_SIZE[R->tform] == 0) : -1);
            CH_sets++; R->che_truth = truth; if (truth == 1) CH_sets_true++; else if (truth == 0) { CH_sets_false++; if (CH_ex < 12) { CH_ex++; printf("CANTHOLD false-set seed=%lx T=%ld poly=%d form=%d msg=\"%.110s\"\n", R->seed, T, R->poly, R->tform, m); } } else CH_sets_unknown++; }
        R->che = 1; R->che_t = T; R->chs = 1;
    } else if (clr) { if (R->che) CH_clears++; R->che = 0; R->chs = 0; }
}
static void canthold_step(Rep* R) {
    const char* m = (const char*)R->o->message; long T = R->o->blstats[20]; int was_poly = R->poly;
    canthold_msg(R, m, T, 0);
    long hd = R->o->blstats[17];
    if (hd > 0 && !R->poly) { CH_miss_hd++; R->poly = 1; R->tform = -1; } // polymorphed with no message seen: form unknown
    if (R->poly && R->tform < 0 && R->S.form >= 0) R->tform = R->S.form; // the derive's own self-look identified the form
    // a form with mlevel > 0 shows HD > 0; HD back at 0 means the hero reverted even if the "You return to" message was lost
    // (topline overflow: several messages in one step, only the last page survives -- the training env loses it the same way)
    if (hd == 0 && R->poly && R->tform >= 0 && NHT_MON_LEVEL[R->tform] > 0) { R->poly = 0; R->tform = -1; CH_silent_revert++; }
    if (R->poly && !was_poly) CH_poly_eps++;
    int truth = !R->poly ? 0 : (R->tform >= 0 && (hd > 0 || NHT_MON_LEVEL[R->tform] == 0) ? (((NHT_MON_M1[R->tform] & 0x2000u) != 0) || NHT_MON_SIZE[R->tform] == 0) : -1);
    if (R->poly && R->tform >= 0 && hd == 0 && NHT_MON_LEVEL[R->tform] == 0) CH_ambig++; // mlevel-0 form (newt, jackal...): HD cannot confirm it is still on; the message truth is used as is
    CH_keys++; if (R->poly) { CH_polykeys++; if (truth < 0) CH_unknown++; } if (truth == 1) CH_truth++;
    if (truth < 0) return;
    if (R->che) { CH_on_e++; if (!truth) { CH_fp_e++; if (R->che_truth == 1) CH_fpstale_e++; if (T != R->fpT_e) { CH_fpT_e++; R->fpT_e = T; }
            if (!R->fp_e_seen) { R->fp_e_seen = 1; CH_fpeps_e++; if (CH_ex < 12) { CH_ex++; printf("CANTHOLD wrong-on(expiry) seed=%lx T=%ld set_T=%ld form=%d msg=\"%.110s\"\n", R->seed, T, R->che_t, R->tform, m); } } } }
    else if (truth) CH_fn_e++;
    if (R->chs) { CH_on_s++; if (!truth) { CH_fp_s++; if (T != R->fpT_s) { CH_fpT_s++; R->fpT_s = T; } if (!R->fp_s_seen) { R->fp_s_seen = 1; CH_fpeps_s++; } } } else if (truth) CH_fn_s++;
}
static void canthold_report(void) {
    printf("CANTHOLD_RAW %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld\n", CH_eps, CH_poly_eps, CH_keys, CH_polykeys, CH_unknown, CH_truth, CH_miss_hd, CH_sets, CH_sets_true, CH_sets_false, CH_sets_unknown, CH_clears, CH_expiries,
           CH_on_e, CH_fp_e, CH_fpstale_e, CH_fn_e, CH_fpT_e, CH_fpeps_e, CH_on_s, CH_fp_s, CH_fn_s, CH_fpT_s, CH_fpeps_s, CH_rev_probe, CH_silent_revert, CH_ambig);
}
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
    R->work = R->r.cur; R->probes++;
    if (g_canthold) canthold_msg(R, (const char*)R->o->message, R->o->blstats[20], 1);
    if (g_msgs && R->o->message[0]) printf("PMSG T=%ld step=%ld key=%d %.150s\n", R->o->blstats[20], R->step, key, (const char*)R->o->message);
    return h.done;
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
    DState* S = &R->S; DRecObs* o = R->o; g_cur_turn = o->blstats[20];
    if (S->d_valid) { int k = S->d_r * 79 + S->d_c; int under = S->top >= 0 ? S->top : S->terrain; if (under < 0) under = CMAP_OFF + 19;
        int engulfed = 0; for (int q = 0; q < DR_CELLS; q++) if (o->glyphs[q] >= SWALLOW_OFF && o->glyphs[q] < SWALLOW_HI) { engulfed = 1; break; }
        // the stock backend keeps the raw hero glyph while blind, hallucinating or engulfed (the fork's own rule); on fork truth that raw glyph IS the export, so only the sighted case is a reconstruction test
        int real = o->glyphs[k], derm = (engulfed || (o->blstats[25] & 0x220)) ? real : dr_map_glyph(S, (short)under); note(C_HERO, real != derm); if (real != derm) example(R, C_HERO, "real=%d derived=%d top=%d terrain=%d cond=%lx blind=%d halu=%d", real, derm, S->top, S->terrain, (unsigned long)o->blstats[25], (int)((o->blstats[25] >> 5) & 1), (int)((o->blstats[25] >> 9) & 1)); }
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
    if (chan != g_watch && !(g_watch == C_WT && chan == C_CAP)) return; if (R->watch_init[chan] && real == R->watch_last[chan]) return;
    printf("WATCH %-12s seed=%lx step=%ld T=%ld real %ld -> %ld (derived %ld) cond=%lx recent:", C_NAMES[chan], R->seed, R->step, R->o->blstats[20], R->watch_init[chan] ? R->watch_last[chan] : -1L, real, der, (unsigned long)R->o->blstats[25]);
    for (int i = 0; i < R->mring_n && i < 6; i++) { int j = (R->mring_n - 1 - i) % 6; printf(" [T%ld \"%s\"]", R->mring_t[j], R->mring[j]); } printf("\n");
    R->watch_last[chan] = real; R->watch_init[chan] = 1;
}
static void hook_check(Rep* R, int chan, int nargs, const long* a, int nvals, const long* v) {
    DState* S = &R->S; long r = nvals ? v[0] : 0; (void)nargs; g_cur_turn = R->o->blstats[20];
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
        if (bw) { char inv[700]; int q = 0; for (int i = 0; i < 55 && R->d.inv_letters && R->d.inv_letters[i] && q < 640; i++) q += snprintf(inv + q, sizeof inv - q, " %c:%.28s", R->d.inv_letters[i], (const char*)R->d.inv_strs + i * 80); if (q == 0) inv[0] = 0; example(R, C_WT, "real=%ld derived=%d cond=%lx inv:%s", rw, S->wt, R->d.blstats[25], inv); } if (bc) { char r23[128] = ""; if (R->d.tty_chars) { char row[DR_TTY_CO + 1]; dr_row(&R->d, 23, row); snprintf(r23, sizeof r23, "%.60s", row); } example(R, C_CAP, "real=%ld derived=%d weight_real=%ld weight_der=%d wlegs=%d form=%d hd=%ld r23=[%s]", rc, S->cap, rw, S->wt, S->wlegs, S->form, R->d.blstats[17], r23); } } break;
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
        if (h.type == R_START) { dr_reset(&R->S, &R->d, (unsigned)R->seed); identity_try(R); { char msg[256]; dr_msg(&R->d, msg, sizeof msg); dr_update_memory(&R->S, &R->d, msg); dr_track_path(&R->S, &R->d, -1); } started = 1; g_eps++; R->tform = -1; R->fpT_e = R->fpT_s = -1; CH_eps++; continue; }
        if (h.type == R_PROBE) { if (g_msgs) printf("PROBE T=%ld step=%ld key=%d\n", R->o->blstats[20], R->step, h.key); R->diverged = 1; R->div_want = -1; R->div_type = R_PROBE; R->div_key = h.key; break; } // the recorded derive probed here, the replayed one did not
        if (h.type == R_KEY) { R->keys++; R->step++;
            if (g_msgs && R->o->message[0]) printf("MSG T=%ld step=%ld %.150s\n", R->o->blstats[20], R->step, (const char*)R->o->message);
            if (g_watch >= 0 && R->o->message[0]) { int j = R->mring_n % 6; snprintf(R->mring[j], sizeof R->mring[j], "%.90s", (const char*)R->o->message); R->mring_t[j] = R->o->blstats[20]; R->mring_n++; }
            dr_after_key(&R->S, &R->d, R, mock_send, h.key, h.done); if (g_canthold) canthold_step(R); continue; }
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
        else if (!strcmp(argv[i], "--min-turn") && i + 1 < argc) g_min_turn = atol(argv[++i]);
        else if (!strcmp(argv[i], "--msgs")) g_msgs = 1;
        else if (!strcmp(argv[i], "--canthold")) g_canthold = 1;
        else if (!strcmp(argv[i], "--log")) dr_log_this = 1;
        else if (!strcmp(argv[i], "--watch") && i + 1 < argc) { const char* w = argv[++i]; for (int c = 0; c < C_N; c++) if (!strcmp(w, C_NAMES[c])) g_watch = c; if (g_watch < 0) { fprintf(stderr, "unknown channel %s\n", w); return 2; } }
        else if (!strcmp(argv[i], "--baseline") && i + 1 < argc) baseline = argv[++i]; else if (!strcmp(argv[i], "--out") && i + 1 < argc) out = argv[++i]; else { replay_path(argv[i]); first = 0; } }
    if (first) { fprintf(stderr, "usage: nh_derive_replay [--examples N] [--all] [--watch channel] [--baseline rates.txt] [--out rates.txt] <file.drec.gz | dir> ...\n"); return 2; }
    printf("DERIVE_REPLAY files=%ld episodes=%ld diverged=%ld truncated=%ld\n", g_files, g_eps, g_eps_div, g_eps_trunc);
    printf("  %-18s %10s %10s %9s\n", "channel", "queries", "mismatch", "rate");
    for (int c = 0; c < C_N; c++) printf("  %-18s %10ld %10ld %8.3f%%\n", C_NAMES[c], M_q[c], M_bad[c], 100.0 * (double)M_bad[c] / (double)(M_q[c] ? M_q[c] : 1));
    if (g_canthold) canthold_report();
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
