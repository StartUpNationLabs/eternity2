#!/usr/bin/env python3
"""Surrogate-score the border library to triage before PT.

Per border, we compute features that should correlate with how well an
interior fit can score:

  1. inward_color_histogram: distribution of the 60 inward colors. (For
     a 16x16 border, 56 edges face interior with 1 color each, 4
     corners with 2 inward colors each -- wait, in our encoding,
     corners don't contribute an inward color directly. Let me
     reconsider.)
  2. Actually: each of the 56 edge cells has 1 inward color. The 4
     corners each have 2 inward-relevant colors (the two non-border
     edges face NOT-into-the-board-interior but along the perimeter
     toward adjacent perimeter cells -- corners do NOT directly
     constrain an interior edge). So the border contributes 56
     inward colors that constrain the row-1/row-14/col-1/col-14
     adjacent inner cells.
  3. demand_match: for each inward color c, the border demands K
     adjacent inner pieces' outward face to be color c. The inner
     bag has some total count of color-c edges; we need at least K.
     Score = sum over colors of (demand - supply)^2 if demand > supply
     (penalty for over-demand).

Lower score = better surrogate (fewer infeasibilities expected).

We also compute a sanity baseline: score the corpus 453's border too.
"""

import json
from collections import Counter

PUZZLE = '../data/puzzles/size_16_official_eternity.csv'
LIB = 'output/borders/sample_10k.jsonl'
CORPUS_453 = 'output/night-archive/HISTORIC_first_453_1778557672.json'


