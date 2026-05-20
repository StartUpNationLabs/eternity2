#!/usr/bin/env python3
"""V172 CHIASMUS — quick PoC.

Take two 460+ boards in DIFFERENT basins. Build a hybrid by interleaving:
  - rows 0, 2, 4, ... 14 from board A
  - rows 1, 3, 5, ... 15 from board B
But pieces must be unique. So we need a piece-deduplication step.

The hybrid's score is then a baseline — what does cross-basin interleaving
look like, score-wise? Is it close to 460 (basins merge cleanly) or
much lower (basins are incompatible)?

If the merge is clean, then the merged board is in a NEW basin
(not basin A, not basin B) and could be a basin-sample for further
ALNS.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_board(path, size=16):
    d = json.loads(Path(path).read_text())
    pl = d.get('placement', [])
    placement = [None] * (size * size)
    has_pos = any(isinstance(e, dict) and 'pos' in e for e in pl if e is not None)
    for i, entry in enumerate(pl):
        if entry is None:
            continue
        pos = int(entry['pos']) if has_pos else i
        placement[pos] = (int(entry['piece_id']), int(entry['rotation']))
    return d.get('matched', None), placement


def hybrid_interleave(A, B, row_owner, size=16):
    """row_owner[i] in {'A', 'B'} chooses which board owns row i.
    Returns (hybrid, conflicts) where hybrid[pos] = (pid, rot) or None,
    and conflicts is the list of positions where the chosen board's
    piece was already used (so we placed None instead).
    """
    used = set()
    hybrid = [None] * (size * size)
    conflicts = []
    for y in range(size):
        src = A if row_owner[y] == 'A' else B
        for x in range(size):
            pos = y * size + x
            ent = src[pos]
            if ent is None:
                continue
            pid, rot = ent
            if pid in used:
                conflicts.append(pos)
                continue  # leave None; will need repair
            used.add(pid)
            hybrid[pos] = (pid, rot)
    return hybrid, conflicts


def score_hybrid(hybrid, puzzle_csv=None, size=16):
    """Compute matched edges given a hybrid placement.
    Each piece's edges are taken at the rotation stored in the hybrid.
    Returns matched edge count.
    """
    # Load piece edges from CSV.
    csv_path = REPO.parent / 'data' / 'puzzles' / 'size_16_official_eternity.csv'
    if not csv_path.exists():
        return None
    edges_by_pid = {}
    for pid, line in enumerate(csv_path.read_text().splitlines()[1:]):
        parts = line.split(',')
        if len(parts) < 4: continue
        # Use string hash to compare. Strings are unique per color.
        edges_by_pid[pid] = parts[:4]

    BORDER = '1111111111111111'
    matched = 0
    for y in range(size):
        for x in range(size):
            pos = y * size + x
            ent = hybrid[pos]
            if ent is None: continue
            pid, rot = ent
            if pid not in edges_by_pid: continue
            edges = edges_by_pid[pid]
            # Rotation r clockwise: edge i in rotated = edges[(i-r) mod 4]
            def rot_edge(i):
                return edges[(i - rot) % 4]
            # East match
            if x + 1 < size:
                ne = hybrid[pos + 1]
                if ne is not None:
                    npid, nrot = ne
                    if npid in edges_by_pid:
                        nedges = edges_by_pid[npid]
                        e = rot_edge(1)
                        w_n = nedges[(3 - nrot) % 4]
                        if e == w_n and e != BORDER:
                            matched += 1
            # South match
            if y + 1 < size:
                se = hybrid[pos + size]
                if se is not None:
                    spid, srot = se
                    if spid in edges_by_pid:
                        sedges = edges_by_pid[spid]
                        s = rot_edge(2)
                        n_s = sedges[(0 - srot) % 4]
                        if s == n_s and s != BORDER:
                            matched += 1
    return matched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--board-a', required=True)
    ap.add_argument('--board-b', required=True)
    ap.add_argument('--scheme', default='ababab', help='row pattern: a/b chars')
    args = ap.parse_args()

    sA, A = load_board(args.board_a)
    sB, B = load_board(args.board_b)
    print(f"A: {args.board_a} score={sA}")
    print(f"B: {args.board_b} score={sB}")

    cpA = (A[0][0], A[15][0], A[240][0], A[255][0])
    cpB = (B[0][0], B[15][0], B[240][0], B[255][0])
    print(f"  cp(A) = {cpA}")
    print(f"  cp(B) = {cpB}")
    print()

    schemes = {
        'rowAB':    ['A' if i % 2 == 0 else 'B' for i in range(16)],
        'rowBA':    ['B' if i % 2 == 0 else 'A' for i in range(16)],
        'top8A':    ['A' if i < 8 else 'B' for i in range(16)],
        'top8B':    ['B' if i < 8 else 'A' for i in range(16)],
        'border4A': ['A' if (i < 4 or i >= 12) else 'B' for i in range(16)],
        'mid8A':    ['B' if (i < 4 or i >= 12) else 'A' for i in range(16)],
    }

    for sname, scheme in schemes.items():
        hybrid, conflicts = hybrid_interleave(A, B, scheme)
        sc = score_hybrid(hybrid)
        placed = sum(1 for h in hybrid if h is not None)
        print(f"  scheme={sname:>10}  placed={placed}/256  conflicts={len(conflicts)}  matched={sc}/480")


if __name__ == '__main__':
    main()
