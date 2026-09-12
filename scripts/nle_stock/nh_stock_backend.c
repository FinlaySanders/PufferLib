// Stock-NLE engine backend for the PufferLib NetHack vec: every env gets its own
// private copy of stock libnethack.so (loaded from a memfd, so each copy has its
// own globals), stepped through stock's nle_start/nle_step/nle_end. The fork-only
// introspection hooks the env reads are derived from stock's public observation
// by nh_derive.h (ported from scripts/nle_stock/eval_stock.py).
#define _GNU_SOURCE
#include <ctype.h>
#include <dlfcn.h>
#include <execinfo.h>
#include <elf.h>
#include <time.h>
#include <link.h>
#include <ucontext.h>
#include <errno.h>
#include <fcntl.h>
#include <setjmp.h>
#include <signal.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include "nletypes.h" // the fork's nle_obs / nle_settings: what the env compiles against
#include "nh_derive.h"

#define ROWS 21
#define COLS 79
#define TTY_LI 24
#define TTY_CO 80
#define SDESC 80
#define INV 55
#define STOCK_INTERNAL 9
#define STOCK_PROG 6

// stock NLE 0.9.0 ABI (verified with offsetof: obs 152 B, settings 49156 B, seeds 24 B)
typedef struct {
    int action;
    int done;
    char in_normal_game;
    int how_done;
    short* glyphs;
    unsigned char* chars;
    unsigned char* colors;
    unsigned char* specials;
    long* blstats;
    unsigned char* message;
    int* program_state;
    int* internal;
    short* inv_glyphs;
    unsigned char* inv_strs;
    unsigned char* inv_letters;
    unsigned char* inv_oclasses;
    unsigned char* screen_descriptions;
    unsigned char* tty_chars;
    signed char* tty_colors;
    unsigned char* tty_cursor;
    int* misc;
} sobs_t;
typedef struct {
    char hackdir[4096];
    char scoreprefix[4096];
    char options[32768];
    char wizkit[4096];
    int spawn_monsters;
    char ttyrecname[4096];
} sset_t;
typedef struct {
    unsigned long seeds[2];
    char reseed;
} sseed_t;

typedef struct Inst {
    void* dl;
    int fd;
    void* ctx; // stock's nle_ctx_t
    void* (*s_start)(sobs_t*, FILE*, sseed_t*, sset_t*);
    void* (*s_step)(void*, sobs_t*);
    void (*s_end)(void*);
    sobs_t so;
    nle_obs* fobs; // the env's observation (fork layout)
    DObs d;        // the derivation module's view of the same buffers
    DState S;
    // buffers for channels the env does not bind, or binds at a different size
    short glyphs[ROWS * COLS];
    unsigned char chars[ROWS * COLS];
    unsigned char colors[ROWS * COLS];
    unsigned char specials[ROWS * COLS];
    long blstats[NLE_BLSTATS_SIZE];
    unsigned char message[NLE_MESSAGE_SIZE];
    int kh[16]; unsigned khn; // last keys, for the stall census
    char lastmsg[256]; // message census dedup
    int prog[STOCK_PROG];
    int internal[STOCK_INTERNAL];
    short inv_glyphs[INV];
    unsigned char inv_strs[INV * NLE_INVENTORY_STR_LENGTH];
    unsigned char inv_letters[INV];
    unsigned char inv_oclasses[INV];
    unsigned char sdesc[ROWS * COLS * SDESC];
    unsigned char tty_chars[TTY_LI * TTY_CO];
    signed char tty_colors[TTY_LI * TTY_CO];
    unsigned char tty_cursor[2];
    int misc[NLE_MISC_SIZE];
    sset_t sset;
    int mapped; // glyph buffers currently hold exported (mapped) glyphs
    long truncations;
    FILE* replay; int rp_diverged; long rp_keys; int rp_over; unsigned long seed0;
    int crashed; // the engine faulted inside this instance: its coroutine is abandoned, never resumed or torn down
    long last_bl[27]; // blstats before the latest key (the done observation is zeroed)
    FILE* probelog; // NH_STOCK_PROBELOG=dir: every probe key with the recorded key index it followed
    unsigned char redrawn[DR_CELLS]; void (*real_pg)(int, int, int, int, int); int in_probe; // print_glyph hook: cells reprinted during the key
    unsigned long (*real_isaac)(void*); unsigned long draws; // NH_STOCK_COUNTDRAWS=1: core RNG draws of this instance
    void* rng_ctx[2]; short raw[DR_CELLS]; // NH_STOCK_TRACE=1: isaac contexts seen (core first), raw engine glyphs before derivation
    char* p_toplines; void** p_ttyDisplay; char topl_save[300]; int toplin_save, topl_saved; long probe_mark;
    char* p_prevmsg; char prevmsg_save[256]; // pline.c's static prevmsg (Norep compares against it): found in the lib file's symtab, located in the copy via its load base // Norep compares a new message with the tty's toplines: probe output must not be left there (NH_STOCK_NOTOPL=1 disables)
    int (*real_dsd)(); unsigned long desc_draws; // stock's do_screen_description (per-glyph farlook text) builds temporary objects with mksobj and draws from the core RNG; the fork's env never asks for descriptions, so those draws are answered from a scratch generator (NH_STOCK_DESC_RNG=1 keeps stock behaviour)
    char rawout[65536]; int rawlen; void (*real_tmt)(void*, const char*, size_t);
    int vmore; char vmore_text[256]; // virtual --More--: the fork's getpos shortcut leaves the pre-prompt message unacknowledged, so the redraw that follows shows --More-- and eats keys until space/Enter/ESC; stock's real getpos (answered here) clears the line instead // raw terminal stream since the last reset (tmt_write interposed): the derive reads pile windows from it
    long ep_n; // episodes started on this instance (NH_STOCK_IDSTATE)
    unsigned long wedge_h; long wedge_same, wedge_diff;
    long ch_steps, ch_noprog, ch_maxnoprog, ch_turn; int ch_aborted, ch_logged; // challenge step accounting (NH_STOCK_STRICT)
} Inst;
static long g_rp_eps, g_rp_exact, g_rp_diverged, g_rp_nofile, g_rp_startdiff; static long g_rp_div_turns[8];
static long g_rp_partdiff[9]; static long g_rp_keydiff[9];
static void rp_report(void) { fprintf(stderr, "KEYREPLAY episodes=%ld exact=%ld diverged=%ld nofile=%ld startdiff=%ld divergence_turn_hist[<10,<50,<200,<1000,<5000,<20000,more]=%ld,%ld,%ld,%ld,%ld,%ld,%ld\n", g_rp_eps, g_rp_exact, g_rp_diverged, g_rp_nofile, g_rp_startdiff, g_rp_div_turns[0], g_rp_div_turns[1], g_rp_div_turns[2], g_rp_div_turns[3], g_rp_div_turns[4], g_rp_div_turns[5], g_rp_div_turns[6]);  { const char* names[9] = {"blstats","glyphs","message","inv","internal","inv_state","inv_true","misc","cursor"}; fprintf(stderr, "KEYREPLAY first-divergence groups:"); for (int g = 0; g < 9; g++) fprintf(stderr, " %s=%ld", names[g], g_rp_keydiff[g]); fprintf(stderr, "\nKEYREPLAY start-group diffs:"); for (int g = 0; g < 9; g++) fprintf(stderr, " %s=%ld", names[g], g_rp_partdiff[g]); fprintf(stderr, "\n"); } }

static int g_verbose; static int g_trace; static int g_trace_live;
// NH_STOCK_STRICT=1: the NetHack Challenge interface (AutoAscend's): NLE default options (NH_NLE_OPTS), no screen_descriptions, no raw
// terminal stream, every key (policy + probe) is a step, episode ends at 1e6 steps or 10,000 consecutive steps without a game turn
static int g_strict;
static unsigned long elf_local_symbol(const char* path, const char* want);

// ---------------------------------------------------------------- library image
static unsigned char* g_img;
static size_t g_img_len;
static const char* stock_lib_path(void) {
    const char* p = getenv("NLE_STOCK_LIB");
    return p && *p ? p : "/puffertank/nle-stock/nle/libnethack.so";
}
static void load_image(void) {
    if (g_img) return;
    static int lock;
    while (__sync_lock_test_and_set(&lock, 1)) {}
    if (!g_img) {
        int fd = open(stock_lib_path(), O_RDONLY);
        if (fd < 0) { fprintf(stderr, "nh_stock: cannot open %s: %s\n", stock_lib_path(), strerror(errno)); exit(1); }
        struct stat st; fstat(fd, &st);
        unsigned char* buf = (unsigned char*)malloc((size_t)st.st_size);
        size_t got = 0;
        while (got < (size_t)st.st_size) {
            ssize_t r = read(fd, buf + got, (size_t)st.st_size - got);
            if (r <= 0) { fprintf(stderr, "nh_stock: short read of %s\n", stock_lib_path()); exit(1); }
            got += (size_t)r;
        }
        close(fd);
        g_img_len = got;
        __sync_synchronize();
        g_img = buf;
    }
    __sync_lock_release(&lock);
}

static int inst_open_lib(Inst* in) {
    load_image();
    in->fd = memfd_create("libnethack_stock", MFD_CLOEXEC);
    if (in->fd < 0) { fprintf(stderr, "nh_stock: memfd_create: %s\n", strerror(errno)); return -1; }
    size_t off = 0;
    while (off < g_img_len) {
        ssize_t w = write(in->fd, g_img + off, g_img_len - off);
        if (w <= 0) { fprintf(stderr, "nh_stock: memfd write: %s\n", strerror(errno)); return -1; }
        off += (size_t)w;
    }
    char path[64];
    snprintf(path, sizeof path, "/proc/self/fd/%d", in->fd);
    in->dl = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!in->dl) { fprintf(stderr, "nh_stock: dlopen: %s\n", dlerror()); return -1; }
    in->s_start = (void* (*)(sobs_t*, FILE*, sseed_t*, sset_t*))dlsym(in->dl, "nle_start");
    in->real_tmt = (void (*)(void*, const char*, size_t))dlsym(in->dl, "tmt_write");
    in->s_step = (void* (*)(void*, sobs_t*))dlsym(in->dl, "nle_step");
    in->s_end = (void (*)(void*))dlsym(in->dl, "nle_end");
    if (!in->s_start || !in->s_step || !in->s_end) { fprintf(stderr, "nh_stock: missing stock symbols\n"); return -1; }
    return 0;
}
static void inst_close_lib(Inst* in) {
    if (in->dl) { dlclose(in->dl); in->dl = NULL; }
    if (in->fd >= 0) { close(in->fd); in->fd = -1; }
}

