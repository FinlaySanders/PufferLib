import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):
    os.environ[key]='1'
import argparse, json, time, traceback, multiprocessing as mp
from pathlib import Path
import gym
import nle
from autoascend.env_wrapper import EnvWrapper

class ObservedChallenge:
    """Expose AutoAscend's action mapping and bookkeeping; game access is reset/step."""
    def __init__(self):
        self.raw=gym.make('NetHackChallenge-v0')
        self._actions=list(self.raw.unwrapped.actions)
        self._steps=0
        self.obs=None
        self.done=False
        self.info={}
        self.live_score=0
        self.live_turns=0
    def reset(self):
        self.obs=self.raw.reset()
        return dict(self.obs,blstats=self.obs["blstats"][:26])
    def step(self, action):
        self.obs,reward,self.done,self.info=self.raw.step(action)
        self._steps+=1
        if not self.done and int(self.obs["blstats"][20])>0:
            self.live_score=int(self.obs["blstats"][9])
            self.live_turns=int(self.obs["blstats"][20])
        return dict(self.obs,blstats=self.obs["blstats"][:26]),reward,self.done,self.info
    def get_seeds(self):
        return None # upstream uses this only in diagnostic logs; challenge disables seed access
    def close(self):
        self.raw.close()

def worker(args):
    worker_id,episodes,out=args
    out=Path(out)
    with (out/f'w{worker_id}.jsonl').open('x',buffering=1) as rows, (out/f'w{worker_id}.log').open('w',buffering=1) as log:
        import contextlib
        with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
            for episode in range(1,episodes+1):
                t=time.time()
                env=None
                row=dict(worker=worker_id,episode=episode,started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
                try:
                    env=ObservedChallenge()
                    wrapper=EnvWrapper(env,visualizer_args={'enable':False},agent_args={'panic_on_errors':False,'verbose':False})
                    wrapper.main()
                    row['agent_end_reason']=wrapper.end_reason
                    row['autoascend_reported_score']=wrapper.score
                except BaseException:
                    row['error']=traceback.format_exc()
                finally:
                    row['duration_s']=time.time()-t
                    row['completed']=bool(env and env.done)
                    if env:
                        row['steps']=env._steps
                        row['end_status']=int(env.info['end_status']) if 'end_status' in env.info else None
                        if env.obs is not None:
                            row['env_score']=env.live_score
                            row['turns']=env.live_turns
                        env.close()
                    rows.write(json.dumps(row)+'\n')
                if not row['completed']:
                    raise RuntimeError('Incomplete game; stopping worker to avoid an invalid benchmark: '+str(row))
    return worker_id

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--workers',type=int,default=4)
    p.add_argument('--episodes',type=int,default=1)
    p.add_argument('--out',required=True)
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    (out/'config.json').write_text(json.dumps(dict(workers=args.workers,episodes_per_worker=args.episodes,nle=nle.__file__,gym=gym.__version__,environment='gym.make("NetHackChallenge-v0")',seeding=False,clock='real wall clock',autoascend_commit='8527910bd85c4d851c18ad912aae606c92cd516a'),indent=2))
    with mp.get_context('spawn').Pool(args.workers) as pool:
        for wid in pool.imap_unordered(worker,[(i,args.episodes,str(out)) for i in range(args.workers)]):
            print('WORKER_DONE',wid,flush=True)
    print('ALL_DONE',flush=True)
