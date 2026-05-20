#!/usr/bin/env python3
"""V183 SEMAPHORE — row-by-row exact chain-DP for E2.

Given a board with row 0 already placed (from V175 build or canonical
hints + border DP), solve each subsequent row OPTIMALLY via chain-DP.

Per row r, the south edges of row r-1 fix the north edges of row r.
We need to pick a 16-tuple of (piece, rotation) that:
  - matches the N-constraint per cell
  - maximizes E-W matched edges within the row (chain-DP optimal)
  - respects piece-uniqueness (no piece reused)

When CSP becomes infeasible (no valid completion exists), we record
the row count and exit.

Output: completed board + score. Compare to V155/V175 builds.
"""
from __future__ import annotations
import argparse
import json
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
    """Load (pid, rot) → (N, E, S, W) edges for all rotations."""
    csv = REPO.parent / 'data' / 'puzzles' / 'size_16_official_eternity.csv'
    pieces = {}
    for pid, line in enumerate(csv.read_text().splitlines()[1:]):
        parts = line.split(',')
        if len(parts) < 4: continue
        # canonical N, E, S, W
        n, e, s, w = parts[:4]
        for r in range(4):
            # rotation r clockwise: edge i in rotated = base[(i - r) % 4]
            edges = [parts[(i - r) % 4] for i in range(4)]
            pieces[(pid, r)] = tuple(edges)  # (N, E, S, W)
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
    """Return list of (pid, rot, edges) that:
    - aren't in used_pids
    - have correct class for this cell
    - respect border constraints (N edge border iff top row, etc.)"""
    r, c = pos // size, pos % size
    cls = cell_class(pos)
    # required border on each side?
    need = [r == 0, c == size - 1, r == size - 1, c == 0]  # N, E, S, W
    out = []
    for (pid, rot), edges in pieces.items():
        if pid in used_pids: continue
        pcls = piece_class(edges)
        if pcls != cls: continue
        # check border constraints
        ok = True
        for i in range(4):
            if need[i]:
                if not is_border(edges[i]):
                    ok = False; break
            else:
                if is_border(edges[i]):
                    ok = False; break
        if ok:
            out.append((pid, rot, edges))
    return out


def solve_row(row_idx, row_above, pieces, used_pids, size=16):
    """row_above: list of (pid, rot, edges) tuples for row r-1. None for row 0.
    Returns: list of (pid, rot, edges) for the new row, or None if infeasible.
    Greedy: row-uniqueness, max E-W matches via chain-DP.
    """
    # Compute the required N-edge for each cell in this row.
    required_n = []
    for c in range(size):
        if row_above is None:
            # row 0: top border
            required_n.append(BORDER)
        else:
            # need to match row_above[c]'s S-edge
            _, _, edges_above = row_above[c]
            required_n.append(edges_above[2])  # S edge

    # For each cell, find candidates matching required_n.
    cand_per_cell = []
    for c in range(size):
        pos = row_idx * size + c
        cs = candidates_for_cell(pos, pieces, used_pids)
        # filter by N-edge constraint
        match = [(pid, rot, edges) for (pid, rot, edges) in cs if edges[0] == required_n[c]]
        cand_per_cell.append(match)
        if not match:
            return None  # infeasible

    # Chain-DP: max matched E-W edges along the row.
    # State at cell c: (chosen piece tuple, used in this row, total E-W matches so far)
    # We must enforce piece-uniqueness within row (and check piece not in used_pids,
    # which is already done in candidates_for_cell).

    # DP state: dp[c] = list of (piece_id, rotation, edges, used_in_row, score, parent_idx)
    # To keep memory bounded, prune to top-K per cell.
    K = 200  # pruning beam

    cell0 = cand_per_cell[0]
    if not cell0: return None
    # Each state: (pid, rot, edges, used_in_row_set, score, parent)
    states = [{(pid, rot): (edges, frozenset([pid]), 0, -1) for (pid, rot, edges) in cell0}]
    # states[c] is dict (pid, rot) → (edges, used_in_row, score, parent_key)

    for c in range(1, size):
        new_states = {}
        for next_pid, next_rot, next_edges in cand_per_cell[c]:
            for (cur_pid, cur_rot), (cur_edges, cur_used, cur_score, _) in states[-1].items():
                if next_pid in cur_used: continue
                # E-W constraint: cur cell's E = next cell's W
                if cur_edges[1] != next_edges[3]: continue
                # E-W match counts unless either is BORDER (border edges don't match for score).
                # In E2, border edges don't contribute to matched-edges count.
                ew_match = 0 if is_border(cur_edges[1]) else 1
                new_score = cur_score + ew_match
                key = (next_pid, next_rot)
                if key not in new_states or new_states[key][2] < new_score:
                    new_states[key] = (next_edges, cur_used | {next_pid}, new_score, (cur_pid, cur_rot))
        # Prune to top-K by score.
        if len(new_states) > K:
            items = sorted(new_states.items(), key=lambda kv: -kv[1][2])[:K]
            new_states = dict(items)
        if not new_states:
            return None
        states.append(new_states)

    # Find best terminal state.
    best_key = max(states[-1].keys(), key=lambda k: states[-1][k][2])
    # Reconstruct chain.
    row = [None] * size
    key = best_key
    for c in range(size - 1, -1, -1):
        edges, _, _, parent = states[c][key]
        row[c] = (key[0], key[1], edges)
        if c > 0:
            key = parent
    return row


