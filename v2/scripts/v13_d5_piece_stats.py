#!/usr/bin/env python3
"""Vol-13 D5 — piece-set statistics on rare-color distribution.

For the canonical E2 piece set (196 interior + 56 edge + 4 corner =
256 pieces), count for each piece:
  - how many rare-color edges (in {1..5}) it has
  - are 2-rare-edge pieces always on opposite-axis edges (vol-7 rule)?

This gives the population bound on the rare-stripe propagator:
- pieces with 0 rare edges: "blockers" — cannot extend a stripe.
- pieces with 1 rare edge: stripe terminators or seeds.
- pieces with 2 rare edges (on opposite axis): stripe propagators.
- pieces with 2 rare edges on adjacent axis: rule violators (expect 0 or
  only corners per vol-7).
- pieces with 3+ rare edges: extreme — would force 2-stripe intersection.

Output:
  - histogram of rare-edge counts
  - per-piece category counts
  - if many 1-rare-edge pieces exist, stripe rule is *probabilistic* —
    most stripes terminate at the first 1-rare cell.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from v11_load_e2 import load


BORDER = 0
RARE = {1, 2, 3, 4, 5}


def main():
    e2 = load()
    pieces = e2['pieces']  # int8 [256, 4] (N, E, S, W)
    border_counts = (pieces == BORDER).sum(axis=1)

    # Bucket: corner (2 border), edge (1 border), interior (0 border)
    interior_idx = (border_counts == 0)
    edge_idx = (border_counts == 1)
    corner_idx = (border_counts == 2)

    print(f"Piece set: {(corner_idx).sum()} corners, {(edge_idx).sum()} edges, {(interior_idx).sum()} interior\n")

    # For each piece, count rare edges (excluding BORDER edges)
    # rare_edge_count[i] = number of rare colors among the 4 edges
    rare_per_piece = []
    for pid in range(256):
        cnt = sum(1 for c in pieces[pid] if int(c) in RARE)
        rare_per_piece.append(cnt)

    for name, mask in [('CORNER', corner_idx), ('EDGE', edge_idx), ('INTERIOR', interior_idx)]:
        ids = [i for i in range(256) if mask[i]]
        rare_dist = Counter(rare_per_piece[i] for i in ids)
        print(f"{name} pieces ({len(ids)} total):")
        for k in sorted(rare_dist.keys()):
            print(f"   {k} rare edges: {rare_dist[k]}")
        print()

    # The key stat for the stripe propagator: among interior pieces, what
    # fraction have ≥2 rare edges (= "stripe propagators")?
    interior_ids = [i for i in range(256) if interior_idx[i]]
    multi_rare = [i for i in interior_ids if rare_per_piece[i] >= 2]
    single_rare = [i for i in interior_ids if rare_per_piece[i] == 1]
    no_rare = [i for i in interior_ids if rare_per_piece[i] == 0]
    print(f"INTERIOR stripe analysis:")
    print(f"   0 rare edges (stripe blockers)  : {len(no_rare)} pieces ({100*len(no_rare)/196:.1f}%)")
    print(f"   1 rare edge  (stripe terminators): {len(single_rare)} pieces ({100*len(single_rare)/196:.1f}%)")
    print(f"   2+ rare edges (stripe propagators): {len(multi_rare)} pieces ({100*len(multi_rare)/196:.1f}%)")
    print()

    # For 2-rare-edge pieces: verify rule (rare edges on OPPOSITE axis,
    # i.e. N+S or E+W, not N+E etc.)
    rule_holds = 0
    rule_breaks = 0
    rule_break_examples = []
    for pid in multi_rare:
        edges = pieces[pid]  # (N=0, E=1, S=2, W=3)
        rare_positions = [i for i in range(4) if int(edges[i]) in RARE]
        if len(rare_positions) == 2:
            # opposite-axis check: {0,2} (N,S) or {1,3} (E,W) are opposite
            ok = set(rare_positions) in ({0, 2}, {1, 3})
            if ok:
                rule_holds += 1
            else:
                rule_breaks += 1
                if len(rule_break_examples) < 3:
                    rule_break_examples.append((pid, tuple(int(c) for c in edges)))
        # >2 rare = different analysis, skip for now

    print(f"2-rare-edge interior pieces: rule holds {rule_holds}, breaks {rule_breaks}")
    if rule_breaks > 0:
        print(f"   break examples (pid, edges):")
        for pid, e in rule_break_examples:
            print(f"     pid={pid}  edges (N,E,S,W) = {e}")
    print()

    # Same for corner pieces (vol-7 noted the 4 corners are the "rule
    # break" because their non-border edges are forced adjacent).
    corner_break_check = []
    for pid in [i for i in range(256) if corner_idx[i]]:
        edges = pieces[pid]
        rare_positions = [i for i in range(4) if int(edges[i]) in RARE]
        if len(rare_positions) == 2:
            ok = set(rare_positions) in ({0, 2}, {1, 3})
            corner_break_check.append((pid, tuple(int(c) for c in edges), len(rare_positions), ok))
    print(f"CORNER pieces: 2-rare-edge ones (vol-7 expected to break the rule):")
    for pid, e, n, ok in corner_break_check:
        print(f"   pid={pid}  edges={e}  rare_count={n}  opposite={ok}")
    print()

    # Bound on the propagator strength:
    # Stripe propagation at cell c with rare on N edge:
    #   - probability piece has another rare on S (rather than not):
    #     P(2nd rare on S | 1 rare on N) for pieces matching constraint.
    # Simplest population estimate: among interior pieces with ≥1 rare edge,
    # how many have a rare edge on the OPPOSITE side of any single rare edge?
    # For 2-rare pieces, by the rule, the answer is always 1.
    # For 1-rare pieces, by definition, the answer is 0.
    p_propagate = len(multi_rare) / (len(multi_rare) + len(single_rare))
    print(f"P(piece has 2nd rare on opposite edge | piece has at least 1 rare edge) = {len(multi_rare)} / {len(multi_rare) + len(single_rare)} = {p_propagate:.3f}")
    print(f"=> a rare-color stripe entering an interior cell continues to the next cell with probability ≈ {p_propagate:.3f}")
    print(f"=> 14-cell stripe survival probability ≈ {p_propagate:.3f}^14 = {p_propagate**14:.4f}")


if __name__ == '__main__':
    main()
