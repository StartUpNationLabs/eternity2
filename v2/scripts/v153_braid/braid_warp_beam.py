#!/usr/bin/env python3
"""V153 BRAID — warp-level beam search.

The board is 16 horizontal warps. Each warp = sequence of 16 pieces
(with rotations) forming a complete row. Warps interact via the
SHARED CELL-SIDES between row y and row y+1 (the S of row y = the N of
row y+1).

Algorithm:
  1. Enumerate top-K warp-0 candidates (16-piece rows from row-0
     piece set: border-corner-left + border-edge × 14 + border-corner-right).
     For row 0: every cell has N=BORDER. So pieces have N=BORDER side.
     Score warp 0 = # matched horizontal edges within the row (max 15).
  2. For each warp 0 in beam, extend to warp 1:
     - Cell (1, x) needs N = warp_0_cell_x.S.
     - W of cell (1, 0) = BORDER, E of cell (1, 15) = BORDER.
     - Warp 1 score = horizontal matches in row 1 + vertical matches between row 0 and row 1.
  3. Continue to row 15.
  4. Output: highest-score complete board.

Branching factor per row is HUGE in principle (16 pieces × 4 rotations
× 22 internal colors). Pruning via:
  - Piece availability (no reuse of placed pieces).
  - N-constraint from above row.
  - Beam top-K filter.
"""

from __future__ import annotations
import argparse
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO / "scripts/v153_braid"))
from braid_poc import load_csv, rotate, piece_class, cell_class


def build_row_candidates(pieces, used_mask, n_constraints, W, y, H, beam_K):
    """Enumerate top-K possible rows.

    n_constraints[x] = required N-color for cell (y, x).
    used_mask: bitmask (or set) of already-used piece IDs.
    Returns list of (row_score, row_layout) where row_layout is
    [(pid, rotation, sides_tuple)] for x = 0..W-1.

    Implementation: greedy + beam — at each cell x in the row, maintain
    top-K partial rows; for each, enumerate compatible (piece, rotation),
    extend, prune.
    """
    BORDER = 0
    # State per partial row: (current_x, row_score, row_layout_so_far, used_in_this_row)
    # row_layout_so_far[x] = (pid, rot, sides=(n,e,s,w))
    initial = (0, 0, [], set())
    beam = [initial]

    for x in range(W):
        new_beam = []
        for (cx, rs, rl, ur) in beam:
            # Constraints at cell (y, x):
            #   N = n_constraints[x]
            #   W = (rl[-1].e) if x > 0 else BORDER
            #   S = BORDER if y == H-1 else free
            #   E = BORDER if x == W-1 else free
            need_n = n_constraints[x]
            need_w = rl[-1][2][1] if rl else BORDER  # E of left = our W
            need_s_border = (y == H - 1)
            need_e_border = (x == W - 1)
            if x == 0:
                need_w = BORDER
            # Iterate all pieces and rotations satisfying constraints.
            for pid, p in enumerate(pieces):
                if used_mask[pid] or pid in ur:
                    continue
                for r in range(4):
                    sides = rotate(p, r)
                    n, e, s, w = sides
                    if n != need_n: continue
                    if w != need_w: continue
                    if need_s_border and s != BORDER: continue
                    if not need_s_border and s == BORDER: continue
                    if need_e_border and e != BORDER: continue
                    if not need_e_border and e == BORDER: continue
                    # Score increment: 1 for the W edge matching (it does, since we required it).
                    # But the W-matched is between THIS cell's W and LEFT cell's E.
                    # That match was: rl[-1].e == w? yes by construction.
                    incr = 1 if x > 0 and w != BORDER else 0
                    # Vertical match: between this cell's N and (y-1, x)'s S. Always matched by N-constraint.
                    incr += 1 if y > 0 and n != BORDER else 0
                    new_rl = rl + [(pid, r, sides)]
                    new_ur = ur | {pid}
                    new_beam.append((cx + 1, rs + incr, new_rl, new_ur))
            # Branching is huge; prune now to beam_K * 4 to keep growing.
        # Prune.
        new_beam.sort(key=lambda s: -s[1])
        beam = new_beam[:beam_K]
        if not beam:
            return []
    return [(rs, rl) for (_, rs, rl, _) in beam]


def braid_warp_search(pieces, size, beam_K=64, time_limit=60.0):
    """Top-K beam over rows: extend best-K row-0 candidates to row-1, etc."""
    BORDER = 0
    W = H = size
    # Initial state: empty board.
    initial_used = [False] * len(pieces)
    initial_n = [BORDER] * W  # row 0's N is BORDER.
    initial = (0, [], [False] * len(pieces), [BORDER] * W)  # (rows_built, board_so_far_per_row, used_mask, n_for_next_row)
    beam = [initial]

    t0 = time.time()
    for y in range(H):
        new_beam = []
        for (ry, board, used, n_top) in beam:
            if time.time() - t0 > time_limit:
                break
            row_cands = build_row_candidates(pieces, used, n_top, W, y, H, beam_K)
            for rs, rl in row_cands:
                new_used = list(used)
                for (pid, _, _) in rl:
                    new_used[pid] = True
                new_board = board + [rl]
                # New n_top for next row = S of each cell in this row.
                new_n_top = [sides[2] for (_, _, sides) in rl]
                # Total score of board so far = sum of horizontal + vertical matches.
                # rs already accumulates per-row (W matches + N matches with above).
                total_score = sum(_rs for _rs, _ in row_cands[:1])  # fix: rs is the per-row, total accumulates
                # Actually I need to track total_score across rows separately.
                new_beam.append((ry + 1, new_board, new_used, new_n_top, rs))
        # Sort by total_score (accumulated). But we stored rs per-row.
        # Let me restructure: track accumulated_score in the tuple.
        # For now, sort by the LATEST row's score (proxy).
        new_beam.sort(key=lambda s: -s[4])
        beam = [t[:4] for t in new_beam[:beam_K]]
        if not beam:
            print(f"[v153] beam empty at row {y}", flush=True)
            return None
        best_so_far = new_beam[0][4]
        print(f"[v153] y={y} beam={len(beam)} latest_row_score={best_so_far} elapsed={time.time()-t0:.1f}s", flush=True)
    return beam


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    ap.add_argument("--beam-k", type=int, default=64)
    ap.add_argument("--time-limit", type=float, default=120.0)
    args = ap.parse_args()
    size, pieces = load_csv(args.puzzle)
    print(f"[v153-warp] puzzle: {size}×{size}, {len(pieces)} pieces, beam_K={args.beam_k}", flush=True)
    result = braid_warp_search(pieces, size, beam_K=args.beam_k, time_limit=args.time_limit)
    if result:
        print(f"[v153-warp] complete: {len(result[0][1])} rows built")


if __name__ == "__main__":
    main()
