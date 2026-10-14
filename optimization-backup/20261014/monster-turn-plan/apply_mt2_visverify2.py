"""CG-only: per-component violation counts for the vision skip verify (hero tuple, viz_clear, typ, lit, seenv, lights)."""
from pathlib import Path
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rep(p, old, new, count=1):
    t=(src/p).read_text(); assert t.count(old)==count, (p, t.count(old), old[:80]); (src/p).write_text(t.replace(old,new))
rep('src/vision.c', """unsigned long long nh_vis_c[8];
static unsigned long long nh_vis_full_last[4096];""", """unsigned long long nh_vis_c[8], nh_vis_comp_viol[8];
static unsigned long long nh_vis_full_last[4096], nh_vis_comp_last[4096][6];""")
rep('src/vision.c', """    unsigned long long h = 1469598103934665603ULL; int x, y; unsigned slot = ((unsigned long) nh_cur >> 6) & 4095;
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
    nh_vis_full_last[slot] = h;""", """    unsigned long long h = 1469598103934665603ULL, c[6]; int x, y, k; unsigned slot = ((unsigned long) nh_cur >> 6) & 4095;
    extern unsigned long long nh_vis_light_hash(unsigned long long);
#define HM(v) (h = (h ^ (unsigned long long) (v)) * 1099511628211ULL)
    HM(u.ux); HM(u.uy); HM(!!Blind); HM(!!Underwater); HM(!!u.uswallow); HM(u.utrap); HM(u.utraptype); HM(u.xray_range); HM(u.nv_range);
    HM(Is_rogue_level(&u.uz)); HM(Is_waterlevel(&u.uz)); c[0] = h;
    h = 1; for (x = 0; x < COLNO; x++) for (y = 0; y < ROWNO; y++) HM(viz_clear[y][x]); c[1] = h;
    h = 1; for (x = 0; x < COLNO; x++) for (y = 0; y < ROWNO; y++) HM(NH_TILE(x, y).typ); c[2] = h;
    h = 1; for (x = 0; x < COLNO; x++) for (y = 0; y < ROWNO; y++) HM(NH_TILE(x, y).lit); c[3] = h;
    h = 1; for (x = 0; x < COLNO; x++) for (y = 0; y < ROWNO; y++) HM(NH_TILE(x, y).seenv); c[4] = h;
    c[5] = nh_vis_light_hash(1469598103934665603ULL);
    h = c[0] ^ c[1] * 3 ^ c[2] * 5 ^ c[3] * 7 ^ c[4] * 11 ^ c[5] * 13;
#undef HM
    nh_vis_c[0]++; nh_vis_c[1] += same;
    if (same && nh_vis_full_last[slot] != h) { nh_vis_c[2]++; for (k = 0; k < 6; k++) if (nh_vis_comp_last[slot][k] != c[k]) nh_vis_comp_viol[k]++; }
    if (!same && nh_vis_full_last[slot] == h) nh_vis_c[3]++;
    nh_vis_full_last[slot] = h; for (k = 0; k < 6; k++) nh_vis_comp_last[slot][k] = c[k];""")
rep('src/nle.c', '    { extern unsigned long long nh_vis_c[8]; fprintf(f, "vision_recalcs %llu skipped %llu VIOLATIONS %llu missed %llu\\n", nh_vis_c[0], nh_vis_c[1], nh_vis_c[2], nh_vis_c[3]); }\n',
    '    { extern unsigned long long nh_vis_c[8], nh_vis_comp_viol[8]; fprintf(f, "vision_recalcs %llu skipped %llu VIOLATIONS %llu missed %llu viol_hero %llu viol_vizclear %llu viol_typ %llu viol_lit %llu viol_seenv %llu viol_lights %llu\\n", nh_vis_c[0], nh_vis_c[1], nh_vis_c[2], nh_vis_c[3], nh_vis_comp_viol[0], nh_vis_comp_viol[1], nh_vis_comp_viol[2], nh_vis_comp_viol[3], nh_vis_comp_viol[4], nh_vis_comp_viol[5]); }\n')
print('per-component verify applied')
