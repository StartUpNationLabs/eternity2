#!/usr/bin/env python3
"""Build a consensus board from the top border family.

For each cell, place the modal (piece, rotation) across all top-family
boards. Repair piece duplicates by reassigning duplicate pieces to
cells that voted for a different (less-modal) piece.

Save as a pt_e2-compatible JSON for `--start-from` polishing.
"""

import argparse
import glob
import json
import re
import sys
from collections import Counter, defaultdict


W = 16; H = 16; BORDER = 0


def parse_csv_piece_word(s):
    v = int(s.strip(), 2)
    if v == 65535: return 0
    return v


def load_pieces(path):
    pieces = []
    with open(path) as f:
        size = int(f.readline().strip())
        for pid, line in enumerate(f):
            cols = line.strip().split(',')
            if len(cols) < 4: continue
            pieces.append(tuple(parse_csv_piece_word(cols[i]) for i in range(4)))
    return pieces


def piece_class(quad):
    n = sum(1 for c in quad if c == BORDER)
    return 0 if n >= 2 else (1 if n == 1 else 2)


def cell_class_pos(pos):
    x, y = pos % W, pos // W
    n = (x == 0) + (x == W-1) + (y == 0) + (y == H-1)
    return 0 if n >= 2 else (1 if n == 1 else 2)


def load_corpus(min_score=449):
    boards = []
    for path in sorted(glob.glob('output/archive/*.json') + glob.glob('output/*.json')):
        try: j = json.load(open(path))
        except: continue
        if not isinstance(j, dict): continue
        sc = j.get('score', {})
        if isinstance(sc, int): score = sc
        elif isinstance(sc, dict): score = sc.get('matched_edges', 0)
        else: continue
        if score < min_score: continue
        if not j.get('placement'): continue
        pl = j['placement']
        if len(pl) != W*H: continue
        boards.append({'path': path, 'score': score, 'pl': pl})
    return boards


def border_sig(pl):
    sig = []
    for ci in range(W*H):
        x, y = ci % W, ci // W
        if x == 0 or x == W-1 or y == 0 or y == W-1:
            c = pl[ci]
            sig.append(c['piece_id'] if c else -1)
    return tuple(sig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--min-score', type=int, default=449)
    ap.add_argument('--puzzle', default='../data/puzzles/size_16_official_eternity.csv')
    args = ap.parse_args()

    pieces = load_pieces(args.puzzle)
    boards = load_corpus(args.min_score)
    print(f'corpus: {len(boards)} boards', file=sys.stderr)
    sig_counts = Counter()
    for b in boards: sig_counts[border_sig(b['pl'])] += 1
    top_sig, top_n = sig_counts.most_common(1)[0]
    top_boards = [b for b in boards if border_sig(b['pl']) == top_sig]
    print(f'top border family: {top_n} boards', file=sys.stderr)

    # Per cell: ranked list of (pid, rot) by frequency.
    cell_ranking = {}
    for ci in range(W*H):
        c = Counter()
        for b in top_boards:
            if b['pl'][ci]:
                c[(b['pl'][ci]['piece_id'], b['pl'][ci]['rotation'])] += 1
        if c:
            cell_ranking[ci] = c.most_common()

    # Greedy assignment: pick modal piece per cell. If duplicate, pick
    # next-modal alternative for one of the conflicting cells.
    placement = [None] * (W * H)
    used_pieces = set()

    # Sort cells by HIGHEST modal-fraction first — most-confident cells
    # get their first choice.
    cells_by_confidence = sorted(
        cell_ranking.keys(),
        key=lambda ci: -cell_ranking[ci][0][1] / sum(n for _, n in cell_ranking[ci])
    )

    n_first_choice = 0
    n_fallback = 0
    n_unfilled = 0
    for ci in cells_by_confidence:
        ranked = cell_ranking[ci]
        # Try in ranking order until we find a piece not yet used.
        chosen = None
        for (pid, rot), count in ranked:
            if pid in used_pieces:
                continue
            chosen = (pid, rot)
            if (pid, rot) == ranked[0][0:2]:
                n_first_choice += 1
            else:
                n_fallback += 1
            break
        if chosen is None:
            n_unfilled += 1
            continue
        used_pieces.add(chosen[0])
        placement[ci] = {'piece_id': chosen[0], 'rotation': chosen[1]}

    print(f'first-choice placements: {n_first_choice}', file=sys.stderr)
    print(f'fallback placements: {n_fallback}', file=sys.stderr)
    print(f'unfilled cells: {n_unfilled}', file=sys.stderr)

    # Fill any unfilled cells with remaining pieces matching cell-class.
    if n_unfilled > 0:
        remaining_pieces = sorted(set(range(len(pieces))) - used_pieces)
        unfilled_cells = [ci for ci in range(W*H) if placement[ci] is None]
        # Match by class.
        for ci in unfilled_cells:
            cls = cell_class_pos(ci)
            for pid in remaining_pieces:
                if piece_class(pieces[pid]) == cls:
                    placement[ci] = {'piece_id': pid, 'rotation': 0}
                    remaining_pieces.remove(pid)
                    used_pieces.add(pid)
                    break

    # Verify.
    n_placed = sum(1 for p in placement if p)
    print(f'final placed: {n_placed}/256', file=sys.stderr)

    # Compute score.
    def rotate(q, r):
        t,rr,b,l = q
        if r == 0: return (t, rr, b, l)
        if r == 1: return (l, t, rr, b)
        if r == 2: return (b, l, t, rr)
        return (rr, b, l, t)

    def score(pl):
        s = 0
        for y in range(H):
            for x in range(W):
                pos = y*W+x
                if not pl[pos]: continue
                edges = rotate(pieces[pl[pos]['piece_id']], pl[pos]['rotation'])
                if x+1 < W and pl[pos+1]:
                    re = rotate(pieces[pl[pos+1]['piece_id']], pl[pos+1]['rotation'])
                    if edges[1] == re[3] and edges[1] != BORDER: s += 1
                if y+1 < H and pl[pos+W]:
                    be = rotate(pieces[pl[pos+W]['piece_id']], pl[pos+W]['rotation'])
                    if edges[2] == be[0] and edges[2] != BORDER: s += 1
        return s

    sc = score(placement)
    print(f'consensus board score: {sc}/480', file=sys.stderr)

    out = {
        'run_name': 'consensus_topfamily',
        'puzzle': {'name': 'size_16_official_eternity'},
        'score': {'matched_edges': sc, 'total_edges': 480, 'percent': 100*sc/480,
                  'placed_cells': n_placed, 'total_cells': W*H},
        'placement': placement,
        'consensus_metadata': {
            'top_family_size': top_n,
            'first_choice_cells': n_first_choice,
            'fallback_cells': n_fallback,
        },
    }
    with open(args.out, 'w') as f:
        json.dump(out, f, indent=2)
    print(f'wrote {args.out}', file=sys.stderr)


if __name__ == '__main__':
    main()
