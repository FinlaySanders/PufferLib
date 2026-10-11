from pathlib import Path
import json
r=Path(__file__).resolve().parent;p=r/'source/src/pufferl.cu';s=p.read_text()
needle='        int timing_stride=1,timing_phase=0;float timing_scale=1.0f;'
assert s.count(needle)==1
s=s.replace(needle,'''        int timing_stride = getenv("PUF_TIMING_STRIDE") ? atoi(getenv("PUF_TIMING_STRIDE")) : 1;
        assert(timing_stride > 0 && horizon % timing_stride == 0);
        int timing_phase = timing_round++ % timing_stride;
        float timing_scale = (float)timing_stride;''')
# The COPY total estimates both D2H and H2D using the same sampled iterations.
start=s.index('static void* vec_thread_main') if 'static void* vec_thread_main' in s else s.index('void* vec_thread_main')
end=s.index('// Fresh episodes + zero RNN carry.',start)
a=s[start:end];assert a.count('my_accum[PROF_COPY] += ms*timing_scale;')==3
a=a.replace('my_accum[PROF_COPY] += ms;','my_accum[PROF_COPY] += ms*timing_scale;')
s=s[:start]+a+s[end:];p.write_text(s)
p=r/'AFFINITY_SCREEN.json';x=json.loads(p.read_text());x.insert(-1,dict(kind='full',label='timing_stride16',binary='affinity_v12',env=dict(PUF_CUDA_WAIT='block',PUF_ROLLOUT_DETAIL=1,PUF_TIMING_STRIDE=16),args=['--epochs=80','--start=64']));p.write_text(json.dumps(x,indent=2))
with (r/'LEDGER.md').open('a') as f:
 f.write('\n18. Sampled rollout timing: current loop records model-start/model-end/copy-end/upload-start/upload-end events and queries elapsed times every step, even in already-captured inference. Existing profile shows substantial CPU submission duration (observer-affected, not a speed estimate). Prepare PUF_TIMING_STRIDE=16: sample1/16steps, rotate phase each horizon, scale model/copy diagnostics; environment and outer-batch clocks remain exact/every-step. Same graphs/actions/syncs/computation. This changes profiling estimates, explicitly separate from simulation/model speed. Not built/tested.\n')
print('Prepared sampled profiling, default exact per-step timing unchanged.')
