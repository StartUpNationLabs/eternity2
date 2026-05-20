#!/usr/bin/env python3
"""V193-T1 — CSP-fill with DFS backtracking on remaining holes.

After unit propagation places all forced cells, run a DFS on the
remaining holes (with candidate sets) to maximise placement count
while keeping 0 mismatches.

DFS strategy:
- Variable ordering: smallest-domain-first (most-constrained-variable).
- Value ordering: try candidates in order of degree (how many other
  hole-cells they help unblock). Skipped if too expensive; default
  iterate.
- Pruning: at each step, propagate new forced placements (unit
  propagation cascade).
"""
import argparse
import json
import os
import sys
import glob
import time
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
    r, c = pos // 16, pos % 16
    cons = [None, None, None, None]
    if r == 0: cons[0] = BORDER
    elif pl[pos-16] is not None:
        pid, rot = pl[pos-16]
        cons[0] = pieces[(pid, rot)][2]
    if c == 15: cons[1] = BORDER
    elif pl[pos+1] is not None:
        pid, rot = pl[pos+1]
        cons[1] = pieces[(pid, rot)][3]
    if r == 15: cons[2] = BORDER
    elif pl[pos+16] is not None:
        pid, rot = pl[pos+16]
        cons[2] = pieces[(pid, rot)][0]
    if c == 0: cons[3] = BORDER
    elif pl[pos-1] is not None:
        pid, rot = pl[pos-1]
        cons[3] = pieces[(pid, rot)][1]
    return cons


def candidates_for_cell(pos, pl, pieces, used_pids):
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


def unit_propagate(pl, used, pieces, holes):
    """Returns (new_pl, new_used, new_holes) after exhaustive unit propagation."""
    pl = list(pl)
    used = set(used)
    holes = set(holes)
    while True:
        progress = False
        for pos in list(holes):
            cands = candidates_for_cell(pos, pl, pieces, used)
            if len(cands) == 1:
                pid, rot = cands[0]
                pl[pos] = (pid, rot)
                used.add(pid)
                holes.discard(pos)
                progress = True
        if not progress: break
    return pl, used, holes


# Global best-placed tracker for DFS
class DFSState:
    __slots__ = ('best_pl', 'best_placed', 'deadline')


def dfs_fill(pl, used, pieces, holes, state, depth_budget=15):
    """DFS to maximise placed cells. holes is set of unplaced positions.
    Returns nothing; updates state.best_pl, state.best_placed in place."""
    if time.time() > state.deadline: return

    placed_count = 256 - len(holes)
    if placed_count > state.best_placed:
        state.best_placed = placed_count
        state.best_pl = list(pl)

    if not holes or depth_budget == 0:
        return

    # Pick MCV (smallest domain).
    cands_by_hole = []
    for pos in holes:
        cands = candidates_for_cell(pos, pl, pieces, used)
        cands_by_hole.append((pos, cands))
    cands_by_hole.sort(key=lambda x: len(x[1]))

    # Drop holes with 0 candidates (can't be filled now).
    cands_by_hole = [(p, c) for p, c in cands_by_hole if c]
    if not cands_by_hole:
        return

    # Branch on smallest-domain hole.
    pos, cands = cands_by_hole[0]
    # Cap candidates explored (avoid blow-up).
    for pid, rot in cands[:8]:
        pl[pos] = (pid, rot)
        used.add(pid)
        holes_new = holes - {pos}
        # Cheap propagation: any neighbor hole that now has a single candidate?
        # Skip full propagation each branch; rely on MCV in recursion.
        dfs_fill(pl, used, pieces, holes_new, state, depth_budget - 1)
        # Backtrack
        pl[pos] = None
        used.discard(pid)
        if time.time() > state.deadline: return


