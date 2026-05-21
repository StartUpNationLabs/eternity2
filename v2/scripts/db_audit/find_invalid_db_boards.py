#!/usr/bin/env python3
"""Audit all DB boards for duplicate / missing pieces."""
import json
import glob
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main():
    db_dir = REPO / 'database-400-480'
    files = sorted(db_dir.glob('*.json'))
    invalid = []
    valid = 0
    for f in files:
        try:
            b = json.load(open(f))
        except Exception:
            invalid.append({'path': str(f.relative_to(REPO)), 'error': 'load_failed'})
            continue
        pl_raw = b.get('placement') or []
        pl = [None] * 256
        for i, ent in enumerate(pl_raw):
            if ent is None: continue
            pos = ent.get('pos', i)  # fall back to array index for indexed format
            if pos is None or pos >= 256: continue
            pl[pos] = ent.get('piece_id')
        placed = sum(1 for x in pl if x is not None)
        pid_count = Counter(x for x in pl if x is not None)
        dups = {p: c for p, c in pid_count.items() if c > 1}
        missing = sorted(set(range(256)) - set(pid_count.keys()))
        score = b.get('matched', b.get('score', 0))
        if dups or missing or placed != 256:
            invalid.append({
                'path': str(f.relative_to(REPO)),
                'score_claimed': score,
                'placed': placed,
                'unique_pieces': len(pid_count),
                'duplicates': dups,
                'n_missing': len(missing),
                'missing_sample': missing[:8],
            })
        else:
            valid += 1

    print(f"Total: {len(files)} | VALID: {valid} | INVALID: {len(invalid)}")
    if invalid:
        print("\nSample of invalid boards:")
        for r in invalid[:25]:
            print(f"  {r['path']}: score={r['score_claimed']} placed={r['placed']} unique={r['unique_pieces']} dups={r['duplicates']} miss={r['n_missing']}")

    out = REPO / 'scripts/db_audit/invalid_db_boards.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w') as fh:
        json.dump({'total': len(files), 'valid': valid, 'invalid': invalid}, fh, indent=2)
    print(f"\nSaved to {out}")


if __name__ == '__main__':
    main()
