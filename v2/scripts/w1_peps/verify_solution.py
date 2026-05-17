"""Verify a PEPS-output solution: piece-uniqueness + edge-match count."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from puzzle_loader import Puzzle, load_puzzle, BORDER


def verify(puzzle: Puzzle, placement: dict[int, tuple[int, int]]) -> dict:
    """Return verification stats: matched edges, total edges, piece-uniqueness."""
    size = puzzle.size
    n_cells = size * size

    # Piece-uniqueness
    pieces_used = [pid for pid, _ in placement.values()]
    unique_pieces = set(pieces_used)
    duplicates = [pid for pid in pieces_used if pieces_used.count(pid) > 1]

    # Edges
    matched = 0
    total_interior = 0
    total_border = 0
    border_correct = 0

    for pos in range(n_cells):
        if pos not in placement: continue
        pid, rot = placement[pos]
        edges = puzzle.piece_edges(pid, rot)  # (N, E, S, W)
        y, x = pos // size, pos % size

        # N edge
        if y == 0:
            total_border += 1
            if edges[0] == BORDER:
                border_correct += 1
        else:
            up_pos = (y - 1) * size + x
            if up_pos in placement:
                total_interior += 1
                up_pid, up_rot = placement[up_pos]
                up_edges = puzzle.piece_edges(up_pid, up_rot)
                # up cell's S edge must match my N edge
                if up_edges[2] == edges[0] and edges[0] != BORDER:
                    matched += 1

        # E edge
        if x == size - 1:
            total_border += 1
            if edges[1] == BORDER:
                border_correct += 1

        # S edge
        if y == size - 1:
            total_border += 1
            if edges[2] == BORDER:
                border_correct += 1

        # W edge
        if x == 0:
            total_border += 1
            if edges[3] == BORDER:
                border_correct += 1

    return {
        'pieces_used': len(pieces_used),
        'unique_pieces': len(unique_pieces),
        'duplicates': sorted(set(duplicates)),
        'matched_interior': matched,
        'total_interior': total_interior,
        'matched_border': border_correct,
        'total_border': total_border,
        'is_valid_placement': len(unique_pieces) == len(pieces_used) == puzzle.n_pieces,
        'is_complete_solution': len(unique_pieces) == puzzle.n_pieces
                                 and matched == total_interior
                                 and border_correct == total_border,
    }


if __name__ == "__main__":
    # 4×4 PEPS-output
    p = load_puzzle("../data/generated/size_4_colors_6_92cd6738.csv")
    peps_sol_4x4 = {}
    out_4x4 = """
    cell (0,0): piece=4 rot=0
    cell (0,1): piece=14 rot=1
    cell (0,2): piece=15 rot=3
    cell (0,3): piece=3 rot=0
    cell (1,0): piece=0 rot=3
    cell (1,1): piece=13 rot=1
    cell (1,2): piece=8 rot=2
    cell (1,3): piece=11 rot=2
    cell (2,0): piece=2 rot=3
    cell (2,1): piece=12 rot=1
    cell (2,2): piece=1 rot=2
    cell (2,3): piece=9 rot=0
    cell (3,0): piece=7 rot=3
    cell (3,1): piece=10 rot=1
    cell (3,2): piece=5 rot=1
    cell (3,3): piece=6 rot=1
    """
    import re
    for line in out_4x4.strip().splitlines():
        m = re.match(r'\s*cell \((\d+),(\d+)\): piece=(\d+) rot=(\d+)', line)
        if not m: continue
        y, x, pid, rot = int(m[1]), int(m[2]), int(m[3]), int(m[4])
        peps_sol_4x4[y * p.size + x] = (pid, rot)

    stats = verify(p, peps_sol_4x4)
    print(f"4×4 PEPS solution verification:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
