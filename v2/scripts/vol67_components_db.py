#!/usr/bin/env python3
"""Vol-67 step 1 — Pre-compute basin-component representatives.

For each of the 47 basin-components in our 135 unique 455+ records,
pick a representative (the highest-score board in the component) and
save as a JSON db.

This db is used by FCD-ALNS to determine basin-component membership
during search.

Output: output/vol-67/components_db.json
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
    if not isinstance(arr, list) or len(arr) == 0: return None, None
    pid = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pid[item["piece_id"]] = item.get("pos", idx)
    return pid, d.get("matched")


def main():
    THRESHOLD = 100
    MIN_SCORE = 455

    # Load all unique 455+ records
    records = []
    seen = set()
    for f in glob.glob("output/**/*.json", recursive=True):
        if "cycles.json" in f or ".log" in f or "INVALID" in f: continue
        pid, sc = load(f)
        if pid is None or not isinstance(sc, int) or sc < MIN_SCORE: continue
        h = hash(tuple(sorted(pid.items())))
        if h in seen: continue
        seen.add(h)
        records.append((sc, pid, f))
    n = len(records)
    print(f"Records: {n}")

    # Union-find on Hamming<THRESHOLD
    parent = list(range(n))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i in range(n):
        for j in range(i + 1, n):
            ham = sum(1 for k in records[i][1] if records[i][1][k] != records[j][1].get(k))
            if ham < THRESHOLD:
                pi, pj = find(i), find(j)
                if pi != pj: parent[pi] = pj

    # Group by component
    comps = collections.defaultdict(list)
    for i in range(n):
        comps[find(i)].append(i)
    print(f"Components: {len(comps)}")

    # For each component, pick the highest-score record as rep
    reps = []
    for root, idxs in comps.items():
        idxs.sort(key=lambda i: -records[i][0])
        best = idxs[0]
        sc, pid, f = records[best]
        reps.append({
            "component_id": len(reps),
            "size": len(idxs),
            "max_score": sc,
            "rep_file": f,
            "rep_placement": pid,
            "internal_max_hamming": max(
                (sum(1 for k in records[i][1]
                     if records[i][1][k] != records[j][1].get(k))
                 for i in idxs for j in idxs if i < j),
                default=0
            ),
        })

    # Sort by max_score desc
    reps.sort(key=lambda r: -r["max_score"])

    # Compute inter-component min Hamming (closest other component to each)
    for i, r in enumerate(reps):
        min_ham_to_other = None
        for j, r2 in enumerate(reps):
            if i == j: continue
            ham = sum(1 for k in r["rep_placement"]
                      if r["rep_placement"][k] != r2["rep_placement"].get(k))
            if min_ham_to_other is None or ham < min_ham_to_other:
                min_ham_to_other = ham
        r["min_ham_to_nearest_other"] = min_ham_to_other

    # Print summary
    print(f"\n{'comp':>4} | {'size':>4} | {'max_sc':>6} | {'int_ham':>7} | {'nearest_other':>13} | rep")
    for r in reps[:15]:
        print(f"{r['component_id']:>4} | {r['size']:>4} | {r['max_score']:>6} | "
              f"{r['internal_max_hamming']:>7} | {r['min_ham_to_nearest_other']:>13} | "
              f"...{r['rep_file'][-50:]}")

    # Save as JSON. Convert placement dict (int keys) to list-of-tuples for JSON.
    out = {
        "threshold": THRESHOLD,
        "min_score": MIN_SCORE,
        "n_components": len(reps),
        "components": [
            {
                "component_id": r["component_id"],
                "size": r["size"],
                "max_score": r["max_score"],
                "rep_file": r["rep_file"],
                "rep_placement": [[pid, pos] for pid, pos in sorted(r["rep_placement"].items())],
                "internal_max_hamming": r["internal_max_hamming"],
                "min_ham_to_nearest_other": r["min_ham_to_nearest_other"],
            }
            for r in reps
        ],
    }
    Path("output/vol-67").mkdir(parents=True, exist_ok=True)
    out_path = "output/vol-67/components_db.json"
    with open(out_path, "w") as f:
        json.dump(out, f)
    print(f"\nWrote {out_path} ({Path(out_path).stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
