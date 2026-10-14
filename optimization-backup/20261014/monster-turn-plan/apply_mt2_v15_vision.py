"""v1.5: exact skip of a flag-triggered vision_recalc whose inputs equal the previous full recalc's.
Inputs of vision_recalc(): viz_clear (written only by fill_point/dig_point/vision_reset), cell typ (nh_move_typ_set), cell lit (read.c set_lit,
dig.c, vault.c), seenv reductions (read.c forget, dig.c, detect.c), hero tuple, light sources (identity/type/range/owner position). Every
writer bumps a per-env epoch; the hero tuple and light sources are folded into a fingerprint at the call. seenv/waslit are only |=/cleared by a
recalc, so a repeated recalc with equal inputs leaves them unchanged (newsym fires only on change). The two unconditional tail effects
(newsym(hero), recalc_mapseen) are kept on the skip path. NH_MT2_CG builds verify every skip decision against a full hash of the inputs."""
from pathlib import Path
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rd(p): return (src/p).read_text()
def wr(p,t): (src/p).write_text(t)
def rep(p, old, new, count=1):
    t=rd(p); assert t.count(old)==count, (p, t.count(old), old[:80]); wr(p, t.replace(old,new))
# per-env state
rep('include/nh_ctx_gen.h', "    int g_nh_mt2_hero_valid, g_nh_mt2_hero_bad; /* monster-turn fast path: cached hero-state word (0 = stale) */",
"""    int g_nh_mt2_hero_valid, g_nh_mt2_hero_bad; /* monster-turn fast path: cached hero-state word (0 = stale) */
    unsigned g_nh_vis_epoch, g_nh_vis_last_epoch; int g_nh_vis_last_valid; unsigned long long g_nh_vis_last_fp; /* vision_recalc() skip state */""")
rep('include/nh_ctx_gen.h', "#define nh_mt2_hero_valid (nh_cur->g_nh_mt2_hero_valid)",
"""#define nh_mt2_hero_valid (nh_cur->g_nh_mt2_hero_valid)
#define nh_vis_epoch (nh_cur->g_nh_vis_epoch)
#define nh_vis_last_epoch (nh_cur->g_nh_vis_last_epoch)
#define nh_vis_last_valid (nh_cur->g_nh_vis_last_valid)
#define nh_vis_last_fp (nh_cur->g_nh_vis_last_fp)""")
# epoch bumps: typ
rep('include/hack.h', "    nh_move_set_col_bit(&level.move_columns[x + 1].door, y, typ == DOOR);\n}",
    "    nh_move_set_col_bit(&level.move_columns[x + 1].door, y, typ == DOOR);\n    nh_vis_epoch++; /* vision input */\n}")
# epoch bumps: opacity (the only three writers of viz_clear)
v=rd('src/vision.c')
for fn in ("fill_point(row, col)", "dig_point(row, col)"):
    i=v.index(fn); j=v.index("{", i); v=v[:j+1]+"\n    nh_vis_epoch++; /* vision input: opacity */"+v[j+1:]
