// Derive-replay recording: the fork harness (mode 0) writes, per episode, every engine interaction the derive saw
// (env keys, its own probe keys, boundary refreshes, each with the public observation after it) plus the fork's
// ground truth at every hook call. nh_derive_replay.c re-runs nh_derive.h over the file with no engine, so a derive
// fix is checked against thousands of recorded steps in seconds instead of an hour of live eval.
// Stream: gzip of [DRecHdr][payload]*; payload = block-delta snapshot (R_START/R_KEY/R_PROBE/R_BOUNDARY) or hook values.
#ifndef NH_DERIVE_REC_H
#define NH_DERIVE_REC_H
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
extern char** environ;

#define DREC_MAGIC 0x32434552 // "REC2": header carries the NH_ and NLE_ environment the derive read its switches from
enum { R_START = 1, R_KEY = 2, R_PROBE = 3, R_BOUNDARY = 4, R_HOOK = 5, R_END = 6 };
typedef struct { int type; int key; int done; long seq; } DRecHdr;
typedef struct {
    short glyphs[21 * 79]; long blstats[27]; unsigned char message[256]; int misc[3];
    unsigned char tty_chars[24 * 80]; signed char tty_colors[24 * 80]; unsigned char tty_cursor[2];
    short inv_glyphs[55]; unsigned char inv_strs[55 * 80]; unsigned char inv_letters[55]; unsigned char inv_oclasses[55];
    int internal[16]; signed char inv_state[55 * 8]; short inv_true[55]; // fork truth the derive never reads
} DRecObs;
#define DREC_BLK 64
#define DREC_NBLK ((int)((sizeof(DRecObs) + DREC_BLK - 1) / DREC_BLK))
#define DREC_MAXVALS 1100

typedef struct { FILE* f; DRecObs prev; long seq; int on; } DRecW;
static int drec_open(DRecW* w, const char* dir, unsigned long seed, int idx, int ep) {
    char cmd[1200]; snprintf(cmd, sizeof cmd, "gzip -1 > %s/%lx_e%d_%d.drec.gz", dir, seed, idx, ep);
    w->f = popen(cmd, "w"); if (!w->f) { w->on = 0; return 0; }
    memset(&w->prev, 0, sizeof w->prev); w->seq = 0; w->on = 1;
    int magic = DREC_MAGIC; fwrite(&magic, sizeof magic, 1, w->f); fwrite(&seed, sizeof seed, 1, w->f);
    { char env[8192]; int n = 0; for (char** e = environ; *e && n < (int)sizeof env - 300; e++) if (!strncmp(*e, "NH_", 3) || !strncmp(*e, "NLE_", 4)) n += snprintf(env + n, sizeof env - (size_t)n, "%s\n", *e);
      fwrite(&n, sizeof n, 1, w->f); if (n) fwrite(env, 1, (size_t)n, w->f); }
    return 1;
}
static void drec_hdr(DRecW* w, int type, int key, int done) { DRecHdr h = { type, key, done, w->seq++ }; fwrite(&h, sizeof h, 1, w->f); }
static void drec_snapshot(DRecW* w, const DRecObs* cur) {
    const unsigned char* a = (const unsigned char*)cur; const unsigned char* b = (const unsigned char*)&w->prev;
    unsigned short n = 0; for (int i = 0; i < DREC_NBLK; i++) { size_t off = (size_t)i * DREC_BLK, len = sizeof(DRecObs) - off < DREC_BLK ? sizeof(DRecObs) - off : DREC_BLK; if (memcmp(a + off, b + off, len)) n++; }
    fwrite(&n, sizeof n, 1, w->f);
    for (int i = 0; i < DREC_NBLK; i++) { size_t off = (size_t)i * DREC_BLK, len = sizeof(DRecObs) - off < DREC_BLK ? sizeof(DRecObs) - off : DREC_BLK;
        if (memcmp(a + off, b + off, len)) { unsigned short idx = (unsigned short)i; fwrite(&idx, sizeof idx, 1, w->f); fwrite(a + off, 1, len, w->f); } }
    w->prev = *cur;
}
static void drec_hook(DRecW* w, int chan, int nargs, const long* args, int nvals, const long* vals) {
    drec_hdr(w, R_HOOK, chan, 0); fwrite(&nargs, sizeof nargs, 1, w->f); if (nargs) fwrite(args, sizeof(long), (size_t)nargs, w->f);
    fwrite(&nvals, sizeof nvals, 1, w->f); if (nvals) fwrite(vals, sizeof(long), (size_t)nvals, w->f);
}
static void drec_close(DRecW* w) { if (!w->on) return; drec_hdr(w, R_END, 0, 0); pclose(w->f); w->f = NULL; w->on = 0; }

