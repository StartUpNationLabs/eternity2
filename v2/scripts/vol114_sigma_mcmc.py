#!/usr/bin/env python3
"""Vol-114 T1b — σ-cycle MCMC. Like vol-22 basin-escape recipe but
done as a Metropolis chain. At each step:
1. Pick a target board (random from a corpus of 459 basins).
2. Compute σ-cycles between current and target.
3. Pick a random cycle (weighted by size or uniform).
4. Apply it as a single move (multi-cell swap of pieces).
5. Metropolis acceptance: Δ ≥ 0 always; else exp(Δ/T).

The hypothesis: σ-cycle moves of size 5-20 cells might cross the
459 barrier when single-piece moves can't. With multiple basins
in the corpus, the chain can mix THROUGH them.
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
    if v == 65535: return 0
    return v


def load_puzzle(csv_path):
    pieces = {}
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) < 4: continue
        try:
            t = parse_color(cols[0]); r = parse_color(cols[1])
            b = parse_color(cols[2]); l = parse_color(cols[3])
        except ValueError: continue
        pieces[pid] = (t, r, b, l)
        pid += 1
    return pieces


def rotate_edges(edges, rot):
    t, r, b, l = edges
    if rot == 0: return (t, r, b, l)
    elif rot == 1: return (l, t, r, b)
    elif rot == 2: return (b, l, t, r)
    else: return (r, b, l, t)


def load_board(path):
    with open(path) as f:
        d = json.load(f)
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    out = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pos = int(item.get("pos", idx))
        out[pos] = (int(item["piece_id"]), int(item["rotation"]))
    return out


def score_board(board, pieces, W=16, H=16):
    matched = 0
    for y in range(H):
        for x in range(W):
            pos = y * W + x
            if pos not in board: continue
            pid, rot = board[pos]
            if pid not in pieces: continue
            t, r, b, l = rotate_edges(pieces[pid], rot)
            if x + 1 < W and (pos+1) in board:
                npid, nrot = board[pos+1]
                if npid in pieces:
                    _, _, _, nl = rotate_edges(pieces[npid], nrot)
                    if r == nl and r != 0: matched += 1
            if y + 1 < H and (pos+W) in board:
                npid, nrot = board[pos+W]
                if npid in pieces:
                    nt, _, _, _ = rotate_edges(pieces[npid], nrot)
                    if b == nt and b != 0: matched += 1
    return matched


def sigma_cycles(board_a, board_b):
    b_pos = {}
    for pos, (pid, _) in board_b.items():
        b_pos[pid] = pos
    sigma = {}
    for pos, (pid, _) in board_a.items():
        if pid in b_pos:
            sigma[pos] = b_pos[pid]
    seen = set()
    cycles = []
    for start in list(sigma.keys()):
        if start in seen: continue
        cyc = []
        q = start
        while q not in seen and q in sigma:
            seen.add(q)
            cyc.append(q)
            q = sigma[q]
        if len(cyc) >= 2:
            cycles.append(cyc)
    cycles.sort(key=lambda c: -len(c))
    return cycles


def apply_cycle(board, target, cycle):
    """Apply ONE σ-cycle: replace board[c] with target[c] for c in cycle."""
    new = dict(board)
    for c in cycle:
        if c in target:
            new[c] = target[c]
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("start_basin")
    ap.add_argument("puzzle")
    ap.add_argument("--corpus", nargs="+", required=True,
                    help="Other 459 basins to use as σ-cycle targets")
    ap.add_argument("--T", type=float, default=2.0)
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--max-cyc-size", type=int, default=20,
                    help="Skip cycles larger than this (cost too high)")
    args = ap.parse_args()

    pieces = load_puzzle(args.puzzle)
    rng = random.Random(args.seed)
    board = load_board(args.start_basin)
    corpus = [load_board(p) for p in args.corpus]

    score = score_board(board, pieces)
    print(f"start score: {score}")
    print(f"corpus size: {len(corpus)} basins")

    best = (score, dict(board))
    high_visits = {}
    for it in range(args.iters):
        # Random target from corpus.
        target = rng.choice(corpus)
        # σ-cycles to target.
        cycles = sigma_cycles(board, target)
        # Filter by size.
        cycles = [c for c in cycles if len(c) <= args.max_cyc_size]
        if not cycles:
            continue
        # Pick a random cycle.
        cyc = rng.choice(cycles)
        new_board = apply_cycle(board, target, cyc)
        new_score = score_board(new_board, pieces)
        delta = new_score - score
        if delta >= 0 or rng.random() < pow(2.71828, delta / args.T):
            board = new_board
            score = new_score
            if score > best[0]:
                best = (score, dict(board))
            if score >= 450:
                high_visits[score] = high_visits.get(score, 0) + 1
        if (it + 1) % 100 == 0:
            print(f"  iter {it+1}: cur={score} best={best[0]}")

    print(f"\nFinal: best={best[0]}")
    print("High-score visits (>= 450):")
    for s in sorted(high_visits.keys(), reverse=True):
        print(f"  {s}: {high_visits[s]}")


if __name__ == "__main__":
    main()
