from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/nethack_sampler.cuh';s=p.read_text()
s=s.replace('__shared__ int chosen[NUM_ATNS];','''__shared__ int chosen[NUM_ATNS];
#ifdef PUF_SAMPLER_SHARED
    __shared__ float caches[NUM_ATNS][PPO_MAX_HEAD_A];
#endif''')
s=s.replace('float cache[PPO_MAX_HEAD_A];','''#ifdef PUF_SAMPLER_SHARED
        float* cache=caches[h];
#else
        float cache[PPO_MAX_HEAD_A];
#endif''')
p.write_text(s)
