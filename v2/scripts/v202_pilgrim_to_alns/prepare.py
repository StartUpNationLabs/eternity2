#!/usr/bin/env python3
"""V202 Stage 1: process PILGRIM corpus → repair → CSP-fill → rank.

Output:
- output/vol-202/<stamp>/repaired_filled/{*.json}   (all processed)
- output/vol-202/<stamp>/top50.json                 (manifest of top 50 by placed+score)
- output/vol-202/<stamp>/_meta.log                  (summary)
"""
import argparse
import glob
import json
import os
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts/v184_lighthouse"))
from build_bidirectional2 import load_pieces, BORDER, is_border

HINTS = {135: 138, 210: 180, 34: 207, 221: 248, 45: 254}


def board_to_pl(board):
    pl = [None] * 256
    for i, ent in enumerate(board.get('placement', []) or []):
        if ent is None: continue
        pos = ent.get('pos', i)
        if pos is None or pos >= 256: continue
        pl[pos] = (ent.get('piece_id'), ent.get('rotation', 0))
    return pl


def pl_to_board(pl, score=0):
    out = []
    for pos, ent in enumerate(pl):
        if ent is not None:
            pid, rot = ent
            out.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
    return {'placement': out, 'placed': len(out), 'matched': score, 'score': score}


def validate(pl):
    pid_count = Counter(p for p, r in (x for x in pl if x is not None))
    dups = {p: c for p, c in pid_count.items() if c > 1}
    missing = set(range(256)) - set(pid_count.keys())
    return dups, missing


def find_mismatches(pl, pieces):
    mis = []
    for pos in range(256):
        if pl[pos] is None: continue
        r, c = pos // 16, pos % 16
        pid, rot = pl[pos]
        edges = pieces[(pid, rot)]
        if c < 15 and pl[pos+1] is not None:
            r_pid, r_rot = pl[pos+1]
            if edges[1] != pieces[(r_pid, r_rot)][3] and not is_border(edges[1]):
                mis.append((pos, pos+1))
        if r < 15 and pl[pos+16] is not None:
            b_pid, b_rot = pl[pos+16]
            if edges[2] != pieces[(b_pid, b_rot)][0] and not is_border(edges[2]):
                mis.append((pos, pos+16))
    return mis


def repair_greedy(pl, pieces, protected_positions):
    """Remove cells participating in mismatches, but never remove cells in protected_positions (the 5 hint positions)."""
    pl = list(pl)
    while True:
        mis = find_mismatches(pl, pieces)
        if not mis: break
        degree = {}
        for p1, p2 in mis:
            degree[p1] = degree.get(p1, 0) + 1
            degree[p2] = degree.get(p2, 0) + 1
        # Pick highest-degree non-protected cell
        candidates = [(d, p) for p, d in degree.items() if p not in protected_positions]
        if not candidates:
            # All mismatches involve protected cells; have to remove a protected cell partner
            # In practice this means the partial is irreparable while keeping hints.
            # Remove the highest-degree cell regardless to keep loop terminating, but mark as failed.
            return None
        candidates.sort(reverse=True)
        _, worst = candidates[0]
        pl[worst] = None
    return pl


def neighbor_constraints(pos, pl, pieces):
    r, c = pos // 16, pos % 16
    cons = [None, None, None, None]
    if r == 0: cons[0] = BORDER
    elif pl[pos-16] is not None:
        cons[0] = pieces[pl[pos-16]][2]
    if c == 15: cons[1] = BORDER
    elif pl[pos+1] is not None:
        cons[1] = pieces[pl[pos+1]][3]
    if r == 15: cons[2] = BORDER
    elif pl[pos+16] is not None:
        cons[2] = pieces[pl[pos+16]][0]
    if c == 0: cons[3] = BORDER
    elif pl[pos-1] is not None:
        cons[3] = pieces[pl[pos-1]][1]
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


