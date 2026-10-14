"""v1.5b: (1) epoch bumps for the persistent direct writers of viz_array outside vision.c (dig.c, hack.c); (2) CG-only no-op oracle:
when the skip logic says 'same', snapshot every state a recalc can touch, run the full recalc anyway, and count any difference."""
from pathlib import Path
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rd(p): return (src/p).read_text()
def wr(p,t): (src/p).write_text(t)
def rep(p, old, new, count=1):
    t=rd(p); assert t.count(old)==count, (p, t.count(old), old[:80]); wr(p, t.replace(old,new))
# (1) direct viz_array writers
rep('src/dig.c', "    viz_array[y][x] = (dist < 3) ? (IN_SIGHT | COULD_SEE) : COULD_SEE;", "    viz_array[y][x] = (dist < 3) ? (IN_SIGHT | COULD_SEE) : COULD_SEE;\n    nh_vis_epoch++; /* vision state written directly */")
rep('src/hack.c', "                        viz_array[ry][rx] |= IN_SIGHT;", "                        viz_array[ry][rx] |= IN_SIGHT;\n                        nh_vis_epoch++; /* vision state written directly */")
# (2) no-op oracle in the CG build: replace the skip path
v=rd('src/vision.c')
old="""#ifdef NH_MT2_CG
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
new="""#ifdef NH_MT2_CG
        nh_vis_verify(same);
        nh_vis_oracle_pending = same; /* run the full recalc anyway and compare at the end */
        if (same) nh_vis_oracle_snapshot();
#else
        if (same) {
            /* identical inputs to the previous full recalc: could_see/in_sight and every per-cell update would repeat exactly
               (seenv/waslit are already at their fixed point), so only the two unconditional tail effects remain */
            if (!program_state.panicking)
                newsym(u.ux, u.uy);
            recalc_mapseen();
            return;
        }
#endif
        nh_vis_last_valid = (control != 2);
        nh_vis_last_epoch = nh_vis_epoch;
        nh_vis_last_fp = fp;
    }
"""
assert v.count(old)==1; v=v.replace(old,new)
# snapshot/compare helpers (CG) before vision_recalc
anchor="void\nvision_recalc(control)"
helpers='''#ifdef NH_MT2_CG
static int nh_vis_oracle_pending;
static struct { char viz[ROWNO][COLNO]; char rmin[ROWNO], rmax[ROWNO]; unsigned char seenv[COLNO][ROWNO], waslit[COLNO][ROWNO]; short glyph[COLNO][ROWNO]; } nh_vis_snap;
static void
nh_vis_oracle_snapshot(void)
{
    int x, y;
    for (y = 0; y < ROWNO; y++) { memcpy(nh_vis_snap.viz[y], viz_array[y], COLNO); nh_vis_snap.rmin[y] = viz_rmin[y]; nh_vis_snap.rmax[y] = viz_rmax[y]; }
    for (x = 0; x < COLNO; x++) for (y = 0; y < ROWNO; y++) { nh_vis_snap.seenv[x][y] = NH_TILE(x, y).seenv; nh_vis_snap.waslit[x][y] = NH_TILE(x, y).waslit; nh_vis_snap.glyph[x][y] = NH_TILE(x, y).glyph; }
}
unsigned long long nh_vis_oracle_viol[6];
static void
nh_vis_oracle_compare(void)
{
    int x, y, d[5] = {0, 0, 0, 0, 0};
    for (y = 0; y < ROWNO; y++) { if (memcmp(nh_vis_snap.viz[y], viz_array[y], COLNO)) d[0] = 1; if (nh_vis_snap.rmin[y] != viz_rmin[y] || nh_vis_snap.rmax[y] != viz_rmax[y]) d[1] = 1; }
    for (x = 0; x < COLNO; x++) for (y = 0; y < ROWNO; y++) { if (nh_vis_snap.seenv[x][y] != NH_TILE(x, y).seenv) d[2] = 1; if (nh_vis_snap.waslit[x][y] != NH_TILE(x, y).waslit) d[3] = 1; if (nh_vis_snap.glyph[x][y] != NH_TILE(x, y).glyph) d[4] = 1; }
    nh_vis_oracle_viol[5]++;
    for (x = 0; x < 5; x++) if (d[x]) nh_vis_oracle_viol[x]++;
    nh_vis_oracle_pending = 0;
}
#endif
'''
assert v.count(anchor)==1; v=v.replace(anchor, helpers+anchor)
# compare at the single exit (after recalc_mapseen at the end of vision_recalc)
k=v.index("skip:\n", v.index("vision_recalc(control)")); e=v.index("    recalc_mapseen();", k); e2=e+len("    recalc_mapseen();")
v=v[:e2]+"\n#ifdef NH_MT2_CG\n    if (nh_vis_oracle_pending)\n        nh_vis_oracle_compare();\n#endif"+v[e2:]
wr('src/vision.c', v)
rep('src/nle.c', 'viol_seenv %llu viol_lights %llu\\n", nh_vis_c[0], nh_vis_c[1], nh_vis_c[2], nh_vis_c[3], nh_vis_comp_viol[0], nh_vis_comp_viol[1], nh_vis_comp_viol[2], nh_vis_comp_viol[3], nh_vis_comp_viol[4], nh_vis_comp_viol[5]); }\n',
    'viol_seenv %llu viol_lights %llu\\n", nh_vis_c[0], nh_vis_c[1], nh_vis_c[2], nh_vis_c[3], nh_vis_comp_viol[0], nh_vis_comp_viol[1], nh_vis_comp_viol[2], nh_vis_comp_viol[3], nh_vis_comp_viol[4], nh_vis_comp_viol[5]);\n      { extern unsigned long long nh_vis_oracle_viol[6]; fprintf(f, "oracle_skips %llu ORACLE_VIOL viz %llu rminmax %llu seenv %llu waslit %llu glyph %llu\\n", nh_vis_oracle_viol[5], nh_vis_oracle_viol[0], nh_vis_oracle_viol[1], nh_vis_oracle_viol[2], nh_vis_oracle_viol[3], nh_vis_oracle_viol[4]); } }\n')
print('v1.5b + oracle applied')
