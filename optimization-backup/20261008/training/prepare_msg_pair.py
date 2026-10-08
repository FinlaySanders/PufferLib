from pathlib import Path
r=Path(__file__).parent;p=r/'source/ocean/nethack/nethack.cu';s=p.read_text()
new=[]
for name in ('nh_msg_pool_kernel','nh_msg_bwd_kernel'):
 i=s.index('__global__ void '+name+'(');j=s.index('\n}',i)+2;fn=s[i:j].replace(name,name+'_pair')
 a='''    int b = blockIdx.x;
    if (b >= B) return;
    int d = threadIdx.x;'''
 b='''    int pair=blockIdx.x*2,e=threadIdx.x/NH_MSG_HID,d=threadIdx.x%NH_MSG_HID;
    int same=__syncthreads_and(threadIdx.x<NH_MSG_LEN ?
        (pair+1<B && ids[pair*NH_MSG_LEN+threadIdx.x]==ids[(pair+1)*NH_MSG_LEN+threadIdx.x]) : 1);
    int b=pair+e;
    if(b>=B || (same && e==1))return;'''
 assert a in fn;fn=fn.replace(a,b,1)
 if name=='nh_msg_pool_kernel':
  a='''    out[(int64_t)b * NH_MSG_HID + d] = from_float(acc * rsqrtf((float)count + 1.0f));''';assert a in fn
  fn=fn.replace(a,a+'''\n    if(same)out[(int64_t)(b+1)*NH_MSG_HID+d]=from_float(acc*rsqrtf((float)count+1.0f));''',1)
 else:
  a='''    if (g == 0.0f) return;
    for (int t = 0; t < count; t++)
        nh_fxp_atomic_add(&dmsg_acc[(int64_t)(int)mi[t] * NH_MSG_HID + d], g);'''
  b='''    unsigned long long q=(unsigned long long)(long long)__float2ll_rn(g*NH_FXP);
    if(same) {
        float g1=to_float(grad_concat[(int64_t)(b+1)*NH_CONCAT+NH_MSG_CONCAT_OFF+d])*rsqrtf((float)count+1.0f);
        q+=(unsigned long long)(long long)__float2ll_rn(g1*NH_FXP);
    }
    if(q==0)return;
    for(int t=0;t<count;t++)atomicAdd((unsigned long long*)&dmsg_acc[(int64_t)(int)mi[t]*NH_MSG_HID+d],q);'''
  assert a in fn;fn=fn.replace(a,b,1)
 new.append(fn)
marker='// spell-key forward:';assert marker in s;s=s.replace(marker,'#ifdef PUF_MSG_PAIR\n'+'\n'.join(new)+'\n#endif\n'+marker,1)
a='''    nh_msg_pool_kernel<<<B, NH_MSG_HID, 0, stream>>>(
        a->msg_out.data, ew->msg_w.data, a->msg_ids.data, B);''';assert a in s
s=s.replace(a,'''#ifdef PUF_MSG_PAIR
    if(B>=256)nh_msg_pool_kernel_pair<<<(B+1)/2,2*NH_MSG_HID,0,stream>>>(a->msg_out.data,ew->msg_w.data,a->msg_ids.data,B);
    else
#endif
'''+a,1)
i=s.index('    nh_msg_bwd_kernel<<<B, NH_MSG_HID, 0, stream>>>(');j=s.index(';',i)+1;a=s[i:j]
b=a.replace('nh_msg_bwd_kernel<<<B, NH_MSG_HID','nh_msg_bwd_kernel_pair<<<(B+1)/2, 2*NH_MSG_HID')
s=s[:i]+'#ifdef PUF_MSG_PAIR\n    if(B>=256) {\n'+b+'\n    } else\n#endif\n'+a+s[j:]
p.write_text(s)
