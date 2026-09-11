// Step-by-step policy agreement: replay a CUDA trajectory's observations through the
// CPU port and ask how often CUDA's chosen action is the CPU's argmax, against what
// that rate should be if the two were the same policy.
#define main nh_demo_main
#include "ocean/nethack/nethack.c"
#undef main
int main(int argc, char** argv) {
    if (argc < 3) { fprintf(stderr, "usage: nh_agree weights actlog\n"); return 1; }
    Weights* w = load_weights(argv[1]); if (!w) return 1;
    NethackNet* net = make_nethack_net(w);
    FILE* f = fopen(argv[2], "rb"); if (!f) { perror("actlog"); return 1; }
    int hdr[3]; if (fread(hdr, sizeof(int), 3, f) != 3) return 1;
    int OS = hdr[0], MS = hdr[1], NH = hdr[2];
    printf("obs=%d mask=%d heads=%d (cpu: obs=%d mask=%d heads=%d)\n", OS, MS, NH,
           NETHACK_OBS_SIZE, (int)(NETHACK_NUM_ACTIONS + 12*NETHACK_INV_SLOTS
           + NETHACK_DIR_HEADS*NETHACK_NUM_DIRS + NETHACK_SPELL_SLOTS), DEMO_NUM_HEADS);
    unsigned char* ob = malloc(OS); unsigned char* mk = malloc(MS); short act[32];
    long n = 0, verb_hit = 0; double verb_p = 0, verb_pmax = 0, logp_cuda = 0, logp_max = 0;
    int sizes[2] = {NETHACK_NUM_ACTIONS, 0};
    while (fread(ob, 1, OS, f) == (size_t)OS && fread(mk, 1, MS, f) == (size_t)MS
           && fread(act, sizeof(short), NH, f) == (size_t)NH) {
        nethack_net_forward(net, ob);
        for (int i = 0; i < MS; i++) if (!mk[i]) net->logits[i] = -1e9f;
        int A = sizes[0]; float mx = -1e30f; int am = 0;
        for (int a = 0; a < A; a++) if (net->logits[a] > mx) { mx = net->logits[a]; am = a; }
        double se = 0; for (int a = 0; a < A; a++) se += exp((double)net->logits[a] - mx);
        double lse = mx + log(se);
        int cv = act[0];
        if (cv >= 0 && cv < A) {
            verb_hit += (cv == am);
            double pc = exp((double)net->logits[cv] - lse), pm = exp((double)mx - lse);
            verb_p += pc; verb_pmax += pm;
            logp_cuda += log(pc + 1e-30); logp_max += log(pm + 1e-30);
        }
        n++;
    }
    printf("\nsteps compared: %ld\n", n);
    printf("  CUDA's verb == CPU's argmax          : %.1f%%  (%ld/%ld)\n", 100.0*verb_hit/n, verb_hit, n);
    printf("  expected if same policy (mean p_max) : %.1f%%\n", 100.0*verb_pmax/n);
    printf("  mean CPU prob of CUDA's verb         : %.3f\n", verb_p/n);
    printf("  mean CPU prob of CPU's own argmax    : %.3f\n", verb_pmax/n);
    printf("  mean log p_cpu(CUDA verb)            : %.3f   (argmax: %.3f)\n", logp_cuda/n, logp_max/n);
    return 0;
}
