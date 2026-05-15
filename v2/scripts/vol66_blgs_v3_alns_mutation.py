#!/usr/bin/env python3
"""Vol-66 v3 — BLGS with ALNS mutation via Rust alns_only subprocess.

After crossover, save the child to JSON and run our Rust alns_only
binary for a short budget (e.g., 30s) to "polish" each offspring.
This is the v3 spec from the BLGS concept page.

Expensive but the right thing: Python crossover + Rust ALNS mutation
combines high-level population control with low-level move quality.
"""

import collections
import json
import random
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"
ALNS_BIN = "target/release/alns_only"
W = H = 16


def load_canonical_pieces():
    BORDER_RAW = 65535
    pieces = []
    with open(PUZZLE_CSV) as f:
        size = int(f.readline().strip())
        for idx, line in enumerate(f):
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            def col(s):
                v = int(s.strip(), 2)
                return 0 if v == BORDER_RAW else v
            pieces.append((col(parts[0]), col(parts[1]),
                           col(parts[2]), col(parts[3])))
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
    pos_to = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pos = item.get("pos", idx)
        pos_to[pos] = (item["piece_id"], item["rotation"])
    return pos_to


def save_placement(path, placement, pieces):
    score = score_board(placement, pieces)
    out = {
        "matched": score,
        "placement": [{"pos": pos, "piece_id": pid, "rotation": rot}
                      for pos, (pid, rot) in sorted(placement.items())],
    }
    Path(Path(path).parent).mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f)


def score_board(placement, pieces):
    grid = [[None] * 16 for _ in range(16)]
    for pos, (pid, rot) in placement.items():
        r, c = divmod(pos, 16)
        grid[r][c] = rotate(pieces[pid], rot)
    matched = 0
    for r in range(16):
        for c in range(15):
            if grid[r][c] and grid[r][c + 1]:
                if grid[r][c][1] == grid[r][c + 1][3]: matched += 1
    for r in range(15):
        for c in range(16):
            if grid[r][c] and grid[r + 1][c]:
                if grid[r][c][2] == grid[r + 1][c][0]: matched += 1
    return matched


def piece_kind(edges):
    nb = sum(1 for c in edges if c == 0)
    return {0: "interior", 1: "edge", 2: "corner"}.get(nb)


def cell_kind(pos):
    r, c = divmod(pos, 16)
    if r in (0, 15) and c in (0, 15): return "corner"
    if r in (0, 15) or c in (0, 15): return "edge"
    return "interior"


