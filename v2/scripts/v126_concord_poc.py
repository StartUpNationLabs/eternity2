#!/usr/bin/env python3
"""V126-T1 — CONCORD: Veit Elser's difference map for E2.

Math:
  x ∈ R^{N × P × R}  (N=256 cells, P=256 pieces, R=4 rotations)
  Set A (cell-valid):    each cell holds exactly one (p, r). P_A = argmax+one-hot per cell.
  Set B (piece-unique + edge-consistent): each piece used once, edges match.
    P_B step 1: solve LAP (cells × pieces) using max-marginal score m[c, p] = max_r x[c, p, r].
                Each cell gets one piece p*(c).
    P_B step 2: for each (c, p*(c)), choose rotation r*(c) = argmax_r x[c, p, r] BIASED toward edge agreement.
  Iteration: x ← x + β · [ P_A( 2·P_B(x) − x ) − P_B(x) ]
  Convergence ⇔ P_A(P_B(x)) = P_B(x) (fixed point).

PoC: 7×7 generated puzzle (49 cells, 49 pieces, 4 rotations).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

REPO = Path(__file__).resolve().parents[1]


def load_puzzle_csv(csv_path: Path) -> tuple[int, list[tuple[int, int, int, int]]]:
    """Load CSV → (size, pieces) where each piece = (N, E, S, W) colors.

    BORDER (65535) → 0.
    """
    BORDER_RAW = 65535
    with open(csv_path) as f:
        size = int(f.readline().strip())
        pieces = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            sides = []
            for s in parts[:4]:
                v = int(s.strip(), 2)
                sides.append(0 if v == BORDER_RAW else v)
            pieces.append(tuple(sides))
    return size, pieces


def rotate_piece(piece, r: int):
    """Rotate piece by r * 90° CCW. Side order: (N, E, S, W).
    r=0: (N,E,S,W). r=1: (E,S,W,N). r=2: (S,W,N,E). r=3: (W,N,E,S).
    """
    N, E, S, W = piece
    return [(N, E, S, W),
            (E, S, W, N),
            (S, W, N, E),
            (W, N, E, S)][r]


def build_edge_arrays(pieces, R=4):
    """For each (piece, rotation), precompute (N, E, S, W) edge colors.
    Shape: edges[p, r] = (N, E, S, W).
    """
    P = len(pieces)
    edges = np.zeros((P, R, 4), dtype=np.int16)
    for p in range(P):
        for r in range(R):
            edges[p, r] = rotate_piece(pieces[p], r)
    return edges


def adjacent_cells(N, W):
    """Yield (i, j, side_i, side_j) for every adjacent pair.
    side_i: which side of i faces j (0=N, 1=E, 2=S, 3=W).
    side_j: which side of j faces i.
    """
    H = N // W
    for r in range(H):
        for c in range(W):
            i = r * W + c
            if c < W - 1:
                yield (i, i + 1, 1, 3)   # i's E ↔ j's W
            if r < H - 1:
                yield (i, i + W, 2, 0)   # i's S ↔ j's N


def project_A(x):
    """P_A: piece-uniqueness — each piece used in at most one cell.

    The natural projection onto the piece-permutation constraint is LAP
    on score s[c, p] = sum_r x[c, p, r] (or max_r). Returns x' with the
    selected (cell, piece) one-hot in rotation marginalized by softmax of x.

    For pieces NOT assigned to any cell: zero them out.
    For each cell c with piece p*(c): set rotation profile = softmax(x[c, p*, :]).
    """
    N, P, R = x.shape
    score = x.sum(axis=2)  # [N, P]
    cost = -score
    if P >= N:
        # pad rows so it's square
        pad = np.zeros((P - N, P), dtype=cost.dtype)
        cost_sq = np.vstack([cost, pad])
    else:
        cost_sq = cost
    row_ind, col_ind = linear_sum_assignment(cost_sq)
    # col_ind[c] for c < N is the assigned piece.
    out = np.zeros_like(x)
    for c in range(N):
        p = int(col_ind[c])
        if p >= P: continue
        # Soft rotation: softmax over r.
        rot_logits = x[c, p, :].astype(np.float64)
        rot_logits -= rot_logits.max()
        rot_probs = np.exp(rot_logits)
        rot_probs /= rot_probs.sum() + 1e-12
        out[c, p, :] = rot_probs
    return out


def project_A_hard(x):
    """Original P_A: cell-valid one-hot. Kept for reference."""
    N, P, R = x.shape
    flat = x.reshape(N, P * R)
    idx = flat.argmax(axis=1)
    out = np.zeros_like(flat)
    out[np.arange(N), idx] = 1.0
    return out.reshape(N, P, R)


def project_B(x, edges, adjacency, n_iter=3):
    """P_B: edge-consistency — adjacent cells' edges must agree.

    Soft projection: iteratively refine per-cell distributions over (piece,
    rotation) so that the marginal color at each shared edge matches.

    Algorithm (BP-style):
      For each cell c, compute the expected per-edge color distribution from
      x (marginalize over (piece, rotation)). For each adjacent (i, j, si, sj):
        target color distribution at boundary = avg of i's si distribution and
        j's sj distribution.
      Then for each (cell, piece, rotation), score = sum over its 4 sides
      of (target color prob at that side for piece/rot's color at that side).
      New x[c, p, r] = softmax_pr(score).

    Returns refined x with the same shape.
    """
    N, P, R = x.shape
    # Determine number of colors from edges
    n_colors = int(edges.max()) + 1
    # Normalize x to per-cell distribution.
    x_norm = x.copy()
    flat = x_norm.reshape(N, P * R)
    flat -= flat.max(axis=1, keepdims=True)
    flat = np.exp(flat * 4.0)  # sharpen
    flat /= (flat.sum(axis=1, keepdims=True) + 1e-12)
    x_norm = flat.reshape(N, P, R)

    out = x.copy()
    for _ in range(n_iter):
        # Compute per-cell per-side color distribution.
        # cell_side_color[c, side, color] = sum over (p, r) of x_norm[c, p, r] * (edges[p, r, side] == color)
        cell_side_color = np.zeros((N, 4, n_colors), dtype=np.float64)
        # Vectorize over (p, r): for each side, edges[p, r, side] gives a color index.
        for side in range(4):
            ec = edges[:, :, side]  # [P, R] of color indices
            # For each color, mask
            for color in range(n_colors):
                mask = (ec == color).astype(np.float64)  # [P, R]
                # cell_side_color[c, side, color] = sum_pr x_norm[c, p, r] * mask[p, r]
                cell_side_color[:, side, color] = x_norm.reshape(N, P * R) @ mask.reshape(-1)

        # For each adjacent (i, j, si, sj): target = (cell_side_color[i, si] + cell_side_color[j, sj]) / 2
        # We'll re-score (cell, piece, rot) at the boundary side using the OTHER cell's distribution
        # → this is a message-passing update.
        score = np.zeros_like(x)
        # Border cells: side facing outside has color 0; we'll handle borders by giving them a
        # one-hot color-0 target at outside-facing sides.
        for (i, j, si, sj) in adjacency:
            # For cell i, side si: target = cell_side_color[j, sj]
            for color in range(n_colors):
                # contribute to score[i, :, :] when edges[:, :, si] == color
                mask_i = (edges[:, :, si] == color).astype(np.float64)  # [P, R]
                score[i] += cell_side_color[j, sj, color] * mask_i
                mask_j = (edges[:, :, sj] == color).astype(np.float64)  # [P, R]
                score[j] += cell_side_color[i, si, color] * mask_j

        # Border-side handling: any side without adjacency must show color 0.
        # Compute which sides are "interior" by adjacency union.
        interior_sides = np.zeros((N, 4), dtype=bool)
        for (i, j, si, sj) in adjacency:
            interior_sides[i, si] = True
            interior_sides[j, sj] = True
        # For non-interior sides, require color 0: score contributes for pieces whose edge color = 0.
        for c in range(N):
            for side in range(4):
                if not interior_sides[c, side]:
                    mask = (edges[:, :, side] == 0).astype(np.float64)
                    score[c] += mask * 1.0  # weight 1.0 for border match

        # Soft update.
        flat = score.reshape(N, P * R)
        flat -= flat.max(axis=1, keepdims=True)
        flat = np.exp(flat * 1.0)
        flat /= (flat.sum(axis=1, keepdims=True) + 1e-12)
        x_norm = flat.reshape(N, P, R)
        out = x_norm.copy()

    return out


def score_assignment(assignment, edges, adjacency, N, W):
    """Score a hard assignment [N, P, R] (one-hot per cell).
    Returns # matched edges."""
    P, R = assignment.shape[1], assignment.shape[2]
    # Decode: for each cell, (piece, rot)
    cell_pr = np.zeros((N, 2), dtype=np.int32)
    valid = np.zeros(N, dtype=bool)
    for c in range(N):
        if assignment[c].sum() < 0.5:
            continue
        flat_idx = assignment[c].reshape(-1).argmax()
        p, r = divmod(int(flat_idx), R)
        cell_pr[c] = [p, r]
        valid[c] = True
    matched = 0
    for (i, j, si, sj) in adjacency:
        if not valid[i] or not valid[j]:
            continue
        pi, ri = cell_pr[i]
        pj, rj = cell_pr[j]
        ci = edges[pi, ri, si]
        cj = edges[pj, rj, sj]
        if ci == cj:
            matched += 1
    return matched, valid.sum()


def initialize_x(N, P, R, seed=42):
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 1, size=(N, P, R)).astype(np.float64)
    return x


