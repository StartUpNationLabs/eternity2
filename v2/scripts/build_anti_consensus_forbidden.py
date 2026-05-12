#!/usr/bin/env python3
"""Build a forbidden-edge list = edges that MATCH on (almost) every
top-family board. Penalizing these in PT forces exploration AWAY
from the 452-class basin.

Per NE2 forbidden format: list of [["h"|"v", pos], ...].
"""

import glob, json
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


def rotate_quad(q, rot):
    t, r, b, l = q
    if rot == 0: return (t, r, b, l)
    if rot == 1: return (l, t, r, b)
    if rot == 2: return (b, l, t, r)
    if rot == 3: return (r, b, l, t)


def edge_signatures(pl, pieces):
    """For each interior edge, return the COLOR if matched, else None."""
    sigs = {}
    for y in range(H):
        for x in range(W):
            pos = y*W+x
            if not pl[pos]: continue
            edges = rotate_quad(pieces[pl[pos]['piece_id']], pl[pos]['rotation'])
            if x+1 < W and pl[pos+1]:
                nedges = rotate_quad(pieces[pl[pos+1]['piece_id']], pl[pos+1]['rotation'])
                if edges[1] == nedges[3] and edges[1] != BORDER:
                    sigs[('h', pos)] = edges[1]
            if y+1 < H and pl[pos+W]:
                nedges = rotate_quad(pieces[pl[pos+W]['piece_id']], pl[pos+W]['rotation'])
                if edges[2] == nedges[0] and edges[2] != BORDER:
                    sigs[('v', pos)] = edges[2]
    return sigs


def main():
    pieces = load_pieces('../data/puzzles/size_16_official_eternity.csv')
    boards = []
    for path in sorted(glob.glob('output/archive/*.json') + glob.glob('output/*.json')):
        try: j = json.load(open(path))
        except: continue
        if not isinstance(j, dict): continue
        sc = j.get('score', {})
        if isinstance(sc, int): score = sc
        elif isinstance(sc, dict): score = sc.get('matched_edges', 0)
        else: continue
        if score < 449: continue
        if not j.get('placement'): continue
        if len(j['placement']) != W*H: continue
        boards.append({'path': path, 'score': score, 'pl': j['placement']})

    print(f'corpus ≥449 with placement: {len(boards)}')

    # For each interior edge, count how often it's MATCHED across the corpus.
    edge_match_count = Counter()
    for b in boards:
        sigs = edge_signatures(b['pl'], pieces)
        for edge in sigs:
            edge_match_count[edge] += 1

    # Edges matched in ≥X% of boards = "consensus edges".
    n = len(boards)
    print(f'\nedges with ≥95% consensus match: '
          f'{sum(1 for c in edge_match_count.values() if c >= 0.95*n)}')
    print(f'edges with ≥90% consensus match: '
          f'{sum(1 for c in edge_match_count.values() if c >= 0.90*n)}')
    print(f'edges with ≥80% consensus match: '
          f'{sum(1 for c in edge_match_count.values() if c >= 0.80*n)}')

    # Pick top-K most-consensus edges. These are the "strong basin
    # signature" edges. Forbidding them = anti-consensus.
    threshold = 0.95
    top_consensus = [edge for edge, c in edge_match_count.items() if c >= threshold * n]
    print(f'\ntop-consensus edges (≥{int(threshold*100)}% match rate): {len(top_consensus)}')

    # But wait — at 95% almost every "matched" edge is in top consensus,
    # because the boards are similar. We want the edges where SPECIFIC
    # COLORS are agreed on. Use color-frequency.

    # For each edge, count distribution of MATCHED colors across corpus.
    edge_color_dist = defaultdict(Counter)
    for b in boards:
        sigs = edge_signatures(b['pl'], pieces)
        for edge, color in sigs.items():
            edge_color_dist[edge][color] += 1

    # "Strong consensus" = a single color appears >= 95% of the time AT THIS EDGE.
    # These are edges whose color is "structurally fixed" across the basin.
    strong_edges = []
    for edge, dist in edge_color_dist.items():
        modal_color, modal_n = dist.most_common(1)[0]
        if modal_n >= 0.95 * n:
            strong_edges.append(edge)
    print(f'edges with ≥95% same-color consensus: {len(strong_edges)}')

    # Limit to top-30 most-consensus to fit forbidden.rs's u64 bitset.
    edge_with_count = [(edge, edge_color_dist[edge].most_common(1)[0][1]) for edge in strong_edges]
    edge_with_count.sort(key=lambda x: -x[1])
    top_30 = [list(edge) for edge, _ in edge_with_count[:30]]

    out_path = 'data/anti_consensus_top30.json'
    json.dump(top_30, open(out_path, 'w'), indent=2)
    print(f'\nwrote {out_path} with {len(top_30)} edges')
    print(f'sample: {top_30[:5]}')


if __name__ == '__main__':
    main()
