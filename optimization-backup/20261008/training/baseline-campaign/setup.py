from pathlib import Path
import shutil,os,subprocess
r=Path(__file__).parent;old=Path('/puffertank/experiments/nethack-size-profile-20260918/source');s=r/'source';s.mkdir()
for n in ['src','config']:shutil.copytree(old/n,s/n)
shutil.copy2(old/'build.sh',s/'build.sh')
for n in ['ocean','resources','vendor','raylib-5.5_linux_amd64']:(s/n).symlink_to((old/n).resolve(),target_is_directory=True)
p=s/'src/pufferl.cu';t=p.read_text()
t=t.replace('    int* env_starts;', '    double perf_completed[4];\n    int* env_starts;')
t=t.replace('        envs[num_envs].rng = num_envs;', '''        envs[num_envs].rng = getenv("PUF_BATCH_REPLAY")
            ? (num_envs / (total_agents / 4)) * 128 + (num_envs % (total_agents / 4)) % 128
            : num_envs;''')
a=t.index('static void* vec_thread_main');b=t.index('\n// Fresh episodes',a);part=t[a:b]
part=part.replace('    __atomic_store_n(state, BUF_WAITING, __ATOMIC_SEQ_CST);\n','',1)
part=part.replace('size_t perf_frame_bytes = (size_t)apb * NUM_ATNS * sizeof(float);','size_t perf_frame_bytes = (size_t)128 * NUM_ATNS * sizeof(float);\n    assert(apb % 128 == 0);')
oldline='                memcpy(&vec->actions[agent_start * NUM_ATNS],perf_replay+perf_replay_pos,perf_frame_bytes);'
assert oldline in part
part=part.replace(oldline,'''                for(int rep=0;rep<apb/128;rep++)
                    memcpy(&vec->actions[(agent_start+rep*128)*NUM_ATNS],perf_replay+perf_replay_pos,perf_frame_bytes);''')
needle='    struct timespec t0, t1;'
part=part.replace(needle,'''    if (getenv("PUF_BATCH_REPLAY")) {
        assert(perf_replay && vec->buffers==4);
        for(int t=0;t<24*512;t++) {
            assert(perf_replay_pos+perf_frame_bytes<=perf_replay_size);
            for(int rep=0;rep<apb/128;rep++)
                memcpy(&vec->actions[(agent_start+rep*128)*NUM_ATNS],perf_replay+perf_replay_pos,perf_frame_bytes);
            perf_replay_pos+=perf_frame_bytes;
            memset(&vec->rewards[agent_start],0,apb*sizeof(float));
            memset(&vec->terminals[agent_start],0,apb*sizeof(float));
            ep_run(vec->env_pool,buf,env_start,env_count);
        }
        cpu_upload(pufferl,agent_start,apb,stream);
        cudaStreamSynchronize(stream);
        fprintf(stderr,"BATCH_WARM buffer=%d game_steps=%d\\n",buf,24*512);
    }
    __atomic_store_n(state, BUF_WAITING, __ATOMIC_SEQ_CST);
'''+needle)
part=part.replace('        __atomic_store_n(state, BUF_WAITING, __ATOMIC_SEQ_CST);', '        vec->perf_completed[buf]=wall_clock();\n        __atomic_store_n(state, BUF_WAITING, __ATOMIC_SEQ_CST);')
t=t[:a]+part+t[b:]
# New benchmark window starts after both GPU graph slots have warmed.
t=t.replace('epoch==32','epoch==8').replace('epoch==38','epoch==14')
t=t.replace('        double perf_epoch_start = wall_clock();', '        double perf_epoch_start = wall_clock();\n        double perf_ppo_done=0;')
t=t.replace('            train_impl(pufferl, &train_src);', '            train_impl(pufferl, &train_src);\n            perf_ppo_done=wall_clock();')
start=t.index('        if (epoch==31 || epoch==37 || epoch==train_epochs-1) {')
end=t.index('        nvtxMarkA(age_marker);',start)
t=t[:start]+'''        if (epoch==7 || epoch==13 || epoch==train_epochs-1) {
            uint64_t hash=1469598103934665603ULL;
            const unsigned char* bytes=(const unsigned char*)pufferl->vec->observations;
            size_t chunk=(size_t)128*OBS_SIZE*sizeof(obs_t);
            int apb=pufferl->hypers.total_agents/4;
            for(int b=0;b<4;b++) {
                const unsigned char* first=bytes+(size_t)b*apb*OBS_SIZE*sizeof(obs_t);
                for(int rep=1;rep<apb/128;rep++) assert(memcmp(first,first+rep*chunk,chunk)==0);
                for(size_t j=0;j<chunk;j++) { hash^=first[j];hash*=1099511628211ULL; }
            }
            fprintf(stderr,"BATCH_PROOF epoch=%ld obs=%016llx params=%ld copies=%d\\n",epoch,(unsigned long long)hash,(long)numel(pufferl->policies[0].master_weights.shape),pufferl->hypers.total_agents/512);
        }
        size_t memfree=0,memtotal=0;cudaMemGetInfo(&memfree,&memtotal);
        double last_rollout=0;
        for(int b=0;b<4;b++) last_rollout=fmax(last_rollout,pufferl->vec->perf_completed[b]);
        fprintf(stderr,"BATCH_PERF epoch=%ld seconds=%.9f rollout_tail=%.9f ppo_tail=%.9f used_mib=%.1f batch=%d mb=%d updates=%d\\n",epoch,perf_epoch_seconds,
            fmax(0.,last_rollout-perf_ppo_done),fmax(0.,perf_ppo_done-last_rollout),
            (double)(memtotal-memfree)/(1024.*1024.),pufferl->hypers.total_agents*pufferl->hypers.horizon,pufferl->hypers.minibatch_size,
            (int)(pufferl->hypers.replay_ratio*pufferl->hypers.total_agents*pufferl->hypers.horizon/pufferl->hypers.minibatch_size));
'''+t[end:]
p.write_text(t)
with (r/'build.log').open('w') as f:subprocess.run(['./build.sh','nethack','puffer_batch'],cwd=s,env=dict(os.environ,NVCC_EXTRA='-DPUF_ENV_POOL -DPUF_PERF_LOAD -DPUF_HEAD_SAMPLER'),stdout=f,stderr=subprocess.STDOUT,check=True)
print('BUILD_DONE',flush=True)
