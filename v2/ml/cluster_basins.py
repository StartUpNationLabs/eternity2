"""Vol-35 T1a — cluster vanilla_fast snapshots from a thread-id sweep
into basin families.

A basin family is a set of snapshots that share an early-prefix
(first ~80 cells identical). The sweep produces many snapshots from
many thread_ids; this script identifies the distinct early-prefix
clusters.

Usage: python ml/cluster_basins.py [sweep_root]
"""

from __future__ import annotations

import glob
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "output/vol-35/sweep"
    files = sorted(glob.glob(f"{root}/offset_*/*.json"))
    print(f"[load] {len(files)} snapshots from {root}")
    if not files:
        return

    # Load each snapshot's placement and identify (thread_offset, thread_idx)
    boards = []
    for path in files:
        try:
            d = json.load(open(path))
            pl = d.get("placement", [])
            config = tuple(
                (p["piece_id"], p["rotation"]) if isinstance(p, dict) else None
                for p in pl
            )
            # Extract thread info from path: .../offset_NNNN/tII_sJJJ_dKKK.json
            offset = int(Path(path).parent.name.split("_")[1])
            fname = Path(path).name
            t_idx = int(fname[1:3])
            global_tid = offset + t_idx
            boards.append((global_tid, config, path))
        except Exception as e:
            print(f"  skip {path}: {e}")

    print(f"[load] {len(boards)} loaded")
    if not boards:
        return

    # Group by global_tid first (each tid is a basin family seed)
    by_tid = defaultdict(list)
    for tid, cfg, path in boards:
        by_tid[tid].append((cfg, path))
    productive_tids = sorted(by_tid.keys())
    print(f"\n=== productive thread_ids: {len(productive_tids)} ===")
    print(f"  TIDs: {productive_tids}")

    # For each productive TID, characterize the basin family by taking the
    # earliest snapshot's first-80-cell prefix.
    family_prefixes = {}
    for tid, snaps in by_tid.items():
        # Take the FIRST snapshot of this thread (deepest will be appended over time)
        snaps_sorted = sorted(snaps, key=lambda x: x[1])
        first_cfg = snaps_sorted[0][0]
        family_prefixes[tid] = first_cfg[:80]

    # Now cluster: two thread_ids are in the same family if their prefixes
    # agree on at least 60 of the first 80 cells.
    tids = list(productive_tids)
    parent = {t: t for t in tids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    THRESHOLD = 60  # min cells matching in the 80-cell prefix
    for i in range(len(tids)):
        for j in range(i + 1, len(tids)):
            a, b = tids[i], tids[j]
            match = sum(
                1
                for k in range(80)
                if family_prefixes[a][k] == family_prefixes[b][k]
            )
            if match >= THRESHOLD:
                pi, pj = find(a), find(b)
                if pi != pj:
                    parent[pi] = pj

    # Group thread_ids by family
    family_groups = defaultdict(list)
    for t in tids:
        family_groups[find(t)].append(t)

    print(f"\n=== basin families: {len(family_groups)} ===")
    print(f"  (threshold: {THRESHOLD}/80 cells matching in early prefix)")
    for f_idx, (rep, members) in enumerate(sorted(family_groups.items())):
        print(f"  family {f_idx}: {sorted(members)} ({len(members)} threads)")


if __name__ == "__main__":
    main()
