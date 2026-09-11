// Diff the CPU port's encoder against a CUDA dump (NH_ENCDUMP) on identical observations.
#define main nh_demo_main
#include "ocean/nethack/nethack.c"
#undef main
typedef struct { int off; const char* name; } Seg;
static int segcmp(const void* a, const void* b) { return ((const Seg*)a)->off - ((const Seg*)b)->off; }
int main(int argc, char** argv) {
    if (argc < 3) { fprintf(stderr, "usage: nh_encdiff weights dump\n"); return 1; }
    Weights* w = load_weights(argv[1]); if (!w) return 1;
    NethackNet* net = make_nethack_net(w);
    FILE* f = fopen(argv[2], "rb"); if (!f) { perror("dump"); return 1; }
    Seg segs[] = {{0,"loc"},{DEMO_LOC_HID,"glb(terr)"},{DEMO_LOC_HID+DEMO_GLB_HID,"bl_mlp"},
        {DEMO_LOC_HID+DEMO_GLB_HID+DEMO_BLH,"bl_raw"},{DEMO_MSG_CONCAT_OFF,"msg"},{DEMO_SPELL_CONCAT_OFF,"spell"},
        {DEMO_IDE_CONCAT_OFF,"ide"},{DEMO_MINV_OFF,"inv_pool"},{DEMO_PASS_OFF,"pass"},{DEMO_MLM_OFF,"mlm"},{DEMO_MLI_OFF,"mli"},{DEMO_CONCAT,"END"}};
    int ns = (int)(sizeof segs / sizeof segs[0]); qsort(segs, ns, sizeof(Seg), segcmp);
    int hdr[3], rec = 0; double tot_h = 0, tot_c = 0;
    while (fread(hdr, sizeof(int), 3, f) == 3) {
        int OS = hdr[0], CW = hdr[1], H = hdr[2];
        unsigned char* ob = malloc(OS); float* cc = malloc(sizeof(float) * CW); float* oo = malloc(sizeof(float) * H);
        if (fread(ob, 1, OS, f) != (size_t)OS || fread(cc, 4, CW, f) != (size_t)CW || fread(oo, 4, H, f) != (size_t)H) break;
        if (rec == 0) printf("obs bytes: cuda=%d cpu=%d | concat: cuda=%d cpu=%d | hidden: cuda=%d cpu=%d\n",
                             OS, NETHACK_OBS_SIZE, CW, DEMO_CONCAT, H, net->hidden_size);
        nethack_net_forward(net, ob);
        int cw = CW < DEMO_CONCAT ? CW : DEMO_CONCAT;
        double mx = 0, ma = 0; int ami = -1;
        for (int i = 0; i < cw; i++) { double d = fabs(net->concat[i] - cc[i]); ma += d; if (d > mx) { mx = d; ami = i; } }
        double hmx = 0, hma = 0, dot = 0, na = 0, nb = 0;
        for (int i = 0; i < H && i < net->hidden_size; i++) { double d = fabs(net->hidden[i] - oo[i]); hma += d; if (d > hmx) hmx = d;
            dot += net->hidden[i] * oo[i]; na += net->hidden[i] * net->hidden[i]; nb += oo[i] * oo[i]; }
        printf("rec %2d  concat: maxabs=%.4f (idx %d) meanabs=%.5f | hidden: maxabs=%.4f meanabs=%.5f cos=%.6f\n",
               rec, mx, ami, ma / cw, hmx, hma / H, dot / (sqrt(na) * sqrt(nb) + 1e-12));
        if (rec < 3) { // per-segment localisation on the first records
            for (int s = 0; s + 1 < ns; s++) { int a = segs[s].off, b = segs[s + 1].off; if (b > cw) b = cw; if (a >= b) continue;
                double smx = 0, sma = 0, ref = 0; for (int i = a; i < b; i++) { double d = fabs(net->concat[i] - cc[i]); sma += d; if (d > smx) smx = d; ref += fabs(cc[i]); }
                printf("      %-9s [%4d,%4d)  maxabs=%.4f meanabs=%.5f  (cuda mean|x|=%.4f)\n", segs[s].name, a, b, smx, sma / (b - a), ref / (b - a)); } }
        tot_h += hma / H; tot_c += ma / cw; rec++; free(ob); free(cc); free(oo);
    }
    printf("records=%d  avg meanabs concat=%.5f hidden=%.5f\n", rec, tot_c / (rec ? rec : 1), tot_h / (rec ? rec : 1));
    return 0;
}
