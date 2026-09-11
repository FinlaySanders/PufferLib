// Replay a logged CUDA trajectory through the CPU port and dump, per step:
// the port's verb argmax, its max prob, and the post-MinGRU hidden state.
// Built twice (fp32 and -DDEMO_BF16) so the two can be compared head to head.
#define main nh_demo_main
#include "ocean/nethack/nethack.c"
#undef main
int main(int argc, char** argv) {
    if (argc < 4) { fprintf(stderr, "usage: nh_trace2 weights actlog out\n"); return 1; }
    Weights* w = load_weights(argv[1]); if (!w) return 1;
    NethackNet* net = make_nethack_net(w);
    FILE* f = fopen(argv[2], "rb"); if (!f) { perror("actlog"); return 1; }
    FILE* o = fopen(argv[3], "wb"); if (!o) { perror("out"); return 1; }
    int hdr[3]; if (fread(hdr, sizeof(int), 3, f) != 3) return 1;
    int OS = hdr[0], MS = hdr[1], NH = hdr[2], H = net->hidden_size;
    fwrite(&H, sizeof(int), 1, o);
    unsigned char* ob = malloc(OS); unsigned char* mk = malloc(MS); short act[32];
    long n = 0;
    while (fread(ob, 1, OS, f) == (size_t)OS && fread(mk, 1, MS, f) == (size_t)MS
           && fread(act, sizeof(short), NH, f) == (size_t)NH) {
        nethack_net_forward(net, ob);
        for (int i = 0; i < MS; i++) if (!mk[i]) net->logits[i] = -1e9f;
        int A = NETHACK_NUM_ACTIONS; float mx = -1e30f; int am = 0;
        for (int a = 0; a < A; a++) if (net->logits[a] > mx) { mx = net->logits[a]; am = a; }
        double se = 0; for (int a = 0; a < A; a++) se += exp((double)net->logits[a] - mx);
        float pmax = (float)(1.0 / se);
        int cv = act[0];
        fwrite(&am, sizeof(int), 1, o); fwrite(&cv, sizeof(int), 1, o); fwrite(&pmax, sizeof(float), 1, o);
        fwrite(net->mingru->output, sizeof(float), (size_t)H, o);
        n++;
    }
    fprintf(stderr, "steps=%ld hidden=%d\n", n, H);
    return 0;
}