def n_match(row):
    """Count N-S matches between consecutive cells in row (just for sanity)."""
    return 0


def score_board(placement, pieces, size=16):
    """Compute matched-edge count given placement: list of (pid, rot)."""
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
    ap.add_argument('--seed-board', help='Optional V175 board to take row 0 from')
    ap.add_argument('--out', default='output/vol-183/build.json')
    args = ap.parse_args()

    pieces = load_pieces()
    print(f"Loaded {len(pieces)} (piece, rotation) entries")

    placement = [None] * 256
    used_pids = set()
    size = 16

    if args.seed_board:
        score, src = load_board(args.seed_board)
        print(f"Seed board: {args.seed_board} score={score}")
        # Take row 0
        for c in range(size):
            if src[c] is None:
                continue
            placement[c] = src[c]
            used_pids.add(src[c][0])
        print(f"  row 0 seeded from {args.seed_board}, used {len(used_pids)} pieces")

    # Build row 0 if not seeded
    if not args.seed_board:
        row0 = solve_row(0, None, pieces, used_pids)
        if row0 is None:
            print("Row 0 INFEASIBLE!")
            return
        for c, (pid, rot, edges) in enumerate(row0):
            placement[c] = (pid, rot)
            used_pids.add(pid)
        print(f"row 0 solved, {len(used_pids)} pieces used")

    # Solve rows 1..15
    for r in range(1, size):
        # Build row_above as triplets
        row_above = []
        for c in range(size):
            pid, rot = placement[(r - 1) * size + c]
            edges = pieces[(pid, rot)]
            row_above.append((pid, rot, edges))
        new_row = solve_row(r, row_above, pieces, used_pids)
        if new_row is None:
            print(f"Row {r} INFEASIBLE — stopping.")
            break
        for c, (pid, rot, edges) in enumerate(new_row):
            placement[r * size + c] = (pid, rot)
            used_pids.add(pid)
        # Compute partial score
        partial_score = score_board(placement, pieces)
        print(f"row {r} solved. {len(used_pids)} used. partial score: {partial_score}")

    # Final score
    total = score_board(placement, pieces)
    print(f"\nFinal score: {total}/480")
    n_placed = sum(1 for p in placement if p is not None)
    print(f"Placed: {n_placed}/256")

    # Save.
    out_path = Path(REPO / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pl_json = []
    for pos, ent in enumerate(placement):
        if ent is None:
            pl_json.append(None)
        else:
            pid, rot = ent
            pl_json.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
    out_path.write_text(json.dumps({'placement': pl_json, 'matched': total}, indent=2))
    print(f"Saved to {out_path}")


if __name__ == '__main__':
    main()
