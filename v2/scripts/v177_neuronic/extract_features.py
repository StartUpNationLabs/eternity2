#!/usr/bin/env python3
"""V177 NEURONIC — Feature extractor for board ranking.

For a (partial or complete) board, compute a fixed-length feature vector:
  - score: raw matched edges
  - prior_sum: sum of prior(piece, position) over placed cells
  - n_placed: number of cells with a piece
  - n_unsupported: cells with prior(piece, pos) == 0
  - mismatch_count: edges within board that don't match
  - mismatch_components: # connected components in mismatch graph
  - border_spectrum[k] for k in {5, 7, 12, 13, 16, 19, 26, 29}
  - per_class_used_ratio: corners/edges/interior used fractions
  - hint_match_count: # hint positions with the expected piece+rot

Output: JSON per board with feature dict + label (final score if known).
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from collections import deque, defaultdict

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
    return d.get('matched'), placement


def load_pieces():
    csv = REPO.parent / 'data' / 'puzzles' / 'size_16_official_eternity.csv'
    pieces = {}
    for pid, line in enumerate(csv.read_text().splitlines()[1:]):
        parts = line.split(',')
        if len(parts) < 4: continue
        pieces[pid] = parts[:4]
    return pieces


def rotate_edges(parts, rot):
    return [parts[(i - rot) % 4] for i in range(4)]


def piece_class(parts):
    n_border = sum(1 for p in parts if p == '1111111111111111')
    if n_border == 2: return 'corner'
    if n_border == 1: return 'edge'
    return 'interior'


BORDER = '1111111111111111'


def matched_edges_and_mismatches(placement, pieces, size=16):
    matched = 0
    mismatch_cells = set()
    for y in range(size):
        for x in range(size):
            pos = y * size + x
            ent = placement[pos]
            if ent is None: continue
            pid, rot = ent
            if pid not in pieces: continue
            e = rotate_edges(pieces[pid], rot)
            # East
            if x + 1 < size:
                rent = placement[pos + 1]
                if rent is not None:
                    rpid, rrot = rent
                    re = rotate_edges(pieces[rpid], rrot)
                    if e[1] != BORDER and e[1] != '':
                        if e[1] == re[3]:
                            matched += 1
                        else:
                            mismatch_cells.add(pos)
                            mismatch_cells.add(pos + 1)
            # South
            if y + 1 < size:
                sent = placement[pos + size]
                if sent is not None:
                    spid, srot = sent
                    se = rotate_edges(pieces[spid], srot)
                    if e[2] != BORDER and e[2] != '':
                        if e[2] == se[0]:
                            matched += 1
                        else:
                            mismatch_cells.add(pos)
                            mismatch_cells.add(pos + size)
    return matched, mismatch_cells


def count_components(cells, size=16):
    if not cells: return 0
    cells = set(cells)
    n = 0
    visited = set()
    for c in cells:
        if c in visited: continue
        n += 1
        q = deque([c])
        visited.add(c)
        while q:
            p = q.popleft()
            x, y = p % size, p // size
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < size and 0 <= ny < size:
                    np = ny * size + nx
                    if np in cells and np not in visited:
                        visited.add(np)
                        q.append(np)
    return n


def border_ring_colors(placement, pieces, size=16):
    """Same as V173 SPECTRA: 60 perimeter cells, interior-facing edge color."""
    color_table = border_ring_colors._table
    out = []
    def cid(s):
        if s not in color_table:
            color_table[s] = len(color_table)
        return color_table[s]
    # Top row, S edges
    for x in range(size):
        pos = x
        if placement[pos] is None:
            out.append(-1); continue
        pid, rot = placement[pos]
        e = rotate_edges(pieces[pid], rot)
        out.append(cid(e[2]))
    # Right col, W edges
    for y in range(1, size - 1):
        pos = y * size + (size - 1)
        if placement[pos] is None:
            out.append(-1); continue
        pid, rot = placement[pos]
        e = rotate_edges(pieces[pid], rot)
        out.append(cid(e[3]))
    # Bottom row, N edges
    for x in range(size - 1, -1, -1):
        pos = (size - 1) * size + x
        if placement[pos] is None:
            out.append(-1); continue
        pid, rot = placement[pos]
        e = rotate_edges(pieces[pid], rot)
        out.append(cid(e[0]))
    # Left col, E edges
    for y in range(size - 2, 0, -1):
        pos = y * size
        if placement[pos] is None:
            out.append(-1); continue
        pid, rot = placement[pos]
        e = rotate_edges(pieces[pid], rot)
        out.append(cid(e[1]))
    return out
border_ring_colors._table = {}


def dft_amp(seq, ks):
    n = len(seq)
    out = []
    for k in ks:
        re = sum(seq[t] * math.cos(2 * math.pi * k * t / n) for t in range(n))
        im = sum(seq[t] * math.sin(2 * math.pi * k * t / n) for t in range(n))
        out.append(math.sqrt(re * re + im * im) / n)
    return out


def extract_features(board_path, pieces, prior=None):
    """Returns dict of features + label (matched). Returns None if invalid."""
    matched, placement = load_board(board_path)
    if matched is None or placement is None:
        return None

    n_placed = sum(1 for p in placement if p is not None)
    # Score (re-compute for verification)
    m, mismatch_cells = matched_edges_and_mismatches(placement, pieces)

    # Prior sum
    prior_sum = 0
    n_unsupported = 0
    if prior is not None:
        for pos, ent in enumerate(placement):
            if ent is None: continue
            pid, _ = ent
            try:
                p_val = prior[pid][pos]
            except (KeyError, IndexError):
                p_val = 0
            prior_sum += p_val
            if p_val == 0:
                n_unsupported += 1

    # Mismatch components
    mc = count_components(mismatch_cells)

    # Border spectrum (only meaningful if border fully placed)
    border_full = all(placement[p] is not None for p in
                      list(range(16)) + list(range(15, 256, 16))
                      + list(range(240, 256)) + list(range(0, 241, 16)))
    if border_full:
        ring = border_ring_colors(placement, pieces)
        if any(c == -1 for c in ring):
            spec = [0.0] * 8
        else:
            spec = dft_amp(ring, [5, 7, 12, 13, 16, 19, 26, 29])
    else:
        spec = [0.0] * 8

    # Per-class piece usage
    used = {'corner': set(), 'edge': set(), 'interior': set()}
    for pos, ent in enumerate(placement):
        if ent is None: continue
        pid, _ = ent
        if pid in pieces:
            cls = piece_class(pieces[pid])
            used[cls].add(pid)
    # Canonical E2: 4 corners, 56 edges, 196 interiors
    used_corner_r = len(used['corner']) / 4
    used_edge_r = len(used['edge']) / 56
    used_interior_r = len(used['interior']) / 196

    return {
        'path': str(board_path),
        'matched': matched,
        'n_placed': n_placed,
        'computed_matched': m,
        'mismatch_count': len(mismatch_cells),
        'mismatch_components': mc,
        'prior_sum': prior_sum,
        'n_unsupported': n_unsupported,
        'border_spec': spec,
        'used_corner_r': used_corner_r,
        'used_edge_r': used_edge_r,
        'used_interior_r': used_interior_r,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db-dir', default='database-400-480')
    ap.add_argument('--prior', default='scripts/v155_prior/prior_matrix_high459.json')
    ap.add_argument('--out', default='output/vol-177/features.jsonl')
    ap.add_argument('--limit', type=int, default=0,
                    help='Limit number of boards (0 = all)')
    args = ap.parse_args()

    pieces = load_pieces()
    print(f"Loaded {len(pieces)} pieces")

    prior = None
    if Path(args.prior).exists():
        prior = json.loads(Path(args.prior).read_text())['matrix']
        print(f"Loaded prior matrix (n_boards={json.loads(Path(args.prior).read_text())['n_boards']})")

    db = Path(REPO / args.db_dir)
    boards = sorted(db.glob('*.json'))
    if args.limit:
        boards = boards[:args.limit]
    print(f"Extracting features from {len(boards)} boards...")

    out_path = Path(REPO / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w') as f:
        for i, bp in enumerate(boards):
            try:
                feat = extract_features(bp, pieces, prior)
            except Exception as e:
                print(f"  ERROR {bp.name}: {e}")
                continue
            if feat is None: continue
            f.write(json.dumps(feat) + '\n')
            if (i + 1) % 100 == 0:
                print(f"  {i + 1}/{len(boards)}")

    print(f"Wrote features to {out_path}")


if __name__ == '__main__':
    main()
