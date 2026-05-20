#!/usr/bin/env python3
"""V190-T3 — repair bf_bw partials by removing cells involved in mismatches.

Greedy: find cells whose removal eliminates the most mismatched edges,
remove them, recompute. Goal: maximize placed-cell-count while keeping
mismatches == 0.

Two strategies:
1. Naive: for each mismatched edge, remove ONE endpoint (the one farther
   from the start, i.e., later in row-major order).
2. Greedy-optimal: for each mismatched edge, remove the endpoint that's
   involved in MORE mismatches (highest-degree).
"""
import argparse
import json
import glob
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v184_lighthouse"))
from build_bidirectional2 import load_pieces, BORDER, is_border

REPO = Path(__file__).resolve().parents[2]


def mismatches(pl, pieces):
    """Returns list of (pos1, pos2, edge_type) for each mismatched edge.
    edge_type: 'EW' or 'NS'."""
    mis = []
    for pos in range(256):
        if pl[pos] is None: continue
        r, c = pos // 16, pos % 16
        pid, rot = pl[pos]
        edges = pieces[(pid, rot)]
        # E-W with right neighbor
        if c < 15 and pl[pos+1] is not None:
            r_pid, r_rot = pl[pos+1]
            if edges[1] != pieces[(r_pid, r_rot)][3] and not is_border(edges[1]):
                mis.append((pos, pos+1, 'EW'))
        # N-S with bottom neighbor
        if r < 15 and pl[pos+16] is not None:
            b_pid, b_rot = pl[pos+16]
            if edges[2] != pieces[(b_pid, b_rot)][0] and not is_border(edges[2]):
                mis.append((pos, pos+16, 'NS'))
    return mis


def repair_greedy(pl, pieces):
    """Greedy: repeat — find cell involved in most mismatches, remove it."""
    pl = list(pl)
    while True:
        mis = mismatches(pl, pieces)
        if not mis: break
        degree = {}
        for p1, p2, _ in mis:
            degree[p1] = degree.get(p1, 0) + 1
            degree[p2] = degree.get(p2, 0) + 1
        # Pick the highest-degree cell. Tie-break: the cell with higher row*16+col (later in scan).
        worst = max(degree, key=lambda p: (degree[p], p))
        pl[worst] = None
    return pl


def board_to_pl(board):
    pl_raw = board['placement']
    pl = [None]*256
    for ent in pl_raw:
        pos = ent.get('pos')
        if pos is None: continue
        pl[pos] = (ent['piece_id'], ent.get('rotation', 0))
    return pl


def pl_to_board_dict(pl, source=''):
    out = []
    for pos, ent in enumerate(pl):
        if ent is not None:
            pid, rot = ent
            out.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
    return {'placement': out, 'source': source}


def score_pl(pl, pieces):
    """E-W + N-S matched-edge count among placed cells."""
    sc = 0
    for pos in range(256):
        if pl[pos] is None: continue
        r, c = pos // 16, pos % 16
        pid, rot = pl[pos]
        edges = pieces[(pid, rot)]
        if c < 15 and pl[pos+1] is not None:
            r_pid, r_rot = pl[pos+1]
            if edges[1] == pieces[(r_pid, r_rot)][3] and not is_border(edges[1]):
                sc += 1
        if r < 15 and pl[pos+16] is not None:
            b_pid, b_rot = pl[pos+16]
            if edges[2] == pieces[(b_pid, b_rot)][0] and not is_border(edges[2]):
                sc += 1
    return sc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in-dir', default='output/vol-190/20260520T202408_1h/partials')
    ap.add_argument('--out-dir', default=None)
    ap.add_argument('--limit', type=int, default=None)
    args = ap.parse_args()

    if args.out_dir is None:
        from datetime import datetime
        stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        args.out_dir = f'output/vol-190/repaired_{stamp}'
    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"out_dir={out_dir}")

    pieces = load_pieces()
    files = sorted(glob.glob(f'{args.in_dir}/*.json'))
    if args.limit:
        files = files[:args.limit]
    print(f"Repairing {len(files)} partials...")

    results = []
    for i, f in enumerate(files):
        try: b = json.load(open(f))
        except: continue
        pl = board_to_pl(b)
        placed_before = sum(1 for x in pl if x is not None)
        mis_before = len(mismatches(pl, pieces))
        pl_repaired = repair_greedy(pl, pieces)
        placed_after = sum(1 for x in pl_repaired if x is not None)
        score_after = score_pl(pl_repaired, pieces)
        results.append({
            'path_in': f,
            'placed_before': placed_before,
            'placed_after': placed_after,
            'mis_before': mis_before,
            'score_after': score_after,
        })
        # Save the repaired partial.
        out_path = out_dir / os.path.basename(f)
        out_data = pl_to_board_dict(pl_repaired, source='bfbw_repaired')
        out_data['placed'] = placed_after
        out_data['score'] = score_after
        with open(out_path, 'w') as fh:
            json.dump(out_data, fh)
        if (i+1) % 500 == 0:
            print(f'  {i+1}/{len(files)} processed')

    print(f'\nProcessed {len(results)} partials')
    print(f'Removed cells (mean): {sum(r["placed_before"] - r["placed_after"] for r in results) / len(results):.1f}')

    # Distribution by placed_after
    from collections import Counter
    by_after = Counter(r['placed_after'] for r in results)
    print(f'\nPlaced-after distribution (top 10):')
    for pa, n in sorted(by_after.items(), reverse=True)[:10]:
        print(f'  placed={pa}: {n} partials')

    # Best by placed_after (then score)
    results.sort(key=lambda r: (-r['placed_after'], -r['score_after']))
    print(f'\nTop 20 repaired partials by placed-after:')
    for r in results[:20]:
        bn = os.path.basename(r['path_in'])
        print(f'  {bn}: {r["placed_before"]}→{r["placed_after"]} (removed {r["placed_before"]-r["placed_after"]}), score={r["score_after"]}, mis_orig={r["mis_before"]}')


if __name__ == '__main__':
    main()
