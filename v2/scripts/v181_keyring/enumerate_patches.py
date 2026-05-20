#!/usr/bin/env python3
"""V181 KEYRING — enumerate 2x2 PERMITTED patches in corpus boards.

For each 2x2 patch position in each corpus board, record the 4-tuple
(piece_id, rotation) × 4 cells. Cluster by canonical form.

Question: how many UNIQUE 2x2 patches appear in the corpus? If small
(~10k), this is a viable Wang tile dictionary.

For ≥460 boards specifically: what patches appear there? Are they a
strict subset of <460 patches?
"""
from __future__ import annotations
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_board(path, size=16):
    d = json.loads(Path(path).read_text())
    pl = d.get('placement', [])
    placement = [None] * (size * size)
    has_pos = any(isinstance(e, dict) and 'pos' in e for e in pl if e is not None)
    for i, entry in enumerate(pl):
        if entry is None: continue
        pos = int(entry['pos']) if has_pos else i
        placement[pos] = (int(entry['piece_id']), int(entry['rotation']))
    return d.get('matched'), placement


def patches_in(placement, size=16):
    """Return list of all 2x2 patches as tuples ((p_tl, r_tl), (p_tr, r_tr),
    (p_bl, r_bl), (p_br, r_br)) where positions follow row-major reading."""
    out = []
    for y in range(size - 1):
        for x in range(size - 1):
            tl = placement[y * size + x]
            tr = placement[y * size + x + 1]
            bl = placement[(y + 1) * size + x]
            br = placement[(y + 1) * size + x + 1]
            if tl and tr and bl and br:
                out.append((tl, tr, bl, br))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db-dir', default='database-400-480')
    args = ap.parse_args()

    db = Path(REPO / args.db_dir)
    boards = sorted(db.glob('*.json'))
    print(f"Loading {len(boards)} corpus boards")

    # Tally patches by score-tier.
    patch_high = Counter()  # ≥460
    patch_low = Counter()   # <460
    patch_all = Counter()
    n_high = 0; n_low = 0
    for bp in boards:
        try:
            score, pl = load_board(bp)
        except Exception:
            continue
        if score is None: continue
        if not all(p is not None for p in pl): continue
        patches = patches_in(pl)
        for p in patches:
            patch_all[p] += 1
            if score >= 460:
                patch_high[p] += 1
            else:
                patch_low[p] += 1
        if score >= 460:
            n_high += 1
        else:
            n_low += 1

    print(f"n_high (≥460) = {n_high}, n_low (<460) = {n_low}")
    print(f"unique patches all:  {len(patch_all)}")
    print(f"unique patches high: {len(patch_high)}")
    print(f"unique patches low:  {len(patch_low)}")
    print(f"patches only in high (NOT in low): {len(set(patch_high) - set(patch_low))}")
    print(f"patches only in low  (NOT in high): {len(set(patch_low) - set(patch_high))}")
    print(f"patches in both: {len(set(patch_high) & set(patch_low))}")
    print()

    # Average patches per board.
    if n_high:
        avg_h = sum(patch_high.values()) / n_high
        print(f"avg patches/board in ≥460: {avg_h:.0f}")
    if n_low:
        avg_l = sum(patch_low.values()) / n_low
        print(f"avg patches/board in <460: {avg_l:.0f}")
    # Note: each 16x16 board has 15×15 = 225 patches.
    print(f"(each 16×16 board has 15²=225 patches)")
    print()

    # Most common patches in ≥460 only.
    print("Top 10 patches in ≥460 (occurrence count):")
    for p, n in patch_high.most_common(10):
        marker = "" if p in patch_low else " *NOVEL TO HIGH*"
        # Compact representation
        tl, tr, bl, br = p
        ptag = f"({tl[0]:>3}r{tl[1]}|{tr[0]:>3}r{tr[1]})/({bl[0]:>3}r{bl[1]}|{br[0]:>3}r{br[1]})"
        print(f"  n={n:>3} {ptag}{marker}")


if __name__ == '__main__':
    main()