// ---------------------------------------------------------------- engine crash isolation
// Stock NLE 0.9.0 has at least one known in-engine segfault (NLE issue #100: launch_obj rolls a boulder out of
// bounds; the fork fixed it in 0d9e5946e with an isok() check). The engine stays unmodified, so a fault inside a
// game must not take the whole eval down: every engine call runs under a per-thread sigsetjmp; the handler jumps
// back, the instance is marked crashed (episode ends, how_done -1) and its coroutine is abandoned.
static __thread Inst* t_cur;
// tmt_write is exported from this binary (--export-dynamic-symbol) so the dlopen'd copies' PLT binds here: every byte the engine
// hands to its virtual terminal is kept per instance (64 KB, reset by the derive before a probe), then passed to the copy's own writer.
// Reason: the ANSI tty port has no clear-to-end-of-screen capability; its cl_eos fallback walks down with newlines and the first
// page of a full-screen text window (a pile of 22+ objects) is drawn with the cursor stuck on the last row, so the screen keeps
// only that page's last line. The stream still carries every line.
static __thread void (*t_tmt_fallback)(void*, const char*, size_t);
void tmt_write(void* vt, const char* str, size_t n) {
    Inst* in = t_cur; void (*real)(void*, const char*, size_t) = in && in->real_tmt ? in->real_tmt : t_tmt_fallback;
    if (in && in->real_tmt) t_tmt_fallback = in->real_tmt;
    if (in) { int room = (int)sizeof in->rawout - in->rawlen; int m = n < (size_t)room ? (int)n : room; if (m > 0) { memcpy(in->rawout + in->rawlen, str, (size_t)m); in->rawlen += m; } }
    if (real) real(vt, str, n);
}
static __thread sigjmp_buf t_jb;
static __thread volatile int t_jb_set;
static __thread char* t_altstack;
static long g_crashes;
static __thread unsigned long t_fault_pc;
static void crash_handler(int sig, siginfo_t* si, void* uc) {
    (void)si;
    t_fault_pc = uc ? (unsigned long)((ucontext_t*)uc)->uc_mcontext.gregs[REG_RIP] : 0UL;
    if (t_jb_set) { t_jb_set = 0; siglongjmp(t_jb, sig); }
    signal(sig, SIG_DFL); raise(sig);
}
static void crash_report(void) { if (g_crashes) fprintf(stderr, "nh_stock: %ld episode(s) ended by an in-engine fault (stock NLE bug, see gap_report.md)\n", g_crashes); }
static void crash_guard_init(void) {
    static int done;
    if (!done && __sync_bool_compare_and_swap(&done, 0, 1)) {
        struct sigaction sa; memset(&sa, 0, sizeof sa);
        sa.sa_sigaction = crash_handler; sa.sa_flags = SA_SIGINFO | SA_ONSTACK | SA_NODEFER; sigemptyset(&sa.sa_mask);
        sigaction(SIGSEGV, &sa, NULL); sigaction(SIGBUS, &sa, NULL); sigaction(SIGFPE, &sa, NULL); sigaction(SIGILL, &sa, NULL);
        atexit(crash_report);
    }
    if (!t_altstack) { t_altstack = (char*)malloc(1 << 16); stack_t ss; ss.ss_sp = t_altstack; ss.ss_size = 1 << 16; ss.ss_flags = 0; sigaltstack(&ss, NULL); }
}
static void crash_note(Inst* in, int sig, const char* where) {
    in->crashed = 1; in->so.done = 1; in->so.how_done = -1;
    long k = __sync_add_and_fetch(&g_crashes, 1);
    unsigned long off = 0; { struct link_map* lm = NULL; if (in->dl && dlinfo(in->dl, RTLD_DI_LINKMAP, &lm) == 0 && lm) off = t_fault_pc - (unsigned long)lm->l_addr; }
    if (k <= 20 || g_verbose) fprintf(stderr, "nh_stock: engine fault (signal %d) in %s at lib+0x%lx, #%ld, seed %lx turn %ld depth %ld last key %d: episode ended\n", sig, where, off, k, in->seed0, in->d.blstats ? in->d.blstats[20] : -1L, in->d.blstats ? in->d.blstats[12] : -1L, in->so.action);
}
static int guarded_step(Inst* in) { // 1 = the engine faulted
    crash_guard_init(); t_cur = in;
    int sig = sigsetjmp(t_jb, 1);
    if (sig == 0) { t_jb_set = 1; in->s_step(in->ctx, &in->so); t_jb_set = 0;
        in->ch_steps++; if (in->d.blstats) { long t = in->d.blstats[20]; if (t == in->ch_turn) { if (++in->ch_noprog > in->ch_maxnoprog) in->ch_maxnoprog = in->ch_noprog; } else { in->ch_turn = t; in->ch_noprog = 0; } }
        // NH_STOCK_WEDGELOG=1: what is the agent repeating when the game clock stops? A zero-time refusal the policy keeps
        // re-picking is a missing action mask, and it costs 14% of episodes under the challenge no-progress rule.
        { static int wl = -1; if (wl < 0) wl = getenv("NH_STOCK_WEDGELOG") != NULL;
          if (wl && in->ch_noprog > 200) { // during a stall: is the observation the agent sees actually CHANGING?
              unsigned long h = dr_hash_sel(&in->d);
              if (in->ch_noprog == 201) { in->wedge_h = h; in->wedge_same = 0; in->wedge_diff = 0; }
              else if (h == in->wedge_h) in->wedge_same++; else { in->wedge_diff++; in->wedge_h = h; }
              if ((in->ch_noprog % 1000) == 0)
                  fprintf(stderr, "WEDGEOBS noprog=%ld identical=%ld changed=%ld\n", in->ch_noprog, in->wedge_same, in->wedge_diff); }
          if (wl && in->ch_noprog > 0 && (in->ch_noprog % 500) == 0) {
              char m[256]; dr_msg(&in->d, m, sizeof m);
              fprintf(stderr, "WEDGE noprog=%ld T=%ld engr=%d cond=%lx keys=", in->ch_noprog,
                      in->d.blstats ? in->d.blstats[20] : -1,
                      in->d.internal ? (in->d.internal[6] & 3) : -1,
                      in->d.blstats ? (unsigned long)in->d.blstats[25] : 0UL);
              for (int q = 0; q < 16; q++) fprintf(stderr, "%d,", in->kh[(in->khn + q) & 15]);
              fprintf(stderr, " msg=\"%.90s\"\n", m); } }
        return 0; }
    crash_note(in, sig, "nle_step"); return 1;
}
static int guarded_start(Inst* in, sseed_t* seed) { // 1 = the engine faulted during start-up
    crash_guard_init(); t_cur = in;
    int sig = sigsetjmp(t_jb, 1);
    FILE* tr = NULL; { const char* v = getenv("NH_STOCK_TTYREC"); if (v && seed) { static unsigned long ls; static int lsi; if (!lsi) { lsi = 1; const char* w = getenv("NH_STOCK_LOGSEED"); ls = w ? strtoul(w, NULL, 16) : 0; } if (!ls || seed->seeds[0] == ls) tr = fopen(v, "wb"); } } // diagnostic: raw terminal stream of the logged seed (bz2 ttyrec)
    if (sig == 0) { t_jb_set = 1; in->ctx = in->s_start(&in->so, tr, seed, &in->sset); t_jb_set = 0; return 0; }
    crash_note(in, sig, "nle_start"); return 1;
}

// ---------------------------------------------------------------- replay file reader
// the fork logger writes S (seeds + start hash), P (per-group start hashes), '#' comment dumps, then K lines
static int rp_next_line(FILE* f, char* buf, size_t n) { while (fgets(buf, (int)n, f)) { if (buf[0] == '#' || (buf[0] == 'K' && buf[1] == 'R') || (buf[0] == 'H' && buf[1] == ' ')) continue; return 1; } return 0; }
static __thread unsigned long t_rp_parts[9]; static __thread int t_rp_have_parts;
static __thread int t_rp_boundary; // the recorded key was followed by an env step boundary (R line): derive + compare here
static int rp_read_key(FILE* f, int* key, unsigned long* h, int* done) { char b[512]; t_rp_boundary = 0; while (rp_next_line(f, b, sizeof b)) { if (b[0] == 'K' && sscanf(b, "K %d %lx %d", key, h, done) == 3) { t_rp_have_parts = sscanf(b, "K %*d %*lx %*d %lx %lx %lx %lx %lx %lx %lx %lx %lx", &t_rp_parts[0], &t_rp_parts[1], &t_rp_parts[2], &t_rp_parts[3], &t_rp_parts[4], &t_rp_parts[5], &t_rp_parts[6], &t_rp_parts[7], &t_rp_parts[8]) == 9;
        long pos = ftell(f); char nb[512]; if (rp_next_line(f, nb, sizeof nb)) { if (nb[0] == 'R') t_rp_boundary = 1; else fseek(f, pos, SEEK_SET); } return 1; } if (b[0] == 'K') return 0; } return 0; }
static void rp_attribute(Inst* in) { if (!t_rp_have_parts) return; unsigned long mine[9]; dr_obs_hash_parts(&in->d, mine); char msg[256] = ""; for (int g = 0; g < 9; g++) if (mine[g] != t_rp_parts[g]) { __sync_fetch_and_add(&g_rp_keydiff[g], 1); strncat(msg, dr_part_names[g], sizeof msg - strlen(msg) - 2); strncat(msg, " ", sizeof msg - strlen(msg) - 1); }
    static long shown; if (g_verbose || __sync_add_and_fetch(&shown, 1) <= 8) fprintf(stderr, "replay %lx: first divergence at key %ld turn %ld: groups %s\n", in->seed0, in->rp_keys, in->d.blstats[20], msg);
    if (g_verbose) { char b[2048]; int p = snprintf(b, sizeof b, "replay %lx: Bstock%ld", in->seed0, in->rp_keys); for (int i = 0; i < 27; i++) p += snprintf(b + p, sizeof b - p, " %ld", in->d.blstats[i]); char m2[256]; dr_msg(&in->d, m2, sizeof m2); snprintf(b + p, sizeof b - p, " | I %d %d | %s", in->d.internal ? in->d.internal[6] : -1, in->d.internal ? in->d.internal[7] : -1, m2); fprintf(stderr, "%s\n", b); char r22[81], r23[81]; dr_row(&in->d, 22, r22); dr_row(&in->d, 23, r23); fprintf(stderr, "replay %lx: TTYstock%ld [%s] [%s]\n", in->seed0, in->rp_keys, r22, r23); if (in->d.inv_state) { char sb2[2048]; int q2 = snprintf(sb2, sizeof sb2, "replay %lx: STATEstock%ld ", in->seed0, in->rp_keys); for (int i = 0; i < 55 && in->d.inv_letters[i] && q2 < 1900; i++) { q2 += snprintf(sb2 + q2, sizeof sb2 - q2, "%c:", in->d.inv_letters[i]); for (int f = 0; f < 8; f++) q2 += snprintf(sb2 + q2, sizeof sb2 - q2, "%d%s", in->d.inv_state[i * 8 + f], f < 7 ? "," : " "); } fprintf(stderr, "%s\n", sb2); } char ib[4096]; int q = snprintf(ib, sizeof ib, "replay %lx: INVstock%ld ", in->seed0, in->rp_keys); for (int i = 0; i < 55 && in->d.inv_letters[i] && q < 3900; i++) q += snprintf(ib + q, sizeof ib - q, "%c=\"%.60s\"[idx %d g=%d] ", in->d.inv_letters[i], (const char*)in->d.inv_strs + i * 80, dr_name_index_lower((const char*)in->d.inv_strs + i * 80), in->d.inv_glyphs ? in->d.inv_glyphs[i] : -1); fprintf(stderr, "%s\n", ib); }
    if (g_trace) { char b[4096]; int p = snprintf(b, sizeof b, "replay %lx: RAWstock%ld", in->seed0, in->rp_keys); for (int k = 0; k < DR_CELLS && p < 4000; k++) if (in->raw[k] != in->d.glyphs[k]) p += snprintf(b + p, sizeof b - p, " %d:%d>%d", k, in->raw[k], in->d.glyphs[k]); fprintf(stderr, "%s\n", b); }
    if (g_verbose) { char* buf = (char*)malloc(65536); int p = snprintf(buf, 65536, "replay %lx: Mstock%ld ", in->seed0, in->rp_keys); for (int k = 0; k < DR_CELLS && p < 65000; k++) if (in->d.glyphs[k] != 2359) p += snprintf(buf + p, 65536 - p, "%d:%d ", k, in->d.glyphs[k]); fprintf(stderr, "%s\n", buf); p = snprintf(buf, 65536, "replay %lx: Rstock%ld ", in->seed0, in->rp_keys); for (int k = 0; k < DR_CELLS && p < 65000; k++) if (in->S.map_raw[k] != 2359) p += snprintf(buf + p, 65536 - p, "%d:%d ", k, in->S.map_raw[k]); fprintf(stderr, "%s\n", buf); free(buf); } }
