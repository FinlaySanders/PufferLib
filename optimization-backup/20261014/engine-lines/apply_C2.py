"""Candidate C2 (action mask, exact): per-slot facts gathered once per step (class, worn, known-cursed, container, fresh-book, armour category,
worn categories), then each verb's usable-slot set is a few 64-bit mask operations instead of a per-(verb, slot) predicate call.
Same predicate semantics as nethack_slot_usable; the original function is kept for reference but no longer called. usage: apply_C2.py <header>"""
import sys
from pathlib import Path
p=Path(sys.argv[1]); t=p.read_text()
def rep(old,new):
    global t; assert t.count(old)==1, old[:80]; t=t.replace(old,new)
rep("""    unsigned long long zt_blk[NETHACK_NUM_ACTIONS];
    nethack_zt_blocked_slots(env, zt_blk);
    for (int a = 0; a < NETHACK_NUM_ACTIONS; a++) {
        const Verb* verb = &NETHACK_VERBS[a];
        if (verb->head < 0) continue; // direct verb, no item argument
        unsigned char* slots = mask + NETHACK_NUM_ACTIONS + verb->head * NETHACK_INV_SLOTS;
        memset(slots, 0, NETHACK_INV_SLOTS);
        int has_usable = 0;
        if ((verb->item_classes & inv_classes)
            && !(a == NETHACK_ACT_WIELD && welded)) {
            for (int i = 0; i < inv_n; i++) {
                if (nethack_slot_usable(env, verb, i, zt_blk[a])) {
                    slots[i] = 1;
                    has_usable = 1;
                }
            }
        }
        if (has_usable) continue;""",
"""    unsigned long long zt_blk[NETHACK_NUM_ACTIONS];
    nethack_zt_blocked_slots(env, zt_blk);
    // per-slot facts, gathered once (bit i = slot i; inv_n <= NETHACK_INV_SLOTS < 64)
    unsigned long long class_m[NETHACK_NUM_OCLASSES]; memset(class_m, 0, sizeof class_m);
    unsigned long long worn_m = 0, cursed_m = 0, cont_m = 0, book_fresh_m = 0;
    signed char cat_of[NETHACK_INV_SLOTS];
    for (int i = 0; i < inv_n; i++) {
        unsigned long long bit = 1ULL << i; int oc = env->inv_oclasses[i];
        class_m[oc] |= bit;
        if (env->inv_state[i * NLE_INV_STATE_FIELDS + 5] & 1) worn_m |= bit;
        if (env->inv_state[i * NLE_INV_STATE_FIELDS + 0] == 1) cursed_m |= bit;
        int gn = env->inv_glyphs[i] - NH_GLYPH_OBJ_OFF;
        cat_of[i] = (signed char)((gn >= 0 && gn < NH_NUM_OBJECTS) ? nh_obj_armcat[gn] : -1);
        if (gn >= 189 /* LARGE_BOX */ && gn <= 194 /* BAG_OF_HOLDING */) cont_m |= bit;
        if (oc == 10 && env->inv_true[i] != NETHACK_PAD_GLYPH) {
            int otyp = env->inv_true[i] - NH_GLYPH_OBJ_OFF;
            for (int j = 0; j < NETHACK_SPELL_SLOTS; j++)
                if (env->spell_ids[j] == otyp && env->spell_knows[j] > 2000) { book_fresh_m |= bit; break; }
        }
    }
    // worn armour categories (same slot walk as the WEAR layering rule: every lettered slot)
    unsigned int worn_cats = 0, worn_cursed_cats = 0;
    for (int j = 0; j < NETHACK_INV_SLOTS && env->inv_letters[j]; j++) {
        if (!(env->inv_state[j * NLE_INV_STATE_FIELDS + 5] & 1)) continue;
        int gj = env->inv_glyphs[j] - NH_GLYPH_OBJ_OFF;
        int cj = (gj >= 0 && gj < NH_NUM_OBJECTS) ? nh_obj_armcat[gj] : -1;
        if (cj < 0) continue;
        worn_cats |= 1u << cj;
        if (env->inv_state[j * NLE_INV_STATE_FIELDS + 0] == 1) worn_cursed_cats |= 1u << cj;
    }
    int blind = (env->blstats[NLE_BL_CONDITION] & 0x20L) != 0;
    for (int a = 0; a < NETHACK_NUM_ACTIONS; a++) {
        const Verb* verb = &NETHACK_VERBS[a];
        if (verb->head < 0) continue; // direct verb, no item argument
        unsigned char* slots = mask + NETHACK_NUM_ACTIONS + verb->head * NETHACK_INV_SLOTS;
        memset(slots, 0, NETHACK_INV_SLOTS);
        int has_usable = 0;
        if ((verb->item_classes & inv_classes)
            && !(a == NETHACK_ACT_WIELD && welded)
            && !(env->cant_hold && (a == NETHACK_ACT_WIELD || a == NETHACK_ACT_THROW || a == NETHACK_ACT_WEAR))) {
            unsigned long long cand = 0;
            for (unsigned int cl = verb->item_classes & ((1u << NETHACK_NUM_OCLASSES) - 1u); cl; cl &= cl - 1) cand |= class_m[__builtin_ctz(cl)];
            cand &= ~zt_blk[a];
            if (a == NETHACK_ACT_APPLY) cand &= ~cont_m;
            if (verb->item_classes == ((1u << 9) | (1u << 10))) { if (blind) cand = 0; else cand &= ~book_fresh_m; }
            if (a == NETHACK_ACT_TAKEOFF || a == NETHACK_ACT_REMOVE) cand &= ~cursed_m;
            if (verb->wornreq == WORN_ONLY) cand &= worn_m;
            else if (verb->wornreq == UNWORN_ONLY) {
                cand &= ~worn_m;
                if (verb->item_classes == (1u << 3)) // WEAR layering: suit/shirt under a cloak, shirt under a suit, known-cursed same-slot swap
                    for (unsigned long long c = cand; c; c &= c - 1) {
                        int i = __builtin_ctzll(c), cat = cat_of[i];
                        if (cat < 0) continue;
                        if (((cat == 0 || cat == 6) && (worn_cats & (1u << 5))) || (cat == 6 && (worn_cats & 1u)) || (worn_cursed_cats & (1u << cat)))
                            cand &= ~(1ULL << i);
                    }
            }
            for (unsigned long long c = cand; c; c &= c - 1) slots[__builtin_ctzll(c)] = 1;
            has_usable = cand != 0;
        }
        if (has_usable) continue;""")
rep("""static int nethack_slot_usable(const Nethack* env, const Verb* verb, int i, unsigned long long zt_blk) {""",
    """static int __attribute__((unused)) nethack_slot_usable(const Nethack* env, const Verb* verb, int i, unsigned long long zt_blk) {""")
p.write_text(t); print('C2 applied to', p)
