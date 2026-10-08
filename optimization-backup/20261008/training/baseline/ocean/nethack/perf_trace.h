#pragma once
#include <assert.h>
typedef struct { char magic[8]; unsigned rng; int discovery; float cfg[11]; } TraceHeader;
typedef struct { unsigned long seed; int spawn,underfoot,moon; char options[32768]; } TraceStart;
static void trace_io(Nethack* e, char kind, const void* data, size_t n) {
    if (!e->trace_file) return;
    if(e->trace_mode==1) {
        assert(fwrite(&kind,1,1,e->trace_file)==1);
        assert(fwrite(data,1,n,e->trace_file)==n);
    } else {
        int k=fgetc(e->trace_file);
        if(k!=kind) { fprintf(stderr,"TRACE event %lu expected %c got %d env %u\n",e->trace_events,kind,k,e->rng); abort(); }
        unsigned char buf[sizeof(TraceStart)+64]; assert(n<=sizeof(buf));
        assert(fread(buf,1,n,e->trace_file)==n);
        if(e->trace_mode==2 && memcmp(buf,data,n)) {
            size_t i=0;while(i<n && buf[i]==((unsigned char*)data)[i])i++;
            fprintf(stderr,"TRACE mismatch env=%u event=%lu kind=%c byte=%zu T=%ld\n",e->rng,e->trace_events,kind,i,e->blstats[NLE_BL_TIME]);abort();
        }
    }
    if(e->trace_aug_file) {
        assert(fwrite(&kind,1,1,e->trace_aug_file)==1);
        assert(fwrite(data,1,n,e->trace_aug_file)==n);
    }
    e->trace_events++;
}
static uint64_t trace_hash(uint64_t h,const void* p,size_t n) {
    if(!p)return h;
    const unsigned char* b=(const unsigned char*)p;
    while(n--) {h^=*b++;h*=1099511628211ULL;}return h;
}
static void trace_start(Nethack* e) {
    if(!e->trace_file && !e->trace_mode) {
        const char* dir=getenv("NH_PERF_RECORD");
        if(!dir)return;
        char path[4096];snprintf(path,sizeof(path),"%s/env%05u.trace",dir,e->rng);
        e->trace_file=fopen(path,"wb");assert(e->trace_file);e->trace_mode=1;
        setvbuf(e->trace_file,NULL,_IOFBF,65536);
        TraceHeader h={0};memcpy(h.magic,"NHPERF2",7);e->trace_version=2;h.rng=e->rng;
        h.discovery=!(getenv("NH_DISC_SWAP") && getenv("NH_DISC_SWAP")[0]=='0');
        memcpy(h.cfg,&e->gold_coef,sizeof(h.cfg));assert(fwrite(&h,1,sizeof(h),e->trace_file)==sizeof(h));
    }
    if(!e->trace_file)return;
    TraceStart st={0};st.seed=e->seed;st.spawn=e->settings.spawn_monsters;st.underfoot=e->settings.underfoot_glyphs;st.moon=e->settings.fix_moon_phase;
    if(e->settings.options[0]=='@') {
        FILE* f=fopen(e->settings.options+1,"rb");assert(f);fread(st.options,1,sizeof(st.options)-1,f);fclose(f);
    }else snprintf(st.options,sizeof(st.options),"%s",e->settings.options);
    trace_io(e,'R',&st,sizeof(st));
}

/* Sidecar records: event u64, kind u8, then (length u32, bytes) per field.
 * Native little-endian ABI, same as the frozen trace. NULL fields have length0.
 * Only enabled explicitly in recording/verification, never timing. */
static FILE* snapshot_begin(Nethack* e, char kind) {
    if(!e->snapshot_checked) {
        e->snapshot_checked=1;
        const char* dir=getenv("NH_PERF_SNAPSHOTS");
        if(dir) {
            assert(e->trace_mode!=3);
            char path[4096];snprintf(path,sizeof(path),"%s/env%05u.obs",dir,e->rng);
            e->snapshot_file=fopen(path,"wbx");assert(e->snapshot_file);
            setvbuf(e->snapshot_file,NULL,_IOFBF,65536);
            assert(fwrite("NHOBS001",1,8,e->snapshot_file)==8);
        }
    }
    FILE* f=e->snapshot_file;if(!f)return NULL;
    uint64_t event=e->trace_events;
    assert(fwrite(&event,8,1,f)==1);assert(fwrite(&kind,1,1,f)==1);return f;
}
static void snapshot_field(FILE* f,const void* data,size_t size) {
    if(!f)return;assert(size<=UINT32_MAX);uint32_t n=data?(uint32_t)size:0;
    assert(fwrite(&n,4,1,f)==1);if(n)assert(fwrite(data,1,n,f)==n);
}