static int rp_read_start(Inst* in, unsigned long* s0, unsigned long* s1, unsigned long* h0) {
    char b[512]; if (!rp_next_line(in->replay, b, sizeof b) || sscanf(b, "S %lx %lx %lx", s0, s1, h0) != 3) return 0;
    long pos = ftell(in->replay);
    if (rp_next_line(in->replay, b, sizeof b) && b[0] == 'P') {
        unsigned long rec[9]; if (sscanf(b, "P %lx %lx %lx %lx %lx %lx %lx %lx %lx", &rec[0], &rec[1], &rec[2], &rec[3], &rec[4], &rec[5], &rec[6], &rec[7], &rec[8]) == 9) {
            unsigned long mine[9]; dr_obs_hash_parts(&in->d, mine); char msg[256] = ""; int nd = 0;
            for (int g = 0; g < 9; g++) if (rec[g] != mine[g]) { __sync_fetch_and_add(&g_rp_partdiff[g], 1); nd++; strncat(msg, dr_part_names[g], sizeof msg - strlen(msg) - 2); strncat(msg, " ", sizeof msg - strlen(msg) - 1); }
            static long shown; if (nd && (g_verbose || __sync_add_and_fetch(&shown, 1) <= 5)) fprintf(stderr, "replay %lx: start groups differing: %s\n", in->seed0, msg);
            if (nd && g_verbose) { fprintf(stderr, "replay %lx: internal=", in->seed0); if (in->d.internal) for (int i = 0; i < 11; i++) fprintf(stderr, "%d ", in->d.internal[i]); fprintf(stderr, "\nreplay %lx: inv=", in->seed0); for (int i = 0; i < 55 && in->d.inv_letters[i]; i++) fprintf(stderr, "%c:%d/%d ", in->d.inv_letters[i], in->d.inv_glyphs[i], in->d.inv_oclasses[i]); fprintf(stderr, "\nreplay %lx: inv_true=", in->seed0); if (in->d.inv_true) for (int i = 0; i < 55 && in->d.inv_letters[i]; i++) fprintf(stderr, "%c:%d ", in->d.inv_letters[i], in->d.inv_true[i]); fprintf(stderr, "\nreplay %lx: inv_state=", in->seed0); if (in->d.inv_state) for (int i = 0; i < 55 && in->d.inv_letters[i]; i++) { fprintf(stderr, "%c:", in->d.inv_letters[i]); for (int f = 0; f < 8; f++) fprintf(stderr, "%d%s", in->d.inv_state[i * 8 + f], f < 7 ? "," : " "); } fprintf(stderr, "\nreplay %lx: misc=", in->seed0); if (in->d.misc) for (int i = 0; i < 3; i++) fprintf(stderr, "%d ", in->d.misc[i]); fprintf(stderr, "\nreplay %lx: cursor=%d %d\n", in->seed0, in->d.tty_cursor ? in->d.tty_cursor[0] : -1, in->d.tty_cursor ? in->d.tty_cursor[1] : -1); char ib[4096]; int q = snprintf(ib, sizeof ib, "replay %lx: invstr=", in->seed0); for (int i = 0; i < 55 && in->d.inv_letters[i] && q < 3900; i++) q += snprintf(ib + q, sizeof ib - q, "%c=\"%.60s\"[idx %d g=%d] ", in->d.inv_letters[i], (const char*)in->d.inv_strs + i * 80, dr_name_index_lower((const char*)in->d.inv_strs + i * 80), in->d.inv_glyphs ? in->d.inv_glyphs[i] : -1); fprintf(stderr, "%s\n", ib); }
        }
    } else fseek(in->replay, pos, SEEK_SET);
    return 1;
}

// ---------------------------------------------------------------- deterministic clock (per copy)
// Stock NetHack reads the wall clock at reset (ubirthday) and it leaks into gameplay: mkroom.c room types (%3),
// shopkeeper names, used-item price parity, scroll labels; getlt() drives the moon phase, Friday 13th, night and
// midnight. The fork (a628bf821 "deterministic under everything") replaces both with seed-derived values:
//   ubirthday = 1600000000 + (seed % 100000) * 257, and a fixed struct tm drawn from isaac64(seed).
// The engine copies stay unmodified: their GOT entries for time() and localtime() are pointed at these two
// functions, which reproduce the fork's formulas for the instance being stepped. NH_STOCK_REALCLOCK=1 disables.
static long nh_fixed_clock(void) { static long v = -2; if (v == -2) { const char* e = getenv("NH_STOCK_FIXEDCLOCK"); v = e ? atol(e) : -1; } return v; }
static time_t nh_fake_time(time_t* tloc) {
    long fx = nh_fixed_clock();
    Inst* in = t_cur;
    time_t v = fx >= 0 ? (time_t)fx : (in ? (time_t)(1600000000L + (long)(in->seed0 % 100000UL) * 257L) : time(NULL));
    if (tloc) *tloc = v; return v;
}
static struct tm* nh_fake_localtime(const time_t* t) {
    static __thread struct tm tmv; Inst* in = t_cur; (void)t;
    memset(&tmv, 0, sizeof tmv);
    if (nh_fixed_clock() >= 0) { // same values the python-side LD_PRELOAD returns
        tmv.tm_year = 120; tmv.tm_mon = 8; tmv.tm_mday = 13; tmv.tm_hour = 12;
        tmv.tm_wday = 0; tmv.tm_yday = 256; tmv.tm_isdst = 0; return &tmv; }
    if (!in || !in->dl) return localtime(t);
    void (*iinit)(void*, const unsigned char*, int) = (void (*)(void*, const unsigned char*, int))dlsym(in->dl, "isaac64_init");
    unsigned long (*inext)(void*, unsigned long) = (unsigned long (*)(void*, unsigned long))dlsym(in->dl, "isaac64_next_uint");
    if (!iinit || !inext) return localtime(t);
    static __thread unsigned char rng[16384]; unsigned long seed = in->seed0; unsigned char sb[8]; memcpy(sb, &seed, 8);
    iinit(rng, sb, 8);
    tmv.tm_year = 100 + (int)inext(rng, 50); tmv.tm_mon = (int)inext(rng, 12); tmv.tm_mday = 1 + (int)inext(rng, 28);
    tmv.tm_hour = (int)inext(rng, 24); tmv.tm_wday = (int)inext(rng, 7); tmv.tm_yday = tmv.tm_mon * 30 + tmv.tm_mday;
    return &tmv;
}
static unsigned long g_bt_seed; static long g_bt_key; // NH_STOCK_DRAWBT=<seedhex>:<key index>: backtrace every RNG draw of that key
static void nh_draw_bt(Inst* in) { void* bt[40]; int n = backtrace(bt, 40); struct link_map* lm = NULL; dlinfo(in->dl, RTLD_DI_LINKMAP, &lm); unsigned long base = lm ? (unsigned long)lm->l_addr : 0; char b[4096]; int p = snprintf(b, sizeof b, "replay %lx: DRAWBT key %ld draw %lu:", in->seed0, in->rp_keys, in->draws); for (int i = 1; i < n && p < 4000; i++) p += snprintf(b + p, sizeof b - p, " %lx", (unsigned long)bt[i] - base); fprintf(stderr, "%s\n", b); }
// sort_rooms: stock compares lx only, so rooms with equal lx sort in qsort's implementation-defined tie order; the fork's
// comparator breaks ties on (ly, hx, hy) (a total order, so any sort gives the fork's order). The copy's qsort import is
// redirected here; the mkroom sort is recognised by its element size, every other qsort passes straight through.
#define NH_MKROOM_SIZE 216
static __thread int (*t_room_cmp)(const void*, const void*);
static int nh_room_total(const void* a, const void* b) { int r = t_room_cmp(a, b); if (r) return r; const signed char* x = (const signed char*)a; const signed char* y = (const signed char*)b;
    if (x[2] != y[2]) return x[2] > y[2] ? 1 : -1; if (x[1] != y[1]) return x[1] > y[1] ? 1 : -1; if (x[3] != y[3]) return x[3] > y[3] ? 1 : -1; return 0; }
