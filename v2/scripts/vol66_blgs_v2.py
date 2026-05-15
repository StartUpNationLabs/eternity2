#!/usr/bin/env python3
"""Vol-66 — BLGS v2: smarter crossover via piece-swap.

When parent A's region is copied into parent B:
- A's region uses piece-set S_A.
- B's region uses piece-set S_B.
- For each piece p in S_A ∩ S_B: it appears at pos_a (in A's region)
  AND at some pos_b (outside region in B's board). After import, p
  exists at both pos_a and pos_b → duplicate.
- FIX: at pos_b, put B's OLD piece that was at pos_a — call this q.
  Then q (previously at pos_a) goes to pos_b. This is a piece-swap
  between region and complement.

After this swap, every piece is at exactly one position. The
question is whether the new placement of q at pos_b matches colors
well. We pick q's BEST rotation at pos_b given the current neighbors.
"""

import collections
import json
import random
import sys
import time
from pathlib import Path

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
    with open(path) as f:
        d = json.load(f)
    arr = d.get("placement", [])
    pos_to = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pos = item.get("pos", idx)
        pos_to[pos] = (item["piece_id"], item["rotation"])
    return pos_to


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
    n_border = sum(1 for c in edges if c == 0)
    return {0: "interior", 1: "edge", 2: "corner"}.get(n_border)


def cell_kind(pos):
    r, c = divmod(pos, 16)
    if r in (0, 15) and c in (0, 15): return "corner"
    if r in (0, 15) or c in (0, 15): return "edge"
    return "interior"


def random_rectangle(rng, min_size=20, max_size=80):
    target = rng.randint(min_size, max_size)
    h = rng.randint(3, 10)
    w = max(2, target // h)
    h = min(h, H); w = min(w, W)
    r0 = rng.randint(0, H - h)
    c0 = rng.randint(0, W - w)
    return [(r0 + dr) * W + (c0 + dc) for dr in range(h) for dc in range(w)]


def best_rotation(pid, pos, placement, pieces):
    """Pick rotation maximizing local matches given neighbors."""
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
    """Smarter crossover: piece-swap repair (no Hungarian).

    Take rectangle from A. Place A's pieces+rotations at those positions.
    For each piece p in A's region that ALSO appears in B's board outside
    the region (at pos_b): place B's old piece (that was at pos_in_region)
    at pos_b, with best rotation.
    """
    region = random_rectangle(rng)
    # Frame-kind filter: only include positions where A's piece-kind == cell-kind
    valid_region = []
    for pos in region:
        if pos not in parent_a: continue
        pid, _ = parent_a[pos]
        if piece_kind(pieces[pid]) == cell_kind(pos):
            valid_region.append(pos)
    if not valid_region:
        return None

    child = dict(parent_b)
    # b_piece_at_region[pos] = parent_b's piece originally at pos (in region)
    b_piece_at_region = {pos: parent_b[pos] for pos in valid_region}
    # piece_to_pos_in_b: pid -> pos (in parent_b's whole board)
    piece_to_pos_in_b = {pid: pos for pos, (pid, _) in parent_b.items()}

    # Replace region with A's pieces
    for pos in valid_region:
        child[pos] = parent_a[pos]

    # Now find duplicates and swap
    # For each pos in valid_region, A inserted (a_pid, a_rot).
    # If a_pid appears in parent_b at some pos_b OUTSIDE valid_region, that's a dup.
    # Resolution: at pos_b, put B's old piece at pos (which is b_piece_at_region[pos]).
    # If pos_b is ALREADY in valid_region (rare; means A's piece at pos_b in region too),
    # this gets tricky. Skip these edge cases for v2.
    valid_region_set = set(valid_region)
    swaps_done = 0
    for pos in valid_region:
        a_pid, _ = parent_a[pos]
        pos_b = piece_to_pos_in_b.get(a_pid)
        if pos_b is None or pos_b == pos: continue
        if pos_b in valid_region_set:
            # A's piece a_pid was at pos_b in B's board, but pos_b is also in
            # the region (so A's value just overwrote it). Skip; the next
            # iteration handles A's pos_b.
            continue
        # Place b_piece_at_region[pos] at pos_b
        old_b_pid_rot = b_piece_at_region[pos]
        old_b_pid = old_b_pid_rot[0]
        # Check frame kind match
        if piece_kind(pieces[old_b_pid]) != cell_kind(pos_b):
            continue  # would violate frame, skip swap (creates duplicate; bail)
        # Best rotation at pos_b for piece old_b_pid
        # Temporarily remove existing piece (the duplicate a_pid) at pos_b
        if pos_b in child:
            del child[pos_b]
        new_rot = best_rotation(old_b_pid, pos_b, child, pieces)
        child[pos_b] = (old_b_pid, new_rot)
        swaps_done += 1

    # Verify no duplicates
    pids = [pid for pid, _ in child.values()]
    if len(set(pids)) != len(pids):
        # Couldn't fully repair; reject
        return None
    if len(child) != 256:
        return None
    return child


def main():
    pieces = load_canonical_pieces()
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 42)

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

    print(f"Initial population: {len(pop)} boards, scores: {sorted([p[0] for p in pop])}")

    n_generations = 30
    n_offspring = 16
    elite_k = 3

    print(f"Running {n_generations} generations, {n_offspring} offspring each...")
    best_ever = max(p[0] for p in pop)
    history = []
    for gen in range(n_generations):
        pop.sort(key=lambda x: -x[0])
        elites = pop[:elite_k]
        offspring = []
        attempts = 0
        while len(offspring) < n_offspring and attempts < 200:
            attempts += 1
            a, b = rng.sample(pop, 2)
            child = crossover_v2(a[1], b[1], pieces, rng)
            if child is None: continue
            child_score = score_board(child, pieces)
            offspring.append((child_score, child, f"gen{gen}"))
            if child_score > best_ever:
                best_ever = child_score
                print(f"  Gen {gen}: NEW BEST {child_score} from {a[2]} × {b[2]}")
        # Keep diversity: elites + offspring
        pop = elites + offspring
        gen_max = max(p[0] for p in pop) if pop else 0
        gen_mean = sum(p[0] for p in pop) / len(pop) if pop else 0
        history.append((gen, gen_max, gen_mean, best_ever))
        print(f"Gen {gen:>2}: max={gen_max} mean={gen_mean:.1f} best={best_ever}")

    pop.sort(key=lambda x: -x[0])
    print(f"\n=== FINAL ===")
    for s, _, lbl in pop[:5]:
        print(f"  {s} ({lbl})")

    if best_ever > 469:
        out = {
            "matched": pop[0][0],
            "placement": [{"pos": pos, "piece_id": pid, "rotation": rot}
                          for pos, (pid, rot) in sorted(pop[0][1].items())],
            "method": "BLGS-v2",
        }
        out_path = f"output/vol-66/blgs_v2_record_{pop[0][0]}_{int(time.time())}.json"
        Path("output/vol-66").mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\n!!! RECORD-BREAKING SAVED: {out_path}")


if __name__ == "__main__":
    main()