def csp_fill_greedy(pl, pieces):
    pl = list(pl)
    used = set(p for p, r in (x for x in pl if x is not None))
    # Unit prop
    while True:
        prog = False
        for pos in range(256):
            if pl[pos] is not None: continue
            c = candidates_for_cell(pos, pl, pieces, used)
            if len(c) == 1:
                pl[pos] = c[0]
                used.add(c[0][0])
                prog = True
        if not prog: break
    # Greedy MCV
    while True:
        best = None
        for pos in range(256):
            if pl[pos] is not None: continue
            c = candidates_for_cell(pos, pl, pieces, used)
            if c and (best is None or len(c) < best[1]):
                best = (pos, len(c), c)
        if best is None: break
        pl[best[0]] = best[2][0]
        used.add(best[2][0][0])
    return pl


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in-dir', default=None)
    ap.add_argument('--top-n', type=int, default=20)
    args = ap.parse_args()

    if args.in_dir is None:
        latest = sorted(glob.glob(str(REPO / 'output/vol-195/relaunch_*')))[-1]
        args.in_dir = f'{latest}/corpus'
    in_dir = Path(args.in_dir)
    stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
    out_dir = REPO / f'output/vol-202/{stamp}'
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'repaired_filled').mkdir(exist_ok=True)

    meta = open(out_dir / '_meta.log', 'w')
    meta.write(f'in_dir={in_dir}\n')
    meta.write(f'out_dir={out_dir}\n')

    pieces = load_pieces()
    files = sorted(glob.glob(str(in_dir / '*.json')))
    print(f'Processing {len(files)} PILGRIM corpus files...')
    meta.write(f'total_files={len(files)}\n')

    protected = set(HINTS.keys())
    results = []
    n_invalid = 0
    n_irreparable = 0
    n_hints_lost = 0
    for i, f in enumerate(files):
        try:
            b = json.load(open(f))
        except:
            continue
        pl = board_to_pl(b)
        dups, missing = validate(pl)
        if dups or missing:
            n_invalid += 1
            continue
        # Verify hints
        hint_hits = sum(1 for hp, he in HINTS.items() if pl[hp] and pl[hp][0] == he)
        if hint_hits < 5:
            n_hints_lost += 1
            continue
        # Repair
        pl_rep = repair_greedy(pl, pieces, protected)
        if pl_rep is None:
            n_irreparable += 1
            continue
        # CSP-fill
        pl_filled = csp_fill_greedy(pl_rep, pieces)
        # Final validation
        dups, missing = validate(pl_filled)
        if dups or missing:
            continue
        placed = sum(1 for x in pl_filled if x is not None)
        score = score_pl(pl_filled, pieces)
        final_hint_hits = sum(1 for hp, he in HINTS.items() if pl_filled[hp] and pl_filled[hp][0] == he)
        out_path = out_dir / 'repaired_filled' / os.path.basename(f)
        with open(out_path, 'w') as fh:
            json.dump(pl_to_board(pl_filled, score=score), fh)
        results.append({
            'source': os.path.basename(f),
            'placed': placed,
            'score': score,
            'hints': final_hint_hits,
            'out_path': str(out_path.relative_to(REPO)),
        })
        if (i + 1) % 200 == 0:
            print(f'  {i+1}/{len(files)} processed')

    meta.write(f'n_invalid={n_invalid}\nn_hints_lost={n_hints_lost}\nn_irreparable={n_irreparable}\nn_valid={len(results)}\n')
    print(f'\nTotal processed: {len(results)}')
    print(f'  invalid (dup/missing): {n_invalid}')
    print(f'  hints lost: {n_hints_lost}')
    print(f'  irreparable: {n_irreparable}')

    # Distribution
    from collections import Counter
    dist = Counter(r['placed'] for r in results)
    print(f'\nPlaced distribution (top 15):')
    for p, n in sorted(dist.items(), reverse=True)[:15]:
        print(f'  placed={p}: {n}')

    # Top N
    results.sort(key=lambda r: (-r['placed'], -r['score']))
    top = results[:args.top_n]
    manifest_path = out_dir / 'top_manifest.json'
    with open(manifest_path, 'w') as fh:
        json.dump(top, fh, indent=2)
    print(f'\nTop {len(top)} saved to {manifest_path}')
    print(f'Top 10:')
    for r in top[:10]:
        print(f'  {r["source"]}: placed={r["placed"]} score={r["score"]} hints={r["hints"]}/5')

    meta.write(f'top_manifest={manifest_path}\n')
    meta.close()


if __name__ == '__main__':
    main()
