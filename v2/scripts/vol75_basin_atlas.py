#!/usr/bin/env python3
"""Vol-75 — Basin atlas: run N short ALNS-from-cold-CP, collect features.

For each run:
- CP profile: random one of {joe_depth150, joe_depth150_bp, BLACKWOOD_RAW}
- ALNS budget: 60s
- Record: final score, Δ, Hamming to McGavin, Hamming to each existing record

Goal: characterize what basins our pipeline samples and how they relate
to McGavin's. Maybe a basin with low Hamming-to-McGavin appears.
"""

import collections
import csv
import json
import subprocess
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


def compute_features(placement, pieces, mcg_placement):
    # Score
    grid = [(0, 0, 0, 0)] * 256
    for pos, (pid, rot) in placement.items():
        grid[pos] = rotate(pieces[pid], rot)
    matched = 0
    for r in range(16):
        for c in range(15):
            if grid[r*16+c][1] == grid[r*16+c+1][3]: matched += 1
    for r in range(15):
        for c in range(16):
            if grid[r*16+c][2] == grid[(r+1)*16+c][0]: matched += 1

    # Δ
    edge_inward = edge_piece_inward_colors(grid)
    A = collections.Counter(edge_inward.values())
    facing = border_facing_colors(grid)
    B = collections.Counter(facing.values())
    delta = sum(abs(A.get(c, 0) - B.get(c, 0)) for c in set(A) | set(B)) // 2

    # Hamming to McGavin
    ham_mcg = sum(1 for pos in placement
                  if pos in mcg_placement and placement[pos][0] != mcg_placement[pos][0])
    return matched, delta, ham_mcg


def main():
    pieces = load_pieces()
    mcg = load_placement("output/vol-65/mcgavin_469.json")

    # Sample 8 quick ALNS runs from cold start (different seeds)
    # Use existing alns_only with random initial board (no CP partial — make one)
    # Easier: use the existing cold portfolio bins or just alns_pt
    # Simpler still: take vol-32 458 board as starting + N short ALNS
    n_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    budget_ms = int(sys.argv[2]) if len(sys.argv) > 2 else 30000

    # Use 4 different starting boards (varying basins) + different seeds
    starting_boards = [
        ("vol-32-458", "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json"),
        ("local-459", "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json"),
        ("vol-61-s17", "output/vol-61/faithful_sota_20260515T174124/stage3_seed17.json"),
        ("vol-61-s200", "output/vol-61/faithful_sota_20260515T174124/stage3_seed200.json"),
    ]
    Path("output/vol-75").mkdir(parents=True, exist_ok=True)
    print(f"{'start':<14} | {'seed':>4} | {'score':>5} | {'Δ':>3} | {'Ham→McG':>7}")
    results = []
    for name, path in starting_boards:
        for seed in [1, 7, 17, 42]:
            proc = subprocess.run(
                ["target/release/alns_only", "--cp-board", path,
                 "--alns-budget-ms", str(budget_ms), "--seed", str(seed),
                 "--ops", "winning5", "--t", "1.0"],
                capture_output=True, text=True, timeout=budget_ms / 1000 + 30,
            )
            saved = None
            for line in (proc.stderr + proc.stdout).split("\n"):
                if line.startswith("saved:"):
                    saved = line.split(":", 1)[1].strip(); break
            if not saved or not Path(saved).exists():
                print(f"{name:<14} | {seed:>4} | FAILED")
                continue
            pl = load_placement(saved)
            score, delta, ham = compute_features(pl, pieces, mcg)
            results.append((name, seed, score, delta, ham, saved))
            print(f"{name:<14} | {seed:>4} | {score:>5} | {delta:>3} | {ham:>7}")

    # Summary
    if results:
        print(f"\n{len(results)} runs")
        # By score range
        scores = [r[2] for r in results]
        print(f"Score range: {min(scores)} - {max(scores)} (mean {sum(scores)/len(scores):.1f})")
        # Best (closest to McGavin)
        results.sort(key=lambda r: r[4])
        print(f"\nTop 5 by closest Hamming to McGavin:")
        for r in results[:5]:
            print(f"  {r[0]} seed={r[1]}: score={r[2]}, Δ={r[3]}, Ham={r[4]}")


if __name__ == "__main__":
    main()
