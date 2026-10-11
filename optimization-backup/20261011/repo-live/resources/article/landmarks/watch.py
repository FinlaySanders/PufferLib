from pathlib import Path
import subprocess,time,sys
p=Path(__file__).resolve().parent
for _ in range(240):
 r=subprocess.run([sys.executable,str(p/'refresh.py')])
 if r.returncode==0:
  (p/'RENDER_DONE').write_text(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())+'\n')
  break
 if r.returncode not in (3,255):raise SystemExit(r.returncode)
 time.sleep(30)
else:raise SystemExit('Landmark result wait exceeded two hours')