def fill_holes_with_dfs(pl_in, pieces, time_budget_s=2.0):
    pl = list(pl_in)
    used = set(p for p, r in (x for x in pl if x is not None))
    holes = set(p for p in range(256) if pl[p] is None)

    # Phase 1: unit propagation.
    pl, used, holes = unit_propagate(pl, used, pieces, holes)

    # Phase 2: DFS on remaining holes.
    state = DFSState()
    state.best_pl = list(pl)
    state.best_placed = 256 - len(holes)
    state.deadline = time.time() + time_budget_s

    pl_work = list(pl)
    used_work = set(used)
    holes_work = set(holes)

    dfs_fill(pl_work, used_work, pieces, holes_work, state, depth_budget=20)

    return state.best_pl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in-dir', default=None,
                    help='dir of repaired partials (default: latest)')
    ap.add_argument('--out-dir', default=None)
    ap.add_argument('--limit', type=int, default=None)
    ap.add_argument('--time-budget', type=float, default=1.0)
    args = ap.parse_args()

    if args.in_dir is None:
        repaired_dirs = sorted(glob.glob('output/vol-190/repaired_*'))
        if not repaired_dirs:
            print("No repaired dirs.")
            sys.exit(1)
        args.in_dir = repaired_dirs[-1]
    if args.out_dir is None:
        from datetime import datetime
        stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        args.out_dir = f'output/vol-193/holefilled_dfs_{stamp}'
    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"in_dir={args.in_dir}")
    print(f"out_dir={out_dir}")
    print(f"time_budget_per_partial={args.time_budget}s")

    pieces = load_pieces()
    files = sorted(glob.glob(f'{args.in_dir}/*.json'))
    if args.limit:
        files = files[:args.limit]
    print(f"Processing {len(files)} partials...")

    results = []
    t0 = time.time()
    for i, f in enumerate(files):
        try: b = json.load(open(f))
        except: continue
        pl = board_to_pl(b)
        placed_before = sum(1 for x in pl if x is not None)
        pl_filled = fill_holes_with_dfs(pl, pieces, time_budget_s=args.time_budget)
        placed_after = sum(1 for x in pl_filled if x is not None)
        score_after = score_pl(pl_filled, pieces)
        # Verify
        mis = 0
        for pos in range(256):
            if pl_filled[pos] is None: continue
            r, c = pos // 16, pos % 16
            pid, rot = pl_filled[pos]
            edges = pieces[(pid, rot)]
            if c < 15 and pl_filled[pos+1] is not None:
                if edges[1] != pieces[pl_filled[pos+1]][3] and not is_border(edges[1]): mis += 1
            if r < 15 and pl_filled[pos+16] is not None:
                if edges[2] != pieces[pl_filled[pos+16]][0] and not is_border(edges[2]): mis += 1
        results.append({
            'path_in': f,
            'placed_before': placed_before,
            'placed_after': placed_after,
            'score_after': score_after,
            'mis': mis,
        })
        out_path = out_dir / os.path.basename(f)
        with open(out_path, 'w') as fh:
            json.dump(pl_to_board(pl_filled, score=score_after), fh)
        if (i+1) % 500 == 0:
            elapsed = time.time() - t0
            rate = (i+1)/elapsed
            eta = (len(files) - i - 1) / rate
            print(f'  {i+1}/{len(files)} done ({elapsed:.0f}s, ETA {eta:.0f}s)')

    print(f'\nProcessed {len(results)} partials')

    from collections import Counter
    by_after = Counter(r['placed_after'] for r in results)
    print(f'\nPlaced-after distribution (top 15):')
    for pa, n in sorted(by_after.items(), reverse=True)[:15]:
        print(f'  placed={pa}: {n}')

    results.sort(key=lambda r: (-r['placed_after'], -r['score_after']))
    print(f'\nTop 20 DFS-filled partials:')
    for r in results[:20]:
        bn = os.path.basename(r['path_in'])
        print(f'  {bn}: {r["placed_before"]}→{r["placed_after"]}, score={r["score_after"]}, mis={r["mis"]}')


if __name__ == '__main__':
    main()
