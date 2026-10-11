import shutil, re
from pathlib import Path
CS=Path('/puffertank/experiments/nethack-compact-state-20261008/engines'); dst=CS/'lz1/source'
if dst.parent.exists(): shutil.rmtree(dst.parent)
shutil.copytree(CS/'lz0/source',dst,symlinks=True)
def rep(path,old,new,count=1):
    p=dst/path; s=p.read_text(); assert s.count(old)==count,(path,s.count(old),old[:70]); p.write_text(s.replace(old,new))
# --- mon.c: lazy selector next to the refactored query
lazy='''
/* Lazy neighbour selection for m_move. 1 = chose (nix/niy/info), 0 = no legal cell, -1 = take the full path
   (needs the legal count, a displacement decision, or the hero/image is adjacent so the mux/muy side effect must follow scan order). */
int
nh_lazy_select(struct monst *mon, long flag, int *appr_io, int gx, int gy, int omx, int omy,
               xchar *nix, xchar *niy, long *info_out)
{
    struct nh_mfnd c;
    int appr = *appr_io, j, k, n, nidist0, bits[9], keys[9];
    unsigned int cand, trackmask = 0;
    long inf;

    if (SPWQ(mon->data, SPW_UNICORN, is_unicorn(mon->data)) && level.lflags.noteleport)
        return -1;
    if (distmin(omx, omy, u.ux, u.uy) <= 1 || distmin(omx, omy, mon->mux, mon->muy) <= 1)
        return -1;
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
    if (appr != 0) {
        n = 0;
        while (cand) {
            int bit = __builtin_ctz(cand), p;
            int nx = c.x - 1 + bit / 3, ny = c.y - 1 + bit % 3;
            int key = dist2(nx, ny, gx, gy) * 16 + bit; /* approach: (dist, scan order) ascending; flee: descending */
            cand &= cand - 1;
            if (appr == -1) key = -key;
            for (p = n; p > 0 && keys[p - 1] > key; p--) { keys[p] = keys[p - 1]; bits[p] = bits[p - 1]; }
            keys[p] = key; bits[p] = bit; n++;
        }
        for (k = 0; k < n; k++) {
            int bit = bits[k], nx = c.x - 1 + bit / 3, ny = c.y - 1 + bit % 3;
            if (!nh_mfnd_cell(&c, nx, ny, &inf)) continue;
            if (trackmask & (1U << bit)) return -1;              /* rn2(4*(cnt-j)) needs cnt */
            if ((inf & ALLOW_MDISP) && !(inf & ALLOW_M)) return -1; /* should_displace needs the full list */
            *nix = nx; *niy = ny; *info_out = inf;
            return 1;
        }
    } else {
        unsigned int rem = cand;
        while (rem) {
            int r = rn2(__builtin_popcount(rem)), bit, nx, ny;
            unsigned int m = rem;
            while (r--) m &= m - 1;
            bit = __builtin_ctz(m); rem &= ~(1U << bit);
            nx = c.x - 1 + bit / 3; ny = c.y - 1 + bit % 3;
            if (!nh_mfnd_cell(&c, nx, ny, &inf)) continue;
            if ((inf & ALLOW_MDISP) && !(inf & ALLOW_M)) return -1;
            *nix = nx; *niy = ny; *info_out = inf;
            return 1;
        }
    }
    if (c.wantpool && !nh_cell_pool(c.origin, c.x, c.y)) { c.wantpool = FALSE; goto again; }
    return 0;
}

int
mfndpos(struct monst *mon, coord *poss, long *info, long flag)
{'''
rep('src/mon.c',"\nint\nmfndpos(struct monst *mon, coord *poss, long *info, long flag)\n{",lazy)
rep('include/mfndpos.h',"#define ALLOW_MDISP 0x00001000L","extern int nh_lazy_select(struct monst *, long, int *, int, int, int, int, xchar *, xchar *, long *);\n#define ALLOW_MDISP 0x00001000L")
# --- monmove.c: factor the original block into nh_select_full, call lazy first
mm=dst/'src/monmove.c'; s=mm.read_text()
start="    {\n        register int i, j, nx, ny, nearer;\n        unsigned int trackmask;\n        int jcnt, cnt;\n        int ndist, nidist;\n        register coord *mtrk;\n        coord poss[9];\n\n        cnt = mfndpos(mtmp, poss, info, flag);"
end=" nxti:\n            ;\n        }\n    }\n"
a=s.index(start); b=s.index(end,a)+len(end); block=s[a:b]; assert s.count(start)==1
body=block[len("    {\n"):-len("    }\n")]  # inner statements
body=body.replace("        coord poss[9];\n","")
for old,new in [('appr','(*appr)'),('nix','(*nix)'),('niy','(*niy)'),('chi','(*chi)'),('mmoved','(*mmoved)'),('avoid','(*avoid)'),('better_with_displacing','(*better)'),('ptr','mtmp->data')]:
    body=re.sub(r'\b'+old+r'\b',new,body)
