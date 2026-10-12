/* replay_pool: today's trainer rollout emulated over the recorded-action workload: the experiment trainer's shared env pool
 * (env_pool.h: work stealing, PUF_CPU_AFFINITY pinning), trainer buffers of POOL_BUF agents, resident groups of 4 buffers
 * (one per action stream) that take turns of POOL_SEG ticks (the cohort ini keys), and a GPU round trip after each buffer tick:
 * ready = ceil_to_window(e) + POOL_FWD_US, optionally serialized over POOL_STREAMS (same model as replay_sched).
 * POOL_BUF=apb reproduces the pre-cohort 4 x apb layout. POOL_PIN=1 pins the pool workers (24 -> physical cores) and the
 * four submitter threads to P-core SMT siblings 1,3,5,7, as the trainer does. Same init/hash as harness_cohort/replay_cohort.c. */
#define _GNU_SOURCE
#include <time.h>
#include <omp.h>
#include <math.h>
#include <sched.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include "source/ocean/nethack/nethack.h"
#include "env_pool.h"
static Env* envs;static float* actions[4];
static int env_count,buffers=4,apb,measured,BUF=128,SEG=64,STREAMS=0,PIN=1,HANDOFF=1;
static long WIN_NS=0,FWD_NS=0;static int latency_on;
static long ticks[4];static uint64_t* advances;static double env_t[4],gpu_t[4];
static pthread_mutex_t gpu_mu=PTHREAD_MUTEX_INITIALIZER;static double* stream_free;static double t_origin;
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
static uint64_t hash_bytes(uint64_t h,const void* ptr,size_t n){const unsigned char* p=ptr;for(size_t j=0;j<n;j++){h^=p[j];h*=1099511628211ULL;}return h;}
static void sleep_until(double t){double d=t-now();if(d<=0)return;struct timespec ts={(time_t)d,(long)((d-(time_t)d)*1e9)};nanosleep(&ts,NULL);}
static double gpu_ready(double e){
 if(!latency_on||(!WIN_NS&&!FWD_NS))return e;
 double t=e;
 if(WIN_NS){double win=WIN_NS*1e-9;t=t_origin+ceil((e-t_origin)/win)*win;}
 if(STREAMS>0){pthread_mutex_lock(&gpu_mu);int s=0;for(int k=1;k<STREAMS;k++)if(stream_free[k]<stream_free[s])s=k;double start=t>stream_free[s]?t:stream_free[s];stream_free[s]=start+FWD_NS*1e-9;double r=stream_free[s];pthread_mutex_unlock(&gpu_mu);return r;}
 return t+FWD_NS*1e-9;
}
static void step_one(void* unused,int i){
 Env* e=envs+i;int b=i/apb,slot=i%apb%128;
 memcpy(e->agents[0].actions,actions[b]+((size_t)ticks[b]*128+slot)*NUM_ATNS,NUM_ATNS*sizeof(float));
 *e->agents[0].rewards=0;*e->agents[0].terminals=0;
 long before=e->blstats[NLE_BL_TIME];
 puf_step(e);
 long after=e->blstats[NLE_BL_TIME];if(measured&&after>before)advances[i]+=after-before;
}
static void rounds(EnvPool* pool,long begin,long count,long seg){
#pragma omp parallel num_threads(buffers)
 {int b=omp_get_thread_num();int ngroups=apb/BUF;
  if(PIN){cpu_set_t cs;CPU_ZERO(&cs);CPU_SET(2*b+1,&cs);sched_setaffinity(0,sizeof cs,&cs);}
  for(long s=begin;s<begin+count;s+=seg){long se=s+seg<begin+count?s+seg:begin+count;
   for(int g=0;g<ngroups;g++){
    for(long t=s;t<se;t++){ticks[b]=t;double e0=now();ep_run(pool,b,b*apb+g*BUF,BUF);double e=now();if(measured)env_t[b]+=e-e0;
     double r=gpu_ready(e);if(r>e){if(measured)gpu_t[b]+=r-e;sleep_until(r);}}
    if(HANDOFF){
#pragma omp barrier
    }
   }
  }
 }
}
static long envl(const char* k,long d){const char* v=getenv(k);return v?atol(v):d;}
int main(int argc,char**argv){
 if(argc<6){fprintf(stderr,"replay_pool envs workers warm steps action_dir\n");return 2;}
 env_count=atoi(argv[1]);int workers=atoi(argv[2]);long warm=atol(argv[3]),steps=atol(argv[4]);
 assert(env_count%buffers==0);apb=env_count/buffers;
 BUF=envl("POOL_BUF",128);if(BUF>apb)BUF=apb;SEG=envl("POOL_SEG",64);WIN_NS=envl("POOL_WIN_US",0)*1000L;FWD_NS=envl("POOL_FWD_US",0)*1000L;
 STREAMS=envl("POOL_STREAMS",0);PIN=envl("POOL_PIN",1);HANDOFF=envl("POOL_HANDOFF_SYNC",1);
 assert(apb%BUF==0&&steps%SEG==0&&workers>0);
 if(PIN)setenv("PUF_CPU_AFFINITY","1",1);
 stream_free=calloc(STREAMS>0?STREAMS:1,sizeof(double));
 omp_set_dynamic(0);omp_set_max_active_levels(2);
 for(int b=0;b<4;b++){char path[4096];snprintf(path,sizeof(path),"%s/buf%d.bin",argv[5],b);int fd=open(path,O_RDONLY);assert(fd>=0);struct stat st;assert(fstat(fd,&st)==0);assert(st.st_size>=(warm+steps)*128*NUM_ATNS*sizeof(float));actions[b]=mmap(NULL,st.st_size,PROT_READ,MAP_PRIVATE,fd,0);assert(actions[b]!=MAP_FAILED);close(fd);}
 envs=calloc(env_count,sizeof(Env));advances=calloc(env_count,sizeof(uint64_t));
 Dict kwargs={0};
 dict_set(&kwargs,"gold_coef",0.0530697852);dict_set(&kwargs,"score_coef",0.00148907036);dict_set(&kwargs,"exp_coef",0.0912783295);dict_set(&kwargs,"descent_coef",1);dict_set(&kwargs,"floor_coef",0.126026332);dict_set(&kwargs,"xp_coef",1);dict_set(&kwargs,"scout_coef",0.00686222408);dict_set(&kwargs,"death_penalty",-0.472198129);dict_set(&kwargs,"mask_search20",0);dict_set(&kwargs,"mask_run",0);dict_set(&kwargs,"multi_role",1);
 int sizes[]=ACT_SIZES,mask_size=0;for(int h=0;h<NUM_ATNS;h++)mask_size+=sizes[h];
 for(int i=0;i<env_count;i++){Env*e=envs+i;e->rng=(i/apb*128+i%apb%128);puf_init(e,&kwargs);Agent*a=e->agents;a->observations=calloc(OBS_SIZE,1);a->actions=calloc(NUM_ATNS,sizeof(float));a->rewards=calloc(1,sizeof(float));a->terminals=calloc(1,sizeof(float));a->action_mask=calloc(mask_size,1);puf_reset(e);}
 EnvPool*pool=ep_create(workers,buffers,step_one,NULL);
 double initialized=now();latency_on=0;rounds(pool,0,warm,warm>0?warm:1);double warmed=now();
 measured=1;latency_on=1;t_origin=now();rounds(pool,warm,steps,SEG);double stopped=now();
 uint64_t hash=1469598103934665603ULL;long turns=0;uint64_t world_steps=0;
 for(int b=0;b<buffers;b++)for(int i=b*apb;i<(b+1)*apb;i++){if(i%apb<128)hash=hash_bytes(hash,envs[i].agents[0].observations,OBS_SIZE);else assert(memcmp(envs[i].agents[0].observations,envs[b*apb+i%128].agents[0].observations,OBS_SIZE)==0);turns+=envs[i].blstats[NLE_BL_TIME];world_steps+=advances[i];}
 double te=0,tg=0;for(int b=0;b<4;b++){te+=env_t[b];tg+=gpu_t[b];}
 printf("RESULT mode=pool envs=%d workers=%d buf=%d groups=%d seg=%d win_us=%ld fwd_us=%ld streams=%d pin=%d handoff=%d warm=%ld steps=%ld warm_seconds=%.3f seconds=%.3f sps=%.2f env_wall_mean=%.3f gpu_wait_mean=%.3f obs=%016lx age=%.2f turns=%lu\n",
  env_count,workers,BUF,apb/BUF,SEG,WIN_NS/1000,FWD_NS/1000,STREAMS,PIN,HANDOFF,warm,steps,warmed-initialized,stopped-warmed,env_count*steps/(stopped-warmed),te/4,tg/4,hash,(double)turns/env_count,world_steps);
 ep_destroy(pool);
 for(int i=0;i<env_count;i++){Env*e=envs+i;puf_close(e);free(e->agents[0].observations);free(e->agents[0].actions);free(e->agents[0].rewards);free(e->agents[0].terminals);free(e->agents[0].action_mask);}free(envs);return 0;
}
