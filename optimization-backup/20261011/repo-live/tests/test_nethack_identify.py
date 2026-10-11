"""Live single-item identify targeting, menu fallback, and head gating.
Run after python3 tests/test_nethack_encoder.py (builds nethack_test.so).
"""
import ctypes as c
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
engine = root / 'vendor/fast-nle'
os.environ['NETHACKDIR'] = str(engine / 'build/dat')
c.CDLL(str(engine / 'build/libnethack.so'), mode=c.RTLD_GLOBAL)
lib = c.CDLL(str(root / 'tests/nethack_test.so'))
with tempfile.TemporaryDirectory() as tmp:
    so = Path(tmp) / 'probe.so'
    subprocess.run(['cc', '-shared', '-fPIC', '-O2', '-DNH_TLS_INITIAL_EXEC',
        '-DNOTPARMDECL', '-DDLB', '-DNOMAIL', '-DNOCLIPPING', '-DNOCWD_ASSUMPTIONS',
        *['-I' + str(engine / p) for p in ['include', 'build/include',
           'third_party/libtmt', 'build/_deps/deboost_context-src/include']],
        str(root / 'tests/nethack_identify_probe.c'), '-o', str(so)], check=True)
    probe = c.CDLL(str(so))
    lib.nh_identify_live.argtypes = [c.c_void_p, c.c_void_p]
    assert lib.nh_identify_live(probe.prepare_identify, probe.check_identify) == 1
for verb in range(26):
    assert lib.nh_identify_gate(verb) == (verb == 20)
lib.nh_identify_menu_choice.argtypes = [c.c_void_p, c.c_int]
screen = bytearray(b' ' * 1920)
title = b'What would you like to identify first?'
screen[:len(title)] = title
screen[80:90] = b'z - a wand'
buf = c.create_string_buffer(bytes(screen))
assert lib.nh_identify_menu_choice(buf, ord('z')) == ord('z')
assert lib.nh_identify_menu_choice(buf, ord('b')) == ord('.')
screen[160:168] = b'(1 of 2)'
buf = c.create_string_buffer(bytes(screen))
assert lib.nh_identify_menu_choice(buf, ord('b')) == ord('>')
buf = c.create_string_buffer(b' ' * 1920)
assert lib.nh_identify_menu_choice(buf, ord('z')) == ord('.')
print('PASS: live target identification, unavailable-target fallback, unrelated menu, READ-only gating')

lib.nh_identify_ppo.argtypes = [c.c_int, c.c_float, c.c_void_p]
def ppo(used, logit):
    out = (c.c_float * 6)()
    lib.nh_identify_ppo(used, logit, out)
    return list(out)
for used in (0, 1):
    baseline = ppo(used, 0)
    assert abs(baseline[3] - 1) < 1e-6, baseline
    lo, hi = ppo(used, -0.001), ppo(used, 0.001)
    numerical = (hi[0] - lo[0]) / 0.002
    assert abs(numerical - baseline[2]) < 0.002, (used, numerical, baseline)
    if not used:
        changed = ppo(used, 3)
        assert changed == baseline, (baseline, changed)
        assert baseline[5] == 0
    else:
        assert baseline[5] > 0
import math
assert abs(ppo(1, 0)[1] - ppo(0, 0)[1] - math.log(55)) < 1e-5
print('PASS: consumed/unused PPO ratios, entropy, exact zero unused-head gradients, finite differences')
