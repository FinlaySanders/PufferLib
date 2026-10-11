from pathlib import Path
import json

root = Path(__file__).resolve().parent
old = Path('/puffertank/experiments/nethack-compact-state-20261008/fast_loop_20261009')
dest = root / 'native_pool'
dest.mkdir(exist_ok=False)
header = (root / 'source/src/env_pool.h').read_text()
needle = '    EnvPool* p = w->pool;\n'
pin = '''    if (getenv("CPU_PIN")) {
        int cpu = w->id < 8 ? 2*w->id : 16+w->id-8;
        cpu_set_t set; CPU_ZERO(&set); CPU_SET(cpu, &set);
        assert(pthread_setaffinity_np(pthread_self(), sizeof(set), &set) == 0);
    }
'''
assert header.count(needle) == 1
(dest / 'env_pool.h').write_text(header.replace(needle, needle + pin))
source = (old / 'snapshot.c').read_text()
source = source.replace('(focus==0 || focus==1 || focus==2)', '(focus>=0 && focus<=5)')
needle = '    is_child=1;selected_focus=(focus==1);steps=case_steps;'
assert source.count(needle) == 1
source = source.replace(needle, needle + '''
    unsetenv("PUF_POOL_SLEEP"); unsetenv("PUF_POOL_CHECK_CLAIM");
    if(focus==3 || focus==5) assert(setenv("PUF_POOL_SLEEP","1",1)==0);
    if(focus==4 || focus==5) assert(setenv("PUF_POOL_CHECK_CLAIM","1",1)==0);
''')
(dest / 'snapshot.c').write_text(source)
runner = (old / 'snapshot_test.py').read_text()
runner = runner.replace('d=Path(__file__).resolve().parent;r=d.parent',
    "d=Path(__file__).resolve().parent;r=Path('/puffertank/experiments/nethack-compact-state-20261008')")
runner = runner.replace("assert((focus==0 || focus==1 || focus==2)", "assert((focus>=0 && focus<=5)")
(dest / 'snapshot_test.py').write_text(runner)
command = json.loads((old / 'snapshot_compile_command.json').read_text())
command[command.index(str(old / 'snapshot.c'))] = str(dest / 'snapshot.c')
command[-1] = str(dest / 'snapshot')
(dest / 'compile_command.json').write_text(json.dumps(command, indent=2))
print('Prepared native CPU-only snapshot screen; no compilation or run yet.')
