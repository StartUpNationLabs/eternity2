#!/usr/bin/env python3
"""V193-T3 — for each high-scoring 238 partial, try multiple repair-choices
and CSP-fill each. Best of all variants per partial.

For an 8-mismatch partial, 2^8 = 256 repair variants. Try all + CSP-fill;
takes a few seconds each. On the top-50 sources, that's 50*256 = 12800
CSP-fills. Each <100ms → ~20 min total.
"""
import argparse
import json
import os
import sys
import glob
import time
import itertools
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


def find_mismatches(pl, pieces):
    """List of (pos1, pos2, edge_type) for each mismatched edge."""
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


def apply_repair_choice(pl, mismatches, choice_bits):
    """choice_bits is iterable of bool — for each mismatched edge, which
    endpoint to remove (False=p1, True=p2). Then remove cells that are
    still touching mismatches recursively until clean."""
    pl = list(pl)
    to_remove = set()
    for i, (p1, p2) in enumerate(mismatches):
        to_remove.add(p2 if choice_bits[i] else p1)
    for pos in to_remove:
        pl[pos] = None
    # Recursively check: did removing those cells leave any other mismatches?
    # (Should not — those mismatches involved the removed cells. But verify and
    # remove additional cells if needed.)
    while True:
        residual = find_mismatches(pl, pieces_global)
        if not residual: break
        for p1, p2 in residual:
            # Remove the later one (heuristic).
            pl[max(p1, p2)] = None
    return pl


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


def csp_fill_greedy(pl, pieces):
    """Unit prop + greedy first-candidate. Returns filled pl."""
    pl = list(pl)
    used = set(p for p, r in (x for x in pl if x is not None))
    while True:
        progress = False
        for pos in range(256):
            if pl[pos] is not None: continue
            cands = candidates_for_cell(pos, pl, pieces, used)
            if len(cands) == 1:
                pid, rot = cands[0]
                pl[pos] = (pid, rot)
                used.add(pid)
                progress = True
        if not progress: break
    # Greedy fill remaining with smallest-domain-first
    while True:
        best = None
        for pos in range(256):
            if pl[pos] is not None: continue
            cands = candidates_for_cell(pos, pl, pieces, used)
            if cands and (best is None or len(cands) < best[1]):
                best = (pos, len(cands), cands)
        if best is None: break
        pos, _, cands = best
        pid, rot = cands[0]
        pl[pos] = (pid, rot)
        used.add(pid)
    return pl


pieces_global = None


def evaluate_repair_variant(pl_source, mismatches, choice_bits):
    """One full variant: apply repair → CSP fill greedy → return (placed, score)."""
    pl_repaired = apply_repair_choice(pl_source, mismatches, choice_bits)
    pl_filled = csp_fill_greedy(pl_repaired, pieces_global)
    placed = sum(1 for x in pl_filled if x is not None)
    score = score_pl(pl_filled, pieces_global)
    return placed, score, pl_filled


def main():
    global pieces_global
    ap = argparse.ArgumentParser()
    ap.add_argument('--in-dir', default='output/vol-190/20260520T202408_1h/partials')
    ap.add_argument('--top-n', type=int, default=50,
                    help='Consider top N source partials by placed-count')
    ap.add_argument('--max-variants', type=int, default=256,
                    help='Max repair variants per source (2^n_mismatches)')
    ap.add_argument('--out-dir', default=None)
    args = ap.parse_args()

    if args.out_dir is None:
        from datetime import datetime
        stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        args.out_dir = f'output/vol-193/multistart_{stamp}'
    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"out_dir={out_dir}")

    pieces_global = load_pieces()

    # Load all sources, sort by placed-count, take top N.
    files = sorted(glob.glob(f'{args.in_dir}/*.json'))
    print(f"Loading {len(files)} sources...")
    sources = []
    for f in files:
        try: d = json.load(open(f))
        except: continue
        pl_raw = d.get('placement') or []
        pl = [None]*256
        for ent in pl_raw:
            pos = ent.get('pos')
            if pos is None: continue
            pl[pos] = (ent['piece_id'], ent.get('rotation', 0))
        placed = sum(1 for x in pl if x is not None)
        sources.append({'path': f, 'pl': pl, 'placed': placed})
    sources.sort(key=lambda s: -s['placed'])
    sources = sources[:args.top_n]
    print(f"Top {len(sources)} sources by placed-count")

    overall_best = (0, 0, None, None, None)  # (placed, score, pl, source, variant)
    t0 = time.time()
    for i, src in enumerate(sources):
        pl_source = src['pl']
        mismatches = find_mismatches(pl_source, pieces_global)
        n_mis = len(mismatches)
        max_explore = max(1, args.max_variants).bit_length() - 1  # log2
        if n_mis > max_explore:
            mismatches = mismatches[:max_explore]
            n_mis = max_explore

        # Try all 2^n_mis variants
        n_variants = 1 << n_mis
        n_variants = min(n_variants, args.max_variants)
        best_local = (0, 0, None, None)
        for v in range(n_variants):
            choice_bits = tuple((v >> i) & 1 for i in range(n_mis))
            placed, score, pl_filled = evaluate_repair_variant(pl_source, mismatches, choice_bits)
            if (placed, score) > (best_local[0], best_local[1]):
                best_local = (placed, score, pl_filled, choice_bits)
        if best_local[0] > overall_best[0] or (best_local[0] == overall_best[0] and best_local[1] > overall_best[1]):
            overall_best = (best_local[0], best_local[1], best_local[2], src['path'], best_local[3])

        if (i+1) % 5 == 0:
            elapsed = time.time() - t0
            print(f'  {i+1}/{len(sources)} src done in {elapsed:.0f}s, current best: placed={overall_best[0]} from {os.path.basename(overall_best[3]) if overall_best[3] else "?"}')

    print(f'\n=== OVERALL BEST ===')
    placed, score, pl_filled, src_path, choice_bits = overall_best
    print(f'placed={placed}, score={score}')
    print(f'source: {src_path}')
    print(f'repair choice_bits: {choice_bits}')

    out_path = out_dir / f'BEST_placed{placed}_score{score}.json'
    with open(out_path, 'w') as fh:
        json.dump(pl_to_board(pl_filled, score=score), fh)
    print(f'saved to {out_path}')


if __name__ == '__main__':
    main()