static void nh_qsort(void* base, size_t n, size_t sz, int (*cmp)(const void*, const void*)) { if (sz == NH_MKROOM_SIZE && n > 1 && !getenv("NH_STOCK_STOCKSORT")) { t_room_cmp = cmp; qsort(base, n, sz, nh_room_total); return; } qsort(base, n, sz, cmp); }
static __thread int t_in_desc; static __thread unsigned long t_scratch = 0x9E3779B97F4A7C15UL;
typedef struct { signed char x, y; } nhc_t;
static int nh_desc_wrap(nhc_t cc, signed char looked, int sym, char* out, const char** fm, void** sup) { Inst* in = t_cur; if (!in || !in->real_dsd) return 0; t_in_desc++; int r = ((int (*)(nhc_t, signed char, int, char*, const char**, void**))in->real_dsd)(cc, looked, sym, out, fm, sup); t_in_desc--; return r; }
static unsigned long nh_count_isaac(void* ctx) { Inst* in = t_cur; if (in && t_in_desc) { in->desc_draws++; t_scratch ^= t_scratch << 13; t_scratch ^= t_scratch >> 7; t_scratch ^= t_scratch << 17; return t_scratch; } if (in) { in->draws++; if (g_bt_seed && in->seed0 == g_bt_seed && in->rp_keys == g_bt_key) nh_draw_bt(in); if (!in->rng_ctx[0]) in->rng_ctx[0] = ctx; else if (ctx != in->rng_ctx[0] && !in->rng_ctx[1]) in->rng_ctx[1] = ctx; if (in->real_isaac) return in->real_isaac(ctx); } return 0; }
static int g_trace_decl_moved; // NH_STOCK_TRACE=1 (with NH_STOCK_COUNTDRAWS=1): per-key RNG-state hashes, blstats and message of every replayed episode
static unsigned long nh_ctx_hash(const void* ctx) { if (!ctx) return 0; const unsigned char* b = (const unsigned char*)ctx; unsigned long h = 1469598103934665603UL; for (size_t i = 0; i < 4128; i++) h = (h ^ b[i]) * 1099511628211UL; return h; }
static void trace_bl(Inst* in, const char* tag) { char b[2048]; int p = snprintf(b, sizeof b, "replay %lx: %s%ld", in->seed0, tag, in->rp_keys); for (int i = 0; i < 27; i++) p += snprintf(b + p, sizeof b - p, " %ld", in->d.blstats[i]); char m2[256]; dr_msg(&in->d, m2, sizeof m2); snprintf(b + p, sizeof b - p, " | I %d %d | %s", in->d.internal ? in->d.internal[6] : -1, in->d.internal ? in->d.internal[7] : -1, m2); fprintf(stderr, "%s\n", b); }
static void nh_print_glyph_wrap(int wid, int x, int y, int glyph, int bk) { // rl port print_glyph, interposed in the copy's rl_procs table
    Inst* in = t_cur; if (!in) return;
    if (!in->in_probe && x >= 1 && x <= DR_COLS && y >= 0 && y < DR_ROWS) in->redrawn[y * DR_COLS + (x - 1)] = 1;
    if (in->real_pg) in->real_pg(wid, x, y, glyph, bk);
}
static int nh_patch_got(Inst* in) { // redirect the copy's imports of time/localtime (and the RNG core when counting); returns the number of slots patched
    int count_draws = getenv("NH_STOCK_COUNTDRAWS") != NULL; in->real_isaac = (unsigned long (*)(void*))dlsym(in->dl, "isaac64_next_uint64"); in->real_dsd = (int (*)())dlsym(in->dl, "do_screen_description"); in->p_toplines = (char*)dlsym(in->dl, "toplines"); in->p_ttyDisplay = (void**)dlsym(in->dl, "ttyDisplay"); if (getenv("NH_STOCK_NOTOPL")) in->p_toplines = NULL;
    { static unsigned long pm_off; static int pm_init; if (!pm_init) { pm_init = 1; const char* lp = getenv("NLE_STOCK_LIB"); pm_off = lp ? elf_local_symbol(lp, "prevmsg") : 0; if (g_verbose) fprintf(stderr, "nh_stock: prevmsg symtab offset %lx\n", pm_off); }
      struct link_map* lm = NULL; if (pm_off && in->dl && dlinfo(in->dl, RTLD_DI_LINKMAP, &lm) == 0 && lm) in->p_prevmsg = (char*)lm->l_addr + pm_off; }
    if (!getenv("NH_STOCK_NOREDRAW")) { // hook print_glyph in rl_procs (copied into windowprocs by choose_windows) and in windowprocs if already chosen
        void* pg = dlsym(in->dl, "_ZN10nethack_rl9NetHackRL14rl_print_glyphEiiiii"); const char* tabs[2] = {"rl_procs", "windowprocs"}; long page = sysconf(_SC_PAGESIZE);
        for (int t = 0; pg && t < 2; t++) { void** procs = (void**)dlsym(in->dl, tabs[t]); if (!procs) continue; for (int i = 0; i < 64; i++) if (procs[i] == pg) { mprotect((void*)((unsigned long)&procs[i] & ~(page - 1)), page, PROT_READ | PROT_WRITE); in->real_pg = (void (*)(int, int, int, int, int))pg; procs[i] = (void*)nh_print_glyph_wrap; break; } }
        { static int rep; if (!rep && __sync_bool_compare_and_swap(&rep, 0, 1) && g_verbose) fprintf(stderr, "nh_stock: print_glyph hook %s\n", in->real_pg ? "installed" : "NOT installed"); } }
    if (getenv("NH_STOCK_REALCLOCK") && !count_draws) return 0;
    struct link_map* lm = NULL; if (dlinfo(in->dl, RTLD_DI_LINKMAP, &lm) != 0 || !lm) return -1;
    ElfW(Dyn)* d = lm->l_ld; const char* strtab = NULL; ElfW(Sym)* symtab = NULL; ElfW(Rela)* jmprel = NULL; size_t jmpsz = 0; ElfW(Rela)* rela = NULL; size_t relasz = 0;
    for (; d->d_tag != DT_NULL; d++) {
        if (d->d_tag == DT_STRTAB) strtab = (const char*)d->d_un.d_ptr; else if (d->d_tag == DT_SYMTAB) symtab = (ElfW(Sym)*)d->d_un.d_ptr;
        else if (d->d_tag == DT_JMPREL) jmprel = (ElfW(Rela)*)d->d_un.d_ptr; else if (d->d_tag == DT_PLTRELSZ) jmpsz = d->d_un.d_val;
        else if (d->d_tag == DT_RELA) rela = (ElfW(Rela)*)d->d_un.d_ptr; else if (d->d_tag == DT_RELASZ) relasz = d->d_un.d_val;
    }
    if (!strtab || !symtab) return -1;
    int n = 0; long page = sysconf(_SC_PAGESIZE);
    for (int pass = 0; pass < 2; pass++) {
        ElfW(Rela)* r = pass ? rela : jmprel; size_t sz = pass ? relasz : jmpsz; if (!r) continue;
        for (size_t i = 0; i < sz / sizeof(ElfW(Rela)); i++) {
            unsigned type = ELF64_R_TYPE(r[i].r_info); if (type != R_X86_64_JUMP_SLOT && type != R_X86_64_GLOB_DAT) continue;
            const char* name = strtab + symtab[ELF64_R_SYM(r[i].r_info)].st_name; void* fn = NULL;
            if (!strcmp(name, "time") && !getenv("NH_STOCK_REALCLOCK")) fn = (void*)nh_fake_time; else if (!strcmp(name, "localtime") && !getenv("NH_STOCK_REALCLOCK")) fn = (void*)nh_fake_localtime; else if (!strcmp(name, "isaac64_next_uint64")) fn = (void*)nh_count_isaac; else if (!strcmp(name, "qsort")) fn = (void*)nh_qsort; else if (!getenv("NH_STOCK_DESC_RNG") && !strcmp(name, "do_screen_description")) fn = (void*)nh_desc_wrap; else continue;
            void** slot = (void**)(lm->l_addr + r[i].r_offset);
            mprotect((void*)((unsigned long)slot & ~(page - 1)), page, PROT_READ | PROT_WRITE);
            *slot = fn; n++;
        }
    }
    return n;
}

// ---------------------------------------------------------------- obs wiring
// Stock writes into the env's buffers wherever the env bound one of the same
// size; everything else lands in the instance's own buffers. Stock's internal
// has 9 slots, the fork's 11: stock writes the first 9 of the env's array.
static void wire_obs(Inst* in, nle_obs* o) {
    // sticky binding: the env passes partial obs structs on intermediate calls (some buffers NULL); a buffer is
    // replaced only by a non-NULL one, so stock keeps writing where the env last asked it to
    sobs_t* s = &in->so;
    if (!s->glyphs) { int act = s->action, done = s->done, how = s->how_done; char ing = s->in_normal_game; memset(s, 0, sizeof *s); s->action = act; s->done = done; s->how_done = how; s->in_normal_game = ing; }
#define NHB(f, mine) s->f = o->f ? o->f : (s->f ? s->f : in->mine)
    NHB(glyphs, glyphs); NHB(chars, chars); NHB(colors, colors); NHB(specials, specials); NHB(blstats, blstats); NHB(message, message);
    s->program_state = o->prog_state ? o->prog_state : (s->program_state ? s->program_state : in->prog);
    NHB(internal, internal); NHB(inv_glyphs, inv_glyphs); NHB(inv_strs, inv_strs); NHB(inv_letters, inv_letters); NHB(inv_oclasses, inv_oclasses);
    s->screen_descriptions = NULL; // never: stock builds descriptions with mksobj (RNG) and marks adjacent objects dknown
    NHB(tty_chars, tty_chars); NHB(tty_colors, tty_colors); NHB(tty_cursor, tty_cursor); NHB(misc, misc);
#undef NHB
    DObs* d = &in->d;
    d->glyphs = s->glyphs; d->blstats = s->blstats; d->message = s->message; d->misc = s->misc;
    d->tty_chars = s->tty_chars; d->tty_colors = s->tty_colors; d->tty_cursor = s->tty_cursor; { static int keep = -1; if (keep < 0) keep = getenv("NH_STOCK_KEEPSDESC") ? 1 : 0; // ablation: which of the two dropped channels costs what
      static int nosd = -1; if (nosd < 0) nosd = getenv("NH_STOCK_NOSDESC") != NULL;
      d->sdesc = (nosd || (g_strict && !keep)) ? NULL : s->screen_descriptions;
      d->rawout = (nosd || (g_strict && !keep)) ? NULL : (unsigned char*)in->rawout;
      d->rawlen = (nosd || (g_strict && !keep)) ? NULL : &in->rawlen; }
    d->inv_glyphs = s->inv_glyphs; d->inv_strs = s->inv_strs; d->inv_letters = s->inv_letters; d->inv_oclasses = s->inv_oclasses;
    if (o->internal) d->internal = o->internal; if (o->inv_state) d->inv_state = o->inv_state; if (o->inv_true_glyphs) d->inv_true = o->inv_true_glyphs;
    d->redrawn = in->real_pg ? in->redrawn : NULL;
}

