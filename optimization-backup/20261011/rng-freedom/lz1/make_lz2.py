import shutil, re
from pathlib import Path
CS=Path('/puffertank/experiments/nethack-compact-state-20261008/engines'); dst=CS/'lz2/source'
if dst.parent.exists(): shutil.rmtree(dst.parent)
shutil.copytree(CS/'lz0/source',dst,symlinks=True)
def rep(path,old,new,count=1):
    p=dst/path; s=p.read_text(); assert s.count(old)==count,(path,s.count(old),old[:70]); p.write_text(s.replace(old,new))
lazy='''
__thread int nh_lazy_reason; /* 1 unicorn/noteleport, 2 hero or image adjacent, 3 tracked legal cell first, 4 displacement decision */
/* Lazy neighbour selection for m_move. 1 = chose (nix/niy/info_out), 0 = no legal cell, -1 = nothing evaluated: take the full path,
   2 = fell back but the full list (poss/info/cnt, scan order) is complete: run the original selection loop on it. */
int
nh_lazy_select(struct monst *mon, long flag, int *appr_io, int gx, int gy, int omx, int omy,
               xchar *nix, xchar *niy, long *info_out, coord *poss, long *info, int *cnt_out)
{
    struct nh_mfnd c;
    int appr = *appr_io, j, k, n, nidist0, bits[9], keys[9], bit, nx, ny, cnt;
    unsigned int cand, trackmask = 0;
    long inf, cinfo[9];
    signed char cstate[9]; /* 0 unevaluated, 1 legal, 2 illegal */

    if (SPWQ(mon->data, SPW_UNICORN, is_unicorn(mon->data)) && level.lflags.noteleport) { nh_lazy_reason = 1; return -1; }
    if (distmin(omx, omy, u.ux, u.uy) <= 1 || distmin(omx, omy, mon->mux, mon->muy) <= 1) { nh_lazy_reason = 2; return -1; }
    nidist0 = dist2(omx, omy, gx, gy);
    if (!mon->mpeaceful && level.lflags.shortsighted
        && nidist0 > (couldsee(omx, omy) ? 144 : 36) && appr == 1)
        appr = 0;
    *appr_io = appr;
    for (j = 0; j < MTSZ; j++)
        trackmask |= nh_move_position_bit(omx, omy, mon->mtrack[j].x, mon->mtrack[j].y);
    nh_mfnd_begin(mon, flag, &c);
 again:
    cand = c.candidates;
    for (j = 0; j < 9; j++) cstate[j] = 0;
#define NH_LAZY_EVAL(b) (cstate[b] ? cstate[b] == 1 : ((cstate[b] = nh_mfnd_cell(&c, c.x - 1 + (b) / 3, c.y - 1 + (b) % 3, &cinfo[b]) ? 1 : 2) == 1))
    if (appr != 0) {
        unsigned int m = cand;
        n = 0;
        while (m) {
            int p, key;
            bit = __builtin_ctz(m); m &= m - 1;
            key = dist2(c.x - 1 + bit / 3, c.y - 1 + bit % 3, gx, gy) * 16 + bit; /* approach: (dist, scan order) asc; flee: desc */
            if (appr == -1) key = -key;
            for (p = n; p > 0 && keys[p - 1] > key; p--) { keys[p] = keys[p - 1]; bits[p] = bits[p - 1]; }
            keys[p] = key; bits[p] = bit; n++;
        }
        for (k = 0; k < n; k++) {
            bit = bits[k];
            if (!NH_LAZY_EVAL(bit)) continue;
            if (trackmask & (1U << bit)) { nh_lazy_reason = 3; goto complete; }
            if ((cinfo[bit] & ALLOW_MDISP) && !(cinfo[bit] & ALLOW_M)) { nh_lazy_reason = 4; goto complete; }
            *nix = c.x - 1 + bit / 3; *niy = c.y - 1 + bit % 3; *info_out = cinfo[bit];
            return 1;
        }
    } else {
        unsigned int rem = cand;
        while (rem) {
            int r = rn2(__builtin_popcount(rem));
            unsigned int m = rem;
            while (r--) m &= m - 1;
            bit = __builtin_ctz(m); rem &= ~(1U << bit);
            if (!NH_LAZY_EVAL(bit)) continue;
            if ((cinfo[bit] & ALLOW_MDISP) && !(cinfo[bit] & ALLOW_M)) { nh_lazy_reason = 4; goto complete; }
            *nix = c.x - 1 + bit / 3; *niy = c.y - 1 + bit % 3; *info_out = cinfo[bit];
            return 1;
        }
    }
    if (c.wantpool && !nh_cell_pool(c.origin, c.x, c.y)) { c.wantpool = FALSE; goto again; }
    return 0;
 complete: /* finish the remaining cells and emit mfndpos's list in scan order */
    cnt = 0;
    for (bit = 0; bit < 9; bit++) {
        if (!(cand & (1U << bit))) continue;
        if (NH_LAZY_EVAL(bit)) { poss[cnt].x = c.x - 1 + bit / 3; poss[cnt].y = c.y - 1 + bit % 3; info[cnt] = cinfo[bit]; cnt++; }
    }
    if (!cnt && c.wantpool && !nh_cell_pool(c.origin, c.x, c.y)) { c.wantpool = FALSE; goto again; }
    *cnt_out = cnt;
    return 2;
#undef NH_LAZY_EVAL
}

int
mfndpos(struct monst *mon, coord *poss, long *info, long flag)
{'''
rep('src/mon.c',"\nint\nmfndpos(struct monst *mon, coord *poss, long *info, long flag)\n{",lazy)
rep('include/mfndpos.h',"#define ALLOW_MDISP 0x00001000L","extern int nh_lazy_select(struct monst *, long, int *, int, int, int, int, xchar *, xchar *, long *, coord *, long *, int *);\nextern __thread int nh_lazy_reason;\n#define ALLOW_MDISP 0x00001000L")
mm=dst/'src/monmove.c'; s=mm.read_text()
start="    {\n        register int i, j, nx, ny, nearer;\n        unsigned int trackmask;\n        int jcnt, cnt;\n        int ndist, nidist;\n        register coord *mtrk;\n        coord poss[9];\n\n        cnt = mfndpos(mtmp, poss, info, flag);"
end=" nxti:\n            ;\n        }\n    }\n"
a=s.index(start); b=s.index(end,a)+len(end); block=s[a:b]; assert s.count(start)==1
body=block[len("    {\n"):-len("    }\n")]
body=body.replace("        coord poss[9];\n","").replace("        cnt = mfndpos(mtmp, poss, info, flag);\n","")
body=body.replace("        int jcnt, cnt;\n","        int jcnt;\n        xchar chcnt;\n")
for old,new in [('appr','(*appr)'),('nix','(*nix)'),('niy','(*niy)'),('chi','(*chi)'),('mmoved','(*mmoved)'),('avoid','(*avoid)'),('better_with_displacing','(*better)'),('ptr','mtmp->data')]:
    body=re.sub(r'\b'+old+r'\b',new,body)
