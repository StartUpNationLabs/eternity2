"""ISENTROPE Variant B (distinct pieces / true-E2 entropy) — own process.
Exact small-n via DFS with used-set. Writes each point as it completes."""
import sys, os, time, math, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
sys.path.insert(0, os.path.dirname(__file__))
from count_entropy import count_distinct

OUT = "scripts/v209_isentrope/output/variantB.jsonl"
open(OUT, "w").close()
print("=== Variant B: true-E2 entropy (distinct pieces) ===", flush=True)
for n in range(1, 6):
    t = time.time()
    w, exact, nodes = count_distinct(n, node_cap=2_000_000_000)
    s = math.log10(w) if w > 0 else float("-inf")
    secs = time.time() - t
    rec = {"n": n, "W": str(w), "S": s, "S_over_n2": (s/(n*n) if w>0 else None),
           "exact": exact, "nodes": nodes, "secs": secs}
    tag = "exact" if exact else f"PARTIAL(nodes={nodes})"
    print(f"  n={n}: W={w}  S={s:.4f}  S/n^2={(s/(n*n) if w>0 else float('nan')):.5f}  [{tag}]  ({secs:.1f}s)", flush=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(rec) + "\n")
    if not exact:
        print(f"  n={n} hit node cap; larger n intractable — stop", flush=True); break
    if secs > 1800:
        print(f"  n={n} took {secs:.0f}s; stopping", flush=True); break
print("Variant B done.", flush=True)
