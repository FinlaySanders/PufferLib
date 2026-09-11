// Control: the same CPU forward pass the challenge binding uses, but on the FORK
// engine. Any gap between this and the CUDA cert is the CPU policy, not the
// reconstruction or the challenge interface.
#define main nh_demo_main
#include "ocean/nethack/nethack.c"
#undef main

int main(int argc, char** argv) {
    const char* wpath = argc > 1 ? argv[1] : "resources/nethack/nethack_t1122_2B_weights.bin";
    int want = argc > 2 ? atoi(argv[2]) : 40;
    Weights* w = load_weights((char*)wpath);
    if (!w) { fprintf(stderr, "no weights %s\n", wpath); return 1; }
    NethackNet* net = make_nethack_net(w);
    Nethack env;
    nethack_color_sink = demo_colors; nethack_invstr_sink = demo_inv_strs;
    const char* s = getenv("NH_SEED");
    srand(s ? (unsigned)strtoul(s, NULL, 10) : (unsigned)time(NULL));
    env_open(&env);
    float acts[DEMO_NUM_HEADS];
    float ep_score = 0, ep_len = 0, ep_depth = 0, ep_xp = 0, ep_gt = 0;
    long done = 0;
    int pin = getenv("NH_PIN_RAND") != NULL; // same experiment every episode: see nhc_direct.py
    int zst = getenv("NH_ZERO_STATE") != NULL;
    int sl = getenv("NH_STATELESS") != NULL; // zero the recurrent state before EVERY forward, as the CUDA rollout effectively does
    if (pin) srand(0);
    while (done < want) {
        long prev_score = (long)env.log.score;
        if (sl) memset(net->mingru->state, 0, (size_t)net->num_layers * net->hidden_size * sizeof(float));
        demo_step_once(net, &env, acts, &ep_score, &ep_len, &ep_depth, &ep_xp, &ep_gt);
        if (env.agents[0].terminals[0] > 0.5f) {
            done++;
            printf("%ld %ld %ld\n", (long)(env.log.score - prev_score) >= 0 ? (long)ep_score - prev_score : 0,
                   (long)env.blstats[NLE_BL_TIME], (long)env.blstats[NLE_BL_DEPTH]);
            fflush(stdout);
            if (pin) srand(0);
            if (zst) memset(net->mingru->state, 0, (size_t)net->num_layers * net->hidden_size * sizeof(float));
        }
    }
    env_close(&env);
    return 0;
}
