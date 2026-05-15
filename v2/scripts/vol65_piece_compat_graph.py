#!/usr/bin/env python3
"""Vol-65 — Piece-compatibility graph (piece-level, not piece-side).

Nodes: 256 pieces.
Edges: (p1, p2) iff some rotation of p1 has a side color = some rotation
       of p2's facing side. This is the "can-be-neighbors" relation.

Edge weight: number of valid (k1, k2, side1, side2) tuples that match.
Higher weight = more flexibility in adjacency.

This graph IS connected (every piece can neighbor many others) — let's
see if it has spectral structure.
"""

import collections
import csv
import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"


def load_pieces(p):
    BORDER_RAW = 65535
    out = []
    with open(p) as f:
        size = int(f.readline().strip())
        for idx, line in enumerate(f):
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            def col(s):
                v = int(s.strip(), 2)
                return 0 if v == BORDER_RAW else v
            out.append((col(parts[0]), col(parts[1]), col(parts[2]), col(parts[3])))
    return out


def main():
    pieces = load_pieces(PUZZLE_CSV)
    n = len(pieces)
    print(f"Pieces: {n}")

    # Build piece-compatibility multigraph
    # Two pieces are "weight-w-compatible" where w is the number of (rotation,
    # side, rotation', side') tuples that satisfy color match AND opposing
    # world-direction (NS or EW).
    # For piece p1 at rotation k1, its world-side d carries color
    # pieces[p1][(d - k1) % 4]. (After k-rotation, world-d sees canonical-(d-k).)
    # Two cells (p1, k1) and (p2, k2) are adjacent in world iff the facing
    # sides match: (p1, k1)'s world-E (color pieces[p1][(1-k1)%4]) = (p2, k2)'s
    # world-W (color pieces[p2][(3-k2)%4])  [horizontal case]
    # or vertical: (p1, k1)'s world-S = (p2, k2)'s world-N.
    # We count BOTH horizontal and vertical compatibility.

    weights = np.zeros((n, n))
    for p1 in range(n):
        for p2 in range(p1 + 1, n):
            count = 0
            for k1 in range(4):
                for k2 in range(4):
                    # horizontal: p1.E matches p2.W
                    c1_E = pieces[p1][(1 - k1) % 4]
                    c2_W = pieces[p2][(3 - k2) % 4]
                    if c1_E != 0 and c2_W != 0 and c1_E == c2_W: count += 1
                    # horizontal swap: p2.E matches p1.W
                    c1_W = pieces[p1][(3 - k1) % 4]
                    c2_E = pieces[p2][(1 - k2) % 4]
                    if c2_E != 0 and c1_W != 0 and c2_E == c1_W: count += 1
                    # vertical: p1.S matches p2.N
                    c1_S = pieces[p1][(2 - k1) % 4]
                    c2_N = pieces[p2][(0 - k2) % 4]
                    if c1_S != 0 and c2_N != 0 and c1_S == c2_N: count += 1
                    # vertical swap
                    c1_N = pieces[p1][(0 - k1) % 4]
                    c2_S = pieces[p2][(2 - k2) % 4]
                    if c2_S != 0 and c1_N != 0 and c2_S == c1_N: count += 1
            weights[p1, p2] = count
            weights[p2, p1] = count

    print(f"Compatibility weight matrix: shape {weights.shape}")
    print(f"  min weight: {weights[weights > 0].min() if (weights > 0).any() else 0}")
    print(f"  max weight: {weights.max()}")
    print(f"  median (off-diag): {np.median(weights[weights > 0]):.1f}")
    print(f"  zero-weight pairs (no compatible adjacency): "
          f"{int(np.sum(weights == 0)) - n} (excluding diagonal)")

    # Degree
    deg = weights.sum(axis=1)
    print(f"  Degree: min={deg.min():.0f}, median={np.median(deg):.0f}, "
          f"max={deg.max():.0f}")

    # Convert to sparse
    W = sp.csr_matrix(weights)

    # Top eigenvalues
    print("\nTop-10 eigenvalues:")
    eigvals, eigvecs = spla.eigsh(W, k=10, which='LM')
    order = np.argsort(-np.abs(eigvals))
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]
    for i, lam in enumerate(eigvals):
        print(f"  λ_{i+1} = {lam:.4f}")
    print(f"\nλ_1/λ_2 = {eigvals[0]/eigvals[1]:.4f}")
    print(f"(λ_1-λ_2)/λ_1 = {(eigvals[0]-eigvals[1])/eigvals[0]:.4f}")

    # Normalized Laplacian (top of degree)
    D_inv_sqrt = sp.diags(1.0 / np.sqrt(deg + 1e-10))
    L_norm = sp.eye(n) - D_inv_sqrt @ W @ D_inv_sqrt
    print("\nBottom-10 eigenvalues of normalized Laplacian:")
    eigvals_L, eigvecs_L = spla.eigsh(L_norm, k=10, which='SM')
    eigvals_L.sort()
    for i, lam in enumerate(eigvals_L):
        print(f"  μ_{i+1} = {lam:.6f}")

    # Cluster pieces by Fiedler vector
    fiedler = eigvecs_L[:, 1]  # 2nd-smallest
    pos = sum(1 for v in fiedler if v > 0)
    neg = sum(1 for v in fiedler if v <= 0)
    print(f"\nFiedler bisection: {pos} pieces with positive value, {neg} negative")

    # Cluster by piece-kind: do corner/edge/interior pieces fall into same cluster?
    kinds = []
    for p in pieces:
        nb = sum(1 for c in p if c == 0)
        kinds.append("corner" if nb == 2 else "edge" if nb == 1 else "interior")
    cluster_kind = collections.Counter()
    for i, v in enumerate(fiedler):
        side = 1 if v > 0 else 0
        cluster_kind[(side, kinds[i])] += 1
    print(f"\nFiedler-cluster by piece-kind:")
    for (side, kind), n_ in sorted(cluster_kind.items()):
        print(f"  side {side}, {kind}: {n_}")

    # Save
    Path("output/vol-65").mkdir(parents=True, exist_ok=True)
    np.savez("output/vol-65/piece_compat_spectrum.npz",
             weights=weights, eigvals=eigvals, eigvals_L=eigvals_L,
             fiedler=fiedler)
    print(f"\nSaved to output/vol-65/piece_compat_spectrum.npz")


if __name__ == "__main__":
    main()
