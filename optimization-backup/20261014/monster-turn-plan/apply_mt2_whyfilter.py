"""CG-only: NH_MT2_CG_WHY=<k> restricts the inverted (old-path) collection to moves whose first failing eligibility clause is k."""
from pathlib import Path
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rep(p, old, new, count=1):
    t=(src/p).read_text(); assert t.count(old)==count, (p, t.count(old), old[:80]); (src/p).write_text(t.replace(old,new))
rep('src/monmove.c', "#define MT2WHY(k) (nh_mt2_why[k]++, 0)", "int nh_mt2_last_why;\n#define MT2WHY(k) (nh_mt2_why[k]++, nh_mt2_last_why = (k), 0)")
rep('src/mon.c', """            static int inv = -1; if (inv < 0) { const char *e = getenv("NH_MT2_CG_INVERT"); inv = e && *e == '1'; }
            nh_mt2_all_moves++; nh_mt2_elig_moves += elig;
            col = inv ? !elig : elig; /* NH_MT2_CG_INVERT=1 collects the moves that take the OLD path */""",
"""            static int inv = -1, whyf = -1; extern int nh_mt2_last_why;
            if (inv < 0) { const char *e = getenv("NH_MT2_CG_INVERT"); inv = e && *e == '1'; e = getenv("NH_MT2_CG_WHY"); whyf = e ? atoi(e) : -1; }
            nh_mt2_all_moves++; nh_mt2_elig_moves += elig;
            col = inv ? (!elig && (whyf < 0 || nh_mt2_last_why == whyf)) : elig; /* NH_MT2_CG_INVERT=1 collects OLD-path moves, NH_MT2_CG_WHY narrows to one clause */
            if (col && inv) nh_mt2_c[63]++;""")
print('why filter applied')
