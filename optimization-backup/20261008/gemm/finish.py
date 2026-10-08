from pathlib import Path
import os,select,subprocess,json
r=Path(__file__).parent
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  args=(proc/'cmdline').read_bytes().split(b'\0')
  if str(r/'strict.py').encode() in args:
   fd=os.pidfd_open(int(proc.name));select.select([fd],[],[]);os.close(fd)
 except (FileNotFoundError,ProcessLookupError,PermissionError):pass
for name in ['strict','lt','workspace-d']:assert (r/'training'/name/'result.json').exists(),name
print('PROFILE',flush=True);subprocess.run(['python',str(r/'profile_strict.py')],check=True)
# One additional strict arm confirms the result after profiling/tuning.
print('STRICT_REPEAT',flush=True);subprocess.run(['python',str(r/'train_lt.py'),'strict-repeat'],check=True)
print('FINISHED',flush=True)
