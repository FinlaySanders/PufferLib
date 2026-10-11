from pathlib import Path
import json
import subprocess

r=Path(__file__).resolve().parent
d=r/'current_workload_pgo'
assert (d/'STOPPED_PROFILE.json').exists()
assert not list((d/'profiles').glob('*nethack.dir*.gcda')), 'Aborted collection unexpectedly wrote engine feedback'
text=(r/'native_pool/snapshot.c').read_text()
old='active_apb<=apb && active_apb>=128 && active_apb%128==0'
assert text.count(old)==1
text=text.replace(old,'active_apb<=apb && active_apb>=1')
old='for(long t=begin;t<begin+count;t+=increment) {ticks[b]=t;'
assert text.count(old)==1
text=text.replace(old,'for(long t=begin;t<begin+count;t+=increment) {if(b==0 && t%1024==0) {fprintf(stderr,"PROFILE_PROGRESS decision=%ld of%ld\\n",t,begin+count);fflush(stderr);}ticks[b]=t;')
(d/'collector.c').write_text(text)
command=json.loads((r/'native_pool/compile_command.json').read_text())
command[command.index(str(r/'native_pool/snapshot.c'))]=str(d/'collector.c')
command.insert(1,'-I'+str(r/'native_pool'))
command[-1]=str(d/'collector')
(d/'collector_command.json').write_text(json.dumps(command,indent=2))
with (d/'collector_build.log').open('w') as f:
    subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True)
# Preserve the complete initial recipe and failure; resume from its generated
# library with a smaller profile-only harness. Native timing harness is unchanged.
script=(r/'build_current_workload_pgo.py').read_text()
script=script.replace('assert not d.exists()','assert d.exists()')
script=script.replace("shutil.copytree(base/'source',s)\nprof.mkdir()\nrows=[]",
    "rows=json.loads((d/'commands.json').read_text())")
start=script.index("build('generate',")
end=script.index("actions=Path(",start)
script=script[:start]+script[end:]
script=script.replace("'distinct_current_streams':512", "'distinct_current_streams':64")
script=script.replace("invoke('current_profile',[r/'native_pool/snapshot','512','24','8064','128',actions]",
    "invoke('current_profile64',[d/'collector','64','0','8064','128',actions]")
script=script.replace("'current_decisions_per_stream':'[0,8192); timed native screen begins at8192'",
    "'current_decisions_per_stream':'[0,8192); timed native screen begins at8192', 'selection':'first16streams from each of4teacher groups;4direct submitters, no pool workers'")
assert 'current_profile64' in script
(d/'resumed_recipe.py.txt').write_text(script)
exec(compile(script,str(r/'build_current_workload_pgo.py'),'exec'),{'__file__':str(r/'build_current_workload_pgo.py'),'__name__':'__main__'})
