from pathlib import Path
r=Path(__file__).resolve().parent
p=r/'source/src/env_pool.h';s=p.read_text()
s=s.replace('    int sleep_tail, check_claim;','    int sleep_tail, check_claim, buffer_lead;')
s=s.replace('        if(p->buffer_fair) {','        if(p->buffer_fair || p->buffer_lead >= 0) {')
s=s.replace('''            unsigned long generation[64];
            for(int i=0;i<p->buffers;i++) {''','''            unsigned long generation[64], minimum = ~0UL;
            for(int i=0;i<p->buffers;i++) {''')
s=s.replace('''                generation[i]=r->active?r->generation:~0UL;
                pthread_mutex_unlock(&r->mu);''','''                unsigned long current = r->generation;
                generation[i]=r->active?current:~0UL;
                if (current < minimum) minimum = current;
                pthread_mutex_unlock(&r->mu);''')
needle='''            for(int i=1;i<p->buffers;i++) {
                int key=order[i],j=i;'''
assert s.count(needle)==1
s=s.replace(needle,'''            if (p->buffer_lead >= 0) {
                for (int i=0;i<p->buffers;i++) {
                    if (generation[i] != ~0UL)
                        generation[i] = (generation[i] > minimum + p->buffer_lead)
                            ? generation[i] + p->buffers : (unsigned long)i;
                }
            }
            for(int i=1;i<p->buffers;i++) {
                int key=order[i],j=i;''')
s=s.replace('p->region[p->buffer_fair?order[k]:','p->region[(p->buffer_fair || p->buffer_lead >= 0)?order[k]:')
needle='''    p->buffer_fair = getenv("PUF_BUFFER_FAIR") != NULL;
    if(p->buffer_fair) assert(buffers<=64);
    p->buffer_focus = p->buffer_fair || getenv("PUF_BUFFER_FOCUS") != NULL;'''
assert s.count(needle)==1
s=s.replace(needle,'''    p->buffer_fair = getenv("PUF_BUFFER_FAIR") != NULL;
    p->buffer_lead = getenv("PUF_BUFFER_LEAD") ? atoi(getenv("PUF_BUFFER_LEAD")) : -1;
    if(p->buffer_fair || p->buffer_lead >= 0) assert(buffers<=64);
    p->buffer_focus = p->buffer_fair || p->buffer_lead >= 0 || getenv("PUF_BUFFER_FOCUS") != NULL;''')
p.write_text(s)
p=r/'pool_smoke.cpp';s=p.read_text().replace('mode<8','mode<12')
s=s.replace('''        unsetenv("PUF_BUFFER_FOCUS");unsetenv("PUF_BUFFER_FAIR");''','''        unsetenv("PUF_BUFFER_FOCUS");unsetenv("PUF_BUFFER_FAIR");
        unsetenv("PUF_BUFFER_LEAD");
        if(mode>=8) {char value[8];snprintf(value,sizeof(value),"%d",1<<(mode-8));setenv("PUF_BUFFER_LEAD",value,1);}''')
(r/'bounded_pool_smoke.cpp').write_text(s)
# Dedicated CPU-only snapshot source; no compiled binary yet.
n=r/'native_bounded';n.mkdir(exist_ok=False)
header=(r/'source/src/env_pool.h').read_text()
needle='    EnvPool* p = w->pool;\n'
header=header.replace(needle,needle+'''    if (getenv("CPU_PIN")) ep_pin_cpu(w->id < 8 ? 2*w->id : 16+w->id-8);
''')
(n/'env_pool.h').write_text(header)
s=(r/'native_pool/snapshot.c').read_text().replace('(focus>=0 && focus<=5)','(focus>=0 && focus<=9)')
needle='    is_child=1;selected_focus=(focus==1);steps=case_steps;'
s=s.replace(needle,needle+'''
    unsetenv("PUF_BUFFER_LEAD");
    if(focus>=6) {char value[8];snprintf(value,sizeof(value),"%d",1<<(focus-6));assert(setenv("PUF_BUFFER_LEAD",value,1)==0);}
''')
(n/'snapshot.c').write_text(s)
(n/'snapshot_test.py').write_text((r/'native_pool/snapshot_test.py').read_text())
import json
cmd=json.loads((r/'native_pool/compile_command.json').read_text());cmd=[x.replace(str(r/'native_pool'),str(n)) for x in cmd]
(n/'compile_command.json').write_text(json.dumps(cmd,indent=2))
with (r/'LEDGER.md').open('a') as f:
 f.write('\n17. Bounded buffer lead: fixed-priority rescan gained nativeCPU but caused a slow last buffer; generation-fair scheduling removed that imbalance but was neutral. Prepare bounded priority (PUF_BUFFER_LEAD=1/2/4/8): prefer low-numbered ready buffers while their generations are within a small lead of the slowest, then prioritize laggards. No cohort barrier and allbuffers remain runnable. Hypothesis is preserving useful locality without unlimited head-start/straggler cost. Reader leases/claim counters unchanged. Prepared native snapshot variants and48case callback smoke; not compiled or measured.\n')
print('Prepared bounded ready-buffer priority, isolated smoke and native harness.')
