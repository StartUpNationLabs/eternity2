#!/usr/bin/env python3
"""Vol-68 — Double near-twin swap on McGavin 469.

Apply TWO near-twin swaps simultaneously. Combinations:
114 pairs × 113/2 + 114 (same pair twice not meaningful, skip) ≈ 6441.

If two non-interacting swaps each preserve score, combining them
preserves it too. If they INTERACT, the score might go up or down.

Goal: find any combination giving ≥ 470. That's a record break.
"""

import sys
sys.path.insert(0, 'scripts')
from vol68_near_twin_swap_sweep import (
    load_pieces, find_near_twin_pairs, load_placement, score_board,
    best_rotation
)
import collections
import time


def main():
    pieces = load_pieces()
    near_twin_pairs = find_near_twin_pairs(pieces)
    mcg = load_placement("output/vol-65/mcgavin_469.json")
    base = score_board(mcg, pieces)
    print(f"McGavin baseline: {base}")
    print(f"Near-twin pairs: {len(near_twin_pairs)}")

    pid_to_pos = {pid: pos for pos, (pid, _) in mcg.items()}

    # Filter pairs that both pieces actually in board (sanity)
    valid_pairs = []
    for (p1, p2) in near_twin_pairs:
        if p1 in pid_to_pos and p2 in pid_to_pos:
            valid_pairs.append((p1, p2))
    print(f"Valid pairs (both pieces placed): {len(valid_pairs)}")

    n_combos = len(valid_pairs) * (len(valid_pairs) - 1) // 2
    print(f"Pair-of-pair combinations: {n_combos}")

    # Apply pair (a, b) + pair (c, d) simultaneously
    t0 = time.time()
    score_dist = collections.Counter()
    record_breaks = []
    for i in range(len(valid_pairs)):
        for j in range(i+1, len(valid_pairs)):
            pa, pb = valid_pairs[i]
            pc, pd = valid_pairs[j]
            # Need all 4 pieces distinct
            if len({pa, pb, pc, pd}) != 4: continue
            posa = pid_to_pos[pa]; posb = pid_to_pos[pb]
            posc = pid_to_pos[pc]; posd = pid_to_pos[pd]
            # Need all 4 positions distinct
            if len({posa, posb, posc, posd}) != 4: continue
            # Apply both swaps
            new = dict(mcg)
            for pos in [posa, posb, posc, posd]:
                del new[pos]
            # Place: swap (pa, pb) at (posa, posb); swap (pc, pd) at (posc, posd)
            new[posa] = (pb, best_rotation(pb, posa, new, pieces))
            new[posb] = (pa, best_rotation(pa, posb, new, pieces))
            new[posc] = (pd, best_rotation(pd, posc, new, pieces))
            new[posd] = (pc, best_rotation(pc, posd, new, pieces))
            sc = score_board(new, pieces)
            score_dist[sc] += 1
            if sc >= 470:
                record_breaks.append(((pa, pb), (pc, pd), sc))
                print(f"  *** ({pa}, {pb}) + ({pc}, {pd}) → {sc} ★ RECORD")

    print(f"\nDouble-swap scan: {sum(score_dist.values())} combos in {time.time()-t0:.1f}s")
    print(f"Score distribution (top):")
    for sc in sorted(score_dist.keys(), reverse=True)[:10]:
        print(f"  {sc}: {score_dist[sc]}")

    if record_breaks:
        print(f"\n!!! {len(record_breaks)} RECORD BREAKS FOUND !!!")
    else:
        print(f"\nNo record breaks ≥ 470 from double near-twin swaps.")


if __name__ == "__main__":
    main()
