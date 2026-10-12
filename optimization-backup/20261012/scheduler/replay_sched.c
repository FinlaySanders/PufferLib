/* replay_sched: cohort scheduler with sticky ownership, cohort-granularity stealing, a dynamic-batching inference model and
 * horizon-segment barriers, over the recorded-action workload (same init/hash as harness_cohort/replay_cohort.c).
 * Cohort k = games [k*C, (k+1)*C), a fixed set. Every cohort has an owner; a worker alternates up to A of its cohorts (ping-pong)
 * inside a segment; a worker whose cohorts have all reached the segment end steals the most-behind idle cohort of another worker
 * (the holder with the most remaining work; its most-behind cohort). The thief BORROWS it for the rest of the segment; if the
 * victim owns at least SCHED_MIGRATE more cohorts than the thief, ownership moves permanently, so ownership drifts toward the
 * faster cores and settles instead of ping-ponging between equal workers. Whole cohorts are stolen only from a holder with >= 2 pending
 * cohorts (stealing a holder's last cohort just moves the work); at the tail the thief SPLITS the most-behind single cohort instead
 * (steal-half: takes the upper half of its games, down to SCHED_CMIN), and adjacent pieces of the same owner merge back (<= C) at the
 * segment barrier. So the balance quantum is a cohort-tick in the body and a few game-ticks at the tail. Inference model: a cohort that finishes a tick at
 * time e has its actions back at ready = ceil_to_window(e) + FWD, optionally serialized over STREAMS GPU streams.
 * Knobs (env): SCHED_C cohort size | SCHED_A active cohorts per worker (SCHED_A_P / SCHED_A_E per core type when pinned)
 *   SCHED_SEG ticks per segment (barrier) | SCHED_WIN_US batching window | SCHED_FWD_US forward latency | SCHED_STREAMS (0 = unbounded)
 *   SCHED_LAZY 1 = activate another own cohort only when none is ready (hot set grows just enough to cover latency)
 *   SCHED_SLACK_US timer slack (default 1) | SCHED_SPIN_US spin instead of sleeping for waits below this (default 20)
 *   SCHED_STREAMS>0 = one forward per batching window shared by all cohorts finishing in it, windows queue on the streams
 *   SCHED_BORROW_US >= 0: when none of a worker's own cohorts is ready within this many us, step ONE tick of another holder's
 *     ready cohort (cold) instead of idling; the holder keeps it. -1 = off.
 *   SCHED_GROUPFILL 1: refill the active set only when it is EMPTY (a group of A fresh cohorts starts the segment together), so a
 *     cohort activated mid-segment never runs alone at the end paying the full round trip per tick (the pass-2 idle source).
 *   SCHED_BORROW_FIT 1: threshold-free borrowing — take a ready cohort of another holder only if its predicted cold tick
 *     (its EWMA tick cost x a self-measured cold factor) fits inside my wait; no wait-time knob.
 *   SCHED_EVENT 1: event-driven readiness (ready-time buckets) + spin-wait polling them for borrowable work; never sleeps
 *   SCHED_STEAL 0/1 | SCHED_MIGRATE ownership-count gap that turns a borrow into a migration (0 = never) | SCHED_PIN 0/1 (24 workers -> one per physical core P 0,2..14 E 16..31; 32 -> cpu w) | SCHED_PWEIGHT initial
 *   P-core ownership weight (1.0 = uniform; migration does the rest)
 * Per-game action order is unchanged, so the final observation hash must equal the pool control's at the same game count. */
#define _GNU_SOURCE
#include <time.h>
#include <pthread.h>
#include <sched.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <assert.h>
#include <sys/prctl.h>
#include <immintrin.h>
#include "source/ocean/nethack/nethack.h"
typedef struct{int first,n;long tick;double ready;int owner;int holder;int busy;double cost;pthread_mutex_t mu;}Cohort;
static Env* envs;static float* actions[4];
static int env_count,buffers=4,apb,W,C=16,A=2,A_P=-1,A_E=-1,SEG=64,STEAL=1,PIN=1,STREAMS=0;
static long WIN_NS=0,FWD_NS=0,SLACK_NS=1000,SPIN_NS=20000,BORROW_NS=-1;static long* borrows;static double PWEIGHT=1.0;static int LAZY=0,GROUPFILL=0,FIT=0,EVENT=0;static double cold_factor=1.5;

