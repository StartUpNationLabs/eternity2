#!/usr/bin/env python3
"""V189-T1 — find corner-perms with ≥458 boards but NO ≥460 boards in DB."""
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main():
    cp_to_max = defaultdict(int)
    cp_to_count = defaultdict(int)
    all_boards = list((REPO / 'database-400-480').glob('*.json'))
    # Also pull any RECORD_46* from output/.
    for d in (REPO / 'output').rglob('RECORD_46*.json'):
        all_boards.append(d)
    print(f"scanning {len(all_boards)} board files")
    for bp in all_boards:
        try:
            d = json.load(open(bp))
        except Exception:
            continue
        score = d.get('matched', 0)
        if score < 458: continue
        pl_raw = d.get('placement')
        if not pl_raw: continue
        pl = [None] * 256
        for i, ent in enumerate(pl_raw):
            if isinstance(ent, dict):
                pos = ent.get('pos', i)
                pl[pos] = ent.get('piece_id', ent.get('pid'))
        # Corner perm = (pid at 0, 15, 240, 255)
        corners = []
        for p in [0, 15, 240, 255]:
            if pl[p] is None: break
            corners.append(pl[p])
        if len(corners) != 4: continue
        cp = tuple(corners)
        cp_to_max[cp] = max(cp_to_max[cp], score)
        cp_to_count[cp] += 1

    print(f"Total cps with ≥458 in DB: {len(cp_to_max)}")
    print(f"\nCPS WITH ≥460 (already explored):")
    explored = [cp for cp, m in cp_to_max.items() if m >= 460]
    for cp in sorted(explored, key=lambda c: -cp_to_max[c]):
        print(f"  cp={cp}  max={cp_to_max[cp]}  count={cp_to_count[cp]}")
    print(f"\nCPS WITH ≥458 BUT NO ≥460 (target):")
    unexplored = [cp for cp, m in cp_to_max.items() if m < 460]
    for cp in sorted(unexplored, key=lambda c: -cp_to_max[c]):
        print(f"  cp={cp}  max={cp_to_max[cp]}  count={cp_to_count[cp]}")
    print(f"\nSummary: {len(unexplored)} CORTEZ target cps")

    # Save target cps
    out = REPO / 'scripts/v189_cortez/target_cps.json'
    out.write_text(json.dumps({'targets': [list(c) for c in unexplored]}))
    print(f"saved {out}")


if __name__ == '__main__':
    main()
