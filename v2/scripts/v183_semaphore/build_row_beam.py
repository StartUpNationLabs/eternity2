#!/usr/bin/env python3
"""V183 SEMAPHORE — multi-row beam search variant.

Instead of greedy row selection (pick the best row, lock it, move on),
maintain TOP-K row completions and continue all of them. This gives
search beam at the row level — 16 levels deep instead of 256 levels.

State: row_states = list of (rows_so_far, used_pids, score).
At each row, expand each state into top-row-K completions of next row,
then dedup and keep best beam_K total.

Per-row chain-DP unchanged (same as build_from_row0.py); difference is
WHICH top-K candidates per row state.
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parents[2]
BORDER = '1111111111111111'


def load_board(path, size=16):
    d = json.loads(Path(path).read_text())
    pl = d.get('placement', [])
    placement = [None] * (size * size)
    has_pos = any(isinstance(e, dict) and 'pos' in e for e in pl if e is not None)
    for i, entry in enumerate(pl):
        if entry is None: continue
        pos = int(entry['pos']) if has_pos else i
        placement[pos] = (int(entry['piece_id']), int(entry['rotation']))
    return d.get('matched'), placement


def load_pieces():
    csv = REPO.parent / 'data' / 'puzzles' / 'size_16_official_eternity.csv'
    pieces = {}
    for pid, line in enumerate(csv.read_text().splitlines()[1:]):
        parts = line.split(',')
        if len(parts) < 4: continue
        n, e, s, w = parts[:4]
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
        pcls = piece_class(edges)
        if pcls != cls: continue
        ok = True
        for i in range(4):
            if need[i]:
                if not is_border(edges[i]): ok = False; break
            else:
                if is_border(edges[i]): ok = False; break
        if ok:
            out.append((pid, rot, edges))
    return out


def solve_row_topk(row_idx, row_above, pieces, used_pids, top_k=10, beam_k=300, size=16):
    """Return top-K (best terminating chains) for this row. Each chain is a
    list of (pid, rot, edges)."""
    # Required N-edges from row_above
    required_n = []
    for c in range(size):
        if row_above is None:
            required_n.append(BORDER)
        else:
            _, _, edges_above = row_above[c]
            required_n.append(edges_above[2])

    cand_per_cell = []
    for c in range(size):
        pos = row_idx * size + c
        cs = candidates_for_cell(pos, pieces, used_pids)
        match = [(pid, rot, edges) for (pid, rot, edges) in cs if edges[0] == required_n[c]]
        cand_per_cell.append(match)
        if not match:
            return []  # infeasible

    # Chain-DP with beam_k pruning.
    # State at cell c: list of (chain_so_far, used_in_row_set, score).
    # We keep beam_k best by score at each level.
    init = []
    for (pid, rot, edges) in cand_per_cell[0]:
        init.append(([(pid, rot, edges)], frozenset([pid]), 0))
    if not init:
        return []
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
        if not new_states:
            return []
        # Prune to beam_k by score.
        new_states.sort(key=lambda x: -x[2])
        new_states = new_states[:beam_k]
        states.append(new_states)

    # Return top-K terminating chains.
    states[-1].sort(key=lambda x: -x[2])
    return [chain for chain, _, _ in states[-1][:top_k]]


def score_board(placement, pieces, size=16):
    matched = 0
    for y in range(size):
        for x in range(size):
            pos = y * size + x
            ent = placement[pos]
            if ent is None: continue
            pid, rot = ent
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
    ap.add_argument('--row-top-k', type=int, default=8, help='Top-K row completions kept per state')
    ap.add_argument('--beam-k', type=int, default=300, help='Per-cell chain-DP beam width')
    ap.add_argument('--out', default='output/vol-183/build_beam.json')
    ap.add_argument('--max-time', type=int, default=180, help='Max seconds')
    args = ap.parse_args()

    t0 = time.time()
    pieces = load_pieces()
    size = 16

    # Multi-row beam. Each beam element is (placement_so_far_list, used_pids, score).
    # placement[r] = list of (pid, rot, edges) for that row.
    beam = [([], frozenset(), 0)]
    best_overall = (0, None, None)  # (score, placement, used_pids)

    for r in range(size):
        if time.time() - t0 > args.max_time:
            print(f"Time budget reached at row {r}")
            break
        new_beam = []
        for rows_so_far, used_pids, score_so_far in beam:
            row_above = rows_so_far[-1] if rows_so_far else None
            top_rows = solve_row_topk(r, row_above, pieces, used_pids,
                                       top_k=args.row_top_k, beam_k=args.beam_k)
            for row in top_rows:
                new_used = used_pids | set(pid for (pid, _, _) in row)
                # Compute partial score
                new_rows = rows_so_far + [row]
                placement = [None] * (size * size)
                for ri, prow in enumerate(new_rows):
                    for ci, (pid, rot, _) in enumerate(prow):
                        placement[ri * size + ci] = (pid, rot)
                new_score = score_board(placement, pieces)
                new_beam.append((new_rows, new_used, new_score))
                # Track best ever (for partial board)
                if new_score > best_overall[0]:
                    best_overall = (new_score, list(placement), new_used)
        if not new_beam:
            print(f"Row {r}: all chains infeasible. Stopping.")
            break
        # Sort + truncate
        new_beam.sort(key=lambda x: -x[2])
        beam = new_beam[:args.row_top_k]
        top = beam[0]
        print(f"Row {r} done. beam={len(beam)}. top_score={top[2]}, partial cells={(r+1)*size}")

    print()
    if best_overall[1] is None:
        print("No solution found")
        return
    score, placement, used = best_overall
    placed = sum(1 for p in placement if p is not None)
    print(f"BEST: score={score}/480, placed={placed}/256")
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
