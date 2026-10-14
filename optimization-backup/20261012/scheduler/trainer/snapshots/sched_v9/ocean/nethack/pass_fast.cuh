// Selection metadata is shared by all feature dimensions of a sample.
template<bool backward>
__device__ __forceinline__ void nh_pass_metadata(
    const precision_t* sfeat, const float* vid, int b,
    unsigned int* masks, int* accessory, int* owner) {
    int k = threadIdx.x;
    if (k < 4) owner[k] = NH_INV;
    if (k < 64) {
        bool valid = k < NH_INV && (int)vid[(int64_t)b * NH_INV + k] != NH_PAD_GLYPH;
        float flags[3] = {0, 0, 0};
        if (valid) {
            const precision_t* f = sfeat + ((int64_t)b * NH_INV + k) * NH_SFEAT;
            flags[0] = to_float(f[10]);
            flags[1] = to_float(f[12]);
            flags[2] = to_float(f[9]);
        }
        for (int region = 0; region < 3; region++) {
            bool selected = valid && (backward ? flags[region] > 0.5f : !(flags[region] <= 0.5f));
            unsigned int bits = __ballot_sync(0xffffffffu, selected);
            if ((k & 31) == 0) masks[region * 2 + k / 32] = bits;
        }
    }
#ifndef NH_NO_APANEL
    if (k < NH_INV) accessory[k] = nh_acc_slot(vid, sfeat, b, k);
#endif
    __syncthreads();
#ifndef NH_NO_APANEL
    if (k < NH_INV && accessory[k] >= 0) atomicMin(owner + accessory[k], k);
#endif
    __syncthreads();
}

__device__ __forceinline__ unsigned long long nh_pass_mask(const unsigned int* masks, int region) {
    return (unsigned long long)masks[2 * region] | ((unsigned long long)masks[2 * region + 1] << 32);
}

__global__ void nh_pass_fast_kernel(
    precision_t* __restrict__ concat, const precision_t* __restrict__ inv_out,
    const precision_t* __restrict__ sfeat, const float* __restrict__ vid,
    int nopass, int passoff, int B) {
    int b = blockIdx.x;
    if (b >= B) return;
    if (nopass == 7) {
        for (int d = threadIdx.x; d < NH_PASS_DIM; d += blockDim.x)
            concat[(int64_t)b * NH_CONCAT + passoff + d] = from_float(0.0f);
        return;
    }
    __shared__ unsigned int masks[6];
    __shared__ int accessory[NH_INV], owner[4];
    nh_pass_metadata<false>(sfeat, vid, b, masks, accessory, owner);
    for (int d = threadIdx.x; d < NH_PASS_DIM; d += blockDim.x) {
        precision_t* dst = concat + (int64_t)b * NH_CONCAT + passoff + d;
        *dst = from_float(0.0f);
#ifndef NH_NO_APANEL
        if (d >= 80 + NH_PWORN_DIM) {
            if (nopass & 4) continue;
            int part = d - 80 - NH_PWORN_DIM;
            int which = part / (NH_INV_HID + NH_SFEAT), e = part % (NH_INV_HID + NH_SFEAT);
            int k = owner[which];
            if (k < NH_INV) {
                const precision_t* f = sfeat + ((int64_t)b * NH_INV + k) * NH_SFEAT;
                const precision_t* v = inv_out + ((int64_t)b * NH_INV + k) * NH_INV_HID;
                *dst = e < NH_INV_HID ? v[e] : f[e - NH_INV_HID];
            }
            continue;
        }
#endif
        int region = d < 40 ? 0 : d < 80 ? 1 : 2;
        int j = region == 0 ? d : region == 1 ? d - 40 : d - 80;
        if (nopass & (1 << region)) continue;
        unsigned long long selected = nh_pass_mask(masks, region);
        int count = __popcll(selected);
        float sum = 0.0f;
        precision_t value = from_float(0.0f);
        while (selected) {
            int k = __ffsll((long long)selected) - 1;
            selected &= selected - 1;
            const precision_t* f = sfeat + ((int64_t)b * NH_INV + k) * NH_SFEAT;
            const precision_t* v = inv_out + ((int64_t)b * NH_INV + k) * NH_INV_HID;
            if (region == 2) sum += to_float(v[j]);
            else {
                float x = j < NH_INV_HID ? to_float(v[j]) : to_float(f[j - NH_INV_HID]);
                value = from_float(to_float(value) + x);
            }
        }
        if (region == 2) {
            if (count > 0) *dst = from_float(sum / (float)count);
        } else *dst = value;
    }
}

__global__ void nh_passbwd_fast_kernel(
    precision_t* __restrict__ inv_grad, const precision_t* __restrict__ grad_concat,
    const precision_t* __restrict__ sfeat, const float* __restrict__ vid,
    int nopass, int passoff, int B) {
    int b = blockIdx.x;
    if (b >= B || nopass == 7) return;
    __shared__ unsigned int masks[6];
    __shared__ int accessory[NH_INV], owner[4];
    nh_pass_metadata<true>(sfeat, vid, b, masks, accessory, owner);
    unsigned long long wielded = nh_pass_mask(masks, 0), quivered = nh_pass_mask(masks, 1);
    unsigned long long worn = nh_pass_mask(masks, 2);
    int count = __popcll(worn);
    const precision_t* gp = grad_concat + (int64_t)b * NH_CONCAT + passoff;
    for (int t = threadIdx.x; t < NH_INV * NH_INV_HID; t += blockDim.x) {
        int k = t / NH_INV_HID, d = t % NH_INV_HID;
        if ((int)vid[(int64_t)b * NH_INV + k] == NH_PAD_GLYPH) continue;
        precision_t* dr = inv_grad + (int64_t)b * NH_INV * NH_INV_HID + t;
        unsigned long long bit = 1ULL << k;
        if (!(nopass & 1) && (wielded & bit))
            *dr = from_float(to_float(*dr) + to_float(gp[d]));
        if (!(nopass & 2) && (quivered & bit))
            *dr = from_float(to_float(*dr) + to_float(gp[40 + d]));
        if (!(nopass & 4) && (worn & bit) && count > 0)
            *dr = from_float(to_float(*dr) + to_float(gp[80 + d]) / (float)count);
#ifndef NH_NO_APANEL
        if (!(nopass & 4) && accessory[k] >= 0)
            *dr = from_float(to_float(*dr) + to_float(gp[80 + NH_PWORN_DIM
                + accessory[k] * (NH_INV_HID + NH_SFEAT) + d]));
#endif
    }
}
