// Composite terminal view of a Nethack env (message ring, coloured map, inventory pane, status box).
// Shared by the TTY demo (nethack.c) and the eval watch hook (nethack.h, NH_WATCH_ENV/NH_WATCH_EP).
#ifndef NETHACK_VIEW_H
#define NETHACK_VIEW_H

static int demo_tty;
static unsigned char demo_tty_chars[NLE_TERM_LI * NLE_TERM_CO];
static signed char demo_tty_colors[NLE_TERM_LI * NLE_TERM_CO];
static unsigned char demo_tty_cursor[2];

#define DEMO_MSG_RING 18
static char demo_msgs[DEMO_MSG_RING][96];
static int demo_msg_n = 0;

static void demo_note_message(Nethack* env) {
    if (!env->message[0]) return;
    char buf[96];
    int j = 0;
    for (; j < 95 && env->message[j]; j++) buf[j] = (char)env->message[j];
    buf[j] = 0;
    if (demo_msg_n > 0) {
        char* prev = demo_msgs[(demo_msg_n - 1) % DEMO_MSG_RING];
        if (strcmp(prev, buf) == 0) return;
        // getline echo: the game repaints the topline per keystroke; an
        // extension of the previous message replaces it (lossless)
        size_t pl = strlen(prev);
        if (pl > 0 && j > (int)pl && strncmp(prev, buf, pl) == 0) {
            strcpy(prev, buf);
            return;
        }
    }
    strcpy(demo_msgs[demo_msg_n % DEMO_MSG_RING], buf);
    demo_msg_n++;
}

// menucolor-style BUC tint
static const char* demo_inv_clr(Nethack* env, int i) {
    if (env->inv_oclasses[i] == 12) return "\x1b[33m"; // COIN_CLASS (objclass.h)
    int buc = env->inv_state[i * NLE_INV_STATE_FIELDS];
    return buc == 1 ? "\x1b[31m" : buc == 3 ? "\x1b[32m"
         : buc == 2 ? "\x1b[37m" : "\x1b[36m";
}

// curses-look cell: walls -> box drawing, floors -> '·', engine colors -> ANSI
#define DEMO_CMAP_OFF 2359
#define DEMO_PET_LO 381
#define DEMO_PET_HI 762
static unsigned char demo_colors[NH_GRID]; // bound via nethack_color_sink
static const char* demo_wall_sym[12] = { // S_stone..S_trwall
    " ", "│", "─", "┌", "┐", "└", "┘",
    "┼", "┴", "┬", "┤", "├"};
static const int demo_ansi_clr[16] = // CLR_* 0..15 -> SGR fg
    {90, 31, 32, 33, 34, 35, 36, 37, 39, 91, 92, 93, 94, 95, 96, 97};

static void demo_map_cell(Nethack* env, int r, int c, int hero) {
    // underfoot_glyphs hides the hero glyph; draw the @ explicitly
    if (hero) {
        printf("\x1b[7;1;97m@\x1b[0m");
        return;
    }
    int g = env->glyphs[r * NH_COLS + c];
    unsigned char ch = env->chars[r * NH_COLS + c];
    int cmap = g - DEMO_CMAP_OFF;
    if (cmap >= 1 && cmap <= 11) { // walls in PUFF_CYAN (connect4.h)
        printf("\x1b[38;2;0;187;187m%s\x1b[0m", demo_wall_sym[cmap]);
        return;
    }
    if (cmap == 19) { // S_room
        printf("\x1b[37m·\x1b[0m");
        return;
    }
    if (cmap == 20) { // S_darkroom
        printf("\x1b[2m·\x1b[0m");
        return;
    }
    if (!ch || ch == ' ') {
        putchar(' ');
        return;
    }
    int clr = demo_colors[r * NH_COLS + c] & 15;
    printf("\x1b[%s%dm%c\x1b[0m",
           (g >= DEMO_PET_LO && g < DEMO_PET_HI) ? "4;" : "",
           demo_ansi_clr[clr], ch);
}

