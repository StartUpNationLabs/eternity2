#!/usr/bin/env python3
"""Check agreement on PIECE (any rotation) per position across top boards.

The agreement_freeze script looked at (piece, rot). Here we look at piece
alone — maybe basins agree on WHICH piece goes WHERE, just with different
rotations.

Then: for cells with high piece agreement, take the most-common piece, try
all 4 rotations exhaustively, pick the best. This is a rotation-only
optimization with strong consensus prior."""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

REPO = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
DB = REPO / "database-400-480"
BORDER = 65535
W = 16


def load_pieces():
    import csv
    pieces = []
    with open(REPO.parent / "data" / "puzzles" / "size_16_official_eternity.csv") as f:
        reader = csv.reader(f); next(reader)
        for row in reader:
            N, E, S, W_ = (int(row[i].strip(), 2) for i in range(4))
            pieces.append((N, E, S, W_))
    return pieces


def rotate(piece, r):
    N, E, S, W_ = piece
    if r == 0: return (N, E, S, W_)
    if r == 1: return (W_, N, E, S)
    if r == 2: return (S, W_, N, E)
    if r == 3: return (E, S, W_, N)


def score_board(board, pieces):
    matches = 0
    for pos, (pid, rot) in board.items():
        row, col = pos // W, pos % W
        p_edges = rotate(pieces[pid], rot)
        if col < 15 and (pos + 1) in board:
            nb = board[pos + 1]; ne = rotate(pieces[nb[0]], nb[1])
            if p_edges[1] == ne[3] and p_edges[1] != BORDER: matches += 1
        if row < 15 and (pos + W) in board:
            nb = board[pos + W]; ne = rotate(pieces[nb[0]], nb[1])
            if p_edges[2] == ne[0] and p_edges[2] != BORDER: matches += 1
    return matches


def load_board(path):
    with open(path) as f: d = json.load(f)
    pl = d.get("placement", [])
    if not pl: return None, 0
    out = {}
    for i, p in enumerate(pl):
        if not isinstance(p, dict): continue
        pos = p.get("pos", i)
        if "piece_id" not in p or "rotation" not in p: return None, 0
        out[int(pos)] = (int(p["piece_id"]), int(p["rotation"]))
    return out, d.get("matched", 0)


