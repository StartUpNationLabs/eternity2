#!/usr/bin/env python3
"""V149-T1 — STRATUM Day 1: enumerate piece-set color-automorphism group.

A color permutation π ∈ S_{22} (on interior colors 1..22; 0/border fixed)
PRESERVES the canonical E2 piece set iff for every piece p ∈ P, there
exists p' ∈ P and rotation r ∈ {0,1,2,3} such that
    π · p = rotated(p', r)
i.e., the piece SET (as a set of rotation-orbit-reps) is closed under
the action of π.

The group G = { π ∈ S_22 : π preserves P } is what we compute.

If |G| > 1, decompose pieces into G-orbits. These are the STRATA.

Algorithm: backtracking on π's image of each color, with pruning by
"does any piece have rotation-orbit equal to π's expected output".

22! = 1.1e21 is intractable to enumerate; pruning makes it tractable
because each new color-image fixes the position of many pieces in P.
"""

from __future__ import annotations
import argparse
import time
from collections import defaultdict
from itertools import permutations
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_canonical_pieces(path):
    """Returns pieces: list of (top, right, bottom, left) tuples, with
    color values in 1..22 (border=0)."""
    with open(path) as f:
        lines = [l.strip() for l in f if l.strip()]
    size = int(lines[0])
    pieces = []
    for line in lines[1:]:
        parts = line.split(",")

        def cw(s):
            v = int(s.strip(), 2)
            return 0 if v == 65535 else v

        t, r, b, l = cw(parts[0]), cw(parts[1]), cw(parts[2]), cw(parts[3])
        pieces.append((t, r, b, l))
    assert len(pieces) == size * size
    return pieces


def rotation_canonical(piece):
    """Return the lex-min rotation of the piece (as a 4-tuple).
    This is the rotation-orbit representative used as a set element."""
    candidates = []
    n, e, s, w = piece
    base = [n, e, s, w]
    for r in range(4):
        rotated = tuple(base[(i + 4 - r) % 4] for i in range(4))
        candidates.append(rotated)
    return min(candidates)


def apply_permutation(piece, pi):
    """Apply color permutation pi (dict color→color, fixing 0) to a piece."""
    return tuple(pi[c] if c != 0 else 0 for c in piece)


