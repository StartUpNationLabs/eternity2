#!/usr/bin/env python3
# R4 — piece-side mutual information on canonical Eternity II.
#
# For each piece, read its (N, E, S, W) colors. Compute:
#   - marginal P(side_X = c)
#   - joint P(side_X = a, side_Y = b)
#   - mutual information I(side_X; side_Y) in bits
#   - conditional entropy H(side_Y | side_X)
#
# Side-pair MI > 1 bit indicates a "linguistic" constraint that
# placing a piece with color a on side X strongly predicts color b on
# side Y. That's a candidate CP propagator the engine does not have.
#
# Also computes rotation-invariant MI (averaged over the 4 cyclic
# rotations of (N,E,S,W)) to separate true piece-structural MI from
# rotation-frame artifacts.

import csv
import math
from collections import Counter
from itertools import combinations
from pathlib import Path

PUZZLE_CSV = Path(__file__).resolve().parents[2] / "data/puzzles/size_16_official_eternity.csv"

BORDER = 255  # sentinel matching crates/benchmark/src/loader.rs

def decode_side(bits16: str) -> int:
    # The CSV stores a color index as a 16-bit binary integer.
    # All-ones (65535) is the BORDER sentinel.
    v = int(bits16, 2)
    if v == 65535:
        return BORDER
    return v

def load_pieces(path: Path):
    sides = []  # list of (N,E,S,W) color ints
    with path.open() as f:
        for row in csv.reader(f):
            if len(row) < 4:
                continue  # size header line
            n = decode_side(row[0])
            e = decode_side(row[1])
            s = decode_side(row[2])
            w = decode_side(row[3])
            sides.append((n, e, s, w))
    return sides

def entropy(counter, total):
    h = 0.0
    for c in counter.values():
        if c > 0:
            p = c / total
            h -= p * math.log2(p)
    return h

def joint_mi(pairs):
    total = len(pairs)
    px = Counter(x for x, _ in pairs)
    py = Counter(y for _, y in pairs)
    pxy = Counter(pairs)
    hx = entropy(px, total)
    hy = entropy(py, total)
    hxy = entropy(pxy, total)
    return hx + hy - hxy, hx, hy, hxy

def is_interior(piece) -> bool:
    return all(c != BORDER for c in piece)

def run_block(label, pieces):
    print()
    print("=" * 70)
    print(f"# {label}: {len(pieces)} pieces")
    print("=" * 70)
    if not pieces:
        return
    colors = sorted({c for p in pieces for c in p})
    print(f"# colors observed: {len(colors)}")
    side_names = ["N", "E", "S", "W"]
    print("## Side entropies (bits)")
    for si, name in enumerate(side_names):
        h = Counter(p[si] for p in pieces)
        print(f"  H({name}) = {entropy(h, len(pieces)):.4f}")
    print("## Pairwise MI between sides of same piece (bits)")
    print("  pair  | I       | H_x     | H_y     | I/min(Hx,Hy)")
    for (i, j) in combinations(range(4), 2):
        pairs = [(p[i], p[j]) for p in pieces]
        mi, hx, hy, _ = joint_mi(pairs)
        denom = min(hx, hy) if min(hx, hy) > 0 else 1.0
        print(f"  {side_names[i]}-{side_names[j]}   | {mi:.4f}  | {hx:.4f}  | {hy:.4f}  | {mi/denom:.3f}")
    print("## Rotation-invariant MI (cyclic-rotation averaged)")
    def cyc(p, r):
        return p[(0 + r) % 4], p[(1 + r) % 4], p[(2 + r) % 4], p[(3 + r) % 4]
    adj_pairs = []
    opp_pairs = []
    for p in pieces:
        for r in range(4):
            pr = cyc(p, r)
            adj_pairs.append((pr[0], pr[1]))
            opp_pairs.append((pr[0], pr[2]))
    mi_adj, hx_a, _, _ = joint_mi(adj_pairs)
    mi_opp, hx_o, _, _ = joint_mi(opp_pairs)
    print(f"  adjacent | I={mi_adj:.4f} (H_x={hx_a:.4f})  ⇒ reduction {100*mi_adj/hx_a if hx_a>0 else 0:.1f}%")
    print(f"  opposite | I={mi_opp:.4f} (H_x={hx_o:.4f})  ⇒ reduction {100*mi_opp/hx_o if hx_o>0 else 0:.1f}%")

