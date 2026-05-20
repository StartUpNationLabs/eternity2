#!/usr/bin/env python3
"""V173 SPECTRAL SIGNATURE — Border-ring Fourier signature analysis.

For each high-score board, extract the border ring as a 56-step sequence
of (color_left, color_right) interior-facing edges. Compute the DFT
amplitude spectrum. Compare signatures across boards by score-class.

Hypothesis: 469-tier boards share spectral peaks at specific frequencies
that 460-tier boards lack. If so, board's border spectrum predicts
ceiling.

Output: per board, the top-5 frequencies + amplitudes. Per score-class,
the median amplitude per frequency. Test for separation.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import math
from collections import defaultdict

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


def load_pieces():
    csv = REPO.parent / 'data' / 'puzzles' / 'size_16_official_eternity.csv'
    pieces = {}
    if not csv.exists():
        return pieces
    for pid, line in enumerate(csv.read_text().splitlines()[1:]):
        parts = line.split(',')
        if len(parts) < 4: continue
        pieces[pid] = parts[:4]
    return pieces


def color_id(s, table=None):
    """Map a 16-bit color string to a small integer id."""
    if table is None: table = color_id._table
    if s not in table:
        table[s] = len(table)
    return table[s]
color_id._table = {}


def border_ring_signature(placement, pieces, size=16):
    """Walk the border ring clockwise starting at (0,0), collecting the
    INTERIOR-facing edge color at each cell. Return a sequence of length 60.

    Each border cell has exactly one interior edge (corners have 0; edges
    have 1; but the ring traversal also has 'turn' angles which we ignore).
    Actually corners have 2 border edges and 2 interior edges. Let's
    return all 60 perimeter cells × their interior-facing edges.

    Indexing: top row (y=0, x=0..15) → interior edge is S
              right col (y=1..14, x=15) → interior edge is W
              bottom row (y=15, x=15..0) → interior edge is N
              left col (y=14..1, x=0) → interior edge is E
    """
    ring = []  # list of (x, y, edge_color_id)
    # Top row, S edges (x=0..15)
    for x in range(size):
        pos = x
        ent = placement[pos]
        if ent is None:
            ring.append((x, 0, -1))
            continue
        pid, rot = ent
        edges = pieces.get(pid)
        if edges is None:
            ring.append((x, 0, -1))
            continue
        # S edge: index 2 in (N, E, S, W) rotated.
        s_edge = edges[(2 - rot) % 4]
        ring.append((x, 0, color_id(s_edge)))
    # Right column, W edges (y=1..14, x=15)
    for y in range(1, size - 1):
        pos = y * size + (size - 1)
        ent = placement[pos]
        if ent is None:
            ring.append((size-1, y, -1))
            continue
        pid, rot = ent
        edges = pieces.get(pid)
        if edges is None:
            ring.append((size-1, y, -1))
            continue
        # W edge: index 3
        w_edge = edges[(3 - rot) % 4]
        ring.append((size-1, y, color_id(w_edge)))
    # Bottom row, N edges (x=15..0)
    for x in range(size - 1, -1, -1):
        pos = (size - 1) * size + x
        ent = placement[pos]
        if ent is None:
            ring.append((x, size-1, -1))
            continue
        pid, rot = ent
        edges = pieces.get(pid)
        if edges is None:
            ring.append((x, size-1, -1))
            continue
        # N edge: index 0
        n_edge = edges[(0 - rot) % 4]
        ring.append((x, size-1, color_id(n_edge)))
    # Left column, E edges (y=14..1, x=0)
    for y in range(size - 2, 0, -1):
        pos = y * size
        ent = placement[pos]
        if ent is None:
            ring.append((0, y, -1))
            continue
        pid, rot = ent
        edges = pieces.get(pid)
        if edges is None:
            ring.append((0, y, -1))
            continue
        # E edge: index 1
        e_edge = edges[(1 - rot) % 4]
        ring.append((0, y, color_id(e_edge)))
    return [c for (_, _, c) in ring]


def dft_amplitude(seq):
    """Naive O(N^2) DFT of an integer-valued sequence. Returns list of
    amplitude per frequency 0..N/2."""
    n = len(seq)
    amps = []
    for k in range(n // 2 + 1):
        re = sum(seq[t] * math.cos(2 * math.pi * k * t / n) for t in range(n))
        im = sum(seq[t] * math.sin(2 * math.pi * k * t / n) for t in range(n))
        amps.append(math.sqrt(re * re + im * im) / n)
    return amps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db-dir', default='database-400-480')
    ap.add_argument('--score-bins', nargs='+', type=int,
                    default=[440, 450, 458, 460, 465, 469, 480])
    args = ap.parse_args()

    pieces = load_pieces()
    print(f"Loaded {len(pieces)} pieces")

    db_dir = REPO / args.db_dir
    boards = sorted(db_dir.glob('*.json'))
    print(f"Scanning {len(boards)} boards...")

    # Compute signatures.
    by_bin = defaultdict(list)
    for bp in boards:
        try:
            score, pl = load_board(bp)
        except Exception:
            continue
        if score is None:
            continue
        if not all(p is not None for p in pl[:16] + pl[240:256]):
            continue
        # Find bin.
        bin_lo = max((b for b in args.score_bins if b <= score), default=None)
        if bin_lo is None:
            continue
        ring = border_ring_signature(pl, pieces)
        if any(c == -1 for c in ring):
            continue
        amps = dft_amplitude(ring)
        by_bin[bin_lo].append((score, bp.name, amps))

    # Report.
    print()
    print("Score-bin signature stats:")
    for bin_lo in sorted(by_bin):
        items = by_bin[bin_lo]
        if not items:
            continue
        n = len(items)
        # median amp per frequency
        amps_by_k = list(zip(*(a for (_, _, a) in items)))
        med = [sorted(a)[len(a) // 2] for a in amps_by_k]
        # Top 5 frequencies by median amp (skip k=0 which is just mean).
        ranked = sorted(enumerate(med[1:], start=1), key=lambda x: -x[1])[:5]
        print(f"  bin>={bin_lo}: n={n}  top freqs (k=DC excluded):")
        for k, m in ranked:
            print(f"    k={k:>2}  median_amp={m:.3f}")

    # Pairwise test: are 460+ boards distinguishable from 440-457 by amp at any frequency?
    print()
    print("Top discriminating frequencies (≥460 vs <460):")
    above_460 = [a for bin_lo in by_bin if bin_lo >= 460 for (_, _, a) in by_bin[bin_lo]]
    below_460 = [a for bin_lo in by_bin if bin_lo < 460 for (_, _, a) in by_bin[bin_lo]]
    if above_460 and below_460:
        n_freq = len(above_460[0])
        diffs = []
        for k in range(1, n_freq):
            ma = sorted(a[k] for a in above_460)[len(above_460) // 2]
            mb = sorted(a[k] for a in below_460)[len(below_460) // 2]
            diffs.append((k, ma - mb, ma, mb))
        diffs.sort(key=lambda x: -abs(x[1]))
        for k, d, ma, mb in diffs[:8]:
            print(f"  k={k:>2}  Δmed={d:>+.3f}  (≥460 med={ma:.3f}  <460 med={mb:.3f})")
    print()
    print(f"n(≥460) = {len(above_460)}, n(<460) = {len(below_460)}")


if __name__ == '__main__':
    main()
