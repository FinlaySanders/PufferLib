"""Seeded timing diagnostic using actual gym.make/step, NOT a scored certificate."""
import os,sys,time,json,re
os.sched_setaffinity(0,{int(os.environ.get('BENCH_CPU','0'))})
import gym,nle
from pathlib import Path
name,total,limit,trace=sys.argv[1:]; total=int(total);limit=int(limit)
lines=Path(name).read_text().splitlines()
meta=next(l for l in lines if l.startswith('meta core='));core,disp=map(int,re.search(r'core=(\d+) disp=(\d+)',meta).groups())
options=next(l[13:] for l in lines if l.startswith('meta options=')).split(',')
player=next(x[5:] for x in options if x.startswith('name:')); options=[x for x in options if not x.startswith('name:')]
keys=[int(l.split()[1]) for l in lines if l.startswith('step ')][:limit]
ORDER=['glyphs','chars','colors','specials','blstats','message','inv_glyphs','inv_strs','inv_letters','inv_oclasses','tty_chars','tty_colors','tty_cursor','misc']
def hobs(obs):
 h=14695981039346656037
 for key in ORDER:
  for v in obs[key].tobytes(): h=((h^v)*1099511628211)&0xffffffffffffffff
 return f'{h:016x}'
t=time.perf_counter();envs=[];start_turns=[]
for i in range(total):
 env=gym.make('NetHackChallenge-v0',character=player.split('-',1)[1],options=options,savedir=None)
 # Challenge deliberately disallows seeding. For this reproducible performance
 # diagnostic only, seed its native object before reset; no source modification.
 env.unwrapped.nethack._pynethack.set_initial_seeds(core,disp,False)
 obs=env.reset();envs.append(env);start_turns.append(int(obs['blstats'][20]))
init=time.perf_counter()-t
mapping={int(a):i for i,a in enumerate(envs[0].unwrapped.actions)}
actions=[mapping[k] for k in keys]
stream=open(trace,'w') if trace!='-' else None
if os.environ.get('BENCH_BARRIER'):
 print('READY',flush=True);sys.stdin.readline()
t=time.perf_counter()
for k,action in enumerate(actions):
 for env in envs:
  obs,reward,done,info=env.step(action)
  if done: raise RuntimeError(f'unexpected termination {k}')
  if stream:stream.write(f'{k} {hobs(obs)} {int(obs["blstats"][20])} {int(obs["blstats"][9])}\n')
elapsed=time.perf_counter()-t
obses=[env.unwrapped._get_observation(env.unwrapped.last_observation) for env in envs]
hashes=[hobs(o) for o in obses]
assert len(set(hashes))==1
print(json.dumps(dict(calls=total*len(actions),seconds=elapsed,sps=total*len(actions)/elapsed,final_hash=hashes[0],turn_advances=sum(int(o['blstats'][20])-start for o,start in zip(obses,start_turns)),final_turn=int(obses[0]['blstats'][20]),final_score=int(obses[0]['blstats'][9]),init_seconds=init)),flush=True)
if stream:stream.close()
for env in envs:env.close()