body=body.replace("        int jcnt, cnt;\n","        int jcnt, cnt;\n        xchar chcnt;\n")
body=body.rstrip('\n')+"\n        *cnt_out = cnt;\n"
full='''/* The original selection (full neighbour list + scan-order loop), kept verbatim as the fallback and the verify reference. */
static void
nh_select_full(struct monst *mtmp, long flag, int *appr, int gx, int gy, int omx, int omy,
               xchar *nix, xchar *niy, int *chi, long *info, coord *poss, int *cnt_out,
               schar *mmoved, boolean *avoid, boolean *better)
{
'''+body+'''}

static int nh_lazy_enabled = -1;
#ifdef NH_LAZY_VERIFY
#include "isaac64.h"
extern isaac64_ctx *nle_rng_state(int);
static unsigned long nh_lazy_stat[3];
__attribute__((destructor)) static void nh_lazy_dump(void)
{ fprintf(stderr, "LAZY_STATS chose=%lu none=%lu fallback=%lu\\n", nh_lazy_stat[1], nh_lazy_stat[0], nh_lazy_stat[2]); }
static void
nh_lazy_verify(struct monst *mtmp, long flag, int appr0, int gx, int gy, int omx, int omy, xchar nix0, xchar niy0,
               int lazy, int lappr, xchar lnix, xchar lniy, long linfo, boolean avoid0, boolean better0)
{
    isaac64_ctx saved;
    int sappr = appr0, schi = -1, cnt, i, ok;
    xchar snix = nix0, sniy = niy0;
    long sinfo[9];
    coord sposs[9];
    schar smoved = 0;
    boolean savoid = avoid0, sbetter = better0;
    const char *what = NULL;
    if (lazy < 0) { nh_lazy_stat[2]++; return; }
    nh_lazy_stat[lazy]++;
    saved = *nle_rng_state(0);
    nh_select_full(mtmp, flag, &sappr, gx, gy, omx, omy, &snix, &sniy, &schi, sinfo, sposs, &cnt, &smoved, &savoid, &sbetter);
    *nle_rng_state(0) = saved;
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
    if (what) fprintf(stderr, "LAZY_MISMATCH %s turn=%ld mon=%d appr=%d at %d,%d lazy=%d,%d full=%d,%d\\n", what, moves,
                      monsndx(mtmp->data), lappr, omx, omy, lnix, lniy, snix, sniy);
}
#endif

'''
newblock='''    {
        int lazy = -1, lappr = appr;
        xchar lnix = nix, lniy = niy;
        long linfo = 0;
        if (nh_lazy_enabled < 0) nh_lazy_enabled = getenv("NH_LAZY") ? atoi(getenv("NH_LAZY")) : 1;
        if (nh_lazy_enabled)
            lazy = nh_lazy_select(mtmp, flag, &lappr, gx, gy, omx, omy, &lnix, &lniy, &linfo);
#ifdef NH_LAZY_VERIFY
        nh_lazy_verify(mtmp, flag, appr, gx, gy, omx, omy, nix, niy, lazy, lappr, lnix, lniy, linfo, avoid, better_with_displacing);
#endif
        if (lazy == 1) {
            appr = lappr; nix = lnix; niy = lniy; info[0] = linfo; chi = 0; mmoved = 1;
        } else if (lazy == 0) {
            appr = lappr;
        } else {
            coord poss[9];
            int cnt;
            nh_select_full(mtmp, flag, &appr, gx, gy, omx, omy, &nix, &niy, &chi, info, poss, &cnt,
                           &mmoved, &avoid, &better_with_displacing);
        }
    }
'''
s=s[:a]+newblock+s[b:]
hdr="int\nm_move(mtmp, after)\n"; assert s.count(hdr)==1; s=s.replace(hdr,full+hdr)
reg="register int after;\n{\n    register int appr;\n"; assert s.count(reg)==1; s=s.replace(reg,"register int after;\n{\n    int appr;\n")
mm.write_text(s); print('lz1 generated; full-path body lines', body.count('\n'))
