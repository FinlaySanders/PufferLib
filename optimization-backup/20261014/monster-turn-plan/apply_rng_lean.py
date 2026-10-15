"""NH_RNG_LEAN (compile-time arm, OFF in every exact build): the user-permitted RNG-semantics change.
 R1 generator: wyrand-style 64-bit state behind the ISAAC64 API (isaac64_init/reseed/next_uint64), seeded by splitmix64 over the
    folded seed bytes. A different, statistically equivalent stream; ISAAC64's refill was 3.3% of all instructions.
 R2 RND(x): Lemire multiply-shift range reduction instead of the 64-bit modulo (one 64x64->128 multiply instead of a hardware divide;
    bias <= x / 2^64).
 R3 mcalcmove(): the rn2(NORMAL_SPEED) draw whose result cannot matter (mmove_adj == 0) is not taken.
Everything is inside #ifdef NH_RNG_LEAN; the exact builds compile the original code."""
from pathlib import Path
src = Path('/puffertank/experiments/nethack-monster-turn-plan-20261014/engines/mt2/source')
def rep(p, old, new, count=1):
    t = (src / p).read_text()
    if old not in t or new in t: print('  already:', p, old[:50].strip()); return
    assert t.count(old) == count, (p, t.count(old), old[:90]); (src / p).write_text(t.replace(old, new))

# R1: generator
rep('src/isaac64.c', "static void isaac64_update(isaac64_ctx *_ctx){", """#ifdef NH_RNG_LEAN
/* NH_RNG_LEAN: a 64-bit-state generator (wyrand construction) behind the ISAAC64 API; state in _ctx->a, _ctx->n unused */
static uint64_t nh_lean_splitmix(uint64_t *s){
  uint64_t z=(*s+=0x9E3779B97F4A7C15ULL);
  z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL;
  z=(z^(z>>27))*0x94D049BB133111EBULL;
  return z^(z>>31);
}
static uint64_t nh_lean_fold(const unsigned char *_seed,int _nseed,uint64_t s){
  int i;
  for(i=0;i<_nseed;i++)s=(s^(uint64_t)_seed[i])*0x100000001B3ULL;
  return s;
}
void isaac64_init(isaac64_ctx *_ctx,const unsigned char *_seed,int _nseed){
  uint64_t s=nh_lean_fold(_seed,_nseed,0x6A09E667F3BCC908ULL);
  _ctx->a=nh_lean_splitmix(&s);
  _ctx->b=_ctx->c=0;
  _ctx->n=0;
}
void isaac64_reseed(isaac64_ctx *_ctx,const unsigned char *_seed,int _nseed){
  uint64_t s=nh_lean_fold(_seed,_nseed,_ctx->a^0x510E527FADE682D1ULL);
  _ctx->a^=nh_lean_splitmix(&s);
}
uint64_t isaac64_next_uint64(isaac64_ctx *_ctx){
  uint64_t a=(_ctx->a+=0xA0761D6478BD642FULL);
  unsigned __int128 t=(unsigned __int128)a*(a^0xE7037ED1A0B428DBULL);
  return (uint64_t)(t>>64)^(uint64_t)t;
}
#else
static void isaac64_update(isaac64_ctx *_ctx){""")
rep('src/isaac64.c', """uint64_t isaac64_next_uint64(isaac64_ctx *_ctx){
  if(!_ctx->n)isaac64_update(_ctx);
  return _ctx->r[--_ctx->n];
}
""", """uint64_t isaac64_next_uint64(isaac64_ctx *_ctx){
  if(!_ctx->n)isaac64_update(_ctx);
  return _ctx->r[--_ctx->n];
}
#endif /* NH_RNG_LEAN */
""")

# R2: range reduction without the divide
rep('src/rnd.c', """static int
RND(int x)
{
    int r = (int) (isaac64_next_uint64(nle_rng_state(CORE)) % x);
""", """static int
RND(int x)
{
#ifdef NH_RNG_LEAN
    int r = (int) (((unsigned __int128) isaac64_next_uint64(nle_rng_state(CORE)) * (unsigned long) x) >> 64);
#else
    int r = (int) (isaac64_next_uint64(nle_rng_state(CORE)) % x);
#endif
""")

# R3: the dead speed-rounding draw
rep('src/mon.c', """    mmove_adj = mmove % NORMAL_SPEED;
    mmove -= mmove_adj;
    if (rn2(NORMAL_SPEED) < mmove_adj)
        mmove += NORMAL_SPEED;
""", """    mmove_adj = mmove % NORMAL_SPEED;
    mmove -= mmove_adj;
#ifdef NH_RNG_LEAN
    if (mmove_adj && rn2(NORMAL_SPEED) < mmove_adj) /* a draw that cannot change anything is not taken */
#else
    if (rn2(NORMAL_SPEED) < mmove_adj)
#endif
        mmove += NORMAL_SPEED;
""")
print('rng lean arm applied (inert without -DNH_RNG_LEAN)')
