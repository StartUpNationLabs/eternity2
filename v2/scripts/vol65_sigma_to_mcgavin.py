#!/usr/bin/env python3
"""Vol-65 — σ-distance from every saved 455+ board to McGavin 469.

Goal: find boards with SMALL σ-distance to McGavin. These are
"near-miss" basins potentially bridgeable by basin-spanning moves.

For each board, compute:
- Hamming distance (cells with different piece-id)
- σ-cycle decomposition lengths
- Largest cycle length (bottleneck for any subset-move)

Output: ranked list by σ-distance ascending.
"""

import collections
import glob
import json
from pathlib import Path


def load(p):
    try:
        with open(p) as f: d = json.load(f)
    except Exception: return None, None
    if not isinstance(d, dict): return None, None
    arr = d.get("placement", [])
    if not isinstance(arr, list): return None, None
    pid_to_pos = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pos = item.get("pos", idx)
        if "piece_id" not in item: continue
        pid_to_pos[item["piece_id"]] = pos
    return pid_to_pos, d.get("matched")


def sigma_cycles(p_a, p_b):
    """σ:a→b at position level."""
    a_pos = {pos: pid for pid, pos in p_a.items()}
    s = {}
    for pos, pid in a_pos.items():
        new = p_b.get(pid)
        if new is not None and new != pos:
            s[pos] = new
    visited = set()
    cycles = []
    for start in s:
        if start in visited: continue
        c = []
        cur = start
        while cur in s and cur not in visited:
            visited.add(cur); c.append(cur); cur = s[cur]
        if len(c) >= 2: cycles.append(c)
    return cycles


def main():
    mcgavin, mcg_score = load("output/vol-65/mcgavin_469.json")
    if mcgavin is None:
        print("FAIL: no McGavin board")
        return

    results = []
    seen_hashes = set()
    for f in glob.glob("output/**/*.json", recursive=True):
        if "cycles.json" in f or ".log" in f or "INVALID" in f: continue
        if "mcgavin" in f.lower(): continue
        bd, sc = load(f)
        if bd is None or not isinstance(sc, int) or sc < 455: continue
        # Dedup by bucas URL hash
        try:
            with open(f) as fp: d = json.load(fp)
            url = d.get("bucas_url", "")
            h = hash(url) if url else hash(json.dumps(sorted(bd.items())))
        except Exception: continue
        if h in seen_hashes: continue
        seen_hashes.add(h)

        ham = sum(1 for pid in bd if bd[pid] != mcgavin.get(pid))
        cycles = sigma_cycles(bd, mcgavin)
        lens = sorted([len(c) for c in cycles], reverse=True)
        max_cyc = lens[0] if lens else 0
        results.append((sc, ham, max_cyc, lens, f))

    print(f"Found {len(results)} unique records with score >= 455")
    print(f"\n{'score':>5} | {'ham':>4} | {'max_cyc':>7} | {'cycles':<35} | {'file':<60}")
    # Sort by Hamming distance (closest to McGavin first)
    for sc, ham, mc, lens, f in sorted(results, key=lambda x: x[1])[:30]:
        cycle_str = "+".join(str(l) for l in lens[:8])
        if len(lens) > 8: cycle_str += "..."
        print(f"{sc:>5} | {ham:>4} | {mc:>7} | {cycle_str:<35} | ...{f[-58:]}")
    print()
    # Histogram of Hamming distances
    import collections
    hams = [r[1] for r in results]
    bucket_edges = [0, 50, 100, 150, 200, 220, 240, 250, 256]
    hist = collections.Counter()
    for h in hams:
        for i in range(len(bucket_edges)-1):
            if bucket_edges[i] <= h < bucket_edges[i+1]:
                hist[(bucket_edges[i], bucket_edges[i+1])] += 1; break
    print(f"Hamming-distance histogram to McGavin:")
    for (lo, hi), n in sorted(hist.items()):
        print(f"  [{lo}, {hi}): {n}")


if __name__ == "__main__":
    main()