def parse_word(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v


def load_pieces(path):
    pieces = []
    with open(path) as f:
        size = int(f.readline().strip())
        for line in f:
            cols = line.strip().split(',')
            if len(cols) < 4: continue
            quad = tuple(parse_word(cols[i]) for i in range(4))
            pieces.append(quad)
    return size, pieces


def rotated(q, r):
    t, ri, b, le = q
    if r == 0: return (t, ri, b, le)
    if r == 1: return (le, t, ri, b)
    if r == 2: return (b, le, t, ri)
    if r == 3: return (ri, b, le, t)


def perimeter_cells(size):
    cells = []
    for x in range(size): cells.append((x, 0))
    for y in range(1, size): cells.append((size-1, y))
    for x in range(size-2, -1, -1): cells.append((x, size-1))
    for y in range(size-2, 0, -1): cells.append((0, y))
    return cells


def inward_color(quad, rot, kind):
    """For each border-cell, what color faces the INTERIOR?
    Edge cells: 1 color. Corner cells: NONE (corners are diagonal to interior — they
    touch interior only at a vertex, not an edge, so contribute 0 inward edges)."""
    e = rotated(quad, rot)
    t, ri, b, le = e
    if kind == 'top': return b
    if kind == 'right': return le
    if kind == 'bottom': return t
    if kind == 'left': return ri
    # corners: don't have an inward edge (diagonal)
    return None


def cell_kind(x, y, sz):
    mx = sz - 1
    if (x,y)==(0,0): return 'TL'
    if (x,y)==(mx,0): return 'TR'
    if (x,y)==(mx,mx): return 'BR'
    if (x,y)==(0,mx): return 'BL'
    if y == 0: return 'top'
    if x == mx: return 'right'
    if y == mx: return 'bottom'
    if x == 0: return 'left'
    return 'inner'


def inner_color_supply(pieces):
    """Multiset of colors available on inner-piece edges (each inner piece
    contributes 4 edges)."""
    cnt = Counter()
    for q in pieces:
        n_border = sum(1 for c in q if c == 0)
        if n_border != 0: continue  # only inner pieces
        for c in q:
            if c != 0:
                cnt[c] += 1
    return cnt


def border_inward_demand(border, cells, pieces):
    """Multiset of inward colors demanded by this border."""
    cnt = Counter()
    for i, (x, y) in enumerate(cells):
        pid, rot = border[i]
        k = cell_kind(x, y, 16)
        ic = inward_color(pieces[pid], rot, k)
        if ic is not None:
            cnt[ic] += 1
    return cnt


def overdemand_score(demand, supply):
    """Sum over colors of max(0, demand - supply). Smaller = better.

    Interpretation: if the border demands more of a color than the inner
    bag has, that's an immediate infeasibility (at least one mismatch
    forced before any inner-search happens). With supply = sum over inner
    pieces edges = 4 × 196 = 784 total edges, but distributed across 22
    colors. Typical color appears ~36 times in supply, ~3 times in
    demand — so the demand-supply gap is usually 0.
    """
    score = 0
    for c, d in demand.items():
        if d > supply.get(c, 0):
            score += d - supply.get(c, 0)
    return score


def main():
    size, pieces = load_pieces(PUZZLE)
    cells = perimeter_cells(size)
    supply = inner_color_supply(pieces)
    print(f'inner-piece color supply (total edges per color):')
    for c in sorted(supply.keys()):
        print(f'  color {c:2d}: {supply[c]:4d}')

    # Score the corpus 453's border for reference
    corpus = json.load(open(CORPUS_453))
    pl = corpus['placement']
    corpus_border = []
    for (x, y) in cells:
        c = pl[y*size + x]
        corpus_border.append((c['piece_id'], c['rotation']))
    corpus_demand = border_inward_demand(corpus_border, cells, pieces)
    corpus_score = overdemand_score(corpus_demand, supply)
    print(f'\nCorpus 453 border inward demand: {dict(sorted(corpus_demand.items()))}')
    print(f'Corpus 453 border over-demand score: {corpus_score}')

    # Score all 10k generated borders
    print(f'\nScoring 10k generated borders...')
    scored = []
    with open(LIB) as f:
        for line in f:
            border = json.loads(line)['border']
            border = [tuple(c) for c in border]
            demand = border_inward_demand(border, cells, pieces)
            score = overdemand_score(demand, supply)
            scored.append((score, border, demand))

    scored.sort(key=lambda x: x[0])
    print(f'\n10k library over-demand-score distribution:')
    sc_vals = [s[0] for s in scored]
    print(f'  min: {sc_vals[0]}  max: {sc_vals[-1]}  median: {sc_vals[5000]}')
    print(f'  mean: {sum(sc_vals)/len(sc_vals):.2f}')
    print(f'  histogram:')
    bins = Counter(sc_vals)
    for k in sorted(bins.keys())[:20]:
        print(f'    {k}: {bins[k]}')

    # Also compute a second feature: how "spread" the inward-color
    # demand is. Borders with concentrated demand on a single color
    # may be harder for the interior to satisfy locally.
    print(f'\nDemand-concentration analysis: top color\'s share of inward demand')
    concentrations = []
    for sc, border, demand in scored:
        if not demand: continue
        total = sum(demand.values())
        top = demand.most_common(1)[0][1]
        concentrations.append(top / total)
    concentrations.sort()
    print(f'  min: {concentrations[0]:.3f}  median: {concentrations[len(concentrations)//2]:.3f}  max: {concentrations[-1]:.3f}')

    # Corpus's concentration
    if corpus_demand:
        ctot = sum(corpus_demand.values())
        ctop = corpus_demand.most_common(1)[0][1]
        print(f'  corpus 453: {ctop/ctot:.3f}  (top color = {corpus_demand.most_common(1)[0][0]})')

    # Combined score: over-demand + entropy-style measure.
    # Lower over-demand + lower concentration = better.
    # Pick top-1000 with smallest over-demand AS FIRST PASS.
    top_k = 1000
    top = scored[:top_k]
    print(f'\nWriting top-{top_k} to output/borders/top_{top_k}_by_surrogate.jsonl')
    with open(f'output/borders/top_{top_k}_by_surrogate.jsonl', 'w') as f:
        for sc, border, demand in top:
            f.write(json.dumps({'border': [list(c) for c in border],
                               'surrogate_score': sc,
                               'inward_demand': dict(demand)}) + '\n')
    print(f'wrote top-{top_k}')


if __name__ == '__main__':
    main()