// tty map cell: authentic chars/colors from the game's own screen (rows 1..21)
static void demo_map_cell_tty(int r, int c) {
    unsigned char ch = demo_tty_chars[(r + 1) * NLE_TERM_CO + (c + 1)];
    int clr = demo_tty_colors[(r + 1) * NLE_TERM_CO + (c + 1)] & 15;
    if (!ch || ch == ' ') {
        putchar(' ');
        return;
    }
    printf("\x1b[%dm%c\x1b[0m", demo_ansi_clr[clr], ch);
}

#define DEMO_INV_W 42 // inventory pane inner width

// perm_invent pane: doname text grouped by class in game display order
static unsigned char demo_inv_strs[NLE_INVENTORY_SIZE * NLE_INVENTORY_STR_LENGTH];
static const int demo_inv_order[] =
    {12, 5, 2, 3, 7, 9, 10, 8, 4, 11, 6, 13, 14, 15, 16, 17, 1};
static const char* demo_class_name[18] = {0, "Illegal objects", "Weapons",
    "Armor", "Rings", "Amulets", "Tools", "Comestibles", "Potions", "Scrolls",
    "Spellbooks", "Wands", "Coins", "Gems/Stones", "Boulders/Statues",
    "Iron balls", "Chains", "Venoms"};
#define DEMO_PANE_MAX 64

static int demo_inv_pane(Nethack* env, char lines[][DEMO_INV_W + 8],
                         const char* clrs[]) {
    int n = 0;
    for (int k = 0; k < (int)(sizeof(demo_inv_order)/sizeof(*demo_inv_order)); k++) {
        int cls = demo_inv_order[k], first = 1;
        for (int i = 0; i < NETHACK_INV_SLOTS && n < DEMO_PANE_MAX - 1; i++) {
            if (!env->inv_letters[i] || env->inv_oclasses[i] != cls) continue;
            if (first) {
                snprintf(lines[n], DEMO_INV_W + 8, "%s", demo_class_name[cls]);
                clrs[n++] = "\x1b[1m";
                first = 0;
            }
            snprintf(lines[n], DEMO_INV_W + 8, "%c) %s", env->inv_letters[i],
                     demo_inv_strs + i * NLE_INVENTORY_STR_LENGTH);
            clrs[n] = demo_inv_clr(env, i);
            n++;
        }
    }
    return n;
}

static void demo_box_edge(const char* l, const char* r, const char* title, int inner) {
    printf("%s", l);
    int n = 0;
    if (title) n = printf("─ %s ", title) - 2; // rule char is 3 bytes, 1 column
    for (; n < inner; n++) printf("─");
    printf("%s", r);
}

// right-column inventory box segment for composite row k (0 = top border)
static void demo_inv_row(int k, int last, int pn,
                         char plines[][DEMO_INV_W + 8], const char** pclrs) {
    if (k == 0) {
        printf(" ");
        demo_box_edge("┌", "┐\n", "Inventory", DEMO_INV_W);
        return;
    }
    if (k >= last) {
        printf(" ");
        demo_box_edge("└", "┘\n", NULL, DEMO_INV_W);
        return;
    }
    printf(" │ ");
    int i = k - 1, len = 0;
    if (i == last - 2 && pn > last - 1)
        len = printf("\x1b[2m... +%d more\x1b[0m", pn - (last - 2)) - 8;
    else if (i < pn)
        len = printf("%s%.*s\x1b[0m", pclrs[i], DEMO_INV_W - 2, plines[i])
            - (int)strlen(pclrs[i]) - 4;
    printf("%*s│\n", DEMO_INV_W - 1 - len, "");
}

// one box row: bytes in buf, visible columns in vis; segments past the box
// width are clipped so the row never wraps
typedef struct { char buf[512]; int pos, vis; } DemoLine;
static void demo_line_add(DemoLine* l, const char* esc, const char* text) {
    int n = (int)strlen(text), room = NH_COLS + 1 - l->vis; // rows are NH_COLS+2 wide with both edges
    if (room <= 0 || n <= 0) return;
    if (n > room) n = room;
    l->pos += snprintf(l->buf + l->pos, sizeof(l->buf) - l->pos, "%s%.*s%s",
                       esc, n, text, esc[0] ? "\x1b[0m" : "");
    l->vis += n;
}
static void demo_line_flush(DemoLine* l) {
    printf("%s%*s│", l->buf, NH_COLS + 1 - l->vis, "");
}

