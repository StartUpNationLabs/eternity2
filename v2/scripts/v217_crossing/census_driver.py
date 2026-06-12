#!/usr/bin/env python3
"""Vol-217 census driver: dedup stage-2 snapshots by the H7 state key
(rows 0-7 content == (frontier, pool) up to interior arrangement; we
key on the exact truncated placement, which is sufficient), emit the
unique batch list + multiplicity stats (H8 diversity data).

Usage: census_driver.py SNAP_DIR TRUNC_ROWS OUT_PREFIX
  -> OUT_PREFIX.list (unique files, one per line)
     OUT_PREFIX.dups.tsv (file, multiplicity)
"""
import hashlib
import json
import os
import sys
from collections import Counter


def state_key(path, trunc):
    pl = json.load(open(path))["placement"]
    cells = []
    for i, e in enumerate(pl):
        if e is None:
            continue
        pos = e.get("pos", i)
        if pos // 16 < trunc:
            cells.append((pos, e["piece_id"], e["rotation"]))
    cells.sort()
    return hashlib.md5(json.dumps(cells).encode()).hexdigest(), len(cells)


def main():
    snap_dir, trunc, out_prefix = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    files = sorted(
        os.path.join(snap_dir, f) for f in os.listdir(snap_dir)
        if f.endswith(".json")
    )
    seen = {}
    mult = Counter()
    incomplete = 0
    for f in files:
        key, ncells = state_key(f, trunc)
        if ncells < trunc * 16:
            incomplete += 1
            continue
        mult[key] += 1
        if key not in seen:
            seen[key] = f
    with open(out_prefix + ".list", "w") as fh:
        for key, f in seen.items():
            fh.write(f + "\n")
    with open(out_prefix + ".dups.tsv", "w") as fh:
        fh.write("file\tmultiplicity\n")
        for key, f in seen.items():
            fh.write(f"{f}\t{mult[key]}\n")
    counts = sorted(mult.values(), reverse=True)
    print(f"{len(files)} snapshots -> {len(seen)} unique stage states "
          f"({incomplete} incomplete dropped)")
    print(f"multiplicity: max {counts[0] if counts else 0}, "
          f"dups>1: {sum(1 for c in counts if c > 1)}")


if __name__ == "__main__":
    main()
