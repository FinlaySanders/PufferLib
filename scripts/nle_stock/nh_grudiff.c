// Isolated MinGRU test: load CUDA's state-in and x, run the CPU recurrence, compare out and state-out.
#define main nh_demo_main
#include "ocean/nethack/nethack.c"
#undef main
static void st(const char* n, const float* a, const float* b, int len) {
    double mx=0, ma=0, d=0, x=0, y=0; int ami=-1;
    for (int i=0;i<len;i++){ double e=fabs(a[i]-b[i]); ma+=e; if(e>mx){mx=e;ami=i;} d+=a[i]*b[i]; x+=a[i]*a[i]; y+=b[i]*b[i]; }
    printf("    %-16s maxabs=%.4f@%-4d meanabs=%.5f cos=%.6f\n", n, mx, ami, ma/len, d/(sqrt(x)*sqrt(y)+1e-12));
}
int main(int argc, char** argv) {
    Weights* w = load_weights(argv[1]); NethackNet* net = make_nethack_net(w);
    FILE* f = fopen(argv[2], "rb"); int hdr[2], rec = 0; float* prev_sin = NULL;
    while (fread(hdr, sizeof(int), 2, f) == 2) {
        int L = hdr[0], H = hdr[1]; int n = 2*H + 2*L*H; float* g = malloc(4*n); if (fread(g,4,n,f)!=(size_t)n) break;
        float *x=g, *sin=g+H, *out=g+H+L*H, *sout=g+2*H+L*H;
        double sdiff = 0; if (prev_sin) { for (int i=0;i<L*H;i++) sdiff += fabs(sin[i]-prev_sin[i]); sdiff/=L*H; }
        printf("rec %2d  cuda state-in change vs previous call: meanabs=%.5f  (|state|=%.4f)\n", rec, sdiff, ({double s=0; for(int i=0;i<L*H;i++) s+=fabs(sin[i]); s/(L*H);}));
        memcpy(net->mingru->state, sin, sizeof(float)*L*H);       // CUDA's state-in
        float* xb = malloc(4*H); memcpy(xb, x, 4*H);
        mingru(net->mingru, xb);                                   // CPU recurrence, one step
        st("out", net->mingru->output, out, H);
        for (int i=0;i<L;i++){ char nm[32]; snprintf(nm,32,"state-out L%d",i); st(nm, net->mingru->state+i*H, sout+i*H, H); }
        if (!prev_sin) prev_sin = malloc(4*L*H); memcpy(prev_sin, sin, 4*L*H);
        free(g); free(xb); rec++; if (rec >= 10) break;
    }
    return 0;
}
