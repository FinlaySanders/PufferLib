"""Candidate C: action-mask computation without per-(verb, slot) zero-time scans and without the per-slot WIELD weld rescan.
Bit-exact: the zero-time block set is precomputed once per step as per-verb slot bitmasks; the caller's welded gate already
implies the inner WIELD scan can never fire. usage: apply_C.py <header path> (edited in place)"""
import sys
from pathlib import Path
p=Path(sys.argv[1]); t=p.read_text()
def rep(old,new):
    global t; assert t.count(old)==1, old[:70]; t=t.replace(old,new)
rep("""static int nethack_zt_blocked(const Nethack* env, int verb, int slot) {
    if (!nethack_zt_mask_on() || !env->zt_n || !nethack_zt_world_same(env)) return 0;
    for (int k = 0; k < env->zt_n; k++) if (env->zt_verb[k] == verb && env->zt_slot[k] == slot && env->zt_cnt[k] >= 2) return 1;
    return 0;
}
static int nethack_slot_usable(const Nethack* env, const Verb* verb, int i) {""",
"""// per-verb bitmask of inventory slots blocked by the zero-time memory (bit i = slot i), built once per mask computation
static void nethack_zt_blocked_slots(const Nethack* env, unsigned long long* blk) {
    memset(blk, 0, sizeof(unsigned long long) * NETHACK_NUM_ACTIONS);
    if (!nethack_zt_mask_on() || !env->zt_n || !nethack_zt_world_same(env)) return;
    for (int k = 0; k < env->zt_n; k++) {
        int v = env->zt_verb[k], s = env->zt_slot[k];
        if (env->zt_cnt[k] >= 2 && v >= 0 && v < NETHACK_NUM_ACTIONS && s >= 0 && s < 64) blk[v] |= 1ULL << s;
    }
}
static int nethack_slot_usable(const Nethack* env, const Verb* verb, int i, unsigned long long zt_blk) {""")
rep("""    if (nethack_zt_blocked(env, (int)(verb - NETHACK_VERBS), i)) return 0;""",
    """    if ((zt_blk >> i) & 1ULL) return 0;""")
rep("""    // WIELD while welded (known-cursed wield) refuses for free and the weld
    // never expires; the revealing first attempt on unknown BUC stays legal
    if (verb == &NETHACK_VERBS[NETHACK_ACT_WIELD]) {
        for (int j = 0; j < NETHACK_INV_SLOTS && env->inv_letters[j]; j++)
            if ((env->inv_state[j * NLE_INV_STATE_FIELDS + 5] & 2)
                && env->inv_state[j * NLE_INV_STATE_FIELDS + 0] == 1)
                return 0;
    }
""",
"""    // WIELD while welded (known-cursed wield) refuses for free: the caller skips the whole verb when any
    // slot is welded (same predicate), so no per-slot rescan is needed here
""")
rep("""    for (int a = 0; a < NETHACK_NUM_ACTIONS; a++) {
        const Verb* verb = &NETHACK_VERBS[a];
        if (verb->head < 0) continue; // direct verb, no item argument""",
"""    unsigned long long zt_blk[NETHACK_NUM_ACTIONS];
    nethack_zt_blocked_slots(env, zt_blk);
    for (int a = 0; a < NETHACK_NUM_ACTIONS; a++) {
        const Verb* verb = &NETHACK_VERBS[a];
        if (verb->head < 0) continue; // direct verb, no item argument""")
rep("""                if (nethack_slot_usable(env, verb, i)) {""",
    """                if (nethack_slot_usable(env, verb, i, zt_blk[a])) {""")
p.write_text(t); print('C applied to', p)
