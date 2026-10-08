#include <vector>
#define CK(x) do {cudaError_t e=(x);if(e!=cudaSuccess){fprintf(stderr,"CUDA %s:%d %s\n",__FILE__,__LINE__,cudaGetErrorString(e));exit(2);}}while(0)
template<class T> T* alloc_test(size_t n){T*p;CK(cudaMalloc(&p,n*sizeof(T)));return p;}
static void equal_test(const void*a,const void*b,size_t n,const char*tag,int B,int mode,int rep){std::vector<unsigned char>x(n),y(n);CK(cudaMemcpy(x.data(),a,n,cudaMemcpyDeviceToHost));CK(cudaMemcpy(y.data(),b,n,cudaMemcpyDeviceToHost));if(memcmp(x.data(),y.data(),n)){size_t i=0;while(x[i]==y[i])i++;fprintf(stderr,"FAIL %s B=%d mode=%d rep=%d byte=%zu %u!=%u\n",tag,B,mode,rep,i,x[i],y[i]);exit(3);}}
int main(){
 int sizes[]=ACT_SIZES,A=0;for(int h=0;h<NUM_ATNS;h++)A+=sizes[h];int*ds=alloc_test<int>(NUM_ATNS);CK(cudaMemcpy(ds,sizes,sizeof(sizes),cudaMemcpyHostToDevice));
 int nv,na;const signed char*hm=env_head_consume_map(&nv,&na);signed char*dm=alloc_test<signed char>(nv*na);CK(cudaMemcpy(dm,hm,nv*na,cudaMemcpyHostToDevice));CK(cudaMemcpyToSymbol(d_hc_stride,&na,sizeof(na)));float*de=alloc_test<float>(1);CK(cudaMemcpyToSymbol(d_veps_dev,&de,sizeof(de)));
 unsigned int seed=17;auto rnd=[&](){seed=1664525u*seed+1013904223u;return seed;};long checked=0;
 for(int B:{1,7,31,32,33,128,129,512,1024}){
  Prec logits={.data=alloc_test<precision_t>((size_t)B*(A+1)),.shape={B,A+1}},ls={};auto mask=alloc_test<precision_t>((size_t)B*A);
  float *act[2],*ea[2];precision_t*lp[2],*val[2];curandStatePhilox4_32_10_t*rs[2];for(int k=0;k<2;k++){act[k]=alloc_test<float>(B*NUM_ATNS);ea[k]=alloc_test<float>(B*NUM_ATNS);lp[k]=alloc_test<precision_t>(B);val[k]=alloc_test<precision_t>(B);rs[k]=alloc_test<curandStatePhilox4_32_10_t>(B);CK(cudaMemset(rs[k],0,B*sizeof(*rs[k])));}
  auto launch=[&](int k,cudaStream_t st){if(k==0)sample_logits<<<grid_size(B),BLOCK_SIZE,0,st>>>(logits,ls,ds,act[k],ea[k],lp[k],val[k],rs[k],mask,A);else sample_logits_heads<<<B,32,0,st>>>(logits,ls,ds,act[k],ea[k],lp[k],val[k],rs[k],mask,A);};
  for(int mode=0;mode<6;mode++)for(float eps:{0.f,.05f,.3f,1.f})for(int cond=0;cond<2;cond++){
   const signed char*mp=cond?dm:NULL;CK(cudaMemcpyToSymbol(d_hc_dev,&mp,sizeof(mp)));CK(cudaMemcpy(de,&eps,sizeof(eps),cudaMemcpyHostToDevice));std::vector<precision_t>x(B*(A+1)),m(B*A);
   for(auto&v:x){float f=((int)(rnd()%20001)-10000)/1000.f;if(mode==1)f=0;if(mode==2)f*=1000;v=from_float(f);}
   for(int b=0;b<B;b++){int off=0;for(int h=0;h<NUM_ATNS;h++){int only=rnd()%sizes[h];for(int j=0;j<sizes[h];j++){int yes=(rnd()%4)!=0;if(mode==3)yes=j==only;if(mode==4)yes=0;if(mode==5)yes=j!=sizes[h]-1;m[b*A+off+j]=from_float((float)yes);}off+=sizes[h];}}
   CK(cudaMemcpy(logits.data,x.data(),x.size()*sizeof(x[0]),cudaMemcpyHostToDevice));CK(cudaMemcpy(mask,m.data(),m.size()*sizeof(m[0]),cudaMemcpyHostToDevice));rng_init<<<grid_size(B),BLOCK_SIZE>>>(rs[0],12345+mode,B);CK(cudaMemcpy(rs[1],rs[0],B*sizeof(*rs[0]),cudaMemcpyDeviceToDevice));
   for(int rep=0;rep<8;rep++){launch(0,0);launch(1,0);CK(cudaDeviceSynchronize());equal_test(act[0],act[1],B*NUM_ATNS*sizeof(float),"actions",B,mode,rep);equal_test(ea[0],ea[1],B*NUM_ATNS*sizeof(float),"env_actions",B,mode,rep);equal_test(lp[0],lp[1],B*sizeof(precision_t),"logprobs",B,mode,rep);equal_test(val[0],val[1],B*sizeof(precision_t),"values",B,mode,rep);equal_test(rs[0],rs[1],B*sizeof(*rs[0]),"rng",B,mode,rep);checked+=B;}
  }
  if(B==128 || B==512){cudaStream_t st;CK(cudaStreamCreate(&st));for(int k:{0,1,0}){cudaGraph_t g;cudaGraphExec_t ex;CK(cudaStreamBeginCapture(st,cudaStreamCaptureModeGlobal));for(int i=0;i<200;i++)launch(k,st);CK(cudaStreamEndCapture(st,&g));CK(cudaGraphInstantiate(&ex,g,0));cudaEvent_t t0,t1;CK(cudaEventCreate(&t0));CK(cudaEventCreate(&t1));CK(cudaGraphLaunch(ex,st));CK(cudaStreamSynchronize(st));CK(cudaEventRecord(t0,st));for(int j=0;j<10;j++)CK(cudaGraphLaunch(ex,st));CK(cudaEventRecord(t1,st));CK(cudaEventSynchronize(t1));float ms;CK(cudaEventElapsedTime(&ms,t0,t1));printf("TIME B=%d variant=%d us=%.5f\n",B,k,ms*1000/2000);CK(cudaEventDestroy(t0));CK(cudaEventDestroy(t1));CK(cudaGraphExecDestroy(ex));CK(cudaGraphDestroy(g));}CK(cudaStreamDestroy(st));}
  CK(cudaFree(logits.data));CK(cudaFree(mask));for(int k=0;k<2;k++){CK(cudaFree(act[k]));CK(cudaFree(ea[k]));CK(cudaFree(lp[k]));CK(cudaFree(val[k]));CK(cudaFree(rs[k]));}
  printf("PASS B=%d checked=%ld\n",B,checked);fflush(stdout);
 }
 printf("PASS all bit-exact samples=%ld heads=%d\n",checked,NUM_ATNS);return 0;
}
