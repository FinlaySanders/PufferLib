// Stage-by-stage diff of the CPU port against CUDA dumps: encoder (enc.dump) and
// decoder inputs/outputs (dec.dump), paired by forward index.
#define main nh_demo_main
#include "ocean/nethack/nethack.c"
#undef main
static double cosv(const float* a, const float* b, int n) { double d=0,x=0,y=0; for (int i=0;i<n;i++){d+=a[i]*b[i];x+=a[i]*a[i];y+=b[i]*b[i];} return d/(sqrt(x)*sqrt(y)+1e-12); }
static void stats(const char* name, const float* a, const float* b, int n) {
    double mx=0, ma=0, ref=0; int ami=-1; for (int i=0;i<n;i++){ double d=fabs(a[i]-b[i]); ma+=d; ref+=fabs(b[i]); if(d>mx){mx=d;ami=i;} }
    printf("    %-14s n=%4d maxabs=%.4f@%-4d meanabs=%.5f cos=%.6f (cuda mean|x|=%.4f)\n", name, n, mx, ami, ma/n, cosv(a,b,n), ref/n);
}
// the CPU port's decoder, factored so it can be fed CUDA-side inputs
static void cpu_decode(NethackNet* net, const float* hs, const float* slots, const float* spkeys, float* out) {
    int H = net->hidden_size; float tmp[DEMO_DEC_LIN]; float q[DEMO_QDIM];
    for (int r = 0; r < DEMO_DEC_LIN; r++) { float acc=0; for (int k=0;k<H;k++) acc += net->dec_lin[r*H+k]*hs[k]; tmp[r]=acc; }
    for (int r = 0; r < DEMO_QDIM; r++)   { float acc=0; for (int k=0;k<H;k++) acc += net->dec_q[r*H+k]*hs[k]; q[r]=acc; }
    float kmat[DEMO_INV_FLAT];
    for (int i = 0; i < NETHACK_INV_SLOTS; i++) for (int r = 0; r < DEMO_INV_HID; r++) {
        float acc=0; for (int k=0;k<DEMO_INV_HID;k++) acc += net->dec_k[r*DEMO_INV_HID+k]*slots[i*DEMO_INV_HID+k]; kmat[i*DEMO_INV_HID+r]=acc; }
    for (int a = 0; a < NETHACK_NUM_ACTIONS; a++) out[a] = tmp[a];
    for (int h = 0; h < DEMO_PTR_HEADS; h++) { const float* qh=q+h*DEMO_INV_HID; float nq=0; for(int k=0;k<DEMO_INV_HID;k++) nq+=qh[k]*qh[k]; nq=sqrtf(nq)+1e-6f;
        for (int i = 0; i < NETHACK_INV_SLOTS; i++) { float dot=0; for(int k=0;k<DEMO_INV_HID;k++) dot+=qh[k]*kmat[i*DEMO_INV_HID+k];
            out[NETHACK_NUM_ACTIONS + h*NETHACK_INV_SLOTS + i] = expf(net->dec_tau[h])*dot/nq; } }
    for (int d = 0; d < NETHACK_DIR_HEADS*NETHACK_NUM_DIRS; d++) out[NETHACK_NUM_ACTIONS + DEMO_PTR_HEADS*NETHACK_INV_SLOTS + d] = tmp[NETHACK_NUM_ACTIONS + d];
    const float* qs = q + DEMO_PTR_HEADS*DEMO_INV_HID;
    for (int sp = 0; sp < NETHACK_SPELL_SLOTS; sp++) { float dot=0; for(int k=0;k<DEMO_SPKEY;k++) dot+=qs[k]*spkeys[sp*DEMO_SPKEY+k];
        out[NETHACK_NUM_ACTIONS + DEMO_PTR_HEADS*NETHACK_INV_SLOTS + NETHACK_DIR_HEADS*NETHACK_NUM_DIRS + sp] = dot*0.25f; }
    out[DEMO_OD] = tmp[NETHACK_NUM_ACTIONS + NETHACK_DIR_HEADS*NETHACK_NUM_DIRS];
}
static void groups(const char* tag, const float* a, const float* b, int od) {
    int v0=0, v1=NETHACK_NUM_ACTIONS, s1=v1+DEMO_PTR_HEADS*NETHACK_INV_SLOTS, d1=s1+NETHACK_DIR_HEADS*NETHACK_NUM_DIRS, p1=d1+NETHACK_SPELL_SLOTS;
    printf("  %s\n", tag);
    stats("verb[0,22)", a+v0, b+v0, v1-v0); stats("slots[660]", a+v1, b+v1, s1-v1); stats("dirs[48]", a+s1, b+s1, d1-s1);
    stats("spell", a+d1, b+d1, p1-d1); if (od > p1) stats("value", a+p1, b+p1, 1);
    // per-head argmax agreement for the verb head and the 12 slot heads
    int agree=0; { int ia=0,ib=0; for(int i=1;i<v1;i++){ if(a[i]>a[ia]) ia=i; if(b[i]>b[ib]) ib=i; } agree+=(ia==ib); }
    for (int h=0;h<DEMO_PTR_HEADS;h++){ const float* x=a+v1+h*NETHACK_INV_SLOTS; const float* y=b+v1+h*NETHACK_INV_SLOTS; int ia=0,ib=0; for(int i=1;i<NETHACK_INV_SLOTS;i++){ if(x[i]>x[ia]) ia=i; if(y[i]>y[ib]) ib=i; } agree+=(ia==ib); }
    printf("    argmax agreement: verb+12 slot heads = %d/13\n", agree);
}
int main(int argc, char** argv) {
    if (argc < 4) { fprintf(stderr, "usage: nh_taildiff weights enc.dump dec.dump\n"); return 1; }
    Weights* w = load_weights(argv[1]); if (!w) return 1; NethackNet* net = make_nethack_net(w);
    FILE* fe = fopen(argv[2], "rb"), *fd = fopen(argv[3], "rb"); if (!fe || !fd) { perror("dump"); return 1; }
    int he[3], hd[4], rec = 0; float* mine = malloc(sizeof(float) * 4096); float* dec = malloc(sizeof(float) * 4096);
    while (fread(he, sizeof(int), 3, fe) == 3 && fread(hd, sizeof(int), 4, fd) == 4) {
        int OS=he[0], CW=he[1], HE=he[2], H=hd[0], SL=hd[1], SK=hd[2], OD=hd[3];
        unsigned char* ob = malloc(OS); float* enc = malloc(4*(CW+HE)); float* tail = malloc(4*(H+SL+SK+OD));
        if (fread(ob,1,OS,fe)!=(size_t)OS || fread(enc,4,CW+HE,fe)!=(size_t)(CW+HE) || fread(tail,4,H+SL+SK+OD,fd)!=(size_t)(H+SL+SK+OD)) break;
        const float *cH = tail, *cSL = tail+H, *cSK = tail+H+SL, *cOUT = tail+H+SL+SK;
        nethack_net_forward(net, ob);
        printf("rec %d\n", rec);
        stats("enc hidden", net->hidden, enc+CW, HE);
        stats("slot keys", net->slots, cSL, SL);
        stats("spell keys", net->spkeys, cSK, SK);
        stats("mingru out", net->mingru->output, cH, H);
        groups("END-TO-END: cpu logits vs cuda", net->logits, cOUT, OD);
        cpu_decode(net, cH, cSL, cSK, dec);
        groups("DECODER-ONLY: cpu decoder on CUDA inputs vs cuda", dec, cOUT, OD);
        rec++; free(ob); free(enc); free(tail);
        if (rec >= 12) break;
    }
    return 0;
}
