from pathlib import Path
import json,difflib,shutil
r=Path('.')
p=r/'source/src/pufferl.cu';old=p.read_text();s=old
s=s.replace('struct VecEnv {', '#include "env_pages.h"\n\nstruct VecEnv {\n    size_t env_mapping_bytes;',1)
s=s.replace('    Env* envs = (Env*)calloc(total_agents, sizeof(Env));','''    int env_pages = getenv("PUF_ENV_PAGES") ? atoi(getenv("PUF_ENV_PAGES")) : 0;
    Env* envs = (Env*)puf_env_array_allocate(total_agents, sizeof(Env), env_pages, &vec->env_mapping_bytes);''',1)
s=s.replace('    envs = (Env*)realloc(envs, num_envs * sizeof(Env));','    if (!vec->env_mapping_bytes) envs = (Env*)realloc(envs, num_envs * sizeof(Env));',1)
needle='''#ifdef MY_VEC_CLOSE
    my_vec_close(vec->envs);
#endif'''
assert s.count(needle)==1
s=s.replace(needle,needle+'''
    if (vec->env_mapping_bytes) {
        puf_env_array_free(vec->envs, vec->env_mapping_bytes);
        vec->envs = NULL;
        vec->env_mapping_bytes = 0;
    }''',1)
assert s!=old;p.write_text(s)
(r/'ENV_PAGES.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='src/pufferl.cu',tofile='src/pufferl.cu')))
p=r/'build.py';s=p.read_text().replace("'src/env_pool.h'","'src/env_pool.h','src/env_pages.h'");p.write_text(s)
env=json.loads((r/'PRIORITY_CANDIDATE.json').read_text())['environment'];env.pop('PUF_ROLLOUT_DETAIL',None)
for title,args,cases in [('SMOKE',['--epochs=4','--start=1'],[('base',0),('aligned',1),('huge',2)]),('FULL',['--epochs=80','--start=64'],[('base_a',0),('aligned',1),('huge',2),('base_b',0)])]:
 jobs=[dict(label='env_pages_'+title.lower()+'_'+name,kind='full',binary='env_pages_v36',env=dict(env,PUF_ENV_PAGES=mode),args=args) for name,mode in cases]
 (r/('ENV_PAGES_'+title+'.json')).write_text(json.dumps(jobs,indent=2))
