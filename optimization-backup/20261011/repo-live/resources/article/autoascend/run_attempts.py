import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):
    os.environ[key]='1'
import argparse, json, time, traceback, multiprocessing as mp, signal
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

class EpisodeTimeout(KeyboardInterrupt):
    pass

def deadline(signum, frame):
    raise EpisodeTimeout('AutoAscend evaluation exceeded wall-clock limit')

def worker(args):
    worker_id,episodes,out,timeout=args
    signal.signal(signal.SIGALRM, deadline)
    out=Path(out)
    with (out/f'w{worker_id}.jsonl').open('x',buffering=1) as rows, (out/f'w{worker_id}.log').open('w',buffering=1) as log:
        import contextlib
        with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
            for episode in range(1,episodes+1):
                t=time.time()
                env=None
                wrapper=None
                fatal=False
                row=dict(worker=worker_id,episode=episode,started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
                try:
                    env=ObservedChallenge()
                    wrapper=EnvWrapper(env,visualizer_args={'enable':False},agent_args={'panic_on_errors':True,'verbose':False})
                    signal.setitimer(signal.ITIMER_REAL, timeout)
                    wrapper.main()
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    row['agent_end_reason']=wrapper.end_reason
                    row['autoascend_reported_score']=wrapper.score
                    row['panic_count']=len(wrapper.agent.all_panics)
                    row['panic_messages']=list(dict.fromkeys(str(e) for e in wrapper.agent.all_panics))[:30]
                except EpisodeTimeout:
                    row['outcome']='timeout'
                    row['error']=traceback.format_exc()
                except Exception:
                    row['error']=traceback.format_exc()
                    # Agent exceptions are outcomes, as in upstream single_simulation.
                    # Failures before the game starts are infrastructure failures.
                    fatal = env is None or wrapper is None or env._steps == 0
                    row['outcome']='infrastructure_error' if fatal else 'agent_exception'
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    row['duration_s']=time.time()-t
                    row['completed']=bool(env and env.done)
                    row.setdefault('outcome','environment_done' if row['completed'] else 'agent_returned')
                    if wrapper is not None:
                        row['autoascend_reported_score']=getattr(wrapper,'score',None)
                        agent=getattr(wrapper,'agent',None)
                        panics=getattr(agent,'all_panics',[])
                        row['panic_count']=len(panics)
                        row['panic_tracebacks']=[''.join(traceback.format_exception(type(e),e,e.__traceback__)) for e in panics[-5:]]
                    if env:
                        row['steps']=env._steps
                        row['end_status']=int(env.info['end_status']) if 'end_status' in env.info else None
                        if env.obs is not None:
                            row['env_score']=env.live_score
                            row['turns']=env.live_turns
                        env.close()
                    rows.write(json.dumps(row)+'\n')
                if fatal:
                    raise RuntimeError('Infrastructure failure: '+str(row))
    return worker_id

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--workers',type=int,default=4)
    p.add_argument('--episodes',type=int,default=1)
    p.add_argument('--out',required=True)
    p.add_argument('--timeout',type=float,default=720)
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    (out/'config.json').write_text(json.dumps(dict(workers=args.workers,episodes_per_worker=args.episodes,nle=nle.__file__,gym=gym.__version__,environment='gym.make("NetHackChallenge-v0")',seeding=False,panic_on_errors=True,clock='real wall clock',timeout_seconds=args.timeout,failure_policy='Retain agent exceptions and timeouts at last live score; no retries; upstream-style attempt accounting',autoascend_commit='8527910bd85c4d851c18ad912aae606c92cd516a'),indent=2))
    with mp.get_context('spawn').Pool(args.workers) as pool:
        for wid in pool.imap_unordered(worker,[(i,args.episodes,str(out),args.timeout) for i in range(args.workers)]):
            print('WORKER_DONE',wid,flush=True)
    print('ALL_DONE',flush=True)
