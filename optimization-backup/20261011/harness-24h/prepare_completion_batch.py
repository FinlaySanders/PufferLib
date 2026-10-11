from pathlib import Path
import json
r=Path(__file__).resolve().parent;p=r/'source/src/env_pool.h';s=p.read_text()
s=s.replace('int sleep_tail, check_claim, buffer_lead;','int sleep_tail, check_claim, buffer_lead, batch_done;')
needle='static int ep_claim(EnvPool* p, EPRegion* r, int id) {'
helper='''static void ep_completed(EnvPool* p, EPRegion* r, int count) {
    int finished = __atomic_add_fetch(&r->done, count, __ATOMIC_RELEASE);
    if (p->sleep_tail && finished == r->count) {
        pthread_mutex_lock(&r->mu);
        pthread_cond_signal(&r->quiet);
        pthread_mutex_unlock(&r->mu);
    }
}

'''
assert s.count(needle)==1;s=s.replace(needle,helper+needle)
needle='''            int finished = __atomic_add_fetch(&r->done, 1, __ATOMIC_RELEASE);
            if (p->sleep_tail && finished == r->count) {
                pthread_mutex_lock(&r->mu);
                pthread_cond_signal(&r->quiet);
                pthread_mutex_unlock(&r->mu);
            }'''
assert s.count(needle)==1;s=s.replace(needle,'            if (!p->batch_done) ep_completed(p, r, 1);')
needle='''    return worked;
}
''';assert s.count(needle)==1
s=s.replace(needle,'''    if (p->batch_done && worked) ep_completed(p, r, worked);
    return worked;
}
''')
needle='    p->check_claim = getenv("PUF_POOL_CHECK_CLAIM") != NULL;'
s=s.replace(needle,needle+'\n    p->batch_done = getenv("PUF_POOL_DONE_BATCH") != NULL;');p.write_text(s)
n=r/'native_completion';n.mkdir(exist_ok=False)
h=s.replace('    EnvPool* p = w->pool;\n','''    EnvPool* p = w->pool;
    if (getenv("CPU_PIN")) {
        cpu_set_t cpus;CPU_ZERO(&cpus);CPU_SET(w->id<8?2*w->id:16+w->id-8,&cpus);
        assert(pthread_setaffinity_np(pthread_self(),sizeof(cpus),&cpus)==0);
    }
''');(n/'env_pool.h').write_text(h)
s=(r/'native_bounded/snapshot.c').read_text().replace('(focus>=0 && focus<=9)','(focus>=0 && focus<=12)')
s=s.replace('if(focus>=6) {','if(focus>=6 && focus<=9) {')
needle='    is_child=1;selected_focus=(focus==1);steps=case_steps;'
s=s.replace(needle,needle+'''
    unsetenv("PUF_POOL_DONE_BATCH");
    if(focus>=10) assert(setenv("PUF_POOL_DONE_BATCH","1",1)==0);
''')
needle='    if(focus==4 || focus==5) assert(setenv("PUF_POOL_CHECK_CLAIM","1",1)==0);'
s=s.replace(needle,needle+'''
    if(focus==11) assert(setenv("PUF_POOL_SLEEP","1",1)==0);
    if(focus==12) assert(setenv("PUF_BUFFER_LEAD","4",1)==0);
''');(n/'snapshot.c').write_text(s)
(n/'snapshot_test.py').write_text((r/'native_pool/snapshot_test.py').read_text())
cmd=json.loads((r/'native_bounded/compile_command.json').read_text());cmd=[x.replace(str(r/'native_bounded'),str(n)) for x in cmd];(n/'compile_command.json').write_text(json.dumps(cmd,indent=2))
s=(r/'bounded_pool_smoke.cpp').read_text().replace('mode<12','mode<16').replace('if(mode>=8) {','if(mode>=8 && mode<12) {')
s=s.replace('        unsetenv("PUF_BUFFER_LEAD");','''        unsetenv("PUF_POOL_DONE_BATCH");
        if(mode>=12)setenv("PUF_POOL_DONE_BATCH","1",1);
        unsetenv("PUF_BUFFER_LEAD");''')
s=s.replace('mode==7)setenv("PUF_POOL_SLEEP"','mode==7 || mode==13 || mode==15)setenv("PUF_POOL_SLEEP"')
s=s.replace('''        for(int i=0;i<buffers*count;i++)actual[i]=0;''','''        if(mode==14 || mode==15)setenv("PUF_BUFFER_LEAD","4",1);
        for(int i=0;i<buffers*count;i++)actual[i]=0;''')
(r/'completion_pool_smoke.cpp').write_text(s)
with (r/'LEDGER.md').open('a') as f:
 f.write('\n19. Batched pool completion publication: source currently performs one release RMW on the same region.done cacheline for every game (512updates/buffer), adjacent to region metadata. Only the final completion count is consumed. Prepare PUF_POOL_DONE_BATCH to publish each ep_claim callback total once after its work, preserving reader leases, release/acquire semantics and optional final condition signal. Suspected ceiling modest (outside-step CPU budget ~2%); possible coherence effects must be measured, not assumed. No game scheduling change within a claim. Prepared64case lifecycle/count smoke and CPU-only snapshot modes10=batch,11=batch+sleep,12=batch+lead4. Not built or timed; no active timing contaminated.\n')
print('Prepared batched completion candidate, no build/run.')
