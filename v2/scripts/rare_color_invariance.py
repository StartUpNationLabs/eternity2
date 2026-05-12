#!/usr/bin/env python3
"""Rare-color invariance verification.

Hypothesis (vol-6 Candidate A): on plateau boards (score ≥ 440), the
5 rare colors (counts 24 each, colors 1-5) are 100% matched (vol-5
finding 29/29). Now ask: are the SAME PIECES placed at the SAME CELLS
across boards?

If yes (e.g., piece 137 always at cell 89 across all 29 boards), then
those rare-color pieces form a STRUCTURAL SKELETON — a fixed sub-
solution that any near-optimal board must contain. Solving E2 reduces
to placing the abundant-color pieces in the remaining cells.

This is genuinely beyond-known. No published E2 work has reported
this kind of invariance because nobody has analyzed an ensemble of
plateau boards from multiple solvers.

Output: per rare-color piece, fraction of boards that place it at
the modal cell. Per cell that ever holds a rare-color piece,
fraction of boards that hold the modal piece there.
"""

import glob
import json
import re
from collections import Counter, defaultdict


W = 16
H = 16
BORDER = 0


def parse_csv_piece_word(s):
    v = int(s.strip(), 2)
    if v == 65535:
        return 0
    return v


def load_pieces_and_classify(path):
    """Returns (pieces, rare_pieces) where rare_pieces is the set of
    piece IDs that have at least one rare-color edge (color ∈ {1..5})."""
    pieces = []
    with open(path) as f:
        size = int(f.readline().strip())
        for pid, line in enumerate(f):
            cols = line.strip().split(',')
            if len(cols) < 4:
                continue
            quad = tuple(parse_csv_piece_word(cols[i]) for i in range(4))
            pieces.append(quad)
    rare_pieces = set()
    for pid, q in enumerate(pieces):
        if any(1 <= c <= 5 for c in q):
            rare_pieces.add(pid)
    return pieces, rare_pieces


def load_corpus():
    """Load all plateau boards (score >= 440) with valid placement."""
    boards = []
    for path in sorted(glob.glob('output/archive/*.json') + glob.glob('output/*.json')):
        try:
            j = json.load(open(path))
        except Exception:
            continue
        if not isinstance(j, dict):
            continue
        sc = j.get('score', {})
        if isinstance(sc, int):
            score = sc
        elif isinstance(sc, dict):
            score = sc.get('matched_edges', 0)
        else:
            continue
        if score < 440:
            continue
        # Need placement OR bucas_url. Prefer placement.
        if j.get('placement'):
            placement = j['placement']
            if len(placement) != W * H:
                continue
            # placement entries are dicts {piece_id, rotation}.
            board = []
            for cell in placement:
                if cell is None:
                    board.append(None)
                else:
                    board.append((cell['piece_id'], cell['rotation']))
            boards.append({'path': path, 'score': score, 'board': board})
    return boards


def main():
    pieces, rare_pieces = load_pieces_and_classify(
        '../data/puzzles/size_16_official_eternity.csv'
    )
    print(f"# total pieces: {len(pieces)}")
    print(f"# rare-color pieces (have ≥1 edge in color {{1..5}}): {len(rare_pieces)}")

    boards = load_corpus()
    print(f"# corpus boards (score≥440 with placement): {len(boards)}")
    if not boards:
        print("# no boards with placement field — cannot do invariance analysis")
        return

    # For each rare-color piece, what cells does it occupy across boards?
    piece_to_cells = defaultdict(Counter)  # pid -> Counter(cell -> n)
    for entry in boards:
        for cell_idx, cell in enumerate(entry['board']):
            if cell is None:
                continue
            pid, rot = cell
            if pid in rare_pieces:
                piece_to_cells[pid][cell_idx] += 1

    # For each cell, what rare-color piece does it hold across boards?
    cell_to_pieces = defaultdict(Counter)  # cell -> Counter(pid -> n)
    for entry in boards:
        for cell_idx, cell in enumerate(entry['board']):
            if cell is None:
                continue
            pid, rot = cell
            if pid in rare_pieces:
                cell_to_pieces[cell_idx][pid] += 1

    n_boards = len(boards)
    print(f"\n=== per rare-color piece: how often is it at its modal cell? ===")
    print(f"{'pid':>4}  {'edges':>20}  {'modal_cell':>10}  {'count':>6}  {'frac':>6}")
    high_inv = 0
    low_inv = 0
    rare_pids_in_corpus = sorted(piece_to_cells.keys())
    for pid in rare_pids_in_corpus:
        cells = piece_to_cells[pid]
        modal_cell, modal_count = cells.most_common(1)[0]
        total = sum(cells.values())
        frac = modal_count / total
        x, y = modal_cell % W, modal_cell // W
        print(f"  {pid:>4}  {str(pieces[pid]):>20}  ({x:>2},{y:>2})={modal_cell:>3}  "
              f"{modal_count:>3}/{total:>2}  {frac:.2f}")
        if frac >= 0.8:
            high_inv += 1
        elif frac <= 0.4:
            low_inv += 1

    print(f"\n=== summary ===")
    print(f"  rare-color pieces appearing in corpus: {len(rare_pids_in_corpus)}")
    print(f"  HIGH invariance (≥80% at modal cell): {high_inv}")
    print(f"  LOW invariance (≤40% at modal cell): {low_inv}")

    print(f"\n=== per cell: which rare piece dominates? ===")
    cells_with_rare = sorted(cell_to_pieces.keys())
    print(f"  cells ever holding a rare piece: {len(cells_with_rare)}")
    high_cell_inv = 0
    for cell_idx in cells_with_rare:
        pids = cell_to_pieces[cell_idx]
        modal_pid, modal_count = pids.most_common(1)[0]
        total = sum(pids.values())
        frac = modal_count / total
        if frac >= 0.8:
            high_cell_inv += 1
    print(f"  HIGH-invariance cells (≥80% same piece): {high_cell_inv} / {len(cells_with_rare)}")

    # The full skeleton: for each cell, if the modal piece is held by
    # ≥80% of boards, consider it "skeleton-fixed". Total skeleton size.
    print(f"\n=== skeleton extraction ===")
    skeleton = {}
    for cell_idx in cells_with_rare:
        pids = cell_to_pieces[cell_idx]
        modal_pid, modal_count = pids.most_common(1)[0]
        total = sum(pids.values())
        if modal_count / total >= 0.8:
            skeleton[cell_idx] = modal_pid
    print(f"  skeleton-fixed cells (≥80% agreement): {len(skeleton)}")
    print(f"  remaining free cells: {W*H - 5 - len(skeleton)} (excluding 5 hint cells)")
    if skeleton:
        print(f"  estimated reduction factor: {(196 - len(skeleton) + 60) / 196:.2f}x")

    # Detailed per-cell breakdown.
    print(f"\n=== detailed cell-piece consensus ===")
    print(f"{'cell':>5}  {'(x,y)':>7}  {'modal_pid':>9}  {'count':>6}  {'frac':>6}")
    for cell_idx in cells_with_rare:
        pids = cell_to_pieces[cell_idx]
        modal_pid, modal_count = pids.most_common(1)[0]
        total = sum(pids.values())
        frac = modal_count / total
        x, y = cell_idx % W, cell_idx // W
        marker = ' <SKEL' if frac >= 0.8 else ''
        print(f"  {cell_idx:>5}  ({x:>2},{y:>2})  {modal_pid:>5}  "
              f"{modal_count:>3}/{total:>2}  {frac:.2f}{marker}")


if __name__ == "__main__":
    main()
