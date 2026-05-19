#!/usr/bin/env python3
"""V154 — Python reference DLX-XCC for small E2 puzzles.

Used to verify the Rust DLX encoder is correct. If Python solves 3×3
but Rust returns 0, the bug is in Rust's search. If both return 0, the
encoding has a bug.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]


def load_csv(p):
    BORDER_RAW = 65535
    pieces = []
    with open(p) as f:
        size = int(f.readline().strip())
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            sides = [int(s.strip(), 2) for s in parts[:4]]
            sides = [0 if v == BORDER_RAW else v for v in sides]
            pieces.append(tuple(sides))
    return size, pieces


def rotate(piece, r):
    """Match Rust convention: rotated[i] = base[(i + 4 - r) % 4]."""
    base = list(piece)
    return tuple(base[(i + 4 - r) % 4] for i in range(4))


def encode_dlx_xcc(pieces, size):
    """Returns (rows, n_primary, n_secondary) where each row is a list of
    (column_idx, color) — color=None for primary items (no color)."""
    BORDER = 0
    n_cells = size * size
    n_pieces = len(pieces)
    assert n_cells == n_pieces

    # Column layout:
    #   Primary: cells 0..n_cells, pieces n_cells..n_cells+n_pieces
    #   Secondary: h_adj 0..size*(size-1), v_adj
    n_h_adj = size * (size - 1)
    n_v_adj = (size - 1) * size
    n_adj = n_h_adj + n_v_adj
    n_primary = n_cells + n_pieces

    def h_adj(r, c): return r * (size - 1) + c
    def v_adj(r, c): return n_h_adj + r * size + c

    rows = []
    for cell in range(n_cells):
        r = cell // size
        c = cell % size
        for pid in range(n_pieces):
            for rot in range(4):
                sides = rotate(pieces[pid], rot)
                top, right, bottom, left = sides
                # Border constraints.
                if r == 0 and top != 0: continue
                if r != 0 and top == 0: continue
                if r == size - 1 and bottom != 0: continue
                if r != size - 1 and bottom == 0: continue
                if c == 0 and left != 0: continue
                if c != 0 and left == 0: continue
                if c == size - 1 and right != 0: continue
                if c != size - 1 and right == 0: continue

                row = [(cell, None), (n_cells + pid, None)]
                if r > 0:
                    row.append((n_primary + v_adj(r - 1, c), top))
                if r < size - 1:
                    row.append((n_primary + v_adj(r, c), bottom))
                if c > 0:
                    row.append((n_primary + h_adj(r, c - 1), left))
                if c < size - 1:
                    row.append((n_primary + h_adj(r, c), right))
                rows.append((row, (cell, pid, rot)))
    return rows, n_primary, n_adj


def solve(rows, n_primary, n_secondary, max_solutions=1):
    """xcover format: list of (set of columns, dict secondary→color).
    But xcover uses a different API. Roll our own minimal DLX-XCC."""
    # Use a simple recursive DLX-XCC. Suited for tiny puzzles.
    # State: which rows are still candidates, per-column purified color.
    n_cols = n_primary + n_secondary
    # Build column-row index.
    col_rows = [set() for _ in range(n_cols)]
    for i, (row_items, _meta) in enumerate(rows):
        for (c, _) in row_items:
            col_rows[c].add(i)
    row_active = [True] * len(rows)
    col_active = [True] * n_cols
    col_purified = [None] * n_cols  # None=unpurified
    solutions = []

    def primary_active():
        return [c for c in range(n_primary) if col_active[c] and any(row_active[r] for r in col_rows[c])]

    def secondary_unrestricted_in_row(row_items):
        """Check: for each secondary item in this row, color compat OK?"""
        for (col, color) in row_items:
            if col < n_primary: continue
            if col_purified[col] is not None and col_purified[col] != color:
                return False
        return True

    def search(depth=0):
        active_primaries = primary_active()
        if not active_primaries:
            solutions.append([_meta for r, (_, _meta) in enumerate(rows) if not row_active[r] and any(_meta is _meta for _ in [None])])
            # Actually we need to track which rows are CHOSEN.
            # Simpler: store chosen-row indices in path.
            return True
        # Check empty column.
        for c in active_primaries:
            cands = [r for r in col_rows[c] if row_active[r]]
            if not cands:
                return False
        # S-heuristic.
        chosen = min(active_primaries, key=lambda c: sum(1 for r in col_rows[c] if row_active[r]))
        cands = [r for r in col_rows[chosen] if row_active[r]]
        for r in cands:
            row_items, _meta = rows[r]
            # Feasibility: secondary colors compatible?
            if not secondary_unrestricted_in_row(row_items):
                continue
            # Try this row.
            # Save state.
            saved_row_active = list(row_active)
            saved_col_active = list(col_active)
            saved_col_purified = list(col_purified)
            for (col, color) in row_items:
                col_active[col] = False
                if col >= n_primary:
                    col_purified[col] = color
            # Hide rows that conflict.
            for other in range(len(rows)):
                if not row_active[other]:
                    continue
                other_items, _ = rows[other]
                conflict = False
                for (col, color) in other_items:
                    if not col_active[col]:
                        if col < n_primary:
                            conflict = True; break
                        else:
                            if col_purified[col] is not None and color != col_purified[col]:
                                conflict = True; break
                if conflict:
                    row_active[other] = False
            chosen_paths.append((r, _meta))
            if search(depth + 1):
                if len(solutions) >= max_solutions: return True
            chosen_paths.pop()
            # Restore.
            for i in range(len(row_active)): row_active[i] = saved_row_active[i]
            for i in range(len(col_active)): col_active[i] = saved_col_active[i]
            for i in range(len(col_purified)): col_purified[i] = saved_col_purified[i]
        return False

    chosen_paths = []
    # Hack: track chosen by writing to solutions ourselves.
    nodes_visited = [0]
    def search2(depth=0):
        nodes_visited[0] += 1
        active_primaries = [c for c in range(n_primary) if col_active[c] and any(row_active[r] for r in col_rows[c])]
        if not active_primaries:
            solutions.append(list(chosen_paths))
            return len(solutions) >= max_solutions
        for c in active_primaries:
            cands = [r for r in col_rows[c] if row_active[r]]
            if not cands:
                return False
        chosen = min(active_primaries, key=lambda c: sum(1 for r in col_rows[c] if row_active[r]))
        cands = [r for r in col_rows[chosen] if row_active[r]]
        for r in cands:
            row_items, _meta = rows[r]
            if not secondary_unrestricted_in_row(row_items):
                continue
            saved_row = list(row_active)
            saved_col = list(col_active)
            saved_pur = list(col_purified)
            for (col, color) in row_items:
                col_active[col] = False
                if col >= n_primary:
                    col_purified[col] = color
            for other in range(len(rows)):
                if not row_active[other]: continue
                other_items, _ = rows[other]
                conflict = False
                for (col, color) in other_items:
                    if not col_active[col]:
                        if col < n_primary:
                            conflict = True; break
                        else:
                            if col_purified[col] is not None and color != col_purified[col]:
                                conflict = True; break
                if conflict:
                    row_active[other] = False
            chosen_paths.append(_meta)
            if search2(depth + 1):
                return True
            chosen_paths.pop()
            for i in range(len(row_active)): row_active[i] = saved_row[i]
            for i in range(len(col_active)): col_active[i] = saved_col[i]
            for i in range(len(col_purified)): col_purified[i] = saved_pur[i]
        return False

    search2()
    print(f"[py-dlx] nodes_visited={nodes_visited[0]}")
    return solutions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    ap.add_argument("--max-solutions", type=int, default=1)
    args = ap.parse_args()
    size, pieces = load_csv(args.puzzle)
    print(f"[py-dlx] puzzle: {size}×{size}, {len(pieces)} pieces")
    rows, n_primary, n_secondary = encode_dlx_xcc(pieces, size)
    print(f"[py-dlx] rows={len(rows)} primary={n_primary} secondary={n_secondary}")
    import time
    t0 = time.time()
    sols = solve(rows, n_primary, n_secondary, args.max_solutions)
    elapsed = time.time() - t0
    print(f"[py-dlx] solutions={len(sols)} elapsed={elapsed:.2f}s")
    for s in sols[:3]:
        print(f"  solution: {s}")


if __name__ == "__main__":
    main()
