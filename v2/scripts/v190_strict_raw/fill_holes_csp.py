#!/usr/bin/env python3
"""V190-T4 — fill holes in repaired partials via deterministic CSP.

Given a repaired partial with holes (cells removed during mismatch repair):
1. For each unplaced cell that has any placed neighbor, compute the set of
   (piece, rotation) candidates that match ALL placed neighbors AND are
   not already used elsewhere.
2. If a cell has exactly one candidate → place it (forced).
3. If multiple cells have multi-candidate options → try CSP/backtracking
   to maximize placed-count with zero mismatches.

Strategy:
- Phase 1 (unit propagation): repeatedly place cells with unique candidate.
- Phase 2 (backtrack): for remaining hole-cells with multiple candidates,
  do a small DFS to maximise placements. Beam-K to bound work.
"""
import argparse
import json
import os
import sys
import glob
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v184_lighthouse"))
from build_bidirectional2 import load_pieces, BORDER, is_border

REPO = Path(__file__).resolve().parents[2]


def board_to_pl(board):
    pl_raw = board['placement']
    pl = [None]*256
    for ent in pl_raw:
        pos = ent.get('pos')
        if pos is None: continue
        pl[pos] = (ent['piece_id'], ent.get('rotation', 0))
    return pl


def pl_to_board(pl, score=0):
    out = []
    for pos, ent in enumerate(pl):
        if ent is not None:
            pid, rot = ent
            out.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
    return {'placement': out, 'placed': len(out), 'matched': score, 'score': score}


def score_pl(pl, pieces):
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


def neighbor_constraints(pos, pl, pieces):
    """Return (n_color, e_color, s_color, w_color), None if neighbor unplaced."""
    r, c = pos // 16, pos % 16
    cons = [None, None, None, None]
    # North: pos - 16
    if r == 0:
        cons[0] = BORDER
    elif pl[pos-16] is not None:
        pid, rot = pl[pos-16]
        cons[0] = pieces[(pid, rot)][2]  # S of north neighbor
    # East: pos + 1
    if c == 15:
        cons[1] = BORDER
    elif pl[pos+1] is not None:
        pid, rot = pl[pos+1]
        cons[1] = pieces[(pid, rot)][3]
    # South: pos + 16
    if r == 15:
        cons[2] = BORDER
    elif pl[pos+16] is not None:
        pid, rot = pl[pos+16]
        cons[2] = pieces[(pid, rot)][0]
    # West: pos - 1
    if c == 0:
        cons[3] = BORDER
    elif pl[pos-1] is not None:
        pid, rot = pl[pos-1]
        cons[3] = pieces[(pid, rot)][1]
    return cons


def candidates_for_cell(pos, pl, pieces, used_pids):
    """All (piece, rot) that satisfy currently-placed neighbors AND aren't used."""
    cons = neighbor_constraints(pos, pl, pieces)
    cands = []
    for pid in range(256):
        if pid in used_pids: continue
        for rot in range(4):
            edges = pieces[(pid, rot)]
            ok = True
            for d, c in enumerate(cons):
                if c is None: continue
                if edges[d] != c:
                    ok = False
                    break
            if ok:
                cands.append((pid, rot))
    return cands