i=v.index("vision_reset()\n{\n    nh_typ_sync();"); v=v.replace("vision_reset()\n{\n    nh_typ_sync();", "vision_reset()\n{\n    nh_vis_epoch++; /* vision input: whole level */\n    nh_vis_last_valid = 0;\n    nh_typ_sync();",1)
# the skip itself (after the flag reset and the init checks; before the census block so the CG build can verify)
old="""    vision_full_recalc = 0; /* reset flag */
    if (in_mklev || !iflags.vision_inited)
        return;
"""
new="""    vision_full_recalc = 0; /* reset flag */
    if (in_mklev || !iflags.vision_inited)
        return;
    {
        unsigned long long fp = nh_vis_fingerprint();
        int same = (control != 2 && nh_vis_last_valid && nh_vis_last_epoch == nh_vis_epoch && nh_vis_last_fp == fp);
#ifdef NH_MT2_CG
        nh_vis_verify(same);
#endif
        if (same) {
            /* identical inputs to the previous full recalc: could_see/in_sight and every per-cell update would repeat exactly
               (seenv/waslit are already at their fixed point), so only the two unconditional tail effects remain */
            if (!program_state.panicking)
                newsym(u.ux, u.uy);
            recalc_mapseen();
            return;
        }
        nh_vis_last_valid = (control != 2);
        nh_vis_last_epoch = nh_vis_epoch;
        nh_vis_last_fp = fp;
    }
"""
assert v.count(old)==1; v=v.replace(old,new)
# fingerprint + verify helpers, placed before vision_recalc
anchor="#ifdef NH_MT2_CG\nunsigned long long nh_vis_c[8];\n#endif\nvoid\nvision_recalc(control)"
assert v.count(anchor)==1
helpers='''/* hero-side and light-source inputs of vision_recalc(), folded into one word (the level-side inputs are tracked by nh_vis_epoch) */
static unsigned long long
nh_vis_fingerprint(void)
{
    unsigned long long h = 1469598103934665603ULL;
    extern unsigned long long nh_vis_light_hash(unsigned long long);
#define NHVF(v) (h = (h ^ (unsigned long long) (v)) * 1099511628211ULL)
    NHVF(u.ux); NHVF(u.uy); NHVF(!!Blind); NHVF(!!Underwater); NHVF(!!u.uswallow); NHVF(u.utrap); NHVF(u.utraptype);
    NHVF(u.xray_range); NHVF(u.nv_range); NHVF(Is_rogue_level(&u.uz)); NHVF(Is_waterlevel(&u.uz));
#undef NHVF
    return nh_vis_light_hash(h);
}
#ifdef NH_MT2_CG
unsigned long long nh_vis_c[8];
static unsigned long long nh_vis_full_last[4096];
/* verify: the epoch/fingerprint decision must agree with a full hash of every input plane */
static void
nh_vis_verify(int same)
{
    unsigned long long h = 1469598103934665603ULL; int x, y; unsigned slot = ((unsigned long) nh_cur >> 6) & 4095;
    extern unsigned long long nh_vis_light_hash(unsigned long long);
#define HM(v) (h = (h ^ (unsigned long long) (v)) * 1099511628211ULL)
    HM(u.ux); HM(u.uy); HM(!!Blind); HM(!!Underwater); HM(!!u.uswallow); HM(u.utrap); HM(u.utraptype); HM(u.xray_range); HM(u.nv_range);
    HM(Is_rogue_level(&u.uz)); HM(Is_waterlevel(&u.uz));
    for (x = 0; x < COLNO; x++) for (y = 0; y < ROWNO; y++) { HM(viz_clear[y][x]); HM(NH_TILE(x, y).typ); HM(NH_TILE(x, y).lit); HM(NH_TILE(x, y).seenv); }
    h = nh_vis_light_hash(h);
#undef HM
    nh_vis_c[0]++; nh_vis_c[1] += same;
    if (same && nh_vis_full_last[slot] != h) nh_vis_c[2]++; /* VIOLATION: skipped although an input changed */
    if (!same && nh_vis_full_last[slot] == h) nh_vis_c[3]++;  /* missed skip (conservative, harmless) */
    nh_vis_full_last[slot] = h;
}
#endif
void
vision_recalc(control)'''
v=v.replace(anchor, helpers)
# drop the earlier census block (superseded by nh_vis_verify)
i=v.index("#ifdef NH_MT2_CG\n    { /* census: how many recalcs have inputs identical"); j=v.index("#endif\n", i)+len("#endif\n")
v=v[:i]+v[j:]
wr('src/vision.c', v)
# light hash available in all builds (was CG-only); include identity
l=rd('src/light.c')
l=l.replace("#ifdef NH_MT2_CG\n/* census helper: mix every light source's type, range and owner position into h */", "/* vision skip: mix every light source's identity, type, range and owner position into h */")
l=l.replace("""        h = (h ^ (unsigned long long) lx) * 1099511628211ULL; h = (h ^ (unsigned long long) ly) * 1099511628211ULL;
    }
    return h;
}
#endif
""", """        h = (h ^ (unsigned long long) lx) * 1099511628211ULL; h = (h ^ (unsigned long long) ly) * 1099511628211ULL;
        h = (h ^ (unsigned long long) (unsigned long) ls) * 1099511628211ULL;
    }
    return h;
}
""")
assert "#endif\n\n/* return true if there exist any light sources */" not in l
wr('src/light.c', l)
# lit writers and seenv reducers bump the epoch
rep('src/read.c', "    if (val) {\n        NH_TILE(x, y).lit = 1;", "    nh_vis_epoch++; /* vision input: lit */\n    if (val) {\n        NH_TILE(x, y).lit = 1;")
d=rd('src/dig.c'); assert d.count("    lev->seenv = 0;")==1 and d.count("        lev->lit = (rockit ? FALSE : TRUE);")==1
d=d.replace("    lev->seenv = 0;", "    lev->seenv = 0;\n    nh_vis_epoch++; /* vision input: seenv/lit */"); wr('src/dig.c', d)
rep('src/vault.c', "                lev->lit = lev->waslit = 0;", "                lev->lit = lev->waslit = 0;\n                nh_vis_epoch++; /* vision input: lit */")
rep('src/read.c', "                NH_TILE(zx, zy).seenv = 0;", "                NH_TILE(zx, zy).seenv = 0;\n                nh_vis_epoch++; /* vision input: seenv reset */")
rep('src/detect.c', "        NH_TILE(x, y).seenv = seenv;", "        NH_TILE(x, y).seenv = seenv;\n        nh_vis_epoch++; /* vision input: seenv restored */")
# stats dump: replace the old census line
n=rd('src/nle.c')
old='    { extern unsigned long long nh_vis_c[8]; fprintf(f, "vision_recalcs %llu control0 %llu control1 %llu control2 %llu redundant %llu redundant_c0 %llu with_light %llu\\n", nh_vis_c[0], nh_vis_c[1], nh_vis_c[2], nh_vis_c[3], nh_vis_c[5], nh_vis_c[6], nh_vis_c[7]); }\n'
assert n.count(old)==1
n=n.replace(old, '    { extern unsigned long long nh_vis_c[8]; fprintf(f, "vision_recalcs %llu skipped %llu VIOLATIONS %llu missed %llu\\n", nh_vis_c[0], nh_vis_c[1], nh_vis_c[2], nh_vis_c[3]); }\n')
wr('src/nle.c', n)
print('v1.5 applied')
