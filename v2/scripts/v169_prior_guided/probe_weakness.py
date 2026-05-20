#!/usr/bin/env python3
"""V169 — fast probe: for each 460 board, compute cell prior support
distribution and identify the 'weakest' cells.

Question (user, 2026-05-20): "what happens if we take the weakest, or
weaker, pieces?"

Quick answer requires:
  1. Load prior matrix (256 pieces × 256 positions; counts from corpus
     boards with score ≥ τ).
  2. Load a 460 board (V155→ALNS output).
  3. For each cell c, compute s(c) = prior_matrix[ board[c].piece_id ][c ].
  4. Report:
     - count of cells with s(c)=0 (unsupported)
     - count with s(c)∈{1,2,3} (weakly-supported)
     - histogram across supports
     - geographic distribution of weak cells (heatmap)
     - what the matched-edge density at weak cells is

Hypothesis: weak cells (low s) cluster near mismatched edges. If true,
prior-guided destroy ≈ defect-driven destroy. If NOT true (weak cells are
in the matched 'interior'), prior-guided destroy is a NEW signal.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]


def load_prior(path):
    d = json.loads(Path(path).read_text())
    mat = d['matrix']  # [piece_id][position] -> count
    return mat, d['n_boards']


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


def load_puzzle_edges():
    """Load piece-edge table for matched-edge computation.
    Returns dict piece_id -> [N, E, S, W] in canonical orientation."""
    # The canonical CSV (size_16_official_eternity.csv) is N,E,S,W as
    # 16-bit binary strings. piece_id is the 1-based line number (line 1
    # is header = 16 board-size). So pid 0 = line 2, etc.
    csv_path = REPO.parent / 'data' / 'puzzles' / 'size_16_official_eternity.csv'
    pieces = {}
    if not csv_path.exists():
        return pieces
    lines = csv_path.read_text().splitlines()
    # Skip first line (board size header).
    for pid, line in enumerate(lines[1:]):
        parts = line.split(',')
        if len(parts) < 4:
            continue
        # Treat each binary as a color id (parse as int base 2 is too big
        # — we just need equality semantics. Hash the string).
        edges = [hash(parts[i]) & 0xFFFF for i in range(4)]
        # But '0000000000000000' is BORDER; preserve that
        BORDER_STR = '0000000000000000'
        for i in range(4):
            if parts[i] == BORDER_STR:
                edges[i] = 0
        pieces[pid] = edges
    return pieces


def rotate_edges(edges, rot):
    """Rotation r ∈ {0..3} clockwise. Edges = [N, E, S, W]."""
    return edges[(0 - rot) % 4], edges[(1 - rot) % 4], edges[(2 - rot) % 4], edges[(3 - rot) % 4]


def count_matched_edges_at(placement, pieces, pos, size=16):
    """How many of cell `pos`'s 4 edges are matched (non-border interior matches)."""
    x, y = pos % size, pos // size
    if placement[pos] is None:
        return 0
    pid, rot = placement[pos]
    if pid not in pieces:
        return 0
    n, e, s, w = rotate_edges(pieces[pid], rot)
    cnt = 0
    BORDER = 0
    # East neighbor
    if x + 1 < size:
        pos_e = pos + 1
        if placement[pos_e] is not None:
            pid2, rot2 = placement[pos_e]
            if pid2 in pieces:
                _, _, _, w2 = rotate_edges(pieces[pid2], rot2)
                if e == w2 and e != BORDER:
                    cnt += 1
    # South neighbor
    if y + 1 < size:
        pos_s = pos + size
        if placement[pos_s] is not None:
            pid2, rot2 = placement[pos_s]
            if pid2 in pieces:
                n2, _, _, _ = rotate_edges(pieces[pid2], rot2)
                if s == n2 and s != BORDER:
                    cnt += 1
    # West neighbor
    if x > 0:
        pos_w = pos - 1
        if placement[pos_w] is not None:
            pid2, rot2 = placement[pos_w]
            if pid2 in pieces:
                _, e2, _, _ = rotate_edges(pieces[pid2], rot2)
                if w == e2 and w != BORDER:
                    cnt += 1
    # North neighbor
    if y > 0:
        pos_n = pos - size
        if placement[pos_n] is not None:
            pid2, rot2 = placement[pos_n]
            if pid2 in pieces:
                _, _, s2, _ = rotate_edges(pieces[pid2], rot2)
                if n == s2 and n != BORDER:
                    cnt += 1
    return cnt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--board', required=True)
    ap.add_argument('--prior',
                    default=str(REPO / 'scripts/v155_prior/prior_matrix_high459.json'))
    ap.add_argument('--top-weak', type=int, default=30)
    args = ap.parse_args()

    prior, n_boards = load_prior(args.prior)
    matched, placement = load_board(args.board)
    pieces = load_puzzle_edges()

    print(f"=== Board {args.board} ===")
    print(f"  matched: {matched}/480")
    print(f"  prior: n_boards={n_boards}, threshold=high459")
    print()

    # Per-cell support
    supports = []
    for pos, ent in enumerate(placement):
        if ent is None:
            supports.append(None)
            continue
        pid, _ = ent
        s = prior[pid][pos]
        supports.append(s)

    # Histogram
    from collections import Counter
    hist = Counter(s for s in supports if s is not None)
    print("Support histogram (count of cells at each support level):")
    total = sum(hist.values())
    for s in sorted(hist):
        bar = '#' * min(hist[s], 40)
        pct = 100 * hist[s] / total
        print(f"  s={s:>3}: {hist[s]:>4} cells ({pct:>5.1f}%) {bar}")
    print()

    # The "unsupported" cells (s=0): the corpus has NEVER seen this piece here
    weak0 = [pos for pos, s in enumerate(supports) if s == 0]
    print(f"Unsupported cells (s=0): {len(weak0)}")
    weak_le_2 = [pos for pos, s in enumerate(supports) if s is not None and s <= 2]
    print(f"Weakly-supported cells (s<=2): {len(weak_le_2)}")
    print()

    # Top-N weakest cells (sorted by support, then by mismatch-edge density)
    pairs = [(pos, s) for pos, s in enumerate(supports) if s is not None]
    pairs.sort(key=lambda x: x[1])
    print(f"Top-{args.top_weak} weakest cells:")
    matched_at_weak = []
    for pos, s in pairs[:args.top_weak]:
        m_at_cell = count_matched_edges_at(placement, pieces, pos) if pieces else -1
        matched_at_weak.append(m_at_cell)
        y, x = pos // 16, pos % 16
        pid, rot = placement[pos]
        print(f"  pos={pos:>3} (y={y:>2},x={x:>2}) pid={pid:>3} rot={rot}  s={s:>3}  matched_edges={m_at_cell}/4")
    if matched_at_weak and matched_at_weak[0] != -1:
        avg_m = sum(matched_at_weak) / len(matched_at_weak)
        print()
        print(f"  Avg matched edges at top-{args.top_weak} weakest cells: {avg_m:.2f}/4")
        # Compare to board average
        all_matched = [count_matched_edges_at(placement, pieces, p) for p in range(256)]
        avg_all = sum(all_matched) / 256
        print(f"  Avg matched edges across all cells:                   {avg_all:.2f}/4")
        print(f"  Ratio (weakest / all): {avg_m / max(avg_all, 0.001):.3f}")
        if avg_m < avg_all * 0.9:
            print("  => Weak cells are MORE DEFECTIVE than average (some overlap with defects).")
        elif avg_m > avg_all * 1.1:
            print("  => Weak cells are LESS DEFECTIVE than average (weakness is NEW SIGNAL beyond defects!).")
        else:
            print("  => Weak cells have ~average matched density (mostly independent signal).")
    print()

    # Print geographic ASCII map
    print("Weakness map (cells with s=0 marked '0', s<=2 marked 'w', else '.'):")
    print("    " + ''.join(f'{x:1d}' if x < 10 else chr(65 + x - 10) for x in range(16)))
    for y in range(16):
        row = '  '
        row += f'{y:>2}: '[2:]
        # use proper line label
        row = f'{y:>2}: '
        for x in range(16):
            pos = y * 16 + x
            s = supports[pos]
            if s is None:
                row += '?'
            elif s == 0:
                row += '0'
            elif s <= 2:
                row += 'w'
            else:
                row += '.'
        print(row)


if __name__ == '__main__':
    main()