def fill_holes(pl, pieces, verbose=False):
    """Phase 1: unit propagation. Phase 2: greedy fill of remaining holes
    with first-candidate (we want to keep 0-mismatch invariant — any
    candidate guarantees 0 new mismatches by construction)."""
    pl = list(pl)
    used = set(p for p, r in (x for x in pl if x is not None))
    holes = [p for p in range(256) if pl[p] is None]

    iterations = 0
    while True:
        iterations += 1
        # For each hole, compute candidates
        progress = False
        # Phase 1: place cells with unique candidate
        for pos in list(holes):
            if pl[pos] is not None: continue
            cands = candidates_for_cell(pos, pl, pieces, used)
            if len(cands) == 1:
                pid, rot = cands[0]
                pl[pos] = (pid, rot)
                used.add(pid)
                progress = True
                if verbose:
                    print(f'  iter {iterations}: forced cell {pos} with pid={pid}, rot={rot}')
        if not progress:
            break

    # Phase 2: greedy-first-candidate on remaining holes (in scan order).
    # Each candidate by construction matches all placed neighbors → no new mismatches.
    # Choose the hole with fewest candidates first.
    while True:
        candidates_per_hole = []
        for pos in range(256):
            if pl[pos] is not None: continue
            cands = candidates_for_cell(pos, pl, pieces, used)
            candidates_per_hole.append((pos, cands))
        # Filter holes with at least 1 candidate
        candidates_per_hole = [(p, c) for p, c in candidates_per_hole if c]
        if not candidates_per_hole:
            break
        candidates_per_hole.sort(key=lambda x: len(x[1]))
        pos, cands = candidates_per_hole[0]
        pid, rot = cands[0]
        pl[pos] = (pid, rot)
        used.add(pid)
        if verbose:
            print(f'  greedy: cell {pos} pid={pid} rot={rot} (from {len(cands)} candidates)')

    return pl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in-dir', default=None,
                    help='dir of repaired partials (default: latest)')
    ap.add_argument('--out-dir', default=None)
    ap.add_argument('--limit', type=int, default=None)
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()

    if args.in_dir is None:
        # Latest repaired_* dir
        repaired_dirs = sorted(glob.glob('output/vol-190/repaired_*'))
        if not repaired_dirs:
            print("No repaired dirs found. Run repair_remove_mismatches.py first.")
            sys.exit(1)
        args.in_dir = repaired_dirs[-1]
    if args.out_dir is None:
        from datetime import datetime
        stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        args.out_dir = f'output/vol-190/holefilled_{stamp}'
    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"in_dir={args.in_dir}")
    print(f"out_dir={out_dir}")

    pieces = load_pieces()
    files = sorted(glob.glob(f'{args.in_dir}/*.json'))
    if args.limit:
        files = files[:args.limit]
    print(f"Processing {len(files)} repaired partials...")

    results = []
    import time
    t0 = time.time()
    for i, f in enumerate(files):
        try: b = json.load(open(f))
        except: continue
        pl = board_to_pl(b)
        placed_before = sum(1 for x in pl if x is not None)
        score_before = score_pl(pl, pieces)
        pl_filled = fill_holes(pl, pieces, verbose=args.verbose and i < 3)
        placed_after = sum(1 for x in pl_filled if x is not None)
        score_after = score_pl(pl_filled, pieces)
        # Verify no mismatches
        mis = 0
        for pos in range(256):
            if pl_filled[pos] is None: continue
            r, c = pos // 16, pos % 16
            pid, rot = pl_filled[pos]
            edges = pieces[(pid, rot)]
            if c < 15 and pl_filled[pos+1] is not None:
                r_pid, r_rot = pl_filled[pos+1]
                if edges[1] != pieces[(r_pid, r_rot)][3] and not is_border(edges[1]):
                    mis += 1
            if r < 15 and pl_filled[pos+16] is not None:
                b_pid, b_rot = pl_filled[pos+16]
                if edges[2] != pieces[(b_pid, b_rot)][0] and not is_border(edges[2]):
                    mis += 1
        results.append({
            'path_in': f,
            'placed_before': placed_before,
            'placed_after': placed_after,
            'score_before': score_before,
            'score_after': score_after,
            'mis_after': mis,
        })
        # Save
        out_path = out_dir / os.path.basename(f)
        with open(out_path, 'w') as fh:
            json.dump(pl_to_board(pl_filled, score=score_after), fh)
        if (i+1) % 500 == 0:
            elapsed = time.time() - t0
            print(f'  {i+1}/{len(files)} processed ({elapsed:.0f}s)')

    print(f'\nProcessed {len(results)} partials')

    # Stats
    gained = [r['placed_after'] - r['placed_before'] for r in results]
    print(f'Cells gained back (mean): {sum(gained)/len(gained):.2f}')
    print(f'Cells gained max: {max(gained)}')

    from collections import Counter
    by_after = Counter(r['placed_after'] for r in results)
    print(f'\nPlaced-after distribution (top 15):')
    for pa, n in sorted(by_after.items(), reverse=True)[:15]:
        print(f'  placed={pa}: {n} partials')

    # Best by placed_after then score
    results.sort(key=lambda r: (-r['placed_after'], -r['score_after']))
    print(f'\nTop 20 hole-filled partials:')
    for r in results[:20]:
        bn = os.path.basename(r['path_in'])
        gain = r['placed_after'] - r['placed_before']
        print(f'  {bn}: {r["placed_before"]}→{r["placed_after"]} (gained +{gain}), score={r["score_after"]}, mis={r["mis_after"]}')


if __name__ == '__main__':
    main()
