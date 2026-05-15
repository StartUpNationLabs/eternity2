#!/usr/bin/env python3
"""Vol-72 — Trace Δ alongside ALNS during search.

Run a manual Python ALNS loop on a starting board. At each iteration:
- Apply destroy + greedy repair
- Compute new score AND new Δ
- Log (iter, score, delta, accept?)

Goal: see if Δ correlates with score during the search, or if ALNS
ever DECREASES Δ while keeping/improving score.

If yes: Δ-regularization may help.
If no: Δ is independent of ALNS's basin transitions.
"""

import collections
import json
import random
import sys
import csv
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


def score_and_delta(placement, pieces):
    grid = [(0, 0, 0, 0)] * 256
    for pos, (pid, rot) in placement.items():
        grid[pos] = rotate(pieces[pid], rot)
    # score
    matched = 0
    for r in range(16):
        for c in range(15):
            if grid[r*16+c][1] == grid[r*16+c+1][3]: matched += 1
    for r in range(15):
        for c in range(16):
            if grid[r*16+c][2] == grid[(r+1)*16+c][0]: matched += 1
    # delta (using v11 def)
    edge_inward = edge_piece_inward_colors(grid)
    A = collections.Counter(edge_inward.values())
    facing = border_facing_colors(grid)
    B = collections.Counter(facing.values())
    delta = sum(abs(A.get(c, 0) - B.get(c, 0)) for c in set(A) | set(B)) // 2
    return matched, delta


def main():
    pieces = load_pieces()
    start_path = sys.argv[1] if len(sys.argv) > 1 else "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    n_iters = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    rng = random.Random(seed)

    B = load_placement(start_path)
    score, delta = score_and_delta(B, pieces)
    print(f"Start: score={score}, delta={delta}, from {start_path}")

    # Simple destroy: pick random pair of positions, swap pieces + best rotation
    history = []
    for t in range(n_iters):
        # Random 2-piece swap (destroy = 2 cells, repair = swap their pieces)
        pos1, pos2 = rng.sample(range(256), 2)
        old1 = B[pos1]; old2 = B[pos2]
        # Try swap with all 4 rotations for each
        best = None
        for r1 in range(4):
            for r2 in range(4):
                B[pos1] = (old2[0], r1)
                B[pos2] = (old1[0], r2)
                s, d = score_and_delta(B, pieces)
                if best is None or s > best[0]:
                    best = (s, d, r1, r2)
        # Apply best
        B[pos1] = (old2[0], best[2])
        B[pos2] = (old1[0], best[3])
        score = best[0]
        delta = best[1]
        history.append((t, score, delta, pos1, pos2))
        if t % 100 == 0:
            print(f"  t={t}: score={score}, delta={delta}")

    print(f"Final: score={score}, delta={delta}")
    # Save trace
    Path("output/vol-72").mkdir(parents=True, exist_ok=True)
    with open(f"output/vol-72/trace_seed{seed}.csv", "w") as f:
        f.write("iter,score,delta,pos1,pos2\n")
        for t, s, d, p1, p2 in history:
            f.write(f"{t},{s},{d},{p1},{p2}\n")
    print(f"Saved trace to output/vol-72/trace_seed{seed}.csv")

    # Stats
    deltas = [d for _, _, d, _, _ in history]
    scores = [s for _, s, _, _, _ in history]
    print(f"\nScore range: {min(scores)} - {max(scores)}")
    print(f"Δ range: {min(deltas)} - {max(deltas)}")


if __name__ == "__main__":
    main()
