"""Eligibility census: for every far (>10) unseen hostile move, count the species/state properties that a v2 fast path would have to support
or fall back on. Adds a flag table dump to the census build."""
from pathlib import Path
src=Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/census/source')
def rep(path, old, new, count=1):
    t=path.read_text(); assert t.count(old)==count, (path, t.count(old), old[:70]); path.write_text(t.replace(old,new))
mon=src/'src/mon.c'
rep(mon, """unsigned long long nh_census_turns, nh_census_mfnd_acc, nh_census_obj_acc;""",
"""unsigned long long nh_census_turns, nh_census_mfnd_acc, nh_census_obj_acc;
unsigned long long nh_elig[24]; /* far-unseen-hostile population: property counts (index = property) */
static void nh_census_props(struct monst *m) {
    struct permonst *p = m->data; int i = 0;
    nh_elig[i++]++;                                           /* 0 total */
    if (likes_objs(p)) nh_elig[i]++; i++;                      /* 1 */
    if (likes_gold(p)) nh_elig[i]++; i++;                      /* 2 */
    if (likes_gems(p)) nh_elig[i]++; i++;                      /* 3 */
    if (likes_magic(p)) nh_elig[i]++; i++;                     /* 4 */
    if (!mindless(p) && !is_animal(p)) nh_elig[i]++; i++;      /* 5 uses_items */
    if (hides_under(p)) nh_elig[i]++; i++;                     /* 6 */
    if (is_flyer(p) || is_floater(p)) nh_elig[i]++; i++;       /* 7 */
    if (is_swimmer(p) || p->mlet == S_EEL) nh_elig[i]++; i++;  /* 8 */
    if (amorphous(p)) nh_elig[i]++; i++;                       /* 9 */
    if (is_giant(p)) nh_elig[i]++; i++;                        /* 10 doorbuster */
    if (nohands(p) || verysmall(p)) nh_elig[i]++; i++;         /* 11 cannot open doors */
    if (m->minvent) nh_elig[i]++; i++;                         /* 12 carries something */
    if (can_track(p)) nh_elig[i]++; i++;                       /* 13 */
    if (is_undead(p) || is_vampshifter(m)) nh_elig[i]++; i++;  /* 14 garlic rule */
    if (is_unicorn(p)) nh_elig[i]++; i++;                      /* 15 */
    if (is_human(p) || p == &mons[PM_MINOTAUR]) nh_elig[i]++; i++; /* 16 scare-monster rule */
    if (p->mlet == S_BAT || p->mlet == S_LIGHT || monsndx(p) == PM_STALKER) nh_elig[i]++; i++; /* 17 random appr */
    if (m->mcansee == 0) nh_elig[i]++; i++;                    /* 18 blinded */
    if (m->msleeping) nh_elig[i]++; i++;                       /* 19 */
    if (!m->mcanmove || m->mfrozen) nh_elig[i]++; i++;         /* 20 immobile */
    if (throws_rocks(p)) nh_elig[i]++; i++;                    /* 21 */
    if (is_mercenary(p)) nh_elig[i]++; i++;                    /* 22 */
    if (m->meating) nh_elig[i]++; i++;                         /* 23 */
}""")
rep(mon, """            nh_census_mfnd_acc = 0; nh_census_obj_acc = 0;""",
"""            nh_census_mfnd_acc = 0; nh_census_obj_acc = 0;
            if (ck == 0 && cd == 3 && cv == 0) nh_census_props(mtmp);""")
nle=src/'src/nle.c'
rep(nle, """    fclose(f);
}
static nle_ctx_t *""",
"""    { extern unsigned long long nh_elig[24]; static const char *props[24] = {"total","likes_objs","likes_gold","likes_gems","likes_magic","uses_items","hides_under","flyer/floater","swimmer/eel","amorphous","giant","nohands/verysmall","carries_items","can_track","undead/vampshifter","unicorn","human/minotaur","bat/light/stalker","blinded","asleep","immobile","throws_rocks","mercenary","eating"};
      fprintf(f, "far_unseen_hostile_props\\n"); for (int i = 0; i < 24; i++) fprintf(f, "%s %llu\\n", props[i], nh_elig[i]); }
    fclose(f);
}
static nle_ctx_t *""")
print('eligibility census added')
