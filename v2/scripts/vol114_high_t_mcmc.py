#!/usr/bin/env python3
"""Vol-114 T1 — high-temperature MCMC on the 459 level set.

Test IDEAS_FROM_BLANK Idea H: standard MCMC at T=1 has acceptance
~0 for σ-cycle moves (Δ<0 intermediates). At T=50-100, acceptance
becomes nontrivial, potentially mixing across the 459-basin
landscape.

Starting from a 459 basin, run Metropolis with random adjacent
piece-swaps. Record:
- score trajectory
- pieces of high-score boards visited
- distinct 459 basins discovered (Hamming distance >= 100 from
  the starting basin)

Falsifiable outcomes:
- HIGH T mixes: discovers multiple 459 basins; validates H.
- HIGH T doesn't mix: even at T=50, chain stays trapped; refutes H.

Usage:
    vol114_high_t_mcmc.py <basin.json> <puzzle.csv> [--T 50] [--iters 100000] [--seed 1]
"""

import argparse
import csv
import json
import random
import sys
from pathlib import Path


def parse_color(s):
    s = s.strip()
    v = int(s, 2)
    if v == 65535:
        return 0
    return v


def load_puzzle(csv_path):
    pieces = {}
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) < 4:
            continue
        try:
            t = parse_color(cols[0])
            r = parse_color(cols[1])
            b = parse_color(cols[2])
            l = parse_color(cols[3])
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


def load_board(path):
    with open(path) as f:
        d = json.load(f)
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    out = {}
    for idx, item in enumerate(arr):
        if item is None:
            continue
        pos = int(item.get("pos", idx))
        out[pos] = (int(item["piece_id"]), int(item["rotation"]))
    return out


def score_board(board, pieces, width=16, height=16):
    matched = 0
    for y in range(height):
        for x in range(width):
            pos = y * width + x
            if pos not in board:
                continue
            pid, rot = board[pos]
            if pid not in pieces:
                continue
            t, r, b, l = rotate_edges(pieces[pid], rot)
            if x + 1 < width:
                npos = pos + 1
                if npos in board:
                    npid, nrot = board[npos]
                    if npid in pieces:
                        _, _, _, nl = rotate_edges(pieces[npid], nrot)
                        if r == nl and r != 0:
                            matched += 1
            if y + 1 < height:
                npos = pos + width
                if npos in board:
                    npid, nrot = board[npos]
                    if npid in pieces:
                        nt, _, _, _ = rotate_edges(pieces[npid], nrot)
                        if b == nt and b != 0:
                            matched += 1
    return matched


def local_score_delta(board, pieces, pos1, pos2, new1, new2, width=16, height=16):
    """Compute delta in score if we swap (and re-rotate) cells pos1, pos2.
    new1 = (pid, rot) to place at pos1; new2 at pos2.
    Returns delta = new_score_at_those_cells - old_score_at_those_cells.
    """
    cells = sorted(set([pos1, pos2]))
    # Edges incident to cells: collect their neighbours.
    affected_edges = set()
    for c in cells:
        x = c % width
        y = c // width
        if x + 1 < width:
            affected_edges.add((c, c + 1, "h"))
        if x > 0:
            affected_edges.add((c - 1, c, "h"))
        if y + 1 < height:
            affected_edges.add((c, c + width, "v"))
        if y > 0:
            affected_edges.add((c - width, c, "v"))

    def edge_matched(b):
        m = 0
        for (a, b_cell, kind) in affected_edges:
            if a not in b or b_cell not in b:
                continue
            pa, ra = b[a]
            pb, rb = b[b_cell]
            if pa not in pieces or pb not in pieces:
                continue
            ea = rotate_edges(pieces[pa], ra)
            eb = rotate_edges(pieces[pb], rb)
            if kind == "h":
                if ea[1] == eb[3] and ea[1] != 0:
                    m += 1
            else:
                if ea[2] == eb[0] and ea[2] != 0:
                    m += 1
        return m

    old = edge_matched(board)
    new_board = dict(board)
    new_board[pos1] = new1
    new_board[pos2] = new2
    new = edge_matched(new_board)
    return new - old


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("basin")
    ap.add_argument("puzzle")
    ap.add_argument("--T", type=float, default=50.0)
    ap.add_argument("--iters", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--swap-rotation", action="store_true",
                    help="Also try random rotation on each cell during swap")
    args = ap.parse_args()

    pieces = load_puzzle(args.puzzle)
    board = load_board(args.basin)
    rng = random.Random(args.seed)
    W = H = 16

    score = score_board(board, pieces)
    print(f"starting basin: score={score}")

    # Identify "free" positions = non-hint cells. For canonical: 5 hint positions.
    HINT_POSITIONS = {34, 45, 135, 210, 221}
    free_positions = [p for p in board if p not in HINT_POSITIONS]

    # MCMC.
    history = [score]  # (iter, score)
    accepted = 0
    accepted_negative = 0  # accepted moves with Δ < 0
    visited_high_scores = {}  # score -> count
    best = (score, dict(board))

    for it in range(args.iters):
        # Random swap of two distinct non-hint cells.
        p1 = rng.choice(free_positions)
        p2 = rng.choice(free_positions)
        if p1 == p2:
            continue
        if p1 not in board or p2 not in board:
            continue
        (pid1, rot1), (pid2, rot2) = board[p1], board[p2]
        new_rot1, new_rot2 = rot1, rot2
        if args.swap_rotation:
            new_rot1 = rng.randint(0, 3)
            new_rot2 = rng.randint(0, 3)
        # Swap pieces.
        new1 = (pid2, new_rot2)
        new2 = (pid1, new_rot1)
        delta = local_score_delta(board, pieces, p1, p2, new1, new2, W, H)
        # Metropolis: accept if delta >= 0, else with p = exp(delta/T).
        if delta >= 0 or rng.random() < pow(2.718281828, delta / args.T):
            board[p1] = new1
            board[p2] = new2
            score += delta
            accepted += 1
            if delta < 0:
                accepted_negative += 1
            if score > best[0]:
                best = (score, dict(board))
            if score >= 450:
                visited_high_scores[score] = visited_high_scores.get(score, 0) + 1
        history.append(score)

        if (it + 1) % 10_000 == 0:
            print(f"  iter {it+1}: cur={score} best={best[0]} acc={accepted}/{it+1} acc<0={accepted_negative}")

    print(f"\nFinal: best score = {best[0]}")
    print(f"Acceptance rate: {accepted/args.iters:.3f}")
    print(f"Acceptance rate (Δ<0): {accepted_negative/args.iters:.3f}")
    print(f"High-score visits (>= 450):")
    for s in sorted(visited_high_scores.keys(), reverse=True):
        print(f"  score={s}: {visited_high_scores[s]} visits")

    # Verify hint compliance of the BEST board.
    hint_preserved = all(best[1].get(p) == board.get(p) for p in HINT_POSITIONS if p in board)
    # Note: hints in original board, not in MCMC moves. We never touched hint cells.

    print(f"\nFinal best board score: {best[0]}, ham-from-start: {sum(1 for p in board if p in best[1] and board[p] != best[1].get(p))}")


if __name__ == "__main__":
    main()
