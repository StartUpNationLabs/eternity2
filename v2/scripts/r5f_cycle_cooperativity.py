#!/usr/bin/env python3
# R5f — measure pairwise cooperativity of σ cycles.
#
# Each individual cycle has negative score delta when applied. Together,
# all 10 give net +9. So the cycles cooperate. Question: what's the
# pairwise structure of cooperation?
#
# For each pair (i, j) compute Δ(cycle_i ∪ cycle_j) − [Δ(cycle_i) + Δ(cycle_j)].
# Positive => cooperative; Negative => antagonistic.

import sys
from pathlib import Path
sys.path.insert(0, "scripts")
import importlib.util
spec = importlib.util.spec_from_file_location("r5e", "scripts/r5e_permutation_cycles.py")
r5e = importlib.util.module_from_spec(spec); spec.loader.exec_module(r5e)

# reuse R5e's apply_cycle_swap and score
size, pieces = r5e.size, r5e.pieces
score = r5e.score
load = r5e.load
apply_cycle_swap = r5e.apply_cycle_swap

def main():
    if len(sys.argv) < 3:
        sys.exit("usage: r5f_cycle_cooperativity.py <current.json> <oracle.json>")
    cur = load(sys.argv[1])
    oracle = load(sys.argv[2])
    s_cur = score(cur); s_or = score(oracle)
    print(f"current: {s_cur}/480   oracle: {s_or}/480")

    # Build σ and extract cycles (lifted from R5e)
    cur_pos = {e[0]: pos for pos, e in enumerate(cur) if e is not None}
    ora_pos = {e[0]: pos for pos, e in enumerate(oracle) if e is not None}
    sigma = {p: ora_pos[cur[p][0]] for p in range(size * size) if cur[p] is not None}
    seen = set(); cycles = []
    for p in sorted(sigma.keys()):
        if p in seen: continue
        cyc = []; q = p
        while q not in seen:
            seen.add(q); cyc.append(q); q = sigma[q]
        if len(cyc) >= 2: cycles.append(cyc)
    cycles.sort(key=len, reverse=True)
    n = len(cycles)
    print(f"# {n} cycles of length >=2")

    # Solo deltas
    solo = []
    for c in cycles:
        new = apply_cycle_swap(cur, oracle, c)
        s = score(new)
        solo.append(s - s_cur)
    print()
    print("## Solo deltas")
    for i, (c, d) in enumerate(zip(cycles, solo)):
        print(f"  cycle {i:>2} (len {len(c):>3}): Δ = {d:+}")
    print(f"  sum of solo Δ: {sum(solo):+}")
    print(f"  total joint Δ: {s_or - s_cur:+} (oracle minus current)")
    print(f"  cooperation gap: {(s_or - s_cur) - sum(solo):+}  (positive = cycles help each other)")

    # Pairwise: apply (i, j) jointly
    print()
    print("## Pairwise interaction matrix (Δ(i+j) − Δ(i) − Δ(j))")
    print("   " + "".join(f"{j:>5}" for j in range(n)))
    interaction_matrix = [[0]*n for _ in range(n)]
    for i in range(n):
        row = [f"{i:>2}:"]
        for j in range(n):
            if j <= i:
                row.append("    .")
                continue
            new = apply_cycle_swap(cur, oracle, cycles[i])
            new = apply_cycle_swap(new, oracle, cycles[j])
            d_joint = score(new) - s_cur
            interaction = d_joint - solo[i] - solo[j]
            interaction_matrix[i][j] = interaction
            row.append(f"{interaction:>+5}")
        print(" ".join(row))

    # Sum of pairwise interactions
    total_pairwise = sum(interaction_matrix[i][j] for i in range(n) for j in range(i+1, n))
    print()
    print(f"sum of pairwise interactions: {total_pairwise:+}")
    print(f"cooperation explained by pairs: {total_pairwise} of {(s_or - s_cur) - sum(solo)} total gap")
    print(f"residual (3-way+ effects): {((s_or - s_cur) - sum(solo)) - total_pairwise:+}")

    # Most cooperative pair
    print()
    pairs_by_coop = [(interaction_matrix[i][j], i, j) for i in range(n) for j in range(i+1, n)]
    pairs_by_coop.sort(reverse=True)
    print("## Top cooperative pairs:")
    for interaction, i, j in pairs_by_coop[:5]:
        d_solo_pair = solo[i] + solo[j]
        d_joint = d_solo_pair + interaction
        print(f"  cycles {i}+{j}: solo {solo[i]:+} {solo[j]:+} = {d_solo_pair:+}, joint Δ {d_joint:+}, cooperation {interaction:+}")
    print()
    print("## Most antagonistic pairs:")
    for interaction, i, j in pairs_by_coop[-5:]:
        d_solo_pair = solo[i] + solo[j]
        d_joint = d_solo_pair + interaction
        print(f"  cycles {i}+{j}: solo {solo[i]:+} {solo[j]:+} = {d_solo_pair:+}, joint Δ {d_joint:+}, cooperation {interaction:+}")

if __name__ == "__main__":
    main()
