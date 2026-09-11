// Agreement on EVERY head, not just the verb: the slot heads run through the
// pointer decoder and the direction heads through the linear tail, so a verb-only
// check can miss a large behavioural difference.
#define main nh_demo_main
#include "ocean/nethack/nethack.c"
#undef main
int main(int argc, char** argv) {
    Weights* w = load_weights(argv[1]); if (!w) return 1;
    NethackNet* net = make_nethack_net(w);
    FILE* f = fopen(argv[2], "rb"); if (!f) { perror("actlog"); return 1; }
    int hdr[3]; if (fread(hdr, sizeof(int), 3, f) != 3) return 1;
    int OS = hdr[0], MS = hdr[1], NH = hdr[2];
    int NA = NETHACK_NUM_ACTIONS, IV = NETHACK_INV_SLOTS, ND = NETHACK_NUM_DIRS;
    int off[20], siz[20];
    off[0]=0; siz[0]=NA;
    for (int h=0;h<12;h++){ off[1+h]=NA+h*IV; siz[1+h]=IV; }
    for (int d=0;d<NETHACK_DIR_HEADS;d++){ off[13+d]=NA+12*IV+d*ND; siz[13+d]=ND; }
    off[19]=NA+12*IV+NETHACK_DIR_HEADS*ND; siz[19]=NETHACK_SPELL_SLOTS;
    long hit[20]={0}, seen[20]={0}, n=0, allhit=0, usedhit=0, usedseen=0;
    double pmax[20]={0}, pchosen[20]={0};
    unsigned char* ob=malloc(OS); unsigned char* mk=malloc(MS); short act[32];
    while (fread(ob,1,OS,f)==(size_t)OS && fread(mk,1,MS,f)==(size_t)MS
           && fread(act,sizeof(short),NH,f)==(size_t)NH) {
        nethack_net_forward(net, ob);
        for (int i=0;i<MS;i++) if(!mk[i]) net->logits[i]=-1e9f;
        int verb = act[0], ok = 1;
        for (int h=0;h<20;h++) {
            int A=siz[h], base=off[h]; if (A<=0) continue;
            float mx=-1e30f; int am=0;
            for (int a=0;a<A;a++) if (net->logits[base+a]>mx){mx=net->logits[base+a];am=a;}
            double se=0; for(int a=0;a<A;a++) se+=exp((double)net->logits[base+a]-mx);
            pmax[h]+=1.0/se;
            if (act[h]>=0 && act[h]<A) pchosen[h]+=exp((double)net->logits[base+act[h]]-mx)/se;
            int same = (am==act[h]); seen[h]++; hit[h]+=same;
            // is this head actually consulted for the verb CUDA chose?
            int used = (h==0) || (h>=1&&h<=12 && NETHACK_VERBS[verb].head==h-1)
                    || (h>=13&&h<=18 && nethack_dir_head(verb)==h-13)
                    || (h==19 && verb==NETHACK_ACT_CAST);
            if (used) { usedseen++; usedhit+=same; if(!same) ok=0; }
        }
        allhit+=ok; n++;
    }
    printf("steps=%ld\n\n", n);
    const char* nm[20]={"verb","slot0","slot1","slot2","slot3","slot4","slot5","slot6","slot7","slot8","slot9","slot10","slot11",
                        "dir0","dir1","dir2","dir3","dir4","dir5","spell"};
    printf("  %-8s %5s  %9s %9s   %s\n", "head", "A", "agree", "ceiling", "p(CUDA choice)");
    for (int h=0;h<20;h++) if (seen[h]) printf("  %-8s %5d  %8.2f%% %8.2f%%   %.3f%s\n", nm[h], siz[h],
        100.0*hit[h]/seen[h], 100.0*pmax[h]/seen[h], pchosen[h]/seen[h],
        (100.0*hit[h]/seen[h] < 100.0*pmax[h]/seen[h] - 3.0) ? "   <-- below ceiling" : "");
    printf("\n  heads actually used for CUDA's verb : %.2f%%  (%ld/%ld)\n", 100.0*usedhit/usedseen, usedhit, usedseen);
    printf("  ALL used heads agree on a step      : %.2f%%  (%ld/%ld)\n", 100.0*allhit/n, allhit, n);
    return 0;
}
