from pathlib import Path
import difflib
p=Path(__file__).parent/'source/src/env_pool.h';s=p.read_text();before=s
s=s.replace('int active, readers, start, count, done;','int active, readers, start, count, done;\n    unsigned long generation;')
s=s.replace('int workers, buffers, stop, buffer_focus;','int workers, buffers, stop, buffer_focus, buffer_fair;')
s=s.replace('        int repeat_ready_scan = 0;','''        int order[64];
        if(p->buffer_fair) {
            unsigned long generation[64];
            for(int i=0;i<p->buffers;i++) {
                EPRegion* r=&p->region[i];
                pthread_mutex_lock(&r->mu);
                generation[i]=r->active?r->generation:~0UL;
                pthread_mutex_unlock(&r->mu);
                order[i]=i;
            }
            for(int i=1;i<p->buffers;i++) {
                int key=order[i],j=i;
                while(j>0 && generation[order[j-1]]>generation[key]) {
                    order[j]=order[j-1];j--;
                }
                order[j]=key;
            }
        }
        int repeat_ready_scan = 0;''')
s=s.replace('EPRegion* r = &p->region[(p->buffer_focus ? k : w->id + k) % p->buffers];','EPRegion* r = &p->region[p->buffer_fair?order[k]:(p->buffer_focus ? k : w->id + k) % p->buffers];')
s=s.replace('    p->buffer_focus = getenv("PUF_BUFFER_FOCUS") != NULL;','''    p->buffer_fair = getenv("PUF_BUFFER_FAIR") != NULL;
    if(p->buffer_fair) assert(buffers<=64);
    p->buffer_focus = p->buffer_fair || getenv("PUF_BUFFER_FOCUS") != NULL;''')
s=s.replace('    r->start = start; r->count = count;','    r->start = start; r->count = count; r->generation++;')
p.write_text(s)
(p.parents[2]/'fair_pool.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='focus/env_pool.h',tofile='fair/env_pool.h')))
