from pathlib import Path
import hashlib
import json

r = Path(__file__).resolve().parent
p = r / 'source/src/algo.cu'
s = p.read_text()
assert 'mingru_scan_forward_regs' not in s
before = hashlib.sha256(p.read_bytes()).hexdigest()
kernels = r'''
// Preload independent gates into registers, then apply the original ordered
// recurrence. No time-parallel approximation or additional activation storage.
template<int TILE>
__global__ void mingru_scan_forward_regs(PrefixScan scan) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int H = scan.H, T = scan.T;
    if (idx >= scan.B * H) return;
    int b = idx / H, h = idx % H;
    int base = b * H * T, cbase = 3 * base;
    float carry = to_float(scan.state_ptr[idx]);
    for (int begin = 0; begin < T; begin += TILE) {
        float zs[TILE], hs[TILE], ps[TILE], xs[TILE];
        bool ends[TILE];
        #pragma unroll
        for (int j = 0; j < TILE; j++) {
            int t = begin + j;
            if (t < T) {
                int off = cbase + 3 * H * t + h;
                float hidden = to_float(__ldg(scan.combined_ptr + off));
                float gate = to_float(__ldg(scan.combined_ptr + off + H));
                float proj = to_float(__ldg(scan.combined_ptr + off + 2 * H));
                zs[j] = sigmoid(gate);
                hs[j] = hidden >= 0.0f ? hidden + 0.5f : sigmoid(hidden);
                ps[j] = sigmoid(proj);
                xs[j] = to_float(__ldg(scan.input_ptr + base + t * H + h));
                ends[j] = scan.terminals_ptr != NULL &&
                    to_float(scan.terminals_ptr[b * T + t]) != 0.0f;
            }
        }
        #pragma unroll
        for (int j = 0; j < TILE; j++) {
            int t = begin + j;
            if (t < T) {
                if (ends[j]) carry = 0.0f;
                int off = base + t * H + h;
                scan.scan_h.data[off] = from_float(carry);
                carry = lerp(carry, hs[j], zs[j]);
                scan.out.data[off] = from_float(ps[j] * carry + (1.0f - ps[j]) * xs[j]);
                carry = to_float(from_float(carry));
            }
        }
    }
    scan.next_state.data[idx] = from_float(carry);
}

template<int TILE>
__global__ void mingru_scan_backward_regs(PrefixScan scan,
        const precision_t* __restrict__ grad_out,
        const precision_t* __restrict__ grad_next_state) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int H = scan.H, T = scan.T;
    if (idx >= scan.B * H) return;
    int b = idx / H, h = idx % H;
    int base = b * H * T, cbase = 3 * base;
    float dh = to_float(grad_next_state[idx]);
    for (int end = T; end > 0; end -= TILE) {
        float zs[TILE], hs[TILE], hps[TILE], outs[TILE];
        bool positive[TILE], ends[TILE];
        #pragma unroll
        for (int j = 0; j < TILE; j++) {
            int t = end - 1 - j;
            if (t >= 0) {
                int off = cbase + 3 * H * t + h;
                int row = base + t * H + h;
                float hidden = to_float(__ldg(scan.combined_ptr + off));
                float gate = to_float(__ldg(scan.combined_ptr + off + H));
                float proj = to_float(__ldg(scan.combined_ptr + off + 2 * H));
                float x = to_float(__ldg(scan.input_ptr + row));
                float gout = to_float(__ldg(grad_out + row));
                float hp = to_float(__ldg(scan.scan_h.data + row));
                float z = sigmoid(gate);
                float ht = hidden >= 0.0f ? hidden + 0.5f : sigmoid(hidden);
                float ps = sigmoid(proj);
                float h_t = lerp(hp, ht, z);
                scan.grad_input.data[row] = from_float(gout * (1.0f - ps));
                scan.grad_combined.data[off + 2 * H] =
                    from_float(gout * (h_t - x) * ps * (1.0f - ps));
                zs[j] = z;
                hs[j] = ht;
                hps[j] = hp;
                outs[j] = gout * ps;
                positive[j] = hidden >= 0.0f;
                ends[j] = scan.terminals_ptr != NULL &&
                    to_float(scan.terminals_ptr[b * T + t]) != 0.0f;
            }
        }
        #pragma unroll
        for (int j = 0; j < TILE; j++) {
            int t = end - 1 - j;
            if (t >= 0) {
                int off = cbase + 3 * H * t + h;
                float z = zs[j], ht = hs[j];
                float total = dh + outs[j];
                float dht = total * z;
                float dz = total * (ht - hps[j]);
                scan.grad_combined.data[off] = from_float(
                    positive[j] ? dht : dht * ht * (1.0f - ht));
                scan.grad_combined.data[off + H] = from_float(dz * z * (1.0f - z));
                dh = total * (1.0f - z);
                if (ends[j]) dh = 0.0f;
            }
        }
    }
    scan.grad_state.data[idx] = from_float(dh);
}
'''
marker = '// Coalesced T-tile load + sequential apply.'
assert s.count(marker) == 1
s = s.replace(marker, kernels + '\n' + marker)
for direction, bit in [('forward', 1), ('backward', 2)]:
    old = f'        if ((getenv("PUF_SCAN_ROW") && (atoi(getenv("PUF_SCAN_ROW")) & {bit}))'
    assert s.count(old) == 1
    args = 'scan' if direction == 'forward' else 'scan, grad.data, a->grad_next_state.data'
    new = f'''        if (getenv("PUF_SCAN_REGS") && (atoi(getenv("PUF_SCAN_REGS")) & {bit})) {{
            int tile = getenv("PUF_SCAN_REG_TILE") ? atoi(getenv("PUF_SCAN_REG_TILE")) : 4;
            int block = 128;
            int grid = (scan.B * scan.H + block - 1) / block;
#define NH_REG_SCAN(T) mingru_scan_{direction}_regs<T><<<grid, block, 0, stream>>>({args})
            if (tile == 2) {{ NH_REG_SCAN(2); }}
            else if (tile == 4) {{ NH_REG_SCAN(4); }}
            else if (tile == 8) {{ NH_REG_SCAN(8); }}
            else {{ assert(false); }}
#undef NH_REG_SCAN
        }} else if ((getenv("PUF_SCAN_ROW") && (atoi(getenv("PUF_SCAN_ROW")) & {bit}))'''
    s = s.replace(old, new)
p.write_text(s)
(r / 'SCAN_REGISTERS_SOURCE.json').write_text(json.dumps({
    'before_sha256': before,
    'after_sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
    'hypothesis': 'Overlap independent gate loads/activations inside each thread, retaining ordered state/gradient recurrences; avoid shared-tile barriers.',
    'tiles': [2, 4, 8],
    'scope': 'Isolated source, disabled by default. No precision or architecture change.'
}, indent=2))
print('Prepared register-prefetch scan; build deferred until current timings finish.')
