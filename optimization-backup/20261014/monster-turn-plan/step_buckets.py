"""Whole-step callgrind (self Ir by function) → bucket shares; usage: step_buckets.py <callgrind_annotate --inclusive=no output> <steps>"""
import re, sys
from collections import defaultdict
path, steps = sys.argv[1], float(sys.argv[2])
rows=[]
for l in open(path, errors='replace'):
    m=re.match(r'\s*([\d,]+)\s+\(\s*([\d.]+)%\)\s+(\S+)', l)
    if m and ':' in m.group(3): rows.append((int(m.group(1).replace(',','')), m.group(3)))
total=sum(r[0] for r in rows)
def bucket(name):
    f=name.split(':')[-1]
    src=name.split(':')[0].split('/')[-1]
    if src in ('replay_sched.c','macros.h','nethack.h','puffernet.h') or 'puf_' in f or 'nethack_' in f: return 'harness+obs header'
    if f.startswith(('m_move','mfndpos','dochug','movemon','mt2_','nh_fobj','set_apparxy','distfleeck','find_','mintrap','minliquid','onscary','gettrack','lined_up','linedup','in_your_sanct','can_carry','searches_for','touch_artifact','mattacku','mattackm','dog_move','m_in_out','place_monster','monhaskey','m_carrying','monnear','mcalcmove','mcalcdistress','mon_regen','wipe_engr','disturb','should_displace','itsstuck','m_digweapon','hideunder','mpickstuff','mpickgold','nh_newsym_moved','mm_','undesirable','cant_squeeze','worm_cross','rloc','mhitu','thrwmu','select_rwep','mon_wield','monster_nearby','m_respond','castmu','spitmu','breamu','buzzmu','m_throw','mdig','meatobj','meatmetal','dmonsfree','restrap','mon_track','passes_walls','rn2','rnd','RND','isaac64','rnl')): return 'monster turn (+RNG)'
    if f.startswith(('newsym','vision','left_side','right_side','clear_path','couldsee','cansee','show_glyph','flush_screen','docrt','map_','display_','feel_','bot','update_blstats','newsym_force','curs','tty_','rl_','render','glyph','back_to_glyph','cmap','show_region','see_monsters','see_objects','vision_recalc','does_block','block_point','unblock_point')): return 'vision+display+status'
    if f.startswith(('fill_obs','nle_','NetHackRL','nethack_rl','step','obs','pack','mainloop','nle_step','nle_yield','jump_fcontext','getenv','rl_nh','nle_getenv','nle_get')): return 'obs/nle glue'
    if f.startswith(('moveloop','nh_timeout','run_timers','dosearch','rhack','domove','test_move','flush','regen','u_wipe','encumber','inv_weight','weight','calc_capacity','check_special','settrack','monster_nearby','lookaround','timeout','stop_occupation','interrupt','nomul','unmul','losehp','exerchk','exercise','gethungry','newuhs','u_slow','u_wipe_engr','dosounds','nh_','context','spoteffects','pickup','look_here','check_here','invent','find_ac','dig_check','drop','dodown','doup','goto_level','mklev','makelevel','mkroom','fill_','rndmonst','makemon','mksobj','mkobj','rndcurse','savelev','getlev','bwrite','mread','restore','save')): return 'hero turn + bookkeeping + level gen'
    if f.startswith(('malloc','free','calloc','realloc','_int_','cfree','__libc','memmove','memcpy','memset','strlen','strcmp','strcpy','strncpy','strstr','strstri','index','sprintf','vsprintf','snprintf','vsnprintf','printf','fprintf','vfprintf','__vfprintf','__printf','_IO_','putc','fputs','Sprintf','Strcpy','Strcat','strcat','lowc','highc','eos','xcrypt','random','rand','pline','vpline','putstr','putmesg','tty_putstr','docorner','an','the','xname','doname','Monnam','mon_nam','x_monnam','distant_name','noit_','minimal_monnam','makeplural','otense','vtense','upstart','s_suffix','fuzzymatch','strcmpi','strncmpi')): return 'libc/alloc/format/names'
    return 'other'
agg=defaultdict(int); top=defaultdict(list)
for ir,name in rows:
    b=bucket(name); agg[b]+=ir; top[b].append((ir,name.split(':')[-1]))
print(f"total {total:,} Ir over {steps:.0f} steps = {total/steps:,.0f} Ir/step")
for b,ir in sorted(agg.items(), key=lambda kv:-kv[1]):
    print(f"\n{b:34s} {100*ir/total:5.1f}%  {ir/steps:8,.0f} Ir/step")
    for x,n in sorted(top[b], reverse=True)[:12]: print(f"    {100*x/total:5.2f}%  {x/steps:8,.0f}  {n}")
