from pathlib import Path
import subprocess, json, hashlib
r=Path(__file__).resolve().parent
d=r/'pass_fast_smoke'
d.mkdir(exist_ok=False)
s=(r/'source/ocean/nethack/nethack.cu').read_text()
a=s.index('__device__ __forceinline__ int nh_acc_slot(')
b=s.index('\n#endif',a)
helper=s[a:b]
a=s.index('__global__ void nh_pass_kernel(')
b=s.index('#include "pass_fast.cuh"',a)
reference=s[a:b]
prefix=r'''
#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>
#define CU(x) do { cudaError_t e=(x); if(e!=cudaSuccess) {fprintf(stderr,"%s:%d %s\n",__FILE__,__LINE__,cudaGetErrorString(e));abort();} } while(0)
using precision_t=__nv_bfloat16;
__host__ __device__ inline float to_float(precision_t x){return __bfloat162float(x);}
__host__ __device__ inline precision_t from_float(float x){return __float2bfloat16(x);}
#define NH_INV 55
#define NH_INV_HID 16
#define NH_SFEAT 24
#define NH_PWORN_DIM 16
#define NH_PAD_GLYPH 5976
#define NH_GLYPH_OBJ_OFF 1906
#define NH_CONCAT 320
#ifdef NH_NO_APANEL
#define NH_PASS_DIM 96
#else
#define NH_PASS_DIM 256
#endif
'''
main=r'''
uint32_t rng=81;
uint32_t next(){rng=1664525U*rng+1013904223U;return rng;}
float val(){int x=(int)(next()%20001)-10000;return (float)x*(next()%3==0?0.0001f:next()%2==0?0.1f:100.f);}
void check(int B,int mode){
 int n=B*NH_INV, nc=B*NH_CONCAT,ni=n*NH_INV_HID,ns=n*NH_SFEAT;
 std::vector<float> ids(n);std::vector<precision_t> sf(ns),in(ni),grad(ni),cat(nc),gc(nc);
 for(auto& x:sf)x=from_float(val());for(auto& x:in)x=from_float(val());
 for(auto& x:grad)x=from_float(val());for(auto& x:cat)x=from_float(val());for(auto& x:gc)x=from_float(val());
 for(int i=0;i<n;i++){
   int ot=next()%4==0?178+next()%11:next()%3==0?150+next()%28:next()%2==0?207+next()%3:next()%150;
   ids[i]=mode==0 || (mode!=1 && next()%5==0) ? NH_PAD_GLYPH : NH_GLYPH_OBJ_OFF+ot;
   for(int j:{9,10,12})sf[i*NH_SFEAT+j]=from_float(mode==1?1.f:mode==3?(float)(next()%3)*.5f:mode==4 && next()%5==0?NAN:next()%4==0?1.f:0.f);
 }
 float* di;precision_t *ds,*din,*dg,*dc,*dgc;
 CU(cudaMalloc(&di,n*sizeof(float)));CU(cudaMalloc(&ds,ns*2));CU(cudaMalloc(&din,ni*2));CU(cudaMalloc(&dg,ni*2));CU(cudaMalloc(&dc,nc*2));CU(cudaMalloc(&dgc,nc*2));
 CU(cudaMemcpy(di,ids.data(),n*4,cudaMemcpyHostToDevice));CU(cudaMemcpy(ds,sf.data(),ns*2,cudaMemcpyHostToDevice));CU(cudaMemcpy(din,in.data(),ni*2,cudaMemcpyHostToDevice));CU(cudaMemcpy(dgc,gc.data(),nc*2,cudaMemcpyHostToDevice));
 std::vector<precision_t>a(nc),b(nc),u(ni),v(ni);
 for(int mask=0;mask<8;mask++){
   CU(cudaMemcpy(dc,cat.data(),nc*2,cudaMemcpyHostToDevice));
   nh_pass_kernel<<<(B*NH_PASS_DIM+255)/256,256>>>(dc,din,ds,di,mask,17,B);
   CU(cudaGetLastError());CU(cudaMemcpy(a.data(),dc,nc*2,cudaMemcpyDeviceToHost));
   CU(cudaMemcpy(dc,cat.data(),nc*2,cudaMemcpyHostToDevice));
   nh_pass_fast_kernel<<<B,256>>>(dc,din,ds,di,mask,17,B);
   CU(cudaGetLastError());CU(cudaMemcpy(b.data(),dc,nc*2,cudaMemcpyDeviceToHost));
   CU(cudaMemcpy(dg,grad.data(),ni*2,cudaMemcpyHostToDevice));
   nh_passbwd_kernel<<<(ni+255)/256,256>>>(dg,dgc,ds,di,mask,17,B);
   CU(cudaGetLastError());CU(cudaMemcpy(u.data(),dg,ni*2,cudaMemcpyDeviceToHost));
   CU(cudaMemcpy(dg,grad.data(),ni*2,cudaMemcpyHostToDevice));
   nh_passbwd_fast_kernel<<<B,256>>>(dg,dgc,ds,di,mask,17,B);
   CU(cudaGetLastError());CU(cudaMemcpy(v.data(),dg,ni*2,cudaMemcpyDeviceToHost));
   int df=0,db=0;for(int i=0;i<nc;i++)df+=memcmp(&a[i],&b[i],2)!=0;for(int i=0;i<ni;i++)db+=memcmp(&u[i],&v[i],2)!=0;
   printf("{\"B\":%d,\"mode\":%d,\"mask\":%d,\"forward_values\":%d,\"backward_values\":%d,\"forward_different\":%d,\"backward_different\":%d}\n",B,mode,mask,nc,ni,df,db);fflush(stdout);
   assert(!df&&!db);
 }
 for(void* p:{(void*)di,(void*)ds,(void*)din,(void*)dg,(void*)dc,(void*)dgc})CU(cudaFree(p));
}
int main(){for(int B:{1,3,31,512})for(int mode=0;mode<5;mode++)check(B,mode);}
'''
src=d/'test.cu'
src.write_text(prefix+'\n#ifndef NH_NO_APANEL\n'+helper+'\n#endif\n'+reference+(r/'source/ocean/nethack/pass_fast.cuh').read_text()+main)
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
allrows=[]
for panel in [True,False]:
 label='panel' if panel else 'no_panel'
 command=['nvcc','-O3','-arch=sm_89','-std=c++17',str(src),'-o',str(d/label)]+([] if panel else ['-DNH_NO_APANEL'])
 (d/(label+'_command.json')).write_text(json.dumps(command))
 with (d/(label+'_build.log')).open('w') as f:subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True)
 with (d/(label+'.jsonl')).open('w') as f:subprocess.run([str(d/label)],stdout=f,stderr=subprocess.STDOUT,check=True)
 allrows += [dict(panel=panel,**json.loads(x)) for x in (d/(label+'.jsonl')).read_text().splitlines()]
summary=dict(cases=len(allrows),forward_values=sum(x['forward_values'] for x in allrows),backward_values=sum(x['backward_values'] for x in allrows),all_byte_exact=True,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest())
(d/'summary.json').write_text(json.dumps(summary,indent=2));print(summary,flush=True)
