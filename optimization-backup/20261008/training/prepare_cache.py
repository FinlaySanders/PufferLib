from pathlib import Path
r=Path(__file__).parent;p=r/'source/ocean/nethack/nethack.cu';s=p.read_text();a='static Prec nethack_encoder_forward('
s=s.replace(a,'#ifdef PUF_CACHE_TABLES\nthread_local bool nh_refresh_tables=true;\n#endif\n\n'+a,1)
old='''    nh_eff_embed_kernel<<<grid_size(NH_GLYPH_VOCAB * NH_EMBED_DIM), BLOCK_SIZE, 0, stream>>>(
        a->e_eff.data, ew->embed_w.data, ew->ekind_w.data, ew->esub_w.data);'''
assert old in s;s=s.replace(old,'#ifdef PUF_CACHE_TABLES\n    if(nh_refresh_tables)\n#endif\n'+old,1)
old='''    nh_inv_table_kernel<<<grid_size(NH_GLYPH_VOCAB * NH_INV_HID), BLOCK_SIZE, 0, stream>>>(
        a->inv_T.data, a->e_eff.data, ew->inv1_w.data);
    nh_inv_table_kernel<<<grid_size(NH_GLYPH_VOCAB * NH_INV_HID), BLOCK_SIZE, 0, stream>>>(
        a->invt_T.data, a->e_eff.data, ew->invt_w.data);'''
assert old in s;s=s.replace(old,'#ifdef PUF_CACHE_TABLES\n    if(nh_refresh_tables) {\n#endif\n'+old+'\n#ifdef PUF_CACHE_TABLES\n    }\n#endif',1);p.write_text(s)
p=r/'source/src/pufferl.cu';s=p.read_text();old='        Prec dec = arch_forward(&pol->arch, *w, *acts, obs_b, *st, stream);';assert old in s;s=s.replace(old,'''#ifdef PUF_CACHE_TABLES
        nh_refresh_tables=(t==0);
#endif
'''+old+'''
#ifdef PUF_CACHE_TABLES
        nh_refresh_tables=true;
#endif''',1);p.write_text(s)
