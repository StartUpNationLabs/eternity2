#!/usr/bin/env python3
"""Vol-122 M17 — Quantum-Walk Greedy Builder.

Algorithm:
1. Start with hints only (5 cells).
2. While unfilled cells exist:
   a. Compute quantum-walk affinity from placed pieces to all unplaced.
   b. Pick the UNPLACED piece with highest affinity.
   c. Find the EMPTY cell adjacent to placed cells with the most matched-edge
      potential for this piece (i.e., best rotation that maximizes matches
      with existing placed neighbors).
   d. Place.
3. Score board.

This is GREEDY + quantum-walk-prioritized. NEW algorithm.
"""
import json
import os
import sys

sys.path.insert(0, 'scripts')
try:
    import numpy as np
    from vol122_m17_quantum_clean_slate import build_piece_compatibility_graph
    from vol122_fft_signature import load_pieces, rot_edges, SIDE
except ImportError as e:
    print("Import error:", e)
    sys.exit(1)


def walk_affinity(M, placed_pids):
    """Quantum walk from placed set."""
    n = M.shape[0]
    psi0 = np.zeros(n, dtype=complex)
    for p in placed_pids:
        psi0[p] = 1.0
    if np.linalg.norm(psi0) < 1e-12:
        return np.zeros(n)
    psi0 = psi0 / np.linalg.norm(psi0)
    eigvals, eigvecs = np.linalg.eigh(M.astype(float))
    eVT = np.exp(-1j * 10.0 * eigvals / 100.0)
    psi_t = eigvecs @ (eVT * (eigvecs.T @ psi0))
    return np.abs(psi_t) ** 2


def best_placement_for_piece(piece_id, placement, pieces):
    """Find the empty cell + rotation that maximizes immediate matches for
    this piece given current placement."""
    e_orig = pieces[piece_id]
    best = None  # (matches, cell, rot)
    for r in range(SIDE):
        for c in range(SIDE):
            if placement[r][c] is not None: continue
            # Check border constraints
            is_top_border = r == 0
            is_bot_border = r == SIDE - 1
            is_left_border = c == 0
            is_right_border = c == SIDE - 1
            for rot in range(4):
                e = rot_edges(e_orig, rot)
                T, R, B, L = e
                # Border check
                if is_top_border and T != 0: continue
                if not is_top_border and T == 0: continue
                if is_bot_border and B != 0: continue
                if not is_bot_border and B == 0: continue
                if is_left_border and L != 0: continue
                if not is_left_border and L == 0: continue
                if is_right_border and R != 0: continue
                if not is_right_border and R == 0: continue
                # Count matches with placed neighbors
                matches = 0
                if r > 0 and placement[r-1][c] is not None:
                    nT, nR, nB, nL = placement[r-1][c]
                    if T == nB and T != 0: matches += 1
                    elif T != nB: matches -= 1  # mismatch penalty
                if r < SIDE-1 and placement[r+1][c] is not None:
                    nT, nR, nB, nL = placement[r+1][c]
                    if B == nT and B != 0: matches += 1
                    elif B != nT: matches -= 1
                if c > 0 and placement[r][c-1] is not None:
                    nT, nR, nB, nL = placement[r][c-1]
                    if L == nR and L != 0: matches += 1
                    elif L != nR: matches -= 1
                if c < SIDE-1 and placement[r][c+1] is not None:
                    nT, nR, nB, nL = placement[r][c+1]
                    if R == nL and R != 0: matches += 1
                    elif R != nL: matches -= 1
                # Score: prefer cells with at least one placed neighbor
                n_placed_neighbors = sum(
                    1 for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]
                    if 0 <= r+dr < SIDE and 0 <= c+dc < SIDE
                    and placement[r+dr][c+dc] is not None
                )
                if n_placed_neighbors == 0:
                    continue  # don't place isolated
                if best is None or matches > best[0]:
                    best = (matches, (r, c), rot)
    return best


def main():
    pieces_raw = load_pieces()
    pieces = [tuple(int(x) for x in p) for p in pieces_raw]
    M = build_piece_compatibility_graph(pieces)
    print(f"Built compat graph. Edges sum: {M.sum() // 2}")

    # Initialize with hints
    placement = [[None] * SIDE for _ in range(SIDE)]
    hint_data = [
        (34 // SIDE, 34 % SIDE, 207, 1),
        (45 // SIDE, 45 % SIDE, 254, 1),
        (135 // SIDE, 135 % SIDE, 138, 0),
        (210 // SIDE, 210 % SIDE, 180, 1),
        (221 // SIDE, 221 % SIDE, 248, 2),
    ]
    placed_pids = set()
    for r, c, pid, rot in hint_data:
        e = rot_edges(pieces[pid], rot)
        placement[r][c] = e
        placed_pids.add(pid)

    iteration = 0
    while True:
        unfilled = sum(1 for row in placement for cell in row if cell is None)
        if unfilled == 0:
            break
        iteration += 1
        if iteration > 256:
            break

        # Compute QW affinity from currently placed pieces
        aff = walk_affinity(M, list(placed_pids))
        unplaced = [(pid, aff[pid]) for pid in range(256) if pid not in placed_pids]
        unplaced.sort(key=lambda x: x[1], reverse=True)

        # Try the top-K affinity pieces; find one that can be placed
        placed_this_iter = False
        for pid, _ in unplaced[:20]:
            res = best_placement_for_piece(pid, placement, pieces)
            if res is not None:
                matches, (r, c), rot = res
                if matches >= 0:  # at least neutral
                    placement[r][c] = rot_edges(pieces[pid], rot)
                    placed_pids.add(pid)
                    if iteration % 20 == 0:
                        print(f"  iter {iteration}: placed pid={pid} at ({r},{c}) rot={rot}, matches={matches}")
                    placed_this_iter = True
                    break

        if not placed_this_iter:
            print(f"  iter {iteration}: stuck (no high-affinity placement); breaking")
            break

    placed = sum(1 for row in placement for cell in row if cell is not None)
    matched = 0
    for r in range(SIDE):
        for c in range(SIDE):
            if placement[r][c] is None: continue
            T, R, B, L = placement[r][c]
            if c + 1 < SIDE and placement[r][c+1]:
                nT, nR, nB, nL = placement[r][c+1]
                if R == nL and R != 0: matched += 1
            if r + 1 < SIDE and placement[r+1][c]:
                nT, nR, nB, nL = placement[r+1][c]
                if B == nT and B != 0: matched += 1

    print(f"\n=== QW GREEDY BUILDER RESULT ===")
    print(f"Placed: {placed}/256, matched: {matched}/480")


if __name__ == "__main__":
    main()