static void demo_render(Nethack* env, int rate_hz, long steps) {
    long* bl = env->blstats;
    printf("\x1b[H\x1b[2J");
    static char plines[DEMO_PANE_MAX][DEMO_INV_W + 8];
    static const char* pclrs[DEMO_PANE_MAX];
    int pn = demo_inv_pane(env, plines, pclrs);
    // left column: message box, map box, status box; inventory runs full height
    int last = 1 + DEMO_MSG_RING + 1 + 1 + NH_ROWS + 1 + 4 - 1;
    int k = 0;
    demo_box_edge("┌", "┐", NULL, NH_COLS);
    demo_inv_row(k++, last, pn, plines, pclrs);
    int shown = demo_msg_n < DEMO_MSG_RING ? demo_msg_n : DEMO_MSG_RING;
    for (int m = 0; m < DEMO_MSG_RING; m++) {
        printf("│ ");
        int len = 0;
        if (m >= DEMO_MSG_RING - shown) {
            int idx = (demo_msg_n - (DEMO_MSG_RING - m)) % DEMO_MSG_RING;
            len = printf("%s%.*s\x1b[0m", m == DEMO_MSG_RING - 1 ? "\x1b[1m" : "\x1b[2m",
                         NH_COLS - 2, demo_msgs[idx]) - 8;
        }
        printf("%*s│", NH_COLS - 1 - len, "");
        demo_inv_row(k++, last, pn, plines, pclrs);
    }
    demo_box_edge("└", "┘", NULL, NH_COLS);
    demo_inv_row(k++, last, pn, plines, pclrs);
    char title[32];
    snprintf(title, sizeof(title), "Dlvl:%ld", bl[NLE_BL_DEPTH]);
    demo_box_edge("┌", "┐", title, NH_COLS);
    demo_inv_row(k++, last, pn, plines, pclrs);
    for (int r = 0; r < NH_ROWS; r++) {
        printf("│");
        for (int c = 0; c < NH_COLS; c++) {
            if (demo_tty) demo_map_cell_tty(r, c);
            else demo_map_cell(env, r, c, c == bl[NLE_BL_X] && r == bl[NLE_BL_Y]);
        }
        printf("│");
        demo_inv_row(k++, last, pn, plines, pclrs);
    }
    demo_box_edge("└", "┘", NULL, NH_COLS);
    demo_inv_row(k++, last, pn, plines, pclrs);
    // status box: hitpointbar over the agent name, then the stat line
    demo_box_edge("┌", "┐", NULL, NH_COLS);
    demo_inv_row(k++, last, pn, plines, pclrs);
    long hp = bl[NLE_BL_HP], hpm = bl[NLE_BL_HPMAX] > 0 ? bl[NLE_BL_HPMAX] : 1;
    static const char* rolenm[13] = {"Archeologist", "Barbarian", "Caveman",
        "Healer", "Knight", "Monk", "Priest", "Rogue", "Ranger", "Samurai",
        "Tourist", "Valkyrie", "Wizard"};
    static const char* racenm[5] = {"human", "elven", "dwarven", "gnomish", "orcish"};
    static const char* alignnm[3] = {"lawful", "neutral", "chaotic"};
    int ir = 0, ic = 0, ig = 0, ia = 0;
    nle_identity(env->ctx, &ir, &ic, &ig, &ia);
    char name[40];
    int nl = snprintf(name, sizeof(name), "Agent the %s",
        (ir >= 0 && ir < 13) ? rolenm[ir] : "Puffer");
    int fill = (int)((hp * nl + hpm - 1) / hpm);
    if (fill > nl) fill = nl;
    int hpc = hp * 3 >= hpm * 2 ? 32 : hp * 3 >= hpm ? 33 : 31;
    // both status rows are clipped to the box width: a long spell list or
    // several conditions used to wrap onto the next terminal line
    DemoLine L = {"│", 3, 1};
    char esc[16], tmp[160];
    snprintf(esc, sizeof(esc), "\x1b[7;%dm", hpc);
    demo_line_add(&L, "", " [");
    snprintf(tmp, sizeof(tmp), "%.*s", fill, name);
    demo_line_add(&L, esc, tmp);
    snprintf(tmp, sizeof(tmp), "%s] ", name + fill);
    demo_line_add(&L, "", tmp);
    snprintf(tmp, sizeof(tmp), "%s %s %s",
             (ia >= 0 && ia < 3) ? alignnm[ia] : "?", ig == 1 ? "female" : "male",
             (ic >= 0 && ic < 5) ? racenm[ic] : "?");
    demo_line_add(&L, "\x1b[2m", tmp);
    snprintf(tmp, sizeof(tmp), " St:%ld Dx:%ld Co:%ld  Score:%ld",
             bl[NLE_BL_STR25], bl[NLE_BL_DEX], bl[NLE_BL_CON], bl[NLE_BL_SCORE]);
    demo_line_add(&L, "", tmp);
    demo_line_flush(&L);
    demo_inv_row(k++, last, pn, plines, pclrs);
    static const char* conds[10] = {"Stone", "Slime", "Strngl", "FoodPois",
        "TermIll", "Blind", "Deaf", "Stun", "Conf", "Hallu"};
    static const char* hungers[5] = {"Satiated", "", "Hungry", "Weak", "Fainting"};
    long hu = bl[NLE_BL_HUNGER];
    L = (DemoLine){"│", 3, 1};
    snprintf(tmp, sizeof(tmp), " Dlvl:%ld $:%ld HP:%ld(%ld) Pw:%ld(%ld) AC:%ld Xp:%ld/%ld T:%ld",
             bl[NLE_BL_DEPTH], bl[NLE_BL_GOLD], hp, bl[NLE_BL_HPMAX],
             bl[NLE_BL_ENE], bl[NLE_BL_ENEMAX], bl[NLE_BL_AC],
             bl[NLE_BL_XP], bl[NLE_BL_EXP], bl[NLE_BL_TIME]);
    demo_line_add(&L, "", tmp);
    if (hu >= 0 && hu < 5 && hungers[hu][0]) {
        demo_line_add(&L, "", " ");
        demo_line_add(&L, "\x1b[33m", hungers[hu]);
    }
    for (int b = 0; b < 10; b++) {
        if (!(bl[NLE_BL_CONDITION] & (1L << b))) continue;
        demo_line_add(&L, "", " ");
        demo_line_add(&L, "\x1b[31;1m", conds[b]);
    }
    // known spells: name Lv fail% (env->spell_* is refreshed each pack_obs);
    // shown only when the whole list fits after the conditions
    if (env->n_spells > 0) {
        static const struct { int id; const char* nm; } spnames[] = {
            {344, "sleep"}, {348, "healing"}, {377, "protection"},
            {340, "force bolt"}, {342, "magic missile"}, {361, "cure blindness"},
        };
        int n = snprintf(tmp, sizeof(tmp), "Sp:");
        for (int i = 0; i < env->n_spells && i < 2; i++) {
            const char* nm = NULL;
            for (unsigned s = 0; s < sizeof(spnames)/sizeof(spnames[0]); s++) {
                if (spnames[s].id != env->spell_ids[i]) continue;
                nm = spnames[s].nm;
                break;
            }
            n += snprintf(tmp + n, sizeof(tmp) - n, "%s%s(L%d %d%%)", i ? "," : "",
                          nm ? nm : "spell", env->spell_levs[i], env->spell_fails[i]);
        }
        if (L.vis + 2 + n <= NH_COLS + 1) {
            demo_line_add(&L, "", "  ");
            demo_line_add(&L, "\x1b[36m", tmp);
        }
    }
    demo_line_flush(&L);
    demo_inv_row(k++, last, pn, plines, pclrs);
    demo_box_edge("└", "┘", NULL, NH_COLS);
    demo_inv_row(k++, last, pn, plines, pclrs);
    if (rate_hz > 0) // auto-run (web): no interactive keys to advertise
        printf("\x1b[2mstep %ld  |  running %d Hz\x1b[0m\n", steps, rate_hz);
    else
        printf("\x1b[2msteps %ld  |  SPACE step/hold 5Hz  |  Shift+SPACE (or S) 20Hz  |  q quit\x1b[0m\n",
               steps);
    fflush(stdout);
}

#endif
