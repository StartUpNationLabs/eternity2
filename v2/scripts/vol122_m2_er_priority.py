#!/usr/bin/env python3
"""Vol-122 M2-extension: effective-resistance priority for unfilled cells.

For a partial board (or empty board with just hints), compute:
- For each unfilled cell c, the EFFECTIVE-RESISTANCE-REDUCTION if c
  were to be filled with all 4 neighbor-matched edges.
- Rank cells by this reduction.

Visualization: print a 16×16 heatmap of priorities.
"""
import json
import os
import sys

sys.path.insert(0, 'scripts')
try:
    import numpy as np
    from vol122_fft_signature import load_pieces, rot_edges, SIDE
    from vol122_k11_4_compression import load_placement
except ImportError as e:
    print("Import error:", e)
    sys.exit(1)


def build_match_adjacency(placement, pieces):
    """Build the current matched-edge adjacency. Includes only edges with
    both endpoints filled AND matching."""
    n = SIDE * SIDE
    A = np.zeros((n, n))
    for r in range(SIDE):
        for c in range(SIDE):
            if placement[r][c] is None: continue
            pid, rot = placement[r][c]
            if pid >= len(pieces): continue
            T, R, B, L = rot_edges(pieces[pid], rot)
            i = r * SIDE + c
            if c + 1 < SIDE and placement[r][c+1]:
                pid2, rot2 = placement[r][c+1]
                if pid2 < len(pieces):
                    nT, nR, nB, nL = rot_edges(pieces[pid2], rot2)
                    if R == nL and R != 0:
                        j = r * SIDE + (c+1)
                        A[i][j] = A[j][i] = 1
            if r + 1 < SIDE and placement[r+1][c]:
                pid2, rot2 = placement[r+1][c]
                if pid2 < len(pieces):
                    nT, nR, nB, nL = rot_edges(pieces[pid2], rot2)
                    if B == nT and B != 0:
                        j = (r+1) * SIDE + c
                        A[i][j] = A[j][i] = 1
    return A


def er_after_filling(A, cell, hint_cells):
    """Effective resistance among hint_cells AFTER hypothetically filling
    cell with 4 matched neighbors."""
    r, c = cell // SIDE, cell % SIDE
    A_new = A.copy()
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < SIDE and 0 <= nc < SIDE:
            j = nr * SIDE + nc
            A_new[cell][j] = A_new[j][cell] = 1
    # Add tiny epsilon for numerical stability (Laplacian regularization)
    D = np.diag(A_new.sum(axis=1))
    L = D - A_new + 1e-9 * np.eye(SIDE * SIDE)
    try:
        L_inv = np.linalg.pinv(L)
    except np.linalg.LinAlgError:
        return float('inf')
    # Sum of pairwise R_eff among hint_cells
    total = 0.0
    diag = np.diag(L_inv)
    for i in hint_cells:
        for j in hint_cells:
            if j > i:
                total += diag[i] + diag[j] - 2 * L_inv[i][j]
    return total


def main():
    pieces = load_pieces()
    # Hint positions
    hint_positions = [34, 45, 135, 210, 221]  # canonical 5 hints

    # Test on an EMPTY board (just hints) — clean slate
    placement_hints_only = [[None] * SIDE for _ in range(SIDE)]
    canonical_hints = [
        (34 // SIDE, 34 % SIDE, 207, 1),
        (45 // SIDE, 45 % SIDE, 254, 1),
        (135 // SIDE, 135 % SIDE, 138, 0),
        (210 // SIDE, 210 % SIDE, 180, 1),
        (221 // SIDE, 221 % SIDE, 248, 2),
    ]
    for r, c, pid, rot in canonical_hints:
        placement_hints_only[r][c] = (pid, rot)
    # Compute baseline with hints-only
    A0 = build_match_adjacency(placement_hints_only, pieces)
    print(f"Hints-only board: {A0.sum()/2} matched edges (probably 0).")
    print(f"\n--- ER priority analysis on CLEAN SLATE (hints only) ---")
    # In hints-only, ALL cells are unfilled. Use a different baseline:
    # the BORDER cells should be filled to start (anchor border).
    # Skip clean-slate analysis for now and use the partial-board version.

    # Test on a sparser partial: border-DP partial (60 cells)
    path = "output/vol-122/border_partial_perm0_b0.json"
    if not os.path.exists(path):
        print(f"Path not found: {path}")
        return
    placement = load_placement(path)
    A = build_match_adjacency(placement, pieces)
    print(f"Loaded partial. Filled cells: {sum(1 for r in range(SIDE) for c in range(SIDE) if placement[r][c] is not None)}")
    print(f"Matched edges in graph: {int(A.sum() / 2)}")

    # Compute baseline ER among hint cells
    D = np.diag(A.sum(axis=1))
    L = D - A + 1e-9 * np.eye(SIDE * SIDE)
    L_inv = np.linalg.pinv(L)
    diag = np.diag(L_inv)
    baseline = 0.0
    for i in hint_positions:
        for j in hint_positions:
            if j > i:
                baseline += diag[i] + diag[j] - 2 * L_inv[i][j]
    print(f"Baseline sum-pair-ER among 5 hints: {baseline:.4f}")

    # For each unfilled cell, compute hypothetical reduction
    unfilled = [(r, c) for r in range(SIDE) for c in range(SIDE) if placement[r][c] is None]
    print(f"Unfilled cells: {len(unfilled)}")
    if not unfilled:
        print("Board is full; no analysis to do.")
        return
    priorities = []
    print("Computing per-cell priorities (could take ~30s)...")
    for r, c in unfilled:
        cell = r * SIDE + c
        new_er = er_after_filling(A, cell, hint_positions)
        reduction = baseline - new_er
        priorities.append(((r, c), reduction))
    priorities.sort(key=lambda x: x[1], reverse=True)
    print("\nTop 10 unfilled cells by ER reduction:")
    for (r, c), red in priorities[:10]:
        print(f"  ({r:2}, {c:2}) → reduction = {red:.4f}")
    print(f"\nBottom 5:")
    for (r, c), red in priorities[-5:]:
        print(f"  ({r:2}, {c:2}) → reduction = {red:.4f}")


if __name__ == "__main__":
    main()
