#!/usr/bin/env python3
"""Vol-122 M17 — Quantum walk on PIECE-COMPATIBILITY graph (clean slate).

Different from M17 on matched-edge graph. Here, we look at:
- 256-node piece-compatibility graph G.
- G[i][j] = # of (rot_i, rot_j, side) tuples where piece i and j can be
  ADJACENT with matching colors.
- Run continuous-time quantum walk from hint pieces.
- At t=10, |ψ(t)|² gives 'probability of being at piece P' = AFFINITY
  of P to the hint pieces.

Hypothesis: pieces with HIGH affinity to hints are 'preferred neighbors'
in the clean-slate puzzle and should be placed near hint cells.
"""
import json
import os
import sys

sys.path.insert(0, 'scripts')
try:
    import numpy as np
    from vol122_fft_signature import load_pieces, rot_edges, SIDE
except ImportError as e:
    print("Import error:", e)
    sys.exit(1)


def build_piece_compatibility_graph(pieces):
    """256x256 symmetric matrix. M[i][j] = # of (rot_i, rot_j, side) where
    rotated edge of piece i at some side matches piece j's opposite side."""
    n = len(pieces)
    M = np.zeros((n, n), dtype=int)
    # For each ordered side pair (a, b), check if there's a rotation pair making it match.
    # Sides 0=T, 1=R, 2=B, 3=L. Adjacency pairs: (1,3) horizontal, (2,0) vertical.
    for i in range(n):
        for rot_i in range(4):
            e_i = rot_edges(pieces[i], rot_i)
            for j in range(i + 1, n):
                for rot_j in range(4):
                    e_j = rot_edges(pieces[j], rot_j)
                    # Horizontal: i's right = j's left
                    if e_i[1] == e_j[3] and e_i[1] != 0:
                        M[i][j] += 1
                        M[j][i] += 1
                    # Vertical: i's bottom = j's top
                    if e_i[2] == e_j[0] and e_i[2] != 0:
                        M[i][j] += 1
                        M[j][i] += 1
    return M


def main():
    pieces_raw = load_pieces()
    # Convert to integer-tuple
    pieces = [tuple(int(x) for x in p) for p in pieces_raw]
    print(f"Loaded {len(pieces)} pieces; building compatibility graph...")
    M = build_piece_compatibility_graph(pieces)
    print(f"Graph built. Edges (sum): {M.sum() // 2}")
    print(f"Mean degree: {M.sum(axis=0).mean():.2f}, max: {M.max(axis=0).max()}")

    # 5 hint pieces
    hint_pieces = [207, 254, 138, 180, 248]
    print(f"\nHint pieces: {hint_pieces}")

    # Compute quantum walk from each hint piece
    eigvals, eigvecs = np.linalg.eigh(M.astype(float))

    # Initial state: superposition over 5 hint pieces
    psi0 = np.zeros(256, dtype=complex)
    for h in hint_pieces:
        psi0[h] = 1.0 / np.sqrt(5)

    # Time evolution
    times = [0.1, 1.0, 10.0, 100.0]
    print(f"\nTop-20 pieces by quantum-walk affinity to hints, at various times:")
    print(f"{'time':>6} {'top affinity pieces'}")
    for t in times:
        eVT = np.exp(-1j * t * eigvals / 100.0)  # scale t to avoid trivial overflow
        psi_t = eigvecs @ (eVT * (eigvecs.T @ psi0))
        p_t = np.abs(psi_t) ** 2
        top_indices = np.argsort(p_t)[::-1][:15]
        # Format
        out = []
        for idx in top_indices:
            out.append(f"{idx}({p_t[idx]:.3f})")
        print(f"  t={t}: {' '.join(out[:10])}")

    # Look at LATE-TIME affinity to identify which pieces are 'closest' to hints
    psi_late = eigvecs @ (np.exp(-1j * 100.0 * eigvals / 100.0) * (eigvecs.T @ psi0))
    p_late = np.abs(psi_late) ** 2

    print(f"\nTop 20 pieces with highest LATE-TIME affinity to hints:")
    top_indices = np.argsort(p_late)[::-1][:20]
    for idx in top_indices:
        # Annotate
        if idx in hint_pieces:
            print(f"  pid={idx:3} (HINT): p={p_late[idx]:.4f}")
        else:
            print(f"  pid={idx:3}: p={p_late[idx]:.4f}")


if __name__ == "__main__":
    main()
