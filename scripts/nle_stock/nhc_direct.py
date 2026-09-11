"""Determinism harness: the SAME policy and the SAME reconstruction, reached through
the Python transport instead of the C one, on a game pinned to be identical.

This drives nle.nethack.Nethack directly (raw keys, no gym wrapper, no action-index
table, no reset key presses) so the only remaining difference from nh_stock_backend.c
is the transport itself. Everything else is pinned: seed, wall clock (LD_PRELOAD),
option string, screen descriptions off, redraw hook off, probe crutches off.
"""
import ctypes, os, sys, time, traceback
import numpy as np

os.environ.setdefault("NH_STOCK_STALLCAP", "1000000")
os.environ.setdefault("NH_STOCK_TERRAIN_PROBE", "1")
os.environ.setdefault("NH_HASH_FULL", "1")

from nle import nethack

SP = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(SP, "libnhagent.so")
SEND = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int)
RESET = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)

KEYS = ["glyphs", "chars", "colors", "specials", "blstats", "message",
        "inv_glyphs", "inv_strs", "inv_letters", "inv_oclasses",
        "tty_chars", "tty_colors", "tty_cursor", "misc"]


def _p(a, t):
    return a.ctypes.data_as(ctypes.POINTER(t))


class DirectRunner:
    def __init__(self, weights, seed, keylog):
        self.lib = ctypes.CDLL(LIB)
        self.lib.nhg_set_callback.argtypes = [SEND, RESET, ctypes.c_void_p]
        self.lib.nhg_open.argtypes = [ctypes.c_char_p, ctypes.c_uint]
        self.lib.nhg_policy_step.argtypes = [ctypes.POINTER(ctypes.c_double)]
        self.nh = nethack.Nethack(observation_keys=KEYS)
        print("OPTIONS=" + self.nh._nethackoptions, flush=True)
        self.seed = seed
        self.keylog = keylog
        self.episode = 0
        self.done = True
        self.fatal = None
        self._send = SEND(self._on_key)
        self._reset = RESET(self._on_reset)
        self.lib.nhg_set_callback(self._send, self._reset, None)
        if self.lib.nhg_open(weights.encode(), 0) != 0:
            raise SystemExit("weights failed to load")

    def _push(self, obs, done):
        d = dict(zip(KEYS, obs))
        self.lib.nhg_fill(
            _p(np.ascontiguousarray(d["glyphs"], dtype=np.int16), ctypes.c_short),
            _p(np.ascontiguousarray(d["chars"]), ctypes.c_ubyte),
            _p(np.ascontiguousarray(d["colors"]), ctypes.c_ubyte),
            _p(np.ascontiguousarray(d["specials"]), ctypes.c_ubyte),
            _p(np.ascontiguousarray(d["blstats"], dtype=np.int64), ctypes.c_long),
            _p(np.ascontiguousarray(d["message"]), ctypes.c_ubyte),
            _p(np.ascontiguousarray(d["inv_glyphs"], dtype=np.int16), ctypes.c_short),
            _p(np.ascontiguousarray(d["inv_strs"]), ctypes.c_ubyte),
            _p(np.ascontiguousarray(d["inv_letters"]), ctypes.c_ubyte),
            _p(np.ascontiguousarray(d["inv_oclasses"]), ctypes.c_ubyte),
            _p(np.ascontiguousarray(d["tty_chars"]), ctypes.c_ubyte),
            _p(np.ascontiguousarray(d["tty_colors"], dtype=np.int8), ctypes.c_byte),
            _p(np.ascontiguousarray(d["tty_cursor"]), ctypes.c_ubyte),
            _p(np.ascontiguousarray(d["misc"], dtype=np.int32), ctypes.c_int),
            ctypes.c_int(1 if done else 0), ctypes.c_int(0))

    def _on_reset(self, _ud):
        try:
            # The policy samples from libc rand(), a stream shared across episodes, so
            # two identically-seeded games diverge even with no leaked state. Pinning
            # it makes every episode of a run the same experiment: any difference that
            # survives is state carried across the reset.
            if os.environ.get("NH_PIN_RAND"):
                ctypes.CDLL(None).srand(0)
            if os.environ.get("NH_ZERO_STATE"):
                self.lib.nhg_zero_state()
            sd = self.seed + (self.episode if os.environ.get('NH_SEED_STEP') else 0)
            self.nh.set_initial_seeds(sd, sd, False)
            if self.keylog:
                self.lib.nhg_keylog(f"{self.keylog}/ep{self.episode}.keys".encode())
            obs = self.nh.reset()
            self.episode += 1
            self.done = False
            self._push(obs, False)
            return 0
        except BaseException:
            self.fatal = sys.exc_info(); traceback.print_exc(); self.done = True
            return 1

    def _on_key(self, _ud, key):
        if self.done:
            return 1
        try:
            obs, done = self.nh.step(key)   # raw keypress, exactly as the C backend sends it
            self.done = bool(done)
            self._push(obs, done)
            return 1 if done else 0
        except BaseException:
            self.fatal = sys.exc_info(); traceback.print_exc(); self.done = True
            return 1

    def run(self, episodes):
        out = (ctypes.c_double * 8)()
        n = 0
        while n < episodes:
            self.lib.nhg_policy_step(out)
            if self.fatal:
                raise RuntimeError("env call failed") from self.fatal[1]
            if int(out[0]) > n:
                n = int(out[0])
                print(f"EP {n} done [{time.time():.0f}]", flush=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--keylog", required=True)
    ap.add_argument("--episodes", type=int, default=1)
    a = ap.parse_args()
    os.makedirs(a.keylog, exist_ok=True)
    DirectRunner(os.path.abspath(a.weights), a.seed, a.keylog).run(a.episodes)
