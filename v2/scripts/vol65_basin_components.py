#!/usr/bin/env python3
"""Vol-65 day 4 — Basin-component landscape via union-find on σ-distance.

Discovers that our 135 unique 455+ records form 47 disjoint
basin-components when connected via Hamming < 100. McGavin is a
size-1 component (min distance 247).
"""
import json, glob, collections

def load(p):
    try:
        with open(p) as f: d = json.load(f)
    except: return None, None
    if not isinstance(d, dict): return None, None
    arr = d.get("placement", [])
    if not isinstance(arr, list) or len(arr) == 0: return None, None
    pid = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pid[item["piece_id"]] = item.get("pos", idx)
    return pid, d.get("matched")


def main(threshold=100, min_score=455):
    records = []
    seen = set()
    for f in glob.glob("output/**/*.json", recursive=True):
        if "cycles.json" in f or ".log" in f or "INVALID" in f: continue
        pid, sc = load(f)
        if pid is None or not isinstance(sc, int) or sc < min_score: continue
        h = hash(tuple(sorted(pid.items())))
        if h in seen: continue
        seen.add(h)
        records.append((sc, pid, f))
    n = len(records)
    print(f"Unique records >= {min_score}: {n}")

    parent = list(range(n))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x

    for i in range(n):
        for j in range(i+1, n):
            ham = sum(1 for k in records[i][1] if records[i][1][k] != records[j][1].get(k))
            if ham < threshold:
                pi, pj = find(i), find(j)
                if pi != pj: parent[pi] = pj

    comps = collections.defaultdict(list)
    for i in range(n):
        comps[find(i)].append(i)
    print(f"Distinct components: {len(comps)}")
    sizes = sorted([len(c) for c in comps.values()], reverse=True)
    print(f"Size distribution (top 10): {sizes[:10]}")
    print(f"Singletons: {sum(1 for s in sizes if s == 1)}")

    # Per-comp max score
    comp_info = []
    for root, idxs in comps.items():
        max_sc = max(records[i][0] for i in idxs)
        comp_info.append((len(idxs), max_sc))
    comp_info.sort(key=lambda x: (-x[1], -x[0]))
    print(f"\nTop 10 components by max score:")
    for sz, mx in comp_info[:10]:
        print(f"  size={sz}, max_score={mx}")


if __name__ == "__main__":
    main()
