from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/algo.cu';s=p.read_text()
a='''void puf_mm_tn_async_after(Prec* a, Prec* b, Prec* out, cudaStream_t main_stream) {
    cudaEventRecord(g_main_ready, main_stream);'''
b='''#ifdef PUF_DW_DEFER
struct DeferredDW { Prec a,b,out; };
thread_local DeferredDW deferred_dw[64];thread_local int deferred_count=0;
#endif
void puf_mm_tn_async_after(Prec* a, Prec* b, Prec* out, cudaStream_t main_stream) {
#ifdef PUF_DW_SERIAL
    puf_mm_tn(a,b,out,main_stream);return;
#endif
#ifdef PUF_DW_DEFER
    assert(deferred_count<64);deferred_dw[deferred_count++]={*a,*b,*out};return;
#endif
    cudaEventRecord(g_main_ready, main_stream);''';assert a in s;s=s.replace(a,b,1)
a='''void puf_dw_join(cudaStream_t consumer) {
    cudaEventRecord'''
b='''void puf_dw_join(cudaStream_t consumer) {
#ifdef PUF_DW_SERIAL
    return;
#endif
#ifdef PUF_DW_DEFER
    for(int i=0;i<deferred_count;i++){auto& d=deferred_dw[i];puf_mm_tn(&d.a,&d.b,&d.out,consumer);}
    deferred_count=0;return;
#endif
    cudaEventRecord''';assert a in s;s=s.replace(a,b,1);p.write_text(s)
p=r/'source/src/pufferl.cu';s=p.read_text();a='''void close_pufferl(PuffeRL* p) {
    if (p->hypers.profile) {''';assert a in s
s=s.replace(a,'''void close_pufferl(PuffeRL* p) {
    if (p->hypers.profile && !getenv("PUF_SKIP_PROF_STOP")) {''',1);p.write_text(s)
