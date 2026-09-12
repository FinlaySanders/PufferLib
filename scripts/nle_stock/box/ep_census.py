#!/usr/bin/env python3
"""Behaviour census over a cert .ep log (one line per finished episode, completion order).
Columns: score how time worst_zero_time_run [role race gender max_depth last_turn killer_mnum+1 killer_mlevel]
(the last seven exist for binaries built after 2026-09-12 11:40). Applies the cert protocol by default: drop the
first 4000 episodes (cold-start censoring), keep the rest.
  python ep_census.py run.ep [--drop 4000] [--keep 10000] [--all]
"""
import sys, statistics, collections
ROLES = ["Archeologist", "Barbarian", "Caveman", "Healer", "Knight", "Monk", "Priest", "Rogue", "Ranger", "Samurai", "Tourist", "Valkyrie", "Wizard"]
RACES = ["human", "elf", "dwarf", "gnome", "orc"]
HOW = {0: "died", 1: "choked", 2: "poisoned", 3: "starved", 4: "drowned", 5: "burned", 6: "dissolved", 7: "crushed", 8: "stoned", 9: "slimed", 10: "genocided", 11: "panicked", 12: "tricked", 13: "quit", 14: "escaped", 15: "ascended", 100: "god's wrath", -1: "truncated/aborted"}

def mon_names():
    try:
        from nle import nethack as n
        return [n.permonst(i).mname for i in range(n.NUMMONS)]
    except Exception:
        return None

def main():
    args = sys.argv[1:]; drop, keep, allrows = 4000, 10000, False; files = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--drop": drop = int(args[i + 1]); i += 2
        elif a == "--keep": keep = int(args[i + 1]); i += 2
        elif a == "--all": allrows = True; i += 1
        else: files.append(a); i += 1
    rows = []
    for f in files:
        for line in open(f):
            p = line.split()
            if len(p) < 4: continue
            rows.append([int(x) for x in p])
    n_all = len(rows)
    if not allrows: rows = rows[drop:drop + keep]
    if not rows: print(f"no rows (total {n_all}, drop {drop})"); return
    scores = [r[0] for r in rows]
    aborted = sum(1 for r in rows if r[3] >= 1000)
    print(f"episodes={len(rows)} (of {n_all}; drop {0 if allrows else drop}) mean={statistics.mean(scores):.0f} median={statistics.median(scores):.0f} "
          f"p10={sorted(scores)[len(scores)//10]} p90={sorted(scores)[len(scores)*9//10]} max={max(scores)} zero-time-aborts={aborted} ({100*aborted/len(rows):.1f}%)")
    hows = collections.Counter(HOW.get(r[1], str(r[1])) for r in rows)
    print("end:", ", ".join(f"{k} {100*v/len(rows):.1f}%" for k, v in hows.most_common()))
    if len(rows[0]) < 11:
        print("(no census columns in this log: role/depth/turn/killer need a binary built after 2026-09-12 11:40)"); return
    print(f"\n{'role':<13}{'n':>6}{'mean':>9}{'median':>9}{'p90':>9}{'depth':>7}{'turns':>8}{'aborts':>8}")
    byrole = collections.defaultdict(list)
    for r in rows: byrole[r[4]].append(r)
    for ri in sorted(byrole, key=lambda k: -statistics.median([r[0] for r in byrole[k]])):
        rs = byrole[ri]; sc = sorted(r[0] for r in rs)
        print(f"{ROLES[ri] if 0 <= ri < 13 else ri:<13}{len(rs):>6}{statistics.mean(sc):>9.0f}{statistics.median(sc):>9.0f}{sc[len(sc)*9//10]:>9}"
              f"{statistics.mean(r[7] for r in rs):>7.2f}{statistics.median(r[8] for r in rs):>8.0f}{100*sum(1 for r in rs if r[3] >= 1000)/len(rs):>7.1f}%")
    byrace = collections.defaultdict(list)
    for r in rows: byrace[r[5]].append(r[0])
    print("\nrace medians:", ", ".join(f"{RACES[k] if 0 <= k < 5 else k} {statistics.median(v):.0f} (n={len(v)})" for k, v in sorted(byrace.items())))
    depths = collections.Counter(min(r[7], 20) for r in rows)
    print("max depth:", ", ".join(f"{d}:{100*c/len(rows):.1f}%" for d, c in sorted(depths.items())))
    turns = sorted(r[8] for r in rows)
    print(f"turns: median {turns[len(turns)//2]} p90 {turns[len(turns)*9//10]}")
    names = mon_names()
    killers = collections.Counter(r[9] for r in rows if r[1] == 0 and r[9] > 0)
    tot = sum(killers.values())
    if tot:
        top = ", ".join(f"{(names[k-1] if names and 0 < k <= len(names) else k)} {100*v/tot:.1f}%" for k, v in killers.most_common(12))
        print(f"killers (of {tot} monster deaths): {top}")
        print(f"killer level: median {statistics.median(r[10] for r in rows if r[1] == 0 and r[9] > 0):.0f}")

if __name__ == "__main__":
    main()
