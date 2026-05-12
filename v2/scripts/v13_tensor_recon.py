#!/usr/bin/env python3
"""Vol-13 — preliminary reconnaissance for the boundary-MPS approach.

Builds the per-cell tile tensor T[N,E,S,W] = #(piece, rotation) with those
colors, then prints diagnostics:

  * total nonzeros (= 256 * 4 = 1024 by construction; verify uniqueness)
  * max multiplicity (how many pieces share a (T,R,B,L) tuple under rotation?)
  * marginal entropy per leg
  * raw size of the tensor (memory if dense int32)
  * how degenerate the border rows are (1 forced edge value, 3 free)

This tells us whether per-row contraction is bounded-multiplicity (= clean
Wang-tile / Liang formulation) or whether identical signatures appear across
pieces (multiplicities > 1).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from v11_load_e2 import load


BORDER = 0
N_COLORS = 22
DOM = N_COLORS + 1  # colors 0..22 (0 = BORDER)


def all_rotations(piece):
    """Return the 4 rotations of a piece, each as (T, R, B, L)."""
    t, r, b, l = piece
    return [
        (t, r, b, l),
        (l, t, r, b),
        (b, l, t, r),
        (r, b, l, t),
    ]


def build_interior_tile_tensor(pieces):
    """T[N,E,S,W] = # (piece_id, rotation) producing those edges.

    Interior cell: no BORDER edges allowed. piece_id has 0 border edges.
    """
    T = np.zeros((DOM, DOM, DOM, DOM), dtype=np.int32)
    border_counts = (pieces == BORDER).sum(axis=1)
    interior_idx = np.where(border_counts == 0)[0]
    assert len(interior_idx) == 196, f"expected 196 interior pieces, got {len(interior_idx)}"

    placements = 0
    for pid in interior_idx:
        for (t, r, b, l) in all_rotations(pieces[pid]):
            if t == BORDER or r == BORDER or b == BORDER or l == BORDER:
                continue
            T[t, r, b, l] += 1
            placements += 1
    return T, placements


def build_edge_tile_tensor(pieces, side):
    """Edge piece tensor for a particular border side.

    side ∈ {'N','E','S','W'}: which edge must be BORDER.
    """
    T = np.zeros((DOM, DOM, DOM, DOM), dtype=np.int32)
    border_counts = (pieces == BORDER).sum(axis=1)
    edge_idx = np.where(border_counts == 1)[0]
    assert len(edge_idx) == 56

    pinned_axis = {'N': 0, 'E': 1, 'S': 2, 'W': 3}[side]
    placements = 0
    for pid in edge_idx:
        for (t, r, b, l) in all_rotations(pieces[pid]):
            edges = (t, r, b, l)
            if edges[pinned_axis] != BORDER:
                continue
            if any(edges[i] == BORDER for i in range(4) if i != pinned_axis):
                continue
            T[t, r, b, l] += 1
            placements += 1
    return T, placements


def build_corner_tile_tensor(pieces, ns, ew):
    """Corner piece tensor. ns ∈ {'N','S'}, ew ∈ {'E','W'}."""
    T = np.zeros((DOM, DOM, DOM, DOM), dtype=np.int32)
    border_counts = (pieces == BORDER).sum(axis=1)
    corner_idx = np.where(border_counts == 2)[0]
    assert len(corner_idx) == 4

    ns_axis = {'N': 0, 'S': 2}[ns]
    ew_axis = {'E': 1, 'W': 3}[ew]
    placements = 0
    for pid in corner_idx:
        for (t, r, b, l) in all_rotations(pieces[pid]):
            edges = (t, r, b, l)
            if edges[ns_axis] != BORDER or edges[ew_axis] != BORDER:
                continue
            other = [i for i in range(4) if i not in (ns_axis, ew_axis)]
            if any(edges[i] == BORDER for i in other):
                continue
            T[t, r, b, l] += 1
            placements += 1
    return T, placements


def report(name, T, expected_total):
    nnz = int((T > 0).sum())
    total = int(T.sum())
    maxmul = int(T.max())
    mem_int32 = T.nbytes / 1024 / 1024
    nbytes_sparse = nnz * (4 + 4 + 4 + 4 + 4)  # 4 indices + 1 value
    print(f"  {name}")
    print(f"    nonzero entries  : {nnz} / {DOM**4} ({nnz/DOM**4:.4%})")
    print(f"    total placements : {total}  (expected: {expected_total})")
    print(f"    max multiplicity : {maxmul}")
    print(f"    dense int32 size : {mem_int32:.2f} MB")
    print(f"    sparse  int32 size: {nbytes_sparse} bytes ({nbytes_sparse/1024:.1f} KB)")

    # entropy per leg (marginalize over other 3)
    eps = 1e-12
    for axis, label in enumerate(['N (top)', 'E (right)', 'S (bottom)', 'W (left)']):
        m = T.sum(axis=tuple(i for i in range(4) if i != axis)).astype(np.float64)
        m = m / max(m.sum(), eps)
        ent = -(m * np.log2(m + eps)).sum()
        nonzero_colors = int((m > 0).sum())
        print(f"    marginal entropy axis-{axis} {label:11s} : {ent:.3f} bits   ({nonzero_colors}/{DOM} colors)")


def main():
    print("loading canonical E2 ...")
    e2 = load()
    pieces = e2['pieces']
    print(f"pieces.shape = {pieces.shape}")
    n_hints = len(e2['hints'])
    print(f"hints: {n_hints}")
    print()

    print(f"building tile tensors (DOM={DOM} = 22 colors + BORDER)")
    print(f"  raw shape = {(DOM,)*4} = {DOM**4} entries each")
    print()

    t0 = time.time()
    T_int, n_int = build_interior_tile_tensor(pieces)
    print(f"INTERIOR (196 pieces × 4 rot = 784 placements)")
    report("interior", T_int, 196 * 4)
    print()

    for side in ['N', 'E', 'S', 'W']:
        T_edge, n_edge = build_edge_tile_tensor(pieces, side)
        print(f"EDGE / side={side} (56 pieces × 1 valid rotation per piece per side)")
        report(f"edge-{side}", T_edge, 56)
        print()

    for ns in ['N', 'S']:
        for ew in ['E', 'W']:
            T_c, _ = build_corner_tile_tensor(pieces, ns, ew)
            print(f"CORNER / {ns}+{ew} (4 corners total, each fits 1 specific corner)")
            report(f"corner-{ns}{ew}", T_c, 1)
            print()

    print(f"reconnaissance done in {time.time()-t0:.2f}s")

    # Diagnostic: how many distinct (T,R,B,L) signatures across interior pieces?
    # If max multiplicity == 1, the boundary-MPS would be a TRUE Wang-tile
    # contraction. If > 1, multiplicities are part of the Z-Wang weight.
    sigs_int = set()
    for pid in range(256):
        bc = int((pieces[pid] == BORDER).sum())
        if bc != 0:
            continue
        for rot, (t, r, b, l) in enumerate(all_rotations(pieces[pid])):
            sigs_int.add((t, r, b, l))
    print(f"distinct interior (T,R,B,L) signatures : {len(sigs_int)} / {196*4} = {len(sigs_int)/(196*4):.4f}")
    print(f"average multiplicity                   : {196*4 / len(sigs_int):.4f}")


if __name__ == '__main__':
    main()
