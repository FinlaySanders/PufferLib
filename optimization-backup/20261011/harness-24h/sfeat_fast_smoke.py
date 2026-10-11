from pathlib import Path
import hashlib,json,subprocess
r=Path(__file__).resolve().parent;d=r/'sfeat_fast_smoke';d.mkdir(exist_ok=False)
s=(r/'source/ocean/nethack/nethack.cu').read_text();a=s.index('static __device__ const signed char nh_obj_armcat_dev');b=s.index('\n};',a)+3
table=s[a:b]
prefix=r'''
#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>
#define CU(x) do { cudaError_t e=(x); if(e!=cudaSuccess) {fprintf(stderr,"%s:%d %s\n",__FILE__,__LINE__,cudaGetErrorString(e));abort();} } while(0)
#ifdef FLOAT_TEST
using precision_t=float;
#define from_float(x) (x)
#else
using precision_t=__nv_bfloat16;
#define from_float(x) __float2bfloat16(x)
#endif
using nh_obs_t=unsigned char;
__device__ __forceinline__ float nh_obs_float(nh_obs_t x){return (float)x;}
#define NH_INV 55
#define NH_SFEAT 24
#define NH_ST_RAW 8
#define NH_NUM_OBJECTS 454
#define NH_GLYPH_OBJ_OFF 1906
#define NH_OBS_SIZE 8192
#define NH_INV_OFF 4096
#define NH_INVST_OFF (NH_INV_OFF+NH_INV*2)
'''
main=r'''
uint32_t rng=90210;
uint32_t next(){rng=1664525U*rng+1013904223U;return rng;}
void check(int B,int mode){
 int N=B*NH_OBS_SIZE,n=B*NH_INV*NH_SFEAT;
 std::vector<nh_obs_t>obs(N);
 for(auto& x:obs)x=next()>>24;
 for(int b=0;b<B;b++)for(int k=0;k<NH_INV;k++){
   int i=b*NH_INV+k,g=i%3==0?i%NH_NUM_OBJECTS+NH_GLYPH_OBJ_OFF:i%3==1?65535:0;
   obs[b*NH_OBS_SIZE+NH_INV_OFF+2*k]=g&255;obs[b*NH_OBS_SIZE+NH_INV_OFF+2*k+1]=(g>>8)&255;
   if(mode)for(int j=0;j<NH_ST_RAW;j++)obs[b*NH_OBS_SIZE+NH_INVST_OFF+k*NH_ST_RAW+j]=(mode==1?i:mode==2?0:255)&255;
 }
 nh_obs_t* di;precision_t *out;CU(cudaMalloc(&di,N));CU(cudaMalloc(&out,(n+32)*sizeof(precision_t)));
 CU(cudaMemcpy(di,obs.data(),N,cudaMemcpyHostToDevice));
 std::vector<precision_t>ref(n+32),value(n+32);
 for(int variant=0;variant<3;variant++){
   CU(cudaMemset(out,0x3c,(n+32)*sizeof(precision_t)));
   if(variant==0)nh_inv_sfeat_kernel<<<(B*NH_INV+255)/256,256>>>(out,di,B);
   if(variant==1)nh_inv_sfeat_packed_kernel<<<(B*NH_INV+255)/256,256>>>(out,di,B);
   if(variant==2)nh_inv_sfeat_flat_kernel<<<(n+255)/256,256>>>(out,di,B);
   CU(cudaGetLastError());CU(cudaMemcpy(value.data(),out,(n+32)*sizeof(precision_t),cudaMemcpyDeviceToHost));
   if(!variant)ref=value;
   int different=0;for(int j=0;j<n+32;j++)different+=memcmp(&ref[j],&value[j],sizeof(precision_t))!=0;
   printf("{\"B\":%d,\"mode\":%d,\"variant\":%d,\"values\":%d,\"different\":%d}\n",B,mode,variant,n+32,different);fflush(stdout);assert(!different);
 }
 CU(cudaFree(di));CU(cudaFree(out));
}
int main(){for(int B:{1,3,31,512})for(int mode=0;mode<4;mode++)check(B,mode);}
'''
src=d/'test.cu';src.write_text(prefix+table+'\n'+(r/'sfeat_reference.cu.txt').read_text()+(r/'sfeat_fast_kernels.cuh.txt').read_text()+main)
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
rows=[]
for fp32 in [False,True]:
 label='fp32' if fp32 else 'bf16';cmd=['nvcc','-O2','-arch=sm_89','-std=c++17','-Xptxas=-v',str(src),'-o',str(d/label)]+(['-DFLOAT_TEST']if fp32 else [])
 (d/(label+'_command.json')).write_text(json.dumps(cmd))
 with (d/(label+'_build.log')).open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 with (d/(label+'.jsonl')).open('w') as f:subprocess.run([str(d/label)],stdout=f,stderr=subprocess.STDOUT,check=True)
 rows+=[dict(dtype=label,**json.loads(x)) for x in (d/(label+'.jsonl')).read_text().splitlines()]
summary=dict(cases=len(rows),values=sum(x['values'] for x in rows),all_byte_exact=True,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest())
(d/'summary.json').write_text(json.dumps(summary,indent=2));print(summary,flush=True)
