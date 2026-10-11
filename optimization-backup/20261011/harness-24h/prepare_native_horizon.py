from pathlib import Path
import json,difflib,hashlib
r=Path(__file__).resolve().parent;d=r/'native_pool';old=(d/'snapshot.c').read_text();s=old
start=s.index('static void rounds(EnvPool* pool,long begin,long count) {');end=s.index('\nint main(',start)
replacement=r'''static void rounds(EnvPool* pool,long begin,long count) {
 int increment=measured?burst:warm_burst;assert(count%increment==0);int width=measured?active_apb:apb;
 int period=measured && getenv("CPU_HORIZON_BARRIER")?atoi(getenv("CPU_HORIZON_BARRIER")):0;
 assert(period>=0 && (!period || period%increment==0));
#pragma omp parallel num_threads(buffers)
 {
  int b=omp_get_thread_num();
  if(getenv("CPU_PIN")){cpu_set_t set;CPU_ZERO(&set);CPU_SET(1+2*b,&set);assert(pthread_setaffinity_np(pthread_self(),sizeof(set),&set)==0);}
  if(period) {
   for(long block=begin;block<begin+count;block+=period) {
    long stop=block+period;if(stop>begin+count)stop=begin+count;
    for(long t=block;t<stop;t+=increment) {ticks[b]=t;if(pool)ep_run(pool,b,b*apb,width);else for(int i=b*apb;i<b*apb+width;i++)step_one(NULL,i);}
#pragma omp barrier
   }
  } else {
   for(long t=begin;t<begin+count;t+=increment) {ticks[b]=t;if(pool)ep_run(pool,b,b*apb,width);else for(int i=b*apb;i<b*apb+width;i++)step_one(NULL,i);}
  }
 }
}'''
s=s[:start]+replacement+s[end:]
s=s.replace('(focus>=0 && focus<=5) && case_steps>0','((focus>=0 && focus<=5) || focus==20 || focus==21) && case_steps>0',1)
s=s.replace('is_child=1;selected_focus=(focus==1);steps=case_steps;', '''is_child=1;selected_focus=(focus==1 || focus==21);steps=case_steps;
    unsetenv("CPU_HORIZON_BARRIER");
    if(focus==20 || focus==21)assert(setenv("CPU_HORIZON_BARRIER","128",1)==0);''',1)
assert s!=old;(d/'snapshot_horizon.c').write_text(s)
(r/'NATIVE_HORIZON.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='snapshot.c',tofile='snapshot_horizon.c')))
cmd=json.loads((d/'compile_command.json').read_text());cmd[cmd.index(str(d/'snapshot.c'))]=str(d/'snapshot_horizon.c');cmd[-1]=str(d/'snapshot_horizon')
(d/'horizon_compile_command.json').write_text(json.dumps(cmd,indent=2))
p=d/'snapshot_test.py';t=p.read_text();t=t.replace('pin=True,warm=8192):','pin=True,warm=8192,binary_override=None):',1);t=t.replace("binary=d/('snapshot_proof' if proof else 'snapshot')","binary=Path(binary_override) if binary_override else d/('snapshot_proof' if proof else 'snapshot')",1);p.write_text(t);compile(t,str(p),'exec')
(r/'NATIVE_HORIZON_SOURCE.json').write_text(json.dumps({'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'description':'Isolated diagnostic, no engine change. Modes20/21 add same128step rendezvous to allfour buffers;21 alsofocus. Original modes0/1 unchanged. Warm8320 andmeasure1920 align fullpipeline64..78prefetch boundaries.'},indent=2))
print('Prepared native barrier diagnostic; build only when all timing jobs finish')