// diagnostic (read-only): NH_STOCK_CHAINDUMP=T1[,T2..] prints the floor object chain under the hero at those turns for the logged seed,
// read straight from the stock library's `level` (struct rm = 8 bytes, objects[COLNO][ROWNO] after locations; obj: nexthere +8, otyp +30, quan +40)
static const char* g_cd_tag = ""; static int g_cd_key = -1;
// NH_STOCK_IDSTATE=1: does identification knowledge survive from one game into the next inside ONE engine instance?
// struct objclass: short name_idx, short descr_idx, char* uname (aligned 8), then the bitfield word -- oc_name_known is
// bit 0 and oc_pre_discovered bit 3 of the byte at OBJC_FLAGS (24 bitfield bits pack into 3 bytes, so oc_class lands at 21). NetHack orders objects[] by class, so a non-decreasing
// oc_class across the array validates the stride before any count is believed.
#define OBJC_SIZE 40
#define OBJC_FLAGS 16
#define OBJC_CLASS 21
static void id_state(Inst* in, const char* when) {
    static int on = -1; if (on < 0) on = getenv("NH_STOCK_IDSTATE") != NULL;
    if (!on) return;
    const unsigned char* ob = (const unsigned char*)dlsym(in->dl, "objects");
    if (!ob) { fprintf(stderr, "IDSTATE no objects symbol\n"); return; }
    int known = 0, pre = 0, known_not_pre = 0, ok = 1, prev = 0;
    for (int i = 0; i < NUM_OBJECTS; i++) {
        const unsigned char* e = ob + (size_t)i * OBJC_SIZE;
        int cl = (signed char)e[OBJC_CLASS]; if (cl < prev || cl < 0 || cl > 18) ok = 0; else prev = cl;
        int k = e[OBJC_FLAGS] & 1, p = (e[OBJC_FLAGS] >> 3) & 1;
        known += k; pre += p; if (k && !p) known_not_pre++;
    }
    fprintf(stderr, "IDSTATE %s inst=%p ep=%ld seed=%lx known=%d pre=%d known_not_pre=%d layout_ok=%d\n",
            when, (void*)in, in->ep_n, in->seed0, known, pre, known_not_pre, ok);
}
// NH_STOCK_IDTYPE=<index>: per key, is that object type identified in the STOCK engine's own table?
static void id_type_watch(Inst* in) {
    static int ty = -2; if (ty == -2) { const char* v = getenv("NH_STOCK_IDTYPE"); ty = v ? atoi(v) : -1; }
    if (ty < 0 || !dr_log_this || !in->d.blstats) return;
    const unsigned char* ob = (const unsigned char*)dlsym(in->dl, "objects"); if (!ob) return;
    const unsigned char* e = ob + (size_t)ty * OBJC_SIZE;
    fprintf(stderr, "IDTYPE key=%ld T=%ld type=%d known=%d descr_idx=%d\n",
            in->rp_keys, in->d.blstats[20], ty, e[OBJC_FLAGS] & 1, (int)*(const short*)(e + 2));
}
static void chain_dump(Inst* in) {
    static long dt[8]; static int ndt = -1; if (ndt < 0) { ndt = 0; const char* v = getenv("NH_STOCK_CHAINDUMP"); if (v) { char b[128]; snprintf(b, sizeof b, "%s", v); for (char* t = strtok(b, ","); t && ndt < 8; t = strtok(NULL, ",")) dt[ndt++] = atol(t); } }
    if (!ndt || !dr_log_this || !in->d.blstats) return; long T = in->d.blstats[20]; int hit = 0; for (int i = 0; i < ndt; i++) if (dt[i] == T) hit = 1; if (!hit) return;
    char* lv = (char*)dlsym(in->dl, "level"); if (!lv) { fprintf(stderr, "chaindump: no level symbol\n"); return; }
    char* uu = (char*)dlsym(in->dl, "u"); int ux = uu ? (int)(signed char)uu[0] : -1, uy = uu ? (int)(signed char)uu[1] : -1;
    int x = (int)in->d.blstats[0] + 1, y = (int)in->d.blstats[1];
    { fprintf(stderr, "rmdump%s%d T=%ld hero x=%d y=%d:", g_cd_tag, g_cd_key, T, x, y); for (int dy = -2; dy <= 2; dy++) for (int dx = -2; dx <= 2; dx++) { int xx = x + dx, yy = y + dy; if (xx < 0 || xx >= 80 || yy < 0 || yy >= 21) continue; unsigned char* rm = (unsigned char*)(lv + ((size_t)xx * 21 + yy) * 8); int glyph = *(int*)rm; int typ = (signed char)rm[4]; int fl = rm[6]; fprintf(stderr, " [%d,%d]typ=%d mem=%d lit=%d waslit=%d", xx, yy, typ, glyph, (fl >> 6) & 1, (fl >> 7) & 1); } fprintf(stderr, "\n"); } // struct rm: int glyph; schar typ; uchar seenv; flags:5 horizontal:1 lit:1 waslit:1
    for (int dx = -1; dx <= 1; dx++) { int xx = x + dx; if (xx < 1 || xx >= 80) continue; char* head = *(char**)(lv + 80 * 21 * 8 + ((size_t)xx * 21 + y) * 8);
        fprintf(stderr, "chaindump T=%ld bl_x=%d y=%d u.ux=%d u.uy=%d cell x=%d:", T, x, y, ux, uy, xx); int n = 0;
        for (char* o = head; o && n < 80; o = *(char**)(o + 8), n++) { short otyp = *(short*)(o + 30); long quan = *(long*)(o + 40); fprintf(stderr, " [%d]%s x%ld", otyp, otyp >= 0 && otyp < NUM_OBJECTS ? NHT_OBJ_NAME[otyp] : "?", quan); }
        fprintf(stderr, " (n=%d)\n", n); }
}
// NH_STOCK_WTCHECK=1: compare the derived weight/capacity with the stock engine's own inventory, priced by the fork's nle_weight
// formula (true-type weights, corpses by monster, coins /100, partly eaten halved; containers count empty). Read-only, no RNG.
// The replay bench cannot check this channel: the fork's public glyphs carry appearances while stock's leak the true type, so
// the derive prices unidentified armor right on stock only (2026-09-12: bench 2.9 % weight mismatch was this artifact).
static long g_wc_n, g_wc_wt, g_wc_wth, g_wc_h, g_wc_cap, g_wc_bad, g_wc_shown;
static void wt_check_report(void) { fprintf(stderr, "WTCHECK boundaries=%ld weight_mismatch=%ld (hallucinating %ld of %ld) cap_mismatch=%ld layout_bad=%ld\n", g_wc_n, g_wc_wt, g_wc_wth, g_wc_h, g_wc_cap, g_wc_bad); }
static void wt_check(Inst* in) {
    static int on = -1, real_wt = -1; if (on < 0) { const char* rw = getenv("NH_STOCK_WTREAL"); real_wt = rw ? (atoi(rw) == 2 ? 2 : 1) : 0; on = real_wt || getenv("NH_STOCK_WTCHECK") != NULL; if (on) atexit(wt_check_report); } if (!on || !in->d.blstats || in->so.done) return;
    char** pinv = (char**)dlsym(in->dl, "invent"); int (*wcap)(void) = (int (*)(void))dlsym(in->dl, "weight_cap"); const unsigned char* ob = (const unsigned char*)dlsym(in->dl, "objects"); if (!pinv || !wcap || !ob) { __sync_fetch_and_add(&g_wc_bad, 1); return; }
    long w = 0; int i = 0, bad = 0; char items[4096]; int p = 0;
    for (char* o = *pinv; o && i < 55; o = *(char**)o, i++) {
        short otyp = *(short*)(o + 30); long q = *(long*)(o + 40); int cls = *(signed char*)(o + 49); char let = *(char*)(o + 50); int cnm = *(int*)(o + 60); unsigned eaten = *(unsigned*)(o + 68);
        if (in->d.inv_letters && (in->d.inv_letters[i] != (unsigned char)let || (in->d.inv_oclasses && in->d.inv_oclasses[i] != (unsigned char)cls))) bad = 1;
        long base = -1; if (cls == 12) w += (q + 50) / 100;
        else if (otyp < 0 || otyp >= NUM_OBJECTS) base = 0;
        else if (otyp == g_corpse_idx && cnm >= 0 && cnm < NUMMONS) { base = NHT_MON_CWT[cnm] * q; if (eaten) base /= 2; w += base; }
        else { // fork f7d8749ab public pricing: true type only while the name is displayed (dknown && oc_name_known), else the appearance's canonical slot; NH_STOCK_WTREAL=2 = the pre-fix true-type channel (for policies trained before it)
            int typ = otyp; if (real_wt != 2) { int dknown = (*(unsigned char*)(o + 54) >> 5) & 1; const unsigned char* oe = ob ? ob + (size_t)otyp * OBJC_SIZE : NULL; int nk = oe ? (oe[OBJC_FLAGS] & 1) : 0; int slot = oe ? (int)*(const short*)(oe + 2) : otyp;
                if (!(dknown && nk)) typ = nk ? slot : dr_gem_canon(slot); }
            base = NHT_OBJ_WT[typ] * q; if (eaten) base /= 2; w += base; }
        if (p < 3800) p += snprintf(items + p, sizeof items - p, " %c:%d/%s x%ld%s=%ld", let, otyp, otyp >= 0 && otyp < NUM_OBJECTS ? NHT_OBJ_NAME[otyp] : "?", q, eaten ? "(eaten)" : "", base);
    }
    int cap = wcap(); long cond = in->d.blstats[25];
    if (__sync_fetch_and_add(&g_wc_n, 1) % 200000 == 199999) wt_check_report();
    if (bad) { __sync_fetch_and_add(&g_wc_bad, 1); return; }
    if (cond & 0x200) __sync_fetch_and_add(&g_wc_h, 1);
    int mw = (int)w != in->S.wt, mc = cap != in->S.cap;
    if (mw) __sync_fetch_and_add((cond & 0x200) ? &g_wc_wth : &g_wc_wt, 1); if (mc) __sync_fetch_and_add(&g_wc_cap, 1);
    if (real_wt) { in->S.wt = (int)w; in->S.cap = cap; } // NH_STOCK_WTREAL=1: diagnostic crutch, the policy gets the engine's weight/capacity (rung-2 style, never a cert)
    if ((mw || mc) && __sync_fetch_and_add(&g_wc_shown, 1) < 40) { char m[256]; dr_msg(&in->d, m, sizeof m); fprintf(stderr, "WTCHECK T=%ld cond=%lx real wt=%ld cap=%d derived wt=%d cap=%d wlegs=%d msg=\"%.80s\" inv:%s\n", in->d.blstats[20], cond, w, cap, in->S.wt, in->S.cap, in->S.wlegs, m, items); }
}
static void sync_status(Inst* in, nle_obs* o) {
    o->done = in->so.done;
    o->how_done = in->so.how_done;
    o->in_normal_game = in->so.in_normal_game;
    if (o->internal) { o->internal[9] = 0; o->internal[10] = 0; }
}

#define NH_TOPLIN_OFF 16 /* offsetof(struct DisplayDesc, toplin) in the stock build */
static unsigned long elf_local_symbol(const char* path, const char* want) { // st_value of a local (non-dynamic) symbol from the file's .symtab
    int fd = open(path, O_RDONLY); if (fd < 0) return 0; struct stat st; if (fstat(fd, &st) < 0) { close(fd); return 0; }
    unsigned char* m = (unsigned char*)mmap(NULL, (size_t)st.st_size, PROT_READ, MAP_PRIVATE, fd, 0); close(fd); if (m == MAP_FAILED) return 0;
    ElfW(Ehdr)* eh = (ElfW(Ehdr)*)m; ElfW(Shdr)* sh = (ElfW(Shdr)*)(m + eh->e_shoff); unsigned long val = 0;
    for (int i = 0; i < eh->e_shnum && !val; i++) { if (sh[i].sh_type != SHT_SYMTAB) continue; ElfW(Sym)* sym = (ElfW(Sym)*)(m + sh[i].sh_offset); size_t n = sh[i].sh_size / sizeof(ElfW(Sym)); const char* str = (const char*)(m + sh[sh[i].sh_link].sh_offset);
        for (size_t k = 0; k < n; k++) if (ELF64_ST_TYPE(sym[k].st_info) == STT_OBJECT && !strcmp(str + sym[k].st_name, want)) { val = sym[k].st_value; break; } }
    munmap(m, (size_t)st.st_size); return val;
}
static int g_notopl = -1;
static int notopl(void) { if (g_notopl < 0) g_notopl = getenv("NH_STOCK_NOTOPL") != NULL; return g_notopl; }
static void topl_save(Inst* in) { if (notopl()) { if (in->d.message) { memcpy(in->topl_save, in->d.message, 256); in->topl_saved = 2; in->probe_mark = in->S.probe_keys; } else in->topl_saved = 0; return; } if (!in->p_toplines || !in->p_ttyDisplay || !*in->p_ttyDisplay) { in->topl_saved = 0; return; } memcpy(in->topl_save, in->p_toplines, 300); if (in->p_prevmsg) memcpy(in->prevmsg_save, in->p_prevmsg, 256); in->toplin_save = *(int*)((char*)*in->p_ttyDisplay + NH_TOPLIN_OFF); in->topl_saved = 1; in->probe_mark = in->S.probe_keys; }
static void topl_restore(Inst* in) { if (in->topl_saved == 2) { in->topl_saved = 0; if (in->S.probe_keys != in->probe_mark && in->d.message) memcpy(in->d.message, in->topl_save, 256); return; } if (!in->topl_saved) return; in->topl_saved = 0; if (in->S.probe_keys == in->probe_mark) return; memcpy(in->p_toplines, in->topl_save, 300); *(int*)((char*)*in->p_ttyDisplay + NH_TOPLIN_OFF) = in->toplin_save; if (in->p_prevmsg) memcpy(in->p_prevmsg, in->prevmsg_save, 256); }
static void topl_restore_always(Inst* in) { if (in->topl_saved == 2) { in->topl_saved = 0; if (in->d.message) memcpy(in->d.message, in->topl_save, 256); return; } if (!in->topl_saved) return; in->topl_saved = 0; memcpy(in->p_toplines, in->topl_save, 300); *(int*)((char*)*in->p_ttyDisplay + NH_TOPLIN_OFF) = in->toplin_save; if (in->p_prevmsg) memcpy(in->p_prevmsg, in->prevmsg_save, 256); }
static int stock_send(void* ctx, int key);
// The fork's getpos() returns at once (headless port: abort when the caller allows it, else the hero's own square).
// Stock's getpos is the interactive cursor browse and raises no misc flag; it announces itself with the verbose
// "(For instructions type a '?')" line. Answer it the fork's way and put the top line back as the fork would show it.
static void nh_answer_getpos(Inst* in) {
    for (int it = 0; it < 3; it++) {
        if (in->d.misc && (in->d.misc[0] || in->d.misc[1] || in->d.misc[2])) return;
        char m[256]; dr_msg(&in->d, m, sizeof m); char* mk = strstr(m, "(For instructions type a"); if (!mk) return;
        int force = strstr(m, "Where do you want") != NULL || strstr(m, "the desired") != NULL;
        topl_save(in); stock_send(in, force ? '.' : 27);
        char post[256]; post[0] = 0; if (in->d.message) snprintf(post, sizeof post, "%.255s", (const char*)in->d.message); int post_wait = in->d.misc && (in->d.misc[0] || in->d.misc[1] || in->d.misc[2]);
        topl_restore_always(in);
        *mk = 0; { char* e = m + strlen(m); while (e > m && e[-1] == ' ') *--e = 0; }
        if (!force && m[0] && !post_wait && !in->so.done && !getenv("NH_STOCK_NOVMORE")) { in->vmore = 1; snprintf(in->vmore_text, sizeof in->vmore_text, "%s", post); if (in->d.misc) in->d.misc[2] = 1; if (in->probelog) fprintf(in->probelog, "V %ld\n", in->rp_keys); }
        if (in->p_toplines) snprintf(in->p_toplines, 300, "%s", m); if (in->d.message) { memset(in->d.message, 0, 256); snprintf((char*)in->d.message, 256, "%s", m); }
        if (in->probelog) fprintf(in->probelog, "G %ld %d [%.70s]\n", in->rp_keys, force, m);
    }
}
static FILE* g_slog; // NH_STOCK_SIMPLELOG=<path>: same format as the gym backend's keylog
static void slog_open(void) { static int done; if (done) return; done = 1; const char* p = getenv("NH_STOCK_SIMPLELOG"); if (p && *p) g_slog = fopen(p, "w"); }
static int stock_send(void* ctx, int key) { // zero-time probe key straight to the stock instance
    Inst* in = (Inst*)ctx;
    if (in->so.done) return 1; // a finished coroutine must never be resumed (jump into a dead context)
    if (in->probelog) fprintf(in->probelog, "P %ld %d m=%d%d%d\n", in->rp_keys, key, in->d.misc ? in->d.misc[0] : -1, in->d.misc ? in->d.misc[1] : -1, in->d.misc ? in->d.misc[2] : -1);
    if (in->probelog && in->real_isaac) fprintf(in->probelog, "PD %ld %lu\n", in->rp_keys, in->draws);
    in->so.action = key;
    // probes must not touch display memory: a full-screen probe window closes with docrt(), whose newsym() on unseen cells turns
    // remembered lit corridors/rooms dark (display.c: !waslit || (dark_room && use_color)); the fork never redraws there, so run
    // every probe key with dark_room off (struct flag byte 8 in the stock build; verified once against nobones/autoopen/confirm)
    { static int nodark = -1; if (nodark < 0) nodark = getenv("NH_STOCK_NODARKFIX") != NULL; // the gym binding cannot reach engine flags: price that
      static int off = -2; unsigned char* fl = (unsigned char*)dlsym(in->dl, "flags"); if (nodark) fl = NULL;
      if (off == -2) { off = (fl && fl[8] == 1 && fl[6] == 0 && fl[3] == 1 && fl[7] == 1) ? 8 : -1; fprintf(stderr, "nh_stock: dark_room hook %s\n", off >= 0 ? "ok" : "MISMATCH (probes will alter lit memory)"); }
      unsigned char saved = 0; if (off >= 0 && fl) { saved = fl[off]; fl[off] = 0; }
      in->in_probe++; guarded_step(in); in->in_probe--;
      if (off >= 0 && fl) fl[off] = saved; }
    g_cd_tag = " probe"; g_cd_key = key; chain_dump(in); g_cd_tag = ""; g_cd_key = -1;
    return in->so.done;
}

