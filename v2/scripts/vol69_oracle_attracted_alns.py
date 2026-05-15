#!/usr/bin/env python3
"""Vol-69 — Oracle-Attracted ALNS prototype (Python).

Augmented objective: f(B) = score(B) - λ × hamming(B, oracle)
where oracle = McGavin 469 board.

Implementation: simple Python ALNS with random-swap destroy + greedy
repair. The point isn't to be the fastest ALNS — it's to test
whether the OA-objective biases search toward McGavin's basin.

If λ is well-chosen, the algorithm should drive hamming(B, McGavin)
down while maintaining reasonable score. If λ is too high, score
collapses. If too low, no progress.

Sweep over λ schedules and starting boards.
"""

import collections
import csv
import json
import random
import sys
import time
from pathlib import Path

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"
W = H = 16


def load_pieces():
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


def hamming_to_oracle(placement, oracle):
    """Count cells where placement and oracle differ in piece_id."""
    diff = 0
    for pos, (pid, _) in placement.items():
        oracle_at_pos = oracle.get(pos)
        if oracle_at_pos is None or oracle_at_pos[0] != pid:
            diff += 1
    return diff


def random_swap_destroy(rng, k=4):
    """Pick k positions to destroy."""
    return rng.sample(range(256), k)


def greedy_fill(placement, destroyed_positions, pieces, oracle, lam, rng):
    """Greedy fill destroyed cells, optionally with oracle attraction.

    For each destroyed cell, pick the piece-rotation that maximizes
    local matched edges (count of color matches with non-destroyed
    neighbors), with a bonus for matching oracle's piece at that pos.
    """
    # Find pieces not currently placed (the destroyed pieces are now unused)
    used_pids = set(pid for pos, (pid, _) in placement.items()
                    if pos not in destroyed_positions)
    free_pids = [p for p in range(256) if p not in used_pids]
    # For each destroyed cell, find best piece+rotation
    # Order matters; randomize order for tie-breaking
    rng.shuffle(destroyed_positions)
    rng.shuffle(free_pids)

    new = dict(placement)
    for pos in destroyed_positions:
        if pos in new: del new[pos]
    for pos in destroyed_positions:
        r_, c_ = divmod(pos, 16)
        # Neighbor colors (from non-destroyed neighbors)
        nbr = {}
        if r_ > 0 and (r_ - 1) * W + c_ in new:
            npid, nrot = new[(r_ - 1) * W + c_]
            nbr['N'] = rotate(pieces[npid], nrot)[2]
        if r_ < H - 1 and (r_ + 1) * W + c_ in new:
            npid, nrot = new[(r_ + 1) * W + c_]
            nbr['S'] = rotate(pieces[npid], nrot)[0]
        if c_ > 0 and r_ * W + (c_ - 1) in new:
            npid, nrot = new[r_ * W + (c_ - 1)]
            nbr['W'] = rotate(pieces[npid], nrot)[1]
        if c_ < W - 1 and r_ * W + (c_ + 1) in new:
            npid, nrot = new[r_ * W + (c_ + 1)]
            nbr['E'] = rotate(pieces[npid], nrot)[3]
        # Find best (pid, rot) — for cell_kind compatibility
        # For now allow any piece (sloppy; in real version respect frame)
        best = None
        for pid in free_pids:
            for k in range(4):
                rs = rotate(pieces[pid], k)
                m = 0
                if 'N' in nbr and rs[0] == nbr['N']: m += 1
                if 'E' in nbr and rs[1] == nbr['E']: m += 1
                if 'S' in nbr and rs[2] == nbr['S']: m += 1
                if 'W' in nbr and rs[3] == nbr['W']: m += 1
                # Oracle attraction bonus
                oracle_at_pos = oracle.get(pos)
                if oracle_at_pos is not None and oracle_at_pos[0] == pid:
                    m += int(lam)  # boost if matching oracle's piece
                score_val = m
                if best is None or score_val > best[0]:
                    best = (score_val, pid, k)
        if best is None:
            continue
        new[pos] = (best[1], best[2])
        if best[1] in free_pids:
            free_pids.remove(best[1])
    return new


def main():
    pieces = load_pieces()
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    n_iters = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    lam_max = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    start_path = sys.argv[4] if len(sys.argv) > 4 else "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json"
    oracle_path = "output/vol-65/mcgavin_469.json"

    start = load_placement(start_path)
    oracle = load_placement(oracle_path)

    B = dict(start)
    B_score = score_board(B, pieces)
    B_ham = hamming_to_oracle(B, oracle)
    print(f"Start: score={B_score}, hamming-to-McGavin={B_ham}")
    print(f"Running {n_iters} iters, lambda_max={lam_max}")

    history = []
    best_score = B_score
    best_ham = B_ham
    # Index oracle's piece positions
    oracle_pid_to_pos = {pid: pos for pos, (pid, _) in oracle.items()}
    for t in range(n_iters):
        lam = lam_max * (t / n_iters)  # linear ramp from 0 to lam_max
        # ORACLE-SWAP move (50% of the time): swap a piece at pos p with
        # McGavin's-target-piece-currently-elsewhere.
        if rng.random() < 0.5:
            # Pick a position where current piece != oracle's piece
            mismatch_positions = [pos for pos, (pid, _) in B.items()
                                  if oracle.get(pos) and pid != oracle[pos][0]]
            if not mismatch_positions:
                continue
            p = rng.choice(mismatch_positions)
            target_pid = oracle[p][0]
            target_rot = oracle[p][1]
            # Find where target_pid currently is
            q = None
            for pos, (pid, _) in B.items():
                if pid == target_pid:
                    q = pos; break
            if q is None or q == p: continue
            # Swap pieces at p and q (and pick best rotations)
            old_p = B[p]; old_q = B[q]
            B_new = dict(B)
            # Place target_pid at p with target rotation (matching oracle)
            B_new[p] = (target_pid, target_rot)
            # Place old_p's piece at q, with best rotation given new neighbors
            B_new[q] = (old_p[0], old_p[1])  # keep old rotation for now
        else:
            # Regular destroy-and-repair
            k_destroy = rng.randint(8, 30)
            destroyed = random_swap_destroy(rng, k=k_destroy)
            B_new = greedy_fill(B, destroyed, pieces, oracle, lam, rng)
        if len(B_new) != 256:
            continue
        s_new = score_board(B_new, pieces)
        h_new = hamming_to_oracle(B_new, oracle)
        # Accept based on combined objective
        f_old = B_score - lam * B_ham
        f_new = s_new - lam * h_new
        T = 1.0
        delta = f_new - f_old
        if delta > 0 or rng.random() < pow(2.718281828, delta / T):
            B = B_new
            B_score = s_new
            B_ham = h_new
            if s_new > best_score:
                best_score = s_new
            if h_new < best_ham:
                best_ham = h_new
        if t % 20 == 0:
            print(f"  iter {t}: score={B_score}, ham={B_ham}, lam={lam:.2f}, "
                  f"best_sc={best_score}, best_ham={best_ham}")
        history.append((t, B_score, B_ham, lam))

    print(f"\nFinal: score={B_score}, ham={B_ham}")
    print(f"Best score: {best_score}, min ham: {best_ham}")
    return best_score, best_ham


if __name__ == "__main__":
    main()
