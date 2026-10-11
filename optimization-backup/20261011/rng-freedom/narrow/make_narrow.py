# Grid-narrow the rollout forward's wide elementwise kernels. Bodies become grid-stride loops (identical per-element math);
# launches INSIDE the inference forward functions are capped at PUF_NARROW_BLOCKS when not training (0/unset = unchanged).
import re, sys
from pathlib import Path
root=Path(sys.argv[1])
helper='''
// Grid narrowing for the rollout forward's elementwise kernels (PUF_NARROW_BLOCKS caps the grid; 0 = unchanged; never in training).
static inline int nh_narrow_grid(int blocks, bool training) {
    static thread_local int cap = -1;
    if (cap < 0) cap = getenv("PUF_NARROW_BLOCKS") ? atoi(getenv("PUF_NARROW_BLOCKS")) : 0;
    return (!training && cap > 0 && blocks > cap) ? cap : blocks;
}
'''
def convert_body(src, kernel):
    m=re.search(r'__global__ void '+kernel+r'\(', src); assert m, kernel
    i=src.index('{', m.end()); depth=0; j=i
    while True:
        if src[j]=='{': depth+=1
        elif src[j]=='}':
            depth-=1
            if depth==0: break
        j+=1
    body=src[i+1:j]
    pat=re.compile(r'(\n\s*)int (\w+) = blockIdx\.x \* blockDim\.x \+ threadIdx\.x;((?:\n\s*[^\n;{}]*;)*?)\s*\n\s*if \((\w+) >= ([^)]+)\)\s*(?:\{\s*return;\s*\}|return;)', re.S)
    mm=pat.search(body); assert mm and mm.group(2)==mm.group(4), (kernel, body[:160])
    ind,var,pre,_,bound=mm.groups(); rest=body[mm.end():]
    assert re.search(r'\b'+var+r'\b', pre) is None, (kernel, 'hoisted statement uses the index', pre)
    assert 'return' not in rest.replace('return;',''), (kernel,'non-trivial return')
    rest=rest.replace('return;','continue;')
    newbody=body[:mm.start()]+pre+f'{ind}for (int {var} = blockIdx.x * blockDim.x + threadIdx.x; {var} < {bound}; {var} += gridDim.x * blockDim.x) {{'+rest.rstrip()+'\n    }\n'
    return src[:i+1]+newbody+src[j:]
def cap_region(src, start_pat, end_pat, kernels, flag):
    a=src.index(start_pat); b=src.index(end_pat, a); region=src[a:b]; n=0
    for k in kernels:
        def rep(m):
            nonlocal n; n+=1; return f'{k}<<<nh_narrow_grid({m.group(1)}, {flag}),'
        region=re.sub(re.escape(k)+r'<<<((?:[^<>,]|<[^<>]*>)+?),', rep, region)
    return src[:a]+region+src[b:], n
enc=['nh_decode_kernel','nh_crop_kernel','nh_loc3_gather_kernel','nh_inv_decode_kernel','nh_inv_table_kernel','nh_inv_gather_kernel','nh_concat_kernel','nh_lab_tok_kernel','nh_eff_embed_kernel','nh_msg_ids_kernel','nh_spkey_kernel']
dec=['nh_dec_assemble_kernel','nh_ptr3_cos_kernel']
p=root/'ocean/nethack/nethack.cu'; s=p.read_text()
for k in enc+dec: s=convert_body(s,k)
s,n1=cap_region(s,'static Prec nethack_encoder_forward(','static void nethack_encoder_init_weights(',enc,'a->training')
s,n2=cap_region(s,'static Prec nethack_decoder_forward(','static Prec nethack_decoder_backward(',dec,'a->saved_input.data != NULL')
lines=s.split('\n'); inc=[i for i,l in enumerate(lines) if l.startswith('#include')]; lines.insert(inc[-1]+1,helper); p.write_text('\n'.join(lines))
print(f'nethack.cu: {len(enc)+len(dec)} kernels converted; launches capped encoder {n1} decoder {n2}')
p=root/'src/pufferl.cu'; s=p.read_text()
for k in ['zero_term_state','cast','record_step']: s=convert_body(s,k)
s,n3=cap_region(s,'void pufferl_forward_step(','#ifdef PUF_REUSE_ROLLOUT\nstruct StepRecord',['cast','zero_term_state'],'false')
s,n4=cap_region(s,'static void record_rollout_step(','static void snapshot_rollout_start(',['record_step'],'false')
s,n5=cap_region(s,'static void snapshot_rollout_start(','\n#endif\n\n\n// Startup/capture-only experiment',['zero_term_state'],'false')
lines=s.split('\n'); inc=[i for i,l in enumerate(lines) if l.startswith('#include')]; lines.insert(inc[-1]+1,helper); p.write_text('\n'.join(lines))
print(f'pufferl.cu: 3 kernels converted; launches capped forward_step {n3} record {n4} snapshot {n5}')
