"""Census build (measurement only, single-worker harness): rdtsc per dochug call bucketed by monster kind x distance x hero-visibility, with the
mfndpos and object-search cycles inside each move; per-step cycles and game turns. Dumped by a library destructor to $NH_CENSUS."""
import sys, shutil
from pathlib import Path
R=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014'); src=R/'engines/census/source'
if not src.exists(): shutil.copytree(Path('/puffertank/experiments/nethack-engine-lines-20261014/engines/selE/source'), src)
def rep(path, old, new, count=1):
    t=path.read_text(); assert t.count(old)==count, (path, t.count(old), old[:70]); path.write_text(t.replace(old,new))
mon=src/'src/mon.c'
rep(mon, """movemon()
{""", """unsigned long long nh_census[9][4][2][4]; /* kind, dist bucket, visible, {calls, dochug cycles, mfndpos cycles, object-search cycles} */
unsigned long long nh_census_turns, nh_census_mfnd_acc, nh_census_obj_acc;
static int nh_census_kind(struct monst *m) {
    if (m->mtame) return 3;
    if (m->isshk || m->ispriest || m->isgd) return 4;
    if (is_covetous(m->data)) return 5;
    if (m->wormno) return 6;
    if (tunnels(m->data) || passes_walls(m->data)) return 7;
    if (m->mconf || m->mstun) return 8;
    if (m->mpeaceful) return 2;
    if (m->mflee) return 1;
    return 0;
}
movemon()
{
    nh_census_turns++;""")
rep(mon, """        if (dochugw(mtmp)) /* otherwise just move the monster */
            continue;""",
"""        {   /* census: classify before the move (the monster may die or move), time the whole move */
            int ck = nh_census_kind(mtmp); int dm = distmin(mtmp->mx, mtmp->my, u.ux, u.uy);
            int cd = dm <= 1 ? 0 : dm <= 5 ? 1 : dm <= 10 ? 2 : 3; int cv = canseemon(mtmp) ? 1 : 0;
            nh_census_mfnd_acc = 0; nh_census_obj_acc = 0;
            unsigned long long ct0 = __builtin_ia32_rdtsc();
            int crd = dochugw(mtmp); /* otherwise just move the monster */
            unsigned long long cdt = __builtin_ia32_rdtsc() - ct0;
            nh_census[ck][cd][cv][0]++; nh_census[ck][cd][cv][1] += cdt; nh_census[ck][cd][cv][2] += nh_census_mfnd_acc; nh_census[ck][cd][cv][3] += nh_census_obj_acc;
            if (crd) continue;
        }""")
rep(mon, """static int mfndpos_masked(mon, poss, info, flag) struct monst *mon;""", """static int mfndpos_masked_impl(mon, poss, info, flag) struct monst *mon;""")
rep(mon, """
int
mfndpos(struct monst *mon, coord *poss, long *info, long flag)
{""", """
static int mfndpos_masked(struct monst *mon, coord *poss, long *info, long flag) {
    unsigned long long t0 = __builtin_ia32_rdtsc(); int r = mfndpos_masked_impl(mon, poss, info, flag);
    nh_census_mfnd_acc += __builtin_ia32_rdtsc() - t0; return r;
}
int
mfndpos(struct monst *mon, coord *poss, long *info, long flag)
{""")
mm=src/'src/monmove.c'
rep(mm, """    {
        register int minr = SQSRCHRADIUS; /* not too far away */""",
"""    {
        extern unsigned long long nh_census_obj_acc; unsigned long long cs_t0 = __builtin_ia32_rdtsc();
        register int minr = SQSRCHRADIUS; /* not too far away */""")
rep(mm, """        if (minr < SQSRCHRADIUS && appr == -1) {""",
"""        nh_census_obj_acc += __builtin_ia32_rdtsc() - cs_t0;
        if (minr < SQSRCHRADIUS && appr == -1) {""")
nle=src/'src/nle.c'
rep(nle, """nle_ctx_t *
nle_step(nle_ctx_t *nle, nle_obs *obs)
{""", """static nle_ctx_t *nle_step_impl(nle_ctx_t *nle, nle_obs *obs);
unsigned long long nh_census_steps, nh_census_step_cycles;
extern unsigned long long nh_census[9][4][2][4], nh_census_turns;
nle_ctx_t *
nle_step(nle_ctx_t *nle, nle_obs *obs)
{
    unsigned long long t0 = __builtin_ia32_rdtsc(); nle_ctx_t *r = nle_step_impl(nle, obs);
    nh_census_steps++; nh_census_step_cycles += __builtin_ia32_rdtsc() - t0; return r;
}
__attribute__((destructor)) static void nh_census_dump(void) {
    const char *p = getenv("NH_CENSUS"); if (!p) return; FILE *f = fopen(p, "w"); if (!f) return;
    static const char *kinds[9] = {"hostile", "fleeing", "peaceful", "pet", "shk/priest/guard", "covetous", "worm", "tunnel/passwall", "conf/stun"};
    fprintf(f, "steps %llu step_cycles %llu turns %llu\\n", nh_census_steps, nh_census_step_cycles, nh_census_turns);
    fprintf(f, "kind dist vis calls dochug_cycles mfndpos_cycles objsearch_cycles\\n");
    for (int k = 0; k < 9; k++) for (int d = 0; d < 4; d++) for (int v = 0; v < 2; v++)
        if (nh_census[k][d][v][0]) fprintf(f, "%s %d %d %llu %llu %llu %llu\\n", kinds[k], d, v, nh_census[k][d][v][0], nh_census[k][d][v][1], nh_census[k][d][v][2], nh_census[k][d][v][3]);
    fclose(f);
}
static nle_ctx_t *
nle_step_impl(nle_ctx_t *nle, nle_obs *obs)
{""")
print('census instrumentation applied to', src)