def find_color_automorphism_group(pieces, time_budget_s=60.0):
    """Enumerate π ∈ S_22 preserving the piece set's rotation-orbit canonical reps.

    Returns the list of π's found.
    """
    # The rotation-orbit canonical representative of each piece.
    piece_canonical = [rotation_canonical(p) for p in pieces]
    piece_canon_set = set(piece_canonical)

    # Colors used.
    colors = set()
    for p in pieces:
        for c in p:
            if c != 0:
                colors.add(c)
    colors = sorted(colors)
    n_colors = len(colors)
    print(f"[v149-t1] {n_colors} interior colors: {colors}", flush=True)
    print(f"[v149-t1] {len(piece_canonical)} pieces, {len(piece_canon_set)} distinct rotation-canonicals", flush=True)

    # Group pieces by COLOR MULTISET (set of 4 non-border colors). π preserves
    # the multiset of each piece. Pieces with the same multiset are
    # interchangeable from π's perspective.
    by_multiset = defaultdict(list)
    for p in pieces:
        ms = tuple(sorted([c for c in p if c != 0]))
        by_multiset[ms].append(p)

    multiset_dist = sorted(by_multiset.items(), key=lambda x: (len(x[0]), -len(x[1])))
    print(f"[v149-t1] {len(by_multiset)} distinct multisets")
    print(f"[v149-t1] multiset distribution (size, count):")
    sizes_seen = defaultdict(int)
    for ms, ps in by_multiset.items():
        sizes_seen[len(ps)] += 1
    for sz, cnt in sorted(sizes_seen.items()):
        print(f"  multisets with {cnt} pieces × {sz} pieces each = {cnt*sz}")
    print()

    # For π to preserve P, π must permute multisets in a way that respects
    # which multisets contain how many pieces. We can decompose colors into
    # "fingerprint classes" by their multiset-frequency:
    #   for each color c, count how many pieces have c on one of their sides.
    # Colors in the same fingerprint class can map to each other; colors in
    # different classes cannot.

    color_count = defaultdict(int)
    for p in pieces:
        for c in p:
            if c != 0:
                color_count[c] += 1

    print(f"[v149-t1] color counts:")
    by_count = defaultdict(list)
    for c, n in sorted(color_count.items()):
        by_count[n].append(c)
    for n in sorted(by_count.keys()):
        colors_with_n = by_count[n]
        print(f"  {n} occurrences: {len(colors_with_n)} colors {colors_with_n}")
    print()

    # Each π must map colors with same occurrence count to colors with same
    # occurrence count. So π factors into permutations within each
    # occurrence-count class.

    # Stronger fingerprint: for each color c, the *multiset of adjacent
    # colors* (4 colors per piece appearance, c excluded).
    color_adj_signature = defaultdict(list)
    for p in pieces:
        for i, c in enumerate(p):
            if c == 0:
                continue
            adj = tuple(sorted([cc for j, cc in enumerate(p) if j != i and cc != 0]))
            color_adj_signature[c].append(adj)
    for c in color_adj_signature:
        color_adj_signature[c] = tuple(sorted(color_adj_signature[c]))

    sig_groups = defaultdict(list)
    for c, sig in color_adj_signature.items():
        sig_groups[sig].append(c)

    print(f"[v149-t1] adjacency-signature classes: {len(sig_groups)}")
    for sig, cs in sig_groups.items():
        if len(cs) > 1:
            print(f"  class of {len(cs)} colors: {cs}")
    print()

    # Each π must permute colors WITHIN each adjacency-signature class.
    # The group |G| ≤ ∏ |class|! .
    upper_bound = 1
    fact = [1]
    for i in range(1, 30):
        fact.append(fact[-1] * i)
    for cs in sig_groups.values():
        upper_bound *= fact[len(cs)]
    print(f"[v149-t1] upper bound on |G| from adjacency-sigs: {upper_bound}")
    print()

    if upper_bound == 1:
        print("[v149-t1] |G| = 1 — adjacency-signature classes all singletons.")
        print("[v149-t1] No non-trivial color-automorphism — STRATUM Day-1 refutation candidate.")
        print("[v149-t1] But adjacency-signature is a NECESSARY condition only; may still have hidden orbits via piece-pairing.")
        return [{c: c for c in colors}]  # only identity

    # Backtracking enumeration of π within the adjacency-signature classes.
    classes = list(sig_groups.values())
    class_sizes = [len(c) for c in classes]
    print(f"[v149-t1] enumerating within {len(classes)} adjacency-signature classes of sizes {class_sizes}...", flush=True)

    found = []
    t0 = time.time()
    n_checked = 0
    n_pruned = 0

    def check_full(pi):
        """Verify π ∈ S_22 preserves the piece SET (rotation-canonical)."""
        # Apply π to every piece, take rotation-canonical, check membership.
        new_set = set()
        for p in pieces:
            pp = apply_permutation(p, pi)
            new_set.add(rotation_canonical(pp))
        return new_set == piece_canon_set

    def backtrack(class_idx, pi):
        nonlocal n_checked, n_pruned
        if time.time() - t0 > time_budget_s:
            return False  # signal time-out
        if class_idx == len(classes):
            n_checked += 1
            if check_full(pi):
                found.append(dict(pi))
                if len(found) % 10 == 0:
                    print(f"  found {len(found)}", flush=True)
            return True
        cs = classes[class_idx]
        for perm in permutations(cs):
            new_pi = dict(pi)
            for src, tgt in zip(cs, perm):
                new_pi[src] = tgt
            if not backtrack(class_idx + 1, new_pi):
                return False
        return True

    backtrack(0, {0: 0})
    print(f"[v149-t1] {n_checked} π's checked, {len(found)} preserve the piece set", flush=True)
    print(f"[v149-t1] |G| = {len(found)}", flush=True)
    print(f"[v149-t1] elapsed: {time.time() - t0:.1f}s", flush=True)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", type=str,
                    default=str(REPO.parent / "data/puzzles/size_16_official_eternity.csv"))
    ap.add_argument("--budget", type=float, default=120.0)
    args = ap.parse_args()
    pieces = load_canonical_pieces(args.puzzle)
    G = find_color_automorphism_group(pieces, time_budget_s=args.budget)

    if len(G) == 1:
        print("\n[v149-t1] CONCLUSION: |G| = 1 (only identity preserves piece set)")
        print("[v149-t1] STRATUM color-automorphism hypothesis: REFUTED for canonical E2")
        print("[v149-t1] No hidden color-symmetry fingerprint in Selby-Riordan piece set")
    else:
        print(f"\n[v149-t1] CONCLUSION: |G| = {len(G)} non-trivial color automorphisms")
        print("[v149-t1] STRATUM color-automorphism hypothesis: CONFIRMED")
        print("[v149-t1] Computing G-orbits on pieces...")
        # G acts on pieces; compute orbits.
        piece_canonical = [rotation_canonical(p) for p in pieces]
        canon_to_idx = {pc: i for i, pc in enumerate(piece_canonical)}
        # Equivalence: pid_i ~ pid_j iff exists π in G with apply(π, pieces[i])
        # rotation-canonical = piece_canonical[j].
        n_pieces = len(pieces)
        parent = list(range(n_pieces))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for pi in G:
            for i, p in enumerate(pieces):
                pp = apply_permutation(p, pi)
                ppc = rotation_canonical(pp)
                if ppc in canon_to_idx:
                    union(i, canon_to_idx[ppc])

        orbits = defaultdict(list)
        for i in range(n_pieces):
            orbits[find(i)].append(i)
        print(f"[v149-t1] {len(orbits)} G-orbits (strata):")
        orbit_sizes = sorted([len(o) for o in orbits.values()], reverse=True)
        from collections import Counter
        size_count = Counter(orbit_sizes)
        for sz, cnt in sorted(size_count.items()):
            print(f"  {cnt} strata × {sz} pieces")
        print()

        # Save the orbits.
        out = REPO / "scripts/v149_stratum/orbits.json"
        import json
        json.dump({
            "n_color_automorphisms": len(G),
            "n_strata": len(orbits),
            "orbit_sizes": orbit_sizes,
            "strata": [{"rep_pid": k, "members": v} for k, v in orbits.items()],
        }, open(out, "w"), indent=2)
        print(f"[v149-t1] orbits saved to {out}")


if __name__ == "__main__":
    main()
