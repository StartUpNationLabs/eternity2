#!/usr/bin/env python3
"""Vol-119 — mismatch-directed basin swap (INVENTION: CORPUS-VOTE-SWAP).

Algorithm:
1. Take board A (a 459 record).
2. Identify mismatch edges in A.
3. For each mismatch edge (c1, c2), the cells c1 and/or c2 are the "weak"
   cells. Look at the disagreement map: what (piece, rot) options does
   the CORPUS suggest for these cells?
4. Try replacing A's (pid_a, rot_a) at c1 with each corpus alternative
   (pid_b, rot_b). For each alternative:
   - Ensure piece-uniqueness (the piece must not already be elsewhere
     in A unless we also remove it).
   - Compute Δ in matched edges.
   - If Δ > 0, ACCEPT and update A.
5. Iterate until no improvement.

This is a CORPUS-VOTE first-improvement local search. Distinct from
ALNS because:
- ALNS proposes random (or heuristic) destroy regions, then re-fills
  via CP/Hungarian.
- Corpus-vote-swap proposes EXACT alternative placements from the
  observed basin variations, no re-fill.

If the corpus has ENOUGH diversity that some basin's choice at cell c
matches A's neighbors better than A's own choice, we can gain.

Limit: only local swaps (single cell), so equivalent to MIP at degree 1.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


W, H = 16, 16


def parse_color(s):
    s = s.strip()
    v = int(s, 2)
    if v == 65535:
        return 0
    return v


def load_puzzle(csv_path):
    pieces = {}
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) < 4:
            continue
        try:
            t = parse_color(cols[0])
            r = parse_color(cols[1])
            b = parse_color(cols[2])
            l = parse_color(cols[3])
        except ValueError:
            continue
        pieces[pid] = (t, r, b, l)
        pid += 1
    return pieces


def rotate_edges(edges, rot):
    t, r, b, l = edges
    if rot == 0:
        return (t, r, b, l)
    elif rot == 1:
        return (l, t, r, b)
    elif rot == 2:
        return (b, l, t, r)
    else:
        return (r, b, l, t)


def load_board(p):
    with open(p) as f:
        d = json.load(f)
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    out = {}
    for idx, item in enumerate(arr):
        if item is None:
            continue
        pos = int(item.get("pos", idx))
        out[pos] = (int(item["piece_id"]), int(item["rotation"]))
    return out


def save_board(board, path, score, source="vol119_mismatch_directed_swap"):
    placement = []
    for pos in sorted(board):
        pid, rot = board[pos]
        placement.append({"pos": pos, "piece_id": pid, "rotation": rot})
    doc = {
        "placement": placement,
        "metadata": {"source": source, "score": score},
    }
    with open(path, "w") as f:
        json.dump(doc, f, indent=2)


def matched_edges(board, pieces):
    matched = 0
    for pos, (pid, rot) in board.items():
        x, y = pos % W, pos // W
        e = rotate_edges(pieces[pid], rot)
        if x < W - 1 and (pos + 1) in board:
            npid, nrot = board[pos + 1]
            ne = rotate_edges(pieces[npid], nrot)
            if e[1] == ne[3] and not (e[1] == 0 and ne[3] == 0):
                matched += 1
        if y < H - 1 and (pos + W) in board:
            npid, nrot = board[pos + W]
            ne = rotate_edges(pieces[npid], nrot)
            if e[2] == ne[0] and not (e[2] == 0 and ne[0] == 0):
                matched += 1
    return matched


def cell_matched_edges(board, pieces, pos):
    """Return the number of edges around `pos` that match (0..4)."""
    if pos not in board:
        return 0
    pid, rot = board[pos]
    x, y = pos % W, pos // W
    e = rotate_edges(pieces[pid], rot)
    cnt = 0
    # right
    if x < W - 1 and (pos + 1) in board:
        npid, nrot = board[pos + 1]
        ne = rotate_edges(pieces[npid], nrot)
        if e[1] == ne[3] and not (e[1] == 0 and ne[3] == 0):
            cnt += 1
    # left
    if x > 0 and (pos - 1) in board:
        npid, nrot = board[pos - 1]
        ne = rotate_edges(pieces[npid], nrot)
        if e[3] == ne[1] and not (e[3] == 0 and ne[1] == 0):
            cnt += 1
    # bottom
    if y < H - 1 and (pos + W) in board:
        npid, nrot = board[pos + W]
        ne = rotate_edges(pieces[npid], nrot)
        if e[2] == ne[0] and not (e[2] == 0 and ne[0] == 0):
            cnt += 1
    # top
    if y > 0 and (pos - W) in board:
        npid, nrot = board[pos - W]
        ne = rotate_edges(pieces[npid], nrot)
        if e[0] == ne[2] and not (e[0] == 0 and ne[2] == 0):
            cnt += 1
    return cnt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="board to improve (single 459 basin)")
    ap.add_argument("corpus", nargs="+", help="other basin boards (source of swap candidates)")
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-iters", type=int, default=10)
    ap.add_argument("--allow-piece-swap", action="store_true",
                    help="if set, also swap the displaced piece in")
    args = ap.parse_args()

    pieces = load_puzzle(Path(args.puzzle))
    A = load_board(Path(args.target))
    print(f"# loaded target: {len(A)} placements", file=sys.stderr)
    score = matched_edges(A, pieces)
    print(f"# target score: {score}/480")

    # Build disagreement map from corpus
    cell_options = defaultdict(set)  # pos -> {(pid, rot)}
    for p in args.corpus:
        b = load_board(Path(p))
        for pos, (pid, rot) in b.items():
            cell_options[pos].add((pid, rot))
    # Add target's own placements
    for pos, (pid, rot) in A.items():
        cell_options[pos].add((pid, rot))

    print(f"# corpus disagreement: 256 cells, mean options = "
          f"{sum(len(s) for s in cell_options.values())/256:.1f}", file=sys.stderr)

    # Iteratively find single-cell swaps that improve score.
    iters = 0
    total_lift = 0
    while iters < args.max_iters:
        iters += 1
        # Rank cells by their CURRENT matched-edge count, lowest first.
        cell_scores = [(cell_matched_edges(A, pieces, pos), pos) for pos in A]
        cell_scores.sort()  # ascending → weakest first
        improved = False
        for cur_matched, pos in cell_scores:
            if cur_matched == 4:
                continue  # already perfect
            current = A[pos]
            current_pid_set = {pid for (pid, _) in A.values()}
            options = cell_options[pos] - {current}
            best_alt = None
            best_delta = 0
            for alt_pid, alt_rot in options:
                # Piece-uniqueness check
                if alt_pid in current_pid_set:
                    if not args.allow_piece_swap:
                        continue
                    # find the current cell of alt_pid in A
                    other_pos = None
                    for p, (pp, _) in A.items():
                        if pp == alt_pid:
                            other_pos = p
                            break
                    if other_pos is None or other_pos == pos:
                        continue
                    # Two-cell swap
                    old_a_score = (cell_matched_edges(A, pieces, pos) +
                                   cell_matched_edges(A, pieces, other_pos))
                    saved = A[pos], A[other_pos]
                    # apply swap: move alt to pos, move current_pid to other_pos
                    # alt is (alt_pid, alt_rot); current is (current_pid, current_rot)
                    A[pos] = (alt_pid, alt_rot)
                    # for other_pos, we need to PICK a rotation for current_pid
                    # try all 4 rotations and pick best
                    cur_pid, cur_rot = current
                    best_other_rot = cur_rot
                    best_pair = -1
                    for rot_try in range(4):
                        A[other_pos] = (cur_pid, rot_try)
                        score_pair = (cell_matched_edges(A, pieces, pos) +
                                      cell_matched_edges(A, pieces, other_pos))
                        if score_pair > best_pair:
                            best_pair = score_pair
                            best_other_rot = rot_try
                    A[other_pos] = (cur_pid, best_other_rot)
                    new_pair = (cell_matched_edges(A, pieces, pos) +
                                cell_matched_edges(A, pieces, other_pos))
                    delta = new_pair - old_a_score
                    if delta > best_delta:
                        best_delta = delta
                        best_alt = ((alt_pid, alt_rot), (other_pos, (cur_pid, best_other_rot)))
                    # revert
                    A[pos], A[other_pos] = saved
                else:
                    # Single-cell swap: try replacing pos with alt
                    saved = A[pos]
                    A[pos] = (alt_pid, alt_rot)
                    new_matched = cell_matched_edges(A, pieces, pos)
                    delta = new_matched - cur_matched
                    if delta > best_delta:
                        best_delta = delta
                        best_alt = ((alt_pid, alt_rot), None)
                    A[pos] = saved
            if best_alt and best_delta > 0:
                # apply
                A[pos] = best_alt[0]
                if best_alt[1]:
                    other_pos, other_val = best_alt[1]
                    A[other_pos] = other_val
                score += best_delta
                total_lift += best_delta
                improved = True
                print(f"  iter={iters}  pos={pos}  Δ={best_delta:+d}  "
                      f"new_score={score}/480  swap={'2-cell' if best_alt[1] else '1-cell'}")
                break  # restart from beginning
        if not improved:
            print(f"  iter={iters}  no improvement found; STOP")
            break

    final_score = matched_edges(A, pieces)
    print(f"# final score: {final_score}/480 (lift Δ={total_lift})")

    if args.out:
        save_board(A, args.out, final_score)
        print(f"# wrote: {args.out}")


if __name__ == "__main__":
    main()
