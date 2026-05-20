#!/usr/bin/env python3
"""V169 follow-up — do the 'corpus-supported' cells in V155→ALNS 460
match the cells in higher-scoring boards (462, 469)?

If YES: anchoring them and re-optimizing the 191 weak cells should lift
to those scores. (V170 ANCHOR strategy.)

If NO: corpus support doesn't mean correct; the 460 plateau cells are
'plausible but not optimal'. Then we need a different escape strategy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_prior(path):
    d = json.loads(Path(path).read_text())
    return d['matrix']


def load_board(path, size=16):
    d = json.loads(Path(path).read_text())
    pl = d.get('placement', [])
    placement = [None] * (size * size)
    has_pos = any(isinstance(e, dict) and 'pos' in e for e in pl if e is not None)
    for i, entry in enumerate(pl):
        if entry is None:
            continue
        pos = int(entry['pos']) if has_pos else i
        placement[pos] = (int(entry['piece_id']), int(entry['rotation']))
    return d.get('matched', None), placement


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True, help='V155→ALNS 460 (the diversified base)')
    ap.add_argument('--reference', required=True, help='Higher board to check against (462/469)')
    ap.add_argument('--prior',
                    default=str(REPO / 'scripts/v155_prior/prior_matrix_high459.json'))
    args = ap.parse_args()

    prior = load_prior(args.prior)
    src_score, src = load_board(args.source)
    ref_score, ref = load_board(args.reference)

    print(f"Source: {args.source} score={src_score}")
    print(f"Reference: {args.reference} score={ref_score}")
    print()

    # Partition source cells by support.
    weak = []   # s=0
    strong = [] # s>=1
    for pos, ent in enumerate(src):
        if ent is None:
            continue
        pid, rot = ent
        s = prior[pid][pos]
        if s == 0:
            weak.append((pos, pid, rot))
        else:
            strong.append((pos, pid, rot, s))

    print(f"Source partition:")
    print(f"  strong (s>=1): {len(strong)} cells")
    print(f"  weak (s=0):    {len(weak)} cells")
    print()

    # Count how many strong cells match the reference exactly.
    strong_match_pid = 0
    strong_match_pidrot = 0
    for pos, pid, rot, s in strong:
        if ref[pos] is None:
            continue
        rpid, rrot = ref[pos]
        if pid == rpid:
            strong_match_pid += 1
            if rot == rrot:
                strong_match_pidrot += 1

    # Count weak cells that match the reference (curiosity — if many, then
    # the 'weak' label is wrong because the corpus just hasn't seen this
    # high-score basin).
    weak_match_pid = 0
    for pos, pid, rot in weak:
        if ref[pos] is None:
            continue
        rpid, rrot = ref[pos]
        if pid == rpid:
            weak_match_pid += 1

    print(f"Strong cells match reference:")
    print(f"  pid match:     {strong_match_pid}/{len(strong)} ({100*strong_match_pid/max(len(strong),1):.1f}%)")
    print(f"  pid+rot match: {strong_match_pidrot}/{len(strong)} ({100*strong_match_pidrot/max(len(strong),1):.1f}%)")
    print()
    print(f"Weak cells match reference:")
    print(f"  pid match:     {weak_match_pid}/{len(weak)} ({100*weak_match_pid/max(len(weak),1):.1f}%)")
    print()

    # Decisive question: of the cells where source and reference DIFFER,
    # how many were 'strong' (corpus says trust the source) vs 'weak'
    # (corpus has no opinion)?
    diff_strong = 0
    diff_weak = 0
    for pos in range(256):
        if src[pos] is None or ref[pos] is None:
            continue
        if src[pos][0] != ref[pos][0]:
            pid, rot = src[pos]
            s = prior[pid][pos]
            if s == 0:
                diff_weak += 1
            else:
                diff_strong += 1
    total_diff = diff_strong + diff_weak
    print(f"Differences from reference: {total_diff} cells")
    print(f"  on strong cells: {diff_strong} ({100*diff_strong/max(total_diff,1):.1f}%)")
    print(f"  on weak cells:   {diff_weak} ({100*diff_weak/max(total_diff,1):.1f}%)")
    print()
    if diff_strong < 10 and total_diff > 30:
        print("=> ANCHORING strong cells looks SAFE: reference also has those pieces there.")
        print("   V170 ANCHOR strategy is viable.")
    elif diff_strong > total_diff * 0.4:
        print("=> ANCHORING strong cells is RISKY: reference disagrees with many strong cells.")
        print("   Corpus support != correctness; V170 ANCHOR would prematurely lock wrong pieces.")
    else:
        print(f"=> Mixed signal: {diff_strong} strong cells disagree with reference.")


if __name__ == '__main__':
    main()