def main():
    pieces = load_pieces(PUZZLE_CSV)
    print(f"# loaded {len(pieces)} pieces from {PUZZLE_CSV.name}")
    interior = [p for p in pieces if is_interior(p)]
    corner = [p for p in pieces if sum(1 for c in p if c == BORDER) == 2]
    edge = [p for p in pieces if sum(1 for c in p if c == BORDER) == 1]
    print(f"#   {len(corner)} corners, {len(edge)} edges, {len(interior)} interior")
    colors = sorted({c for p in pieces for c in p})
    print(f"# colors observed: {len(colors)} = {colors}")

    side_names = ["N", "E", "S", "W"]
    print()
    print("## Per-side color histogram (count of pieces with each color on each side)")
    for si, name in enumerate(side_names):
        h = Counter(p[si] for p in pieces)
        line = f"  {name}: " + " ".join(f"{c}:{h[c]}" for c in sorted(h))
        print(line)

    print()
    print("## Side entropies (bits)")
    for si, name in enumerate(side_names):
        h = Counter(p[si] for p in pieces)
        print(f"  H({name}) = {entropy(h, len(pieces)):.4f}")

    print()
    print("## Pairwise mutual information between two sides of the SAME piece (bits)")
    print("  (fixed-rotation: pieces are NOT cyclically averaged)")
    print("  pair        | I        | H_x      | H_y      | H_xy     | I/min(Hx,Hy)")
    for (i, j) in combinations(range(4), 2):
        pairs = [(p[i], p[j]) for p in pieces]
        mi, hx, hy, hxy = joint_mi(pairs)
        denom = min(hx, hy) if min(hx, hy) > 0 else 1.0
        print(f"  {side_names[i]}-{side_names[j]}        | {mi:.4f}   | {hx:.4f}   | {hy:.4f}   | {hxy:.4f}   | {mi/denom:.3f}")

    print()
    print("## Rotation-invariant MI (average over 4 cyclic rotations of (N,E,S,W))")
    print("  This estimates a piece-intrinsic MI invariant to placement rotation.")
    print("  pair-type     | I_avg (bits)")
    # adjacent = sides at distance 1 around the cycle; opposite = distance 2
    def cyc(p, r):
        return p[(0 + r) % 4], p[(1 + r) % 4], p[(2 + r) % 4], p[(3 + r) % 4]
    adj_pairs = []
    opp_pairs = []
    for p in pieces:
        for r in range(4):
            pr = cyc(p, r)
            # adjacent pairs in cycled (N',E',S',W'): (N',E'), (E',S'), (S',W'), (W',N')
            adj_pairs.append((pr[0], pr[1]))
            # opposite pairs: (N',S'), (E',W')
            opp_pairs.append((pr[0], pr[2]))
    mi_adj, hx_a, hy_a, _ = joint_mi(adj_pairs)
    mi_opp, hx_o, hy_o, _ = joint_mi(opp_pairs)
    print(f"  adjacent      | {mi_adj:.4f}   (H_x={hx_a:.4f} H_y={hy_a:.4f})")
    print(f"  opposite      | {mi_opp:.4f}   (H_x={hx_o:.4f} H_y={hy_o:.4f})")

    print()
    print("## Conditional distribution P(side_E = b | side_N = a)")
    print("  (only entries with conditional prob > 0.10 shown)")
    n_e_pairs = [(p[0], p[1]) for p in pieces]
    joint = Counter(n_e_pairs)
    marg_n = Counter(p[0] for p in pieces)
    for n_color in sorted(marg_n):
        total = marg_n[n_color]
        if total == 0:
            continue
        e_cond = []
        for e_color in colors:
            c = joint.get((n_color, e_color), 0)
            p = c / total
            if p > 0.10:
                e_cond.append((e_color, p, c))
        if e_cond:
            line = f"  N={n_color:>2} (n={total:>3}): " + " ".join(
                f"E={e}:{c}({p:.0%})" for e, p, c in sorted(e_cond, key=lambda x: -x[1])
            )
            print(line)

    print()
    print("## Strongest *piece-internal* predictive pairs (conditional entropy < median)")
    # Find (X, Y) pairs where H(Y|X) is much smaller than H(Y).
    # Look across all 12 ordered (X, Y) directional pairs.
    rows = []
    for i in range(4):
        for j in range(4):
            if i == j:
                continue
            pairs = [(p[i], p[j]) for p in pieces]
            mi, hx, hy, hxy = joint_mi(pairs)
            h_y_given_x = hxy - hx
            reduction = (hy - h_y_given_x) / hy if hy > 0 else 0.0
            rows.append((side_names[i], side_names[j], hy, h_y_given_x, reduction, mi))
    rows.sort(key=lambda r: -r[4])
    print("  X -> Y | H(Y)    | H(Y|X)  | reduction | I(X;Y)")
    for r in rows:
        print(f"  {r[0]} -> {r[1]} | {r[2]:.4f}  | {r[3]:.4f}  | {r[4]*100:>5.1f}%    | {r[5]:.4f}")

def run_blocks_for_subsets(all_pieces, interior, edge_pieces):
    run_block("ALL 256 PIECES", all_pieces)
    run_block("INTERIOR ONLY (no border)", interior)
    run_block("EDGE PIECES (exactly 1 border side)", edge_pieces)

if __name__ == "__main__":
    main()
    pieces = load_pieces(PUZZLE_CSV)
    interior = [p for p in pieces if is_interior(p)]
    edge_pieces = [p for p in pieces if sum(1 for c in p if c == BORDER) == 1]
    run_blocks_for_subsets(pieces, interior, edge_pieces)
