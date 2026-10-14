__global__ void nh_inv_sfeat_packed_kernel(precision_t* __restrict__ out,
    const nh_obs_t* __restrict__ obs, int B) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= B * NH_INV) return;
    int b = t / NH_INV, s = t % NH_INV;
    const nh_obs_t* src = obs + (int64_t)b * NH_OBS_SIZE + NH_INVST_OFF + s * NH_ST_RAW;
    int st[NH_ST_RAW];
    for (int j = 0; j < NH_ST_RAW; j++) {
        int v = (int)nh_obs_float(src[j]);
        st[j] = v >= 128 ? v - 256 : v; // bytes -> int8
    }
    alignas(16) precision_t f[NH_SFEAT];
    for (int c = 0; c < 4; c++) f[c] = from_float(st[0] == c ? 1.0f : 0.0f);
    int spe_known = st[1] != -128;
    f[4] = from_float((float)spe_known);
    // strict [-1,1]: spe clamp/7; quantity LINEAR capped (log-squash
    // regressed ammo-count .88->.76 across two seeds — counts want scale)
    f[5] = from_float(spe_known ? fmaxf(fminf((float)st[1], 7.0f), -7.0f) * (1.0f / 7.0f) : 0.0f);
    f[6] = from_float(fminf(fmaxf((float)st[2], 0.0f), 30.0f) * (1.0f / 30.0f));
    f[7] = from_float((float)st[3] * (1.0f / 3.0f));
    f[8] = from_float((float)st[4] * (1.0f / 3.0f));
    for (int c = 0; c < 7; c++)
        f[9 + c] = from_float((float)((st[5] >> c) & 1));
    f[16] = from_float((float)st[6]);
    // armor slot category one-hot (suit/shield/helm/gloves/boots/cloak/shirt)
    // from the slot glyph via the engine's baked otyp->ARM_* table
    const nh_obs_t* gsrc = obs + (int64_t)b * NH_OBS_SIZE + NH_INV_OFF + 2 * s;
    int g = (int)nh_obs_float(gsrc[0]) + ((int)nh_obs_float(gsrc[1]) << 8);
    int ot = g - NH_GLYPH_OBJ_OFF;
    int cat = (ot >= 0 && ot < NH_NUM_OBJECTS) ? nh_obj_armcat_dev[ot] : -1;
    for (int c = 0; c < 7; c++)
        f[17 + c] = from_float(cat == c ? 1.0f : 0.0f);
    static_assert(NH_SFEAT * sizeof(precision_t) % 16 == 0, "packed store alignment");
    uint4* dst = (uint4*)(out + (int64_t)t * NH_SFEAT);
    const uint4* values = (const uint4*)f;
    #pragma unroll
    for (int i = 0; i < NH_SFEAT * sizeof(precision_t) / 16; i++) dst[i] = values[i];
}


__global__ void nh_inv_sfeat_flat_kernel(precision_t* __restrict__ out,
    const nh_obs_t* __restrict__ obs, int B) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= B * NH_INV * NH_SFEAT) return;
    int d = t % NH_SFEAT, item = t / NH_SFEAT;
    int b = item / NH_INV, slot = item % NH_INV;
    const nh_obs_t* src = obs + (int64_t)b * NH_OBS_SIZE + NH_INVST_OFF + slot * NH_ST_RAW;
    float f;
    if (d < 17) {
        int field = d < 4 ? 0 : d < 6 ? 1 : d == 6 ? 2 : d < 9 ? d - 4 : d < 16 ? 5 : 6;
        int v = (int)nh_obs_float(src[field]);
        int st = v >= 128 ? v - 256 : v;
        if (d < 4) f = st == d ? 1.0f : 0.0f;
        else if (d == 4) f = (float)(st != -128);
        else if (d == 5) f = st != -128 ? fmaxf(fminf((float)st, 7.0f), -7.0f) * (1.0f / 7.0f) : 0.0f;
        else if (d == 6) f = fminf(fmaxf((float)st, 0.0f), 30.0f) * (1.0f / 30.0f);
        else if (d < 9) f = (float)st * (1.0f / 3.0f);
        else if (d < 16) f = (float)((st >> (d - 9)) & 1);
        else f = (float)st;
    } else {
        const nh_obs_t* gsrc = obs + (int64_t)b * NH_OBS_SIZE + NH_INV_OFF + 2 * slot;
        int g = (int)nh_obs_float(gsrc[0]) + ((int)nh_obs_float(gsrc[1]) << 8);
        int ot = g - NH_GLYPH_OBJ_OFF;
        int cat = (ot >= 0 && ot < NH_NUM_OBJECTS) ? nh_obj_armcat_dev[ot] : -1;
        f = cat == d - 17 ? 1.0f : 0.0f;
    }
    out[t] = from_float(f);
}
