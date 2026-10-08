from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/pufferl.cu';s=p.read_text();a=s.index('static void* vec_thread_main');b=s.index('// Fresh episodes',a);t=s[a:b]
t=t.replace('    while (1) {','    int timing_round=0;\n    while (1) {',1)
# Find actual loop spelling if above did not match.
if 'int timing_round=0;' not in t:
 pos=t.index('    __atomic_store_n(state, BUF_WAITING, __ATOMIC_SEQ_CST);');t=t[:pos]+'    int timing_round=0;\n'+t[pos:]
t=t.replace('''        int h2d_pending = 0;
        for (int t = 0; t < horizon; t++) {''','''        int h2d_pending = 0;
#ifdef PUF_SAMPLE_TIMING
        int timing_stride=min(16,horizon), timing_phase=timing_round++%timing_stride;
        float timing_scale=(float)horizon/((horizon-1-timing_phase)/timing_stride+1);
#else
        int timing_stride=1,timing_phase=0;float timing_scale=1.0f;
#endif
        for (int t = 0; t < horizon; t++) {
            bool timing_sample=t%timing_stride==timing_phase;''')
for name in ['MODEL_START','MODEL_END','COPY_END','H2D_START','H2D_END']:
 t=t.replace('            cudaEventRecord(ev['+name+'], stream);','            if(timing_sample) cudaEventRecord(ev['+name+'], stream);')
old='''            cudaEventElapsedTime(&ms, ev[MODEL_START], ev[MODEL_END]);
            my_accum[PROF_MODEL] += ms;
            cudaEventElapsedTime(&ms, ev[MODEL_END], ev[COPY_END]);
            my_accum[PROF_COPY] += ms;'''
new='''            if(timing_sample) {
                cudaEventElapsedTime(&ms, ev[MODEL_START], ev[MODEL_END]);
                my_accum[PROF_MODEL] += ms*timing_scale;
                cudaEventElapsedTime(&ms, ev[MODEL_END], ev[COPY_END]);
                my_accum[PROF_COPY] += ms*timing_scale;
            }'''
assert old in t;t=t.replace(old,new)
t=t.replace('my_accum[PROF_COPY] += ms;','my_accum[PROF_COPY] += ms*timing_scale;')
t=t.replace('            h2d_pending = 1;','            h2d_pending = timing_sample;')
assert 'timing_sample=t%' in t and t.count('if(timing_sample) cudaEventRecord')==5
s=s[:a]+t+s[b:];p.write_text(s)
