#!/usr/bin/env python3
# R5d — direct oracle swap experiment.
#
# Take a 447 board. For every piece that's at the WRONG position
# relative to a 456 oracle, swap it with the piece currently at the
# oracle's destination. Rotate to match. Score the result.
#
# This is a single-pass synchronous swap. It's NOT a search; it's
# testing whether the swap PATH is viable at all.

import sys, json
from pathlib import Path
sys.path.insert(0, "scripts")
import importlib.util
spec = importlib.util.spec_from_file_location("r5", "scripts/r5_mismatch_homology.py")
r5 = importlib.util.module_from_spec(spec); spec.loader.exec_module(r5)

V2 = Path(".").resolve()
size, pieces = r5.load_puzzle(r5.PUZZLE_CSV)

def load(path):
    return r5.load_placement(Path(path).resolve(), size)[0]

def score(board):
    return r5.score_and_classify_edges(board, size, pieces)[0]

def piece_to_pos_rot(board):
    out = {}
    for pos, e in enumerate(board):
        if e is None: continue
        pid, rot = e
        out[pid] = (pos, rot)
    return out

def main():
    if len(sys.argv) < 3:
        sys.exit("usage: r5d_oracle_swap.py <current_board.json> <oracle_board.json>")
    cur = load(sys.argv[1])
    oracle = load(sys.argv[2])
    s_cur = score(cur)
    s_oracle = score(oracle)
    print(f"current board: {s_cur}/480")
    print(f"oracle  board: {s_oracle}/480")
    cur_p2 = piece_to_pos_rot(cur)
    ora_p2 = piece_to_pos_rot(oracle)

    # Strategy 1: full snap. Apply oracle's (pos, rot) for EVERY piece.
    # Since the multiset is preserved (same 256 pieces), this is just =
    # oracle. So the score after = oracle's score. Sanity check.
    snapped = [None] * (size * size)
    for pid, (pos, rot) in ora_p2.items():
        snapped[pos] = (pid, rot)
    s_snap = score(snapped)
    print(f"full-snap to oracle: {s_snap}/480  (sanity: should equal oracle = {s_oracle})")

    # Strategy 2: partial snap. Sort pieces by how "misplaced" they are
    # (Manhattan distance between current pos and oracle pos). Apply
    # the worst-K swaps. This tests: does the score interpolate
    # monotonically from cur to oracle as we apply more swaps?
    dists = []
    for pid in range(256):
        cp, _ = cur_p2[pid]
        op, _ = ora_p2[pid]
        cx, cy = cp % size, cp // size
        ox, oy = op % size, op // size
        d = abs(cx-ox) + abs(cy-oy)
        if d > 0:
            dists.append((d, pid))
    dists.sort(reverse=True)
    print(f"# pieces misplaced: {len(dists)}")
    if dists:
        print(f"# max manhattan: {dists[0][0]}, mean: {sum(d for d,_ in dists)/len(dists):.1f}")

    # Apply swaps incrementally.
    print()
    print("k_swaps | score (cur board after applying k swaps with rotation)")
    work = [row[:] for row in [[None]*size for _ in range(size)]]
    work_flat = list(cur)
    # We need to think carefully: swapping means EXCHANGING two pieces. We
    # can't just "place" piece P at the oracle's pos because that pos is
    # currently occupied by some other piece Q. We need to find piece Q's
    # oracle target and place Q there next.
    # Simpler: for each step, pick the most-misplaced piece P, swap it with
    # whatever piece currently sits at P's oracle target. Apply oracle's
    # rotation to P. Repeat.
    # Better algorithm: in a single pass, for each piece in oracle-position
    # order (top to bottom), place it at its oracle pos with oracle rot;
    # the piece formerly there goes to the freed slot.
    work_flat = list(cur)
    snap_counts = [5, 10, 20, 40, 60, 80, 120, 160, 200, 240]
    swaps_done = 0
    next_snap = 0
    scores_at = []
    for target_pos in range(size * size):
        oentry = oracle[target_pos]
        if oentry is None:
            continue
        target_pid, target_rot = oentry
        # find piece target_pid in current work
        cur_pos = None
        for pos, e in enumerate(work_flat):
            if e is not None and e[0] == target_pid:
                cur_pos = pos; break
        if cur_pos is None or cur_pos == target_pos:
            continue
        other = work_flat[target_pos]
        work_flat[target_pos] = (target_pid, target_rot)
        work_flat[cur_pos] = other
        swaps_done += 1
        if next_snap < len(snap_counts) and swaps_done >= snap_counts[next_snap]:
            s = score(work_flat)
            scores_at.append((snap_counts[next_snap], s))
            print(f"  {snap_counts[next_snap]:>3} | {s}/480")
            next_snap += 1
    s_final = score(work_flat)
    print(f"  ALL ({swaps_done} swaps) | {s_final}/480")

    # Now apply a more LOCALIZED variant: only swap pieces whose oracle
    # target is within k=8 cells of their current position.
    print()
    print("## Localized swap (only swap if oracle-target within 8 manhattan cells)")
    work_local = list(cur)
    sw = 0
    for target_pos in range(size * size):
        oentry = oracle[target_pos]
        if oentry is None: continue
        target_pid, target_rot = oentry
        cur_pos = None
        for pos, e in enumerate(work_local):
            if e is not None and e[0] == target_pid:
                cur_pos = pos; break
        if cur_pos is None or cur_pos == target_pos:
            continue
        cx, cy = cur_pos % size, cur_pos // size
        tx, ty = target_pos % size, target_pos // size
        d = abs(cx-tx) + abs(cy-ty)
        if d > 8:
            continue
        other = work_local[target_pos]
        work_local[target_pos] = (target_pid, target_rot)
        work_local[cur_pos] = other
        sw += 1
    s_local = score(work_local)
    print(f"  {sw} local swaps, score = {s_local}/480")

if __name__ == "__main__":
    main()
