#!/usr/bin/env python3
"""V184 LIGHTHOUSE v2 — full bidirectional row-build with meeting.

Top-down: rows 0..M-1 (constrained by N from row above).
Bottom-up: rows 15..M  (constrained by S from row below).
Meeting: at row M-1/M interface, top's S must match bottom's N.

Then merge: a top-half state × bottom-half state pair must have:
  - disjoint pieces (no overlap)
  - S of top[M-1] == N of bottom[M] per column

For each compatible pair, score the joint board.
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BORDER = '1111111111111111'


def load_pieces():
    csv = REPO.parent / 'data' / 'puzzles' / 'size_16_official_eternity.csv'
    pieces = {}
    for pid, line in enumerate(csv.read_text().splitlines()[1:]):
        parts = line.split(',')
        if len(parts) < 4: continue
        for r in range(4):
            edges = [parts[(i - r) % 4] for i in range(4)]
            pieces[(pid, r)] = tuple(edges)
    return pieces


def is_border(s):
    return s == BORDER


def cell_class(pos, size=16):
    r, c = pos // size, pos % size
    on_h = r == 0 or r == size - 1
    on_v = c == 0 or c == size - 1
    if on_h and on_v: return 'corner'
    if on_h or on_v: return 'edge'
    return 'interior'


def piece_class(edges):
    n_border = sum(1 for e in edges if is_border(e))
    if n_border == 2: return 'corner'
    if n_border == 1: return 'edge'
    return 'interior'


def candidates_for_cell(pos, pieces, used_pids, size=16):
    r, c = pos // size, pos % size
    cls = cell_class(pos)
    need = [r == 0, c == size - 1, r == size - 1, c == 0]
    out = []
    for (pid, rot), edges in pieces.items():
        if pid in used_pids: continue
        if piece_class(edges) != cls: continue
        ok = True
        for i in range(4):
            if need[i]:
                if not is_border(edges[i]): ok = False; break
            else:
                if is_border(edges[i]): ok = False; break
        if ok:
            out.append((pid, rot, edges))
    return out


def solve_row_topk(row_idx, n_constraint, pieces, used_pids, top_k=8, beam_k=300, size=16):
    """Chain-DP keyed on N-constraint."""
    cand_per_cell = []
    for c in range(size):
        pos = row_idx * size + c
        cs = candidates_for_cell(pos, pieces, used_pids)
        match = [(pid, rot, edges) for (pid, rot, edges) in cs if edges[0] == n_constraint[c]]
        cand_per_cell.append(match)
        if not match:
            return []

    init = []
    for (pid, rot, edges) in cand_per_cell[0]:
        init.append(([(pid, rot, edges)], frozenset([pid]), 0))
    if not init: return []
    states = [init]
    for c in range(1, size):
        new_states = []
        for chain, used_row, score in states[-1]:
            cur_edges = chain[-1][2]
            for next_pid, next_rot, next_edges in cand_per_cell[c]:
                if next_pid in used_row: continue
                if cur_edges[1] != next_edges[3]: continue
                ew_match = 0 if is_border(cur_edges[1]) else 1
                new_chain = chain + [(next_pid, next_rot, next_edges)]
                new_states.append((new_chain, used_row | {next_pid}, score + ew_match))
        if not new_states: return []
        new_states.sort(key=lambda x: -x[2])
        new_states = new_states[:beam_k]
        states.append(new_states)
    states[-1].sort(key=lambda x: -x[2])
    return [(chain, used_row) for chain, used_row, _ in states[-1][:top_k]]


def solve_row_topk_by_s(row_idx, s_constraint, pieces, used_pids, top_k=8, beam_k=300, size=16):
    """Chain-DP keyed on S-constraint. Same as solve_row_topk but matches
    edges[2] (S) instead of edges[0] (N) per cell."""
    cand_per_cell = []
    for c in range(size):
        pos = row_idx * size + c
        cs = candidates_for_cell(pos, pieces, used_pids)
        match = [(pid, rot, edges) for (pid, rot, edges) in cs if edges[2] == s_constraint[c]]
        cand_per_cell.append(match)
        if not match:
            return []

    init = []
    for (pid, rot, edges) in cand_per_cell[0]:
        init.append(([(pid, rot, edges)], frozenset([pid]), 0))
    if not init: return []
    states = [init]
    for c in range(1, size):
        new_states = []
        for chain, used_row, score in states[-1]:
            cur_edges = chain[-1][2]
            for next_pid, next_rot, next_edges in cand_per_cell[c]:
                if next_pid in used_row: continue
                if cur_edges[1] != next_edges[3]: continue
                ew_match = 0 if is_border(cur_edges[1]) else 1
                new_chain = chain + [(next_pid, next_rot, next_edges)]
                new_states.append((new_chain, used_row | {next_pid}, score + ew_match))
        if not new_states: return []
        new_states.sort(key=lambda x: -x[2])
        new_states = new_states[:beam_k]
        states.append(new_states)
    states[-1].sort(key=lambda x: -x[2])
    return [(chain, used_row) for chain, used_row, _ in states[-1][:top_k]]


def score_full(placement, pieces, size=16):
    matched = 0
    for y in range(size):
        for x in range(size):
            pos = y * size + x
            if placement[pos] is None: continue
            pid, rot = placement[pos]
            edges = pieces[(pid, rot)]
            if x + 1 < size:
                ne = placement[pos + 1]
                if ne is not None:
                    pid2, rot2 = ne
                    e2 = pieces[(pid2, rot2)]
                    if edges[1] == e2[3] and not is_border(edges[1]):
                        matched += 1
            if y + 1 < size:
                se = placement[pos + size]
                if se is not None:
                    pid2, rot2 = se
                    e2 = pieces[(pid2, rot2)]
                    if edges[2] == e2[0] and not is_border(edges[2]):
                        matched += 1
    return matched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--meet-row', type=int, default=8)
    ap.add_argument('--row-k', type=int, default=8)
    ap.add_argument('--beam-k', type=int, default=300)
    ap.add_argument('--max-time', type=int, default=300)
    ap.add_argument('--out', default='output/vol-184/build_bidir.json')
    args = ap.parse_args()

    t0 = time.time()
    pieces = load_pieces()
    M = args.meet_row

    # === Top-down phase ===
    print("=== TOP-DOWN ===")
    top_beam = [([], frozenset(), 0)]  # (rows[0..r-1], used, score)
    for r in range(M):
        if time.time() - t0 > args.max_time / 2: break
        new_beam = []
        for rows_so_far, used, _ in top_beam:
            row_above = rows_so_far[-1] if rows_so_far else None
            if row_above is None:
                n_constraint = [BORDER] * 16
            else:
                n_constraint = [edges[2] for (_, _, edges) in row_above]
            chains = solve_row_topk(r, n_constraint, pieces, used,
                                     top_k=args.row_k, beam_k=args.beam_k)
            for chain, used_row in chains:
                new_used = used | used_row
                new_rows = rows_so_far + [chain]
                # Compute partial score from placement
                pl = [None] * 256
                for ri, row in enumerate(new_rows):
                    for ci, (pid, rot, _) in enumerate(row):
                        pl[ri * 16 + ci] = (pid, rot)
                s = score_full(pl, pieces)
                new_beam.append((new_rows, new_used, s))
        if not new_beam:
            print(f"Top-down row {r}: infeasible")
            break
        new_beam.sort(key=lambda x: -x[2])
        top_beam = new_beam[:args.row_k]
        print(f"  row {r}: beam={len(top_beam)} top_score={top_beam[0][2]}")

    # === Bottom-up phase ===
    print("=== BOTTOM-UP ===")
    # bot_beam stores (rows_below[r..15], used, score) keyed by r at lowest index.
    # Easier: store as dict r → list of chains. Use rows_below = list of (chain, used_in_row).
    # Track: bot_rows[i] is for row (15 - i), so bot_rows[0] = row 15, etc.
    bot_beam = [([], frozenset(), 0)]  # (rows_below, used, score)
    for r in range(15, M - 1, -1):
        if time.time() - t0 > args.max_time: break
        new_beam = []
        for rows_below, used, _ in bot_beam:
            # Row below us (already placed) is rows_below[-1] = the LAST added = row r+1.
            # S of row r must match N of row r+1.
            if not rows_below:
                # Row 15: S constraint is BORDER.
                s_constraint = [BORDER] * 16
            else:
                # Most-recently-added row in rows_below is row r+1.
                row_below = rows_below[-1]
                # N edges of row r+1 = piece N edges
                s_constraint = [edges[0] for (_, _, edges) in row_below]
            chains = solve_row_topk_by_s(r, s_constraint, pieces, used,
                                          top_k=args.row_k, beam_k=args.beam_k)
            for chain, used_row in chains:
                new_used = used | used_row
                new_rows = rows_below + [chain]
                # Score partial board placement
                pl = [None] * 256
                for i, row in enumerate(new_rows):
                    real_row = 15 - i  # row 15 first, then 14, etc.
                    for ci, (pid, rot, _) in enumerate(row):
                        pl[real_row * 16 + ci] = (pid, rot)
                s = score_full(pl, pieces)
                new_beam.append((new_rows, new_used, s))
        if not new_beam:
            print(f"Bottom-up row {r}: infeasible")
            break
        new_beam.sort(key=lambda x: -x[2])
        bot_beam = new_beam[:args.row_k]
        print(f"  row {r}: beam={len(bot_beam)} top_score={bot_beam[0][2]}")

    # === MERGE ===
    print("=== MERGE ===")
    # For each (top, bot) pair, check:
    #   - disjoint pieces
    #   - top[M-1].S edges match bot[M].N edges
    best = None
    n_pairs = 0; n_valid = 0
    for top_rows, top_used, top_score in top_beam:
        if len(top_rows) != M: continue
        top_last_s = [edges[2] for (_, _, edges) in top_rows[-1]]
        for bot_rows_below, bot_used, bot_score in bot_beam:
            n_pairs += 1
            # Bot has rows 15, 14, ..., M. Length should be 16 - M.
            if len(bot_rows_below) != 16 - M: continue
            # The row immediately below the interface is row M, which is the LAST in bot_rows_below.
            # bot_rows_below[-1] is the most recently added = row M.
            bot_first = bot_rows_below[-1]
            bot_first_n = [edges[0] for (_, _, edges) in bot_first]
            # Check interface match
            if top_last_s != bot_first_n: continue
            # Check piece disjointness
            if top_used & bot_used: continue
            # Build full placement
            pl = [None] * 256
            for ri, row in enumerate(top_rows):
                for ci, (pid, rot, _) in enumerate(row):
                    pl[ri * 16 + ci] = (pid, rot)
            for i, row in enumerate(bot_rows_below):
                real_row = 15 - i
                for ci, (pid, rot, _) in enumerate(row):
                    pl[real_row * 16 + ci] = (pid, rot)
            s = score_full(pl, pieces)
            n_valid += 1
            if best is None or s > best[0]:
                best = (s, pl)
    print(f"  examined {n_pairs} pairs, {n_valid} valid")
    if best is None:
        print("No valid merged board.")
        return
    score, placement = best
    n_placed = sum(1 for p in placement if p is not None)
    print(f"\nBEST MERGED: score={score}/480, placed={n_placed}/256")
    out_path = Path(REPO / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pl_json = []
    for pos, ent in enumerate(placement):
        if ent is None:
            pl_json.append(None)
        else:
            pid, rot = ent
            pl_json.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
    out_path.write_text(json.dumps({'placement': pl_json, 'matched': score}))
    print(f"saved {out_path}")


if __name__ == '__main__':
    main()
