"""Stage A part 2: fused encoder front (NH_FRONT_FUSED=1): insert the kernel and route the inference forward through it."""
from pathlib import Path
f=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/ocean/nethack/nethack.cu'); t=f.read_text()
kern=Path('/puffertank/experiments/nethack-latency-20261014/stageA/front_kernel.cu').read_text()
def rep(old,new,count=1):
    global t; assert t.count(old)==count, (t.count(old), old[:80]); t=t.replace(old,new)
anchor="static Prec nethack_encoder_forward(void* w, void* activations, Prec input, cudaStream_t stream) {"
rep(anchor, kern+"\n"+anchor)
rep("""    if (nh_refresh_tables) {
    nh_eff_embed_kernel<<<nh_narrow_grid(grid_size(NH_GLYPH_VOCAB * NH_EMBED_DIM), a->training), BLOCK_SIZE, 0, stream>>>(
        a->e_eff.data, ew->embed_w.data, ew->ekind_w.data, ew->esub_w.data);
    }
""",
"""    if (nh_refresh_tables) {
    nh_eff_embed_kernel<<<nh_narrow_grid(grid_size(NH_GLYPH_VOCAB * NH_EMBED_DIM), a->training), BLOCK_SIZE, 0, stream>>>(
        a->e_eff.data, ew->embed_w.data, ew->ekind_w.data, ew->esub_w.data);
    }
    bool front = nh_front_fused && !a->training;
    if (front) {
        if (nh_refresh_tables) {
        nh_inv_table_kernel<<<nh_narrow_grid(grid_size(NH_GLYPH_VOCAB * NH_INV_HID), a->training), BLOCK_SIZE, 0, stream>>>(
            a->inv_T.data, a->e_eff.data, ew->inv1_w.data);
        nh_inv_table_kernel<<<nh_narrow_grid(grid_size(NH_GLYPH_VOCAB * NH_INV_HID), a->training), BLOCK_SIZE, 0, stream>>>(
            a->invt_T.data, a->e_eff.data, ew->invt_w.data);
        }
#ifdef NH_MSG_FROZEN
        cudaMemcpyAsync(ew->msg_w.data, nh_msg_w0_dev, (size_t)NH_MSG_VOCAB * NH_MSG_HID * sizeof(precision_t), cudaMemcpyDeviceToDevice, stream);
#endif
        nh_front_kernel<<<B, 256, 0, stream>>>(a->glyph_idx.data, a->crop_glyph.data, a->x_local.data, ew->locc_w.data, nh_locc_lut_dev,
            a->terr_tf.data, nh_terrc_lut_dev, nh_secband_lut_dev,
            a->inv_idx.data, a->invt_idx.data, a->inv_sfeat.data,
            a->inv_out.data, a->inv_T.data, ew->inv1_b.data, ew->inv1s_w.data, a->invt_T.data,
            a->bl_feats.data,
            a->msg_ids.data, a->msg_out.data, ew->msg_w.data,
            a->lm_tok.data, a->lm_gid.data, a->li_tok.data, a->li_gid.data, a->e_eff.data, nh_haz_lut_dev,
            a->spk_keys.data, a->spk_in.data, a->spell_idx.data, ew->spk_w.data,
            a->concat.data, a->ide_idx.data, ew->ide_role_w.data, ew->ide_race_w.data, ew->ide_gend_w.data, ew->ide_algn_w.data,
            NH_FRONT_NOPASS, NH_MINV_OFF + 2 * NH_MV, (const nh_obs_t*)input.data, B);
    }
""")
for first in ["    nh_decode_kernel<<<nh_narrow_grid(grid_size(B * NH_MGRID), a->training), BLOCK_SIZE, 0, stream>>>(",
              "    nh_crop_kernel<<<nh_narrow_grid(grid_size(B * NH_CGRID), a->training), BLOCK_SIZE, 0, stream>>>(",
              "    nh_loc3_gather_kernel<<<nh_narrow_grid(grid_size(B * NH_LOC_IN), a->training), BLOCK_SIZE, 0, stream>>>(",
              "    nh_terr_feat_kernel<<<B, 256, 0, stream>>>(",
              "    nh_sfeat_launch(a->inv_sfeat.data, (const nh_obs_t*)input.data, B, stream);",
              "    nh_inv_gather_kernel<<<nh_narrow_grid(grid_size(B * NH_INV_FLAT), a->training), BLOCK_SIZE, 0, stream>>>(",
              "    nh_blstats_kernel<<<grid_size(B * 32), BLOCK_SIZE, 0, stream>>>(",
              "    nh_msg_ids_kernel<<<nh_narrow_grid(grid_size(B * NH_MSG_LEN), a->training), BLOCK_SIZE, 0, stream>>>(",
              "    nh_msg_pool_kernel<<<B, NH_MSG_HID, 0, stream>>>(",
              "    nh_spkey_kernel<<<nh_narrow_grid(grid_size(B * NH_SPELL_SLOTS * NH_SPKEY), a->training), BLOCK_SIZE, 0, stream>>>(",
              "    nh_sp_doorstep_kernel<<<grid_size(B * 4), BLOCK_SIZE, 0, stream>>>("]:
    rep(first, "    if (!front) "+first.strip())
rep("    nh_inv_decode_kernel<<<nh_narrow_grid(grid_size(B * NH_INV), a->training), BLOCK_SIZE, 0, stream>>>(",
    "    if (!front) nh_inv_decode_kernel<<<nh_narrow_grid(grid_size(B * NH_INV), a->training), BLOCK_SIZE, 0, stream>>>(", count=2)
rep("    nh_lab_tok_kernel<<<nh_narrow_grid(grid_size(B * NH_LABK * NH_LAB_IN), a->training), BLOCK_SIZE, 0, stream>>>(",
    "    if (!front) nh_lab_tok_kernel<<<nh_narrow_grid(grid_size(B * NH_LABK * NH_LAB_IN), a->training), BLOCK_SIZE, 0, stream>>>(", count=2)
rep("""    if (nh_refresh_tables) {
    nh_inv_table_kernel<<<""", """    if (!front && nh_refresh_tables) {
    nh_inv_table_kernel<<<""")
rep("""    nh_pass_launch(
        a->concat.data, a->inv_out.data, a->inv_sfeat.data, a->inv_idx.data,""",
    """    if (!front) nh_pass_launch(
        a->concat.data, a->inv_out.data, a->inv_sfeat.data, a->inv_idx.data,""", count=2)
rep("""    if (getenv("NH_IDENTITY_WARP")) {
    nh_idemb_warp_kernel<<<""", """    if (!front) { if (getenv("NH_IDENTITY_WARP")) {
    nh_idemb_warp_kernel<<<""")
rep("""    }
    NH_MM_BR(&a->concat, &ew->proj_w, &a->out, ew->proj_b);
    return a->out;""", """    } }
    NH_MM_BR(&a->concat, &ew->proj_w, &a->out, ew->proj_b);
    return a->out;""")
f.write_text(t); print('front applied; forward launches gated:', t.count('if (!front)'))
