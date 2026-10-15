"""Packer (ocean/nethack/nethack.h, C2 header) exact slices, written to headers_p/ (the harness include root):
 P2 nethack_ray_target(): the per-step bounds test is monotone in k, so after the k=1 test (kept) the far-side bound is the only exit
 P4 one pass over the inventory slots instead of four (class set/prefix length, welded scan, per-slot facts, worn armour categories);
    every quantity is a pure function of the slot arrays, so the merged pass computes identical values"""
from pathlib import Path
import shutil
P = Path('/puffertank/experiments/nethack-monster-turn-plan-20261014')
C2 = Path('/puffertank/experiments/nethack-engine-lines-20261014/headers/harness_root/source/ocean/nethack/nethack.h')
dst = P / 'headers_p/source/ocean/nethack/nethack.h'
dst.parent.mkdir(parents=True, exist_ok=True)
t = C2.read_text()
def rep(old, new, count=1):
    global t
    assert t.count(old) == count, (t.count(old), old[:90]); t = t.replace(old, new)

rep("""static int nethack_ray_target(Nethack* env, int dx, int dy) {
    long hx = env->blstats[NLE_BL_X], hy = env->blstats[NLE_BL_Y];
    for (int k = 1; k <= 8; k++) {
        long x = hx + dx * k, y = hy + dy * k;
        if (x < 0 || x >= NH_COLS || y < 0 || y >= NH_ROWS) return 0;
        int gl = env->glyphs[y * NH_COLS + x];""", """static int nethack_ray_target(Nethack* env, int dx, int dy) {
    long hx = env->blstats[NLE_BL_X], hy = env->blstats[NLE_BL_Y];
    // the k = 1 bounds test as before; x and y are monotone in k, so beyond it only the far border ends the walk
    if (hx + dx < 0 || hx + dx >= NH_COLS || hy + dy < 0 || hy + dy >= NH_ROWS) return 0;
    long kx = dx > 0 ? NH_COLS - 1 - hx : dx < 0 ? hx : 8, ky = dy > 0 ? NH_ROWS - 1 - hy : dy < 0 ? hy : 8;
    long kmax = kx < ky ? kx : ky; if (kmax > 8) kmax = 8;
    for (long k = 1; k <= kmax; k++) {
        long x = hx + dx * k, y = hy + dy * k;
        int gl = env->glyphs[y * NH_COLS + x];""")

rep("""    unsigned int inv_classes = 0;
    int inv_n = 0;
    for (int i = 0; i < NETHACK_INV_SLOTS && env->inv_letters[i]; i++) {
        if (env->inv_oclasses[i] >= NETHACK_NUM_OCLASSES) break; // padded tail
        inv_classes |= 1u << env->inv_oclasses[i];
        inv_n = i + 1;
    }
    int welded = 0;
    for (int j = 0; j < NETHACK_INV_SLOTS && env->inv_letters[j]; j++)
        if ((env->inv_state[j * NLE_INV_STATE_FIELDS + 5] & 2)
            && env->inv_state[j * NLE_INV_STATE_FIELDS + 0] == 1) { welded = 1; break; }
    unsigned long long zt_blk[NETHACK_NUM_ACTIONS];
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
""", """    unsigned int inv_classes = 0;
    int inv_n = 0, welded = 0, prefix = 1; // prefix: the class-known slots before the padded tail
    unsigned long long zt_blk[NETHACK_NUM_ACTIONS];
    nethack_zt_blocked_slots(env, zt_blk);
    // per-slot facts in one pass (bit i = slot i; inv_n <= NETHACK_INV_SLOTS < 64): the class set and prefix length, the weld
    // scan and the worn armour categories cover every lettered slot; the per-slot masks cover the class-known prefix
    unsigned long long class_m[NETHACK_NUM_OCLASSES]; memset(class_m, 0, sizeof class_m);
    unsigned long long worn_m = 0, cursed_m = 0, cont_m = 0, book_fresh_m = 0;
    signed char cat_of[NETHACK_INV_SLOTS];
    unsigned int worn_cats = 0, worn_cursed_cats = 0;
    for (int i = 0; i < NETHACK_INV_SLOTS && env->inv_letters[i]; i++) {
        const signed char* sti = env->inv_state + i * NLE_INV_STATE_FIELDS;
        int worn = sti[5] & 1, cursed = sti[0] == 1;
        int gn = env->inv_glyphs[i] - NH_GLYPH_OBJ_OFF;
        signed char cat = (signed char)((gn >= 0 && gn < NH_NUM_OBJECTS) ? nh_obj_armcat[gn] : -1);
        if (prefix && env->inv_oclasses[i] < NETHACK_NUM_OCLASSES) {
            unsigned long long bit = 1ULL << i; int oc = env->inv_oclasses[i];
            inv_classes |= 1u << oc;
            inv_n = i + 1;
            class_m[oc] |= bit;
            if (worn) worn_m |= bit;
            if (cursed) cursed_m |= bit;
            cat_of[i] = cat;
            if (gn >= 189 /* LARGE_BOX */ && gn <= 194 /* BAG_OF_HOLDING */) cont_m |= bit;
            if (oc == 10 && env->inv_true[i] != NETHACK_PAD_GLYPH) {
                int otyp = env->inv_true[i] - NH_GLYPH_OBJ_OFF;
                for (int j = 0; j < NETHACK_SPELL_SLOTS; j++)
                    if (env->spell_ids[j] == otyp && env->spell_knows[j] > 2000) { book_fresh_m |= bit; break; }
            }
        } else prefix = 0; // padded tail
        if ((sti[5] & 2) && cursed) welded = 1;
        if (worn && cat >= 0) {
            worn_cats |= 1u << cat;
            if (cursed) worn_cursed_cats |= 1u << cat;
        }
    }
""")
dst.write_text(t)
print('packer header written:', dst)