def random_rect(rng, min_size=20, max_size=80):
    target = rng.randint(min_size, max_size)
    h = rng.randint(3, 10)
    w = max(2, target // h)
    h = min(h, H); w = min(w, W)
    r0 = rng.randint(0, H - h)
    c0 = rng.randint(0, W - w)
    return [(r0 + dr) * W + (c0 + dc) for dr in range(h) for dc in range(w)]


def best_rotation(pid, pos, placement, pieces):
    r, c = divmod(pos, 16)
    nbr = {}
    if r > 0 and (r - 1) * W + c in placement:
        np_, nr = placement[(r - 1) * W + c]
        nbr['N'] = rotate(pieces[np_], nr)[2]
    if r < H - 1 and (r + 1) * W + c in placement:
        np_, nr = placement[(r + 1) * W + c]
        nbr['S'] = rotate(pieces[np_], nr)[0]
    if c > 0 and r * W + (c - 1) in placement:
        np_, nr = placement[r * W + (c - 1)]
        nbr['W'] = rotate(pieces[np_], nr)[1]
    if c < W - 1 and r * W + (c + 1) in placement:
        np_, nr = placement[r * W + (c + 1)]
        nbr['E'] = rotate(pieces[np_], nr)[3]
    best_k = 0; best_m = -1
    for k in range(4):
        rs = rotate(pieces[pid], k)
        m = 0
        if 'N' in nbr and rs[0] == nbr['N']: m += 1
        if 'E' in nbr and rs[1] == nbr['E']: m += 1
        if 'S' in nbr and rs[2] == nbr['S']: m += 1
        if 'W' in nbr and rs[3] == nbr['W']: m += 1
        if m > best_m: best_m, best_k = m, k
    return best_k


def crossover_v2(parent_a, parent_b, pieces, rng):
    """v2 piece-swap repair."""
    region = random_rect(rng)
    valid_region = []
    for pos in region:
        if pos not in parent_a: continue
        pid, _ = parent_a[pos]
        if piece_kind(pieces[pid]) == cell_kind(pos):
            valid_region.append(pos)
    if not valid_region: return None
    child = dict(parent_b)
    b_at_region = {pos: parent_b[pos] for pos in valid_region}
    piece_to_pos_b = {pid: pos for pos, (pid, _) in parent_b.items()}
    for pos in valid_region:
        child[pos] = parent_a[pos]
    region_set = set(valid_region)
    for pos in valid_region:
        a_pid, _ = parent_a[pos]
        pos_b = piece_to_pos_b.get(a_pid)
        if pos_b is None or pos_b == pos or pos_b in region_set:
            continue
        old_b = b_at_region[pos]
        if piece_kind(pieces[old_b[0]]) != cell_kind(pos_b):
            continue
        if pos_b in child:
            del child[pos_b]
        new_rot = best_rotation(old_b[0], pos_b, child, pieces)
        child[pos_b] = (old_b[0], new_rot)
    pids = [p for p, _ in child.values()]
    if len(set(pids)) != len(pids) or len(child) != 256:
        return None
    return child


def alns_mutate(placement, pieces, seed, budget_ms=20000):
    """Run alns_only on a board, return improved placement."""
    Path("output/vol-66/blgs_v3").mkdir(parents=True, exist_ok=True)
    inp = f"output/vol-66/blgs_v3/child_in_{seed}_{int(time.time()*1000)%100000}.json"
    save_placement(inp, placement, pieces)
    proc = subprocess.run(
        [ALNS_BIN, "--cp-board", inp, "--alns-budget-ms", str(budget_ms),
         "--seed", str(seed), "--ops", "minimal", "--t", "1.0"],
        capture_output=True, text=True, timeout=budget_ms / 1000 + 30,
    )
    # alns_only's output line "saved: <path>" gives the best board
    saved = None
    for line in proc.stdout.split("\n"):
        if line.startswith("saved:"):
            saved = line.split(":", 1)[1].strip()
    if not saved or not Path(saved).exists():
        return placement  # fallback
    return load_placement(saved)


def main():
    pieces = load_canonical_pieces()
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 42)
    n_gen = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    n_offspring = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    mutation_ms = int(sys.argv[4]) if len(sys.argv) > 4 else 15000

    initial = [
        "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json",
        "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json",
        "output/vol-61/faithful_sota_20260515T174124/stage3_seed17.json",
        "output/vol-61/faithful_sota_20260515T174124/stage3_seed200.json",
        "output/vol-65/mcgavin_469.json",
    ]
    pop = []
    for p in initial:
        if not Path(p).exists(): continue
        placement = load_placement(p)
        s = score_board(placement, pieces)
        pop.append((s, placement, Path(p).stem[:25]))
    print(f"Initial: {[p[0] for p in pop]}, best={max(p[0] for p in pop)}")

    best_ever = max(p[0] for p in pop)
    for gen in range(n_gen):
        pop.sort(key=lambda x: -x[0])
        elites = pop[:2]
        offspring = []
        attempts = 0
        while len(offspring) < n_offspring and attempts < 30:
            attempts += 1
            a, b = rng.sample(pop, 2)
            child = crossover_v2(a[1], b[1], pieces, rng)
            if child is None: continue
            pre_score = score_board(child, pieces)
            # ALNS mutation
            polished = alns_mutate(child, pieces, rng.randint(1, 1000), mutation_ms)
            post_score = score_board(polished, pieces)
            offspring.append((post_score, polished, f"gen{gen}-c{a[2][:8]}x{b[2][:8]}"))
            if post_score > best_ever:
                best_ever = post_score
                print(f"  Gen {gen} child{len(offspring)}: NEW BEST {post_score} "
                      f"(pre-mutation {pre_score})")
        pop = elites + offspring
        gen_max = max(p[0] for p in pop)
        gen_mean = sum(p[0] for p in pop) / len(pop)
        print(f"Gen {gen}: max={gen_max} mean={gen_mean:.1f} best_ever={best_ever}")

    pop.sort(key=lambda x: -x[0])
    print(f"\nFINAL top 5: {[p[0] for p in pop[:5]]}")
    if best_ever > 469:
        out_path = f"output/vol-66/blgs_v3/RECORD_{best_ever}_{int(time.time())}.json"
        save_placement(out_path, pop[0][1], pieces)
        print(f"!!! RECORD: {out_path}")


if __name__ == "__main__":
    main()