def difference_map(x, P_A, P_B, beta=1.0):
    """One difference-map step:
       x ← x + β · [ P_A(2·P_B(x) − x) − P_B(x) ]
    """
    pb = P_B(x)
    pa = P_A(2 * pb - x)
    return x + beta * (pa - pb), pb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", type=str, default=str(REPO.parent / "data/puzzles/size_16_official_eternity.csv"),
                    help="Path to puzzle CSV")
    ap.add_argument("--max-iters", type=int, default=500)
    ap.add_argument("--beta", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", type=str, default=None)
    args = ap.parse_args()

    if args.out_dir is None:
        args.out_dir = str(REPO / "output/vol-126" / f"concord_{time.strftime('%Y%m%dT%H%M%S')}_seed{args.seed}")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = Path(args.puzzle)
    size, pieces = load_puzzle_csv(csv_path)
    N = size * size
    P = len(pieces)
    R = 4
    W = size

    print(f"Puzzle: {csv_path.name}  size={size}×{size}  cells={N}  pieces={P}", flush=True)
    print(f"β={args.beta}  max_iters={args.max_iters}  seed={args.seed}", flush=True)
    print(f"OUT_DIR={out_dir}", flush=True)

    edges = build_edge_arrays(pieces)
    adjacency = list(adjacent_cells(N, W))
    n_edges = len(adjacency)
    print(f"Adjacent edge pairs: {n_edges}", flush=True)

    x = initialize_x(N, P, R, seed=args.seed)
    rng = np.random.default_rng(args.seed + 1000)

    def P_A(x): return project_A(x)
    def P_B(x): return project_B(x, edges, adjacency)

    best_matched = -1
    best_iter = -1
    best_pb = None
    history = []

    t0 = time.time()
    x_prev = x.copy()
    for it in range(args.max_iters):
        x, pb = difference_map(x, P_A, P_B, beta=args.beta)

        # Score the current P_B output (the "candidate solution").
        matched, placed = score_assignment(pb, edges, adjacency, N, W)
        # Fixed-point measure: ||x_{n+1} - x_n||
        update_norm = float(np.linalg.norm(x - x_prev))
        history.append({"iter": int(it), "matched": int(matched), "placed": int(placed),
                        "x_norm": float(np.linalg.norm(x)),
                        "update_norm": update_norm})

        if matched > best_matched:
            best_matched = int(matched)
            best_iter = int(it)
            best_pb = pb.copy()

        if it % 10 == 0 or it < 20:
            print(f"iter={it:4d}  matched={matched:>3d}  placed={placed:>3d}  "
                  f"x_norm={history[-1]['x_norm']:>7.2f}  "
                  f"update={update_norm:>7.4f}  "
                  f"t={time.time()-t0:.1f}s", flush=True)

        if update_norm < 1e-6:
            print(f"FIXED POINT at iter={it}", flush=True)
            break
        x_prev = x.copy()

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s. Best matched={best_matched} at iter={best_iter}", flush=True)

    # Save best.
    if best_pb is not None:
        placement = []
        for c in range(N):
            if best_pb[c].sum() < 0.5: continue
            flat_idx = int(best_pb[c].reshape(-1).argmax())
            p, r = divmod(flat_idx, R)
            placement.append({"pos": int(c), "piece_id": int(p), "rotation": int(r)})
        out_path = out_dir / "best.json"
        with open(out_path, "w") as f:
            json.dump({
                "matched": best_matched,
                "best_iter": best_iter,
                "placement": placement,
                "args": vars(args),
            }, f, indent=2)
        print(f"Wrote {out_path}", flush=True)

    hist_path = out_dir / "history.json"
    with open(hist_path, "w") as f:
        json.dump(history, f, indent=2)
    print(f"Wrote {hist_path}", flush=True)


if __name__ == "__main__":
    main()
