"""W7 — Frozen-variable backbone measurement for 459 basin.

For each cell on the 16×16 grid, count the number of DISTINCT (piece_id, rotation)
combinations across all available 459 boards. Cells with exactly 1 distinct
combo = "frozen" (true backbone). Cells with many = "liquid".

Vol-17 found a 17/18-cell backbone (was scan-order artifact per vol-20). Vol-20
corrected to just 5 hint cells. W7 measures whether there's a deeper backbone
in the 459 basin that vol-20 missed by considering only basin-equivalent boards.

References:
  - Achlioptas-Coja-Oghlan: Random Formulas Have Frozen Variables
  - Molloy 2012: Freezing threshold for k-coloring
  - vault/concepts/web-roam-2026-05-17.md (W7)

Usage:
  python3 measure.py output/v17_alns_only/*.json output/vol-110/NEW*.json [...]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict


def load_board(path: str) -> dict | None:
    """Return {pos: (piece_id, rotation)} or None if file not parsable."""
    try:
        data = json.loads(Path(path).read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return None
    placement = data.get('placement', data.get('placements', []))
    if not placement: return None
    out = {}
    for p in placement:
        pos = p.get('pos', p.get('position', None))
        pid = p.get('piece_id', p.get('pid', None))
        rot = p.get('rotation', p.get('rot', None))
        if pos is not None and pid is not None and rot is not None:
            out[int(pos)] = (int(pid), int(rot))
    return out if out else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("boards", nargs='+', help="Board JSON files to analyze")
    ap.add_argument("--score-filter", type=int, default=None,
                    help="Only include boards with matched_edges = this score")
    ap.add_argument("--out", type=Path, default=None,
                    help="Write detailed JSON output here")
    args = ap.parse_args()

    boards = []
    score_filter = args.score_filter
    skipped = 0
    for path in args.boards:
        try:
            data = json.loads(Path(path).read_text())
        except Exception:
            skipped += 1
            continue
        if score_filter is not None:
            score = data.get('interior_matched', data.get('matched_edges', data.get('matched', None)))
            if score != score_filter:
                skipped += 1
                continue
        placement = data.get('placement', data.get('placements', []))
        if not placement:
            skipped += 1
            continue
        board = {}
        for p in placement:
            pos = p.get('pos', p.get('position', None))
            pid = p.get('piece_id', p.get('pid', None))
            rot = p.get('rotation', p.get('rot', None))
            if pos is not None and pid is not None and rot is not None:
                board[int(pos)] = (int(pid), int(rot))
        if len(board) >= 256:
            boards.append((path, board))
        else:
            skipped += 1

    print(f"Loaded {len(boards)} boards; skipped {skipped}")
    if not boards:
        print("No valid boards.")
        return

    # For each cell, count distinct (pid, rot) across all boards.
    per_cell_distinct: dict[int, Counter] = defaultdict(Counter)
    for path, board in boards:
        for pos, val in board.items():
            per_cell_distinct[pos][val] += 1

    # Compute distribution: # cells with 1 distinct val, 2, 3, etc.
    distinct_counts = [len(per_cell_distinct[pos]) for pos in range(256)]
    dist_histogram = Counter(distinct_counts)
    print(f"\nFreezing distribution (# of cells with N distinct piece-rotations):")
    for n in sorted(dist_histogram.keys()):
        cnt = dist_histogram[n]
        pct = 100.0 * cnt / 256
        bar = '#' * min(60, int(cnt / 256 * 60))
        print(f"  N={n:3d}: {cnt:4d} cells ({pct:5.1f}%) {bar}")

    frozen = sum(1 for c in distinct_counts if c == 1)
    print(f"\n*** FROZEN cells (N=1): {frozen}/256 ({100*frozen/256:.1f}%) ***")

    # Print top-frozen cell locations
    frozen_cells = [(pos, list(per_cell_distinct[pos].items())[0])
                    for pos in range(256) if len(per_cell_distinct[pos]) == 1]
    print(f"\nFrozen cells (full list):")
    for pos, (val, cnt) in sorted(frozen_cells):
        y, x = pos // 16, pos % 16
        pid, rot = val
        print(f"  cell ({y:2d},{x:2d}) [pos {pos}]: piece={pid} rot={rot}")

    if args.out:
        output = {
            'n_boards': len(boards),
            'frozen_count': frozen,
            'distinct_distribution': {n: c for n, c in dist_histogram.items()},
            'frozen_cells': [
                {'pos': pos, 'y': pos // 16, 'x': pos % 16,
                 'piece_id': pid, 'rotation': rot}
                for pos, ((pid, rot), _) in sorted(frozen_cells)
            ],
            'per_cell_distinct_count': {pos: c for pos, c in enumerate(distinct_counts)},
        }
        args.out.write_text(json.dumps(output, indent=2))
        print(f"\nDetailed output written to {args.out}")


if __name__ == "__main__":
    main()
