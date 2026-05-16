#!/usr/bin/env python3
"""Vol-119 T3 follow-up — apply σ_S and measure ACTUAL Δ(S) on a board.

The sigma-thin search found pair bseed6 ↔ RECORD_TIE_459_p06 has a
cycle (N=190) with MIN B(S)/|S| ratio = 0.356. The vol-118 theorem
says Δ(S) ≈ -B(S)·p, but it's a heuristic; what we want is DIRECT
empirical Δ(S) for the thinnest subsets we can find.

For a chosen cycle and subset S:
- For each pos in S, replace board_A's (piece, rot) at pos with
  board_B's piece (via the σ map: board_B's piece at σ(pos) = piece_A at pos).
  Wait — σ: pos_A → pos_B is the position bijection. We want to take
  board_B's piece at pos_B and place it at pos_A. So for p ∈ S:
    let pid = pid_a[p]
    let σ(p) = pid_b_to_pos[pid]  (where board_B has this piece)
    Wait, σ is defined as σ(pos) = pid_b_to_pos[pid_a[pos]] — i.e., the position
    of the same piece-id in board B.
  Replacing means: at position p in board_A, place the piece-id that
  board_B placed at σ(p). i.e., new pid at p = pid_b[σ(p)] = pid_b[pid_b_to_pos[pid_a[p]]] = pid_a[p].
  That's the SAME piece! Hmm.

Wait, I need to rethink. σ is the bijection on POSITIONS that takes A
to B. Apply σ to subset S means: each piece in S moves from its A-position
to its B-position. Equivalently: at A-position p, place the piece that
USED TO be at A-position σ⁻¹(p) — which is the piece whose A-position is
σ⁻¹(p), i.e., pid_a[σ⁻¹(p)]. After applying σ_S, position p has piece
pid = pid_a[σ⁻¹(p)] with rotation = rot_b[p].

Actually the cleanest way is to think of σ_S as a position-permutation:
positions in S get permuted according to σ restricted to S. For this to
be well-defined as a permutation, σ(S) must equal S — which IS true for
a CYCLE (a cycle is closed under σ).

For S a contiguous subset of a cycle (positions in cycle order), σ(S)
may include the FIRST position OUTSIDE S (the cycle takes the last
element to a position not in S). So σ_S as a literal permutation only
works for S = cycle itself.

For PROPER subsets S ⊂ cycle, σ-subset application is defined as:
- For positions in S, use piece+rotation from board_B at the SAME position
  (NOT σ(position)).
- For positions outside S, keep board_A's piece+rotation.

This is the formulation in vol-117 / vol-118 (the "σ-subset application"
that the theorem bounds). It is NOT a permutation — it's a coordinate-wise
replacement of A's contents by B's contents on subset S.

That's what I'll implement.

Score the resulting hybrid board and compute Δ(S) = score(hybrid) - score(A).

Compares against the theorem: Δ ≈ -B(S)·p.

Usage:
  vol119_sigma_subset_apply_measure.py <board_a> <board_b> [--seed N]
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

W, H = 16, 16


def load_board(p):
    with open(p) as f:
        d = json.load(f)
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    pos_to_piece_rot = {}
    for idx, item in enumerate(arr):
        if item is None:
            continue
        pos = int(item.get("pos", idx))
        pid = int(item["piece_id"])
        rot = int(item["rotation"])
        pos_to_piece_rot[pos] = (pid, rot)
    return pos_to_piece_rot


def load_puzzle_pieces(csv_path: Path) -> Dict[int, Tuple[int, int, int, int]]:
    """Parse the canonical puzzle CSV into {pid: (top, right, bottom, left)}.

    Color encoding: 16-bit binary. 1111111111111111 = BORDER (we use 0).
    """
    pieces = {}
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) < 4:
            continue
        try:
            t = int(cols[0], 2)
            r = int(cols[1], 2)
            b = int(cols[2], 2)
            l = int(cols[3], 2)
            if t == 65535: t = 0
            if r == 65535: r = 0
            if b == 65535: b = 0
            if l == 65535: l = 0
        except ValueError:
            continue
        pieces[pid] = (t, r, b, l)
        pid += 1
    return pieces


def rotate_edges(edges, rot):
    t, r, b, l = edges
    if rot == 0:
        return (t, r, b, l)
    elif rot == 1:
        return (l, t, r, b)
    elif rot == 2:
        return (b, l, t, r)
    else:
        return (r, b, l, t)


def score_board(pos_to_piece_rot, pieces) -> int:
    """Count matched edges (right-of-A == left-of-B; bottom-of-A == top-of-B).

    Skip BORDER-BORDER edges (vol-118 T13). Two cells are adjacent if
    they're at (x, y) and (x+1, y) or (x, y+1).
    """
    matched = 0
    for pos, (pid, rot) in pos_to_piece_rot.items():
        x, y = pos % W, pos // W
        edges_a = rotate_edges(pieces[pid], rot)  # (top, right, bottom, left)

        # Right neighbor
        if x < W - 1:
            np = pos + 1
            if np in pos_to_piece_rot:
                npid, nrot = pos_to_piece_rot[np]
                edges_n = rotate_edges(pieces[npid], nrot)
                if edges_a[1] == edges_n[3]:  # right_a == left_n
                    if not (edges_a[1] == 0 and edges_n[3] == 0):
                        matched += 1
        # Bottom neighbor
        if y < H - 1:
            np = pos + W
            if np in pos_to_piece_rot:
                npid, nrot = pos_to_piece_rot[np]
                edges_n = rotate_edges(pieces[npid], nrot)
                if edges_a[2] == edges_n[0]:  # bottom_a == top_n
                    if not (edges_a[2] == 0 and edges_n[0] == 0):
                        matched += 1
    return matched


def sigma_cycles(pos_a, pid_to_pos_b):
    s = {}
    for pos, (pid, _) in pos_a.items():
        bpos = pid_to_pos_b.get(pid)
        if bpos is not None and bpos != pos:
            s[pos] = bpos
    visited = set()
    cycles = []
    for start in s:
        if start in visited:
            continue
        cycle = []
        cur = start
        while cur not in visited and cur in s:
            visited.add(cur)
            cycle.append(cur)
            cur = s[cur]
        if cycle:
            cycles.append(cycle)
    cycles.sort(key=len, reverse=True)
    return cycles


def grid_neighbors(p):
    x, y = p % W, p // W
    out = []
    if x > 0:
        out.append(p - 1)
    if x < W - 1:
        out.append(p + 1)
    if y > 0:
        out.append(p - W)
    if y < H - 1:
        out.append(p + W)
    return out


def boundary(subset):
    b = 0
    for p in subset:
        for q in grid_neighbors(p):
            if q not in subset:
                b += 1
    return b


def apply_sigma_subset(board_a, board_b, subset):
    """Return board where positions in subset use board_B's content, rest A."""
    out = dict(board_a)
    for p in subset:
        if p in board_b:
            out[p] = board_b[p]
    return out


