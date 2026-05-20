#!/usr/bin/env python3
"""Compute per-row color quotas from corpus boards.

corpus_q[r][color] = average count of `color` in row r's S-edges across
the corpus (boards with score >= threshold).

This gives the top-down beam a target distribution for the bottom rows:
it should leave row-12-14 with their corpus-expected color counts.
"""
import argparse
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v184_lighthouse"))
from build_bidirectional2 import load_pieces, BORDER

REPO = Path(__file__).resolve().parents[2]


def s_edge_color(pieces, pid, rot):
    return pieces[(pid, rot)][2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus-dir', default='database-400-480')
    ap.add_argument('--threshold', type=int, default=440)
    ap.add_argument('--out', default='scripts/v186_lighthouse_soft/corpus_color_quota.json')
    args = ap.parse_args()

    pieces = load_pieces()
    corpus_dir = REPO / args.corpus_dir
    boards = list(corpus_dir.glob('*.json'))
    print(f"corpus dir: {corpus_dir}, files: {len(boards)}")

    # Accumulators: per-row color count, count of contributing boards.
    row_color_sum = [defaultdict(int) for _ in range(16)]
    n_boards = 0
    for bp in boards:
        try:
            d = json.load(open(bp))
        except Exception:
            continue
        score = d.get('matched', 0)
        if score < args.threshold:
            continue
        # Support indexed format AND sparse format.
        placement_raw = d.get('placement')
        if placement_raw is None:
            continue
        pl = [None] * 256
        for i, ent in enumerate(placement_raw):
            if ent is None:
                continue
            if isinstance(ent, dict):
                pos = ent.get('pos', i)
                pid = ent['piece_id']
                rot = ent['rotation']
            else:
                continue
            pl[pos] = (pid, rot)
        n_placed = sum(1 for x in pl if x is not None)
        if n_placed < 256:
            continue
        n_boards += 1
        for pos in range(256):
            pid, rot = pl[pos]
            sc = s_edge_color(pieces, pid, rot)
            r = pos // 16
            row_color_sum[r][sc] += 1

    print(f"Eligible corpus (score >= {args.threshold}): {n_boards} boards")
    if n_boards == 0:
        print("ERROR: no eligible corpus boards.")
        return

    # Average per row.
    corpus_q = []
    for r in range(16):
        row_q = {c: cnt / n_boards for c, cnt in row_color_sum[r].items()}
        corpus_q.append(row_q)

    # Sanity: print row-12-14 distribution for a few colors.
    print(f"\nCorpus-empirical color quota for rows 12-14 (top 5 colors by mass):")
    all_colors = set()
    for r in corpus_q:
        all_colors.update(r.keys())
    for c in sorted(all_colors, key=lambda c: -sum(corpus_q[r].get(c, 0) for r in range(16)))[:5]:
        per_row = [corpus_q[r].get(c, 0) for r in range(16)]
        print(f"  color {c} per-row: {[f'{x:.2f}' for x in per_row]}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({
        'threshold': args.threshold,
        'n_boards': n_boards,
        'corpus_q': corpus_q,
    }))
    print(f"\nwrote {args.out}")


if __name__ == '__main__':
    main()
