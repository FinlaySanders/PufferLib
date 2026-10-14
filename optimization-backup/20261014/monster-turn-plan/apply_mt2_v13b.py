"""v1.3b: the cached hero-state word must be per environment (the corpus replay and the trainer run many games on parallel threads)."""
from pathlib import Path
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rd(p): return (src/p).read_text()
def wr(p,t): (src/p).write_text(t)
def rep(p, old, new, count=1):
    t=rd(p); assert t.count(old)==count, (p, t.count(old), old[:80]); wr(p, t.replace(old,new))
# per-env storage: nh_ctx_gen.h struct field + accessor macro (same pattern as the other migrated globals)
g=rd('include/nh_ctx_gen.h')
assert g.count("    int g_nh_display_sense; /* global: nh_display_sense */")==1 and g.count("#define nh_display_sense (nh_cur->g_nh_display_sense)")==1
g=g.replace("    int g_nh_display_sense; /* global: nh_display_sense */", "    int g_nh_display_sense; /* global: nh_display_sense */\n    int g_nh_mt2_hero_valid, g_nh_mt2_hero_bad; /* monster-turn fast path: cached hero-state word (0 = stale) */")
g=g.replace("#define nh_display_sense (nh_cur->g_nh_display_sense)", "#define nh_display_sense (nh_cur->g_nh_display_sense)\n#define nh_mt2_hero_valid (nh_cur->g_nh_mt2_hero_valid)\n#define nh_mt2_hero_bad (nh_cur->g_nh_mt2_hero_bad)")
wr('include/nh_ctx_gen.h', g)
rep('src/monmove.c', "extern int nh_mt2_fast, nh_mt2_hero_stale;\n", "extern int nh_mt2_fast;\n")
rep('src/monmove.c', """int nh_mt2_hero_stale = 1, nh_mt2_hero_bad;
static int
mt2_hero_bad(void)
{
    if (nh_mt2_hero_stale) {
        nh_mt2_hero_bad = (u.uswallow || Underwater || Invis || Displaced || Hallucination || Conflict || Upolyd || Reflecting
                           || u.uundetected || U_AP_TYPE != M_AP_NOTHING);
        nh_mt2_hero_stale = 0;
    }
    return nh_mt2_hero_bad;
}""", """static int
mt2_hero_bad(void)
{
    if (!nh_mt2_hero_valid) {
        nh_mt2_hero_bad = (u.uswallow || Underwater || Invis || Displaced || Hallucination || Conflict || Upolyd || Reflecting
                           || u.uundetected || U_AP_TYPE != M_AP_NOTHING);
        nh_mt2_hero_valid = 1;
    }
    return nh_mt2_hero_bad;
}""")
t=rd('src/monmove.c'); n=t.count("nh_mt2_hero_stale = 1;"); assert n==2, n; wr('src/monmove.c', t.replace("nh_mt2_hero_stale = 1;", "nh_mt2_hero_valid = 0;"))
rep('src/mon.c', "    { extern int nh_mt2_hero_stale; nh_mt2_hero_stale = 1; }\n", "    nh_mt2_hero_valid = 0; /* hero actions since the last pass may have changed the cached hero-state word */\n")
print('v1.3b applied'); import re; print('remaining stale refs:', len(re.findall('nh_mt2_hero_stale', rd('src/monmove.c')+rd('src/mon.c'))))
