from pathlib import Path
import subprocess,shutil,json
root=Path('/workspace/experiments/nethack-landmarks-20260914')
source=Path('/workspace/pufferlib_fix')
root.mkdir(exist_ok=False)
tree=root/'source'
subprocess.run(['git','clone','--shared',str(source),str(tree)],check=True)
engine=tree/'vendor/fast-nle'
if engine.exists():shutil.rmtree(engine)
subprocess.run(['git','clone','--shared',str(source/'vendor/fast-nle'),str(engine)],check=True)
# Use the exact campaign engine revision, not a later release.
assert subprocess.check_output(['git','-C',str(engine),'rev-parse','HEAD'],text=True).strip()=='f7d8749ab1985349425f4c5bd11f70ee2e914854'
for name in ('resources','raylib-5.5_linux_amd64'):
 p=tree/name
 if p.exists():
  if p.is_dir():shutil.rmtree(p)
  else:p.unlink()
 p.symlink_to(source/name,target_is_directory=True)
f=engine/'include/nletypes.h';s=f.read_text();s=s.replace('} nle_ctx_t;','    int landmark_visits[4]; /* medusa, castle, their assigned depths */\n} nle_ctx_t;');f.write_text(s)
f=engine/'src/do.c';s=f.read_text();s=s.replace('#include "hack.h"','#include "hack.h"\nextern void nle_record_landmark_entry(void);',1);needle='    assign_level(&u.uz, newlevel);';assert s.count(needle)==1;s=s.replace(needle,needle+'\n    nle_record_landmark_entry();');f.write_text(s)
f=engine/'src/nle.c';s=f.read_text();s+='''
/* Evaluation-only counters; never added to observations or policy inputs. */
void nle_record_landmark_entry(void) {
    if (Is_medusa_level(&u.uz)) current_nle_ctx->landmark_visits[0] = 1;
    if (Is_stronghold(&u.uz)) current_nle_ctx->landmark_visits[1] = 1;
    current_nle_ctx->landmark_visits[2] = depth(&medusa_level);
    current_nle_ctx->landmark_visits[3] = depth(&stronghold_level);
}
int nle_landmark_stat(nle_ctx_t *ctx, int index) {
    return ctx->landmark_visits[index];
}
'''
# Record assigned depths even in games ending before their first transition.
needle='    obs->done = nle->done;';start=s.index('nle_start(nle_obs');pos=s.index(needle,start)+len(needle)
s=s[:pos]+'''\n    nle->landmark_visits[2] = depth(&medusa_level);
    nle->landmark_visits[3] = depth(&stronghold_level);'''+s[pos:];f.write_text(s)
f=tree/'ocean/nethack/nethack.h';s=f.read_text();needle='extern void nle_end(nle_ctx_t*);';assert needle in s;s=s.replace(needle,needle+'\nextern int nle_landmark_stat(nle_ctx_t*, int);')
old='"%ld %d %ld %d %d %d %d %d %ld %d %d\\n"';assert s.count(old)==1;s=s.replace(old,'"%ld %d %ld %d %d %d %d %d %ld %d %d %d %d %d %d\\n"')
needle='env->obs.internal ? env->obs.internal[10] : 0);';assert s.count(needle)==1;s=s.replace(needle,'env->obs.internal ? env->obs.internal[10] : 0, nle_landmark_stat(env->ctx, 0), nle_landmark_stat(env->ctx, 1), nle_landmark_stat(env->ctx, 2), nle_landmark_stat(env->ctx, 3));');f.write_text(s)
base=Path('/workspace/experiments/nethack-depth-2b-20260914')
shutil.copytree(base/'config',root/'config');(root/'dat').symlink_to(base/'dat',target_is_directory=True)
(root/'resources').symlink_to(source/'resources',target_is_directory=True)
(root/'source.patch').write_bytes(subprocess.check_output(['git','-C',str(tree),'diff']))
(root/'engine.patch').write_bytes(subprocess.check_output(['git','-C',str(engine),'diff']))
print(root,flush=True)
subprocess.run(['cmake','-S',str(engine),'-B',str(engine/'build'),'-DCMAKE_BUILD_TYPE=Release'],check=True)
subprocess.run(['cmake','--build',str(engine/'build'),'--target','nethack','-j32'],check=True)
subprocess.run(['bash','build.sh','nethack'],cwd=tree,check=True)
shutil.copy2(tree/'puffer',root/'puffer');(root/'lib').mkdir();shutil.copy2(engine/'build/libnethack.so',root/'lib/libnethack.so')
(root/'BUILD_DONE').write_text('ok\n')
