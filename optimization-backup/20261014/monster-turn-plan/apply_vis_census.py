"""CG-build census (inert elsewhere): classify every EXECUTED vision_recalc by which input group changed since the previous executed
recalc on the same env: control 2 / level epoch (opacity, typ, lit, seenv writers) / hero tuple / lights only. A large light-only share
would justify reusing the previous could-see array (skipping view_from) when only light sources moved."""
from pathlib import Path
src = Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rep(p, old, new, count=1):
    t = (src / p).read_text()
    if old not in t or new in t: print('  already:', p, old[:50].strip()); return
    assert t.count(old) == count, (p, t.count(old), old[:90]); (src / p).write_text(t.replace(old, new))

rep('src/vision.c', """        nh_vis_last_valid = (control != 2);
        nh_vis_last_epoch = nh_vis_epoch;
        nh_vis_last_fp = fp;
    }
""", """#ifdef NH_MT2_CG
        { /* census of executed recalcs by changed input group (per env slot) */
            static unsigned long long cl_epoch[4096], cl_hero[4096], cl_light[4096]; static char cl_valid[4096];
            unsigned slot = ((unsigned long) nh_cur >> 6) & 4095;
            unsigned long long hh = 1469598103934665603ULL, lh;
            extern unsigned long long nh_vis_light_hash(unsigned long long);
#define NHVC(v) (hh = (hh ^ (unsigned long long) (v)) * 1099511628211ULL)
            NHVC(u.ux); NHVC(u.uy); NHVC(!!Blind); NHVC(!!Underwater); NHVC(!!u.uswallow); NHVC(u.utrap); NHVC(u.utraptype);
            NHVC(u.xray_range); NHVC(u.nv_range); NHVC(Is_rogue_level(&u.uz)); NHVC(Is_waterlevel(&u.uz));
#undef NHVC
            lh = nh_vis_light_hash(1469598103934665603ULL);
            if (!cl_valid[slot]) nh_vis_c[7]++;
            else if (control == 2) nh_vis_c[7]++;
            else if (cl_epoch[slot] != nh_vis_epoch) nh_vis_c[6]++;
            else if (cl_hero[slot] != hh) nh_vis_c[5]++;
            else if (cl_light[slot] != lh) nh_vis_c[4]++;
            else nh_vis_c[7]++; /* xray or other: fingerprint equal but not skipped */
            cl_epoch[slot] = nh_vis_epoch; cl_hero[slot] = hh; cl_light[slot] = lh; cl_valid[slot] = 1;
        }
#endif
        nh_vis_last_valid = (control != 2);
        nh_vis_last_epoch = nh_vis_epoch;
        nh_vis_last_fp = fp;
    }
""")
rep('src/nle.c', """nh_vis_comp_viol[0], nh_vis_comp_viol[1], nh_vis_comp_viol[2], nh_vis_comp_viol[3], nh_vis_comp_viol[4], nh_vis_comp_viol[5]);""",
    """nh_vis_comp_viol[0], nh_vis_comp_viol[1], nh_vis_comp_viol[2], nh_vis_comp_viol[3], nh_vis_comp_viol[4], nh_vis_comp_viol[5]);
      fprintf(f, "vision_executed_by_cause lights_only %llu hero %llu epoch %llu other %llu\\n", nh_vis_c[4], nh_vis_c[5], nh_vis_c[6], nh_vis_c[7]); }
    {""")
print('vision census applied (CG only)')