full='''/* The original selection loop over a complete neighbour list (scan order), kept verbatim. */
static void
nh_select_loop(struct monst *mtmp, int *appr, int gx, int gy, int omx, int omy,
               xchar *nix, xchar *niy, int *chi, long *info, coord *poss, int cnt,
               schar *mmoved, boolean *avoid, boolean *better)
{
'''+body.rstrip('\n')+'''
}

static int nh_lazy_enabled = -1;
#ifdef NH_LAZY_VERIFY
#include "isaac64.h"
extern isaac64_ctx *nle_rng_state(int);
static unsigned long nh_lazy_stat[8];
__attribute__((destructor)) static void nh_lazy_dump(void)
{ fprintf(stderr, "LAZY_STATS chose=%lu none=%lu listdone=%lu fullpath=%lu reasons unicorn=%lu hero=%lu tracked=%lu mdisp=%lu\\n",
    nh_lazy_stat[1], nh_lazy_stat[0], nh_lazy_stat[2], nh_lazy_stat[3], nh_lazy_stat[4], nh_lazy_stat[5], nh_lazy_stat[6], nh_lazy_stat[7]); }
static void
nh_lazy_verify(struct monst *mtmp, long flag, int appr0, int gx, int gy, int omx, int omy, xchar nix0, xchar niy0,
               int lazy, int lappr, xchar lnix, xchar lniy, long linfo, coord *lposs, long *linfoarr, int lcnt, boolean avoid0, boolean better0)
{
    isaac64_ctx saved;
    int sappr = appr0, schi = -1, cnt, i, ok;
    xchar snix = nix0, sniy = niy0;
    long sinfo[9];
    coord sposs[9];
    schar smoved = 0;
    boolean savoid = avoid0, sbetter = better0;
    const char *what = NULL;
    if (lazy == -1) { nh_lazy_stat[3]++; nh_lazy_stat[3 + nh_lazy_reason]++; return; }
    nh_lazy_stat[lazy]++;
    if (lazy == 2) nh_lazy_stat[3 + nh_lazy_reason]++;
    saved = *nle_rng_state(0);
    cnt = mfndpos(mtmp, sposs, sinfo, flag);
    if (lazy == 2) {
        if (cnt != lcnt) what = "list count";
        else for (i = 0; i < cnt; i++) if (sposs[i].x != lposs[i].x || sposs[i].y != lposs[i].y || sinfo[i] != linfoarr[i]) { what = "list entry"; break; }
    } else {
        nh_select_loop(mtmp, &sappr, gx, gy, omx, omy, &snix, &sniy, &schi, sinfo, sposs, cnt, &smoved, &savoid, &sbetter);
        if (sappr != lappr) what = "appr";
        else if (lazy == 0) { if (smoved) what = "lazy none, full moved"; }
        else if (lappr != 0) { if (!smoved || snix != lnix || sniy != lniy || sinfo[schi] != linfo) what = "approach choice"; }
        else {
            ok = 0;
            for (i = 0; i < cnt; i++) {
                if (sposs[i].x != lnix || sposs[i].y != lniy) continue;
                if (savoid && (sinfo[i] & NOTONL)) break;
                if ((sinfo[i] & ALLOW_MDISP) && !(sinfo[i] & ALLOW_M) && !sbetter) break;
                ok = (sinfo[i] == linfo); break;
            }
            if (!ok) what = "wander choice";
        }
    }
    *nle_rng_state(0) = saved;
    if (what) fprintf(stderr, "LAZY_MISMATCH %s turn=%ld mon=%d appr=%d at %d,%d lazy=%d,%d full=%d,%d\\n", what, moves,
                      monsndx(mtmp->data), lappr, omx, omy, lnix, lniy, snix, sniy);
}
#endif

'''
newblock='''    {
        int lazy = -1, lappr = appr, cnt = 0;
        xchar lnix = nix, lniy = niy;
        long linfo = 0;
        coord poss[9];
        if (nh_lazy_enabled < 0) nh_lazy_enabled = getenv("NH_LAZY") ? atoi(getenv("NH_LAZY")) : 1;
        if (nh_lazy_enabled)
            lazy = nh_lazy_select(mtmp, flag, &lappr, gx, gy, omx, omy, &lnix, &lniy, &linfo, poss, info, &cnt);
#ifdef NH_LAZY_VERIFY
        nh_lazy_verify(mtmp, flag, appr, gx, gy, omx, omy, nix, niy, lazy, lappr, lnix, lniy, linfo, poss, info, cnt, avoid, better_with_displacing);
#endif
        if (lazy == 1) {
            appr = lappr; nix = lnix; niy = lniy; info[0] = linfo; chi = 0; mmoved = 1;
        } else if (lazy == 0) {
            appr = lappr;
        } else {
            if (lazy == -1) cnt = mfndpos(mtmp, poss, info, flag);
            else appr = lappr;
            nh_select_loop(mtmp, &appr, gx, gy, omx, omy, &nix, &niy, &chi, info, poss, cnt,
                           &mmoved, &avoid, &better_with_displacing);
        }
    }
'''
s=s[:a]+newblock+s[b:]
hdr="int\nm_move(mtmp, after)\n"; assert s.count(hdr)==1; s=s.replace(hdr,full+hdr)
reg="register int after;\n{\n    register int appr;\n"; assert s.count(reg)==1; s=s.replace(reg,"register int after;\n{\n    int appr;\n")
mm.write_text(s); print('lz2 generated')
