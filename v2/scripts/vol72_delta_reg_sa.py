#!/usr/bin/env python3
"""Vol-72 — Δ-Regularized SA-ALNS (proper).

f(B) = score(B) - λ × Δ(B)

SA acceptance: accept if f_new > f_old, OR with prob exp(Δf / T).

Standard ALNS at λ=0. Higher λ biases toward low-Δ basins.

Run on local-459 starting board for N iterations, multiple λ.
Track score trajectory + final Δ.
"""

import collections
import csv
import json
import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, 'scripts')
from v11_ns1_verify import edge_piece_inward_colors, border_facing_colors


def load_pieces():
    BORDER_RAW = 65535
    pieces = []
    with open("../data/puzzles/size_16_official_eternity.csv") as f:
        size = int(f.readline().strip())
        for idx, line in enumerate(f):
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            def col(s):
                v = int(s.strip(), 2)
                return 0 if v == BORDER_RAW else v
            pieces.append((col(parts[0]), col(parts[1]), col(parts[2]), col(parts[3])))
    return pieces


def rotate(edges, k):
    n, e, s, w = edges
    if k == 0: return (n, e, s, w)
    if k == 1: return (w, n, e, s)
    if k == 2: return (s, w, n, e)
    if k == 3: return (e, s, w, n)


def load_placement(path):
    with open(path) as f: d = json.load(f)
    arr = d.get("placement", [])
    out = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pos = item.get("pos", idx)
        out[pos] = (item["piece_id"], item["rotation"])
    return out


def quads_from(placement, pieces):
    out = [(0, 0, 0, 0)] * 256
    for pos, (pid, rot) in placement.items():
        out[pos] = rotate(pieces[pid], rot)
    return out


def score_board(quads):
    m = 0
    for r in range(16):
        for c in range(15):
            if quads[r*16+c][1] == quads[r*16+c+1][3]: m += 1
    for r in range(15):
        for c in range(16):
            if quads[r*16+c][2] == quads[(r+1)*16+c][0]: m += 1
    return m


def compute_delta(quads):
    edge_inward = edge_piece_inward_colors(quads)
    A = collections.Counter(edge_inward.values())
    facing = border_facing_colors(quads)
    B = collections.Counter(facing.values())
    return sum(abs(A.get(c, 0) - B.get(c, 0)) for c in set(A) | set(B)) // 2


def piece_kind(edges):
    nb = sum(1 for c in edges if c == 0)
    return {0: "interior", 1: "edge", 2: "corner"}.get(nb)


def cell_kind(pos):
    r, c = divmod(pos, 16)
    if r in (0, 15) and c in (0, 15): return "corner"
    if r in (0, 15) or c in (0, 15): return "edge"
    return "interior"


def main():
    pieces = load_pieces()
    start = sys.argv[1] if len(sys.argv) > 1 else "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json"
    lam = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    n_iters = int(sys.argv[3]) if len(sys.argv) > 3 else 500
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 42
    rng = random.Random(seed)

    B = load_placement(start)
    quads = quads_from(B, pieces)
    score = score_board(quads)
    delta = compute_delta(quads)
    print(f"Start: score={score}, delta={delta}, λ={lam}")
    T = 1.0
    best_score = score
    best_delta = delta
    acc_count = 0
    rej_count = 0
    for t in range(n_iters):
        # Random 2-piece swap respecting frame
        for _ in range(10):  # retry up to 10 times to find a valid swap
            pos1, pos2 = rng.sample(range(256), 2)
            old1 = B[pos1]; old2 = B[pos2]
            # Same kind?
            if piece_kind(pieces[old1[0]]) != piece_kind(pieces[old2[0]]):
                continue
            # OK, try
            # Pick best rotation for each at new position
            old_quads = quads.copy()
            # Try all (r1, r2) for new arrangement
            best_local = None
            for r1 in range(4):
                # Frame check
                test_q = rotate(pieces[old2[0]], r1)
                if cell_kind(pos1) == "interior" and 0 in test_q: continue
                for r2 in range(4):
                    test_q2 = rotate(pieces[old1[0]], r2)
                    if cell_kind(pos2) == "interior" and 0 in test_q2: continue
                    # Apply
                    quads[pos1] = test_q
                    quads[pos2] = test_q2
                    s_new = score_board(quads)
                    d_new = compute_delta(quads)
                    f_new = s_new - lam * d_new
                    if best_local is None or f_new > best_local[0]:
                        best_local = (f_new, s_new, d_new, r1, r2)
            quads[pos1] = old_quads[pos1]
            quads[pos2] = old_quads[pos2]
            if best_local is None: continue
            f_new, s_new, d_new, r1, r2 = best_local
            f_old = score - lam * delta
            delta_f = f_new - f_old
            # SA accept
            if delta_f >= 0 or rng.random() < math.exp(min(delta_f / T, 0)):
                B[pos1] = (old2[0], r1)
                B[pos2] = (old1[0], r2)
                quads[pos1] = rotate(pieces[B[pos1][0]], r1)
                quads[pos2] = rotate(pieces[B[pos2][0]], r2)
                score = s_new
                delta = d_new
                acc_count += 1
                if score > best_score: best_score = score
                if delta < best_delta: best_delta = delta
            else:
                rej_count += 1
            break  # done with this iteration
        if t % 50 == 0:
            print(f"  t={t}: score={score}, Δ={delta}, best=({best_score}, {best_delta})")

    print(f"\nFinal: score={score}, Δ={delta}")
    print(f"Best: score={best_score}, Δ={best_delta}")
    print(f"Accepted: {acc_count}, Rejected: {rej_count}")


if __name__ == "__main__":
    main()