// ---------------------------------------------------------------- engine entry points (fork signatures)
// Interposed for the stock engine copies (RTLD_LOCAL libs resolve their PLT calls against the executable first):
// stock nle.c runs the whole game on a create_fcontext_stack(64 KiB) coroutine stack, which overflows on deep call
// chains under this policy (throw/explode cascades) and corrupts the engine context -> "NetHack exit with status
// <garbage>". The fork's fix is 256 KiB. Same layout as deboost (mmap + one guard page, sptr = top, ssize = mapped
// size) so the engine's own destroy_fcontext_stack() unmaps it. NH_STOCK_STACK_KB overrides the size.
// fcontext_stack_t comes from the fork headers already included via nletypes.h (same layout as stock: sptr, ssize)
fcontext_stack_t create_fcontext_stack(size_t size) {
    static size_t want;
    if (!want) { const char* e = getenv("NH_STOCK_STACK_KB"); want = (size_t)(e ? atol(e) : 256) * 1024; }
    size_t page = (size_t)sysconf(_SC_PAGESIZE);
    size_t sz = size < want ? want : size;
    sz = (sz / page) * page; if (sz < 2 * page) sz = 2 * page;
    fcontext_stack_t s = {0, 0};
    void* vp = mmap(0, sz, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (vp == MAP_FAILED) return s;
    mprotect(vp, page, PROT_NONE);
    s.sptr = (char*)vp + sz; s.ssize = sz;
    { static int once; if (__sync_bool_compare_and_swap(&once, 0, 1)) fprintf(stderr, "nh_stock: coroutine stack %zu KiB (interposed; engine asked for %zu KiB)\n", sz / 1024, size / 1024); }
    return s;
}

nle_ctx_t* nle_start(nle_obs* obs, FILE* f, nle_settings* set) {
    (void)f;
    static int env_seq;
    Inst* in = (Inst*)calloc(1, sizeof(Inst));
    in->fd = -1;
    in->fobs = obs;
    g_strict = getenv("NH_STOCK_STRICT") != NULL; if (g_strict) setenv("NH_NLE_OPTS", "1", 1);
    g_verbose = getenv("NH_STOCK_VERBOSE") != NULL; g_trace = getenv("NH_STOCK_TRACE") != NULL; g_trace_live = getenv("NH_STOCK_TRACE_LIVE") != NULL; { const char* bt = getenv("NH_STOCK_DRAWBT"); if (bt) sscanf(bt, "%lx:%ld", &g_bt_seed, &g_bt_key); }
    { // the env builds its per-env hackdir from NETHACKDIR; stock panics on the fork's dungeon file
      // ("Dungeon description not valid", how_done 11, every game scores 0), so refuse anything but the stock data dir
        static int checked;
        if (!checked) {
            const char* nd = getenv("NETHACKDIR");
            char want[4400], libdir[4200]; snprintf(libdir, sizeof libdir, "%s", stock_lib_path());
            char* slash = strrchr(libdir, '/'); if (slash) *slash = 0;
            snprintf(want, sizeof want, "%s/nethackdir", libdir);
            char rn[PATH_MAX], rw[PATH_MAX];
            if (!nd || !realpath(nd, rn) || !realpath(want, rw) || strcmp(rn, rw) != 0) {
                fprintf(stderr, "nh_stock: NETHACKDIR must be the stock data dir %s (got %s); refusing to run the stock engine on the fork's data\n", want, nd ? nd : "(unset)");
                exit(2);
            }
            checked = 1;
        }
    }
    if (inst_open_lib(in) != 0) exit(1);
    { static int reported; int np = nh_patch_got(in); if (!reported && __sync_bool_compare_and_swap(&reported, 0, 1)) fprintf(stderr, "nh_stock: clock interposition: %d GOT slots redirected per copy (%s)\n", np, np > 0 ? "seed-derived birthday + fixed tm, as the fork" : "OFF: real wall clock"); }
    wire_obs(in, obs);
    memset(&in->sset, 0, sizeof in->sset);
    snprintf(in->sset.hackdir, sizeof in->sset.hackdir, "%s", set->hackdir);
    // NH_STOCK_LITERALOPTS: take the option string verbatim instead of writing an rc
    // file, which is how NLE itself passes options. Determinism harness only.
    const char* litopts = getenv("NH_STOCK_LITERALOPTS");
    // the same rc file the fork reads, minus the fork's fast status path (stock fills blstats from the status line)
    {
        const char* opt = set->options;
        if (opt[0] == '@') {
            char dst[4600]; snprintf(dst, sizeof dst, "%s.stock%s", opt + 1, g_strict ? "n" : "");
            static int rc_lock; static int rc_seq;
            while (__sync_lock_test_and_set(&rc_lock, 1)) {} // one writer: the worker threads all start here at once
            if (access(dst, R_OK) != 0) {
                char tmp[4700]; snprintf(tmp, sizeof tmp, "%s.%d.%d", dst, (int)getpid(), __sync_add_and_fetch(&rc_seq, 1));
                FILE* fi = fopen(opt + 1, "r"); FILE* fo = fopen(tmp, "w");
                if (fi && fo) {
                    char line[8192];
                    while (fgets(line, sizeof line, fi)) {
                        char* s;
                        while ((s = strstr(line, ",!status_updates")) != NULL) memmove(s, s + 16, strlen(s + 16) + 1);
                        while ((s = strstr(line, "!status_updates,")) != NULL) memmove(s, s + 16, strlen(s + 16) + 1);
                        // NH_STOCK_STRICT: NLE's own default option set (nle/nethack/nethack.py NETHACKOPTIONS), the interface the
                        // NetHack Challenge (and AutoAscend) ran: autopickup of $?!/ only, NetHack's own pile_limit, no exception
                        // list. Done here, not via the env's rc writer, so it holds whatever the env wrote and in any call order.
                        if (g_strict) {
                            if (!strncmp(line, "AUTOPICKUP_EXCEPTION", 20)) continue; // config-file-only directive: drop it
                            // idempotent: the env's own rc writer may already have applied this (NH_NLE_OPTS set at process
                            // start), and applying it twice produced a line with pickup_types in it two times.
                            if (strstr(line, "pickup_types:")) { fputs(line, fo); continue; }
                            static int keep_pl = -1; if (keep_pl < 0) keep_pl = getenv("NH_KEEP_PILELIMIT") != NULL;
                            if (keep_pl) { /* ablation: keep pile_limit:0, just add the NLE pickup set */
                                if ((s = strstr(line, "pile_limit:0,")) != NULL) { char rest[8192]; snprintf(rest, sizeof rest, "%s", s);
                                    snprintf(s, sizeof line - (size_t)(s - line), "pickup_types:$?!/,%s", rest); }
                            } else if ((s = strstr(line, "pile_limit:0,")) != NULL) {
                                char rest[8192]; snprintf(rest, sizeof rest, "%s", s + 13);
                                snprintf(s, sizeof line - (size_t)(s - line), "pickup_types:$?!/,%s", rest);
                            }
                        }
                        fputs(line, fo);
                    }
                }
                if (fi) fclose(fi);
                if (fo) { fclose(fo); rename(tmp, dst); }
            }
            __sync_lock_release(&rc_lock);
            snprintf(in->sset.options, sizeof in->sset.options, "@%s", dst);
            if (litopts && *litopts) snprintf(in->sset.options, sizeof in->sset.options, "%s", litopts);
            if (g_strict) { static int shown; if (__sync_bool_compare_and_swap(&shown, 0, 1)) { FILE* fv = fopen(dst, "r"); char l[8192];
                while (fv && fgets(l, sizeof l, fv)) if (!strncmp(l, "OPTIONS=", 8)) { fprintf(stderr, "STRICT rc %s\n%s", dst, l); break; }
                if (fv) fclose(fv); } }
        } else {
            snprintf(in->sset.options, sizeof in->sset.options, "%s", opt);
        }
    }
    { static int shown_opts; if (__sync_bool_compare_and_swap(&shown_opts, 0, 1)) // what the engine actually gets
        fprintf(stderr, "nh_stock: FINAL OPTIONS=%s\n", in->sset.options); }
    in->sset.spawn_monsters = set->spawn_monsters;
    in->ch_steps = 0; in->ch_noprog = 0; in->ch_maxnoprog = 0; in->ch_turn = -1; in->ch_aborted = 0; in->ch_logged = 0;
    sseed_t seed = {{set->initial_seeds.seeds[0], set->initial_seeds.seeds[1]}, 0};
    { const char* fs = getenv("NH_STOCK_FORCESEED"); // determinism harness: pin the game both backends play
      if (fs && *fs) { unsigned long v = strtoul(fs, NULL, 0); seed.seeds[0] = v; seed.seeds[1] = v; } }
    in->seed0 = seed.seeds[0];
    { const char* pd = getenv("NH_STOCK_PROBELOG"); if (pd) { char fn[512]; snprintf(fn, sizeof fn, "%s/%lx.probes", pd, in->seed0); in->probelog = fopen(fn, "w"); } }
    in->ep_n++;
    id_state(in, "pre "); // the table as the PREVIOUS game left it
    if (guarded_start(in, set->initial_seeds.use_init_seeds ? &seed : NULL)) { obs->done = 1; obs->how_done = -1; return (nle_ctx_t*)in; }
    id_state(in, "post"); // after this game's own init_objects()
    // NH_STOCK_CLEAREOS=1: supply the "clear to end of screen" capability NLE leaves undeclared. Its ANSI terminal branch has
    // the line commented out upstream (win/tty/termcap.c: /* nh_CD = "\033[J" */), so cl_eos() falls back to walking down the
    // screen a newline at a time; against a scrolling emulator that pushes window content off the top, and a list window ends
    // up delivering one entry per page. nh_CD is the third pointer of the exported struct tc_lcl_data (tc_CM, tc_ND, tc_CD).
    // This sets a terminal capability every real terminal has; it changes no game state and stock's own source is untouched.
    { static int ce = -1; if (ce < 0) ce = getenv("NH_STOCK_CLEAREOS") != NULL;
      if (ce) { static char esc[] = "\033[J"; char** tc = (char**)dlsym(in->dl, "tc_lcl_data");
        if (tc) { tc[2] = esc; static int shown; if (__sync_bool_compare_and_swap(&shown, 0, 1)) fprintf(stderr, "nh_stock: clear-to-end-of-screen supplied\n"); }
        else { static int warned; if (__sync_bool_compare_and_swap(&warned, 0, 1)) fprintf(stderr, "nh_stock: tc_lcl_data not found\n"); } } }
    sync_status(in, obs);
    if (in->so.done) { // the engine exited during start-up: hand the env a finished episode, touch nothing else
        static long n_startdead; long k = __sync_add_and_fetch(&n_startdead, 1);
        if (k <= 3 || g_verbose) { fprintf(stderr, "nh_stock: game ended during start-up (#%ld, how_done=%d) hackdir=%s\n", k, in->so.how_done, in->sset.hackdir); for (int r = 0; r < 6; r++) fprintf(stderr, "  tty[%d] %.78s\n", r, in->so.tty_chars + r * TTY_CO); fprintf(stderr, "  msg: %.120s\n", in->so.message); }
        obs->done = 1; obs->how_done = -1;
        return (nle_ctx_t*)in;
    }
    slog_open();
    if (g_slog) fprintf(g_slog, "S role=%d race=%d gender=%d align=%d\n", 0, 0, 0, 0);
    unsigned dseed = (unsigned)(set->initial_seeds.seeds[0] ^ (unsigned long)(__sync_add_and_fetch(&env_seq, 1) * 7919));
    dr_reset(&in->S, &in->d, dseed);
    dr_identity_from_text(&in->S, &in->d);
    { char msg[256]; dr_msg(&in->d, msg, sizeof msg); dr_update_memory(&in->S, &in->d, msg); dr_track_path(&in->S, &in->d, -1); }
    topl_save(in);
    if (!in->so.done && !dr_prompt_open(&in->d)) { dr_probe_discoveries(&in->S, &in->d, in, stock_send); in->S.disc_time_probed = 1; }
    if (obs->inv_state) memset(obs->inv_state, 0, INV * NLE_INV_STATE_FIELDS);
    if (obs->inv_true_glyphs) for (int i = 0; i < INV; i++) obs->inv_true_glyphs[i] = NO_GLYPH;
    in->mapped = 0;
    { const char* rd = getenv("NH_KEYREPLAY"); if (rd) { static int init; if (__sync_bool_compare_and_swap(&init, 0, 1)) atexit(rp_report);
        char fn[512]; snprintf(fn, sizeof fn, "%s/%lx.keys", rd, set->initial_seeds.seeds[0]); in->replay = fopen(fn, "r"); in->seed0 = set->initial_seeds.seeds[0];
        if (!in->replay) __sync_fetch_and_add(&g_rp_nofile, 1);
        else { unsigned long s0, s1, h0; if (!in->so.done) { dr_boundary(&in->S, &in->d, in, stock_send); chain_dump(in); wt_check(in); dr_export_glyphs(&in->S, &in->d, 1); in->mapped = 1; sync_status(in, obs); topl_restore(in); }
            if (rp_read_start(in, &s0, &s1, &h0) && h0 != dr_hash_sel(&in->d)) { __sync_fetch_and_add(&g_rp_startdiff, 1); if (g_verbose) { char m[256]; dr_msg(&in->d, m, sizeof m); fprintf(stderr, "replay %lx: start hash differs; stock msg=%s bl=", in->seed0, m); for (int i = 0; i < 27; i++) fprintf(stderr, "%ld ", in->d.blstats[i]); fprintf(stderr, "\nreplay %lx: map=", in->seed0); for (int k = 0; k < 21 * 79; k++) if (in->d.glyphs[k] != 2359 && in->d.glyphs[k] < 5976) fprintf(stderr, "%d:%d ", k, in->d.glyphs[k]); fprintf(stderr, "\n"); for (int r = 0; r < 24; r++) { char row[81]; dr_row(&in->d, r, row); fprintf(stderr, "replay %lx: tty%02d=%s\n", in->seed0, r, row); } } } __sync_fetch_and_add(&g_rp_eps, 1); } } }
    return (nle_ctx_t*)in;
}

nle_ctx_t* nle_step(nle_ctx_t* c, nle_obs* obs) {
    Inst* in = (Inst*)c;
    if (in->so.done) { obs->done = 1; return c; } // finished coroutine: the env must reset, not step
    wire_obs(in, obs); // the env may re-bind any output buffer between calls (multi-buffer pipeline): always write where it reads
    int key = obs->action;
    in->kh[in->khn++ & 15] = key;
    { static int ml = -1; if (ml < 0) ml = getenv("NH_STOCK_MSGLOG") != NULL; // message census for the score-gap loop (lycanthropy / prayer / polymorph events)
      if (ml && in->d.message && in->d.message[0]) { const char* m = (const char*)in->d.message; static const char* PATS[] = {"feverish", "purified", "You turn into", "You begin praying", "displeased", "smite", "hopeful feeling", "You feel much better", "You return to human", "You feel a change coming", "You are hit by a", "wolfsbane"};
        for (size_t i = 0; i < sizeof PATS / sizeof PATS[0]; i++) if (strstr(m, PATS[i])) { if (strcmp(in->lastmsg, m)) { fprintf(stderr, "msg %lx: T=%ld %s\n", in->seed0, in->d.blstats[20], m); snprintf(in->lastmsg, sizeof in->lastmsg, "%s", m); } break; } } }
    if (g_verbose && in->S.same == 21) { // what the env saw during the zero-time loop (post-probe export of the previous boundary)
        char sm[256]; dr_msg(&in->d, sm, sizeof sm); char tl[81]; for (int i = 0; i < 80; i++) { unsigned char ch = in->tty_chars[i]; tl[i] = ch ? (char)ch : ' '; } tl[80] = 0;
        fprintf(stderr, "loopobs %lx: T=%ld key=%d msg=[%s] top=[%s] misc=%d%d%d hp=%ld/%ld hd=%ld cond=%lx x=%ld y=%ld\n", in->seed0, in->d.blstats[20], key, sm, tl, in->d.misc ? in->d.misc[0] : -1, in->d.misc ? in->d.misc[1] : -1, in->d.misc ? in->d.misc[2] : -1, in->d.blstats[10], in->d.blstats[11], in->d.blstats[18], in->d.blstats[25], in->d.blstats[0], in->d.blstats[1]);
        for (int r = 1; r < 6; r++) { char row[81]; for (int i = 0; i < 80; i++) { unsigned char ch = in->tty_chars[r * 80 + i]; row[i] = ch ? (char)ch : ' '; } row[80] = 0; fprintf(stderr, "loopobs %lx: tty%d [%s]\n", in->seed0, r, row); }
        for (int r = 22; r < 24; r++) { char row[81]; for (int i = 0; i < 80; i++) { unsigned char ch = in->tty_chars[r * 80 + i]; row[i] = ch ? (char)ch : ' '; } row[80] = 0; fprintf(stderr, "loopobs %lx: tty%d [%s]\n", in->seed0, r, row); }
    }
    unsigned long rh = 0; int rdone = 0; int have_rec = 0;
    if (in->replay && !in->rp_over) { int rk; if (rp_read_key(in->replay, &rk, &rh, &rdone)) { key = rk; have_rec = 1; in->rp_keys++; } else { in->rp_over = 1; } }
    if (in->vmore) { // the fork is showing --More-- here: keys other than space/Enter/ESC are eaten, the dismissal reveals the text the turn produced (nothing after ESC: WIN_STOP)
        int dis = key == ' ' || key == 13 || key == 10 || key == 27;
        if (dis) { in->vmore = 0; const char* t = key == 27 ? "" : in->vmore_text; if (in->p_toplines) snprintf(in->p_toplines, 300, "%s", t); if (in->d.message) { memset(in->d.message, 0, 256); snprintf((char*)in->d.message, 256, "%s", t); } if (in->d.misc) in->d.misc[2] = 0; }
        if (in->probelog) fprintf(in->probelog, "%s %ld %d\n", dis ? "VD" : "VS", in->rp_keys, key);
        goto vmore_skip; }
    in->so.action = key;
    in->S.count_pending = (key >= (int)'0' && key <= (int)'9'); // a count prefix is being typed: no probe may come between its digits and the command
    if (in->d.blstats && in->d.blstats[20] > 0) memcpy(in->last_bl, in->d.blstats, sizeof in->last_bl);
    if (guarded_step(in)) { sync_status(in, obs); obs->done = 1; obs->how_done = -1; return c; } // full stock fill: glyph buffers hold true glyphs again
    if (in->probelog && in->real_isaac) fprintf(in->probelog, "KD %ld %lu\n", in->rp_keys, in->draws); // draws right after the recorded key, before any probe
    if (g_trace && have_rec) { memcpy(in->raw, in->so.glyphs, sizeof in->raw); fprintf(stderr, "replay %lx: KRstock %ld %lx %lx %lu\n", in->seed0, in->rp_keys, nh_ctx_hash(in->rng_ctx[0]), nh_ctx_hash(in->rng_ctx[1]), in->draws); }
vmore_skip:
    in->mapped = 0;
    sync_status(in, obs);
    { static unsigned long ls; static int lsi; if (!lsi) { lsi = 1; const char* v = getenv("NH_STOCK_LOGSEED"); ls = v ? strtoul(v, NULL, 16) : 0; } dr_log_this = in->replay != NULL && (!ls || in->seed0 == ls); } // NH_STOCK_LOGSEED=<hex>: derive diagnostics for one instance only
    if (!in->so.done && !in->vmore && !getenv("NH_STOCK_NOGETPOS")) nh_answer_getpos(in);
    topl_save(in);
    int stalled = dr_after_key(&in->S, &in->d, in, stock_send, key, in->so.done);
    int at_boundary = have_rec && t_rp_boundary;
    if (at_boundary && !rdone && !in->so.done && !stalled) { // an env step boundary: derive (probes) + export, then compare, like the fork's full fill
        dr_boundary(&in->S, &in->d, in, stock_send); chain_dump(in); wt_check(in); dr_export_glyphs(&in->S, &in->d, 1); in->mapped = 1; sync_status(in, obs);
    } else if (!in->so.done && !stalled && !rdone) {
        // a move inside a multi-key env step (e.g. [move, e, y, Enter] ending blind): the fork's arrival look happened at the move,
        // so derive now while the hero can still see; the boundary then reuses this cell (NH_STOCK_NOMIDLOOK=1 disables)
        static int nomid = -1; if (nomid < 0) nomid = getenv("NH_STOCK_NOMIDLOOK") != NULL;
        if (!nomid && dr_hero_moved(&in->S, &in->d) && !dr_prompt_open(&in->d) && !in->S.count_pending && in->d.blstats && !(in->d.blstats[25] & 0x220)) dr_boundary(&in->S, &in->d, in, stock_send); // only when a look can actually run, else the boundary keeps 'moved'
    }
    topl_restore(in);
    if (g_strict && !in->so.done && (in->ch_steps >= 1000000 || in->ch_noprog >= 10000)) { in->ch_aborted = 1; in->so.done = 1; in->so.how_done = 13; obs->done = 1; obs->how_done = 13; } // NetHackChallenge: max_episode_steps 1e6, no_progress_timeout 10,000 steps
    id_type_watch(in);
    { static int wl2 = -1; if (wl2 < 0) wl2 = getenv("NH_STOCK_WEDGELOG") != NULL;
      if (wl2 && in->ch_noprog > 200 && obs->message) { // what the POLICY sees, at the step boundary
          char m[256]; snprintf(m, sizeof m, "%.120s", (const char*)obs->message);
          if (strstr(m, "# ") || strstr(m, "terrain") || strstr(m, "Unknown command"))
              fprintf(stderr, "BOUNDARYMSG noprog=%ld \"%.100s\"\n", in->ch_noprog, m); } }
    if (g_strict && in->so.done && !in->ch_logged) { in->ch_logged = 1; fprintf(stderr, "CHALLENGE %lx steps=%ld maxnoprog=%ld aborted=%d score=%ld turn=%ld how=%d\n", in->seed0, in->ch_steps, in->ch_maxnoprog, in->ch_aborted, in->d.blstats ? in->d.blstats[9] : -1L, in->d.blstats ? in->d.blstats[20] : -1L, in->so.how_done); }
    if (in->probelog && in->real_isaac) fprintf(in->probelog, "D %ld %lu\n", in->rp_keys, in->draws);
    if (g_trace && (have_rec || g_trace_live)) { char tag[64]; int tl = -1, im = -1, ir = -1; if (in->p_ttyDisplay && *in->p_ttyDisplay) { tl = *(int*)((char*)*in->p_ttyDisplay + 16); im = *(int*)((char*)*in->p_ttyDisplay + 24); ir = *(int*)((char*)*in->p_ttyDisplay + 28); } snprintf(tag, sizeof tag, "Tstock key=%d misc=%d%d%d tty=%d/%d/%d n", key, in->d.misc ? in->d.misc[0] : -1, in->d.misc ? in->d.misc[1] : -1, in->d.misc ? in->d.misc[2] : -1, tl, im, ir); snprintf(tag + strlen(tag), sizeof tag - strlen(tag), "%s", ""); if (0) snprintf(tag, sizeof tag, "Tstock key=%d misc=%d%d%d n", key, in->d.misc ? in->d.misc[0] : -1, in->d.misc ? in->d.misc[1] : -1, in->d.misc ? in->d.misc[2] : -1); if (!have_rec) in->rp_keys++; trace_bl(in, tag); }
    if (have_rec && in->rp_keys == 1 && g_verbose) { char m1[256]; dr_msg(&in->d, m1, sizeof m1); fprintf(stderr, "replay %lx: MSG1 %s\n", in->seed0, m1); }
    if (have_rec) {
        if (at_boundary && !in->rp_diverged && !rdone && !in->so.done && dr_hash_sel(&in->d) != rh) { in->rp_diverged = 1; rp_attribute(in); long t = in->d.blstats[20]; int bin = t < 10 ? 0 : t < 50 ? 1 : t < 200 ? 2 : t < 1000 ? 3 : t < 5000 ? 4 : t < 20000 ? 5 : 6; __sync_fetch_and_add(&g_rp_div_turns[bin], 1); __sync_fetch_and_add(&g_rp_diverged, 1); if (g_verbose) { fprintf(stderr, "replay %lx: diverged at key %ld turn %ld (key %d)\n", in->seed0, in->rp_keys, t, key); static int dumps; if (dumps < 3) { dumps++; for (int r = 0; r < 24; r++) { char row[81]; dr_row(&in->d, r, row); if (row[0]) fprintf(stderr, "replay %lx: div_tty%02d=%s\n", in->seed0, r, row); } } } }
        if (rdone || in->so.done) { if (!in->rp_diverged) __sync_fetch_and_add(&g_rp_exact, 1); obs->done = 1; in->rp_over = 1;
            if (g_verbose) fprintf(stderr, "replay %lx: E score=%ld turn=%ld depth=%ld how=%d\n", in->seed0, in->d.blstats[9], in->d.blstats[20], in->d.blstats[12], in->so.how_done);
            if (g_verbose) fprintf(stderr, "replay %lx: END %s after %ld keys turn %ld (rec_done=%d stock_done=%d)\n", in->seed0, in->rp_diverged ? "diverged" : "EXACT", in->rp_keys, in->d.blstats[20], rdone, in->so.done); }
    } else if (in->replay && in->rp_over && !obs->done) { obs->done = 1; obs->how_done = -1; } // recorded stream exhausted
    if (!in->replay && in->so.done && g_verbose) fprintf(stderr, "live %lx: E score=%ld turn=%ld depth=%ld how=%d\n", in->seed0, in->last_bl[9], in->last_bl[20], in->last_bl[12], in->so.how_done);
    if (g_slog) fprintf(g_slog, "K %d %d\n", key, in->so.done);
    if (stalled) {
        // zero-time loop: end the episode as truncated, like the python bridge
        if (!in->truncations || g_verbose) { in->truncations++; if (g_verbose) fprintf(stderr, "nh_stock: truncated at T=%ld after %d keys without game time\n", in->d.blstats[20], DR_STALL_CAP); }
        if (g_verbose) { // stall context: message, tty top line, last 16 keys
            char sm[256]; dr_msg(&in->d, sm, sizeof sm); char tl[81]; for (int i = 0; i < 80; i++) { unsigned char ch = in->tty_chars[i]; tl[i] = ch ? (char)ch : ' '; } tl[80] = 0;
            fprintf(stderr, "stall %lx: T=%ld hp=%ld dlvl=%ld msg=[%s] top=[%s] keys=", in->seed0, in->d.blstats[20], in->d.blstats[10], in->d.blstats[12], sm, tl);
            for (unsigned i = in->khn > 16 ? in->khn - 16 : 0; i < in->khn; i++) fprintf(stderr, "%d,", in->kh[i & 15]); fprintf(stderr, "\n");
        }
        obs->done = 1; obs->how_done = -1;
    }
    return c;
}

// step boundary: probes, every derived hook value, then the glyph export (bijection + hero tile + engraving bits)
nle_ctx_t* nle_obs_refresh(nle_ctx_t* c, nle_obs* obs) {
    Inst* in = (Inst*)c;
    if (in->so.glyphs != (obs->glyphs ? obs->glyphs : in->glyphs) || in->so.blstats != (obs->blstats ? obs->blstats : in->blstats) || in->so.message != (obs->message ? obs->message : in->message)) wire_obs(in, obs);
    sync_status(in, obs);
    if (obs->done) return c;
    if (in->mapped) return c; // a second refresh without a key in between: nothing new to derive
    if (in->replay) { dr_export_glyphs(&in->S, &in->d, 1); in->mapped = 1; return c; } // replay: the env's own step structure is not the recorded one; probes only at recorded R boundaries
    topl_save(in);
    dr_boundary(&in->S, &in->d, in, stock_send); wt_check(in);
    topl_restore(in);
    dr_export_glyphs(&in->S, &in->d, 1);
    in->mapped = 1;
    if (g_slog) { unsigned long pp[9]; dr_obs_hash_parts(&in->d, pp); fprintf(g_slog, "R"); for (int i = 0; i < 8; i++) fprintf(g_slog, " %lx", pp[i]); fprintf(g_slog, "\n"); fflush(g_slog); }
    return c;
}

void nle_end(nle_ctx_t* c) {
    Inst* in = (Inst*)c;
    if (!in) return;
    if (in->replay) fclose(in->replay);
    if (in->probelog) fclose(in->probelog);
    if (in->ctx && in->s_end && !in->crashed) in->s_end(in->ctx); // a faulted engine is abandoned (its stack leaks), never re-entered
    inst_close_lib(in);
    free(in);
}

void nle_identity(nle_ctx_t* c, int* r, int* rc, int* g, int* a) {
    Inst* in = (Inst*)c;
    *r = in->S.role; *rc = in->S.race; *g = in->S.gender; *a = in->S.align;
}

int nle_path_drain(nle_ctx_t* c, short* p, int n) {
    Inst* in = (Inst*)c;
    int m = n < in->S.path_n ? n : in->S.path_n;
    memcpy(p, in->S.path, 2 * (size_t)m * sizeof(short));
    in->S.path_n = 0;
    return m;
}

// ---------------------------------------------------------------- fork-only hooks, from the derived state
long nle_shop_price(nle_ctx_t* c) { return ((Inst*)c)->S.price; }
int nle_terrain_underfoot(nle_ctx_t* c) { return ((Inst*)c)->S.terrain; }
int nle_inside_shop(nle_ctx_t* c) { return ((Inst*)c)->S.inshop; }
int nle_container_at(nle_ctx_t* c) { return ((Inst*)c)->S.cont; }
int nle_food_underfoot(nle_ctx_t* c) { return ((Inst*)c)->S.food; }
int nle_discoveries(nle_ctx_t* c) { (void)c; return 0; }
int nle_peaceful_at(nle_ctx_t* c, int x, int y) { Inst* in = (Inst*)c; return (x >= 1 && x < 80 && y >= 0 && y < 21) ? in->S.peace[y * 79 + (x - 1)] : 0; }
int nle_lnc_bits(nle_ctx_t* c) { return ((Inst*)c)->S.lnc; }
void nle_weight(nle_ctx_t* c, int* wt, int* cap) { Inst* in = (Inst*)c; *wt = in->S.wt; *cap = in->S.cap; }
int nle_spells(nle_ctx_t* c, short* a, signed char* b, signed char* d, int* e, int n) {
    Inst* in = (Inst*)c; int m = n < in->S.nsp ? n : in->S.nsp;
    for (int i = 0; i < m; i++) { a[i] = in->S.sp_ids[i]; b[i] = in->S.sp_levs[i]; d[i] = in->S.sp_fails[i]; e[i] = in->S.sp_knows[i]; }
    return m;
}
int nle_cast_blocked(nle_ctx_t* c) { return ((Inst*)c)->S.castblk; }
int nle_intrinsics(nle_ctx_t* c) { return ((Inst*)c)->S.intr; }
