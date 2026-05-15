#!/usr/bin/env python3
"""Vol-65 — Rotation-orbit analysis of canonical E2 piece set.

For each piece, compute its rotation orbit under ℤ/4 (set of 4
cyclic permutations of (N,E,S,W) edges). Group pieces by orbit-rep.

Findings of interest:
1. How many distinct rotation-orbits are there in canonical E2?
   (If all 256 distinct → no rotation symmetry; expected.)
2. Are there any "rotation-symmetric" pieces (orbit smaller than 4)?
   Such pieces would be invariant under 90° rotation.
3. Are there any near-twins (two pieces sharing 3 of 4 edges with
   some rotation alignment)? These are partially-exchangeable.
"""

import collections
import csv
import json
from pathlib import Path

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"


def load_pieces(csv_path):
    BORDER_RAW = 65535
    pieces = []
    with open(csv_path) as f:
        size = int(f.readline().strip())
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            def col(s):
                v = int(s.strip(), 2)
                return 0 if v == BORDER_RAW else v
            top = col(parts[0])
            right = col(parts[1])
            bottom = col(parts[2])
            left = col(parts[3])
            pieces.append((idx, (top, right, bottom, left)))
    return pieces


def rotate(edges, k):
    """Cyclic rotation of (N, E, S, W) by k * 90°.

    Convention: rotating piece by k=1 (90° clockwise) makes the
    canonical-N edge face East in world coordinates. So in the new
    canonical labeling (what's at N,E,S,W after rotation):
      new_N = old_W
      new_E = old_N
      new_S = old_E
      new_W = old_S

    Equivalent: rotate the tuple right by k positions.
    """
    n, e, s, w = edges
    if k == 0: return (n, e, s, w)
    if k == 1: return (w, n, e, s)
    if k == 2: return (s, w, n, e)
    if k == 3: return (e, s, w, n)
    raise ValueError(k)


def canonical_rep(edges):
    """Among the 4 rotations, return the lexicographically smallest."""
    return min(rotate(edges, k) for k in range(4))


def edge_multiset(edges):
    """Sorted edges (unordered)."""
    return tuple(sorted(edges))


def main():
    pieces = load_pieces(PUZZLE_CSV)
    n = len(pieces)
    print(f"Pieces: {n}")

    # 1. Distinct rotation orbits
    orbit_count = collections.Counter()
    orbit_members = collections.defaultdict(list)
    for p, e in pieces:
        rep = canonical_rep(e)
        orbit_count[rep] += 1
        orbit_members[rep].append(p)
    print(f"Distinct rotation-orbit representatives: {len(orbit_count)}")
    # Multiplicities
    mult_dist = collections.Counter(orbit_count.values())
    print(f"Orbit size distribution (multiplicity: # orbits):")
    for sz, n_orbits in sorted(mult_dist.items()):
        print(f"  size {sz}: {n_orbits} orbits → covers {sz * n_orbits} pieces")
    # Total: should sum to 256
    assert sum(sz * n_orbits for sz, n_orbits in mult_dist.items()) == n

    # 2. Rotation-symmetric pieces (orbit size < 4)
    sym_pieces = []
    for rep, members in orbit_members.items():
        # An orbit-rep maps to ONE piece-id (since distinct pieces all have
        # distinct edge-tuples). If members has multiple, they are duplicates.
        # Actually 'orbit_count' counts pieces with same canonical_rep.
        # A single piece's orbit has size = 4 / stabilizer; if rep is invariant
        # under some k>0, the orbit is smaller.
        e = pieces[members[0]][1]
        if len(set(rotate(e, k) for k in range(4))) < 4:
            sym_pieces.append(members[0])
    print(f"Rotation-symmetric pieces (own orbit has <4 distinct rotations): {len(sym_pieces)}")
    if sym_pieces:
        for p in sym_pieces[:5]:
            print(f"  piece {p}: edges={pieces[p][1]}")

    # 3. Edge-multiset analysis
    ms_count = collections.Counter()
    ms_members = collections.defaultdict(list)
    for p, e in pieces:
        ms = edge_multiset(e)
        ms_count[ms] += 1
        ms_members[ms].append(p)
    print(f"\nDistinct edge-multisets: {len(ms_count)}")
    ms_mult_dist = collections.Counter(ms_count.values())
    print(f"Multiset multiplicity distribution:")
    for sz, n in sorted(ms_mult_dist.items()):
        print(f"  multiplicity {sz}: {n} multisets ({sz*n} pieces)")

    # 4. Near-twins: pieces sharing 3 of 4 edges in canonical rotation
    near_twins = collections.defaultdict(list)
    for p1, e1 in pieces:
        canon1 = canonical_rep(e1)
        # 3-of-4 key: try each of 4 sides as "missing"
        for omit in range(4):
            key = tuple(c for i, c in enumerate(canon1) if i != omit)
            near_twins[(omit, key)].append(p1)
    # Count groups with >= 2 pieces
    twin_groups = sum(1 for k, v in near_twins.items() if len(v) >= 2)
    twin_pairs = sum((len(v) * (len(v) - 1)) // 2
                     for k, v in near_twins.items() if len(v) >= 2)
    print(f"\n3-of-4-canonical-edge twin groups: {twin_groups}")
    print(f"3-of-4 near-twin piece-pairs: {twin_pairs}")
    # Show a few examples
    twin_examples = sorted(
        ((k, v) for k, v in near_twins.items() if len(v) >= 2),
        key=lambda x: -len(x[1]),
    )[:5]
    print(f"Top 5 near-twin groups (by group size):")
    for (omit, key), members in twin_examples:
        print(f"  omit_side={omit} other_edges={key} → pieces {members[:8]}")

    # Save summary
    out_path = "output/vol-65/piece_orbits.json"
    Path("output/vol-65").mkdir(parents=True, exist_ok=True)
    out = {
        "n_pieces": n,
        "n_orbits": len(orbit_count),
        "orbit_size_distribution": dict(mult_dist),
        "rotation_symmetric_pieces": sym_pieces,
        "n_multisets": len(ms_count),
        "multiset_multiplicity_distribution": dict(ms_mult_dist),
        "n_near_twin_groups": twin_groups,
        "n_near_twin_pairs": twin_pairs,
    }
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
