#!/usr/bin/env python3
"""Vol-122 M17 — Quantum walk on PARTIAL board (clean slate + some placement).

Given a partial board (e.g., border partial with 60 cells), compute:
- Which UNPLACED pieces have highest quantum-walk affinity to PLACED pieces
  via the piece-compatibility graph.
- Use this as a piece-ordering heuristic for filling.

Different from M17 clean slate: here the 'sources' are placed pieces,
not just hint pieces. This gives a richer 'preference network'.
"""
import json
import os
import sys

sys.path.insert(0, 'scripts')
try:
    import numpy as np
    from vol122_m17_quantum_clean_slate import build_piece_compatibility_graph
    from vol122_fft_signature import load_pieces
except ImportError as e:
    print("Import error:", e)
    sys.exit(1)


def walk_affinity(M, source_pieces, t=10.0):
    n = M.shape[0]
    psi0 = np.zeros(n, dtype=complex)
    for p in source_pieces:
        psi0[p] = 1.0
    psi0 = psi0 / np.linalg.norm(psi0)
    eigvals, eigvecs = np.linalg.eigh(M.astype(float))
    # Scale t to handle large eigvals
    eVT = np.exp(-1j * t * eigvals / 100.0)
    psi_t = eigvecs @ (eVT * (eigvecs.T @ psi0))
    return np.abs(psi_t) ** 2


def main():
    # Use Python parser (may have small offsets but structure should be OK)
    pieces_raw = load_pieces()
    pieces = [tuple(int(x) for x in p) for p in pieces_raw]
    print(f"Loaded {len(pieces)} pieces; building graph...")
    M = build_piece_compatibility_graph(pieces)

    # Load a partial board
    partial_path = "output/vol-122/border_partial_perm0_b0.json"
    with open(partial_path) as f:
        data = json.load(f)
    placed_pids = set(p['piece_id'] for p in data['placement'])
    print(f"\nLoaded {len(placed_pids)} placed pieces from {partial_path}")
    unplaced = [p for p in range(256) if p not in placed_pids]
    print(f"Unplaced: {len(unplaced)}")

    p_aff = walk_affinity(M, list(placed_pids), t=10.0)

    # Restrict to unplaced
    unplaced_aff = [(pid, p_aff[pid]) for pid in unplaced]
    unplaced_aff.sort(key=lambda x: x[1], reverse=True)
    print(f"\nTop 20 UNPLACED pieces by affinity to placed-set:")
    for pid, aff in unplaced_aff[:20]:
        print(f"  pid={pid:3}: aff={aff:.5f}")
    print(f"\nBottom 5 (least affinity):")
    for pid, aff in unplaced_aff[-5:]:
        print(f"  pid={pid:3}: aff={aff:.5f}")


if __name__ == "__main__":
    main()
