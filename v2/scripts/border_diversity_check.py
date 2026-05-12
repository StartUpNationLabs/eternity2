#!/usr/bin/env python3
"""Quantify diversity of the 10k generated borders.

Compare per-cell agreement across the new border library vs. the corpus.
A truly diverse library should have per-cell agreement near random
(corner cells: 1/24 = 4.2%; edge cells: ~1/?? — depends on color
constraints).
"""

import json
from collections import Counter

import sys
LIB = sys.argv[1] if len(sys.argv) > 1 else 'output/borders/sample_100k.jsonl'

def main():
    rows = []
    with open(LIB) as f:
        for line in f:
            rows.append(json.loads(line)['border'])
    n = len(rows)
    n_cells = len(rows[0])
    print(f'borders: {n}, cells/border: {n_cells}')

    # Per-cell modal frequency
    agreements = []
    distinct_per_cell = []
    for i in range(n_cells):
        col = [tuple(r[i]) for r in rows]
        cnt = Counter(col)
        modal = cnt.most_common(1)[0][1]
        agreements.append(modal / n)
        distinct_per_cell.append(len(cnt))

    print(f'\nGenerated library (n={n}):')
    print(f'  mean per-cell agreement (modal/n): {sum(agreements)/n_cells:.3f}')
    print(f'  cells with >=80% agreement:        {sum(1 for a in agreements if a >= 0.8)}')
    print(f'  cells with >=50% agreement:        {sum(1 for a in agreements if a >= 0.5)}')
    print(f'  cells with >=20% agreement:        {sum(1 for a in agreements if a >= 0.2)}')
    print(f'  mean distinct (pid,rot)/cell:       {sum(distinct_per_cell)/n_cells:.1f}')
    print(f'  min/max distinct/cell:              {min(distinct_per_cell)}/{max(distinct_per_cell)}')
    print(f'  cell-0 (TL corner) distinct:         {distinct_per_cell[0]} (max possible: 4)')
    print(f'  cell-15 (TR corner) distinct:        {distinct_per_cell[15]} (max possible: 4)')
    print(f'  cell-30 (BR corner) distinct:        {distinct_per_cell[30]}')
    print(f'  cell-45 (BL corner) distinct:        {distinct_per_cell[45]}')

    print(f'\nReference (corpus boards >=449, n=28):')
    print(f'  mean per-cell agreement: 0.862  (BORDER-1 finding)')
    print(f'  unique borders: 3')

    # Pairwise overlap distribution: random sample of 1000 pairs
    import random
    random.seed(42)
    overlaps = []
    for _ in range(1000):
        a, b = random.sample(rows, 2)
        same = sum(1 for x, y in zip(a, b) if x == y)
        overlaps.append(same / n_cells)
    overlaps.sort()
    print(f'\nPairwise overlap (1000 random pairs):')
    print(f'  mean: {sum(overlaps)/len(overlaps):.3f}')
    print(f'  median: {overlaps[500]:.3f}')
    print(f'  min: {overlaps[0]:.3f}  max: {overlaps[-1]:.3f}')
    print(f'  10th pct: {overlaps[100]:.3f}  90th pct: {overlaps[900]:.3f}')

    # Sanity: how many pairs would be ≥80% overlap (= same basin in the corpus sense)?
    near_dups = sum(1 for o in overlaps if o >= 0.8)
    print(f'  pairs with >=80% overlap: {near_dups}/1000')

    # How many DISTINCT corner-quads represented?
    corner_sigs = Counter((tuple(r[0]), tuple(r[15]), tuple(r[30]), tuple(r[45])) for r in rows)
    print(f'\nDistinct corner-quadruples in library: {len(corner_sigs)} (max possible: 24)')
    print(f'  most common corner-quad: {corner_sigs.most_common(1)[0][1]} occurrences')
    print(f'  least common corner-quad: {corner_sigs.most_common()[-1][1]} occurrences')


if __name__ == '__main__':
    main()