def greedy_min_boundary_subsets(cycle, max_k=None, max_iters=300, rng=None):
    """For each k ∈ {1..N-1}, find a min-B(S) subset of size k via greedy local opt.

    Returns list of (k, B, subset).
    """
    if rng is None:
        rng = random.Random()
    N = len(cycle)
    if max_k is None:
        max_k = N - 1
    cycle_set = set(cycle)
    results = []
    for k in range(1, min(max_k, N - 1) + 1):
        best_b = float('inf')
        best_subset = None
        n_restarts = max(3, max_iters // max(1, N))
        for _ in range(n_restarts):
            subset = set(rng.sample(cycle, k))
            cur_b = boundary(subset)
            improved = True
            iters = 0
            while improved and iters < 4 * N:
                improved = False
                iters += 1
                ins = list(subset)
                outs = list(cycle_set - subset)
                rng.shuffle(ins)
                rng.shuffle(outs)
                made_swap = False
                for p_in in ins:
                    for p_out in outs:
                        new_subset = (subset - {p_in}) | {p_out}
                        new_b = boundary(new_subset)
                        if new_b < cur_b:
                            subset = new_subset
                            cur_b = new_b
                            improved = True
                            made_swap = True
                            break
                    if made_swap:
                        break
            if cur_b < best_b:
                best_b = cur_b
                best_subset = subset.copy()
        results.append((k, best_b, best_subset))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board_a")
    ap.add_argument("board_b")
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cycle-idx", type=int, default=-1,
                    help="if ≥0, only test this cycle; else test all ≥3-cycles")
    ap.add_argument("--max-k", type=int, default=None,
                    help="max subset size to consider (default min(N-1, 60))")
    ap.add_argument("--top-n-per-k", type=int, default=3,
                    help="how many random/swap restarts per (cycle, k)")
    args = ap.parse_args()

    rng = random.Random(args.seed)

    pieces = load_puzzle_pieces(Path(args.puzzle))
    print(f"# loaded {len(pieces)} pieces from puzzle CSV", file=sys.stderr)

    board_a = load_board(Path(args.board_a))
    board_b = load_board(Path(args.board_b))
    print(f"# board_a: {len(board_a)} placements", file=sys.stderr)
    print(f"# board_b: {len(board_b)} placements", file=sys.stderr)

    s_a = score_board(board_a, pieces)
    s_b = score_board(board_b, pieces)
    print(f"# score(A) = {s_a}, score(B) = {s_b}, δ = {s_b - s_a}")

    pid_to_pos_b = {pid: p for p, (pid, _) in board_b.items()}
    cycles = sigma_cycles(board_a, pid_to_pos_b)
    print(f"# {len(cycles)} σ-cycles, sizes: {[len(c) for c in cycles][:10]}{'...' if len(cycles) > 10 else ''}")

    overall_best = (-float('inf'), None, None, None)  # (delta, cycle_idx, k, subset)

    for ci, cycle in enumerate(cycles):
        if args.cycle_idx >= 0 and ci != args.cycle_idx:
            continue
        N = len(cycle)
        if N < 3:
            continue

        max_k = args.max_k if args.max_k is not None else min(N - 1, 60)
        print(f"\n## cycle #{ci}, N={N}, max-k={max_k}")
        subsets = greedy_min_boundary_subsets(cycle, max_k=max_k, max_iters=args.top_n_per_k * 50, rng=rng)
        print(f"  k    B(S)   ratio    Δ(S)   Δ-θ(predicted)")
        for k, b, subset in subsets:
            hybrid = apply_sigma_subset(board_a, board_b, subset)
            s_h = score_board(hybrid, pieces)
            delta = s_h - s_a
            predicted = -b  # vol-118 theorem with p=1
            ratio = b / k
            print(f"  {k:3d}  {b:4d}  {ratio:5.2f}  {delta:+5d}     {predicted:+5d}")
            if delta > overall_best[0]:
                overall_best = (delta, ci, k, subset)

    print()
    print(f"# === BEST OVERALL ===")
    delta, ci, k, subset = overall_best
    print(f"# Δ_max = {delta:+d}  (cycle #{ci}, k={k})")
    if delta > 0:
        print(f"# (!) σ-subset application produced SCORE LIFT!")
        print(f"# Subset positions: {sorted(subset)[:20]}{'...' if len(subset) > 20 else ''}")


if __name__ == "__main__":
    main()