#define NWIN 65536
static long win_k[NWIN];static double win_end[NWIN];
static Cohort* coh;static int ncoh,ncoh_cap,CMIN=2;static pthread_mutex_t alloc_mu=PTHREAD_MUTEX_INITIALIZER;static long* splits;
static uint64_t* advances;static double *busy,*idle_t,*bar_t;static long *steals,*migrations;static int *owned;static int measured,latency_on;static pthread_mutex_t own_mu=PTHREAD_MUTEX_INITIALIZER;static int MIGRATE=2;
static pthread_barrier_t barrier;static pthread_mutex_t gpu_mu=PTHREAD_MUTEX_INITIALIZER;static double* stream_free;static double t_origin;
/* event-driven readiness: every cohort whose actions come back at time r is pushed into bucket floor((r-t0)/Q); a core looking for
 * borrowable work reads only the buckets whose time has passed (a few dozen entries), and polls them while spinning instead of sleeping */
#define NB 65536
#define BQ 50e-6
typedef struct{long gen;int n;int* ids;volatile int lock;}Bucket;
static Bucket* buckets;static int bucket_cap;
static void bucket_push(int id,double r){long b=(long)((r-t_origin)/BQ);if(b<0)b=0;Bucket* k=&buckets[b%NB];
 while(__atomic_exchange_n(&k->lock,1,__ATOMIC_ACQUIRE))_mm_pause();
 if(k->gen!=b){k->gen=b;k->n=0;} if(k->n<bucket_cap)k->ids[k->n++]=id;
 __atomic_store_n(&k->lock,0,__ATOMIC_RELEASE);}
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
static uint64_t hash_bytes(uint64_t h,const void* ptr,size_t n){const unsigned char* p=ptr;for(size_t j=0;j<n;j++){h^=p[j];h*=1099511628211ULL;}return h;}
static void step_game(int i,long t){
 Env* e=envs+i;int b=i/apb,slot=i%apb%128;
 memcpy(e->agents[0].actions,actions[b]+((size_t)t*128+slot)*NUM_ATNS,NUM_ATNS*sizeof(float));
 *e->agents[0].rewards=0;*e->agents[0].terminals=0;
 long before=e->blstats[NLE_BL_TIME];
 puf_step(e);
 long after=e->blstats[NLE_BL_TIME];if(measured&&after>before)advances[i]+=after-before;
}
static void sleep_until(double t){double d=t-now();if(d<=0)return;if(d*1e9>SPIN_NS){struct timespec ts={(time_t)d,(long)((d-(time_t)d)*1e9)};nanosleep(&ts,NULL);}while(now()<t)_mm_pause();}
static int is_pcore(int w){if(!PIN)return 0;if(W==24)return w<8;if(W==32)return w<16;return 0;}
static double gpu_ready(double e){
 if(!latency_on||(!WIN_NS&&!FWD_NS))return e;
 double t=e;
 if(WIN_NS){double win=WIN_NS*1e-9;t=t_origin+ceil((e-t_origin)/win)*win;}
 if(STREAMS>0){double win=WIN_NS>0?WIN_NS*1e-9:FWD_NS*1e-9;long k=(long)ceil((e-t_origin)/win);int slot=(int)(k%NWIN);double r;
  pthread_mutex_lock(&gpu_mu);
  if(win_k[slot]==k)r=win_end[slot];
  else{int s=0;for(int j=1;j<STREAMS;j++)if(stream_free[j]<stream_free[s])s=j;double wend=t_origin+k*win;double start=wend>stream_free[s]?wend:stream_free[s];stream_free[s]=start+FWD_NS*1e-9;win_k[slot]=k;win_end[slot]=stream_free[s];r=win_end[slot];}
  pthread_mutex_unlock(&gpu_mu);return r;}
 return t+FWD_NS*1e-9;
}
#define LD(x) __atomic_load_n(&(x),__ATOMIC_RELAXED)
#define DEAD 0x7fffffffffffffffL
static int cmp_first(const void*a,const void*b){int x=*(const int*)a,y=*(const int*)b;return (coh[x].first>coh[y].first)-(coh[x].first<coh[y].first);}
typedef struct{int w;long begin,end,seg;}WorkerArg;
static void* worker(void* arg){
 WorkerArg* wa=arg;int w=wa->w;
 if(PIN){int cpu=-1;if(W==24)cpu=w<8?2*w:16+w-8;else if(W==32)cpu=w;if(cpu>=0){cpu_set_t cs;CPU_ZERO(&cs);CPU_SET(cpu,&cs);sched_setaffinity(0,sizeof cs,&cs);}}
 prctl(PR_SET_TIMERSLACK,SLACK_NS);
 int amax=is_pcore(w)?(A_P>0?A_P:A):(A_E>0?A_E:A);if(amax>64)amax=64;if(LAZY)amax=64;
 int act[64];
 for(long sb=wa->begin;sb<wa->end;sb+=wa->seg){
  long se=sb+wa->seg<wa->end?sb+wa->seg:wa->end;int nact=0;
  for(;;){
   for(int j=0;j<nact;){Cohort*c=&coh[act[j]];if(LD(c->holder)!=w||LD(c->tick)>=se)act[j]=act[--nact];else j++;}
   if(!(GROUPFILL&&nact>0))while(nact<amax){if(LAZY&&nact>0){double tn=now();int any=0;for(int j=0;j<nact;j++)if(coh[act[j]].ready<=tn){any=1;break;}if(any)break;} /* lazy: grow the hot set only when nothing is ready */
    int pick=-1;for(int k=0;k<ncoh;k++){Cohort*c=&coh[k];if(LD(c->holder)!=w||LD(c->tick)>=se)continue;int in=0;for(int j=0;j<nact;j++)if(act[j]==k){in=1;break;}if(!in){pick=k;break;}}if(pick<0)break;act[nact++]=pick;}
   if(!nact){
    if(!STEAL)break;
    long rem[256]={0};int pend[256]={0};int pending=0,nc=LD(ncoh);
    for(int k=0;k<nc;k++){Cohort*c=&coh[k];long tk=LD(c->tick);if(tk>=se)continue;pending++;int h=LD(c->holder);pend[h]++;if(LD(c->busy))continue;rem[h]+=se-tk;}
    if(!pending)break;
    int v=-1;for(int u=0;u<W;u++){if(u==w||!rem[u]||pend[u]<2)continue;if(v<0||rem[u]>rem[v])v=u;}
    if(v>=0){ /* whole-cohort steal: the most-behind idle cohort of the busiest holder that keeps at least one */
     int victim=-1;long most=-1;for(int k=0;k<nc;k++){Cohort*c=&coh[k];if(LD(c->holder)!=v||LD(c->busy)||LD(c->tick)>=se)continue;long r=se-LD(c->tick);if(r>most){most=r;victim=k;}}
     if(victim<0)continue;
     Cohort*c=&coh[victim];pthread_mutex_lock(&c->mu);int ok=(c->holder==v&&!c->busy&&c->tick<se);if(ok)c->holder=w;pthread_mutex_unlock(&c->mu);
     if(ok){if(measured)steals[w]++;act[nact++]=victim;
      pthread_mutex_lock(&own_mu);int o=c->owner;if(MIGRATE>0&&o!=w&&owned[o]-owned[w]>=MIGRATE){c->owner=w;owned[o]--;owned[w]++;if(measured)migrations[w]++;}pthread_mutex_unlock(&own_mu);}
     continue;
    }
    /* tail: every holder is on its last cohort; split the most-behind idle one (upper half of its games) */
    int victim=-1;long most=-1;for(int k=0;k<nc;k++){Cohort*c=&coh[k];if(LD(c->holder)==w||LD(c->busy)||LD(c->tick)>=se||LD(c->n)<2*CMIN)continue;long r=(se-LD(c->tick))*(long)LD(c->n);if(r>most){most=r;victim=k;}}
    if(victim<0){sched_yield();continue;} /* all busy or at CMIN: their holders finish them */
    Cohort*c=&coh[victim];pthread_mutex_lock(&c->mu);
    if(c->busy||c->tick>=se||c->n<2*CMIN||c->holder==w){pthread_mutex_unlock(&c->mu);continue;}
    pthread_mutex_lock(&alloc_mu);int slot=-1;for(int k=0;k<ncoh;k++)if(coh[k].n==0&&!coh[k].busy&&LD(coh[k].tick)==DEAD){slot=k;break;}
    if(slot<0&&ncoh<ncoh_cap)slot=ncoh;
    if(slot>=0){Cohort*d=&coh[slot];pthread_mutex_lock(&d->mu);int half=c->n/2;d->first=c->first+c->n-half;d->n=half;d->owner=c->owner;d->holder=w;d->ready=c->ready;d->busy=0;d->cost=c->cost*half/c->n;c->cost-=d->cost;__atomic_store_n(&d->tick,c->tick,__ATOMIC_RELAXED);c->n-=half;pthread_mutex_unlock(&d->mu);if(slot==ncoh)__atomic_store_n(&ncoh,ncoh+1,__ATOMIC_RELEASE);}
    pthread_mutex_unlock(&alloc_mu);pthread_mutex_unlock(&c->mu);
    if(slot>=0){if(measured)splits[w]++;act[nact++]=slot;}
    continue;
   }
   int best=-1;for(int j=0;j<nact;j++){Cohort*c=&coh[act[j]];if(LD(c->busy))continue;if(best<0||c->ready<coh[best].ready)best=act[j];}
   if(best<0){sched_yield();continue;} /* all my active cohorts are being borrowed right now */
   Cohort*c=&coh[best];double t0=now();
   if(c->ready>t0){
    double wait=c->ready-t0;
    if((FIT&&wait>0)||(BORROW_NS>=0&&wait>BORROW_NS*1e-9)){ /* fill the wait with one tick of somebody else's ready cohort */
     int b=-1;long most=-1;int nc=LD(ncoh);double cf_now=cold_factor;
     for(int k=0;k<nc;k++){Cohort*d=&coh[k];if(LD(d->holder)==w||LD(d->busy)||LD(d->tick)>=se||d->ready>t0)continue;
      if(FIT&&d->cost>0&&d->cost*cf_now>wait)continue; /* would not finish before my own actions are back */
      long r=se-LD(d->tick);if(r>most){most=r;b=k;}}
     if(b>=0){Cohort*d=&coh[b];pthread_mutex_lock(&d->mu);int ok=(d->holder!=w&&!d->busy&&d->tick<se&&d->ready<=t0);int cf=d->first,cn=d->n;if(ok)d->busy=1;pthread_mutex_unlock(&d->mu);
      if(ok){double s=now();long t=d->tick;for(int i=cf;i<cf+cn;i++)step_game(i,t);double e=now();if(measured){busy[w]+=e-s;borrows[w]++;}
       double r=gpu_ready(e);pthread_mutex_lock(&d->mu);d->tick=t+1;d->ready=r;d->busy=0;if(EVENT&&d->tick<se)bucket_push(b,r);
       if(d->cost>0){double ratio=(e-s)/d->cost;pthread_mutex_lock(&gpu_mu);cold_factor=0.95*cold_factor+0.05*(ratio<1?1:ratio);pthread_mutex_unlock(&gpu_mu);}
       pthread_mutex_unlock(&d->mu);continue;}
     }
    }
    if(EVENT){ /* spin: poll the ready buckets for any other holder's ready cohort; step it; else wait for my own */
     double spin0=now();int borrowed=0;
     for(;;){double tn=now();if(c->ready<=tn||LD(c->holder)!=w||LD(c->busy))break;
      long bnow=(long)((tn-t_origin)/BQ),bold=bnow-(long)(0.004/BQ);if(bold<0)bold=0;int b=-1;long most=-1;
      for(long q=bnow;q>=bold&&b<0;q--){Bucket* k=&buckets[q%NB];if(k->gen!=q)continue;int n=k->n;for(int j=0;j<n&&j<bucket_cap;j++){int id=k->ids[j];Cohort*d=&coh[id];
        if(LD(d->holder)==w||LD(d->busy)||LD(d->tick)>=se||d->ready>tn)continue;if(FIT&&d->cost>0&&d->cost*cold_factor>c->ready-tn)continue;long r=se-LD(d->tick);if(r>most){most=r;b=id;}}}
      if(b>=0){Cohort*d=&coh[b];pthread_mutex_lock(&d->mu);int ok=(d->holder!=w&&!d->busy&&d->tick<se&&d->ready<=tn);int cf=d->first,cn=d->n;if(ok)d->busy=1;pthread_mutex_unlock(&d->mu);
       if(ok){if(measured)idle_t[w]+=now()-spin0;double s=now();long t=d->tick;for(int i=cf;i<cf+cn;i++)step_game(i,t);double e=now();if(measured){busy[w]+=e-s;borrows[w]++;}
        double r=gpu_ready(e);pthread_mutex_lock(&d->mu);d->tick=t+1;d->ready=r;d->busy=0;if(d->tick<se)bucket_push(b,r);
        if(d->cost>0){double ratio=(e-s)/d->cost;pthread_mutex_lock(&gpu_mu);cold_factor=0.95*cold_factor+0.05*(ratio<1?1:ratio);pthread_mutex_unlock(&gpu_mu);}
        pthread_mutex_unlock(&d->mu);borrowed=1;break;}
       continue;}
      for(int z=0;z<32;z++)_mm_pause();
     }
     if(borrowed)continue;
     if(measured)idle_t[w]+=now()-spin0;
    } else {
     if(measured)idle_t[w]+=c->ready-t0;sleep_until(c->ready);
    }
   }
   pthread_mutex_lock(&c->mu);int ok=(c->holder==w&&!c->busy&&c->tick<se);int cf=c->first,cn=c->n;if(ok)c->busy=1;pthread_mutex_unlock(&c->mu);
   if(!ok)continue;
   double s=now();long t=c->tick;for(int i=cf;i<cf+cn;i++)step_game(i,t);double e=now();
   if(measured)busy[w]+=e-s;
   double r=gpu_ready(e);
   pthread_mutex_lock(&c->mu);c->tick=t+1;c->ready=r;c->busy=0;c->cost=c->cost>0?0.875*c->cost+0.125*(e-s):(e-s);pthread_mutex_unlock(&c->mu);if(EVENT&&c->tick<se)bucket_push(best,r);
  }
  double b0=now();pthread_barrier_wait(&barrier);
  { int mine[4096],nm=0,nc=LD(ncoh);for(int k=0;k<nc&&nm<4096;k++)if(coh[k].n>0&&coh[k].owner==w){mine[nm++]=k;__atomic_store_n(&coh[k].holder,w,__ATOMIC_RELAXED);} /* borrowed cohorts go home */
    qsort(mine,nm,sizeof(int),cmp_first);
    for(int a=0;a+1<nm;a++){Cohort*x=&coh[mine[a]];for(int b=a+1;b<nm;b++){Cohort*y=&coh[mine[b]];if(y->n==0)continue;if(y->first!=x->first+x->n||x->n+y->n>C)break;x->n+=y->n;if(y->ready>x->ready)x->ready=y->ready;y->n=0;__atomic_store_n(&y->tick,DEAD,__ATOMIC_RELAXED);} } }
  pthread_barrier_wait(&barrier);if(measured)bar_t[w]+=now()-b0;
 }
 return NULL;
}
static void run_window(long begin,long end,long seg){
 pthread_t th[256];WorkerArg wa[256];
 for(int k=0;k<ncoh;k++){if(coh[k].n==0)continue;coh[k].tick=begin;coh[k].ready=0;coh[k].busy=0;coh[k].holder=coh[k].owner;}
 for(int w=0;w<W;w++){wa[w].w=w;wa[w].begin=begin;wa[w].end=end;wa[w].seg=seg;pthread_create(&th[w],NULL,worker,&wa[w]);}
 for(int w=0;w<W;w++)pthread_join(th[w],NULL);
}
static long envl(const char* k,long d){const char* v=getenv(k);return v?atol(v):d;}
int main(int argc,char**argv){
 if(argc<6){fprintf(stderr,"replay_sched envs workers warm steps action_dir\n");return 2;}
 env_count=atoi(argv[1]);W=atoi(argv[2]);long warm=atol(argv[3]),steps=atol(argv[4]);
 C=envl("SCHED_C",16);A=envl("SCHED_A",2);A_P=envl("SCHED_A_P",-1);A_E=envl("SCHED_A_E",-1);SEG=envl("SCHED_SEG",64);
 WIN_NS=envl("SCHED_WIN_US",0)*1000L;FWD_NS=envl("SCHED_FWD_US",0)*1000L;STREAMS=envl("SCHED_STREAMS",0);
 STEAL=envl("SCHED_STEAL",1);LAZY=envl("SCHED_LAZY",0);GROUPFILL=envl("SCHED_GROUPFILL",0);FIT=envl("SCHED_BORROW_FIT",0);EVENT=envl("SCHED_EVENT",0);BORROW_NS=envl("SCHED_BORROW_US",-1);if(BORROW_NS>=0)BORROW_NS*=1000L;SLACK_NS=envl("SCHED_SLACK_US",1)*1000L;SPIN_NS=envl("SCHED_SPIN_US",20)*1000L;MIGRATE=envl("SCHED_MIGRATE",2);CMIN=envl("SCHED_CMIN",2);PIN=envl("SCHED_PIN",1);if(getenv("SCHED_PWEIGHT"))PWEIGHT=atof(getenv("SCHED_PWEIGHT"));
 assert(env_count%buffers==0);apb=env_count/buffers;assert(C>=1&&env_count%C==0&&A>=1&&W>=1&&W<=256&&SEG>=1&&steps%SEG==0&&STREAMS>=0&&STREAMS<=64);
 for(int b=0;b<4;b++){char path[4096];snprintf(path,sizeof(path),"%s/buf%d.bin",argv[5],b);int fd=open(path,O_RDONLY);assert(fd>=0);struct stat st;assert(fstat(fd,&st)==0);assert(st.st_size>=(warm+steps)*128*NUM_ATNS*sizeof(float));actions[b]=mmap(NULL,st.st_size,PROT_READ,MAP_PRIVATE,fd,0);assert(actions[b]!=MAP_FAILED);close(fd);}
 envs=calloc(env_count,sizeof(Env));advances=calloc(env_count,sizeof(uint64_t));busy=calloc(W,sizeof(double));idle_t=calloc(W,sizeof(double));bar_t=calloc(W,sizeof(double));steals=calloc(W,sizeof(long));migrations=calloc(W,sizeof(long));owned=calloc(W,sizeof(int));
 stream_free=calloc(STREAMS>0?STREAMS:1,sizeof(double));pthread_barrier_init(&barrier,NULL,W);
 bucket_cap=env_count;buckets=calloc(NB,sizeof(Bucket));for(int k=0;k<NB;k++){buckets[k].gen=-1;buckets[k].ids=calloc(bucket_cap,sizeof(int));}
 ncoh=env_count/C;ncoh_cap=env_count;coh=calloc(ncoh_cap,sizeof(Cohort));for(int k=0;k<ncoh_cap;k++){pthread_mutex_init(&coh[k].mu,NULL);coh[k].tick=DEAD;}for(int k=0;k<ncoh;k++){coh[k].first=k*C;coh[k].n=C;}splits=calloc(W,sizeof(long));borrows=calloc(W,sizeof(long));
 { double wt[256],wsum=0;int n[256],assigned=0;for(int w=0;w<W;w++){wt[w]=is_pcore(w)?PWEIGHT:1.0;wsum+=wt[w];}
   for(int w=0;w<W;w++){n[w]=(int)floor(ncoh*wt[w]/wsum);assigned+=n[w];}
   for(int w=0;assigned<ncoh;w=(w+1)%W){n[w]++;assigned++;}
   int k=0;for(int w=0;w<W;w++){owned[w]=n[w];for(int j=0;j<n[w];j++){coh[k].owner=w;coh[k].holder=w;k++;}}assert(k==ncoh); }
 Dict kwargs={0};
 dict_set(&kwargs,"gold_coef",0.0530697852);dict_set(&kwargs,"score_coef",0.00148907036);dict_set(&kwargs,"exp_coef",0.0912783295);dict_set(&kwargs,"descent_coef",1);dict_set(&kwargs,"floor_coef",0.126026332);dict_set(&kwargs,"xp_coef",1);dict_set(&kwargs,"scout_coef",0.00686222408);dict_set(&kwargs,"death_penalty",-0.472198129);dict_set(&kwargs,"mask_search20",0);dict_set(&kwargs,"mask_run",0);dict_set(&kwargs,"multi_role",1);
 int sizes[]=ACT_SIZES,mask_size=0;for(int h=0;h<NUM_ATNS;h++)mask_size+=sizes[h];
 for(int i=0;i<env_count;i++){Env*e=envs+i;e->rng=(i/apb*128+i%apb%128);puf_init(e,&kwargs);Agent*a=e->agents;a->observations=calloc(OBS_SIZE,1);a->actions=calloc(NUM_ATNS,sizeof(float));a->rewards=calloc(1,sizeof(float));a->terminals=calloc(1,sizeof(float));a->action_mask=calloc(mask_size,1);puf_reset(e);}
 double initialized=now();
 latency_on=0;run_window(0,warm,warm>0?warm:1); /* warm: same scheduler, no inference latency, ownership settles */
 double warmed=now();measured=1;latency_on=1;t_origin=now();for(int s=0;s<(STREAMS>0?STREAMS:1);s++)stream_free[s]=0;for(int k=0;k<NWIN;k++)win_k[k]=-1;for(int k=0;k<NB;k++){buckets[k].gen=-1;buckets[k].n=0;}
 run_window(warm,warm+steps,SEG);double stopped=now();
 uint64_t hash=1469598103934665603ULL;long turns=0;uint64_t world_steps=0;
 for(int b=0;b<buffers;b++)for(int i=b*apb;i<(b+1)*apb;i++){if(i%apb<128)hash=hash_bytes(hash,envs[i].agents[0].observations,OBS_SIZE);else assert(memcmp(envs[i].agents[0].observations,envs[b*apb+i%128].agents[0].observations,OBS_SIZE)==0);turns+=envs[i].blstats[NLE_BL_TIME];world_steps+=advances[i];}
 double tb=0,ti=0,tbar=0,maxb=0,minb=1e30;long ts=0,tm=0,tsp=0,tbo=0;int ownP=0,ownE=0,live=0;for(int w=0;w<W;w++){tb+=busy[w];ti+=idle_t[w];tbar+=bar_t[w];ts+=steals[w];tm+=migrations[w];tsp+=splits[w];tbo+=borrows[w];if(busy[w]>maxb)maxb=busy[w];if(busy[w]<minb)minb=busy[w];}
 for(int k=0;k<ncoh;k++){if(coh[k].n==0)continue;live++;if(is_pcore(coh[k].owner))ownP++;else ownE++;}
 printf("RESULT mode=sched envs=%d workers=%d event=%d borrow_us=%ld fit=%d cold=%.2f groupfill=%d lazy=%d slack_us=%ld spin_us=%ld C=%d A=%d A_P=%d A_E=%d seg=%d win_us=%ld fwd_us=%ld streams=%d steal=%d pin=%d pweight=%.2f migrate=%d warm=%ld steps=%ld warm_seconds=%.3f seconds=%.3f sps=%.2f busy_sps=%.2f busy_mean=%.3f busy_min=%.3f busy_max=%.3f idle_mean=%.3f bar_mean=%.3f steals=%ld migrations=%ld splits=%ld borrows=%ld live_cohorts=%d own_P=%d own_E=%d obs=%016lx age=%.2f turns=%lu\n",
  env_count,W,EVENT,BORROW_NS>=0?BORROW_NS/1000:-1,FIT,cold_factor,GROUPFILL,LAZY,SLACK_NS/1000,SPIN_NS/1000,C,A,A_P,A_E,SEG,WIN_NS/1000,FWD_NS/1000,STREAMS,STEAL,PIN,PWEIGHT,MIGRATE,warm,steps,warmed-initialized,stopped-warmed,env_count*steps/(stopped-warmed),env_count*steps/(tb/W),tb/W,minb,maxb,ti/W,tbar/W,ts,tm,tsp,tbo,live,ownP,ownE,hash,(double)turns/env_count,world_steps);
 for(int i=0;i<env_count;i++){Env*e=envs+i;puf_close(e);free(e->agents[0].observations);free(e->agents[0].actions);free(e->agents[0].rewards);free(e->agents[0].terminals);free(e->agents[0].action_mask);}free(envs);return 0;
}
