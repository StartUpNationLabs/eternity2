"""E2 canonical I/O utilities for Python scripts.

Matches the Rust loader in crates/puzzle-io/src/lib.rs exactly.

Color encoding:
- The CSV stores each color as a 16-bit BINARY STRING (16 chars of 0/1).
- The string converts DIRECTLY to a u8 color value via int(s, 2).
- "1111111111111111" (65535) is the BORDER sentinel, mapped to 0.
- All other values are colors 1..22 in canonical E2.

Rotation encoding:
- Rotation 0: edges = [top, right, bottom, left] (as stored).
- Rotation 1: edges = [left, top, right, bottom] (R90 cw).
- Rotation 2: edges = [bottom, left, top, right] (R180).
- Rotation 3: edges = [right, bottom, left, top] (R270 cw).

Match definition:
- Two adjacent placed cells (i, j) with edges e_i, e_j MATCH on their
  shared edge iff the colors are equal AND non-zero (non-BORDER).
- Border edges (color = 0) DO NOT count as matched.

Use this module to avoid Python parser bugs.

API:
- load_pieces(path) -> List[Tuple[int, int, int, int]]: per-piece (T, R, B, L) tuples.
- load_canonical_hints() -> List[Tuple[int, int, int, int]]: (pos, pid, rot, _).
- rot_edges(edges, rot) -> Tuple[int, int, int, int]: apply rotation.
- load_placement(path) -> List[List[Tuple|None]]: 16x16 grid of (pid, rot) or None.
- score_board(placement, pieces) -> Tuple[int, int]: (matched_count, total_possible).
"""
import json
from pathlib import Path

SIDE = 16
DEFAULT_PUZZLE = "../data/puzzles/size_16_official_eternity.csv"


def parse_color(s):
    """Parse 16-bit binary string as u8 color value.
    BORDER (all 1s) maps to 0; other values are colors 1..255."""
    s = s.strip()
    if s == "1" * 16:
        return 0
    return int(s, 2)


def load_pieces(path=DEFAULT_PUZZLE):
    """Load all pieces from the canonical CSV.
    Returns: List of (T, R, B, L) tuples, indexed by piece_id (0..255)."""
    pieces = []
    with open(path) as f:
        # First line is size
        next(f)
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 4: continue
            t = parse_color(parts[0])
            r = parse_color(parts[1])
            b = parse_color(parts[2])
            l = parse_color(parts[3])
            pieces.append((t, r, b, l))
    return pieces


def load_canonical_hints(path=DEFAULT_PUZZLE):
    """Load hint annotations from the CSV.
    Returns: List of (pos, piece_id, rotation) tuples."""
    hints = []
    with open(path) as f:
        next(f)
        for pid, line in enumerate(f):
            parts = line.strip().split(',')
            if len(parts) < 7: continue
            try:
                x = int(parts[4])
                y = int(parts[5])
                rot = int(parts[6])
            except ValueError:
                continue
            # Hint convention: non-zero x, y, or rot → hint at (y, x)
            # Except piece 0 with all-zero (= absent hint).
            if pid == 0 and (x, y, rot) == (0, 0, 0):
                continue
            if (x, y, rot) == (0, 0, 0):
                continue
            pos = y * SIDE + x
            hints.append((pos, pid, rot))
    return hints


def rot_edges(edges, rot):
    """Apply rotation to 4-tuple (T, R, B, L).
    Matches eternity2_core::Edges::rotated."""
    if rot == 0: return edges
    if rot == 1: return (edges[3], edges[0], edges[1], edges[2])
    if rot == 2: return (edges[2], edges[3], edges[0], edges[1])
    if rot == 3: return (edges[1], edges[2], edges[3], edges[0])
    raise ValueError(f"bad rotation {rot}")


def load_placement(board_path, pieces=None):
    """Load a board JSON. Returns 16x16 grid of (pid, rot) or None.
    Supports 'placement' formats: indexed array OR sparse with 'pos' field."""
    with open(board_path) as f:
        data = json.load(f)
    grid = [[None] * SIDE for _ in range(SIDE)]
    arr = data.get('placement', [])
    for idx, item in enumerate(arr):
        if item is None: continue
        pos = item.get('pos', idx)
        pid = item['piece_id']
        rot = item['rotation']
        r, c = pos // SIDE, pos % SIDE
        grid[r][c] = (pid, rot)
    return grid


def score_board(placement, pieces):
    """Count matched edges in a placement. Returns (matched, total_possible)."""
    matched = 0
    total = 0
    for r in range(SIDE):
        for c in range(SIDE):
            cell = placement[r][c]
            if cell is None: continue
            pid, rot = cell
            T, R, B, L = rot_edges(pieces[pid], rot)
            # Right neighbor
            if c + 1 < SIDE and placement[r][c+1] is not None:
                pid2, rot2 = placement[r][c+1]
                nT, nR, nB, nL = rot_edges(pieces[pid2], rot2)
                total += 1
                if R == nL and R != 0:
                    matched += 1
            # Bottom neighbor
            if r + 1 < SIDE and placement[r+1][c] is not None:
                pid2, rot2 = placement[r+1][c]
                nT, nR, nB, nL = rot_edges(pieces[pid2], rot2)
                total += 1
                if B == nT and B != 0:
                    matched += 1
    return matched, total
