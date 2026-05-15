#!/usr/bin/env python3
"""Vol-66 — Basin-Level Genetic Search (BLGS) prototype.

Population of complete E2 boards. Each generation:
1. Score each individual.
2. Select top-K elites + tournament-pick parents.
3. Crossover: take a region from parent A, copy to parent B's rest,
   repair duplicate pieces via Hungarian assignment.
4. Mutation: optionally do a small local-swap perturbation.
5. Replace population with elites + offspring.

This is the FIRST INVENTED ALGORITHM per the user directive.

Initial population: our 4 known 458/459 records + McGavin 469.
"""

import collections
import csv
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"
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
    """Return pos -> (piece_id, rotation)."""
    with open(path) as f:
        d = json.load(f)
    arr = d.get("placement", [])
    pos_to = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pos = item.get("pos", idx)
        pos_to[pos] = (item["piece_id"], item["rotation"])
    return pos_to


def piece_kind(edges):
    n_border = sum(1 for c in edges if c == 0)
    return {0: "interior", 1: "edge", 2: "corner"}.get(n_border)


def score_board(placement, pieces):
    """Matched-edges score."""
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


def random_rectangle(rng, min_size=20, max_size=80):
    """Pick a random rectangle of cells in 16×16."""
    target_size = rng.randint(min_size, max_size)
    # Pick aspect-ratio-ish dimensions
    h = rng.randint(3, 10)
    w = max(2, target_size // h)
    h = min(h, H); w = min(w, W)
    r0 = rng.randint(0, H - h)
    c0 = rng.randint(0, W - w)
    cells = []
    for dr in range(h):
        for dc in range(w):
            cells.append((r0 + dr) * W + (c0 + dc))
    return cells


def repair_duplicates(child, pieces, rng):
    """After region inheritance, child may have duplicate piece-IDs.

    Use Hungarian assignment: for each piece-ID appearing in MORE than
    one cell, decide which cell keeps it; the others get reassigned
    via min-cost matching to UNUSED piece-IDs (the puzzle has 256
    distinct pieces).
    """
    pid_to_positions = collections.defaultdict(list)
    for pos, (pid, rot) in child.items():
        pid_to_positions[pid].append(pos)
    duplicates_positions = []
    keep_at = {}  # pid -> kept_pos
    for pid, positions in pid_to_positions.items():
        if len(positions) <= 1: continue
        # Keep at first; the rest are duplicates
        keep_at[pid] = positions[0]
        duplicates_positions.extend(positions[1:])
    if not duplicates_positions:
        return child
    used_pids = set(pid for pos, (pid, _) in child.items() if pos == keep_at.get(pid, None) or pid not in keep_at)
    used_pids = set()
    for pos, (pid, _) in child.items():
        if pos in duplicates_positions:
            continue
        used_pids.add(pid)
    free_pids = [p for p in range(256) if p not in used_pids]
    if len(free_pids) < len(duplicates_positions):
        # Shouldn't happen: total piece count = 256 = total cells
        return None
    # Hungarian: for each duplicate-position, find best (free_pid, rotation)
    # by counting matched edges with neighbors (assume neighbors fixed).
    n = len(duplicates_positions)
    m = len(free_pids)
    # Cost matrix: -matched_neighbors for each (dup-pos, free-pid)
    cost = np.full((n, m), 1e6)
    for i, pos in enumerate(duplicates_positions):
        r, c = divmod(pos, 16)
        # Find neighbor colors
        nbr_colors = {}
        if r > 0 and (r-1)*W+c not in duplicates_positions and (r-1)*W+c in child:
            npid, nrot = child[(r-1)*W+c]
            nbr_colors['N'] = rotate(pieces[npid], nrot)[2]  # neighbor's S color
        if r < H-1 and (r+1)*W+c not in duplicates_positions and (r+1)*W+c in child:
            npid, nrot = child[(r+1)*W+c]
            nbr_colors['S'] = rotate(pieces[npid], nrot)[0]
        if c > 0 and r*W+(c-1) not in duplicates_positions and r*W+(c-1) in child:
            npid, nrot = child[r*W+(c-1)]
            nbr_colors['W'] = rotate(pieces[npid], nrot)[1]
        if c < W-1 and r*W+(c+1) not in duplicates_positions and r*W+(c+1) in child:
            npid, nrot = child[r*W+(c+1)]
            nbr_colors['E'] = rotate(pieces[npid], nrot)[3]
        for j, pid in enumerate(free_pids):
            # Best rotation gives most matches
            best = 0
            for k in range(4):
                rs = rotate(pieces[pid], k)  # N, E, S, W
                matches = 0
                if 'N' in nbr_colors and rs[0] == nbr_colors['N']: matches += 1
                if 'E' in nbr_colors and rs[1] == nbr_colors['E']: matches += 1
                if 'S' in nbr_colors and rs[2] == nbr_colors['S']: matches += 1
                if 'W' in nbr_colors and rs[3] == nbr_colors['W']: matches += 1
                if matches > best: best = matches
            cost[i, j] = -best  # minimize -matches

    row_ind, col_ind = linear_sum_assignment(cost)
    new_child = dict(child)
    # Remove duplicates at duplicate positions
    for pos in duplicates_positions:
        del new_child[pos]
    for i, j in zip(row_ind, col_ind):
        pos = duplicates_positions[i]
        pid = free_pids[j]
        # Pick rotation that gives most matches
        r_, c_ = divmod(pos, 16)
        nbr_colors = {}
        if r_ > 0 and (r_-1)*W+c_ in new_child:
            npid, nrot = new_child[(r_-1)*W+c_]
            nbr_colors['N'] = rotate(pieces[npid], nrot)[2]
        if r_ < H-1 and (r_+1)*W+c_ in new_child:
            npid, nrot = new_child[(r_+1)*W+c_]
            nbr_colors['S'] = rotate(pieces[npid], nrot)[0]
        if c_ > 0 and r_*W+(c_-1) in new_child:
            npid, nrot = new_child[r_*W+(c_-1)]
            nbr_colors['W'] = rotate(pieces[npid], nrot)[1]
        if c_ < W-1 and r_*W+(c_+1) in new_child:
            npid, nrot = new_child[r_*W+(c_+1)]
            nbr_colors['E'] = rotate(pieces[npid], nrot)[3]
        best_rot = 0; best_matches = -1
        for k in range(4):
            rs = rotate(pieces[pid], k)
            matches = 0
            if 'N' in nbr_colors and rs[0] == nbr_colors['N']: matches += 1
            if 'E' in nbr_colors and rs[1] == nbr_colors['E']: matches += 1
            if 'S' in nbr_colors and rs[2] == nbr_colors['S']: matches += 1
            if 'W' in nbr_colors and rs[3] == nbr_colors['W']: matches += 1
            if matches > best_matches:
                best_matches = matches; best_rot = k
        new_child[pos] = (pid, best_rot)
    return new_child


def crossover(parent_a, parent_b, pieces, rng):
    """Take a rectangle from parent_a, paste into parent_b's rest, repair."""
    region = random_rectangle(rng)
    # Frame constraint: only inherit cells where piece-kind matches
    # If parent_a's piece at cell is a corner but the cell isn't a corner cell, skip.
    # Easiest: filter region to only cells where piece-kind == cell-kind.
    valid_region = []
    for pos in region:
        if pos not in parent_a: continue
        pid, _ = parent_a[pos]
        pk = piece_kind(pieces[pid])
        r, c = divmod(pos, 16)
        cell_kind = "corner" if (r in (0, 15) and c in (0, 15)) \
            else "edge" if (r in (0, 15) or c in (0, 15)) \
            else "interior"
        if pk == cell_kind:
            valid_region.append(pos)
    if not valid_region:
        return None
    child = dict(parent_b)
    for pos in valid_region:
        child[pos] = parent_a[pos]
    child = repair_duplicates(child, pieces, rng)
    return child


def main():
    pieces = load_canonical_pieces()
    rng = random.Random(42)

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
        pop.append((s, placement, Path(p).stem[:20]))
        print(f"Loaded {Path(p).stem[:30]} → score {s}")

    print(f"\nInitial population: {len(pop)}")
    print(f"Score range: {min(p[0] for p in pop)} - {max(p[0] for p in pop)}")

    # Run generations
    n_generations = 20
    n_offspring = 8
    elite_k = 2

    print(f"\nRunning {n_generations} generations, {n_offspring} offspring each...")
    best_ever = max(p[0] for p in pop)
    for gen in range(n_generations):
        pop.sort(key=lambda x: -x[0])
        elites = pop[:elite_k]
        offspring = []
        attempts = 0
        while len(offspring) < n_offspring and attempts < 50:
            attempts += 1
            a, b = rng.sample(pop, 2)
            child = crossover(a[1], b[1], pieces, rng)
            if child is None or len(child) != 256:
                continue
            child_score = score_board(child, pieces)
            offspring.append((child_score, child, f"gen{gen}-cross"))
            if child_score > best_ever:
                best_ever = child_score
                print(f"  Gen {gen}: NEW BEST {child_score} via crossover of "
                      f"{a[2]} × {b[2]}")
        pop = elites + offspring
        gen_max = max(p[0] for p in pop) if pop else 0
        gen_mean = sum(p[0] for p in pop) / len(pop) if pop else 0
        print(f"Gen {gen}: pop_size={len(pop)} max={gen_max} mean={gen_mean:.1f} "
              f"best_ever={best_ever}")

    # Save best
    pop.sort(key=lambda x: -x[0])
    print(f"\n=== FINAL ===")
    for s, _, lbl in pop[:5]:
        print(f"  {s} ({lbl})")

    # If best beats 459, save it
    if best_ever >= 460:
        # Save
        best_placement = pop[0][1]
        out = {
            "matched": pop[0][0],
            "placement": [{"pos": pos, "piece_id": pid, "rotation": rot}
                          for pos, (pid, rot) in sorted(best_placement.items())],
            "method": "BLGS",
        }
        out_path = f"output/vol-66/blgs_best_{pop[0][0]}_{int(time.time())}.json"
        Path("output/vol-66").mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\nSaved BEST to {out_path}")


if __name__ == "__main__":
    main()