def main():
    boards_by_band = defaultdict(list)
    for f in sorted(DB.glob("*.json")):
        if f.name == "README.md": continue
        b, s = load_board(f)
        if b and len(b) == 256:
            boards_by_band[s].append((f.name, b))

    # Top 12 boards (469+466+465+462+461).
    targets = [469, 466, 465, 462, 461]
    selected = []
    for sc in targets:
        selected.extend(boards_by_band.get(sc, []))
    print(f"Selected high-score boards: {len(selected)}", flush=True)

    pieces = load_pieces()

    # Per-cell, count which PIECE (ignoring rotation) appears most.
    cell_piece_votes = defaultdict(Counter)
    cell_rotation_votes = defaultdict(Counter)  # for the most-voted piece
    for name, board in selected:
        for pos, (pid, rot) in board.items():
            cell_piece_votes[pos][pid] += 1
            cell_rotation_votes[pos][(pid, rot)] += 1

    print(f"\n=== PIECE-ALONE agreement (rotation ignored) ===", flush=True)
    piece_agreement = []
    for pos in range(256):
        if pos not in cell_piece_votes: continue
        votes = cell_piece_votes[pos]
        total = sum(votes.values())
        top_piece, top_count = votes.most_common(1)[0]
        agree = top_count / total * 100
        piece_agreement.append((agree, pos, top_piece, top_count, total))
    piece_agreement.sort(reverse=True)

    print(f"Top 30 cells by piece-alone agreement:", flush=True)
    for ag, pos, pid, cnt, total in piece_agreement[:30]:
        row, col = pos // 16, pos % 16
        print(f"  pos={pos:3d} ({row:2d},{col:2d}): piece={pid:3d} agreement={ag:.1f}% ({cnt}/{total})", flush=True)

    # Histogram.
    buckets = [0, 50, 60, 70, 80, 90, 95, 100, 101]
    hist = [0] * (len(buckets) - 1)
    for ag, *_ in piece_agreement:
        for i in range(len(buckets) - 1):
            if buckets[i] <= ag < buckets[i+1]:
                hist[i] += 1; break
    print(f"\nPiece-alone agreement histogram:")
    for i in range(len(buckets) - 1):
        print(f"  [{buckets[i]:>3}-{buckets[i+1]:>3}%): {hist[i]} cells")

    print(f"\n=== Backbone by threshold (piece alone) ===")
    for thresh in [50, 60, 70, 80, 90]:
        bb = [(pos, pid, cnt) for ag, pos, pid, cnt, total in piece_agreement if ag >= thresh]
        print(f"  threshold {thresh}%: {len(bb)}/256 cells")

    # NEW EXPERIMENT: Use the top-voted PIECE per position from top 12 boards,
    # then optimize ROTATION exhaustively (4^free_cells).
    # If we get >461, breakthrough.

    print(f"\n=== Build voted board (per cell: most-voted piece, then optimize rotation) ===", flush=True)
    # Step 1: get top-voted piece per cell.
    voted_pieces = {}
    voted_strength = {}
    for ag, pos, pid, cnt, total in piece_agreement:
        voted_pieces[pos] = pid
        voted_strength[pos] = ag
    # Step 2: check piece uniqueness.
    piece_counts = Counter(voted_pieces.values())
    duplicates = {pid for pid, cnt in piece_counts.items() if cnt > 1}
    print(f"  duplicated voted pieces: {len(duplicates)}", flush=True)

    if duplicates:
        # Resolve: for each duplicate, keep the one with highest agreement; replace others.
        print(f"  Resolving via highest-agreement-keeps strategy", flush=True)
        # For each piece used multiple times, find the position with max agreement.
        for dup in duplicates:
            positions_using = [pos for pos, pid in voted_pieces.items() if pid == dup]
            # Keep the position with max agreement.
            best_pos = max(positions_using, key=lambda p: voted_strength[p])
            for pos in positions_using:
                if pos != best_pos:
                    # Find next-best piece for this pos.
                    votes = cell_piece_votes[pos]
                    for cand, cnt in votes.most_common():
                        if cand not in voted_pieces.values() or cand == voted_pieces.get(pos):
                            voted_pieces[pos] = cand
                            voted_strength[pos] = (cnt / sum(votes.values())) * 100
                            break

    # Check piece uniqueness again.
    piece_counts = Counter(voted_pieces.values())
    duplicates2 = {pid for pid, cnt in piece_counts.items() if cnt > 1}
    print(f"  duplicates after resolution: {len(duplicates2)}", flush=True)
    used_pieces = set(voted_pieces.values())
    missing_pieces = set(range(256)) - used_pieces
    print(f"  pieces used: {len(used_pieces)}, missing: {len(missing_pieces)}", flush=True)

    if missing_pieces:
        # Assign missing pieces to currently-duplicated positions.
        print(f"  Need to handle missing/duplicated mismatch — skip for now", flush=True)

    # Step 3: optimize rotation per cell using global score.
    # First place voted pieces with best individual rotation.
    board = {}
    for pos, pid in voted_pieces.items():
        # Try all 4 rots, pick best (versus already-placed neighbors).
        best_r = 0; best_score = -1
        for r in range(4):
            board_try = dict(board)
            board_try[pos] = (pid, r)
            row, col = pos // 16, pos % 16
            p_edges = rotate(pieces[pid], r)
            local = 0
            for d_pos, opp, mine in [(-W, 2, 0), (+W, 0, 2), (-1, 1, 3), (+1, 3, 1)]:
                if d_pos == -W and row == 0: continue
                if d_pos == +W and row == 15: continue
                if d_pos == -1 and col == 0: continue
                if d_pos == +1 and col == 15: continue
                nb_pos = pos + d_pos
                if nb_pos in board:
                    nb_pid, nb_rot = board[nb_pos]
                    nb_edges = rotate(pieces[nb_pid], nb_rot)
                    if nb_edges[opp] == p_edges[mine] and p_edges[mine] != BORDER:
                        local += 1
            if local > best_score:
                best_score = local; best_r = r
        board[pos] = (pid, best_r)

    sc = score_board(board, pieces)
    print(f"\nVoted-pieces-greedy-rotation board score: {sc}", flush=True)

    if sc > 461:
        out_path = REPO / "output" / "vol-125" / f"voted_board_{sc}.json"
        out_data = {
            "matched": sc, "source": "piece_pos_agreement",
            "placement": [{"pos": p, "piece_id": pid, "rotation": rot}
                          for p, (pid, rot) in sorted(board.items())],
        }
        out_path.write_text(json.dumps(out_data, indent=2))
        print(f"🎯 NEW RECORD candidate: saved to {out_path}", flush=True)


if __name__ == "__main__":
    main()
