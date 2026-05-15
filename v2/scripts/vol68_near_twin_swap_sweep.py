#!/usr/bin/env python3
"""Vol-68 — Near-twin swap sweep on McGavin's 469.

For each of the 114 near-twin piece-pairs (from vol-65 piece-orbit
analysis), find where each piece sits in McGavin's 469. If both
pieces of the pair sit in the board, swap them. Re-score.

If the swap gives ≥469, save as a new 469-level board.
If it gives 470+, record break.
"""

import collections
import csv
import json
import sys
from pathlib import Path

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"


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


def canonical_rep(edges):
    return min(rotate(edges, k) for k in range(4))


def find_near_twin_pairs(pieces):
    """Find pairs of pieces sharing 3 of 4 edges in canonical rotation."""
    # canonical_rep[i] gives the lex-smallest rotation of piece i's edges
    canon_reps = [canonical_rep(p) for p in pieces]
    # For each piece's canonical-rep, take 3-of-4 subsets and group by them
    near_groups = collections.defaultdict(list)
    for i, rep in enumerate(canon_reps):
        # 3-of-4 subsets: omit one position
        for omit in range(4):
            key = tuple(c for j, c in enumerate(rep) if j != omit)
            near_groups[(omit, key)].append(i)
    pairs = []
    for (omit, key), members in near_groups.items():
        if len(members) < 2: continue
        for i in range(len(members)):
            for j in range(i+1, len(members)):
                pairs.append((members[i], members[j]))
    # Dedup
    return list(set(tuple(sorted(p)) for p in pairs))


def load_placement(path):
    with open(path) as f: d = json.load(f)
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


def best_rotation(pid, pos, placement, pieces):
    """Pick rotation maximizing matches."""
    W = 16
    r_, c_ = divmod(pos, W)
    nbr = {}
    if r_ > 0 and (r_ - 1) * W + c_ in placement:
        np_, nr = placement[(r_ - 1) * W + c_]
        nbr['N'] = rotate(pieces[np_], nr)[2]
    if r_ < 15 and (r_ + 1) * W + c_ in placement:
        np_, nr = placement[(r_ + 1) * W + c_]
        nbr['S'] = rotate(pieces[np_], nr)[0]
    if c_ > 0 and r_ * W + (c_ - 1) in placement:
        np_, nr = placement[r_ * W + (c_ - 1)]
        nbr['W'] = rotate(pieces[np_], nr)[1]
    if c_ < 15 and r_ * W + (c_ + 1) in placement:
        np_, nr = placement[r_ * W + (c_ + 1)]
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


def main():
    pieces = load_pieces()
    near_twin_pairs = find_near_twin_pairs(pieces)
    print(f"Near-twin pairs (3-of-4 edges shared canonical): {len(near_twin_pairs)}")

    mcg = load_placement("output/vol-65/mcgavin_469.json")
    base_score = score_board(mcg, pieces)
    print(f"McGavin baseline: {base_score}")
    print()

    # For each pair, find both pieces' positions in McGavin
    pid_to_pos = {pid: pos for pos, (pid, _) in mcg.items()}

    results = []
    for (p1, p2) in near_twin_pairs:
        if p1 not in pid_to_pos or p2 not in pid_to_pos:
            continue
        pos1 = pid_to_pos[p1]
        pos2 = pid_to_pos[p2]
        # Swap: put p2 at pos1, p1 at pos2
        # Use best rotation for each (given current neighbors)
        new = dict(mcg)
        # Remove old pieces
        del new[pos1]
        del new[pos2]
        # Place p2 at pos1 with best rotation
        rot1 = best_rotation(p2, pos1, new, pieces)
        rot2 = best_rotation(p1, pos2, new, pieces)
        new[pos1] = (p2, rot1)
        new[pos2] = (p1, rot2)
        # Score
        sc = score_board(new, pieces)
        results.append((p1, p2, pos1, pos2, sc))
        if sc >= 469:
            r1_x, r1_y = pos1 % 16, pos1 // 16
            r2_x, r2_y = pos2 % 16, pos2 // 16
            print(f"** ({p1}, {p2}): {sc}  at pos {pos1} ({r1_x},{r1_y}) ↔ pos {pos2} ({r2_x},{r2_y})")

    print()
    print(f"Total swap candidates tested: {len(results)}")
    scores_dist = collections.Counter(r[4] for r in results)
    print(f"Score distribution:")
    for sc in sorted(scores_dist.keys(), reverse=True)[:15]:
        print(f"  {sc}: {scores_dist[sc]}")

    # Find any 470+
    records = [r for r in results if r[4] >= 470]
    if records:
        print(f"\n!!! POTENTIAL RECORD BREAKS (>= 470):")
        for p1, p2, pos1, pos2, sc in records:
            print(f"  pieces ({p1}, {p2}) swap at pos ({pos1}, {pos2}): score {sc}")


if __name__ == "__main__":
    main()