static uint64_t trace_engine_hash(Nethack* e) {
    uint64_t h=14695981039346656037ULL;
    if(e->trace_mode!=3) {
#define H(p,n) h=trace_hash(h,p,n)
        H(e->obs.glyphs,NH_GRID*sizeof(short)); H(e->obs.chars,NH_GRID);H(e->obs.colors,NH_GRID);H(e->obs.specials,NH_GRID);
        H(e->obs.blstats,sizeof(e->blstats));H(e->obs.message,sizeof(e->message));H(e->obs.misc,sizeof(e->misc));H(e->obs.internal,sizeof(e->internal));
        H(e->obs.inv_glyphs,sizeof(e->inv_glyphs));H(e->obs.inv_true_glyphs,sizeof(e->inv_true));H(e->obs.inv_letters,sizeof(e->inv_letters));H(e->obs.inv_oclasses,sizeof(e->inv_oclasses));H(e->obs.inv_state,sizeof(e->inv_state));
        H(&e->obs.done,sizeof(e->obs.done));H(&e->obs.how_done,sizeof(e->obs.how_done));
#undef H
    }
    return h;
}
static void trace_engine(Nethack* e,char kind) {
    if(!e->trace_file)return;
    FILE* f=snapshot_begin(e,kind);
        snapshot_field(f,e->obs.glyphs,NH_GRID*sizeof(short)); snapshot_field(f,e->obs.chars,NH_GRID);snapshot_field(f,e->obs.colors,NH_GRID);snapshot_field(f,e->obs.specials,NH_GRID);
        snapshot_field(f,e->obs.blstats,sizeof(e->blstats));snapshot_field(f,e->obs.message,sizeof(e->message));snapshot_field(f,e->obs.misc,sizeof(e->misc));snapshot_field(f,e->obs.internal,sizeof(e->internal));
        snapshot_field(f,e->obs.inv_glyphs,sizeof(e->inv_glyphs));snapshot_field(f,e->obs.inv_true_glyphs,sizeof(e->inv_true));snapshot_field(f,e->obs.inv_letters,sizeof(e->inv_letters));snapshot_field(f,e->obs.inv_oclasses,sizeof(e->inv_oclasses));snapshot_field(f,e->obs.inv_state,sizeof(e->inv_state));
        snapshot_field(f,&e->obs.done,sizeof(e->obs.done));snapshot_field(f,&e->obs.how_done,sizeof(e->obs.how_done));

    snapshot_field(f,e->obs.tty_chars,24*80);
    uint64_t h=trace_engine_hash(e);trace_io(e,kind,&h,sizeof(h));
}
static void trace_extra_refresh(Nethack* e) {
    if(e->trace_version==2) {trace_engine(e,'F');return;}
    if(e->trace_aug_file) {
        uint64_t h=trace_engine_hash(e);char kind='F';
        assert(fwrite(&kind,1,1,e->trace_aug_file)==1);
        assert(fwrite(&h,1,sizeof(h),e->trace_aug_file)==sizeof(h));
    }
}
static void trace_key(Nethack* e) {int key=e->obs.action;trace_io(e,'k',&key,sizeof(key));}
static void trace_action(Nethack* e) {trace_io(e,'A',e->agents[0].actions,NUM_ATNS*sizeof(float));}
static void trace_policy(Nethack* e) {
    if(!e->trace_file)return;
    uint64_t h=14695981039346656037ULL;
    if(e->trace_mode!=3) {
        h=trace_hash(h,e->agents[0].observations,OBS_SIZE);
        int sizes[]=ACT_SIZES;int n=0;for(int i=0;i<NUM_ATNS;i++)n+=sizes[i];
        h=trace_hash(h,e->agents[0].action_mask,n);
    }
    FILE* f=snapshot_begin(e,'O');
    snapshot_field(f,e->agents[0].observations,OBS_SIZE);
    int sizes2[]=ACT_SIZES;int n2=0;for(int i=0;i<NUM_ATNS;i++)n2+=sizes2[i];
    snapshot_field(f,e->agents[0].action_mask,n2);
    trace_io(e,'O',&h,sizeof(h));
}
static void trace_reward(Nethack* e) {float x[]={e->agents[0].rewards[0],e->agents[0].terminals[0]};trace_io(e,'W',x,sizeof(x));}
static void trace_end(Nethack* e,int how) {
    long x[]={e->prev_score,e->prev_time,e->stats.max_depth,e->stats.max_xp,how,e->stats.length};trace_io(e,'E',x,sizeof(x));
    if(e->trace_file && e->trace_mode==1)fflush(e->trace_file);
}