typedef struct { FILE* f; DRecObs cur; unsigned long seed; int have_pend; DRecHdr pend; char env[8192]; } DRecR;
static int drec_ropen(DRecR* r, const char* path) {
    char cmd[1200]; snprintf(cmd, sizeof cmd, "gzip -dc %s", path); r->f = popen(cmd, "r"); if (!r->f) return 0;
    int magic = 0; if (fread(&magic, sizeof magic, 1, r->f) != 1 || magic != DREC_MAGIC) { pclose(r->f); r->f = NULL; return 0; }
    if (fread(&r->seed, sizeof r->seed, 1, r->f) != 1) { pclose(r->f); r->f = NULL; return 0; }
    { int n = 0; if (fread(&n, sizeof n, 1, r->f) != 1 || n < 0 || n >= (int)sizeof r->env) { pclose(r->f); r->f = NULL; return 0; } if (n && fread(r->env, 1, (size_t)n, r->f) != (size_t)n) { pclose(r->f); r->f = NULL; return 0; } r->env[n] = 0; }
    memset(&r->cur, 0, sizeof r->cur); r->have_pend = 0; return 1;
}
static int drec_next(DRecR* r, DRecHdr* h) { if (r->have_pend) { *h = r->pend; r->have_pend = 0; return 1; } return fread(h, sizeof *h, 1, r->f) == 1; }
static void drec_unread(DRecR* r, const DRecHdr* h) { r->pend = *h; r->have_pend = 1; }
static int drec_read_obs(DRecR* r) {
    unsigned short n; if (fread(&n, sizeof n, 1, r->f) != 1) return 0; unsigned char* a = (unsigned char*)&r->cur;
    for (int j = 0; j < n; j++) { unsigned short idx; if (fread(&idx, sizeof idx, 1, r->f) != 1 || idx >= DREC_NBLK) return 0;
        size_t off = (size_t)idx * DREC_BLK, len = sizeof(DRecObs) - off < DREC_BLK ? sizeof(DRecObs) - off : DREC_BLK; if (fread(a + off, 1, len, r->f) != len) return 0; }
    return 1;
}
static int drec_read_hook(DRecR* r, int* nargs, long* args, int* nvals, long* vals) {
    if (fread(nargs, sizeof *nargs, 1, r->f) != 1 || *nargs < 0 || *nargs > 8) return 0; if (*nargs && fread(args, sizeof(long), (size_t)*nargs, r->f) != (size_t)*nargs) return 0;
    if (fread(nvals, sizeof *nvals, 1, r->f) != 1 || *nvals < 0 || *nvals > DREC_MAXVALS) return 0; if (*nvals && fread(vals, sizeof(long), (size_t)*nvals, r->f) != (size_t)*nvals) return 0;
    return 1;
}
static void drec_apply_env(const DRecR* r) { char b[8192]; snprintf(b, sizeof b, "%s", r->env); for (char* l = strtok(b, "\n"); l; l = strtok(NULL, "\n")) { char* eq = strchr(l, '='); if (!eq) continue; *eq = 0; setenv(l, eq + 1, 0); } }
static void drec_rclose(DRecR* r) { if (r->f) pclose(r->f); r->f = NULL; }
#endif
